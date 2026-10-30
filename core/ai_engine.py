"""
============================================================
  Logi-Track ZeroBaran - العقل الذكي اللوجستي (AI Engine)
  المؤلف: Baran Avisat
============================================================
  هذه الوحدة مسؤولة عن:
  - صياغة رسائل الإشعارات الودية والمخصصة للعملاء
  - تحليل أسباب التأخير إن وجدت
  - ترجمة الحالة التقنية الجافة إلى رسالة إنسانية راقية
  - يدعم Google Gemini API و Groq API (Free Tiers)
============================================================
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from dataclasses import dataclass

from loguru import logger

from config.settings import settings


# ============================================================
#  نماذج
# ============================================================
@dataclass
class NotificationMessage:
    """رسالة إشعار مُولَّدة من العقل الذكي."""

    body: str
    subject: str = ""
    tone: str = "friendly"  # friendly, urgent, formal, apology
    language: str = "ar"
    success: bool = True
    raw_response: Dict = None
    error: Optional[str] = None


# ============================================================
#  العقل الذكي اللوجستي
# ============================================================
class LogisticsBrain:
    """العقل الذكي المسؤول عن صياغة الإشعارات - Logi-Track ZeroBaran."""

    def __init__(self) -> None:
        self.provider = settings.ai_provider
        self._gemini_model = None
        self._groq_client = None
        self._init_providers()

    def _init_providers(self) -> None:
        """تهيئة مزودي الذكاء الاصطناعي."""
        # Gemini
        if settings.has_gemini:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self._gemini_model = genai.GenerativeModel(
                    settings.gemini_model,
                    system_instruction=self._system_prompt(),
                )
                logger.info(f"🧠 تم تفعيل Google Gemini ({settings.gemini_model})")
            except Exception as e:
                logger.error(f"❌ فشل تفعيل Gemini: {e}")
                self._gemini_model = None

        # Groq (بديل سريع)
        if settings.has_groq:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.groq_api_key)
                logger.info(f"🧠 تم تفعيل Groq ({settings.groq_model})")
            except Exception as e:
                logger.error(f"❌ فشل تفعيل Groq: {e}")
                self._groq_client = None

        if self.provider == "none":
            logger.warning("⚠️ لا يوجد مزود ذكاء اصطناعي مُفعَّل - سيتم استخدام القوالب المحلية")

    # ============================================================
    #  صياغة رسالة إشعار للعميل
    # ============================================================
    def compose_notification(
        self,
        customer_name: str,
        tracking_number: str,
        status: str,
        status_ar: str,
        last_location: Optional[str] = None,
        eta: Optional[str] = None,
        carrier: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> NotificationMessage:
        """صياغة رسالة إشعار ودية ومخصصة للعميل."""

        context = context or {}
        context.update({
            "customer_name": customer_name,
            "tracking_number": tracking_number,
            "status": status,
            "status_ar": status_ar,
            "last_location": last_location or "غير محدد",
            "eta": eta or "غير محدد",
            "carrier": carrier or "غير محدد",
        })

        # نحاول عبر المزود المُفعَّل
        if self.provider == "gemini" and self._gemini_model:
            return self._compose_via_gemini(context)
        if self.provider == "groq" and self._groq_client:
            return self._compose_via_groq(context)

        # fallback محلي
        logger.info("ℹ️ استخدام القوالب المحلية للإشعار")
        return self._compose_local(context)

    # ============================================================
    #  تحليل سبب التأخير
    # ============================================================
    def analyze_delay(
        self,
        tracking_number: str,
        events: list,
        carrier: Optional[str] = None,
    ) -> str:
        """تحليل ذكي لأسباب التأخير المتوقع."""
        if not events:
            return "لا تتوفر بيانات كافية لتحليل سبب التأخير."

        context = {
            "tracking_number": tracking_number,
            "carrier": carrier or "غير محدد",
            "events_count": len(events),
            "events": [str(e) for e in events[:5]],
        }

        prompt = (
            f"أنت خبير لوجستي. حلّل سبب تأخير الشحنة {tracking_number} "
            f"بناءً على الأحداث التالية: {json.dumps(context, ensure_ascii=False, default=str)}. "
            "قدم تحليلاً موجزاً (3 أسطر كحد أقصى) باللغة العربية، يوضح السبب المحتمل."
        )

        if self.provider == "gemini" and self._gemini_model:
            try:
                resp = self._gemini_model.generate_content(prompt)
                return resp.text.strip()
            except Exception as e:
                logger.error(f"❌ Gemini delay analysis error: {e}")

        if self.provider == "groq" and self._groq_client:
            try:
                completion = self._groq_client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=200,
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"❌ Groq delay analysis error: {e}")

        return "قد يكون التأخير بسبب أسباب لوجستية خارجية (طقس، ضغط عمل، تأخير جمركي)."

    # ============================================================
    #  صياغة عبر Gemini
    # ============================================================
    def _compose_via_gemini(self, context: Dict) -> NotificationMessage:
        prompt = self._build_user_prompt(context)
        try:
            resp = self._gemini_model.generate_content(prompt)
            text = resp.text.strip()
            return NotificationMessage(
                body=text,
                tone="friendly",
                language="ar",
                raw_response={"provider": "gemini", "text": text},
            )
        except Exception as e:
            logger.error(f"❌ Gemini compose error: {e}")
            msg = self._compose_local(context)
            msg.error = str(e)
            return msg

    # ============================================================
    #  صياغة عبر Groq
    # ============================================================
    def _compose_via_groq(self, context: Dict) -> NotificationMessage:
        prompt = self._build_user_prompt(context)
        try:
            completion = self._groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            text = completion.choices[0].message.content.strip()
            return NotificationMessage(
                body=text,
                tone="friendly",
                language="ar",
                raw_response={"provider": "groq", "text": text},
            )
        except Exception as e:
            logger.error(f"❌ Groq compose error: {e}")
            msg = self._compose_local(context)
            msg.error = str(e)
            return msg

    # ============================================================
    #  صياغة محلية (fallback بدون AI)
    # ============================================================
    def _compose_local(self, context: Dict) -> NotificationMessage:
        """قوالب محلية جاهزة - تعمل حتى بدون AI."""
        name = context.get("customer_name", "عميلنا الكريم")
        tn = context.get("tracking_number", "")
        status = context.get("status", "pending")
        last_location = context.get("last_location", "غير محدد")
        eta = context.get("eta", "غير محدد")

        templates = {
            "pending": (
                f"مرحباً {name} 👋\n"
                f"تم تسجيل شحنتك رقم {tn} في نظامنا بنجاح. "
                f"سنبدأ متابعتها فور توفّر أول تحديث من شركة الشحن.\n"
                f"📦 نتابع شحنتك لحظة بلحظة حتى تصل إليك بأمان."
            ),
            "in_transit": (
                f"مرحباً {name} 👋\n"
                f"شحنتك رقم {tn} في طريقها إليك الآن 🚚\n"
                f"📍 آخر موقع مُسجَّل: {last_location}\n"
                f"⏰ الموعد المتوقع للتسليم: {eta}\n"
                f"سنبقيك على اطلاع بكل تحديث حتى تصلك بأمان."
            ),
            "out_for_delivery": (
                f"مرحباً {name} 👋\n"
                f"شحنتك رقم {tn} خرجت للتوصيل الآن 🛵✨\n"
                f"📍 {last_location}\n"
                f"⏰ ستصل إليك اليوم خلال ساعات قليلة. يُرجى التأهب للاستلام.\n"
                f"هل لديك أي استفسار؟ نحن هنا لمساعدتك."
            ),
            "delivered": (
                f"مرحباً {name} 👋\n"
                f"نفيدك بأن شحنتك رقم {tn} قد تم تسليمها بنجاح ✅\n"
                f"📍 موقع التسليم: {last_location}\n"
                f"نتمنى أن تكون تجربتك ممتعة معنا 💚\n"
                f"شكراً لثقتك بنا!"
            ),
            "delayed": (
                f"مرحباً {name} 👋\n"
                f"نود إعلامك بأن شحنتك رقم {tn} تأخرت قليلاً بسبب ظروف خارجة عن السيطرة ⏳\n"
                f"📍 آخر موقع: {last_location}\n"
                f"⏰ الموعد المتوقع الجديد: {eta}\n"
                f"نعتذر عن هذا التأخير ونعمل على متابعتها حتى تصلك بأسرع وقت."
            ),
            "exception": (
                f"مرحباً {name} 👋\n"
                f"هناك حالة استثنائية تخص شحنتك رقم {tn} ⚠️\n"
                f"📍 {last_location}\n"
                f"فريقنا يعمل حالياً على حل المشكلة وسنحدّثك فوراً بأي جديد.\n"
                f"للاستفسار المباشر: تواصل معنا في أي وقت."
            ),
            "returned": (
                f"مرحباً {name} 👋\n"
                f"نود إعلامك بأن شحنتك رقم {tn} قد تم إرجاعها ↩️\n"
                f"📍 {last_location}\n"
                f"يرجى التواصل معنا لمعرفة التفاصيل وترتيب إعادة الإرسال."
            ),
        }

        body = templates.get(status, templates["pending"])
        return NotificationMessage(
            body=body,
            tone="friendly",
            language="ar",
            raw_response={"provider": "local_template"},
        )

    # ============================================================
    #  برومبت النظام
    # ============================================================
    def _system_prompt(self) -> str:
        return (
            "أنت 'Logi-Track ZeroBaran' - مساعد ذكي متخصص في التواصل اللوجستي "
            "للعملاء. مهمتك صياغة رسائل إشعارات قصيرة (3-5 أسطر كحد أقصى) باللغة العربية "
            "بأسلوب ودّي، دافئ، واحترافي. ابدأ دائماً بتحية العميل باسمه. "
            "اذكر رقم الشحنة بوضوح، الحالة الحالية، الموقع إن وُجد، ووقت التسليم المتوقع. "
            "لا تستخدم لغة تقنية جافة. لا تذكر كلمات مثل 'API' أو 'status code'. "
            "تجنّب الإطالة. استخدم إيموجي واحد أو اثنين فقط بشكل لطيف."
        )

    def _build_user_prompt(self, context: Dict) -> str:
        return (
            f"اكتب رسالة إشعار قصيرة ومودّة باللغة العربية للعميل '{context.get('customer_name')}'.\n"
            f"تفاصيل الشحنة:\n"
            f"- رقم التتبع: {context.get('tracking_number')}\n"
            f"- الحالة التقنية: {context.get('status')}\n"
            f"- الحالة بالعربية: {context.get('status_ar')}\n"
            f"- آخر موقع: {context.get('last_location')}\n"
            f"- وقت التسليم المتوقع: {context.get('eta')}\n"
            f"- شركة الشحن: {context.get('carrier')}\n\n"
            f"اكتب الرسالة الآن مباشرةً، بدون عنوان أو ملاحظات إضافية."
        )


# ============================================================
#  نسخة مشتركة
# ============================================================
ai_brain = LogisticsBrain()
