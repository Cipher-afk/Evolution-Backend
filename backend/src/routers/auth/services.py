from sqlalchemy.ext.asyncio import AsyncSession
from .models import (
    SignUpModel,
    LoginModel,
    GoalDescriptionModel,
    UpdateUserModel,
)
from sqlalchemy import asc

from .schema import User
from sqlalchemy import select
from utils import hash_password, verify_password_hash
from fastapi.exceptions import HTTPException
import asyncio
from uuid import UUID



class UserService:
    async def create_user(self, signup_info: SignUpModel, session: AsyncSession):
        signup_data = signup_info.model_dump()
        new_user = User(**signup_data)
        new_user.password_hash = await asyncio.to_thread(
            hash_password, password=signup_data["password"]
        )
        session.add(new_user)
        await session.commit()
        return new_user

    async def sign_in(self, login_info: LoginModel, session: AsyncSession):
        email = login_info.email
        password = login_info.password
        user = await self.get_user_by_email(email=email, session=session)
        if user is None:
            raise HTTPException(status_code=404, detail={"message": "user not found"})
        password_hash = user.password_hash
        verified = verify_password_hash(password=password, password_hash=password_hash)
        if not verified:
            raise HTTPException(
                status_code=403, detail={"message": "password is incorrect"}
            )
        return user

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        user = result.scalars().first()
        return user

    async def get_user_by_user_id(self, user_id, session: AsyncSession):
        statement = select(User).where(User.user_id == user_id)
        result = await session.execute(statement)
        user = result.scalars().first()
        return user

    async def update_user_info(
        self, update_info: UpdateUserModel, session: AsyncSession
    ):
        updated_message = {"updated": None}
        try:
            email = update_info.email
            info = update_info.info
            user = await self.get_user_by_email(email=email, session=session)
            if user is None:
                raise HTTPException(
                    status_code=404, detail={"message": "user not found"}
                )
            for key, value in info.items():
                setattr(user, key, value)
            await session.commit()
            updated_message["updated"] = True
            return updated_message
        except Exception as e:
            await session.rollback()
            updated_message["updated"] = False
            return updated_message

    async def level_user_up(self, email: UUID, session: AsyncSession):
        user = await self.get_user_by_email(email=email, session=session)
        if user.lifetime_xp > user.level_up_xp:
            new_level = user.current_level + 1
            new_level_up_xp = user.level_up_xp + 200
            update_info = UpdateUserModel(
                email=email,
                info={"current_level": new_level, "level_up_xp": new_level_up_xp},
            )
            await self.update_user_info(update_info=update_info, session=session)
            return {"leveled_up": True}
        return {"leveled_up": False}

    async def get_all_users(self,session:AsyncSession):
        statement = select(User).order_by(asc(User.lifetime_xp))
        results = await session.execute(statement=statement)
        users = results.scalars().all()
        return users



    


