"""Register verified production webhooks without ever printing bot tokens."""
from __future__ import annotations

import argparse
import asyncio
import sys

import aiohttp
from dotenv import load_dotenv

load_dotenv()

from config import settings


def required(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


async def register_telegram(dry_run: bool) -> None:
    token = required(settings.TELEGRAM.token, "TELEGRAM_BOT_TOKEN")
    url = required(settings.TELEGRAM.webhook_url, "TELEGRAM_WEBHOOK_URL")
    secret = required(settings.TELEGRAM.webhook_secret, "TELEGRAM_WEBHOOK_SECRET")
    if not url.startswith("https://"):
        raise RuntimeError("TELEGRAM_WEBHOOK_URL must use HTTPS")
    if dry_run:
        print("Telegram webhook: READY_TO_REGISTER")
        print("Telegram Mini App menu: READY_TO_REGISTER")
        return
    webhook_payload = {"url": url, "secret_token": secret, "allowed_updates": ["message", "callback_query"]}
    menu_payload = {
        "menu_button": {
            "type": "web_app",
            "text": "Играть",
            "web_app": {"url": required(settings.MINI_APP_URL, "MINI_APP_URL")},
        }
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(f"https://api.telegram.org/bot{token}/setWebhook", json=webhook_payload) as response:
            result = await response.json(content_type=None)
        if response.status != 200 or not result.get("ok"):
            raise RuntimeError(f"Telegram setWebhook failed with HTTP {response.status}")
        async with session.post(f"https://api.telegram.org/bot{token}/setChatMenuButton", json=menu_payload) as response:
            result = await response.json(content_type=None)
        if response.status != 200 or not result.get("ok"):
            raise RuntimeError(f"Telegram setChatMenuButton failed with HTTP {response.status}")
    print("Telegram webhook: REGISTERED")
    print("Telegram Mini App menu: REGISTERED")


async def register_max(dry_run: bool) -> None:
    token = required(settings.BOT.token, "BOT_TOKEN")
    url = required(settings.BOT.webhook_url, "MAX_WEBHOOK_URL")
    secret = required(settings.BOT.webhook_secret, "MAX_WEBHOOK_SECRET")
    if not url.startswith("https://"):
        raise RuntimeError("MAX_WEBHOOK_URL must use HTTPS")
    if dry_run:
        print("MAX webhook: READY_TO_REGISTER")
        return
    payload = {"url": url, "secret": secret, "update_types": ["message_created", "message_callback", "bot_started"]}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20), headers={"Authorization": token}) as session:
        async with session.post("https://platform-api2.max.ru/subscriptions", json=payload) as response:
            result = await response.json(content_type=None)
    if response.status != 200 or result.get("success") is False:
        raise RuntimeError(f"MAX POST /subscriptions failed with HTTP {response.status}")
    print("MAX webhook: REGISTERED")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("telegram", "max", "all"), default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.platform in {"telegram", "all"}:
        await register_telegram(args.dry_run)
    if args.platform in {"max", "all"}:
        await register_max(args.dry_run)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as error:
        print(f"Webhook registration: FAILED ({error})", file=sys.stderr)
        raise SystemExit(1) from error
