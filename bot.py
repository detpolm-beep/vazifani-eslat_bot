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
TASK_SUBJECT, TASK_CLASS, TASK_DESC, TASK_DEADLINE = range(4, 8)

# O'quvchi vazifa ko'rish holati
VIEW_SUBJECT = 8

SUBJECTS = [
    "📐 Matematika", "📖 Ona tili", "🌍 Ingliz tili",
    "🔬 Fizika", "⚗️ Kimyo", "🧬 Biologiya",
    "🗺️ Geografiya", "📜 Tarix", "💻 Informatika",
    "🎨 Chizmachilik", "⚽ Jismoniy tarbiya", "🎵 Musiqa"
]


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
            ["📚 Vazifa berish", "📋 Vazifalar"],
            ["👥 O'quvchilar", "📊 Statistika"],
            ["📢 Xabar yuborish", "🗑 Vazifa o'chirish"],
            ["⚙️ Admin panel", "ℹ️ Yordam"]
        ]
    else:
        keyboard = [
            ["📋 Vazifalarim", "ℹ️ Yordam"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --- Ro'yxatdan o'tish ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_registered(user_id) or is_admin(user_id):
        users = load_users()
        user = users.get(str(user_id), {})
        name = user.get("name", "Admin") if user else "Admin"
        surname = user.get("surname", "") if user else ""
        await update.message.reply_text(
            f"👋 Xush kelibsiz, *{name} {surname}*!\n\n"
            f"🏫 *Stanford School* vazifa botiga xush kelibsiz!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🏫 *Stanford School*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *Bu bot nima qiladi?*\n\n"
        "✅ Maktab o'qituvchilari tomonidan\n"
        "   berilgan uy vazifalarini ko'rasiz\n\n"
        "✅ Har bir fan bo'yicha vazifalar\n"
        "   va topshirish muddati ko'rsatiladi\n\n"
        "✅ Yangi vazifa berilganda\n"
        "   darhol xabardor bo'lasiz\n\n"
        "✅ O'z sinfingiz vazifalarini\n"
        "   istalgan vaqt ko'rishingiz mumkin\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 *Created by:* Meleboyev Tohirbek | 7-B\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Davom etish uchun ro'yxatdan o'ting 👇\n\n"
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
    await update.message.reply_text(
        f"✅ Ism: *{name}*\n\n👤 *Familiyangizni* kiriting:",
        parse_mode="Markdown"
    )
    return REG_SURNAME


async def reg_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text.strip()
    if len(surname) < 2:
        await update.message.reply_text("❌ Familiya juda qisqa! Qayta kiriting:")
        return REG_SURNAME
    context.user_data["reg_surname"] = surname
    await update.message.reply_text(
        f"✅ Familiya: *{surname}*\n\n"
        f"🏫 *Sinfingizni* kiriting:\n"
        f"Misol: `5A`, `9B`, `11V`",
        parse_mode="Markdown"
    )
    return REG_CLASS


async def reg_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    school_class = update.message.text.strip().upper()
    if len(school_class) < 2:
        await update.message.reply_text("❌ Sinf noto'g'ri! Misol: `5A`", parse_mode="Markdown")
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
        await update.message.reply_text("❌ Yosh 5 dan 20 gacha bo'lishi kerak!")
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
        f"👤 {users[user_id]['name']} {users[user_id]['surname']}\n"
        f"🏫 Sinf: {users[user_id]['class']}\n"
        f"🎂 Yosh: {users[user_id]['age']}\n\n"
        f"🏫 Stanford School botiga xush kelibsiz!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(int(user_id))
    )
    return ConversationHandler.END


# --- Vazifa qo'shish (Admin) ---

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Vazifa faqat admin tomonidan beriladi!")
        return ConversationHandler.END

    keyboard = [[s] for s in SUBJECTS]
    keyboard.append(["❌ Bekor qilish"])
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📚 *YANGI VAZIFA BERISH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Fanni tanlang 👇",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return TASK_SUBJECT


async def add_task_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text.strip()
    if subject == "❌ Bekor qilish":
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    context.user_data["task_subject"] = subject

    # Sinf tanlash
    keyboard = [
        ["1A", "1B", "2A", "2B"],
        ["3A", "3B", "4A", "4B"],
        ["5A", "5B", "6A", "6B"],
        ["7A", "7B", "8A", "8B"],
        ["9A", "9B", "10A", "10B"],
        ["11A", "11B", "🏫 Barcha sinflar"],
        ["❌ Bekor qilish"]
    ]
    await update.message.reply_text(
        f"✅ Fan: *{subject}*\n\n🏫 *Qaysi sinf uchun?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return TASK_CLASS


async def add_task_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_class = update.message.text.strip()
    if target_class == "❌ Bekor qilish":
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=get_main_keyboard(update.effective_user.id))
        return ConversationHandler.END

    context.user_data["task_class"] = target_class
    await update.message.reply_text(
        f"✅ Sinf: *{target_class}*\n\n"
        f"📝 *Vazifa mazmunini* yozing:\n\n"
        f"Misol: Sahifa 45-50 mashqlarini bajaring",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return TASK_DESC


async def add_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["task_desc"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Vazifa yozildi.\n\n"
        f"📅 *Topshirish muddatini* kiriting:\n\n"
        f"Format: `DD.MM.YYYY` yoki `ertaga` yoki `bugun`\n"
        f"Misol: `25.11.2026`",
        parse_mode="Markdown"
    )
    return TASK_DEADLINE


async def add_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadline_text = update.message.text.strip().lower()
    user_id = str(update.effective_user.id)

    today = datetime.now()
    if deadline_text == "bugun":
        deadline = today.strftime("%d.%m.%Y")
    elif deadline_text == "ertaga":
        from datetime import timedelta
        deadline = (today + timedelta(days=1)).strftime("%d.%m.%Y")
    else:
        try:
            day, month, year = map(int, deadline_text.split("."))
            deadline = f"{day:02d}.{month:02d}.{year}"
        except Exception:
            await update.message.reply_text(
                "❌ Noto'g'ri format! Misol: `25.11.2026`",
                parse_mode="Markdown"
            )
            return TASK_DEADLINE

    subject = context.user_data["task_subject"]
    target_class = context.user_data["task_class"]
    desc = context.user_data["task_desc"]

    reminders = load_reminders()
    if "tasks" not in reminders:
        reminders["tasks"] = []

    task_id = str(len(reminders["tasks"]) + 1)
    task = {
        "id": task_id,
        "subject": subject,
        "class": target_class,
        "desc": desc,
        "deadline": deadline,
        "created": today.strftime("%d.%m.%Y %H:%M"),
        "created_by": user_id
    }
    reminders["tasks"].append(task)
    save_reminders(reminders)

    # O'quvchilarga xabar yuborish
    await notify_students(context.application, task)

    await update.message.reply_text(
        f"✅ *Vazifa muvaffaqiyatli berildi!*\n\n"
        f"📚 Fan: {subject}\n"
        f"🏫 Sinf: {target_class}\n"
        f"📝 Vazifa: {desc}\n"
        f"📅 Muddat: {deadline}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(int(user_id))
    )
    return ConversationHandler.END


async def notify_students(app, task):
    """Vazifa berilganda tegishli o'quvchilarga xabar yuborish"""
    users = load_users()
    for uid, user in users.items():
        if task["class"] == "🏫 Barcha sinflar" or user["class"] == task["class"]:
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text=f"📚 *Yangi uy vazifasi!*\n\n"
                         f"📖 Fan: {task['subject']}\n"
                         f"🏫 Sinf: {task['class']}\n"
                         f"📝 Vazifa: {task['desc']}\n"
                         f"📅 Muddat: {task['deadline']}\n\n"
                         f"🏫 Stanford School",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Xabar yuborishda xato {uid}: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Bekor qilindi.",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END


# --- Vazifalarni ko'rish (fan tanlash bilan) ---

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_users()
    user = users.get(str(user_id), {})

    if is_admin(user_id):
        # Admin uchun ham fan tanlash
        keyboard = [[s] for s in SUBJECTS]
        keyboard.append(["📋 Barcha fanlar"])
        keyboard.append(["🔙 Orqaga"])
        await update.message.reply_text(
            "📚 *Qaysi fanning vazifalarini ko'rish?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        # O'quvchi uchun fan tanlash
        user_class = user.get("class", "")
        reminders = load_reminders()
        tasks = reminders.get("tasks", [])
        # Faqat shu sinfga tegishli fanlarni chiqar
        my_tasks = [t for t in tasks if t["class"] == user_class or t["class"] == "🏫 Barcha sinflar"]
        available_subjects = list({t["subject"] for t in my_tasks})

        if not available_subjects:
            await update.message.reply_text(
                "📭 *Hozircha sizning sinfingiz uchun vazifa yo'q.*",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

        keyboard = [[s] for s in sorted(available_subjects)]
        keyboard.append(["📋 Barcha fanlar"])
        keyboard.append(["🔙 Orqaga"])
        await update.message.reply_text(
            f"📚 *{user_class} sinfi — fan tanlang:*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    return VIEW_SUBJECT


async def view_subject_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "🔙 Orqaga":
        await update.message.reply_text(
            "🏠 Asosiy menyu",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END

    users = load_users()
    user = users.get(str(user_id), {})
    user_class = user.get("class", "") if user else ""

    reminders = load_reminders()
    tasks = reminders.get("tasks", [])

    # Sinfga qarab filtrlash
    if is_admin(user_id):
        class_tasks = tasks
    else:
        class_tasks = [t for t in tasks if t["class"] == user_class or t["class"] == "🏫 Barcha sinflar"]

    # Fanga qarab filtrlash
    if text == "📋 Barcha fanlar":
        filtered = class_tasks
        title = "📋 *Barcha fanlar vazifalari:*"
    else:
        filtered = [t for t in class_tasks if t["subject"] == text]
        title = f"📚 *{text} — vazifalar:*"

    if not filtered:
        await update.message.reply_text(
            f"📭 *{text}* dan hozircha vazifa yo'q.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END

    result = title + "\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, task in enumerate(filtered, 1):
        result += (
            f"*{i}.* {task['subject']}\n"
            f"🏫 Sinf: {task['class']}\n"
            f"📝 {task['desc']}\n"
            f"📅 Muddat: *{task['deadline']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END


# --- Vazifa o'chirish ---

async def delete_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Faqat admin o'chira oladi!")
        return

    reminders = load_reminders()
    tasks = reminders.get("tasks", [])

    if not tasks:
        await update.message.reply_text("📭 O'chiriladigan vazifalar yo'q.")
        return

    text = "🗑 *Qaysi vazifani o'chirish?*\n\nRaqamini yozing:\n\n"
    for task in tasks:
        text += f"*{task['id']}.* {task['subject']} | {task['class']} | {task['deadline']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data["deleting"] = True


# --- Admin: o'quvchilar ro'yxati ---

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sizda admin huquqi yo'q!")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📭 Hech qanday o'quvchi yo'q.")
        return

    text = f"👥 *Ro'yxatdan o'tgan o'quvchilar: {len(users)} ta*\n\n"
    for uid, u in users.items():
        text += f"👤 {u['name']} {u['surname']} | {u['class']} | {u['age']} yosh\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# --- Admin: broadcast ---

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


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_users()
    info = users.get(str(user.id), {})
    text = f"🆔 ID: `{user.id}`\n"
    if info:
        text += (
            f"👤 {info['name']} {info['surname']}\n"
            f"🏫 Sinf: {info['class']}\n"
            f"🎂 Yosh: {info['age']}\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Ruxsat yo'q!")
        return

    user = update.effective_user
    users = load_users()
    reminders = load_reminders()
    tasks = reminders.get("tasks", [])
    today = datetime.now().strftime("%d.%m.%Y")

    admin_info = users.get(str(user.id), {})
    admin_name = admin_info.get("name", user.first_name) if admin_info else user.first_name

    text = (
        f"👋 Salom, *{admin_name}*!\n"
        f"⚙️ Admin panelga xush kelibsiz!\n\n"
        "╔══════════════════════╗\n"
        "║   🏫  ADMIN PANEL    ║\n"
        "║   Stanford School    ║\n"
        "╚══════════════════════╝\n\n"
        f"👥 Jami o'quvchilar: *{len(users)}* ta\n"
        f"📚 Jami vazifalar: *{len(tasks)}* ta\n"
        f"📅 Bugungi sana: *{today}*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Mavjud buyruqlar:*\n\n"
        "📚 *Vazifa berish* — yangi vazifa qo'shish\n"
        "📋 *Vazifalar* — barcha vazifalarni ko'rish\n"
        "👥 *O'quvchilar* — ro'yxatdagi o'quvchilar\n"
        "📊 *Statistika* — batafsil ma'lumot\n"
        "📢 *Xabar yuborish* — hammaga xabar\n"
        "🗑 *Vazifa o'chirish* — vazifani o'chirish\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 *Created by:* Meleboyev Tohirbek | 7-B"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Ruxsat yo'q!")
        return

    users = load_users()
    reminders = load_reminders()
    tasks = reminders.get("tasks", [])

    # Sinflar bo'yicha hisoblash
    class_count = {}
    for u in users.values():
        c = u.get("class", "Noma'lum")
        class_count[c] = class_count.get(c, 0) + 1

    # Fanlar bo'yicha vazifalar
    subject_count = {}
    for t in tasks:
        s = t.get("subject", "Noma'lum")
        subject_count[s] = subject_count.get(s, 0) + 1

    text = (
        "📊 *STATISTIKA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *O'quvchilar:* {len(users)} ta\n"
        f"📚 *Jami vazifalar:* {len(tasks)} ta\n\n"
    )

    if class_count:
        text += "🏫 *Sinflar bo'yicha:*\n"
        for cls, cnt in sorted(class_count.items()):
            text += f"  • {cls}: {cnt} ta o'quvchi\n"
        text += "\n"

    if subject_count:
        text += "📖 *Fanlar bo'yicha vazifalar:*\n"
        for subj, cnt in sorted(subject_count.items(), key=lambda x: -x[1]):
            text += f"  • {subj}: {cnt} ta\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_text(text, parse_mode="Markdown")



    user = update.effective_user
    users = load_users()
    info = users.get(str(user.id), {})
    text = f"🆔 ID: `{user.id}`\n"
    if info:
        text += (
            f"👤 {info['name']} {info['surname']}\n"
            f"🏫 Sinf: {info['class']}\n"
            f"🎂 Yosh: {info['age']}\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Stanford School vazifa boti*\n\n"
        "📋 *Vazifalarim* — o'z sinfi vazifalarini ko'rish\n"
        "ℹ️ *Yordam* — yordam\n\n"
        "🏫 Stanford School",
        parse_mode="Markdown"
    )


# --- Xabarlar ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not is_registered(user_id) and not is_admin(user_id):
        await update.message.reply_text(
            "⚠️ Avval ro'yxatdan o'ting!\n/start buyrug'ini bosing."
        )
        return

    if context.user_data.get("deleting"):
        context.user_data["deleting"] = False
        reminders = load_reminders()
        tasks = reminders.get("tasks", [])
        new_tasks = [t for t in tasks if t["id"] != text.strip()]
        if len(new_tasks) == len(tasks):
            await update.message.reply_text("❌ Bunday raqamli vazifa topilmadi.")
        else:
            for i, t in enumerate(new_tasks, 1):
                t["id"] = str(i)
            reminders["tasks"] = new_tasks
            save_reminders(reminders)
            await update.message.reply_text("✅ Vazifa o'chirildi!")
        return

    if text in ["📚 Vazifa berish"]:
        await add_task_start(update, context)
    elif text == "🗑 Vazifa o'chirish":
        await delete_task_start(update, context)
    elif text == "👥 O'quvchilar":
        await admin_users(update, context)
    elif text == "📊 Statistika":
        await admin_stats(update, context)
    elif text == "⚙️ Admin panel":
        await admin_panel(update, context)
    elif text == "📢 Xabar yuborish":
        await update.message.reply_text(
            "📢 Foydalanish: `/broadcast matn`",
            parse_mode="Markdown"
        )
    elif text == "ℹ️ Yordam":
        await help_command(update, context)


async def on_startup(app):
    users = load_users()
    reminders = load_reminders()
    tasks = reminders.get("tasks", [])
    logger.info(f"{len(tasks)} ta vazifa, {len(users)} ta o'quvchi yuklandi")


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

    # Vazifa berish
    task_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📚 Vazifa berish$"), add_task_start),
            CommandHandler("add", add_task_start)
        ],
        states={
            TASK_SUBJECT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_subject)],
            TASK_CLASS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_class)],
            TASK_DESC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_desc)],
            TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_deadline)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Vazifalarni ko'rish (fan tanlash)
    view_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📋 Vazifalarim$|^📋 Vazifalar$"), list_tasks),
            CommandHandler("list", list_tasks)
        ],
        states={
            VIEW_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_subject_tasks)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(reg_handler)
    app.add_handler(task_handler)
    app.add_handler(view_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("panel", admin_panel))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = on_startup

    scheduler.start()
    logger.info("Stanford School boti ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
