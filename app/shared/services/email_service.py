# app/core/email_service.py - VERSÃO ATUALIZADA

import asyncio
import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr, SecretStr

from app.core.config import settings

# Logger para debugs
logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=SecretStr(settings.SMTP_PASSWORD),
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_PORT=int(settings.SMTP_PORT),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,  # True para porta 465, False para 587
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,  # importante para validar o certificado SSL
)

fm = FastMail(conf)


class EmailService:
    """Serviço centralizado de emails"""

    @staticmethod
    def send_email_background(email_to: str, token: str) -> None:
        """Compatibilidade com seu código existente"""
        asyncio.run(EmailService.send_confirmation_email(email_to, token))

    @staticmethod
    async def send_email(subject: str, email_to: EmailStr, body: str) -> None:
        """Método genérico para enviar emails"""
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[email_to],
                body=body,
                subtype=MessageType.html,
            )
            await fm.send_message(message)
            logger.info(f"Email enviado com sucesso para: {email_to}")

        except Exception:
            logger.exception(f"Erro ao enviar email para {email_to}")
            raise

    @staticmethod
    async def send_confirmation_email(email_to: EmailStr, token: str) -> None:
        """Seu método existente - mantido para compatibilidade"""
        html_content = f"""
            <h1>Código de Confirmação</h1>
            <p>Use o código abaixo para confirmar seu e-mail no aplicativo:</p>
            <h2 style="font-size: 24px; font-weight: bold;">{token}</h2>
            <p>Este código expira em 10 minutos.</p>
            <p>Se não foi você quem solicitou, ignore esta mensagem.</p>
        """

        await EmailService.send_email(
            subject="Código de confirmação de e-mail",
            email_to=email_to,
            body=html_content,
        )

    @staticmethod
    async def send_verification_email(email: str, name: str, token: str) -> str | None:
        """🆕 Novo método para verificação de conta"""

        # URL do frontend - ajuste conforme sua configuração
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Bem-vindo ao Zenny!</title>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; background: #f9f9f9; }}
                .button {{
                    display: inline-block;
                    background: #667eea;
                    color: white !important;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ background: #333; color: #ccc; padding: 20px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Bem-vindo ao Zenny, {name}!</h1>
                </div>

                <div class="content">
                    <p>Obrigado por se cadastrar no <strong>Zenny</strong> - sua carteira digital inteligente!</p>

                    <p>Para começar a usar todos os recursos da plataforma, você precisa verificar seu email clicando no botão abaixo:</p>

                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">✅ Verificar Email</a>
                    </div>

                    <p>Ou copie e cole este link no seu navegador:</p>
                    <p style="background: #e9e9e9; padding: 10px; border-radius: 5px; word-break: break-all; font-family: monospace; font-size: 12px;">
                        {verification_url}
                    </p>

                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">

                    <p><strong>⚠️ Importante:</strong></p>
                    <ul>
                        <li>Este link expira em <strong>24 horas</strong></li>
                        <li>Se não foi você quem se cadastrou, ignore este email</li>
                        <li>Nunca compartilhe este link com outras pessoas</li>
                    </ul>
                </div>

                <div class="footer">
                    <p>© 2025 Zenny - Carteira Digital</p>
                    <p>Este é um email automático, não responda a esta mensagem.</p>
                </div>
            </div>
        </body>
        </html>
        """  # noqa: E501

        await EmailService.send_email(
            subject="🎉 Bem-vindo ao Zenny - Verifique seu email",
            email_to=email,
            body=html_content,
        )

    @staticmethod
    async def send_password_reset_email(email: str, name: str, token: str) -> None:
        """🆕 Email para reset de senha"""

        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"  # type: ignore

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reset de Senha - Zenny</title>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; background: #f9f9f9; }}
                .button {{
                    display: inline-block;
                    background: #ff6b6b;
                    color: white !important;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Reset de Senha</h1>
                </div>

                <div class="content">
                    <p>Olá, {name}!</p>

                    <p>Recebemos uma solicitação para redefinir a senha da sua conta no <strong>Zenny</strong>.</p>

                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">🔑 Redefinir Senha</a>
                    </div>

                    <p><strong>⚠️ Este link expira em 1 hora por segurança.</strong></p>

                    <p>Se você não solicitou esta alteração, ignore este email. Sua senha continuará a mesma.</p>
                </div>
            </div>
        </body>
        </html>
        """

        await EmailService.send_email(
            subject="🔐 Reset de Senha - Zenny", email_to=email, body=html_content
        )


# 🆕 Função para background tasks (compatibilidade)
def send_verification_email_background(email: str, name: str, token: str) -> None:
    """Para usar com BackgroundTasks se precisar"""
    asyncio.run(EmailService.send_verification_email(email, name, token))
