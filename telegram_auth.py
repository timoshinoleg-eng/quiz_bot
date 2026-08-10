"""Telegram Mini App authentication, per the official HMAC WebAppData procedure."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramIdentity:
    external_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> TelegramIdentity:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    values = dict(pairs)
    if not pairs or len(values) != len(pairs) or sum(key == "hash" for key, _ in pairs) != 1:
        raise TelegramAuthError("invalid initData")
    if not values.get("hash") or not values.get("user"):
        raise TelegramAuthError("missing initData fields")
    try:
        auth_date = int(values["auth_date"])
        user = json.loads(values["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TelegramAuthError("malformed initData") from error
    if abs(int(time.time()) - auth_date) > max_age_seconds:
        raise TelegramAuthError("expired initData")
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(pairs) if key != "hash")
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, values["hash"]):
        raise TelegramAuthError("invalid initData signature")
    return TelegramIdentity(user_id, user.get("username"), user.get("first_name"), user.get("last_name"))
