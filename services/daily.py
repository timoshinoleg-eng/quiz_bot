"""Daily Challenge application service."""

from datetime import date
from typing import Any, Dict, Optional

from db import DailyAlreadyPlayed, db_manager


async def start_daily(user_id: int, challenge_date: Optional[date] = None):
    return await db_manager.create_daily_game(user_id, challenge_date)


async def status(user_id: int, challenge_date: Optional[date] = None) -> Dict[str, Any]:
    return await db_manager.get_daily_status(user_id, challenge_date)


__all__ = ["DailyAlreadyPlayed", "start_daily", "status"]
