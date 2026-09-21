# -*- coding: utf-8 -*-
"""
config.py — Botning sozlamalari shu yerda.

Faqat shu faylni tahrirlang — bot.py ichiga tegishning hojati yo'q.
"""

import os

# BotFather'dan olingan tokeningiz.
# Xohlasangiz shu yerga to'g'ridan-to'g'ri yozing, yoki BOT_TOKEN muhit
# o'zgaruvchisi orqali bering (shunda bu yerdagi qiymat ishlatilmaydi).
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926772109:AAEqg1trnWji8fUvq_PpZki40jLMa8U28ws")

# Har bir savolga beriladigan vaqt (soniyalarda).
TIME_PER_QUESTION = 30

# Fayl nomlari (odatda o'zgartirish shart emas).
QUESTIONS_FILE_NAME = "questions.json"
DB_FILE_NAME = "users.db"

# ---------------------------------------------------------------------------
# ADMINLAR — "➕ Savol qo'shish" funksiyasiga kira oladigan telefon raqamlar.
# ---------------------------------------------------------------------------
# Har bir raqamni FAQAT RAQAMLAR bilan yozing (bo'shliq, "+", "-" belgilarisiz),
# davlat kodi bilan birga — Telegram kontakt yuborganda shu formatda keladi.
# Masalan O'zbekiston raqami uchun: "998901234567"
#
# Xohlagancha raqam qo'shishingiz mumkin — har birini alohida qatorga,
# vergul bilan yozing:
ADMIN_PHONES = [
    "998980074877",
    "998993409914",# <-- bu yerga o'zingizning admin raqamlaringizni yozing
    # "998912223344",
    # "998933334455",
]