"""Profile, XP and leaderboard read models."""

from db import db_manager


async def get_profile(user_id: int):
    return await db_manager.get_user(user_id)


async def weekly_leaderboard(limit: int = 10):
    return await db_manager.get_weekly_leaderboard(limit)
