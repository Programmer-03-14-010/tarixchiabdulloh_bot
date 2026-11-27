# -*- coding: utf-8 -*-
"""
Telegram bot: ro'yxatdan o'tkazadi va "Ilovani ochish" tugmasini chiqaradi.
Barcha test/admin funksiyalari endi Mini App (static/) ichida.
"""
import logging

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, MenuButtonWebApp,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, WebAppInfo,
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters,
)

import config
import db

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_NAME, ASK_PHONE = range(2)


def open_app_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("📖 Ilovani ochish", web_app=WebAppInfo(url=config.WEBAPP_URL))]])


async def send_open_button(chat_id: int, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if not config.WEBAPP_URL:
        await context.bot.send_message(chat_id, "⚠️ WEBAPP_URL sozlanmagan. Administratorga xabar bering.")
        return
    await context.bot.send_message(chat_id, text, reply_markup=open_app_markup())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if db.is_registered(user.id):
        row = db.get_user(user.id)
        await send_open_button(
            update.effective_chat.id, context,
            f"Xush kelibsiz, {row['full_name']}! 👋\n\nTarix fanidan bilimingizni sinash uchun ilovani oching 👇",
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\nUshbu bot tarix fanidan bilimingizni oshirishga yordam beradi.\n"
        "Boshlash uchun avval ro'yxatdan o'tamiz.\n\nIsm va familyangizni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("Iltimos, ism va familyangizni to'liq kiriting (masalan: Ali Valiyev):")
        return ASK_NAME
    context.user_data["full_name"] = name
    markup = ReplyKeyboardMarkup([[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
                                 resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(f"Rahmat, {name}!\n\nEndi telefon raqamingizni yuboring:", reply_markup=markup)
    return ASK_PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Iltimos, pastdagi tugma orqali telefon raqamingizni yuboring.")
        return ASK_PHONE
    user = update.effective_user
    # keep_name=False: foydalanuvchi kiritgan ism-familya Telegram profilidagi nomdan ustun.
    db.save_user(user.id, context.user_data.get("full_name", user.full_name), contact.phone_number,
                 user.username or "", keep_name=False)
    await update.message.reply_text("Ro'yxatdan muvaffaqiyatli o'tdingiz! ✅", reply_markup=ReplyKeyboardRemove())
    await send_open_button(update.effective_chat.id, context, "Ilovani ochish uchun tugmani bosing 👇")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Bekor qilindi. Qaytadan boshlash uchun /start ni bosing.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if db.is_registered(update.effective_user.id):
        await send_open_button(update.effective_chat.id, context, "Ilovani ochish 👇")
    else:
        await update.message.reply_text("Avval /start orqali ro'yxatdan o'ting.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Ilovani ochish uchun /start ni yuboring.")


async def post_init(application: Application) -> None:
    # Chat pastidagi menyu tugmasi ham ilovani ochadi
    if config.WEBAPP_URL:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Ilova", web_app=WebAppInfo(url=config.WEBAPP_URL)))


def run_bot() -> None:
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    reg = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(reg)
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(MessageHandler(filters.ALL, unknown))
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
