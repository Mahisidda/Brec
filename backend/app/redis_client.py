import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3
    )
    redis_client.ping()
    print(f"[Redis] Connected to: {REDIS_URL}")
except redis.ConnectionError as e:
    print(f"[Redis Error] Could not connect to Redis: {e}")
    redis_client = None
