from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies.redis_config import add_to_blacklist
from db_config import get_session
from .services import UserService
from .models import SignUpModel, LoginModel, UserDataDict, UpdateUserModel
from utils import (
    create_token,
    decode_token,
    TokenDataDict,
    create_otp,
    create_otp_token,
    hash_password,
)
from mail_config import send_email_verification_otp, send_password_reset_otp
from datetime import timedelta, datetime
from dependencies.security import AccessTokenBearer, RefreshTokenBearer,RoleChecker
from typing import Dict, Tuple,Optional
import asyncio
from uuid import UUID
from config import settings as s


router = APIRouter()
service = UserService()
REFRESH_TOKEN_EXPIRY = timedelta(days=30)

async def verify_otp_code(otp_token: str, sent_otp: str) -> Tuple[bool, str,str|None]:
    otp_data = await asyncio.to_thread(decode_token, token=otp_token)
    original_otp = otp_data["otp_code"]
    user_id = otp_data["user_id"]
    referral_niche_id = otp_data["referral_niche_id"] if "referral_niche_id" in otp_data else None
    expiry: float = otp_data["expiry"]
    if expiry < (datetime.now().timestamp()):
        raise HTTPException(
            status_code=403, detail={"message": "Expired OTP try again"}
        )
    if original_otp != sent_otp:
        raise HTTPException(
            status_code=403, detail={"message": "Invalid OTP code please try again"}
        )
    return (True, user_id,referral_niche_id)


async def send_user_verification_mail(
    users_email: str, username: str, user_id: UUID,referral_niche_id:str|None, bg: BackgroundTasks
):
    otp_code = await asyncio.to_thread(create_otp)
    recipients = [users_email]
    bg.add_task(
        send_email_verification_otp,
        recipients=recipients,
        username=username,
        otp_code=otp_code,
    )
    otp_token = await asyncio.to_thread(
        create_otp_token, user_id=user_id, otp_code=otp_code, referral_niche_id=referral_niche_id
    )
    return JSONResponse(
        content={
            "verified": False,
            "detail": {
                "info": {
                    "message": "Please enter the otp sent to your email for verification",
                    "otp_token": otp_token,
                }
            },
        }
    )


async def send_password_reset_mail(
    users_email: str, username: str, user_id: UUID, bg: BackgroundTasks
):
    otp_code = await asyncio.to_thread(create_otp)
    recipients = [users_email]
    bg.add_task(
        send_password_reset_otp,
        recipients=recipients,
        username=username,
        otp_code=otp_code,
    )
    otp_token = await asyncio.to_thread(
        create_otp_token, user_id=user_id, otp_code=otp_code
    )
    return JSONResponse(
        content={
            "verified": False,
            "detail": {
                "info": {
                    "message": "Please enter the otp sent to your email for password_reset",
                    "otp_token": otp_token,
                }
            },
        }
    )


