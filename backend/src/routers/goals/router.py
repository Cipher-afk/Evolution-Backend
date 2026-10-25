from fastapi import APIRouter, Depends
from .models import GoalDescriptionModel,NicheResponseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db_config import get_session
from .service import GoalService
from dependencies.security import AccessTokenBearer,RoleChecker
from typing import Dict
from uuid import UUID
from fastapi.responses import JSONResponse

router = APIRouter()
service = GoalService()
role_checker = RoleChecker(roles=['admin'])

@router.post("/add_goals")
async def add_goals(
    goals_info: GoalDescriptionModel,
    token_data: Dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_id = token_data['user']["user_id"]
    new_goals = await service.store_goal_description(
        user_id=user_id, goals_info=goals_info, session=session
    )
    return new_goals


@router.get("/all_niches", dependencies=[Depends(role_checker)])
async def get_all_niches(session: AsyncSession = Depends(get_session)):
    niches = await service.get_all_niche(session=session)
    return niches


@router.get("/niche_goals", dependencies=[Depends(AccessTokenBearer())])
async def get_goals_related_to_niche(
    niche_id: UUID, session: AsyncSession = Depends(get_session)
):
    niche_goals = await service.get_goals_related_to_niche(
        niche_id=niche_id, session=session
    )
    return list(niche_goals)

@router.get('/niche/{niche_id}',response_model=NicheResponseModel)
async def get_niche_by_niche_id(niche_id:str|UUID,session:AsyncSession = Depends(get_session)):
    niche = await service.get_niche_by_niche_id(niche_id=niche_id,session=session)
    return niche
