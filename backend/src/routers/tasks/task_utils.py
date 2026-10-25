from enum import Enum
from .schema import Difficulty
from math import ceil
from .prompts import PATH_GEN_PROMPT, TASK_GEN_PROMPT
from utils import get_total_daily_xp
from typing import Dict, List, TypedDict
from groq import AsyncGroq, APIStatusError, RateLimitError
from fastapi import HTTPException,status
import asyncio
import json
from config import settings
from redis.asyncio import Redis
from dataclasses import dataclass
import json
import re
from .schema import Difficulty

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


class DailyTaskDict(TypedDict):
    regular_tasks: List["TaskInfoDict"]
    bonus_task: "TaskInfoDict"
    weekly_challenge: "WeeklyChallengeDict"


class TaskInfoDict(TypedDict):
    title: str
    description: str
    difficulty: str


class WeeklyChallengeDict(TaskInfoDict):
    success_criteria: List[str]


class ProgressionLevel(TypedDict):
    level: int
    title: str
    main_focus: str
    description: str
    skills: List[str]
    knowledge: List[str]
    practical_abilities: List[str]
    completion_criteria: List[str]
    progression_areas: List[str]


@dataclass(kw_only=True)
class GroqRateLimiter:
    redis_client: Redis
    max_per_minute: int = 25
    max_per_day: int = 900
    minute_key: str = "groq:rl:minute"
    day_key: str = "groq:rl:day"

    async def acquire(self) -> tuple[bool, str]:
        minute_count = await self.redis_client.get(self.minute_key)
        daily_count = await self.redis_client.get(self.day_key)
        minute_count = int(minute_count) if minute_count else 0
        daily_count = int(daily_count) if daily_count else 0
        if minute_count > self.max_per_minute:
            return (False, "minute")
        if daily_count > self.max_per_day:
            return (False, "daily")
        pipe = self.redis_client.pipeline()
        pipe.incr(self.minute_key)
        pipe.expire(self.minute_key, 60, nx=True)
        pipe.incr(self.day_key)
        pipe.expire(self.day_key, 86400, nx=True)
        await pipe.execute()
        return (True, "")

    async def seconds_until_minute(self) -> int:
        ttl = await self.redis_client.ttl(self.minute_key)
        return max(ttl, 1)


class Weights(int, Enum):
    EASY = 2
    MEDIUM = 3
    HARD = 4
    EXTREME = 5


async def calculate_xp_awarded(difficulty: Difficulty, level_up_xp: int):
    total_daily_xp = await get_total_daily_xp(level_up_xp=level_up_xp)
    edited_difficulty_argument = difficulty.lower()
    weight = 0
    if edited_difficulty_argument == Difficulty.EASY.lower():
        weight = Weights.EASY
    elif edited_difficulty_argument == Difficulty.MEDIUM.lower():
        weight = Weights.MEDIUM
    elif edited_difficulty_argument == Difficulty.HARD.lower():
        weight = Weights.HARD
    else:
        weight = Weights.EXTREME
    xp_awarded = ceil(
        total_daily_xp * (weight / 14)
    )  # 14 signifies the amount of days needed to level up
    return xp_awarded


async def edit_path_gen_prompt(goal: str, goal_description: str, current_ability: str):
    edited_prompt = (
        PATH_GEN_PROMPT.replace("{{goal}}", goal)
        .replace("{{goal_description}}", goal_description)
        .replace("{{current_ability}}", current_ability)
    )
    prompt = [{"role": "user", "content": edited_prompt}]
    return prompt


async def edit_task_gen_prompt(
    goal: str,
    start_date: str,
    today: str,
    current_level: int,
    current_level_path: Dict,
    previous_focus: str,
    previous_task_results: Dict,
    weekly_challenge: Dict,
):
    edited_prompt = (
        TASK_GEN_PROMPT.replace("{{goal}}", goal)
        .replace("{{start_date}}", str(start_date))
        .replace("{{today}}", str(today))
        .replace("{{current_level}}", str(current_level))
        .replace("{{current_level_path}}", str(current_level_path))
        .replace("{{previous_focus}}", str(previous_focus))
        .replace("{{previous_day_tasks}}", str(previous_task_results))
        .replace("{{weekly_challenge}}", str(weekly_challenge))
    )
    prompt = [{"role": "user", "content": edited_prompt}]
    return prompt


async def call_groq_with_retry(prompt: List[Dict], max_tries: int = 3):
    for attempt in range(max_tries):
        try:
            response = await groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=prompt,
                temperature=0.3,
                max_tokens=4096,
                response_format={'type':'json_object'}
            )
            choice = response.choices[0]
            if choice.finish_reason == "length":
                raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED,detail={'message':'Max tokens exhausted shorten prompt or raise max_tokens'})
            response_text = choice.message.content.strip()
            response_text = re.sub(r"^```(?:json)?\s*|\s*```$","",response_text)
            # if response_text.startswith("```"):
            #     response_text = response.strip("`")
            #     response_text = response.replace("json", "", 1)
            response_data = json.loads(response_text)
            return response_data
        except RateLimitError as e:
            wait_time = 5 * (attempt + 1)
            if attempt < (max_tries - 1):
                await asyncio.sleep(wait_time)
                continue
            raise

        except APIStatusError as e:
            if attempt < (max_tries - 1):
                await asyncio.sleep(3)
                continue
            raise


async def get_daily_tasks(groq_response: Dict):
    regular_tasks: List[TaskInfoDict] = groq_response["tasks"]
    bonus_task = groq_response["bonus_task"]
    weekly_challenge = groq_response["weekly_challenge"]
    response_data: DailyTaskDict = {
        "regular_tasks": regular_tasks,
        "bonus_task": bonus_task,
        "weekly_challenge": weekly_challenge,
    }
    return response_data


async def get_path_data(groq_response: Dict):
    levels: List[ProgressionLevel] = groq_response["levels"]
    return levels
