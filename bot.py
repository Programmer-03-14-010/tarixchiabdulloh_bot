# -*- coding: utf-8 -*-
"""
Tarix bilim bot — Telegram bot for history quiz (@QuizBot uslubida)

Ishga tushirish:
    1. BOT_TOKEN muhit o'zgaruvchisiga yoki quyidagi qatorga tokeningizni yozing
    2. pip install -r requirements.txt
    3. python bot.py

Savollarni qo'shish/tahrirlash uchun README.md faylidagi ko'rsatmaga qarang
(savollar_qoshish.py skripti orqali).
"""

import asyncio
import json
import logging
import os
import random
import sqlite3
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from config import BOT_TOKEN, TIME_PER_QUESTION, QUESTIONS_FILE_NAME, DB_FILE_NAME, ADMIN_PHONES

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / QUESTIONS_FILE_NAME
DB_FILE = BASE_DIR / DB_FILE_NAME

ALL_TOPICS_MARKER = -1  # "Barcha mavzular" ni bildiradi

ASK_NAME, ASK_PHONE = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ma'lumotlar bazasi (foydalanuvchilar)
# ---------------------------------------------------------------------------

def init_db() -> None:
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Eski bazalarda is_admin ustuni bo'lmasligi mumkin — xavfsiz qo'shamiz.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # ustun allaqachon mavjud
    conn.commit()
    conn.close()


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())


def is_admin_phone(phone: str) -> bool:
    normalized = normalize_phone(phone)
    admin_numbers = {normalize_phone(p) for p in ADMIN_PHONES}
    return normalized in admin_numbers


