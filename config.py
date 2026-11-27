# -*- coding: utf-8 -*-
"""
config.py — barcha sozlamalar shu yerda.
Maxfiy qiymatlar (token, API kalit) FAQAT muhit o'zgaruvchilari orqali beriladi.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
BOOKS_DIR = DATA_DIR / "books"
IMPORT_DIR = DATA_DIR / "imports"
for _d in (DATA_DIR, AUDIO_DIR, BOOKS_DIR, IMPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_FILE = DATA_DIR / "users.db"
SEED_QUESTIONS_FILE = BASE_DIR / "questions.json"   # faqat birinchi ishga tushishda bazaga o'tkaziladi

# --- Telegram -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926772109:AAEqg1trnWji8fUvq_PpZki40jLMa8U28ws")
# Ilova joylashgan HTTPS manzil (masalan https://tarix.example.com)
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))

# --- Test sozlamalari -------------------------------------------------------
TIME_PER_QUESTION = 30          # soniya
POINTS_PER_CORRECT = 0.5        # har bir to'g'ri javob uchun ball
TZ_OFFSET_HOURS = 5             # O'zbekiston (kunlik streak hisobi uchun)

# --- Adminlar ---------------------------------------------------------------
# Telefon raqam (faqat raqamlar, davlat kodi bilan) yoki Telegram ID bo'yicha.
ADMIN_PHONES = [
    "998980074877",
    "998993409914",
]
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# --- AI (fayldan savollarni ajratib olish) -----------------------------------
# Google Gemini: kalitni https://aistudio.google.com/apikey dan bepul olish mumkin
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCcILdOdTIg1S-ZPDhIEoWINJTXdd19DNc")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# --- Dev rejim (faqat kompyuteringizda sinash uchun!) ---------------------------
DEV_MODE = os.environ.get("DEV_MODE", "") == "1"
