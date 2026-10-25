from fastapi_mail import MessageSchema, MessageType, FastMail, ConnectionConfig
from config import settings
from pathlib import Path
from typing import List
from utils import TEMPLATE_PATH
import asyncio
from utils import get_user_verificaion_email, get_password_reset_email

config = ConnectionConfig(
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_SSL_TLS=True,
    MAIL_STARTTLS=False,
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    TEMPLATE_FOLDER=TEMPLATE_PATH,
    VALIDATE_CERTS=False,
)

mail = FastMail(config=config)


async def create_message(recipients: List[str], subject: str, body: str):
    message = MessageSchema(
        recipients=recipients, subject=subject, body=body, subtype=MessageType.html
    )
    return message


async def send_email_verification_otp(
    recipients: List[str], username: str, otp_code: str
):
    subject = "Email Verification For Evolution"
    body = await asyncio.to_thread(
        get_user_verificaion_email, username=username, otp_code=otp_code
    )
    message = await create_message(recipients=recipients, subject=subject, body=body)
    await mail.send_message(message=message)


async def send_password_reset_otp(recipients: List[str], username: str, otp_code: str):
    subject = "Password Reset For Evolution"
    body = await asyncio.to_thread(
        get_password_reset_email, username=username, otp_code=otp_code
    )
    message = await create_message(recipients=recipients, subject=subject, body=body)
    await mail.send_message(message=message)
