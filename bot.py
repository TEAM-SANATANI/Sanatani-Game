import os
import logging
import threading
import random
import asyncio
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Load environment variables from .env file if present locally
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOGGER_ID = int(os.getenv("LOGGER_ID", "0"))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# --- MongoDB Database Setup ---
if not MONGO_URI:
    logger.error("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client["sanatani_game_bot"]
users_collection = db["users"]

def get_user(user_id, username="Devotee"):
    user = users_collection.find_one({"user_id": user_id})
    if user:
        return user
    else:
        new_user = {
            "user_id": user_id,
            "username": username,
            "balance": 100,
            "last_pray": 0,
            "last_rob": 0
        }
        users_collection.insert_one(new_user)
        return new_user

def update_balance(user_id, amount, username="Devotee"):
    users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": amount},
            "$set": {"username": username}
        },
        upsert=True
    )

# --- Telegram Bot Commands & Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)
    
    welcome_text = (
        f"🙏 Namaste **{user.first_name}**! Welcome to **Sanatani Game Bot**.\n\n"
        "Embark on your spiritual economy journey! Earn, pray, rob rivals, or interact with friends using punch, kick, and kiss."
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="btn_balance"),
         InlineKeyboardButton("🌿 Work", callback_data="btn_work")],
        [InlineKeyboardButton("📿 Pray", callback_data="btn_pray"),
         InlineKeyboardButton("🦹 Rob Rival", callback_data="btn_rob")],
        [InlineKeyboardButton("🥊 Punch", callback_data="btn_punch"),
         InlineKeyboardButton("🦵 Kick", callback_data="btn_kick")],
        [InlineKeyboardButton("💖 Kiss", callback_data="btn_kiss"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="btn_leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id, user.first_name)
    bal = user_data.get("balance", 100)
    text = f"💰 Your current balance is **{bal} Coins**."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def work_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    earned = random.randint(30, 80)
    update_balance(user.id, earned, user.first_name)
    user_data = get_user(user.id)
    text = f"🌿 You performed noble service and earned **{earned} Coins**!\n💰 Total Balance: **{user_data['balance']} Coins**."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def pray_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    blessing = random.randint(100, 250)
    update_balance(user.id, blessing, user.first_name)
    user_data = get_user(user.id)
    text = f"📿 You offered intense prayers at the shrine and received divine grace of **{blessing} Coins**!\n💰 Total Balance: **{user_data['balance']} Coins**."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pipeline = [
        {"$match": {"user_id": {"$ne": user.id}, "balance": {"$gte": 50}}},
        {"$sample": {"size": 1}}
    ]
    victim_cursor = list(users_collection.aggregate(pipeline))
    
    if not victim_cursor:
        text = "🦹 No vulnerable targets found right now. Try again later!"
    else:
        victim = victim_cursor[0]
        v_id, v_name, v_bal = victim["user_id"], victim.get("username", "Traveler"), victim["balance"]
        success = random.choice([True, False])
        if success:
            stolen = random.randint(20, min(v_bal, 100))
            update_balance(user.id, stolen, user.first_name)
            update_balance(v_id, -stolen, v_name)
            text = f"🦹 Successful heist! You looted **{stolen} Coins** from `{v_name}`!"
        else:
            penalty = 40
            update_balance(user.id, -penalty, user.first_name)
            text = f"🚨 Caught in the act! You failed your robbery attempt and paid a fine of **{penalty} Coins**."

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def punch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message and update.message.reply_to_message else None
    
    if target:
        if target.id == user.id:
            text = "🥊 You tried to punch yourself... but missed awkwardly!"
        else:
            get_user(target.id, target.first_name)
            fine = 25
            update_balance(target.id, -fine, target.first_name)
            text = f"🥊 **{user.first_name}** gave a fierce punch to **{target.first_name}**! They dropped **{fine} Coins** from the impact!"
    else:
        text = "🥊 Reply to someone's message with `/punch` to hit them!"

    await update.message.reply_text(text, parse_mode="Markdown")

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message and update.message.reply_to_message else None
    
    if target:
        if target.id == user.id:
            text = "🦵 You tried to kick yourself and fell over!"
        else:
            get_user(target.id, target.first_name)
            fine = 30
            update_balance(target.id, -fine, target.first_name)
            text = f"🦵 **{user.first_name}** delivered a powerful kick to **{target.first_name}**! They lost **{fine} Coins** flying backwards!"
    else:
        text = "🦵 Reply to someone's message with `/kick` to launch them!"

    await update.message.reply_text(text, parse_mode="Markdown")

async def kiss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message and update.message.reply_to_message else None
    
    if target:
        if target.id == user.id:
            text = "💖 Self-love is important, but you kissed your own reflection!"
        else:
            get_user(target.id, target.first_name)
            reward = 20
            update_balance(user.id, reward, user.first_name)
            update_balance(target.id, reward, target.first_name)
            text = f"💖 **{user.first_name}** sent a sweet blessing kiss to **{target.first_name}**! Both gained **{reward} Coins** of mutual joy!"
    else:
        text = "💖 Reply to someone's message with `/kiss` to bless them with coins!"

    await update.message.reply_text(text, parse_mode="Markdown")

async def gamble_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("🎲 Usage: `/gamble <amount>` (e.g., `/gamble 50`)", parse_mode="Markdown")
        return
    
    try:
        bet = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for your bet.")
        return

    user_data = get_user(user.id, user.first_name)
    bal = user_data["balance"]
    if bet <= 0 or bet > bal:
        await update.message.reply_text(f"❌ Invalid bet amount. Your balance is **{bal} Coins**.", parse_mode="Markdown")
        return

    won = random.choice([True, False])
    if won:
        update_balance(user.id, bet, user.first_name)
        await update.message.reply_text(f"🎉 You rolled high and won **{bet} Coins**!", parse_mode="Markdown")
    else:
        update_balance(user.id, -bet, user.first_name)
        await update.message.reply_text(f"💔 Lady Luck turned away. You lost your bet of **{bet} Coins**.", parse_mode="Markdown")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = users_collection.find().sort("balance", -1).limit(5)
    
    text = "🏆 **Sanatani Leaderboard (Top Devotees)**:\n\n"
    for idx, u in enumerate(top_users, 1):
        name = u.get("username", "Devotee")
        bal = u.get("balance", 0)
        text += f"{idx}. {name} - **{bal} Coins**\n"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/broadcast <message>`", parse_mode="Markdown")
        return
    
    announcement = " ".join(context.args)
    all_users = users_collection.find({}, {"user_id": 1})
    count = 0
    
    for u in all_users:
        try:
            await context.bot.send_message(chat_id=u["user_id"], text=f"📢 **Announcement:**\n\n{announcement}", parse_mode="Markdown")
            count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ Broadcast sent successfully to {count} users.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "btn_balance":
        await balance_cmd(update, context)
    elif data == "btn_work":
        await work_cmd(update, context)
    elif data == "btn_pray":
        await pray_cmd(update, context)
    elif data == "btn_rob":
        await rob_cmd(update, context)
    elif data == "btn_punch":
        await query.answer("Reply to someone in chat with /punch to use this!", show_alert=True)
    elif data == "btn_kick":
        await query.answer("Reply to someone in chat with /kick to use this!", show_alert=True)
    elif data == "btn_kiss":
        await query.answer("Reply to someone in chat with /kiss to use this!", show_alert=True)
    elif data == "btn_leaderboard":
        await leaderboard_cmd(update, context)

# --- Flask Keep-Alive Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Sanatani Game Bot is live and running!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# --- Main Application Runner ---
async def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    if not MONGO_URI:
        logger.error("MONGO_URI environment variable not set!")
        return

    # Start Flask server in a daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Build and start Telegram application with explicit event loop management
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance_cmd))
    application.add_handler(CommandHandler("work", work_cmd))
    application.add_handler(CommandHandler("pray", pray_cmd))
    application.add_handler(CommandHandler("rob", rob_cmd))
    application.add_handler(CommandHandler("punch", punch_cmd))
    application.add_handler(CommandHandler("kick", kick_cmd))
    application.add_handler(CommandHandler("kiss", kiss_cmd))
    application.add_handler(CommandHandler("gamble", gamble_cmd))
    application.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Sanatani Game Bot is polling...")
    
    # Explicitly initialize, start, and run polling to avoid Python 3.14 main thread loop errors
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep the application running until stopped
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
