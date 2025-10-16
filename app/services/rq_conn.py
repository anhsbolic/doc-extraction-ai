import os
from functools import lru_cache

from redis import Redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://vdr-redis:6379/0")


@lru_cache()
def get_redis_connection() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=False)


def get_queue(name: str = "default") -> Queue:
    conn = get_redis_connection()
    return Queue(name, connection=conn)