@router.post("/signup",name="signup_route")
async def signup(
    signup_info: SignUpModel,
    bg: BackgroundTasks,
    referral_niche_id:Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    new_user = await service.create_user(signup_info=signup_info, session=session)
    username = new_user.username
    user_id = new_user.user_id
    users_email = new_user.email
    response = await send_user_verification_mail(
        users_email=users_email,referral_niche_id=referral_niche_id, username=username, user_id=user_id, bg=bg
    )
    return response


@router.get("/verify_email_verification_otp")
async def verify_otp(
    otp_token: str,sent_otp: str, session: AsyncSession = Depends(get_session)
):
    verified, user_id,referral_niche_id = await verify_otp_code(otp_token=otp_token, sent_otp=sent_otp)
    if verified:
        user = await service.get_user_by_user_id(user_id=user_id, session=session)
        if user is None:
            raise HTTPException(status_code=404, detail={"message": "user not found"})
        user_data: UserDataDict = {
            "email": user.email,
            "user_id": str(user.user_id),
            "username": user.username
        }
        update_data = {'is_verified':True,'role':'admin' if user.email in s.ADMIN_EMAILS else 'user'}
        update_info = UpdateUserModel(email=user.email, info=update_data)
        await service.update_user_info(update_info=update_info, session=session)
        access_token = create_token(user_info=user_data)
        refresh_token = create_token(
            user_info=user_data, expiry=REFRESH_TOKEN_EXPIRY, refresh=True
        )
        return JSONResponse(
            content={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_data": user_data,
                "refresh_niche_id":referral_niche_id if referral_niche_id is not None else None
            }
        )


@router.get("/verify_password_reset_otp")
async def verify_otp(otp_token, sent_otp, session: AsyncSession = Depends(get_session)):
    verified, user_id = await verify_otp_code(otp_token=otp_token, sent_otp=sent_otp)
    if verified:
        user = await service.get_user_by_user_id(user_id=user_id, session=session)
        if user is None:
            raise HTTPException(status_code=404, detail={"message": "user not found"})
        return True


@router.post("/login")
async def login(
    login_info: LoginModel,
    bg: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    user = await service.sign_in(login_info=login_info, session=session)
    user_data: UserDataDict = {
        "email": user.email,
        "user_id": str(user.user_id),
        "username": user.username,
    }
    if not user.is_verified:
        response = await send_user_verification_mail(
            users_email=user_data["email"],
            username=user_data["username"],
            user_id=user_data["user_id"],
            bg=bg,
        )
        return response
    access_token = create_token(user_info=user_data)
    refresh_token = create_token(
        user_info=user_data, expiry=REFRESH_TOKEN_EXPIRY, refresh=True
    )
    return JSONResponse(
        content={
            "verified": True,
            "detail": {
                "info": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user_data": user_data,
                }
            },
        }
    )


@router.get("/forgot_password")
async def reset_password(
    email: str, bg: BackgroundTasks, session: AsyncSession = Depends(get_session)
):
    user = await service.get_user_by_email(email=email, session=session)
    if user is None:
        raise HTTPException(status_code=404, detail={"message": "user not found"})
    response = await send_password_reset_mail(
        users_email=email, username=user.username, user_id=user.user_id, bg=bg
    )
    return response


@router.get("/update_password")
async def update_password(
    new_password: str,
    session: AsyncSession = Depends(get_session),
    token_data: Dict = Depends(AccessTokenBearer()),
):
    email = token_data["user"]["email"]
    user = await service.get_user_by_email(email=email, session=session)
    if user is None:
        raise HTTPException(status_code=404, detail={"message": "user not found"})
    new_password_hash = await asyncio.to_thread(hash_password, password=new_password)
    update_info = UpdateUserModel(
        email=email, info={"password_hash": new_password_hash}
    )
    response = await service.update_user_info(update_info=update_info, session=session)
    if response["updated"]:
        return JSONResponse(content={"password_updated": True})
    raise HTTPException(status_code=403, detail={"message": "Error updating password"})


@router.get("/resend_otp")
async def resend_otp(
    email: str,
    bg: BackgroundTasks,
    email_verification: bool = True,
    session: AsyncSession = Depends(get_session),
):
    user = await service.get_user_by_email(email=email, session=session)
    email = user.email
    username = user.username
    user_id = user.user_id
    response = (
        await send_user_verification_mail(
            users_email=email, username=username, user_id=user_id, bg=bg
        )
        if email_verification
        else await send_password_reset_mail(
            users_email=email, username=username, user_id=user_id, bg=bg
        )
    )
    return response


@router.get("/refresh_token")
async def get_new_access_token(
    token_data: TokenDataDict = Depends(RefreshTokenBearer()),
):
    expiry = token_data["expiry"]
    user_data = token_data["user"]
    if expiry > (datetime.now().timestamp()):
        raise HTTPException(
            status_code=403, detail={"message": "refresh token expired"}
        )
    access_token = create_token(user_info=user_data)
    refresh_token = create_token(
        user_info=user_data, expiry=REFRESH_TOKEN_EXPIRY, refresh=True
    )
    return JSONResponse(
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_data": user_data,
        }
    )


@router.get("/logout")
async def log_out(token_data: TokenDataDict = Depends(AccessTokenBearer())):
    jti = token_data["jti"]
    await add_to_blacklist(jti=jti)
    return JSONResponse(content={"message": "logged out successfully"})
