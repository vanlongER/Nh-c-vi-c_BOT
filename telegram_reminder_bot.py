"""
🔔 Telegram Task Reminder Bot v2
=================================
Bot nhắc việc qua Telegram với các tùy chọn:
- ✅ Đã hoàn thành
- 📊 Đã làm được 1 phần (cập nhật tiến độ)
- ⏰ Nhắc lại sau (chọn thời gian)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMINDER_TIMES = ["08:00", "20:00"]
DATA_FILE = "tasks_data.json"
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ── Data ─────────────────────────────────────────────────────
def load_data() -> dict:
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_tasks(user_id: str) -> list:
    return load_data().get(user_id, [])


def save_user_tasks(user_id: str, tasks: list):
    data = load_data()
    data[user_id] = tasks
    save_data(data)


# ── Keyboards ────────────────────────────────────────────────
def build_task_list_keyboard(tasks: list):
    """Danh sách việc chưa làm - bấm vào để xem tùy chọn."""
    keyboard = []
    for i, task in enumerate(tasks):
        if not task["done"]:
            progress = task.get("progress", 0)
            if progress > 0:
                label = f"⏳ {task['title']} ({progress}%)"
            else:
                label = f"⏳ {task['title']}"
            keyboard.append(
                [InlineKeyboardButton(label, callback_data=f"menu:{i}")]
            )
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def build_action_menu(task_idx: int, task: dict):
    """Menu hành động khi bấm vào 1 task."""
    title = task["title"]
    progress = task.get("progress", 0)

    keyboard = [
        # Hàng 1: Hoàn thành
        [InlineKeyboardButton("✅ Đã hoàn thành", callback_data=f"done:{task_idx}")],
        # Hàng 2: Tiến độ
        [
            InlineKeyboardButton("📊 Đã làm được...", callback_data=f"progress_menu:{task_idx}"),
        ],
        # Hàng 3: Nhắc lại
        [
            InlineKeyboardButton("⏰ Nhắc lại lúc...", callback_data=f"snooze_menu:{task_idx}"),
        ],
        # Hàng 4: Quay lại
        [InlineKeyboardButton("◀️ Quay lại", callback_data="back_to_list")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_progress_keyboard(task_idx: int):
    """Chọn mức tiến độ."""
    keyboard = [
        [
            InlineKeyboardButton("10%", callback_data=f"set_progress:{task_idx}:10"),
            InlineKeyboardButton("25%", callback_data=f"set_progress:{task_idx}:25"),
            InlineKeyboardButton("50%", callback_data=f"set_progress:{task_idx}:50"),
        ],
        [
            InlineKeyboardButton("75%", callback_data=f"set_progress:{task_idx}:75"),
            InlineKeyboardButton("90%", callback_data=f"set_progress:{task_idx}:90"),
            InlineKeyboardButton("100% ✅", callback_data=f"done:{task_idx}"),
        ],
        [InlineKeyboardButton("◀️ Quay lại", callback_data=f"menu:{task_idx}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_snooze_keyboard(task_idx: int):
    """Chọn thời gian nhắc lại."""
    keyboard = [
        [
            InlineKeyboardButton("15 phút", callback_data=f"snooze:{task_idx}:15"),
            InlineKeyboardButton("30 phút", callback_data=f"snooze:{task_idx}:30"),
        ],
        [
            InlineKeyboardButton("1 giờ", callback_data=f"snooze:{task_idx}:60"),
            InlineKeyboardButton("2 giờ", callback_data=f"snooze:{task_idx}:120"),
        ],
        [
            InlineKeyboardButton("4 giờ", callback_data=f"snooze:{task_idx}:240"),
            InlineKeyboardButton("Ngày mai 8h", callback_data=f"snooze_tomorrow:{task_idx}"),
        ],
        [InlineKeyboardButton("◀️ Quay lại", callback_data=f"menu:{task_idx}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_delete_keyboard(tasks: list):
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task["done"] else "⏳"
        keyboard.append(
            [InlineKeyboardButton(f"🗑 Xóa: {status} {task['title']}", callback_data=f"delete:{i}")]
        )
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def progress_bar(percent: int) -> str:
    filled = percent // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty


def format_task_list(tasks: list) -> str:
    if not tasks:
        return "📭 Bạn chưa có việc nào. Dùng /add <tên việc> để thêm!"

    pending = [t for t in tasks if not t["done"]]
    done = [t for t in tasks if t["done"]]
    lines = []

    if pending:
        lines.append("📋 <b>VIỆC CẦN LÀM:</b>\n")
        for task in pending:
            progress = task.get("progress", 0)
            line = f"  ⏳ <b>{task['title']}</b>"
            if progress > 0:
                line += f"\n      {progress_bar(progress)} {progress}%"
            if task.get("deadline"):
                line += f"\n      📅 Hạn: {task['deadline']}"
            if task.get("snooze_time"):
                line += f"\n      ⏰ Nhắc lúc: {task['snooze_time']}"
            lines.append(line)

    if done:
        lines.append("\n✅ <b>ĐÃ HOÀN THÀNH:</b>\n")
        for task in done:
            line = f"  ☑️ <s>{task['title']}</s>"
            if task.get("finished"):
                line += f"  ({task['finished']})"
            lines.append(line)

    return "\n".join(lines)


# ── Commands ─────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 <b>Xin chào! Tôi là Bot Nhắc Việc</b>\n\n"
        "Tôi sẽ giúp bạn quản lý và nhắc nhở công việc.\n\n"
        "📌 <b>Các lệnh:</b>\n"
        "  /add <tên việc> — Thêm việc mới\n"
        "  /list — Xem danh sách & bấm chọn việc\n"
        "  /done — Đánh dấu việc đã xong\n"
        "  /delete — Xóa việc\n"
        "  /clear — Xóa tất cả việc đã hoàn thành\n"
        "  /remind — Nhận nhắc nhở ngay\n"
        "  /help — Xem hướng dẫn\n\n"
        "💡 <b>Mẹo:</b> Gửi thẳng tên việc (không cần /add) cũng được!\n"
        "💡 Bấm vào tên việc để xem tùy chọn: hoàn thành, tiến độ, nhắc lại."
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG</b>\n\n"
        "1️⃣ <b>Thêm việc:</b>\n"
        "   /add Mua sữa\n"
        "   /add Họp team 15h | 2025-04-15\n"
        "   Hoặc gõ thẳng tên việc!\n\n"
        "2️⃣ <b>Xem & quản lý:</b>  /list\n"
        "   → Bấm vào việc để xem menu:\n"
        "   • ✅ Đã hoàn thành\n"
        "   • 📊 Cập nhật tiến độ (10%-100%)\n"
        "   • ⏰ Nhắc lại sau (15p, 30p, 1h...)\n\n"
        "3️⃣ <b>Xóa việc:</b>  /delete\n\n"
        "4️⃣ <b>Dọn dẹp:</b>  /clear\n\n"
        f"🔔 Bot tự nhắc lúc: {', '.join(REMINDER_TIMES)}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    raw = " ".join(context.args) if context.args else ""

    if not raw.strip():
        await update.message.reply_text(
            "⚠️ Cần nhập tên việc!\n\nVí dụ: /add Mua sữa\nHoặc: /add Họp team | 2025-04-15"
        )
        return

    parts = raw.split("|", 1)
    title = parts[0].strip()
    deadline = parts[1].strip() if len(parts) > 1 else ""

    tasks = get_user_tasks(user_id)
    tasks.append({
        "title": title,
        "done": False,
        "progress": 0,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "deadline": deadline,
        "finished": "",
        "snooze_time": "",
    })
    save_user_tasks(user_id, tasks)

    msg = f"✅ Đã thêm: <b>{title}</b>"
    if deadline:
        msg += f"\n📅 Hạn: {deadline}"
    pending_count = sum(1 for t in tasks if not t["done"])
    msg += f"\n\n📊 Bạn có <b>{pending_count}</b> việc chưa làm."
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    text = format_task_list(tasks)
    pending = [t for t in tasks if not t["done"]]

    if pending:
        text += "\n\n👇 <b>Bấm vào việc để xem tùy chọn:</b>"

    keyboard = build_task_list_keyboard(tasks)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    pending = [t for t in tasks if not t["done"]]

    if not pending:
        await update.message.reply_text("🎉 Tuyệt vời! Bạn không có việc nào chưa làm!")
        return

    keyboard = build_task_list_keyboard(tasks)
    await update.message.reply_text(
        "👇 <b>Bấm vào việc để xem tùy chọn:</b>", parse_mode="HTML", reply_markup=keyboard
    )


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 Không có việc nào để xóa.")
        return
    keyboard = build_delete_keyboard(tasks)
    await update.message.reply_text(
        "👇 <b>Bấm nút để xóa việc:</b>", parse_mode="HTML", reply_markup=keyboard
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    before = len(tasks)
    tasks = [t for t in tasks if not t["done"]]
    removed = before - len(tasks)
    if removed == 0:
        await update.message.reply_text("Không có việc đã hoàn thành nào để xóa.")
        return
    save_user_tasks(user_id, tasks)
    await update.message.reply_text(f"🧹 Đã dọn <b>{removed}</b> việc đã hoàn thành.", parse_mode="HTML")


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    pending = [t for t in tasks if not t["done"]]
    if not pending:
        await update.message.reply_text("🎉 Bạn không có việc gì cần nhắc!")
        return

    text = "🔔 <b>NHẮC NHỞ CÔNG VIỆC</b>\n\n"
    for i, task in enumerate(pending, 1):
        progress = task.get("progress", 0)
        text += f"  {i}. ⏳ <b>{task['title']}</b>"
        if progress > 0:
            text += f" ({progress}%)"
        if task.get("deadline"):
            text += f"  — hạn: {task['deadline']}"
        text += "\n"
    text += f"\n📊 Tổng: <b>{len(pending)}</b> việc chưa làm."
    text += "\n\n👇 Bấm vào việc để xem tùy chọn:"

    keyboard = build_task_list_keyboard(tasks)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


# ── Callback Handler ─────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = query.data
    tasks = get_user_tasks(user_id)

    # ── Quay lại danh sách ──
    if data == "back_to_list":
        text = format_task_list(tasks)
        pending = [t for t in tasks if not t["done"]]
        if pending:
            text += "\n\n👇 <b>Bấm vào việc để xem tùy chọn:</b>"
        keyboard = build_task_list_keyboard(tasks)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Menu hành động cho 1 task ──
    if data.startswith("menu:"):
        idx = int(data.split(":")[1])
        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return
        task = tasks[idx]
        progress = task.get("progress", 0)

        text = f"📌 <b>{task['title']}</b>\n\n"
        if progress > 0:
            text += f"📊 Tiến độ: {progress_bar(progress)} {progress}%\n"
        if task.get("deadline"):
            text += f"📅 Hạn: {task['deadline']}\n"
        if task.get("created"):
            text += f"🕐 Tạo: {task['created']}\n"
        if task.get("snooze_time"):
            text += f"⏰ Nhắc lúc: {task['snooze_time']}\n"
        text += "\n👇 <b>Chọn hành động:</b>"

        keyboard = build_action_menu(idx, task)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Đánh dấu hoàn thành ──
    if data.startswith("done:"):
        idx = int(data.split(":")[1])
        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return

        task = tasks[idx]
        task["done"] = True
        task["progress"] = 100
        task["finished"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        task["snooze_time"] = ""
        save_user_tasks(user_id, tasks)

        pending = [t for t in tasks if not t["done"]]
        text = f"🎉 Đã hoàn thành: <b>{task['title']}</b>\n\n"

        if pending:
            text += f"📊 Còn <b>{len(pending)}</b> việc chưa làm.\n"
            text += "👇 Bấm vào việc tiếp theo:"
            keyboard = build_task_list_keyboard(tasks)
        else:
            text += "🏆 <b>Tuyệt vời! Bạn đã hoàn thành tất cả!</b>"
            keyboard = None

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Menu chọn tiến độ ──
    if data.startswith("progress_menu:"):
        idx = int(data.split(":")[1])
        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return
        task = tasks[idx]
        current = task.get("progress", 0)

        text = f"📊 <b>{task['title']}</b>\n\n"
        text += f"Tiến độ hiện tại: {progress_bar(current)} {current}%\n\n"
        text += "👇 <b>Chọn mức tiến độ mới:</b>"

        keyboard = build_progress_keyboard(idx)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Cập nhật tiến độ ──
    if data.startswith("set_progress:"):
        parts = data.split(":")
        idx = int(parts[1])
        new_progress = int(parts[2])

        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return

        task = tasks[idx]
        old_progress = task.get("progress", 0)
        task["progress"] = new_progress
        save_user_tasks(user_id, tasks)

        text = (
            f"📊 <b>{task['title']}</b>\n\n"
            f"Tiến độ: {progress_bar(old_progress)} {old_progress}%\n"
            f"      ↓\n"
            f"Tiến độ: {progress_bar(new_progress)} {new_progress}%\n\n"
            f"💪 Cố lên! "
        )

        if new_progress < 50:
            text += "Mới bắt đầu thôi, tiếp tục nào!"
        elif new_progress < 75:
            text += "Đã hơn nửa rồi, tốt lắm!"
        elif new_progress < 100:
            text += "Sắp xong rồi, chút nữa thôi!"

        pending = [t for t in tasks if not t["done"]]
        if pending:
            text += "\n\n👇 Việc khác:"
            keyboard = build_task_list_keyboard(tasks)
        else:
            keyboard = None

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Menu chọn thời gian nhắc lại ──
    if data.startswith("snooze_menu:"):
        idx = int(data.split(":")[1])
        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return
        task = tasks[idx]

        text = f"⏰ <b>{task['title']}</b>\n\n"
        text += "👇 <b>Nhắc lại sau bao lâu?</b>"

        keyboard = build_snooze_keyboard(idx)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Đặt nhắc lại (phút) ──
    if data.startswith("snooze:"):
        parts = data.split(":")
        idx = int(parts[1])
        minutes = int(parts[2])

        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return

        task = tasks[idx]
        remind_at = datetime.now() + timedelta(minutes=minutes)
        task["snooze_time"] = remind_at.strftime("%d/%m/%Y %H:%M")
        save_user_tasks(user_id, tasks)

        # Đặt job nhắc lại
        context.job_queue.run_once(
            snooze_callback,
            when=timedelta(minutes=minutes),
            data={"user_id": user_id, "task_idx": idx, "task_title": task["title"]},
            name=f"snooze_{user_id}_{idx}",
        )

        if minutes >= 60:
            time_text = f"{minutes // 60} giờ"
            if minutes % 60 > 0:
                time_text += f" {minutes % 60} phút"
        else:
            time_text = f"{minutes} phút"

        text = (
            f"⏰ Đã đặt nhắc lại!\n\n"
            f"📌 <b>{task['title']}</b>\n"
            f"🔔 Sẽ nhắc lúc: <b>{remind_at.strftime('%H:%M ngày %d/%m')}</b>\n"
            f"   (sau {time_text})"
        )

        pending = [t for t in tasks if not t["done"]]
        if pending:
            text += "\n\n👇 Việc khác:"
            keyboard = build_task_list_keyboard(tasks)
        else:
            keyboard = None

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Nhắc lại ngày mai 8h ──
    if data.startswith("snooze_tomorrow:"):
        idx = int(data.split(":")[1])

        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return

        task = tasks[idx]
        tomorrow_8am = (datetime.now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        delay = (tomorrow_8am - datetime.now()).total_seconds()

        task["snooze_time"] = tomorrow_8am.strftime("%d/%m/%Y %H:%M")
        save_user_tasks(user_id, tasks)

        context.job_queue.run_once(
            snooze_callback,
            when=timedelta(seconds=delay),
            data={"user_id": user_id, "task_idx": idx, "task_title": task["title"]},
            name=f"snooze_{user_id}_{idx}",
        )

        text = (
            f"⏰ Đã đặt nhắc lại!\n\n"
            f"📌 <b>{task['title']}</b>\n"
            f"🔔 Sẽ nhắc lúc: <b>8:00 sáng ngày mai ({tomorrow_8am.strftime('%d/%m')})</b>"
        )

        pending = [t for t in tasks if not t["done"]]
        if pending:
            text += "\n\n👇 Việc khác:"
            keyboard = build_task_list_keyboard(tasks)
        else:
            keyboard = None

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Xóa ──
    if data.startswith("delete:"):
        idx = int(data.split(":")[1])
        if idx < 0 or idx >= len(tasks):
            await query.edit_message_text("⚠️ Việc này không còn tồn tại.")
            return

        title = tasks[idx]["title"]
        tasks.pop(idx)
        save_user_tasks(user_id, tasks)

        text = f"🗑 Đã xóa: <b>{title}</b>\n"
        if tasks:
            keyboard = build_delete_keyboard(tasks)
            pending = sum(1 for t in tasks if not t["done"])
            text += f"\n📊 Còn <b>{len(tasks)}</b> việc ({pending} chưa làm)."
        else:
            keyboard = None
            text += "\n📭 Danh sách trống."

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return


# ── Snooze callback ──────────────────────────────────────────
async def snooze_callback(context: ContextTypes.DEFAULT_TYPE):
    """Gửi nhắc nhở khi hết thời gian snooze."""
    job_data = context.job.data
    user_id = job_data["user_id"]
    task_idx = job_data["task_idx"]
    task_title = job_data["task_title"]

    tasks = get_user_tasks(user_id)

    # Xóa snooze_time
    if task_idx < len(tasks) and not tasks[task_idx]["done"]:
        tasks[task_idx]["snooze_time"] = ""
        save_user_tasks(user_id, tasks)

    text = (
        f"🔔 <b>NHẮC NHỞ!</b>\n\n"
        f"📌 <b>{task_title}</b>\n\n"
        f"Đã đến lúc làm việc này rồi!"
    )

    # Tạo menu hành động
    if task_idx < len(tasks) and not tasks[task_idx]["done"]:
        keyboard = build_action_menu(task_idx, tasks[task_idx])
    else:
        keyboard = None

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Snooze remind failed for {user_id}: {e}")


# ── Text handler ─────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    raw = update.message.text.strip()
    if not raw:
        return

    parts = raw.split("|", 1)
    title = parts[0].strip()
    deadline = parts[1].strip() if len(parts) > 1 else ""

    tasks = get_user_tasks(user_id)
    tasks.append({
        "title": title,
        "done": False,
        "progress": 0,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "deadline": deadline,
        "finished": "",
        "snooze_time": "",
    })
    save_user_tasks(user_id, tasks)

    msg = f"✅ Đã thêm: <b>{title}</b>"
    if deadline:
        msg += f"\n📅 Hạn: {deadline}"
    pending_count = sum(1 for t in tasks if not t["done"])
    msg += f"\n\n📊 Bạn có <b>{pending_count}</b> việc chưa làm."
    await update.message.reply_text(msg, parse_mode="HTML")


# ── Auto remind ──────────────────────────────────────────────
async def auto_remind(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    for user_id, tasks in data.items():
        pending = [t for t in tasks if not t["done"]]
        if not pending:
            continue

        text = "🔔 <b>NHẮC NHỞ TỰ ĐỘNG</b>\n\n"
        for i, task in enumerate(pending, 1):
            progress = task.get("progress", 0)
            text += f"  {i}. ⏳ <b>{task['title']}</b>"
            if progress > 0:
                text += f" ({progress}%)"
            if task.get("deadline"):
                text += f"  — hạn: {task['deadline']}"
            text += "\n"
        text += f"\n📊 Bạn có <b>{len(pending)}</b> việc chưa làm."
        text += "\n👇 Bấm vào việc để xem tùy chọn:"

        keyboard = build_task_list_keyboard(tasks)
        try:
            await context.bot.send_message(
                chat_id=int(user_id), text=text, parse_mode="HTML", reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Auto remind failed for {user_id}: {e}")


# ── Main ─────────────────────────────────────────────────────
async def main_async():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  HÃY ĐIỀN BOT TOKEN!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    job_queue = app.job_queue
    for time_str in REMINDER_TIMES:
        h, m = map(int, time_str.split(":"))
        job_queue.run_daily(
            auto_remind,
            time=datetime.now().replace(hour=h, minute=m, second=0).time(),
            name=f"remind_{time_str}",
        )

    print("🤖 Bot đang chạy! Nhấn Ctrl+C để dừng.")
    print(f"🔔 Nhắc nhở tự động lúc: {', '.join(REMINDER_TIMES)}")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main_async())
