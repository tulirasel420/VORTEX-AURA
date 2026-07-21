import os
import io
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from pyquotex.stable_api import Quotex

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8610661294:AAHjo8yPmzwZ8EKuCKjF7gl7NY12OAgXZPc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8280240170"))  # আপনার Telegram User ID

QX_EMAIL = os.getenv("QX_EMAIL", "dzwwpgmh1z@bltiwd.com")
QX_PASSWORD = os.getenv("QX_PASSWORD", "@RASUU_QXB")

DEVELOPER_TAG = "Developers @RASUU_QXB"
BOT_NAME = "EPSON AI"

# Database/State Management
users_db = {ADMIN_ID: {"expiry": datetime(2099, 1, 1), "is_admin": True}} # Admin by default
bot_state = {"active": False, "mode": "AUTO", "market_type": "OTC", "task": None}

# ==================== CHART GENERATOR MODULE ====================
def generate_custom_chart(df: pd.DataFrame, asset: str, watermark_text: str = "EPSON AI", signal_box: dict = None) -> io.BytesIO:
    """স্ক্রিনশটের মতো ডার্ক থিম চার্ট জেনারেট করে ওয়াটারমার্ক ও S/R লেভেল সহ"""
    
    # Matplotlib styling for Dark Theme (like images)
    style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        rc={'font.family': 'sans-serif', 'axes.edgecolor': '#333333', 'grid.color': '#111111'},
        marketcolors=mpf.make_marketcolors(
            up='#00E676', down='#FF5252', edge='inherit', wick='inherit', volume='inherit'
        )
    )

    fig, axlist = mpf.plot(
        df, type='candle', style=style, returnfig=True,
        figscale=1.5, figratio=(16, 9), volume=False
    )
    ax = axlist[0]
    
    # 1. Add Center Watermark (EPSON AI)
    fig.text(0.5, 0.5, watermark_text, fontsize=42, color='#D4AF37',
             ha='center', va='center', alpha=0.18, fontweight='bold')

    # 2. Add Top-Left Info Box
    ax.text(0.02, 0.95, f"{watermark_text}\n{asset} | M1", transform=ax.transAxes,
            fontsize=10, color='#FFD700', bbox=dict(boxstyle='square,pad=0.4', facecolor='black', edgecolor='#FFD700', alpha=0.8))

    # 3. Add Top-Right Time Box
    current_time_str = datetime.now().strftime("%H:%M:%S BDT")
    ax.text(0.98, 0.95, f"⏱ {current_time_str}\nNext Candle: 50s", transform=ax.transAxes,
            fontsize=9, color='#00E5FF', ha='right', bbox=dict(boxstyle='square,pad=0.4', facecolor='#0B0E14', edgecolor='#00E5FF', alpha=0.8))

    # 4. Add Supply/Demand Zones & Pivot Lines
    high_val = df['High'].max()
    low_val = df['Low'].min()
    
    # Supply Box (Red Top)
    ax.axhspan(high_val * 0.998, high_val, color='#8B0000', alpha=0.3)
    ax.text(0.01, high_val * 0.998, f"SUPPLY {high_val:.4f}", color='#FF5252', fontsize=8)

    # Demand Box (Green Bottom)
    ax.axhspan(low_val, low_val * 1.002, color='#006400', alpha=0.3)
    ax.text(0.01, low_val, f"DEMAND {low_val:.4f}", color='#00E676', fontsize=8)

    # 5. Add Signal Box on Chart (If available)
    if signal_box:
        # Highlight trade candle
        ax.axvspan(len(df)-2, len(df)-1, color='#00E676' if signal_box['status'] == 'WIN' else '#FF5252', alpha=0.2)
        ax.text(len(df)-1.5, df['High'].iloc[-1], f"{signal_box['text']}", color='#00FF00',
                fontsize=9, bbox=dict(boxstyle='square', facecolor='black', edgecolor='#00FF00'))

    # Save image to BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#0B0E14')
    plt.close(fig)
    buf.seek(0)
    return buf

# ==================== TELEGRAM UTILS & KEYBOARDS ====================
def check_access(user_id: int) -> bool:
    if user_id in users_db:
        return datetime.now() < users_db[user_id]["expiry"]
    return False

def get_main_keyboard(user_id: int):
    keyboard = [
        [
            InlineKeyboardButton("📊 OTC Market", callback_data="market_otc"),
            InlineKeyboardButton("🌐 Live Market", callback_data="market_live")
        ],
        [
            InlineKeyboardButton("⚡ Auto Mode", callback_data="mode_auto"),
            InlineKeyboardButton("🎯 Manual Mode", callback_data="mode_manual")
        ]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Control Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_stop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 STOP SIGNAL BOT", callback_data="stop_signals")]
    ])

