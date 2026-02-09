import sys
from loguru import logger
from src.config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ლოგერის კონფიგურაცია
logger.remove()  # default handler-ის წაშლა

# კონსოლის ლოგი
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
)

# ფაილის ლოგი
logger.add(
    LOG_DIR / "aibetuchio.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG",
)


def get_logger(name: str):
    return logger.bind(name=name)
