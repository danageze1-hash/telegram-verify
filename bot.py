import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@yourchannel")

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    wallet TEXT DEFAULT '',
    referred_by INTEGER DEFAULT 0
)
""")
conn.commit()


def add_user(user_id, referred_by=0):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(user_id, referred_by) VALUES (?, ?)",
            (user_id, referred_by)
        )
        conn.commit()

        if referred_by and referred_by != user_id:
            cur.execute(
                "UPDATE users SET balance = balance + 5 WHERE user_id=?",
                (referred_by,)
            )
            conn.commit()


def menu():
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("📝 Tasks", callback_data="tasks")
        ],
        [
            InlineKeyboardButton("🎁 Invite & Earn", callback_data="invite"),
            InlineKeyboardButton("🏦 Set Wallet", callback_data="wallet")
        ],
        [
            InlineKeyboardButton("⬆️ Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("👥 Stats", callback_data="stats")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    ref = 0
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    add_user(user.id, ref)

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Complete tasks and invite friends to earn.\n"
        "💵 Referral reward: 5 ETB\n"
        "💳 Minimum withdrawal: 50 ETB",
        reply_markup=menu()
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    add_user(user_id)

    if query.data == "balance":
        cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cur.fetchone()[0]

        await query.message.reply_text(
            f"💰 Your Balance\n\n{balance:.2f} ETB"
        )

    elif query.data == "tasks":
        keyboard = [
            [InlineKeyboardButton(
                "📢 Join Channel",
                url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
            )],
            [InlineKeyboardButton(
                "✅ Verify Join",
                callback_data="verify_join"
            )]
        ]

        await query.message.reply_text(
            "📝 Task\n\n"
            "1️⃣ Join our Telegram channel\n"
            "2️⃣ Press Verify Join",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "verify_join":
        try:
            member = await context.bot.get_chat_member(
                CHANNEL_USERNAME, user_id
            )

            if member.status in ["member", "administrator", "creator"]:
                await query.message.reply_text(
                    "✅ Channel membership verified!"
                )
            else:
                await query.message.reply_text(
                    "❌ Please join the channel first."
                )

        except Exception:
            await query.message.reply_text(
                "⚠️ Verification failed.\n"
                "Make sure the bot is an administrator in the channel."
            )

    elif query.data == "invite":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"

        await query.message.reply_text(
            "🎁 Invite & Earn\n\n"
            "Invite a new user and earn 5 ETB.\n\n"
            f"🔗 Your referral link:\n{link}"
        )

    elif query.data == "wallet":
        context.user_data["waiting_wallet"] = True

        await query.message.reply_text(
            "🏦 Send your Telebirr number now:"
        )

    elif query.data == "withdraw":
        cur.execute(
            "SELECT balance, wallet FROM users WHERE user_id=?",
            (user_id,)
        )
        balance, wallet = cur.fetchone()

        if balance < 50:
            await query.message.reply_text(
                f"❌ Minimum withdrawal is 50 ETB.\n"
                f"Your balance: {balance:.2f} ETB"
            )
            return

        if not wallet:
            await query.message.reply_text(
                "⚠️ Please set your Telebirr number first."
            )
            return

        await query.message.reply_text(
            "⬆️ Withdrawal request received!\n\n"
            f"💰 Amount: {balance:.2f} ETB\n"
            f"📱 Telebirr: {wallet}\n\n"
            "⏳ Your request will be reviewed manually."
        )

        if ADMIN_ID:
            await context.bot.send_message(
                ADMIN_ID,
                f"💸 NEW WITHDRAWAL REQUEST\n\n"
                f"User ID: {user_id}\n"
                f"Amount: {balance:.2f} ETB\n"
                f"Telebirr: {wallet}"
            )

    elif query.data == "stats":
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        await query.message.reply_text(
            f"👥 Bot Stats\n\n"
            f"Total users: {total}"
        )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if context.user_data.get("waiting_wallet"):
        cur.execute(
            "UPDATE users SET wallet=? WHERE user_id=?",
            (text, user_id)
        )
        conn.commit()

        context.user_data["waiting_wallet"] = False

        await update.message.reply_text(
            f"✅ Telebirr number saved:\n{text}",
            reply_markup=menu()
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
