from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    get_user_agent,
)
from app.api.v1.auth.schemas import (
    DeviceInfo,
    Enable2FARequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    TwoFactorSetup,
    UserLogin2FA,
    UserProfile,
    UserRegister,
    Verify2FARequest,
)
from app.api.v1.auth.services import AuthService
from app.core.database import get_async_db
from app.core.middlewares.rate_limit_middleware import rate_limit
from app.core.network_utils import get_client_ip
from app.models.user import User

DBSession = Annotated[AsyncSession, Depends(get_async_db)]

# # Rate limiting
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/register", response_model=dict)
@limiter.limit("3000/minute")  # type: ignore[reportUntypedFunctionDecorator]
async def register(
    request: Request, user_data: UserRegister, db: DBSession
) -> dict[str, str | int]:
    """Registra novo usuário"""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    return await AuthService.register_user(db, user_data, ip_address, user_agent)


@router.post("/login", response_model=TokenResponse)
@rate_limit(limit=10, window_seconds=60)  # 10 req / 60s per IP
async def login(
    request: Request,
    login_data: UserLogin2FA,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Login com suporte a 2FA"""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    try:
        user, requires_2fa = await AuthService.authenticate_user(
            db, login_data, ip_address, user_agent
        )

        if requires_2fa and not (login_data.totp_code or login_data.backup_code):
            return TokenResponse(
                access_token="", refresh_token="", expires_in=0, requires_2fa=True
            )

        return await AuthService.create_user_session(db, user, ip_address, user_agent)
    except HTTPException as e:
        # Se for erro de email não verificado, dá mais informações
        if e.status_code == 403 and "Email não verificado" in str(e.detail):
            # Opcionalmente, você pode adicionar um campo no response para indicar que precisa verificar email
            # Por enquanto, só re-raise o erro com a mensagem melhorada
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Email não verificado",
                    "action": "verify_email",
                    "description": "Verifique seu email ou solicite um novo link de verificação",
                },
            ) from e
        # Re-raise outros erros normalmente
        raise


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Renova access token"""
    return await AuthService.refresh_access_token(db, refresh_data.refresh_token)


@router.post("/logout")
async def logout(
    refresh_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Logout da sessão atual"""
    return await AuthService.logout(db, current_user, refresh_data.refresh_token)


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Logout de todas as sessões"""
    return await AuthService.logout_all(db, current_user)


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserProfile:
    """Obtém perfil do usuário atual"""
    return UserProfile(
        id=current_user.id,
        nome=current_user.name,
        email=current_user.email,
        is_verified=current_user.is_verified,
        is_2fa_enabled=current_user.is_2fa_enabled,
        plan=current_user.plan,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
    )


@router.get("/sessions", response_model=list[DeviceInfo])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[DeviceInfo]:
    """Lista sessões ativas do usuário"""
    return await AuthService.get_user_sessions(db, current_user)


@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Verifica email do usuário através do token"""
    return await AuthService.verify_email(db, token)


@router.post("/resend-verification")
@limiter.limit("2000/minute")  # type: ignore[reportUntypedFunctionDecorator]
async def resend_verification_email(
    request: Request,
    email_data: dict[str, str],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Reenvia email de verificação"""
    return await AuthService.resend_verification_email(db, email_data["email"])


# ============================================================================
# ENDPOINTS DE 2FA
# ============================================================================


@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> TwoFactorSetup:
    """Configura 2FA para o usuário"""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA já está habilitado"
        )

    return await AuthService.setup_2fa(db, current_user)


@router.post("/2fa/enable")
async def enable_2fa(
    enable_data: Enable2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Ativa 2FA após verificar código"""
    return await AuthService.enable_2fa(db, current_user, enable_data.totp_code)


@router.post("/2fa/disable")
async def disable_2fa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Desativa 2FA"""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA não está habilitado"
        )

    return await AuthService.disable_2fa(db, current_user)


@router.post("/2fa/verify")
async def verify_2fa(
    verify_data: Verify2FARequest,
    current_user: User = Depends(get_current_user),  # Não precisa estar verificado
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str | bool]:
    """Verifica código 2FA (para login em andamento)"""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA não está habilitado"
        )

    totp_valid = False
    backup_valid = False

    if verify_data.totp_code and current_user.totp_secret:
        from app.shared.services.security import TOTPManager

        totp_valid = TOTPManager.verify_totp(
            current_user.totp_secret, verify_data.totp_code
        )

    if verify_data.backup_code and not totp_valid:
        backup_valid = await AuthService.check_backup_code(
            db, current_user.id, verify_data.backup_code
        )

    if not (totp_valid or backup_valid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Código 2FA inválido"
        )

    return {"message": "2FA verificado com sucesso", "verified": True}


# ============================================================================
# 11. ENDPOINTS DE GERENCIAMENTO DE SENHA
# ============================================================================


@router.post("/password/change")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Altera senha do usuário"""
    return await AuthService.change_password(
        db, current_user, password_data.current_password, password_data.new_password
    )


@router.post("/password/reset-request")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Solicita reset de senha (envia email)"""
    # NOTE: Implementar envio de email
    return {"message": "Instruções de reset enviadas por email"}


@router.post("/password/reset-confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Confirma reset de senha com token"""
    # NOTE:: Implementar validação de token e reset
    return {"message": "Senha resetada com sucesso"}
