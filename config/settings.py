"""
============================================================
  Logi-Track ZeroBaran - إعدادات النظام المركزية
  المؤلف: Baran Avisat (Baranavisat@gmail.com)
  واتساب: 00905313263722
============================================================
  هذه الوحدة تحمل كل إعدادات النظام من متغيرات البيئة
  وتوفر وصولاً موحداً لكل طبقات النظام.
============================================================
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# ============================================================
#  مسارات المشروع الأساسية
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"

# إنشاء المجلدات إن لم تكن موجودة
for d in (DATA_DIR, LOGS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
#  معلومات المؤلف وحقوق الملكية
# ============================================================
AUTHOR = {
    "name": "Baran Avisat",
    "email": "Baranavisat@gmail.com",
    "whatsapp": "00905313263722",
    "role": "Founder & Lead Engineer",
}

PROJECT_META = {
    "name": "Logi-Track ZeroBaran",
    "version": "1.0.0",
    "author": AUTHOR["name"],
    "email": AUTHOR["email"],
    "license": "Proprietary - All Rights Reserved",
    "description": (
        "المنظومة الذاتية الذكية لتتبع الشحنات، إدارة مسارات "
        "التوصيل، وإشعارات العملاء آلياً عبر رسائل فورية"
    ),
}


class Settings(BaseSettings):
    """إعدادات النظام المركزية المستخرجة من متغيرات البيئة."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === معلومات عامة ===
    project_name: str = Field(default="Logi-Track ZeroBaran")
    project_version: str = Field(default="1.0.0")
    environment: str = Field(default="production")

    # === Supabase ===
    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")
    supabase_service_key: str = Field(default="")

    # === Gemini / Groq ===
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-flash")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # === Telegram ===
    telegram_bot_token: str = Field(default="")
    telegram_admin_chat_id: str = Field(default="")

    # === سلوك النظام ===
    poll_interval_hours: int = Field(default=1)
    timezone: str = Field(default="Asia/Istanbul")
    default_language: str = Field(default="ar")

    # === شركات الشحن (اختيارية) ===
    aramex_api_key: str = Field(default="")
    dhl_api_key: str = Field(default="")
    fedex_api_key: str = Field(default="")
    turkey_ptt_api_key: str = Field(default="")

    # === المتاجر ===
    shopify_api_key: str = Field(default="")
    shopify_shop_domain: str = Field(default="")

    # === مفاتيح ذكية ===
    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_admin_chat_id)

    @property
    def ai_provider(self) -> str:
        """يرجع مزود الذكاء الاصطناعي المفضل (الأولوية لـ Gemini)."""
        if self.has_gemini:
            return "gemini"
        if self.has_groq:
            return "groq"
        return "none"


# نسخة وحيدة مشتركة (singleton)
settings = Settings()