def get_user(telegram_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute(
        "SELECT full_name, phone, is_admin FROM users WHERE telegram_id = ?", (telegram_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row  # (full_name, phone, is_admin) yoki None


def save_user(telegram_id: int, full_name: str, phone: str) -> None:
    is_admin = 1 if is_admin_phone(phone) else 0
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR REPLACE INTO users (telegram_id, full_name, phone, is_admin) VALUES (?, ?, ?, ?)",
        (telegram_id, full_name, phone, is_admin),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Savollar bazasi: {grade: {subject: {topic: [ {question, options, answer} ]}}}
# ---------------------------------------------------------------------------

with open(QUESTIONS_FILE, encoding="utf-8") as f:
    QUESTIONS = json.load(f)

GRADES = list(QUESTIONS.keys())


def subjects_for(grade: str):
    return list(QUESTIONS.get(grade, {}).keys())


def topics_for(grade: str, subject: str):
    return list(QUESTIONS.get(grade, {}).get(subject, {}).keys())


def questions_for(grade: str, subject: str, topic_index: int):
    """topic_index == ALL_TOPICS_MARKER bo'lsa, shu fandagi barcha mavzular
    savollari birlashtirilib qaytariladi.

    MUHIM: bu yerda savol dict'lari nusxalanmaydi — xuddi QUESTIONS
    ichidagi ASL obyektlarning o'zi qaytariladi. Shunga admin "Tahrirlash"/
    "O'chirish" qilganda, xotiradagi aktiv test sessiyasidagi savol bilan
    fayldagi savol AYNAN bitta obyekt bo'lib qoladi (identifikator orqali
    topiladi) va to'g'ridan-to'g'ri joyida yangilanadi/o'chiriladi.
    """
    topics = topics_for(grade, subject)
    if topic_index == ALL_TOPICS_MARKER:
        pool = []
        for t in topics:
            pool.extend(QUESTIONS[grade][subject][t])
        return pool
    topic_name = topics[topic_index]
    return list(QUESTIONS[grade][subject][topic_name])


# ---------------------------------------------------------------------------
# Ro'yxatdan o'tish (/start)
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    existing = get_user(user_id)
    if existing:
        full_name, _phone, _is_admin = existing
        await update.message.reply_text(
            f"Xush kelibsiz, {full_name}! 👋\n"
            "Ushbu bot sizga tarix fanidan bilimingizni oshirishingiz uchun yordam beradi."
        )
        await show_start_button(update.effective_chat.id, context)
        return ConversationHandler.END

    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Ushbu bot sizga tarix fanidan bilimingizni oshirishingiz uchun yordam beradi.\n\n"
        "Boshlash uchun avval ro'yxatdan o'tamiz.\n"
        "Ism va familyangizni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    full_name = update.message.text.strip()
    if len(full_name) < 3:
        await update.message.reply_text(
            "Iltimos, ism va familyangizni to'liq kiriting (masalan: Ali Valiyev):"
        )
        return ASK_NAME

    context.user_data["full_name"] = full_name

    phone_button = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[phone_button]], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"Rahmat, {full_name}!\n\nEndi telefon raqamingizni yuboring:",
        reply_markup=markup,
    )
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    if not contact:
        await update.message.reply_text(
            "Iltimos, pastdagi tugma orqali telefon raqamingizni yuboring."
        )
        return ASK_PHONE

    phone = contact.phone_number
    full_name = context.user_data.get("full_name", "Foydalanuvchi")
    user_id = update.effective_user.id
    save_user(user_id, full_name, phone)

    await update.message.reply_text(
        "Ro'yxatdan muvaffaqiyatli o'tdingiz! ✅",
        reply_markup=ReplyKeyboardRemove(),
    )
    await show_start_button(update.effective_chat.id, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Ro'yxatdan o'tish bekor qilindi. Qaytadan boshlash uchun /start ni bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# "Testni boshlash" tugmasi va 3-2-1 sanoq
# ---------------------------------------------------------------------------

async def show_start_button(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [[InlineKeyboardButton("🎯 Testni boshlash", callback_data="begin_test")]]

    # Shaxsiy chatda chat_id == foydalanuvchi telegram_id
    user_row = get_user(chat_id)
    if user_row and len(user_row) > 2 and user_row[2]:
        buttons.append([InlineKeyboardButton("➕ Savol qo'shish (admin)", callback_data="admin_add")])

    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id, text="Nima qilmoqchisiz?", reply_markup=markup
    )


async def begin_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    msg = await query.edit_message_text("3️⃣")
    await asyncio.sleep(1)
    await msg.edit_text("2️⃣")
    await asyncio.sleep(1)
    await msg.edit_text("1️⃣")
    await asyncio.sleep(1)
    await msg.edit_text("🚀 Boshladik!")

    await show_grade_menu(update.effective_chat.id, context)


# ---------------------------------------------------------------------------
# Sinf / fan / mavzu tanlash (index asosida — callback_data qisqa bo'lishi uchun)
# ---------------------------------------------------------------------------

async def show_grade_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [InlineKeyboardButton(g, callback_data=f"g:{i}")] for i, g in enumerate(GRADES)
    ]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, text="Sinfingizni tanlang:", reply_markup=markup)


async def grade_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    grade_idx = int(query.data.split(":")[1])
    grade = GRADES[grade_idx]
    subjects = subjects_for(grade)

    buttons = [
        [InlineKeyboardButton(s, callback_data=f"s:{grade_idx}:{i}")]
        for i, s in enumerate(subjects)
    ]
    buttons.append([InlineKeyboardButton("⬅️ Sinfni qayta tanlash", callback_data="backg")])
    markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(f"{grade} tanlandi.\n\nQaysi fandan bilimingizni sinaysiz?", reply_markup=markup)


async def back_to_grades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton(g, callback_data=f"g:{i}")] for i, g in enumerate(GRADES)
    ]
    markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Sinfingizni tanlang:", reply_markup=markup)


async def subject_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, grade_idx, subj_idx = query.data.split(":")
    grade_idx, subj_idx = int(grade_idx), int(subj_idx)
    grade = GRADES[grade_idx]
    subject = subjects_for(grade)[subj_idx]
    topics = topics_for(grade, subject)

    buttons = [
        [InlineKeyboardButton(f"{t} ({len(QUESTIONS[grade][subject][t])} ta)", callback_data=f"t:{grade_idx}:{subj_idx}:{i}")]
        for i, t in enumerate(topics)
    ]
    total = sum(len(QUESTIONS[grade][subject][t]) for t in topics)
    buttons.append(
        [InlineKeyboardButton(f"🎲 Barcha mavzular ({total} ta)", callback_data=f"t:{grade_idx}:{subj_idx}:{ALL_TOPICS_MARKER}")]
    )
    buttons.append([InlineKeyboardButton("⬅️ Fanni qayta tanlash", callback_data=f"g:{grade_idx}")])
    markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        f"{grade}, {subject}\n\nQaysi mavzudan (test to'plamidan) sinov topshirasiz?",
        reply_markup=markup,
    )