# ==================== SIGNAL ENGINE ====================
async def run_signal_scanner(app: Application, chat_id: int):
    """স্বয়ংক্রিয় সিগন্যাল জেনারেটর এবং মার্টিঙ্গেল রেজাল্ট চেকার"""
    client = Quotex(email=QX_EMAIL, password=QX_PASSWORD)
    ok, _ = await client.connect()
    
    if not ok:
        await app.bot.send_message(chat_id, "❌ Quotex Broker Connection Failed!")
        return

    asset = "USDCOP-OTC" if bot_state["market_type"] == "OTC" else "EURUSD"

    while bot_state["active"]:
        # 1. Fetch Candle Data
        candles = await client.get_historical_candles(asset, 3600, 60)
        df = pd.DataFrame(candles)
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'time': 'Date'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'], unit='s')
        df.set_index('Date', inplace=True)

        # 2. Simple Strategy Signal Logic (RSI / Candle Pattern)
        last_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        direction = "PUT🔴" if last_close < prev_close else "CALL🟢"
        
        entry_time = (datetime.now() + timedelta(minutes=1)).strftime("%H:%M")

        # 3. Generate Pre-Signal Chart
        chart_img = generate_custom_chart(df, asset, watermark_text=BOT_NAME)

        signal_msg = (
            f"🔮 **{BOT_NAME} QX BOT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f" 📊 **PAIR**             ➜ {asset}\n"
            f" ⏳ **ENTRY**          ➜ {entry_time}\n"
            f" 💻 **EXPIRE**         ➜ M1\n"
            f" 🚥 **DIRECTION**  ➜ {direction}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *1-min candle. Use 1-step Martingale if needed.*\n\n"
            f"👨‍💻 {DEVELOPER_TAG}"
        )

        sent_msg = await app.bot.send_photo(
            chat_id=chat_id, photo=chart_img, caption=signal_msg,
            parse_mode="Markdown", reply_markup=get_stop_keyboard()
        )

        # 4. Wait for Candle Expiry (1 Min) & 1-Step Martingale Verification
        await asyncio.sleep(60)
        
        # Check Result
        candles_new = await client.get_historical_candles(asset, 300, 60)
        c_df = pd.DataFrame(candles_new)
        win_non_mtg = (c_df['close'].iloc[-1] < c_df['open'].iloc[-1]) if "PUT" in direction else (c_df['close'].iloc[-1] > c_df['open'].iloc[-1])

        if win_non_mtg:
            res_text = "☑️ WIN SURESHOT ☑️"
            box_text = "NON-MTG WIN"
        else:
            # Check Martingale (1 Step)
            await asyncio.sleep(60)
            candles_mtg = await client.get_historical_candles(asset, 300, 60)
            m_df = pd.DataFrame(candles_mtg)
            win_mtg = (m_df['close'].iloc[-1] < m_df['open'].iloc[-1]) if "PUT" in direction else (m_df['close'].iloc[-1] > m_df['open'].iloc[-1])
            
            if win_mtg:
                res_text = "☑️ WIN ✦ Martingale"
                box_text = "MTG WIN"
            else:
                res_text = "❌ LOSS ❌"
                box_text = "LOSS"

        # 5. Send Result Chart & Message
        result_chart = generate_custom_chart(df, asset, watermark_text=BOT_NAME, signal_box={"text": box_text, "status": "WIN" if "WIN" in res_text else "LOSS"})

        result_msg = (
            f"📊 **{BOT_NAME} RESULT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💱  **Pair:**            {asset}\n"
            f"⏱    **Time:**           {entry_time}\n"
            f"🔮  **DIRECTION:** {direction}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{res_text}\n\n"
            f"👨‍💻 {DEVELOPER_TAG}"
        )

        await app.bot.send_photo(chat_id=chat_id, photo=result_chart, caption=result_msg, parse_mode="Markdown")
        await asyncio.sleep(10) # Interval between signals

    await client.close()

# ==================== TELEGRAM HANDLERS ====================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_access(user_id):
        await update.message.reply_text("❌ Access Denied! Contact Admin for Access Key.")
        return

    welcome_text = f"✨ **Welcome to {BOT_NAME} Control Panel** ✨\n\nSelect your signal preferences below:"
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not check_access(user_id):
        await query.edit_message_text("❌ Your access has expired!")
        return

    data = query.data

    if data == "market_otc":
        bot_state["market_type"] = "OTC"
        await query.edit_message_text("✅ Market set to: **OTC Market**", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
    elif data == "market_live":
        bot_state["market_type"] = "LIVE"
        await query.edit_message_text("✅ Market set to: **Live Market**", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
    elif data == "mode_auto":
        bot_state["mode"] = "AUTO"
        bot_state["active"] = True
        await query.edit_message_text("🚀 **AUTO MODE STARTED!** Scanning pairs for high win-rate signals...", parse_mode="Markdown")
        bot_state["task"] = asyncio.create_task(run_signal_scanner(context.application, query.message.chat_id))
    elif data == "stop_signals":
        bot_state["active"] = False
        if bot_state["task"]:
            bot_state["task"].cancel()
        await query.message.reply_text("🛑 **Signals Stopped.** Returning to main menu.", reply_markup=get_main_keyboard(user_id))
    elif data == "admin_panel" and user_id == ADMIN_ID:
        admin_text = "⚙️ **ADMIN CONTROL PANEL**\n\nUse commands:\n`/add_user <user_id> <days>`\n`/ban_user <user_id>`\n`/broadcast <msg>`"
        await query.edit_message_text(admin_text, parse_mode="Markdown")

# ==================== ADMIN COMMANDS ====================
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        users_db[target_id] = {"expiry": datetime.now() + timedelta(days=days), "is_admin": False}
        await update.message.reply_text(f"✅ User `{target_id}` added for {days} days!", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/add_user <user_id> <days>`", parse_mode="Markdown")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        users_db.pop(target_id, None)
        await update.message.reply_text(f"🚫 User `{target_id}` has been Banned/Removed!", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/ban_user <user_id>`", parse_mode="Markdown")

# ==================== MAIN APPLICATION ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("add_user", add_user))
    app.add_handler(CommandHandler("ban_user", ban_user))
    app.add_handler(CallbackQueryHandler(button_handler))

    print(f"🤖 {BOT_NAME} Telegram Bot is running successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()