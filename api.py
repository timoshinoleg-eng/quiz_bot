"""FastAPI boundary for the Mini App; game rules stay in db_manager."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, time
from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from config import settings
from db import db_manager, get_db, init_db
from max_auth import MaxAuthError, MaxIdentity, validate_init_data
from telegram_auth import TelegramAuthError, TelegramIdentity, validate_init_data as validate_telegram_init_data
from models import Question, QuizPack, UserQuestionHistory

app = FastAPI(title="Quiz Battle API", version="2.1")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Development-User"])
class AuthPayload(BaseModel): init_data: str = Field(min_length=12)
class NewGame(BaseModel):
    pack_slug: str | None = None; category: str = "general"; difficulty: str = "medium"; question_count: int = Field(default=5, ge=5, le=20)
class Answer(BaseModel): position: int = Field(ge=0); selected_index: int = Field(ge=0, le=3)
def _session_key() -> bytes: return (os.getenv("APP_SESSION_SECRET") or settings.BOT.token).encode()
def _issue_session(user_id: int) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"uid":user_id,"exp":int(time.time())+3600}, separators=(",", ":")).encode()).decode().rstrip("=")
    return body + "." + hmac.new(_session_key(), body.encode(), hashlib.sha256).hexdigest()
def _read_session(token: str) -> int:
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, hmac.new(_session_key(), body.encode(), hashlib.sha256).hexdigest()): raise ValueError
        value = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(value["exp"]) < time.time(): raise ValueError
        return int(value["uid"])
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError): raise HTTPException(401, "Invalid session")
async def current_user(authorization: Annotated[str|None, Header()] = None, development_user: Annotated[str|None, Header(alias="X-Development-User")] = None) -> int:
    if settings.ENV == "development" and development_user:
        try: return int(development_user)
        except ValueError: raise HTTPException(401, "Invalid development user")
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    return _read_session(authorization[7:])
def public_game(game, rows) -> dict:
    current = next((row for row in rows if row.position == game.current_question_index), None)
    return {"id":game.id,"mode":game.mode,"status":game.status,"score":game.score,"correct_answers":game.correct_answers,"question_count":game.question_count,"current_question":None if not current else {"position":current.position,"text":current.question.text,"options":current.answer_options,"timeout_seconds":settings.GAME.answer_timeout}}
@app.on_event("startup")
async def startup(): await init_db()
@app.get("/health")
async def health(): return {"status":"ok", "service":"quiz-battle-api"}
@app.post("/api/v1/auth/max")
async def auth_max(payload: AuthPayload):
    try: identity = validate_init_data(payload.init_data, settings.BOT.token)
    except MaxAuthError as error: raise HTTPException(401, str(error))
    user = await db_manager.get_or_create_platform_user("max", identity.user_id, identity.username, identity.first_name, identity.last_name)
    return {"access_token":_issue_session(user.id), "token_type":"bearer", "expires_in":3600}
@app.post("/api/v1/auth/telegram")
async def auth_telegram(payload: AuthPayload):
    if not settings.TELEGRAM.token:
        raise HTTPException(503, "Telegram is not configured")
    try: identity = validate_telegram_init_data(payload.init_data, settings.TELEGRAM.token)
    except TelegramAuthError as error: raise HTTPException(401, str(error))
    user = await db_manager.get_or_create_platform_user("telegram", identity.external_user_id, identity.username, identity.first_name, identity.last_name)
    await db_manager.log_event("app_open", user.id, {"platform": "telegram"})
    return {"access_token":_issue_session(user.id), "token_type":"bearer", "expires_in":3600}
@app.post("/telegram/webhook")
async def telegram_webhook(update: dict, secret: Annotated[str|None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None):
    if not settings.TELEGRAM.token or not settings.TELEGRAM.webhook_secret:
        raise HTTPException(503, "Telegram webhook is not configured")
    if not hmac.compare_digest(secret or "", settings.TELEGRAM.webhook_secret):
        raise HTTPException(401, "Invalid Telegram webhook secret")
    from telegram_bot import TelegramBot
    await TelegramBot(settings.TELEGRAM.token, settings.MINI_APP_URL).handle_update(update)
    return {"ok": True}
@app.get("/api/v1/quizzes")
async def quizzes(language: str="ru", featured: bool|None=None, age: int|None=None, category: str|None=None):
    async with get_db() as db:
        query=select(QuizPack).where(QuizPack.active.is_(True), QuizPack.language==language)
        if featured is not None: query=query.where(QuizPack.featured.is_(featured))
        if age is not None: query=query.where(QuizPack.age_min<=age, QuizPack.age_max>=age)
        if category: query=query.where(QuizPack.category==category)
        packs=list((await db.execute(query.order_by(QuizPack.sort_order, QuizPack.id))).scalars())
        items=[]
        for pack in packs:
            rows=(await db.execute(select(Question.difficulty,func.count(Question.id)).join(Question.packs).where(QuizPack.id==pack.id,Question.is_active.is_(True)).group_by(Question.difficulty))).all(); difficulty={level:count for level,count in rows}
            items.append({"slug":pack.slug,"title":pack.title,"emoji":pack.emoji,"description":pack.short_description,"question_count":sum(difficulty.values()),"estimated_minutes":pack.estimated_minutes,"age_min":pack.age_min,"age_max":pack.age_max,"featured":pack.featured,"difficulty":difficulty})
        return {"items":items}
@app.get("/api/v1/quizzes/{slug}")
async def quiz(slug: str):
    async with get_db() as db:
        pack=await db.scalar(select(QuizPack).where(QuizPack.slug==slug,QuizPack.active.is_(True)))
        if not pack: raise HTTPException(404,"Quiz pack not found")
        total=await db.scalar(select(func.count(Question.id)).join(Question.packs).where(QuizPack.id==pack.id,Question.is_active.is_(True)))
        return {"slug":pack.slug,"title":pack.title,"emoji":pack.emoji,"description":pack.description,"category":pack.category,"question_count":total or 0,"estimated_minutes":pack.estimated_minutes,"age_min":pack.age_min,"age_max":pack.age_max}
@app.get("/api/v1/categories")
async def categories():
    async with get_db() as db:
        rows=(await db.execute(select(Question.category,func.count(Question.id)).where(Question.is_active.is_(True)).group_by(Question.category))).all()
        return [{"slug":category,"title":category.replace("_"," ").title(),"question_count":count} for category,count in rows]
@app.get("/api/v1/content/stats")
async def content_stats():
    async with get_db() as db:
        total=await db.scalar(select(func.count(Question.id))); active=await db.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True))); russian=await db.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True),Question.language=="ru")); verified=await db.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True),Question.verified.is_(True))); packs=await db.scalar(select(func.count(QuizPack.id)).where(QuizPack.active.is_(True)))
        return {"total_questions":total or 0,"active_questions":active or 0,"languages":{"ru":russian or 0},"quiz_packs":packs or 0,"verified":verified or 0}
@app.get("/api/v1/daily")
async def daily():
    challenge=await db_manager.ensure_daily_challenge(question_count=7); return {"date":challenge.challenge_date.isoformat(),"question_count":challenge.question_count,"title":"Квиз дня"}
@app.post("/api/v1/daily/games")
async def start_daily(user_id: int = Depends(current_user)):
    try: game = await db_manager.create_daily_game(user_id)
    except Exception as error:
        if error.__class__.__name__ == "DailyAlreadyPlayed":
            raise HTTPException(409, {"error": "daily_already_played", "game_id": error.game_id})
        raise
    return public_game(game, await db_manager.get_game_questions(game.id))
@app.get("/api/v1/me")
async def me(user_id: int=Depends(current_user)):
    user=await db_manager.get_or_create_user(user_id); return {"id":user.id,"name":user.first_name or user.username or "Игрок","xp":user.xp,"level":user.level,"streak":user.daily_streak,"achievements":user.achievements or []}
@app.get("/api/v1/me/progress")
async def progress(user_id: int=Depends(current_user)):
    async with get_db() as db:
        rows=(await db.execute(select(Question.category,func.count(UserQuestionHistory.id),func.coalesce(func.sum(UserQuestionHistory.times_correct),0)).join(UserQuestionHistory,UserQuestionHistory.question_id==Question.id).where(UserQuestionHistory.user_id==user_id).group_by(Question.category))).all()
        return {"mastery":[{"category":category,"seen":seen,"correct":int(correct),"percent":min(100,round(100*int(correct)/max(1,seen)))} for category,seen,correct in rows]}
@app.post("/api/v1/games")
async def create_game(payload: NewGame,user_id: int=Depends(current_user)):
    await db_manager.get_or_create_user(user_id)
    try: game=await db_manager.create_game(user_id,payload.category,payload.difficulty,payload.question_count,pack_slug=payload.pack_slug)
    except ValueError as error: raise HTTPException(422,str(error))
    return public_game(game,await db_manager.get_game_questions(game.id))
@app.post("/api/v1/challenges")
async def create_challenge(payload: NewGame, user_id: int = Depends(current_user)):
    challenge, game = await db_manager.create_challenge(user_id, payload.category, payload.difficulty, 5)
    await db_manager.log_event("challenge_create", user_id, {"challenge_id": challenge.id})
    return {"id": challenge.id, "code": challenge.code, "game": public_game(game, await db_manager.get_game_questions(game.id))}
@app.post("/api/v1/challenges/{code}/join")
async def join_challenge(code: str, user_id: int = Depends(current_user)):
    try: game = await db_manager.join_challenge(code, user_id)
    except Exception as error:
        if error.__class__.__name__ == "ChallengeError": raise HTTPException(409, str(error))
        raise
    await db_manager.log_event("challenge_join", user_id, {"code": code})
    return public_game(game, await db_manager.get_game_questions(game.id))
@app.get("/api/v1/challenges/{challenge_id}")
async def challenge_summary(challenge_id: int, user_id: int = Depends(current_user)):
    result = await db_manager.get_challenge_summary(challenge_id)
    if not result["found"]: raise HTTPException(404, "Challenge not found")
    challenge = result["challenge"]
    if user_id not in {challenge.creator_id, challenge.opponent_id}: raise HTTPException(404, "Challenge not found")
    return {"id": challenge.id, "code": challenge.code, "finished": result["finished"], "attempts": [
        {"user_id": attempt.user_id, "score": attempt.score, "correct_answers": attempt.correct_answers, "completed": attempt.completed_at is not None}
        for attempt in result["attempts"]]}
@app.get("/api/v1/leaderboard")
async def leaderboard(limit: int = 10):
    return {"items": await db_manager.get_weekly_leaderboard(min(max(limit, 1), 50))}
@app.get("/api/v1/games/{game_id}")
async def game(game_id:int,user_id:int=Depends(current_user)):
    row=await db_manager.get_game(game_id)
    if not row or row.user_id!=user_id: raise HTTPException(404,"Game not found")
    return public_game(row,await db_manager.get_game_questions(game_id))
@app.post("/api/v1/games/{game_id}/answer")
async def answer(game_id:int,payload:Answer,user_id:int=Depends(current_user)):
    result=await db_manager.answer_game(game_id,user_id,payload.position,payload.selected_index)
    if not result.get("ok"): raise HTTPException(409,result.get("error","answer_failed"))
    row=result["game"]; response={"correct":result.get("correct"),"points":result.get("points",0),"duplicate":result.get("duplicate",False),"game_over":result.get("game_over",False),"score":row.score,"lives_remaining":row.lives_remaining}
    if not result.get("correct") and result.get("question"): response.update({"explanation":result["question"].question.explanation,"correct_answer":result.get("correct_answer")})
    if not response["game_over"]: response["next"]=public_game(row,await db_manager.get_game_questions(game_id))["current_question"]
    return response
dist=Path(__file__).parent/"frontend"/"dist"
if dist.exists(): app.mount("/",StaticFiles(directory=dist,html=True),name="miniapp")