async def topic_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, grade_idx, subj_idx, topic_idx = query.data.split(":")
    grade_idx, subj_idx, topic_idx = int(grade_idx), int(subj_idx), int(topic_idx)
    grade = GRADES[grade_idx]
    subject = subjects_for(grade)[subj_idx]
    topics = topics_for(grade, subject)

    if topic_idx == ALL_TOPICS_MARKER:
        topic_name = "Barcha mavzular"
    else:
        topic_name = topics[topic_idx]

    pool = questions_for(grade, subject, topic_idx)
    if not pool:
        await query.edit_message_text("Kechirasiz, bu bo'lim uchun hozircha savollar mavjud emas.")
        return

    context.user_data["pending_quiz"] = {
        "grade": grade,
        "subject": subject,
        "topic": topic_name,
        "grade_idx": grade_idx,
        "subj_idx": subj_idx,
        "topic_idx": topic_idx,
    }

    info_text = (
        f"🎲 “{topic_name}”\n\n"
        f"{grade} — {subject}. Testiga tayyorlaning\n\n"
        f"🖊 {len(pool)} ta savol\n"
        f"⏱️ Har bir savol uchun {TIME_PER_QUESTION} soniya\n"
        f"📰 Ovozlar test egasiga ko'rinadigan bo'ladi\n\n"
        f"🏁 Tayyor bo'lganingizda quyidagi tugmani bosing.\n"
        f"Uni to'xtatish uchun /stop buyrug'ini yuboring."
    )
    buttons = [
        [InlineKeyboardButton("🏁 Boshlash", callback_data="run_quiz")],
        [InlineKeyboardButton("⬅️ Mavzuni qayta tanlash", callback_data=f"s:{grade_idx}:{subj_idx}")],
    ]
    await query.edit_message_text(info_text, reply_markup=InlineKeyboardMarkup(buttons))


# ---------------------------------------------------------------------------
# Savol-javob jarayoni (native Telegram quiz-poll, 35 soniyalik taymer bilan)
# ---------------------------------------------------------------------------

async def run_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get("pending_quiz")
    if not pending:
        await query.edit_message_text("Avval /start orqali sinf va fanni tanlang.")
        return

    pool = questions_for(pending["grade"], pending["subject"], pending["topic_idx"])
    random.shuffle(pool)

    context.user_data["quiz"] = {
        "grade": pending["grade"],
        "subject": pending["subject"],
        "topic": pending["topic"],
        "questions": pool,
        "index": 0,
        "correct": 0,
        "wrong": 0,
        "skipped": 0,
        "history": [],
        "current_poll_id": None,
        "current_message_id": None,
        "last_correct_index": None,
        "answered": True,  # boshida True — birinchi savol yuborilganda False bo'ladi
        "chat_id": update.effective_chat.id,
    }
    context.user_data.pop("pending_quiz", None)

    await query.edit_message_text(f"“{pending['topic']}” boshlandi! 🚀")
    await send_next_poll(update.effective_chat.id, update.effective_user.id, context)


