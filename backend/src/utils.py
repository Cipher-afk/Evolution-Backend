import secrets, jwt
from passlib.context import CryptContext
from config import settings as s
from typing import Dict, TypedDict
from datetime import datetime, timedelta,timezone
import logging
import uuid
from pathlib import Path
from math import ceil
from authlib.oauth2 import OAuth2Client

password_context = CryptContext(schemes=["argon2"])
JWT_KEY = s.JWT_KEY
JWT_ALGORITHM = s.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRY = timedelta(minutes=20)
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = Path(BASE_DIR, "templates")
# oauth = OAuth2Client()


class TokenDataDict(TypedDict):
    jti: str
    user: Dict[str, str]
    expiry: float
    refresh: bool


def hash_password(password: str) -> str:
    hashed_password = password_context.hash(password)
    return hashed_password


def verify_password_hash(password: str, password_hash: str):
    return True if password_context.verify(password, password_hash) else False


def create_token(user_info: Dict, expiry: timedelta = None, refresh: bool = False):
    payload: TokenDataDict = {}
    payload["jti"] = str(uuid.uuid4())
    payload["user"] = user_info
    payload["expiry"] = (
        datetime.now(timezone.utc) + (expiry if expiry is not None else ACCESS_TOKEN_EXPIRY)
    ).timestamp()
    payload["refresh"] = refresh
    token = jwt.encode(payload=payload, key=JWT_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str):
    try:
        token_data = jwt.decode(token, key=JWT_KEY, algorithms=[JWT_ALGORITHM])
        return token_data
    except Exception as e:
        logging.error(e)


def create_otp():
    otp = str(secrets.randbelow(10000)).zfill(3)
    return otp


def create_otp_token(user_id: uuid.UUID, otp_code: str,referral_niche_id:str|None = None):
    payload = {"user_id": str(user_id), "otp_code": otp_code}
    if referral_niche_id is not None:
        payload["referral_niche_id"] = referral_niche_id
    payload["expiry"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()
    token = jwt.encode(payload=payload, key=JWT_KEY, algorithm=JWT_ALGORITHM)
    return token


def get_user_verificaion_email(username: str, otp_code: str):
    with open(Path(TEMPLATE_PATH, "email_verification.html"), "r") as file:
        contents = file.read()
    contents = contents.replace("{{username}}", username).replace(
        "{{otp_code}}", otp_code
    )
    return contents


def get_password_reset_email(username: str, otp_code: str):
    with open(Path(TEMPLATE_PATH, "password_reset_sent.html"), "r") as file:
        contents = file.read()
    contents = contents.replace("{{username}}", username).replace(
        "{{otp_code}}", otp_code
    )
    return contents


async def get_total_daily_xp(level_up_xp: int):
    total_daily_xp = 0
    value = level_up_xp / 14
    ceiling_value = ceil(value)
    if ceiling_value % 2 == 0:
        total_daily_xp = ceiling_value
    else:
        total_daily_xp = ceiling_value + 1
    return total_daily_xp
