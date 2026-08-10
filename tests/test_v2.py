import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from api import public_game
from content.packs.curated_ru import PACKS, build_questions
from max_auth import MaxAuthError, validate_init_data
from scripts.content.audit import normalise


def signed_init_data(user_id=99):
    values={"auth_date":str(int(time.time())),"query_id":"q","user":json.dumps({"id":user_id,"first_name":"Тест"},separators=(",",":"))}
    launch="\n".join(f"{key}={value}" for key,value in sorted(values.items()))
    secret=hmac.new(b"WebAppData",b"token",hashlib.sha256).digest()
    values["hash"]=hmac.new(secret,launch.encode(),hashlib.sha256).hexdigest()
    return urlencode(values)


def test_max_init_data_validation_is_signed_and_expiring():
    assert validate_init_data(signed_init_data(),"token").user_id==99
    with __import__("pytest").raises(MaxAuthError): validate_init_data(signed_init_data(),"wrong-token")


def test_v2_curated_catalog_has_ten_packs_and_550_russian_records():
    rows=build_questions()
    assert len(PACKS)==10 and len(rows)==550
    assert all(len(row["wrong_answers"])==3 and row["correct_answer"] not in row["wrong_answers"] and row["explanation"] for row in rows)
    texts=[normalise(row["text"]) for row in rows]
    assert len(texts)==len(set(texts))


def test_public_game_contract_never_serializes_answer_key():
    question=type("Question",(),{"text":"Вопрос","correct_answer":"Секрет"})()
    row=type("GameQuestion",(),{"position":0,"question":question,"answer_options":["A","B","C","D"],"correct_index":2})()
    game=type("Game",(),{"id":1,"mode":"solo","status":"in_progress","score":0,"correct_answers":0,"question_count":5,"current_question_index":0})()
    payload=public_game(game,[row])
    rendered=json.dumps(payload,ensure_ascii=False)
    assert "Секрет" not in rendered
    assert {"correct_index", "correct_answer"}.isdisjoint(payload.keys() | payload["current_question"].keys())