async def send_next_poll(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    quiz = context.user_data.get("quiz")
    if not quiz:
        return

    idx = quiz["index"]
    questions = quiz["questions"]

    if idx >= len(questions):
        await finish_quiz(chat_id, user_id, context)
        return

    q = questions[idx]
    options = list(q["options"])
    random.shuffle(options)
    correct_index = options.index(q["answer"])

    stop_markup_buttons = []
    # Faqat ADMIN_PHONES ro'yxatidagi foydalanuvchilarga ko'rinadi - oddiy
    # foydalanuvchilar bu tugmani umuman ko'rmaydi.
    if user_is_admin(user_id):
        stop_markup_buttons.append(
            [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"admeditmenu:{idx}")]
        )
    stop_markup_buttons.append(
        [InlineKeyboardButton("🛑 Tugatish", callback_data="finish_quiz_btn")]
    )
    stop_markup = InlineKeyboardMarkup(stop_markup_buttons)

    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"{idx + 1}-savol: {q['question']}",
        options=options,
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False,
        open_period=TIME_PER_QUESTION,
        reply_markup=stop_markup,
    )

    quiz["current_poll_id"] = message.poll.id
    quiz["current_message_id"] = message.message_id
    quiz["last_correct_index"] = correct_index
    quiz["answered"] = False

    context.job_queue.run_once(
        poll_timeout,
        when=TIME_PER_QUESTION + 2,
        chat_id=chat_id,
        user_id=user_id,
        data={"poll_id": message.poll.id, "index": idx},
        name=f"timeout:{user_id}:{message.poll.id}",
    )


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    answer = update.poll_answer
    user_id = answer.user.id
    quiz = context.user_data.get("quiz")
    if not quiz or quiz.get("current_poll_id") != answer.poll_id or quiz.get("answered"):
        return

    idx = quiz["index"]
    q = quiz["questions"][idx]
    quiz["answered"] = True

    chosen_indexes = answer.option_ids
    is_correct = bool(chosen_indexes) and quiz.get("last_correct_index") == chosen_indexes[0]

    if is_correct:
        quiz["correct"] += 1
        mark = "✅"
    else:
        quiz["wrong"] += 1
        mark = "❌"

    quiz["history"].append({"question": q["question"], "status": mark})

    for job in context.job_queue.get_jobs_by_name(f"timeout:{user_id}:{answer.poll_id}"):
        job.schedule_removal()

    quiz["index"] += 1
    chat_id = quiz.get("chat_id")
    if chat_id:
        await asyncio.sleep(1.5)
        await send_next_poll(chat_id, user_id, context)


async def poll_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = context.job.user_id
    chat_id = context.job.chat_id
    quiz = context.user_data.get("quiz")
    if not quiz or quiz.get("current_poll_id") != job_data["poll_id"] or quiz.get("answered"):
        return

    quiz["answered"] = True
    quiz["skipped"] += 1
    idx = job_data["index"]
    q = quiz["questions"][idx]
    quiz["history"].append({"question": q["question"], "status": "⏭ (vaqt tugadi)"})

    try:
        await context.bot.stop_poll(chat_id=chat_id, message_id=quiz["current_message_id"])
    except Exception:
        pass

    quiz["index"] += 1
    await send_next_poll(chat_id, user_id, context)


