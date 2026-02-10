import json 
import os
from typing import List, Tuple
import redis
from dotenv import load_dotenv

load_dotenv()

MAX_TURNS = 5 
REDIS_KEY_PREFIX = "conv:"
REDIS_TTL = 86400 

REDIS_HOST = os.getenv("REDIS_HOST") or "localhost"
REDIS_PORT = os.getenv("REDIS_PORT") or 6379
REDIS_DB = os.getenv("REDIS_DB") or 0


_memory_store: dict[str, List[Tuple[str, str]]] = {}
_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        return _redis_client
    try:
        _redis_client = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB,
            decode_responses=True,
        )
        _redis_client.ping()
        return _redis_client
    except redis.exceptions.ConnectionError as e:
        print(f"Error al conectar a Redis: {e}")
        return None


def get_history(customer_id: str)-> List[Tuple[str, str]]:
    "devuelve el historial de conversacion del cliente"
    r = _get_redis()
    if r is not None:
        try:
            key = f"{REDIS_KEY_PREFIX}{customer_id}"
            raw = r.get(key)
            if raw:
                data = json.loads(raw)
                return [(item["role"], item["content"]) for item in data]
            return []
        except Exception:
            pass
    if customer_id in _memory_store:
        return []
    return (_memory_store[customer_id])

def append_turn(customer_id: str, human_text: str, ai_text: str)-> None:

    history = get_history(customer_id)
    history.append(("human", human_text))
    history.append(("ai", ai_text))
    while len(history) > MAX_TURNS * 2:
        history.pop(0)
        history.pop(0)
    
    payload = [{"role": role, "content": content} for role, content in history]
    json_str = json.dumps(payload, ensure_ascii=False)
    r = _get_redis()
    if r is not None:
        try:
            key = f"{REDIS_KEY_PREFIX}{customer_id}"
            r.setex(key, REDIS_TTL, json_str)
            return 
        except Exception:
            pass
    _memory_store[customer_id] = history


def clear_history(customer_id: str)-> None:
    "limpia el historial de conversacion del cliente"
    r = _get_redis()
    if r is not None:
        try:
            key = f"{REDIS_KEY_PREFIX}{customer_id}"
            r.delete(key)
        except Exception:
            pass
    _memory_store.pop(customer_id, None)