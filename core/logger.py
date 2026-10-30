"""
============================================================
  Logi-Track ZeroBaran - نظام السجلات (Logger)
  المؤلف: Baran Avisat
============================================================
  إعداد loguru المركزي مع الكتابة إلى ملف وإلى الطرفية.
============================================================
"""

import sys
from pathlib import Path
from loguru import logger

from config.settings import BASE_DIR, LOGS_DIR


def setup_logger(level: str = "INFO") -> None:
    """تهيئة المسجل المركزي."""
    logger.remove()

    # === الطرفية ===
    logger.add(
        sys.stdout,
        level=level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=True,
    )

    # === ملف السجل اليومي ===
    log_file = LOGS_DIR / "logi_track_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        level=level,
        rotation="00:00",  # يدور عند منتصف الليل
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        backtrace=True,
        diagnose=False,
    )

    # === ملف للأخطاء فقط ===
    error_file = LOGS_DIR / "errors_{time:YYYY-MM-DD}.log"
    logger.add(
        str(error_file),
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | ERROR | "
            "{name}:{function}:{line} - {message}\n{exception}"
        ),
        backtrace=True,
        diagnose=True,
    )

    logger.info("📝 تم تهيئة نظام السجلات بنجاح")


# تهيئة تلقائية عند الاستيراد
setup_logger()

__all__ = ["logger", "setup_logger"]