async def end_active_quiz(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Faol testni majburan to'xtatadi va natijani chiqaradi. Test yo'q bo'lsa False qaytaradi."""
    quiz = context.user_data.get("quiz")
    if not quiz:
        return False

    for job in context.job_queue.get_jobs_by_name(f"timeout:{user_id}:{quiz.get('current_poll_id')}"):
        job.schedule_removal()

    if quiz.get("current_message_id"):
        try:
            await context.bot.stop_poll(chat_id=chat_id, message_id=quiz["current_message_id"])
        except Exception:
            pass

    await finish_quiz(chat_id, user_id, context)
    return True


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ended = await end_active_quiz(update.effective_chat.id, update.effective_user.id, context)
    if not ended:
        await update.message.reply_text("Hozirda faol test yo'q.")


async def finish_quiz_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    ended = await end_active_quiz(update.effective_chat.id, update.effective_user.id, context)
    if not ended:
        await query.message.reply_text("Bu test allaqachon yakunlangan.")


async def finish_quiz(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    quiz = context.user_data.get("quiz")
    if not quiz:
        return

    user_row = get_user(user_id)
    full_name = user_row[0] if user_row else "Foydalanuvchi"

    correct = quiz["correct"]
    wrong = quiz["wrong"]
    skipped = quiz["skipped"]
    total = correct + wrong + skipped

    summary = (
        "📊 Sizning natijangiz:\n\n"
        f"👤 Ism familya: {full_name}\n"
        f"📚 {quiz['grade']}, {quiz['subject']} — {quiz['topic']}\n"
        f"✅ To'g'ri javoblar: {correct}\n"
        f"❌ Xato javoblar: {wrong}\n"
        f"⏭ O'tkazib yuborilgan (vaqt tugagan): {skipped}\n"
        f"📝 Jami savollar: {total}"
    )
    await context.bot.send_message(chat_id=chat_id, text=summary)

    history = quiz["history"]
    if history:
        lines = [f"{i}. {h['status']} {h['question']}" for i, h in enumerate(history, start=1)]
        await send_long_text(context, chat_id, "\n".join(lines), header="📋 Batafsil natija:")

    context.user_data.pop("quiz", None)

    buttons = [[InlineKeyboardButton("🔁 Yana boshlash", callback_data="begin_test")]]
    await context.bot.send_message(
        chat_id=chat_id, text="Yana bir test topshirmoqchimisiz?", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def send_long_text(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, header: str = "") -> None:
    MAX_LEN = 3500
    chunks = []
    current = header + "\n\n" if header else ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_LEN:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    for chunk in chunks:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


# ---------------------------------------------------------------------------
# ADMIN: "Savol qo'shish" (faqat config.py dagi ADMIN_PHONES raqamlari uchun)
# ---------------------------------------------------------------------------

ADM_GRADE, ADM_SUBJECT, ADM_TOPIC, ADM_QUESTION, ADM_A, ADM_B, ADM_C, ADM_D, ADM_CORRECT = range(2, 11)


def user_is_admin(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and len(row) > 2 and row[2])


def save_questions_to_file() -> None:
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(QUESTIONS, f, ensure_ascii=False, indent=1)


def find_question_topic(grade: str, subject: str, target_q: dict):
    """
    Berilgan savol lug'ati (dict) QUESTIONS bazasida qaysi mavzuga
    tegishli ekanini topadi (identity - `is` - orqali, matn bo'yicha emas,
    shunda bir xil matnli boshqa savol bilan chalkashmaydi).
    """
    for topic, qlist in QUESTIONS.get(grade, {}).get(subject, {}).items():
        for q in qlist:
            if q is target_q:
                return topic
    return None


def add_question_to_bank(grade: str, subject: str, topic: str, question: str, options: list, correct_text: str) -> None:
    QUESTIONS.setdefault(grade, {})
    QUESTIONS[grade].setdefault(subject, {})
    QUESTIONS[grade][subject].setdefault(topic, [])
    QUESTIONS[grade][subject][topic].append(
        {"question": question, "options": options, "answer": correct_text}
    )
    if grade not in GRADES:
        GRADES.append(grade)
    save_questions_to_file()


async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not user_is_admin(update.effective_user.id):
        await query.message.reply_text("Bu funksiya faqat adminlar uchun.")
        return ConversationHandler.END

    context.user_data["new_q"] = {}
    existing_grades = ", ".join(GRADES) if GRADES else "(hozircha yo'q)"
    await query.message.reply_text(
        "➕ Yangi savol qo'shish\n\n"
        f"Mavjud sinflar: {existing_grades}\n\n"
        "Sinfni kiriting (masalan: 11-sinf):\n"
        "Istalgan vaqt bekor qilish uchun /admin_cancel yuboring."
    )
    return ADM_GRADE


async def admin_get_grade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    grade = update.message.text.strip()
    context.user_data["new_q"]["grade"] = grade
    existing_subjects = ", ".join(subjects_for(grade)) or "(hozircha yo'q)"
    await update.message.reply_text(
        f"Mavjud fanlar ({grade}): {existing_subjects}\n\nFanni kiriting (masalan: Jahon tarixi):"
    )
    return ADM_SUBJECT


async def admin_get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    subject = update.message.text.strip()
    context.user_data["new_q"]["subject"] = subject
    grade = context.user_data["new_q"]["grade"]
    existing_topics = ", ".join(topics_for(grade, subject)) or "(hozircha yo'q)"
    await update.message.reply_text(
        f"Mavjud mavzular: {existing_topics}\n\nMavzuni kiriting (masalan: Amir Temur davri):"
    )
    return ADM_TOPIC


async def admin_get_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["topic"] = update.message.text.strip()
    await update.message.reply_text("Savol matnini kiriting:")
    return ADM_QUESTION


async def admin_get_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["question"] = update.message.text.strip()
    await update.message.reply_text("A) variantini kiriting:")
    return ADM_A


async def admin_get_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["a"] = update.message.text.strip()
    await update.message.reply_text("B) variantini kiriting:")
    return ADM_B


async def admin_get_b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["b"] = update.message.text.strip()
    await update.message.reply_text("C) variantini kiriting:")
    return ADM_C


async def admin_get_c(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["c"] = update.message.text.strip()
    await update.message.reply_text("D) variantini kiriting:")
    return ADM_D


async def admin_get_d(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_q"]["d"] = update.message.text.strip()
    nq = context.user_data["new_q"]

    buttons = [
        [InlineKeyboardButton(f"A) {nq['a'][:40]}", callback_data="admcorrect:A")],
        [InlineKeyboardButton(f"B) {nq['b'][:40]}", callback_data="admcorrect:B")],
        [InlineKeyboardButton(f"C) {nq['c'][:40]}", callback_data="admcorrect:C")],
        [InlineKeyboardButton(f"D) {nq['d'][:40]}", callback_data="admcorrect:D")],
    ]
    await update.message.reply_text(
        "Qaysi variant TO'G'RI javob?", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ADM_CORRECT


async def admin_get_correct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    letter = query.data.split(":", 1)[1]

    nq = context.user_data.get("new_q")
    if not nq:
        await query.edit_message_text("Xatolik: ma'lumot topilmadi. Qaytadan /menu orqali boshlang.")
        return ConversationHandler.END

    options = [nq["a"], nq["b"], nq["c"], nq["d"]]
    correct_text = {"A": nq["a"], "B": nq["b"], "C": nq["c"], "D": nq["d"]}[letter]

    add_question_to_bank(nq["grade"], nq["subject"], nq["topic"], nq["question"], options, correct_text)

    await query.edit_message_text(
        f"✅ Savol qo'shildi!\n\n"
        f"📚 {nq['grade']} — {nq['subject']} — {nq['topic']}\n"
        f"❓ {nq['question']}\n"
        f"✔️ To'g'ri javob: {correct_text}"
    )
    context.user_data.pop("new_q", None)

    buttons = [
        [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="begin_test")],
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Davom etamizmi?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_q", None)
    context.user_data.pop("edit_q", None)
    await update.message.reply_text("Savol qo'shish/tahrirlash bekor qilindi.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ADMIN: har bir savol tagidagi "✏️ Tahrirlash" tugmasi - savolni
# to'g'irlash yoki o'chirish (FAQAT ADMIN_PHONES ro'yxatidagilar uchun -
# tugmaning o'zi ham faqat adminga ko'rsatiladi, bu yerda esa yana bir bor
# ikkilamchi tekshiruv qilinadi, chunki eski/qayta yuborilgan callback
# orqali chetdan urinish bo'lishi mumkin).
# ---------------------------------------------------------------------------

EDQ_QUESTION, EDQ_A, EDQ_B, EDQ_C, EDQ_D, EDQ_CORRECT = range(11, 17)


def _current_quiz_question(context: ContextTypes.DEFAULT_TYPE, idx: int):
    """Joriy (yoki hali tugamagan) test sessiyasidagi `idx`-savolning aynan
    o'sha lug'at (dict) obyektini qaytaradi - topilmasa None."""
    quiz = context.user_data.get("quiz")
    if not quiz:
        return None
    questions = quiz.get("questions") or []
    if idx < 0 or idx >= len(questions):
        return None
    return quiz, questions[idx]


async def admin_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not user_is_admin(update.effective_user.id):
        await query.message.reply_text("Bu funksiya faqat adminlar uchun.")
        return

    idx = int(query.data.split(":", 1)[1])
    found = _current_quiz_question(context, idx)
    if not found:
        await query.message.reply_text("Bu savol endi mavjud emas (test yakunlangan yoki sessiya tugagan).")
        return
    _quiz, q = found

    preview = q["question"]
    if len(preview) > 250:
        preview = preview[:250] + "…"

    buttons = [
        [InlineKeyboardButton("✏️ Savol va javobni to'g'irlash", callback_data=f"admeditgo:{idx}")],
        [InlineKeyboardButton("🗑 Savolni o'chirish", callback_data=f"admdelq:{idx}")],
    ]
    await query.message.reply_text(
        f"✏️ Tahrirlash\n\n❓ {preview}\n\nNima qilmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def admin_delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not user_is_admin(update.effective_user.id):
        await query.message.reply_text("Bu funksiya faqat adminlar uchun.")
        return

    idx = int(query.data.split(":", 1)[1])
    found = _current_quiz_question(context, idx)
    if not found:
        await query.edit_message_text("Bu savol endi mavjud emas.")
        return
    quiz, target_q = found

    topic = find_question_topic(quiz["grade"], quiz["subject"], target_q)
    if not topic:
        await query.edit_message_text("Savol bazada topilmadi (allaqachon o'chirilgan bo'lishi mumkin).")
        return

    QUESTIONS[quiz["grade"]][quiz["subject"]][topic] = [
        q for q in QUESTIONS[quiz["grade"]][quiz["subject"]][topic] if q is not target_q
    ]
    save_questions_to_file()

    await query.edit_message_text(f"🗑 Savol butunlay o'chirildi:\n\n❓ {target_q['question']}")


async def admin_edit_q_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not user_is_admin(update.effective_user.id):
        await query.message.reply_text("Bu funksiya faqat adminlar uchun.")
        return ConversationHandler.END

    idx = int(query.data.split(":", 1)[1])
    found = _current_quiz_question(context, idx)
    if not found:
        await query.message.reply_text("Bu savol endi mavjud emas (test yakunlangan yoki sessiya tugagan).")
        return ConversationHandler.END
    quiz, target_q = found

    context.user_data["edit_q"] = {
        "grade": quiz["grade"],
        "subject": quiz["subject"],
        "target": target_q,
    }
    await query.message.reply_text(
        f"✏️ Savolni tahrirlash\n\nHozirgi savol matni:\n{target_q['question']}\n\n"
        "Yangi savol matnini yuboring (o'zgartirmoqchi bo'lmasangiz, xuddi shu matnni qayta yuboring):\n\n"
        "Istalgan vaqt bekor qilish uchun /admin_cancel yuboring."
    )
    return EDQ_QUESTION


async def admin_edit_get_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edit_q"]["question"] = update.message.text.strip()
    old = context.user_data["edit_q"]["target"]["options"]
    await update.message.reply_text(
        f"Eski A) {old[0] if len(old) > 0 else ''}\nA) variantini kiriting:"
    )
    return EDQ_A


async def admin_edit_get_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edit_q"]["a"] = update.message.text.strip()
    old = context.user_data["edit_q"]["target"]["options"]
    await update.message.reply_text(
        f"Eski B) {old[1] if len(old) > 1 else ''}\nB) variantini kiriting:"
    )
    return EDQ_B


async def admin_edit_get_b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edit_q"]["b"] = update.message.text.strip()
    old = context.user_data["edit_q"]["target"]["options"]
    await update.message.reply_text(
        f"Eski C) {old[2] if len(old) > 2 else ''}\nC) variantini kiriting:"
    )
    return EDQ_C


async def admin_edit_get_c(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edit_q"]["c"] = update.message.text.strip()
    old = context.user_data["edit_q"]["target"]["options"]
    await update.message.reply_text(
        f"Eski D) {old[3] if len(old) > 3 else ''}\nD) variantini kiriting:"
    )
    return EDQ_D


async def admin_edit_get_d(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["edit_q"]["d"] = update.message.text.strip()
    eq = context.user_data["edit_q"]

    buttons = [
        [InlineKeyboardButton(f"A) {eq['a'][:40]}", callback_data="edcorrect:A")],
        [InlineKeyboardButton(f"B) {eq['b'][:40]}", callback_data="edcorrect:B")],
        [InlineKeyboardButton(f"C) {eq['c'][:40]}", callback_data="edcorrect:C")],
        [InlineKeyboardButton(f"D) {eq['d'][:40]}", callback_data="edcorrect:D")],
    ]
    await update.message.reply_text(
        "Qaysi variant TO'G'RI javob?", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return EDQ_CORRECT


async def admin_edit_get_correct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    letter = query.data.split(":", 1)[1]

    eq = context.user_data.get("edit_q")
    if not eq:
        await query.edit_message_text("Xatolik: ma'lumot topilmadi. Qaytadan boshlang.")
        return ConversationHandler.END

    options = [eq["a"], eq["b"], eq["c"], eq["d"]]
    correct_text = {"A": eq["a"], "B": eq["b"], "C": eq["c"], "D": eq["d"]}[letter]

    # `target` - QUESTIONS bazasidagi savolning aynan o'zi (o'sha dict
    # obyekti) - shuni joyida yangilaymiz, shunda hech qanday qidiruvsiz
    # ham QUESTIONS avtomatik yangilangan bo'ladi.
    target_q = eq["target"]
    target_q.clear()
    target_q.update({"question": eq["question"], "options": options, "answer": correct_text})
    save_questions_to_file()

    await query.edit_message_text(
        "✅ Savol muvaffaqiyatli yangilandi!\n\n"
        f"❓ {eq['question']}\n"
        f"✔️ To'g'ri javob: {correct_text}"
    )
    context.user_data.pop("edit_q", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Umumiy
# ---------------------------------------------------------------------------

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_start_button(update.effective_chat.id, context)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Tushunmadim. /menu buyrug'ini yuboring.")


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit(
            "BOT_TOKEN muhit o'zgaruvchisini o'rnating (yoki bot.py faylida to'g'ridan-to'g'ri yozing)."
        )

    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern=r"^admin_add$")],
        states={
            ADM_GRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_grade)],
            ADM_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_subject)],
            ADM_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_topic)],
            ADM_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_question)],
            ADM_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_a)],
            ADM_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_b)],
            ADM_C: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_c)],
            ADM_D: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_d)],
            ADM_CORRECT: [CallbackQueryHandler(admin_get_correct, pattern=r"^admcorrect:[ABCD]$")],
        },
        fallbacks=[CommandHandler("admin_cancel", admin_cancel)],
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_q_start, pattern=r"^admeditgo:\d+$")],
        states={
            EDQ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_get_question)],
            EDQ_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_get_a)],
            EDQ_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_get_b)],
            EDQ_C: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_get_c)],
            EDQ_D: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_get_d)],
            EDQ_CORRECT: [CallbackQueryHandler(admin_edit_get_correct, pattern=r"^edcorrect:[ABCD]$")],
        },
        fallbacks=[CommandHandler("admin_cancel", admin_cancel)],
    )

    application.add_handler(registration_conv)
    application.add_handler(admin_conv)
    application.add_handler(edit_conv)
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("stop", stop_command))

    application.add_handler(CallbackQueryHandler(begin_test, pattern=r"^begin_test$"))
    application.add_handler(CallbackQueryHandler(back_to_grades, pattern=r"^backg$"))
    application.add_handler(CallbackQueryHandler(grade_chosen, pattern=r"^g:\d+$"))
    application.add_handler(CallbackQueryHandler(subject_chosen, pattern=r"^s:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(topic_chosen, pattern=r"^t:\d+:\d+:-?\d+$"))
    application.add_handler(CallbackQueryHandler(run_quiz, pattern=r"^run_quiz$"))
    application.add_handler(CallbackQueryHandler(finish_quiz_button, pattern=r"^finish_quiz_btn$"))
    application.add_handler(CallbackQueryHandler(admin_edit_menu, pattern=r"^admeditmenu:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_delete_question, pattern=r"^admdelq:\d+$"))

    application.add_handler(PollAnswerHandler(receive_poll_answer))

    application.add_handler(MessageHandler(filters.ALL, unknown))

    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()