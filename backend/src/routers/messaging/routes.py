from fastapi import APIRouter
from uuid import UUID

router = APIRouter()

@router.get('/friend_messages/{friend_id}')
async def get_friend_messages(friend_id:UUID|str):
    pass

