from requests import session

from .task_utils import (
    call_groq_with_retry,
    TaskInfoDict,
    edit_path_gen_prompt,
    edit_task_gen_prompt,
    get_daily_tasks,
    DailyTaskDict,
    calculate_xp_awarded,
    get_path_data,
)
from pprint import pprint
from typing import Dict
from datetime import datetime, timezone, timedelta
from .schema import DailyTask, WeeklyChallenge, ProgressionPath, TaskStatus
from uuid import UUID
from typing import List
from routers.auth.services import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from routers.goals.service import GoalService
import uuid
from .models import PreviousDayTaskModel, CurrentLevelPathModel, WeeklyChallengeModel,TaskModel
from routers.auth.models import UpdateUserModel

auth_service = UserService()
goal_service = GoalService()


class TaskService:
    async def generate_daily_task(
        self,
        user_id: UUID,
        session: AsyncSession,
    ) -> JSONResponse:
        today = datetime.now(timezone.utc)
        user = await auth_service.get_user_by_user_id(user_id=user_id, session=session)
        if user is None:
            raise HTTPException(status_code=404, detail={"message": "user not found"})
        goal_info = await goal_service.get_goal_by_user_id(
            user_id=user_id, session=session
        )
        ##This part gets all the neccessary info needed for the prompt
        goal = goal_info.goal_name
        start_date = user.date_joined
        current_level = user.current_level
        current_level_path_info = await self.get_current_level_path(
            current_level=current_level, session=session
        )
        current_level_path = current_level_path_info.model_dump() if current_level_path_info is not None else None
        previous_focus = current_level_path_info.main_focus if current_level_path_info is not None else None
        previous_task_results_info = await self.get_previous_day_tasks(
            user_id=user_id, session=session
        )
        previous_day = (
            previous_task_results_info[0].day if previous_task_results_info is not None else None
        )
        ## This block of code checks for a new week based on the subtraction of total number of days - current day
        if (previous_day is not None) and (7 - previous_day > 0):
            weekly_task_id = previous_task_results_info[
                0
            ].weekly_task_id  # Assigns the previous task id if the day is in the same week
        else:
            weekly_task_id = None
        ## If the result of the subtraction of the 7 - previous day is 0 or lower then it's a new week and a new weekly id should be none else it should use the previous days id
        previous_task_results = (
            [
                previous_task_result.model_dump()
                for previous_task_result in previous_task_results_info
            ]
            if previous_task_results_info
            else None
        )  # Gets the task results if there are any
        task_id = previous_task_results_info[0].task_id if previous_task_results_info else None
        weekly_challenge = (
            await self.get_weekly_challenge(task_id=task_id, session=session)
            if weekly_task_id != None
            else None
        )
        dumped_weekly_challenge = WeeklyChallengeModel.model_validate(
            weekly_challenge
        ).model_dump() if weekly_task_id is not None else None
        prompt = await edit_task_gen_prompt(
            goal=goal,
            start_date=start_date,
            today=today,
            current_level=current_level,
            current_level_path=current_level_path,
            previous_focus=previous_focus,
            previous_task_results=previous_task_results,
            weekly_challenge=dumped_weekly_challenge,
        )
        task_response = await call_groq_with_retry(prompt=prompt)
        task_data: DailyTaskDict = await get_daily_tasks(groq_response=task_response)
        daily_tasks = await self.store_daily_tasks(
            user_id=user_id,
            task_data=task_data,
            previous_day=previous_day,
            session=session,
            weekly_task_id=weekly_task_id,
        )
        weekly_task_id = daily_tasks[0]["weekly_task_id"]
        weekly_challenge = await self.store_weekly_challenge(
            user_id=user_id,
            weekly_task_id=weekly_task_id,
            task_id=daily_tasks[0]["task_id"],
            task_data=task_data,
            session=session,
        )
        return JSONResponse(
            content={"daily_tasks": daily_tasks, "weekly_challenge": weekly_challenge}
        )

    async def store_daily_tasks(
        self,
        user_id: UUID,
        previous_day: int | None,
        task_data: DailyTaskDict,
        session: AsyncSession, 
        weekly_task_id: UUID = None,
    ):
        weekly_task_id = uuid.uuid4() if weekly_task_id is None else weekly_task_id
        stored_tasks: List[DailyTask] = []
        regular_tasks: List[TaskInfoDict] = task_data["regular_tasks"]
        user = await auth_service.get_user_by_user_id(user_id=user_id, session=session)
        for task in regular_tasks:
            daily_task = DailyTask(goal_id=user.goal_id, user_id=user_id)
            title, difficulty, description = (
                task["title"],
                task["difficulty"],  # Converts the difficulty to lower case to match the enum
                task["description"],
            )
            print(f'Difficulty: {difficulty}')
            daily_task.task = title
            daily_task.difficulty = difficulty# Converts the difficulty to lower case to match the enum
            print(f'Difficulty after conversion: {daily_task.difficulty}')
            if (previous_day is not None) and (
                previous_day <= 7
            ):  # This resets the day back to 1 if the previous day is > 7 or none
                daily_task.day = previous_day + 1
            else:
                daily_task.day = 1
            daily_task.weekly_task_id = weekly_task_id
            daily_task.task_description = description
            xp_awarded = await calculate_xp_awarded(
                difficulty=difficulty, level_up_xp=user.level_up_xp
            )
            daily_task.xp_awarded = xp_awarded
            session.add(daily_task)
            stored_tasks.append(daily_task.model_dump(mode='json'))
        await session.commit()
        return stored_tasks

    async def store_weekly_challenge(
        self,
        user_id: UUID,
        task_id: UUID,
        weekly_task_id: UUID,
        task_data: DailyTaskDict,
        session: AsyncSession,
    ):
        goal = await goal_service.get_goal_by_user_id(user_id=user_id, session=session)
        weekly_challenge_data = task_data["weekly_challenge"]
        weekly_challenge = WeeklyChallenge(user_id=user_id, goal_id=goal.goal_id)
        weekly_challenge.challenge = weekly_challenge_data["title"]
        weekly_challenge.challenge_description = weekly_challenge_data["description"]
        weekly_challenge.weekly_task_id = weekly_task_id
        weekly_challenge.xp_awarded = 0 
        weekly_challenge.task_id = task_id
        session.add(weekly_challenge)
        await session.commit()
        return weekly_challenge.model_dump(mode='json')

    async def get_task_by_id(self, task_id: UUID, session: AsyncSession):
        statement = select(DailyTask).where(DailyTask.task_id == task_id)
        result = await session.execute(statement)
        daily_task = result.scalars().first() 
        return daily_task

    async def get_tasks_by_user_id(self, user_id: UUID, session: AsyncSession):
        statement = select(DailyTask).where(DailyTask.user_id == user_id)
        result = await session.execute(statement)
        daily_tasks = result.scalars().all()
        return daily_tasks

    async def update_task_info(
        self, daily_task: DailyTask, info: Dict, session: AsyncSession
    ):
        try:
            for k, v in info.items():
                setattr(daily_task, k, v)
            await session.commit()
            await session.refresh(daily_task)
            return {"updated": True}
        except Exception as e:
            raise HTTPException(
                status_code=403,
                detail={"message": f"Failed to update task xp because of {e}"},
            )

    async def update_xp_gained(
        self, email: str, task_id: UUID, xp_gained: int, session: AsyncSession
    ):
        daily_task = await self.get_task_by_id(task_id=task_id, session=session)
        if daily_task is None:
            raise HTTPException(status_code=404, detail={"message": "task not found"})
        info = {"xp_gained": xp_gained, "task_status": TaskStatus.COMPLETED}
        await self.update_task_info(daily_task=daily_task, info=info, session=session)
        user = await auth_service.get_user_by_email(email=email, session=session)
        weekly_xp = user.weekly_xp + xp_gained
        update_info = UpdateUserModel(email=email, info={"weekly_xp": weekly_xp})
        await auth_service.update_user_info(update_info=update_info)
        return {"completed": True}

    async def generate_progression_path(self, user_id: UUID, session: AsyncSession):
        goal = await goal_service.get_goal_by_user_id(user_id=user_id, session=session)
        prompt = edit_path_gen_prompt(
            goal=goal.goal_name,
            goal_description=goal.goal_description,
            current_ability="beginner",
        )
        response_data = await call_groq_with_retry(prompt=prompt)
        all_paths = await self.store_progression_path(
            user_id=goal.user_id, response_data=response_data, session=session
        )
        return all_paths

    async def store_progression_path(
        self, user_id: UUID, response_data: Dict, session: AsyncSession
    ):
        all_paths = []
        path_data = await get_path_data(groq_response=response_data)
        for path in path_data:
            new_path = ProgressionPath()
            new_path.level = path["level"]
            new_path.title = path["title"]
            new_path.user_id = user_id
            new_path.main_focus = path["main_focus"]
            new_path.description = path["description"]
            new_path.skills = path["skills"]
            new_path.knowledge = path["knowledge"]
            new_path.practical_abilities = path["practical_abilities"]
            new_path.completion_criteria = path["completion_criteria"]
            path.progression_areas = path["progression_areas"]
            session.add(new_path)
            all_paths.append(new_path)
        await session.commit()
        return all_paths

    async def get_current_level_path(self, current_level: int, session: AsyncSession):
        statement = select(ProgressionPath).where(
            ProgressionPath.level == current_level
        )
        result = await session.execute(statement=statement)
        current_level_path = result.scalars().first()
        return CurrentLevelPathModel.model_validate(current_level_path) if current_level_path is not None else None

    async def get_weekly_challenge(self, task_id: UUID, session: AsyncSession):
        task = await self.get_task_by_id(task_id=task_id, session=session)
        weekly_task_id = task.weekly_task_id
        statement = select(WeeklyChallenge).where(
            WeeklyChallenge.weekly_task_id == weekly_task_id
        )
        result = await session.execute(statement=statement)
        weekly_challenge = result.scalars().first()
        return weekly_challenge

    async def get_previous_day_tasks(self, user_id: UUID, session: AsyncSession):
        previous_day = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        statement = select(DailyTask).where(
            DailyTask.created_at == previous_day, DailyTask.user_id == user_id
        )  # This statement gets a taks from the prevvious day based on the date
        results = await session.execute(statement=statement)
        previous_tasks = results.scalars().all()
        # Validates the task to make sure they match the PreviousDayTaskModel which cinsists of this
        """
        weekly_task_id: UUID
        task_id: UUID
        day: int
        task: str
        task_description: str
        difficulty: Difficulty
        xp_awarded: int
        xp_gained: int
        task_status: TaskStatus
        """
        return (
            [PreviousDayTaskModel.model_validate(task) for task in previous_tasks]
            if previous_tasks
            else None
        )

    async def update_challenge_info(
        self, weekly_challenge: WeeklyChallenge, info: Dict
    ):
        try:
            for key, value in info.items():
                setattr(weekly_challenge, key, value)
            await session.commit()
            return {"updated": True, "error": None}
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=403, detail={"message": f"Failed to update because of {e}"}
            )

    async def update_challenge_xp_gained(
        self, email: str, xp_gained: int, weekly_task_id: UUID, session: AsyncSession
    ):
        user = await auth_service.get_user_by_email(email=email, session=session)
        weekly_challenge = await self.get_weekly_challenge(
            weekly_task_id=weekly_task_id, session=session
        )
        if weekly_challenge is None:
            raise HTTPException(
                status_code=404, detail={"message": "challenge not found"}
            )
        updated_info = await self.update_challenge_info(
            weekly_challenge=weekly_challenge,
            info={"xp_gained": xp_gained, "task_status": TaskStatus.COMPLETED},
        )
        weekly_xp = user.weekly_xp + xp_gained
        update_info = UpdateUserModel(
            email=email, info={"weekly_xp": 0, "lifetime_xp": weekly_xp}
        )
        await auth_service.update_user_info(update_info=update_info, session=session)
        if updated_info["updated"]:
            return {"completed": True}

    async def validate_proof():
        pass



