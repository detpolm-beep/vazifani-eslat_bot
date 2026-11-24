import logging
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Konfiguratsiya ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
_admin_env = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable o'rnatilmagan!")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = "reminders.json"
USERS_FILE = "users.json"

# Ro'yxatdan o'tish holatlari
REG_NAME, REG_SURNAME, REG_CLASS, REG_AGE = range(4)
# Vazifa qo'shish holatlari
TASK_TEXT, TASK_TIME = range(4, 6)


# --- Ma'lumotlar ---

def load_reminders():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_reminders(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_registered(user_id: int) -> bool:
    users = load_users()
    return str(user_id) in users


def get_main_keyboard(user_id: int):
    if is_admin(user_id):
        keyboard = [
            ["➕ Vazifa qo'shish", "📋 Vazifalarim"],
            ["🗑 Vazifa o'chirish", "ℹ️ Yordam"]
        ]
    else:
        keyboard = [
            ["📋 Vazifalarim", "ℹ️ Yordam"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --- Ro'yxatdan o'tish ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_registered(user_id):
        users = load_users()
        user = users[str(user_id)]
        await update.message.reply_text(
            f"👋 Xush kelibsiz, *{user['name']} {user['surname']}*!\n\n"
            f"🏫 Stanford School maktabi vazifa eslatuvchi botiga xush kelibsiz!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id)
        )
        return

    await update.message.reply_text(
        "🏫 *Stanford School* maktabining vazifa eslatuvchi botiga xush kelibsiz!\n\n"
        "Davom etish uchun ro'yxatdan o'tishingiz kerak.\n\n"
        "👤 *Ismingizni* kiriting:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Ism juda qisqa! Qayta kiriting:")
        return REG_NAME
    context.user_data["reg_name"] = name
    await update.message.reply_text(f"✅ Ism: *{name}*\n\n👤 *Familiyangizni* kiriting:", parse_mode="Markdown")
    return REG_SURNAME


async def reg_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text.strip()
    if len(surname) < 2:
        await update.message.reply_text("❌ Familiya juda qisqa! Qayta kiriting:")
        return REG_SURNAME
    context.user_data["reg_surname"] = surname
    await update.message.reply_text(
        f"✅ Familiya: *{surname}*\n\n🏫 *Sinfingizni* kiriting:\n"
        "Misol: `5A`, `9B`, `11V`",
        parse_mode="Markdown"
    )
    return REG_CLASS


async def reg_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    school_class = update.message.text.strip().upper()
    if len(school_class) < 2:
        await update.message.reply_text("❌ Sinf noto'g'ri! Qayta kiriting (misol: 5A):")
        return REG_CLASS
    context.user_data["reg_class"] = school_class
    await update.message.reply_text(
        f"✅ Sinf: *{school_class}*\n\n🎂 *Yoshingizni* kiriting (raqamda):",
        parse_mode="Markdown"
    )
    return REG_AGE


async def reg_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_text = update.message.text.strip()
    if not age_text.isdigit() or not (5 <= int(age_text) <= 20):
        await update.message.reply_text("❌ Yosh 5 dan 20 gacha bo'lishi kerak! Qayta kiriting:")
        return REG_AGE

    user_id = str(update.effective_user.id)
    users = load_users()
    users[user_id] = {
        "name": context.user_data["reg_name"],
        "surname": context.user_data["reg_surname"],
        "class": context.user_data["reg_class"],
        "age": int(age_text),
        "joined": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "telegram_id": user_id
    }
    save_users(users)

    await update.message.reply_text(
        f"🎉 *Ro'yxatdan o'tish muvaffaqiyatli!*\n\n"
        f"👤 Ism: {users[user_id]['name']} {users[user_id]['surname']}\n"
        f"🏫 Sinf: {users[user_id]['class']}\n"
        f"🎂 Yosh: {users[user_id]['age']}\n\n"
        f"🏫 Stanford School botiga xush kelibsiz!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(int(user_id))
    )
    return ConversationHandler.END


# --- Yordam ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Buyruqlar:*\n\n"
        "📋 *Vazifalarim* — barcha vazifalarni ko'rish\n"
        "ℹ️ *Yordam* — ushbu yordam xabari\n\n"
        "⏰ Vaqt formati: `HH:MM` (masalan `09:30`)\n"
        "📅 Kun formati: `kunlik` yoki `DD.MM.YYYY`\n\n"
        "🏫 *Stanford School*",
        parse_mode="Markdown"
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_users()
    info = users.get(str(user.id), {})
    text = (
        f"👤 *Ma'lumotlaringiz:*\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"👤 Ism: {user.first_name}\n"
    )
    if info:
        text += (
            f"📛 To'liq ism: {info['name']} {info['surname']}\n"
            f"🏫 Sinf: {info['class']}\n"
            f"🎂 Yosh: {info['age']}\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


# --- Admin buyruqlar ---

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sizda admin huquqi yo'q!")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📭 Hech qanday foydalanuvchi yo'q.")
        return

    text = f"👥 *Ro'yxatdan o'tgan o'quvchilar: {len(users)} ta*\n\n"
    for uid, u in users.items():
        text += f"👤 {u['name']} {u['surname']} | {u['class']} sinf | {u['age']} yosh\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sizda admin huquqi yo'q!")
        return

    if not context.args:
        await update.message.reply_text(
            "📢 Foydalanish: `/broadcast Salom barchaga!`",
            parse_mode="Markdown"
        )
        return

    message = " ".join(context.args)
    users = load_users()
    success, failed = 0, 0

    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"📢 *Stanford School xabari:*\n\n{message}",
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Yuborildi: {success} ta\n❌ Yuborilmadi: {failed} ta"
    )


# --- Vazifa qo'shish (faqat admin) ---

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Vazifa faqat admin tomonidan qo'shiladi!")
        return ConversationHandler.END
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

    # Admin o'z vazifalarini ko'radi, oddiy foydalanuvchi admin vazifalarini ko'radi
    if is_admin(int(user_id)):
        tasks = reminders.get(user_id, [])
    else:
        # Barcha admin vazifalarini ko'rsat
        tasks = []
        for admin_id in ADMIN_IDS:
            tasks += reminders.get(str(admin_id), [])

    if not tasks:
        await update.message.reply_text("📭 Hozircha vazifalar yo'q.")
        return

    text = "📋 *Vazifalar:*\n\n"
    for task in tasks:
        text += f"🔹 *{task['id']}.* {task['text']}\n"
        text += f"   ⏰ {task['display_time']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# --- Vazifa o'chirish ---

async def delete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Vazifa faqat admin tomonidan o'chiriladi!")
        return

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


# --- Xabarlar ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Ro'yxatdan o'tmagan bo'lsa
    if not is_registered(user_id) and not is_admin(user_id):
        await update.message.reply_text(
            "⚠️ Avval ro'yxatdan o'ting!\n/start buyrug'ini bosing."
        )
        return

    if context.user_data.get("deleting"):
        context.user_data["deleting"] = False
        uid = str(user_id)
        reminders = load_reminders()
        tasks = reminders.get(uid, [])

        new_tasks = [t for t in tasks if t["id"] != text.strip()]
        if len(new_tasks) == len(tasks):
            await update.message.reply_text("❌ Bunday raqamli vazifa topilmadi.")
        else:
            for i, t in enumerate(new_tasks, 1):
                t["id"] = str(i)
            reminders[uid] = new_tasks
            save_reminders(reminders)
            await update.message.reply_text("✅ Vazifa o'chirildi!")
        return

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
        # Barcha ro'yxatdan o'tgan foydalanuvchilarga yuborish
        users = load_users()
        for uid in users:
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text=f"🔔 *Stanford School eslatmasi!*\n\n📌 {task['text']}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Xabar yuborishda xato {uid}: {e}")

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
    reminders = load_reminders()
    for user_id, tasks in reminders.items():
        for task in tasks:
            schedule_reminder(app.scheduler, app, user_id, task)
    users = load_users()
    logger.info(f"{sum(len(t) for t in reminders.values())} ta vazifa, {len(users)} ta foydalanuvchi yuklandi")


# --- Asosiy ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    scheduler = AsyncIOScheduler()
    app.scheduler = scheduler

    # Ro'yxatdan o'tish
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_surname)],
            REG_CLASS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_class)],
            REG_AGE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_age)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Vazifa qo'shish
    task_handler = ConversationHandler(
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

    app.add_handler(reg_handler)
    app.add_handler(task_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = on_startup

    scheduler.start()
    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
