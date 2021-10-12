from redis import from_url, StrictRedis
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_URL

redis: StrictRedis = (
    from_url(REDIS_URL, db=REDIS_DB)
    if REDIS_URL
    else (
        StrictRedis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD
        )
    )
)
