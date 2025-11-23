import redis
from app.core.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True
)


def add_to_blacklist(token: str, expire_seconds: int):
    """Добавление токена в блэклист"""
    redis_client.setex(f"blacklist:{token}", expire_seconds, "1")


def is_token_blacklisted(token: str) -> bool:
    """Проверка, находится ли токен в блэклисте"""
    return redis_client.exists(f"blacklist:{token}") > 0


def store_refresh_token(user_id: str, token: str, expire_seconds: int):
    """Сохранение refresh токена"""
    redis_client.setex(f"refresh_token:{user_id}", expire_seconds, token)


def get_refresh_token(user_id: str) -> str | None:
    """Получение refresh токена пользователя"""
    return redis_client.get(f"refresh_token:{user_id}")


def delete_refresh_token(user_id: str):
    """Удаление refresh токена"""
    redis_client.delete(f"refresh_token:{user_id}")

