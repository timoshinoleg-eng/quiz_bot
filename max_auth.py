"""MAX Mini App authentication; never trust initDataUnsafe or client user ids."""
from __future__ import annotations
import hashlib, hmac, json, time
from dataclasses import dataclass
from urllib.parse import parse_qsl

class MaxAuthError(ValueError): pass
@dataclass(frozen=True)
class MaxIdentity:
    user_id: int; username: str | None; first_name: str | None; last_name: str | None

def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> MaxIdentity:
    """Validate WebAppData using MAX's documented two-stage HMAC."""
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if not pairs or sum(key == "hash" for key, _ in pairs) != 1: raise MaxAuthError("invalid initData")
    values = dict(pairs)
    if len(values) != len(pairs) or not values.get("hash") or not values.get("user"): raise MaxAuthError("duplicate or missing initData fields")
    try:
        auth_date, user = int(values["auth_date"]), json.loads(values["user"]); user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error: raise MaxAuthError("malformed initData") from error
    if abs(int(time.time()) - auth_date) > max_age_seconds: raise MaxAuthError("expired initData")
    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(pairs) if key != "hash")
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, values["hash"]): raise MaxAuthError("invalid initData signature")
    return MaxIdentity(user_id, user.get("username"), user.get("first_name"), user.get("last_name"))
