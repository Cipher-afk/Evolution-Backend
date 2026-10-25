import email

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .services import TaskService
from typing import Dict
from dependencies.security import AccessTokenBearer
from db_config import get_session
from uuid import UUID

router = APIRouter()
task_service = TaskService()

@router.get('/generate_progression_path')
async def generate_progression_path(token_data:Dict = Depends(AccessTokenBearer()),session:AsyncSession = Depends(get_session)):
    user_id = token_data['user']['user_id']
    progression_path = await task_service.generate_progression_path(user_id=user_id,session=session)
    return progression_path

@router.get("/generate_daily_task")
async def generate_task_for_today(
    token_data: Dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_id = token_data["user"]["user_id"]
    daily_tasks = await task_service.generate_daily_task(
        user_id=user_id, session=session
    )
    return daily_tasks


@router.get("/get_weekly_challenge/{task_id}")
async def get_weekly_challenge(
    task_id: UUID,
    token_data: Dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    weekly_challenge = await task_service.get_weekly_challenge(
        task_id=task_id, session=session
    )
    return weekly_challenge


@router.get("/complete_task/{task_id}", dependencies=[Depends(AccessTokenBearer())])
async def complete_task(task_id: UUID, session: AsyncSession = Depends(get_session)):
    daily_task = await task_service.get_task_by_id(task_id=task_id, session=session)
    xp_gained = (
        daily_task.xp_awarded
    )  # For now there's no proof so you just get your points
    task_info = await task_service.update_xp_gained(
        task_id=task_id, xp_gained=xp_gained, session=session
    )
    return task_info


@router.get(
    "/complete_weekly_challenge/{task_id}"
)
async def complete_challenge(
    task_id: UUID, session: AsyncSession = Depends(get_session),token_data:Dict = Depends(AccessTokenBearer())
):
    email = token_data["user"]["email"]
    weekly_challenge = await task_service.get_weekly_challenge(email=email,
        task_id=task_id, session=session
    )
    xp_gained = weekly_challenge.xp_awarded
    weekly_task_id = weekly_challenge.weekly_task_id
    challenge_info = await task_service.update_challenge_xp_gained(
        weekly_task_id=weekly_task_id, xp_gained=xp_gained, session=session
    )
    return challenge_info

@router.get("/get_users_task")
async def get_users_task(
    token_data: Dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_id = token_data["user"]["user_id"]
    daily_tasks = await task_service.get_tasks_by_user_id(
        user_id=user_id, session=session
    )
    return daily_tasks 

@router.post("/send_proof")
async def send_proof_of_completion():
    pass
