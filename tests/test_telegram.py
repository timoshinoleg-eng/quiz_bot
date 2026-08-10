from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

import db
from config import settings
from models import PlatformIdentity
from telegram_auth import TelegramAuthError, validate_init_data


@pytest.fixture
async def database(tmp_path):
    from dataclasses import replace
    await db.close_db()
    settings.DATABASE = replace(settings.DATABASE, url=f"sqlite+aiosqlite:///{tmp_path / 'telegram.sqlite3'}")
    await db.init_db()
    yield
    await db.close_db()


def signed_init_data(token: str = "telegram-test-token", user_id: int = 4242, auth_date: int | None = None) -> str:
    values = {"auth_date": str(auth_date or int(time.time())), "query_id": "q", "user": json.dumps({"id": user_id, "first_name": "Тест"}, separators=(",", ":"))}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_telegram_init_data_valid_invalid_old_and_forged_identity():
    raw = signed_init_data()
    assert validate_init_data(raw, "telegram-test-token").external_user_id == 4242
    with pytest.raises(TelegramAuthError): validate_init_data(raw.replace("4242", "9001"), "telegram-test-token")
    with pytest.raises(TelegramAuthError): validate_init_data(signed_init_data(auth_date=int(time.time()) - 7200), "telegram-test-token")


@pytest.mark.asyncio
async def test_telegram_identity_does_not_collide_with_max(database):
    max_user = await db.db_manager.get_or_create_platform_user("max", 4242, first_name="MAX")
    telegram_user = await db.db_manager.get_or_create_platform_user("telegram", 4242, first_name="TG")
    assert max_user.id == 4242 and telegram_user.id < 0 and telegram_user.id != max_user.id
    async with db.get_db() as session:
        identities = list((await session.execute(__import__('sqlalchemy').select(PlatformIdentity))).scalars())
    assert {(item.platform, item.external_user_id) for item in identities} == {("max", "4242"), ("telegram", "4242")}
