from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status
from sqlalchemy.ext.asyncio import AsyncSession
from .schema import Message, Friend, FriendRequest
from sqlalchemy import select
from routers.auth.services import UserService
from routers.auth.schema import User
from uuid import UUID

user_service = UserService()


class MessagingService:

    def __init__(self):
        self.online_users = {}

    async def connect_user(
        self, websocket: WebSocket, username: str, session: AsyncSession
    ):
        user = await user_service.get_user_by_username(
            username=username, session=session
        )
        try:
            await websocket.accept()
            self.online_users[username] = websocket
            user.online_status = True
        except WebSocketDisconnect as e:
            self.online_users.pop(username)
            user.online_status = False
        finally:
            await session.commit()
            await session.refresh(user)
        while True:
            pass

    async def send_messages(
        self, receiver_username: str, username: str, message: str, session: AsyncSession
    ):
        current_user = await user_service.get_user_by_username(
            username=username, session=session
        )
        recieving_user = await user_service.get_user_by_username(
            username=receiver_username, session=session
        )
        sending_friend = await self.get_friend_by_user_id(
            user_id=recieving_user.user_id, friend_username=username, session=session
        )
        receiving_friend = await self.get_friend_by_user_id(
            user_id=current_user.user_id,
            friend_username=receiver_username,
            session=session,
        )
        if receiving_friend is None:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Messages can only be sent to friends",
            )
        recieiver_friend_id = receiving_friend.friend_id
        sender_friend_id = sending_friend.friend_id
        if receiver_username in self.online_users:
            receivers_websocket: WebSocket = self.online_users[receiver_username]
            receivers_websocket.send_json({"sender": username, "message": message})
        await self.store_messages(
            current_user=current_user,
            receiver_username=receiver_username,
            friend_id=recieiver_friend_id,
            message_text=message,
            session=session,
        )  # Stores Message on users end
        await self.store_messages(
            current_user=recieving_user,
            receiver_username=username,
            friend_id=sender_friend_id,
            message_text=message,
            session=session,
        )  # Stores message on friends end
        # TODO Find a way to store received status on the friend part so when pulling the messages you can pull

    async def store_messages(
        self,
        current_user: User,
        receiver_username: str,
        friend_id: UUID,
        message_text: str,
        session: AsyncSession,
    ):
        new_message = Message(
            user_id=current_user.user_id,
            message_text=message_text,
            sender_username=current_user.username,
            receiver_username=receiver_username,
            friend_id=friend_id,
        )
        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)

    async def get_all_friends_messages():
        pass

    async def set_request_status():
        pass

    async def get_potential_friends():
        pass

    async def get_friend_by_user_id(
        self, user_id: UUID, friend_username: str, session: AsyncSession
    ):
        statement = select(Friend).where(
            user_id == Friend.user_id, Friend.friend_username == friend_username
        )
        result = await session.execute(statement=statement)
        friend = result.scalars().first()
        return friend
