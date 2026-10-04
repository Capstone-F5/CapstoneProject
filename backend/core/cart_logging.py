import logging
import os
from logging.handlers import RotatingFileHandler


_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

cart_logger = logging.getLogger("cart_api")
cart_logger.setLevel(logging.INFO)
cart_logger.propagate = False

if not cart_logger.handlers:
    handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "cart_api.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    cart_logger.addHandler(handler)
