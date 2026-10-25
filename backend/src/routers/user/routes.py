from fastapi import APIRouter,Depends
from dependencies.security import AccessTokenBearer,get_current_user,RoleChecker
from routers.auth.schema import User
from routers.auth.services import UserService
from routers.goals.service import GoalService
from sqlalchemy.ext.asyncio import AsyncSession
from db_config import get_session
from typing import Dict

router = APIRouter()
user_service = UserService()
goal_service = GoalService()
role_checker = RoleChecker(roles=['admin'])

@router.get('/me')
async def get_current_user(current_user:User = Depends(get_current_user)):
    return current_user

@router.get('/all_users',dependencies=[Depends(role_checker)])
async def get_all_users(session:AsyncSession = Depends(get_session)):
    all_users = await user_service.get_all_users(session=session)
    return all_users

@router.get('/related_by_niche/{niche_name}',dependencies=[Depends(AccessTokenBearer())])
async def get_users_related_by_niche(niche_name:str,session:AsyncSession = Depends(get_session)):
    related_niche_users = await goal_service.get_users_related_by_niche(niche_name=niche_name,session=session)
    return related_niche_users

@router.get('/leaderboard')
async def get_leaderboard(token_data:Dict = Depends(AccessTokenBearer()),session:AsyncSession = Depends(get_session)):
    user_id = token_data['user']['user_id']
    leaderboard = await goal_service.get_leaderboard_based_on_niche(user_id=user_id,session=session)
    return leaderboard

@router.get('/top_niche_users')
async def get_top_users_in_niche(token_data:Dict = Depends(AccessTokenBearer()),session:AsyncSession = Depends(get_session)):
    user_id = token_data['user']['user_id']
    leaderboard = await goal_service.get_leaderboard_based_on_niche(user_id=user_id,session=session)
    top_3_users = leaderboard[:4] if len(leaderboard) > 3 else leaderboard
    return top_3_users

@router.get('/niche_invitation_link')
async def get_invitation_link_for_niche(token_data:Dict = Depends(AccessTokenBearer()),session:AsyncSession = Depends(get_session)):
    user_id = token_data['user']['user_id']
    niche_invitation_link = await goal_service.get_niche_link(user_id=user_id,session=session)
    return niche_invitation_link