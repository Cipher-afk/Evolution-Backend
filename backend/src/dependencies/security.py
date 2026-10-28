from fastapi.security import HTTPBearer
from fastapi import HTTPException,status,Depends,WebSocket,WebSocketException
from utils import decode_token
import asyncio
from typing import Dict, List
from .redis_config import is_in_blacklist
from fastapi import Request
from redis import ConnectionError
from sqlalchemy.ext.asyncio import AsyncSession
from db_config import get_session
from routers.auth.services import UserService
from routers.auth.schema import User
from dataclasses import dataclass

auth_service = UserService()


class WebSocketTokenBearer():
    async def __call__(self, websocket:WebSocket):
        auth = websocket.headers.get('authorization','')
        scheme,_,token = auth.partition(' ')
        if scheme.lower() == 'bearer':
            token_data = await asyncio.to_thread(decode_token, token=token)
            if token_data is None:
                raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA,reason='Invalid Token')
            await self.verify_token(token_data=token_data)
            jti = token_data["jti"]
            try:
                if await is_in_blacklist(jti=jti):
                    raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA,reason='Invalid Token')
            except ConnectionError as e:
                raise WebSocketException(code=status.WS_1013_TRY_AGAIN_LATER,reason='Internet Connection is bad try again later')
            return token_data
        raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA,reason='No bearer token')
    
            
class TokenBearer(HTTPBearer):
    def __init__(
        self, *, bearerFormat=None, scheme_name=None, description=None, auto_error=True
    ):
        super().__init__(
            bearerFormat=bearerFormat,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request:Request):
        cred = await super().__call__(request)
        token = cred.credentials
        token_data = await asyncio.to_thread(decode_token, token=token)
        if token_data is None:
            raise HTTPException(status_code=403, detail={"message": "Invalid_Token"})
        await self.verify_token(token_data=token_data)
        jti = token_data["jti"]
        try:
            if await is_in_blacklist(jti=jti):
                raise HTTPException(status_code=403, detail={"message": "Invalid Token"})
        except ConnectionError as e:
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT,detail={'message':'check your internet connection and try again'})
        return token_data

    async def verify_token(self, token_data: Dict):
        raise NotImplementedError({"message": "Call from children classes"})


class AccessTokenBearer(TokenBearer):
    async def verify_token(self, token_data):
        if token_data["refresh"]:
            raise HTTPException(
                status_code=403, detail={"message": "Access Token Needed"}
            )


class RefreshTokenBearer(TokenBearer):
    async def verify_token(self, token_data):
        if not token_data["refresh"]:
            raise HTTPException(
                status_code=403, detail={"message": "Refresh Token Needed"}
            )

async def get_current_user(token_data:Dict = Depends(AccessTokenBearer()),session:AsyncSession = Depends(get_session)):
    user_id = token_data['user']['user_id']
    user = await auth_service.get_user_by_user_id(user_id=user_id,session=session)
    return user

@dataclass(kw_only=True)
class RoleChecker:
    roles:List[str]

    async def __call__(self,current_user:User = Depends(get_current_user)):
        if current_user.role not in self.roles:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={'message':'You are not allowed to access this service'})
        return True
