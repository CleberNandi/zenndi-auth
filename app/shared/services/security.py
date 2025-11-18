"""
Camada de segurança central do serviço de autenticação Zenndi.

Inclui:
- Hash seguro de senhas (argon2)
- Tokens JWT (RS256)
- Autenticação de 2 fatores (TOTP)
- Validação de força de senha
"""

import base64
import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum
from io import BytesIO
from typing import Any

import pyotp
import qrcode
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ==============================================================
# 🔐 CONFIGURAÇÃO DE HASH DE SENHAS (ARGON2)
# ==============================================================

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt_sha256"],
    default="argon2",
    deprecated="auto",
)


# ==============================================================
# 🧾 ENUM DE TIPOS DE TOKEN
# ==============================================================


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# ==============================================================
# 🔒 GERENCIADOR DE SENHAS
# ==============================================================


class SecurityManager:
    """Gerenciador central de segurança"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha está correta"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Gera hash da senha"""
        return pwd_context.hash(password)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Valida força da senha"""
        min_length = getattr(settings, "PASSWORD_MIN_LENGTH", 8)

        if len(password) < min_length:
            return False, f"Senha deve ter pelo menos {min_length} caracteres"

        if not any(c.isupper() for c in password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"

        if not any(c.islower() for c in password):
            return False, "Senha deve conter pelo menos uma letra minúscula"

        if not any(c.isdigit() for c in password):
            return False, "Senha deve conter pelo menos um número"

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Senha deve conter pelo menos um caractere especial"

        return True, "Senha válida"


# ==============================================================
# 🧩 GERENCIADOR DE TOKENS JWT (ASSIMÉTRICO)
# ==============================================================


class JWTManager:
    """Gerenciador de tokens JWT"""

    @staticmethod
    def _get_private_key() -> str:
        with open(settings.JWT_PRIVATE_KEY_PATH, "r") as f:
            return f.read()

    @staticmethod
    def _get_public_key() -> str:
        with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
            return f.read()

    @classmethod
    def create_access_token(cls, data: dict[str, Any]) -> str:
        """Cria token de acesso"""
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(
            minutes=getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
        )
        to_encode.update({"exp": expire, "type": "access"})
        private_key = cls._get_private_key()

        return jwt.encode(
            to_encode,
            private_key,
            algorithm="RS256",
        )

    @classmethod
    def create_refresh_token(cls, data: dict[str, Any]) -> str:
        """Cria token de refresh"""
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(
            days=getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 30)
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        private_key = cls._get_private_key()

        return jwt.encode(
            to_encode,
            private_key,
            algorithm="RS256",
        )

    @classmethod
    def verify_token(
        cls, token: str, token_type: TokenType = TokenType.ACCESS
    ) -> dict[str, Any] | None:
        """Verifica e decodifica token"""
        try:
            public_key = cls._get_public_key()
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
        except JWTError:
            return None
        else:
            if payload.get("type") != token_type:
                return None
            return payload


# ==============================================================
# 📲 GERENCIADOR DE TOTP (2FA)
# ==============================================================


class TOTPManager:
    """Gerenciador de 2FA TOTP"""

    @staticmethod
    def generate_secret() -> str:
        """Gera secret para 2FA"""
        return pyotp.random_base32()

    @staticmethod
    def generate_qr_code(email: str, secret: str) -> str:
        """Gera QR code para 2FA (retorna base64)"""
        issuer = getattr(settings, "TOTP_ISSUER_NAME", "Zenny")
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name=issuer)

        # Gera QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Converte para base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")  # type: ignore
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verifica código TOTP"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)

    @staticmethod
    def get_backup_codes() -> list[str]:
        """Gera códigos de backup"""
        return [secrets.token_hex(4).upper() for _ in range(10)]
