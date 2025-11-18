import secrets
from datetime import UTC, datetime, timedelta
from smtplib import SMTPException
from uuid import uuid4

import sentry_sdk
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.schemas import (
    DeviceInfo,
    TokenResponse,
    TwoFactorSetup,
    UserLogin2FA,
    UserRegister,
)
from app.core.config import settings
from app.core.metrics import CODE_SENT, LOGIN_FAILED, LOGIN_SUCCESS, USER_CREATED
from app.models.auth_session import AuthSession
from app.models.backup_code import BackupCode
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.shared.services.email_service import EmailService
from app.shared.services.security import JWTManager, SecurityManager, TOTPManager
from app.utils.date_utils import ensure_utc, utc_now


class AuthService:
    @staticmethod
    async def register_user(
        db: AsyncSession, user_data: UserRegister, ip_address: str, user_agent: str
    ) -> dict[str, str | int]:
        """Registra novo usuário"""

        # Verifica se email já existe
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado"
            )

        # Valida força da senha
        is_valid, message = SecurityManager.validate_password_strength(
            user_data.password
        )
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

        # Cria usuário
        hashed_password = SecurityManager.get_password_hash(user_data.password)
        verification_token = secrets.token_urlsafe(32)

        user = User(
            name=user_data.nome,
            email=user_data.email,
            hashed_password=hashed_password,
            verification_token=verification_token,
            is_verified=False,
            plan="Basic",
            password_changed_at=datetime.now(UTC),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        USER_CREATED.labels(result="success").inc()

        # Registra tentativa de login
        login_attempt = LoginAttempt(
            email=user_data.email,
            ip_address=ip_address,
            success=True,
            attempted_at=datetime.now(UTC),
            user_agent=user_agent,
        )
        db.add(login_attempt)
        await db.commit()

        # 🆕 ENVIAR EMAIL DE VERIFICAÇÃO
        try:
            await AuthService.send_welcome_verification_email(user)
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Erro de conexão ao enviar email de verificação para %s: %s",
                user.email,
                e,
            )
        except ValueError as e:
            logger.warning("Erro de configuração de email para %s: %s", user.email, e)
        except SMTPException as e:
            logger.error(
                "Erro SMTP ao enviar email de verificação para %s: %s", user.email, e
            )
        except Exception:  # noqa: BLE001 - fallback para erros não previstos
            logger.exception(
                "Erro inesperado ao enviar email de verificação para %s", user.email
            )

        return {
            "message": "Usuário criado com sucesso! Verifique seu email para ativar a conta.",
            "user_id": user.id,
        }

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, login_data: UserLogin2FA, ip_address: str, user_agent: str
    ) -> tuple[User, bool]:  # (user, requires_2fa)
        """Autentica usuário com suporte a 2FA"""

        # Busca usuário
        user = await AuthService._find_user_by_email(db, login_data.email)

        # Cria registro de tentativa de login
        login_attempt = LoginAttempt(
            email=login_data.email,
            ip_address=ip_address,
            success=False,
            attempted_at=datetime.now(UTC),
            user_agent=user_agent,
        )

        # Validações básicas
        await AuthService._validate_user_login(db, user, login_data, login_attempt)

        # Verifica 2FA se necessário
        requires_2fa = await AuthService._handle_2fa_verification(
            db, user, login_data, login_attempt
        )
        if requires_2fa:
            return user, True

        # Login bem-sucedido
        await AuthService._finalize_successful_login(db, user, login_attempt)

        return user, False

    @staticmethod
    async def _find_user_by_email(db: AsyncSession, email: str) -> User:
        """Busca usuário por email"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            LOGIN_FAILED.labels(reason="Credenciais inválidas").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas"
            )

        return user

    @staticmethod
    async def _validate_user_login(
        db: AsyncSession,
        user: User,
        login_data: UserLogin2FA,
        login_attempt: LoginAttempt,
    ) -> None:
        """Valida conta e credenciais do usuário"""

        # Verifica se conta está bloqueada
        if user.is_locked:
            db.add(login_attempt)
            await db.commit()
            LOGIN_FAILED.labels(reason="Conta temporariamente bloqueada").inc()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Conta temporariamente bloqueada",
            )

        # Verifica senha
        if not SecurityManager.verify_password(
            login_data.password, user.hashed_password
        ):
            await AuthService._handle_failed_login(db, user, login_attempt)
            LOGIN_FAILED.labels(reason="Credenciais inválidas").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas"
            )

        # Verifica se email foi verificado
        if not user.is_verified:
            db.add(login_attempt)
            await db.commit()
            LOGIN_FAILED.labels(
                reason="Email não verificado. Verifique seu email ou solicite um novo link de verificação"
            ).inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email não verificado. Verifique seu email ou solicite um novo link de verificação.",
            )

    @staticmethod
    async def _handle_failed_login(
        db: AsyncSession, user: User, login_attempt: LoginAttempt
    ) -> None:
        """Lida com tentativas de login falhadas"""
        user.failed_login_attempts += 1

        max_attempts = settings.get("MAX_LOGIN_ATTEMPTS", 5)  # type: ignore
        if user.failed_login_attempts >= max_attempts:
            lockout_duration = settings.get("LOCKOUT_DURATION_MINUTES", 15)  # type: ignore
            user.locked_until = datetime.now(UTC) + timedelta(minutes=lockout_duration)  # type: ignore

        db.add(login_attempt)
        await db.commit()

    @staticmethod
    async def _handle_2fa_verification(
        db: AsyncSession,
        user: User,
        login_data: UserLogin2FA,
        login_attempt: LoginAttempt,
    ) -> bool:
        """Verifica 2FA se habilitado. Retorna True se ainda precisa de 2FA"""

        if not user.is_2fa_enabled:
            return False

        # Se não forneceu códigos 2FA, indica que precisa
        if not (login_data.totp_code or login_data.backup_code):
            return True

        # Verifica códigos fornecidos
        totp_valid = False
        backup_valid = False

        # Verifica código TOTP
        if login_data.totp_code and user.totp_secret:
            totp_valid = TOTPManager.verify_totp(user.totp_secret, login_data.totp_code)

        # Verifica código de backup
        if login_data.backup_code and not totp_valid:
            backup_valid = await AuthService._verify_backup_code(
                db, user.id, login_data.backup_code
            )

        # Se forneceu código mas está inválido
        if not (totp_valid or backup_valid):
            if not totp_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código TOTP inválido",
                )
            elif not backup_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Código de backup inválido",
                )

        return False

    @staticmethod
    async def _finalize_successful_login(
        db: AsyncSession, user: User, login_attempt: LoginAttempt
    ) -> None:
        """Finaliza login bem-sucedido"""
        user.reset_failed_attempts()
        user.last_login = datetime.now(UTC)
        login_attempt.success = True
        LOGIN_SUCCESS.labels(client="web").inc()
        sentry_sdk.set_user({"id": user.id, "email": user.email, "username": user.name})

        db.add(login_attempt)
        await db.commit()

    @staticmethod
    async def create_user_session(
        db: AsyncSession, user: User, ip_address: str, user_agent: str
    ) -> TokenResponse:
        """Cria sessão de usuário e tokens"""

        # Dados para o JWT
        token_data = {"sub": str(user.id), "email": user.email}

        # Cria tokens
        access_token = JWTManager.create_access_token(token_data)
        refresh_token = JWTManager.create_refresh_token(token_data)
        refresh_expire_days = settings.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 30)
        refresh_expire_minutes = settings.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)

        # Cria sessão
        session = AuthSession(
            session_token=str(uuid4()),
            refresh_token=refresh_token,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=utc_now() + timedelta(days=refresh_expire_days),
            last_activity=datetime.now(UTC),
        )

        db.add(session)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=refresh_expire_minutes * 60,
        )

    @staticmethod
    async def setup_2fa(db: AsyncSession, user: User) -> TwoFactorSetup:
        """Configura 2FA para usuário"""

        # Gera secret
        secret = TOTPManager.generate_secret()

        # Gera QR code
        qr_code = TOTPManager.generate_qr_code(user.email, secret)

        # Gera códigos de backup
        backup_codes = TOTPManager.get_backup_codes()

        # Salva secret (mas não ativa ainda)
        user.totp_secret = secret

        # Remove códigos de backup antigos
        await db.execute(select(BackupCode).where(BackupCode.user_id == user.id))

        # Salva novos códigos de backup
        for code in backup_codes:
            code_hash = SecurityManager.get_password_hash(code)
            backup_code = BackupCode(user_id=user.id, code_hash=code_hash)
            db.add(backup_code)

        await db.commit()

        return TwoFactorSetup(secret=secret, qr_code=qr_code, backup_codes=backup_codes)

    @staticmethod
    async def enable_2fa(
        db: AsyncSession, user: User, totp_code: str
    ) -> dict[str, str]:
        """Ativa 2FA após verificar código"""

        if not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA não foi configurado",
            )

        # Verifica código
        if not TOTPManager.verify_totp(user.totp_secret, totp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Código 2FA inválido"
            )

        # Ativa 2FA
        user.is_2fa_enabled = True
        await db.commit()

        return {"message": "2FA ativado com sucesso"}

    @staticmethod
    async def disable_2fa(db: AsyncSession, user: User) -> dict[str, str]:
        """Desativa 2FA"""

        user.is_2fa_enabled = False
        user.totp_secret = None

        # Remove códigos de backup
        result = await db.execute(
            select(BackupCode).where(BackupCode.user_id == user.id)
        )
        for backup_code in result.scalars():
            await db.delete(backup_code)

        await db.commit()

        return {"message": "2FA desativado com sucesso"}

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession, refresh_token: str
    ) -> TokenResponse:
        """Renova token de acesso usando refresh token"""

        # Verifica refresh token
        payload = JWTManager.verify_token(refresh_token, "refresh")  # type: ignore
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        # Verifica se sessão existe e está ativa
        result = await db.execute(
            select(AuthSession).where(
                and_(
                    AuthSession.refresh_token == refresh_token,
                    AuthSession.user_id == int(user_id),
                    AuthSession.is_active,
                    AuthSession.expires_at > datetime.now(UTC),
                )
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão inválida ou expirada",
            )

        # Busca usuário
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido"
            )

        # Cria novo access token
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = JWTManager.create_access_token(token_data)

        # Atualiza última atividade
        session.last_activity = datetime.now(UTC)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Mantém o mesmo refresh token
            expires_in=settings.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30) * 60,  # type: ignore
        )

    @staticmethod
    async def logout(
        db: AsyncSession, user: User, refresh_token: str
    ) -> dict[str, str]:
        """Faz logout invalidando sessão"""

        # Busca e desativa sessão
        result = await db.execute(
            select(AuthSession).where(
                and_(
                    AuthSession.refresh_token == refresh_token,
                    AuthSession.user_id == user.id,
                    AuthSession.is_active,
                )
            )
        )
        session = result.scalar_one_or_none()

        if session:
            session.is_active = False
            await db.commit()

        return {"message": "Logout realizado com sucesso"}

    @staticmethod
    async def logout_all(db: AsyncSession, user: User) -> dict[str, str]:
        """Faz logout de todas as sessões do usuário"""

        result = await db.execute(
            select(AuthSession).where(
                and_(AuthSession.user_id == user.id, AuthSession.is_active)
            )
        )

        for session in result.scalars():
            session.is_active = False

        await db.commit()

        return {"message": "Logout de todas as sessões realizado"}

    @staticmethod
    async def get_user_sessions(db: AsyncSession, user: User) -> list[DeviceInfo]:
        """Lista sessões ativas do usuário"""

        query = (
            select(AuthSession)
            .where(AuthSession.user_id == user.id)
            .where(AuthSession.is_active.is_(True))
            .where(AuthSession.expires_at > utc_now())
            .order_by(AuthSession.last_activity.desc())
        )
        result = await db.execute(query)
        active_sessions = result.scalars().all()

        return [
            DeviceInfo(
                session_id=session.session_token,
                device_info=session.device_info,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                last_activity=session.last_activity,
                is_current=False,  # Será definido no endpoint
            )
            for session in active_sessions
        ]

    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> dict[str, str]:
        """Altera senha do usuário"""

        # Verifica senha atual
        if not SecurityManager.verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta"
            )

        # Valida nova senha
        is_valid, message = SecurityManager.validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

        # Verifica se não é a mesma senha
        if SecurityManager.verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da atual",
            )

        # Atualiza senha
        user.hashed_password = SecurityManager.get_password_hash(new_password)
        user.password_changed_at = datetime.now(UTC)

        # Invalida todas as sessões (força novo login)
        await AuthService.logout_all(db, user)

        await db.commit()

        return {"message": "Senha alterada com sucesso"}

    @staticmethod
    async def check_backup_code(db: AsyncSession, user_id: int, code: str) -> bool:
        return await AuthService._verify_backup_code(db, user_id, code)

    @staticmethod
    async def _verify_backup_code(
        db: AsyncSession, user_id: int, backup_code: str
    ) -> bool:
        """Verifica código de backup"""

        result = await db.execute(
            select(BackupCode).where(
                and_(BackupCode.user_id == user_id, BackupCode.used.is_(False))
            )
        )

        for code in result.scalars():
            if SecurityManager.verify_password(backup_code, code.code_hash):
                # Marca como usado
                code.used = True
                code.used_at = datetime.now(UTC)
                await db.commit()
                return True

        return False

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> dict[str, str]:
        """Verifica email através do token"""

        # Busca usuário pelo token
        result = await db.execute(
            select(User).where(
                and_(User.verification_token == token, User.is_verified.is_(False))
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido ou usuário já verificado",
            )

        # Verifica se token não expirou (opcional - 24h)
        if ensure_utc(user.created_at) < utc_now() - timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expirado. Solicite um novo email de verificação",
            )

        # Marca como verificado
        user.is_verified = True
        user.verification_token = None  # Remove o token usado
        user.verified_at = datetime.now(UTC)  # Se tiver essa coluna

        await db.commit()

        return {"message": "Email verificado com sucesso! Você já pode fazer login."}

    @staticmethod
    async def resend_verification_email(db: AsyncSession, email: str) -> dict[str, str]:
        """Reenvia email de verificação"""

        # Busca usuário
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # Por segurança, não revela se email existe
            return {"message": "Se o email existir, um novo link foi enviado"}

        if user.is_verified:
            return {"message": "Email já está verificado"}

        # Gera novo token
        user.verification_token = secrets.token_urlsafe(32)
        await db.commit()

        # Enviar email (você implementa com seu serviço)
        await EmailService.send_verification_email(
            user.email, user.name, user.verification_token
        )  # type: ignore

        return {"message": "Novo email de verificação enviado"}

    @staticmethod
    async def send_welcome_verification_email(user: User) -> None:
        """Envia email de boas-vindas com verificação"""

        await EmailService.send_verification_email(
            email=user.email, name=user.name, token=user.verification_token
        )  # type: ignore

        CODE_SENT.labels(channel="email").inc()
