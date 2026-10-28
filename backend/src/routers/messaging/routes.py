from fastapi import APIRouter,WebSocket,Depends
from uuid import UUID
from dependencies.security import WebSocketTokenBearer
from sqlalchemy.ext.asyncio import AsyncSession
from db_config import get_session
from typing import Dict

router = APIRouter()

@router.websocket('/ws')
async def websocket_endpoint(websocket:WebSocket,session:AsyncSession = Depends(get_session),token_data:Dict = Depends(WebSocketTokenBearer())):
    pass

@router.get('/friend_messages/{friend_id}')
async def get_friend_messages(friend_id:UUID|str):
    pass

  