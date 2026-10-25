from .models import GoalDescriptionModel, ListingGoalsModel,SimilarGoalsModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,asc
from .schema import Goals, Niche
from sqlalchemy.orm import selectinload
from uuid import UUID
import uuid
from routers.auth.services import UserService
from routers.auth.schema import User
from fastapi import HTTPException
from fastapi import Request

user_service = UserService()

class GoalService:
    async def store_niche(self,user_id:str, niche_name: str, session: AsyncSession):
        user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        existing_niche = await self.get_niche_by_name(niche_name=niche_name, session=session)
        if existing_niche is None:
            new_niche = Niche()
            new_niche.niche_name = niche_name
            new_niche.user_id = user_id
            session.add(new_niche)
            await session.commit()
            await session.refresh(new_niche)
            return new_niche
        else:
            return existing_niche

    async def store_goal_description(
        self, user_id: str, goals_info: GoalDescriptionModel, session: AsyncSession,request:Request
    ):
        user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        user = await user_service.get_user_by_user_id(user_id=user_id,session=session)
        niche_name = goals_info.niche
        # goal_description_data = goals_info.model_dump()
        new_niche = await self.store_niche(user_id=user_id, niche_name=niche_name, session=session)
        user.niche_id = new_niche.niche_id
        niche_invitation_link = request.url_for('signup_route',referral_niche_id=new_niche.niche_id)
        user.niche_invitation_link = niche_invitation_link
        new_goals = Goals(user_id=user_id,goal_name=goals_info.goal_name, goal_description=goals_info.goal_description, duration=goals_info.duration, niche_id=new_niche.niche_id)
        new_goals.user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        session.add(new_goals)
        await session.commit()
        await session.refresh(new_goals)
        user.goal_id = new_goals.goal_id
        await session.commit()
        return new_goals



    async def get_all_niche(self, session: AsyncSession):
        statement = select(Niche).options(
            selectinload(goal.goal_name for goal in Niche.goals)
        )
        results = await session.execute(statement=statement)
        niches = results.scalars().all()
        return niches

    async def get_goals_related_to_niche(self, niche_id: str, session: AsyncSession):
        statement = select(Goals).where(Goals.niche_id == niche_id)
        results = await session.execute(statement=statement)
        goals = results.scalars().all()
        return (ListingGoalsModel.model_validate(goal) for goal in goals)

    async def get_goal_by_user_id(self, user_id: UUID, session: AsyncSession):
        statement = select(Goals).where(Goals.user_id == user_id)
        result = await session.execute(statement=statement)
        goal = result.scalars().first()
        return goal

    async def get_niche_by_name(self,niche_name:str,session:AsyncSession):
        statement = select(Niche).where(Niche.niche_name == niche_name)
        result = await session.execute(statement=statement)
        niche = result.scalars().first()
        return niche

    async def get_niche_by_niche_id(self,niche_id:UUID,session:AsyncSession):
        statement = select(Niche).where(Niche.niche_id == niche_id)
        result = await session.execute(statement=statement)
        niche = result.scalars().first()
        return niche

    async def get_user_by_niche_id(self,niche_id:UUID,session:AsyncSession):
        statement = select(User).where(niche_id == User.niche_id).order_by(asc(User.lifetime_xp))
        results = await session.execute(statement=statement)
        users = results.scalars().all()
        return users
        
    
    async def get_users_related_by_niche(self,niche_name:str,session:AsyncSession):
        niche_table = await self.get_niche_by_name(niche_name=niche_name,session=session)
        if niche_table is None:
            raise HTTPException(status_code=403,detail={'message':'Niche not available'})
        niche_id = niche_table.niche_id
        users = await self.get_user_by_niche_id(niche_id=niche_id,session=session)
        return users

    async def get_users_with_similar_goals(self,goal_name:str,session:AsyncSession):
        statement = select(Goals).where(goal_name == Goals.goal_name)
        results = await session.execute(statement=statement)
        similar_goals = results.scalars().all()
        return SimilarGoalsModel.model_validate(similar_goals)

    async def get_leaderboard_based_on_niche(self,user_id:str|UUID,session:AsyncSession):
        user = await user_service.get_user_by_user_id(user_id=user_id,session=session)
        niche_id = user.niche_id
        users = await self.get_user_by_niche_id(niche_id=niche_id,session=session)
        return users

    async def get_niche_link(self,user_id:str|UUID,session:AsyncSession):
        user = await user_service.get_user_by_user_id(user_id=user_id,session=session)
        niche_link = user.niche_invitation_link
        return{'niche_invitation_link':niche_link}






        