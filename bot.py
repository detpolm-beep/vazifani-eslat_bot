import logging
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = "reminders.json"

# ConversationHandler holatlari
TASK_TEXT, TASK_TIME = range(2)


def load_reminders():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_reminders(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Buyruqlar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ Vazifa qo'shish", "📋 Vazifalarim"],
        ["🗑 Vazifa o'chirish", "ℹ️ Yordam"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Salom! Men vazifa eslatuvchi botman.\n\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Buyruqlar:*\n\n"
        "➕ *Vazifa qo'shish* — yangi eslatma qo'shish\n"
        "📋 *Vazifalarim* — barcha vazifalarni ko'rish\n"
        "🗑 *Vazifa o'chirish* — vazifani o'chirish\n\n"
        "⏰ Vaqt formati: `HH:MM` (masalan `09:30`)\n"
        "📅 Kun formati: `kunlik` yoki `DD.MM.YYYY`",
        parse_mode="Markdown"
    )


# --- Vazifa qo'shish (ConversationHandler) ---

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Vazifa matnini yozing:\n\n"
        "(Bekor qilish uchun /cancel)"
    )
    return TASK_TEXT


async def add_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_text"] = update.message.text
    await update.message.reply_text(
        "⏰ Eslatish vaqtini kiriting:\n\n"
        "Format: `HH:MM` yoki `HH:MM DD.MM.YYYY`\n"
        "Misol: `09:00` (har kuni) yoki `14:30 25.11.2026`",
        parse_mode="Markdown"
    )
    return TASK_TIME


async def add_task_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        parts = time_text.split()
        time_part = parts[0]
        hour, minute = map(int, time_part.split(":"))

        if len(parts) == 2:
            date_part = parts[1]
            day, month, year = map(int, date_part.split("."))
            run_date = datetime(year, month, day, hour, minute)
            schedule_type = "once"
            display_time = f"{time_part} {date_part}"
        else:
            run_date = None
            schedule_type = "daily"
            display_time = f"Har kuni {time_part}"

    except Exception:
        await update.message.reply_text(
            "❌ Noto'g'ri format! Qayta kiriting:\n"
            "`09:00` yoki `14:30 25.11.2026`",
            parse_mode="Markdown"
        )
        return TASK_TIME

    reminders = load_reminders()
    if user_id not in reminders:
        reminders[user_id] = []

    task_id = str(len(reminders[user_id]) + 1)
    task = {
        "id": task_id,
        "text": context.user_data["task_text"],
        "time": time_part,
        "type": schedule_type,
        "display_time": display_time,
        "created": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    if run_date:
        task["date"] = run_date.strftime("%d.%m.%Y")

    reminders[user_id].append(task)
    save_reminders(reminders)

    # Schedulerga qo'shish
    scheduler = context.application.scheduler
    schedule_reminder(scheduler, context.application, user_id, task)

    await update.message.reply_text(
        f"✅ Vazifa qo'shildi!\n\n"
        f"📌 *{task['text']}*\n"
        f"⏰ {display_time}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# --- Vazifalarni ko'rish ---

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reminders = load_reminders()
    tasks = reminders.get(user_id, [])

    if not tasks:
        await update.message.reply_text("📭 Sizda hozircha vazifalar yo'q.")
        return

    text = "📋 *Sizning vazifalaringiz:*\n\n"
    for task in tasks:
        text += f"🔹 *{task['id']}.* {task['text']}\n"
        text += f"   ⏰ {task['display_time']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# --- Vazifa o'chirish ---

async def delete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reminders = load_reminders()
    tasks = reminders.get(user_id, [])

    if not tasks:
        await update.message.reply_text("📭 O'chiriladigan vazifalar yo'q.")
        return

    text = "🗑 *Qaysi vazifani o'chirish?*\n\nRaqamini yozing:\n\n"
    for task in tasks:
        text += f"*{task['id']}.* {task['text']} — {task['display_time']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data["deleting"] = True


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if context.user_data.get("deleting"):
        context.user_data["deleting"] = False
        user_id = str(update.effective_user.id)
        reminders = load_reminders()
        tasks = reminders.get(user_id, [])

        new_tasks = [t for t in tasks if t["id"] != text.strip()]
        if len(new_tasks) == len(tasks):
            await update.message.reply_text("❌ Bunday raqamli vazifa topilmadi.")
        else:
            # ID larni qayta raqamlash
            for i, t in enumerate(new_tasks, 1):
                t["id"] = str(i)
            reminders[user_id] = new_tasks
            save_reminders(reminders)
            await update.message.reply_text("✅ Vazifa o'chirildi!")
        return

    # Tugmalar
    if text == "➕ Vazifa qo'shish":
        await add_task_start(update, context)
    elif text == "📋 Vazifalarim":
        await list_tasks(update, context)
    elif text == "🗑 Vazifa o'chirish":
        await delete_task_start(update, context)
    elif text == "ℹ️ Yordam":
        await help_command(update, context)


# --- Scheduler ---

def schedule_reminder(scheduler, app, user_id, task):
    job_id = f"{user_id}_{task['id']}"
    hour, minute = map(int, task["time"].split(":"))

    async def send_reminder():
        try:
            await app.bot.send_message(
                chat_id=int(user_id),
                text=f"🔔 *Eslatma!*\n\n📌 {task['text']}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Xabar yuborishda xato: {e}")

    if task["type"] == "daily":
        scheduler.add_job(
            send_reminder,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True
        )
    elif task["type"] == "once" and task.get("date"):
        day, month, year = map(int, task["date"].split("."))
        run_date = datetime(year, month, day, hour, minute)
        if run_date > datetime.now():
            scheduler.add_job(
                send_reminder,
                trigger="date",
                run_date=run_date,
                id=job_id,
                replace_existing=True
            )


async def on_startup(app):
    """Bot ishga tushganda mavjud vazifalarni schedulerga yuklash"""
    reminders = load_reminders()
    for user_id, tasks in reminders.items():
        for task in tasks:
            schedule_reminder(app.scheduler, app, user_id, task)
    logger.info(f"{sum(len(t) for t in reminders.values())} ta vazifa yuklandi")


# --- Asosiy ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Scheduler ulash
    scheduler = AsyncIOScheduler()
    app.scheduler = scheduler

    # ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Vazifa qo'shish$"), add_task_start),
            CommandHandler("add", add_task_start)
        ],
        states={
            TASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_text)],
            TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = on_startup

    scheduler.start()
    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
