"""Thin Telegram Bot API transport for Quiz Battle's shared API/core."""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote

import aiohttp

from config import settings

log = logging.getLogger(__name__)
API = "https://api.telegram.org"


class TelegramBot:
    def __init__(self, token: str, mini_app_url: str) -> None:
        self.token, self.mini_app_url = token, mini_app_url.rstrip("/")

    async def call(self, method: str, **payload):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API}/bot{self.token}/{method}", json=payload, timeout=aiohttp.ClientTimeout(total=20)) as response:
                data = await response.json(content_type=None)
                if not response.ok or not data.get("ok"):
                    raise RuntimeError(f"Telegram {method} failed: {data.get('description', response.status)}")
                return data["result"]

    def app_url(self, startapp: str | None = None) -> str:
        # The app URL itself never carries trust data; Telegram sends signed initData.
        return self.mini_app_url + (f"?startapp={quote(startapp)}" if startapp else "")

    async def start(self, chat_id: int, startapp: str | None = None) -> None:
        keyboard = [[{"text": "🎮 Играть", "web_app": {"url": self.app_url(startapp)}}],
                    [{"text": "🎯 Квиз дня", "web_app": {"url": self.app_url("daily")}},
                     {"text": "⚔️ Вызвать друга", "web_app": {"url": self.app_url("challenge_new")}}],
                    [{"text": "🏆 Рейтинг", "web_app": {"url": self.app_url("leaderboard")}}]]
        await self.call("sendMessage", chat_id=chat_id,
                        text="🧠 <b>Quiz Battle</b>\n\nБыстрые квизы, ежедневные испытания\nи битвы с друзьями.",
                        parse_mode="HTML", reply_markup={"inline_keyboard": keyboard})

    async def handle_update(self, update: dict) -> None:
        message = update.get("message") or update.get("callback_query", {}).get("message")
        if not message:
            return
        text = (update.get("message") or {}).get("text", "")
        chat_id = message["chat"]["id"]
        command, _, argument = text.partition(" ")
        if command == "/start":
            await self.start(chat_id, argument or None)
        elif command in {"/play", "/daily", "/challenge", "/profile", "/leaderboard"}:
            mapping = {"/play": None, "/daily": "daily", "/challenge": "challenge_new", "/profile": "profile", "/leaderboard": "leaderboard"}
            await self.call("sendMessage", chat_id=chat_id, text="Открываю игру…", reply_markup={"inline_keyboard": [[{"text": "🎮 Открыть Quiz Battle", "web_app": {"url": self.app_url(mapping[command])}}]]})
        elif command == "/help":
            await self.call("sendMessage", chat_id=chat_id, text="/play — игра\n/daily — квиз дня\n/challenge — вызов другу\n/profile — профиль\n/leaderboard — рейтинг")


async def run_polling() -> None:
    if not settings.TELEGRAM.token or not settings.MINI_APP_URL:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and MINI_APP_URL are required")
    bot, offset = TelegramBot(settings.TELEGRAM.token, settings.MINI_APP_URL), 0
    await bot.call("setMyCommands", commands=[{"command": x, "description": y} for x, y in [
        ("start", "Открыть Quiz Battle"), ("play", "Быстрая игра"), ("daily", "Квиз дня"),
        ("challenge", "Вызвать друга"), ("profile", "Профиль"), ("leaderboard", "Рейтинг"), ("help", "Помощь")]])
    while True:
        updates = await bot.call("getUpdates", offset=offset, timeout=25, allowed_updates=["message"])
        for update in updates:
            offset = update["update_id"] + 1
            try: await bot.handle_update(update)
            except Exception: log.exception("Telegram update failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_polling())
