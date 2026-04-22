import os
import redis.asyncio as redis
from langgraph.checkpoint.redis import AsyncRedisSaver
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis():
    return redis.from_url(REDIS_URL)


def get_checkpointer():
    return AsyncRedisSaver.from_conn_string(REDIS_URL)