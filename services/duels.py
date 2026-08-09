"""Compatibility facade for the beta Friend Challenge service.

The old Redis realtime duel implementation was removed from the runtime.
Challenges are asynchronous and are persisted in PostgreSQL/SQLite instead.
"""

from db import ChallengeError, db_manager


class DuelService:
    async def create_duel(self, player1_id: int, category="general", question_count: int = 5):
        challenge, game = await db_manager.create_challenge(player1_id, category, "medium", question_count)
        return {"id": challenge.id, "code": challenge.code, "game_id": game.id}

    async def join_duel(self, duel_id: int, player2_id: int):
        challenge = await db_manager.get_challenge(duel_id)
        if not challenge:
            raise ChallengeError("challenge_not_found")
        game = await db_manager.join_challenge(challenge.code, player2_id)
        return {"id": challenge.id, "game_id": game.id}


duel_service = DuelService()
