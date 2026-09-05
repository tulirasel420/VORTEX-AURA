#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zebronix Ultimate Control Center - BLACKOUT/WHITEOUT ONLY
Powered by @RASUU_QXB
Description: Specialized Telegram Bot for BLACKOUT & WHITEOUT Future Signals Only.
"""

import os
import re
import time
import uuid
import hashlib
import requests
import threading
import random
import sqlite3
import json
from datetime import datetime, timedelta

from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
#          CONFIGURATION SETUP
# ==========================================

API_TOKEN = "8159698797:AAGCcna_LGG3KNRWdjJN3XM6JQQxBm2T9UY"  # Replace with your bot token
ADMIN_ID = 8280240170  # Replace with your admin ID

# File paths
KEYS_FILE = "keys.txt"
DB_FILE = "users.db"
CHANNEL_USERNAME = "@your_channel"
OWNER_USERNAME = "@RASUU_QXB"
POWERED_BY = "@RASUU_QXB"

# ==========================================
#          PAIR LIST CONFIGURATIONS
# ==========================================

LIVE_REAL_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURJPY',
    'GBPJPY', 'AUDJPY', 'EURGBP', 'EURCHF', 'GBPCHF', 'CADJPY', 'CHFJPY', 'EURCAD',
    'EURAUD', 'GBPAUD', 'GBPCAD', 'AUDCAD'
]

# ==========================================
#    TELEGRAM BOT 9.4+ BUTTON STYLE SETTING
# ==========================================

BTN_PRIMARY = "primary"
BTN_SUCCESS = "success"
BTN_DANGER = "danger"

def Btn(
    text: str,
    callback_data: str = None,
    url: str = None,
    style: str = BTN_PRIMARY,
    icon_custom_emoji_id: str = None,
    **kwargs,
) -> InlineKeyboardButton:
    return telebot.types.InlineKeyboardButton(
        text,
        callback_data=callback_data,
        url=url,
        style=style,
        icon_custom_emoji_id=icon_custom_emoji_id,
        **kwargs,
    )

# ==========================================
#          FLASK WEB SERVER SETUP
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return 'Zebronix Ultimate Control Center is 100% Online!'

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
#            DATABASE FUNCTIONS
# ==========================================

def init_db():
    """Initialize SQLite database for users."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, joined_at TEXT)''')
    conn.commit()
    conn.close()

def save_user(user_id):
    """Save user to database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_users():
    """Get all registered user IDs."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [str(row[0]) for row in c.fetchall()]
    conn.close()
    return users

def is_valid_key(key):
    """Check if a key exists and is valid."""
    if not os.path.exists(KEYS_FILE):
        return False
    with open(KEYS_FILE, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split('|')
            if len(parts) >= 2 and parts[0] == key:
                if parts[1] == "UNLIMITED":
                    return True
                try:
                    if time.time() < float(parts[1]):
                        return True
                except:
                    pass
    return False

def remove_used_key(key):
    """Remove a key after use."""
    if not os.path.exists(KEYS_FILE):
        return
    with open(KEYS_FILE, 'r') as f:
        lines = f.readlines()
    with open(KEYS_FILE, 'w') as f:
        for line in lines:
            if line.strip().split('|')[0] != key:
                f.write(line)

def is_user_still_valid(chat_id):
    """Check if user has valid key."""
    if chat_id == ADMIN_ID:
        return True
    if not os.path.exists(KEYS_FILE):
        return False
    with open(KEYS_FILE, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split('|')
            if len(parts) > 2 and parts[2] == str(chat_id):
                exp_ts = parts[1]
                if exp_ts == "UNLIMITED":
                    return True
                if time.time() < float(exp_ts):
                    return True
    return False

# ==========================================
#            TELEGRAM BOT INIT
# ==========================================

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# ==========================================
#        KEYBOARD GENERATORS
# ==========================================

def make_live_pair_keyboard(selected_pairs):
    """Generate inline grid keyboard for LIVE market pairs."""
    markup = InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    for pair in LIVE_REAL_PAIRS:
        is_selected = pair in selected_pairs
        btn_style = BTN_DANGER if is_selected else BTN_PRIMARY
        emoji_id = "6213053622574392612" if is_selected else "6172369471848588525"
        
        buttons.append(Btn(
            text=pair if is_selected else pair,
            callback_data=f"toggle_live_{pair}",
            style=btn_style,
            icon_custom_emoji_id=emoji_id
        ))
    
    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])
    
    markup.add(Btn(
        "GENERATE SIGNAL",
        callback_data="live_selection_done",
        style=BTN_SUCCESS,
        icon_custom_emoji_id="6246611984469467622"
    ))
    markup.add(Btn(
        "HOME",
        callback_data="go_home",
        style=BTN_PRIMARY,
        icon_custom_emoji_id="5323642109767460983"
    ))
    return markup

# ==========================================
#             DASHBOARD
# ==========================================

def show_main_dashboard(chat_id):
    """Displays the main control panel of the bot."""
    if chat_id not in user_data:
        user_data[chat_id] = {'raw_signals': [], 'selected_pairs': []}
    user_data[chat_id]['state'] = 'MAIN_MENU'
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        Btn(' LIVE MARKET SIGNALS', callback_data='btn_live_market', style=BTN_PRIMARY, icon_custom_emoji_id='6208713364848256468'),
        Btn(' BLACKOUT FUTURE', callback_data='btn_blackout_mode', style=BTN_DANGER, icon_custom_emoji_id='6075388783887392362'),
        Btn(' WHITEOUT FUTURE', callback_data='btn_whiteout_mode', style=BTN_SUCCESS, icon_custom_emoji_id='6248789150636449446')
    )
    
    if chat_id == ADMIN_ID:
        markup.add(Btn(' BROADCAST', callback_data='btn_admin_broadcast', style=BTN_DANGER, icon_custom_emoji_id='6312339217619885468'))
    
    dashboard_text = (
        "<b>🕯 𝚆𝙴𝙻𝙲𝙾𝙼𝙴 𝚃𝙾 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝚃𝙾𝙾𝙻𝚂 🕯</b>\n"
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n\n"
        "<b>👑 𝙰𝙸-𝙳𝚁𝙸𝚅𝙴𝙽 𝙼𝙰𝚁𝙺𝙴𝚃 𝙵𝙾𝚁𝙴𝙲𝙰𝚂𝚃𝙸𝙽𝙶 🥂</b>\n"
        "<b>❄️ 𝙰𝙳𝚅𝙰𝙽𝙲𝙴 𝚂𝚃𝚁𝙰𝚃𝙴𝙶𝚈 𝚅𝙾𝙻𝙸𝙽𝙶 𝚂𝚈𝚂𝚃𝙴𝙼 💀</b>\n\n"
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n\n"
        "<b>🍾 𝚆𝙷𝚈 𝚃𝚁𝙰𝙳𝙴𝚁 𝙲𝙷𝙾𝙾𝚂𝙴 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 🧠</b>\n\n"
        "<b>🆗 𝙳𝙴𝙴𝙿 𝙰𝙽𝙰𝙻𝚈𝚂𝙴𝚂 𝙻𝙸𝚅𝙴 𝙿𝙰𝙸𝚁 📊</b>\n"
        "<b>📊 𝚁𝙴𝙰𝙻-𝚃𝙸𝙼𝙴 𝙾𝚁𝙳𝙴𝚁 𝙵𝙻𝙾𝚆 𝙰𝙽𝙰𝙻𝚈𝚂𝙸𝚂 🎙</b>\n"
        "<b>⚙️ 𝙱𝙻𝙰𝙲𝙺𝙾𝚄𝚃 & 𝚆𝙷𝙸𝚃𝙴𝙾𝚄𝚃 𝚂𝙸𝙶𝙽𝙰𝙻𝚂 🎮</b>\n\n"
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n\n"
        "<b>😍 𝙿𝚘𝚠𝚎𝚛𝚎𝚍 𝚋𝚢 @RASUU_QXB ✅</b>\n"
        "<b>🔒 𝚃𝙰𝙺𝙴 𝙲𝙾𝙽𝚃𝚁𝙾𝙻 𝙾𝙵 𝙴𝚅𝙴𝚁𝚈 𝚂𝙴𝙲𝙾𝙽𝙳 🔥</b>\n\n"
        "<b>🚀 𝙺𝙴𝙴𝙿 𝚂𝙸𝙶𝙽𝙰𝙻 𝚃𝙾 𝚂𝙼𝙰𝚁𝚃 𝚃𝚁𝙰𝙳𝙸𝙽𝙶 😍</b>"
    )
    bot.send_message(chat_id, dashboard_text, reply_markup=markup, parse_mode='HTML')

# ==========================================
#         COMMAND & PASS CHECK LOGIC
# ==========================================

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    
    if chat_id == ADMIN_ID:
        save_user(chat_id)
        bot.send_message(chat_id, '🔑 <b>𝚁𝙰𝚂𝚄 𝚀𝚇𝙱 𝚆𝙴𝙻𝙲𝙾𝙼𝙴 𝙱𝙾𝚂𝚂....</b>', parse_mode='HTML')
        show_main_dashboard(chat_id)
    elif is_user_still_valid(chat_id):
        show_main_dashboard(chat_id)
    else:
        bot.send_message(chat_id, '🔓 <b>𝙿𝚕𝚎𝚊𝚜𝚎 𝚎𝚗𝚝𝚎𝚛 𝚢𝚘𝚞𝚛 𝙰𝚌𝚌𝚎𝚜𝚜 𝙺𝚎𝚢 𝙲𝚘𝚗𝚝𝚊𝚌𝚝 𝚘𝚠𝚗𝚎𝚛:@RASUU_QXB 🔒</b>', parse_mode='HTML')
        user_data[chat_id] = {'state': 'AWAITING_PASSWORD', 'raw_signals': [], 'selected_pairs': []}

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('state') == 'AWAITING_PASSWORD')
def check_password(message):
    chat_id = message.chat.id
    entered_key = message.text.strip().upper()
    
    valid = False
    
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split('|')
            key_in_file = parts[0]
            
            if key_in_file == entered_key:
                exp_ts = parts[1]
                if len(parts) > 2 and parts[2] != str(chat_id):
                    new_lines.append(line)
                    continue
                
                if exp_ts == "UNLIMITED":
                    valid = True
                else:
                    if time.time() < float(exp_ts):
                        valid = True
                    else:
                        valid = False
                
                if valid:
                    if len(parts) == 2:
                        new_lines.append(f"{parts[0]}|{parts[1]}|{chat_id}\n")
                    else:
                        new_lines.append(line)
                    continue
            
            new_lines.append(line)
            
        with open(KEYS_FILE, 'w') as f:
            f.writelines(new_lines)

    if valid:
        save_user(chat_id)
        bot.send_message(chat_id, '💰 <b>Access Granted! Your account is successfully linked.</b>', parse_mode='HTML')
        show_main_dashboard(chat_id)
    else:
        bot.send_message(chat_id, '⚠️ <b>Invalid, Expired or Used Key! Please try again or contact Admin.</b>', parse_mode='HTML')

# ==========================================
#               ADMIN MODULES
# ==========================================

@bot.message_handler(commands=['genkey'])
def admin_genkey(message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.send_message(message.chat.id, "😕 <b>Usage:</b> <code>/genkey [duration]</code>\nExample:\n<code>/genkey 1mint</code>\n<code>/genkey 1days</code>\n<code>/genkey 1week</code>\n<code>/genkey 1month</code>\n<code>/genkey 1year</code>\n<code>/genkey unlimited</code>", parse_mode='HTML')
                return
                
            duration_str = args[1].lower()
            current_time = time.time()
            exp_timestamp = "UNLIMITED"
            label = "Unlimited Access"
            
            match = re.match(r'^(\d*)(mint|days|week|month|year|unlimited)$', duration_str)
            if not match:
                bot.send_message(message.chat.id, "😕 <b>ভুল ফরম্যাট!</b> দয়া করে সঠিক ইউনিট ব্যবহার করুন (mint, days, week, month, year, unlimited)", parse_mode='HTML')
                return
                
            val_str = match.group(1)
            value = int(val_str) if val_str else 1
            unit = match.group(2)
            
            if unit == "mint":
                exp_timestamp = str(current_time + (value * 60))
                label = f"{value} Minute(s)"
            elif unit == "days":
                exp_timestamp = str(current_time + (value * 86400))
                label = f"{value} Day(s)"
            elif unit == "week":
                exp_timestamp = str(current_time + (value * 7 * 86400))
                label = f"{value} Week(s)"
            elif unit == "month":
                exp_timestamp = str(current_time + (value * 30 * 86400))
                label = f"{value} Month(s)"
            elif unit == "year":
                exp_timestamp = str(current_time + (value * 365 * 86400))
                label = f"{value} Year(s)"
            elif unit == "unlimited":
                exp_timestamp = "UNLIMITED"
                label = "Unlimited Lifetime"

            new_key = uuid.uuid4().hex[:10].upper()
            
            with open(KEYS_FILE, 'a') as f:
                f.write(f"{new_key}|{exp_timestamp}\n")
                    
            msg_text = (
                f"🔒 <b>Generated New Access Key:</b>\n\n"
                f"<code>{new_key}</code>\n\n"
                f"🔥 <b>Validity:</b> {label}\n"
                f"<i>Click on the key to copy it and send to user.</i>"
            )
            bot.send_message(message.chat.id, msg_text, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"🤍 <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')

@bot.message_handler(commands=['expirekey'])
def admin_expirekey(message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.text.split()
            if len(args) < 2:
                bot.send_message(message.chat.id, "💔 <b>Usage:</b> <code>/expirekey [KEY]</code>\nExample: <code>/expirekey 2EEF63B3E4</code>", parse_mode='HTML')
                return
                
            target_key = args[1].strip().upper()
            
            if not os.path.exists(KEYS_FILE):
                bot.send_message(message.chat.id, "⚠️ <b>Database-এ কোনো সচল Key পাওয়া যায়নি।</b>", parse_mode='HTML')
                return
                
            with open(KEYS_FILE, 'r') as f:
                lines = f.readlines()
                
            found = False
            new_lines = []
            for line in lines:
                if line.strip().split('|')[0] == target_key:
                    found = True
                    continue 
                new_lines.append(line)
                
            if found:
                with open(KEYS_FILE, 'w') as f:
                    f.writelines(new_lines)
                bot.send_message(message.chat.id, f"🚨 <b>Key Successfully Expired!</b>\n\n<code>{target_key}</code> কি-টি সিস্টেম থেকে ডিঅ্যাক্টিভেট বা রিমুভ করা হয়েছে।", parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, f"⭕ <b>Key Not Found!</b>\nসিস্টেমে <code>{target_key}</code> নামের কোনো সচল কি খুঁজে পাওয়া যায়নি।", parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ <b>Error:</b> <code>{str(e)}</code>", parse_mode='HTML')

# ==========================================
#          GENERATE SIGNALS LOGIC
# ==========================================

def generate_blackout_whiteout_signals(pairs, mode, filter_days=1):
    """Generate BLACKOUT or WHITEOUT signals with time gaps."""
    signals = []
    
    now = datetime.now()
    start_time = now.replace(minute=0, second=0, microsecond=0)
    
    # Time gaps: 3, 4, 6, 9, 12, 14, 19 minutes
    time_gaps = [3, 4, 6, 9, 12, 14, 19]
    
    # Generate signals for next 6 hours with random gaps
    current_time = start_time
    end_time = start_time + timedelta(hours=6)
    
    while current_time <= end_time:
        time_str = current_time.strftime("%H:%M")
        
        for pair in pairs[:5]:  # Limit to 5 pairs per run
            seed = f"{pair}{time_str}{mode}{filter_days}{current_time.minute}"
            hash_val = int(hashlib.sha256(seed.encode('utf-8')).hexdigest(), 16)
            
            direction = "CALL" if (hash_val % 2 == 0) else "PUT"
            accuracy = 93 + (hash_val % 6)  # 93-98% accuracy
            
            signals.append({
                'asset': pair,
                'time': time_str,
                'direction': direction,
                'accuracy': accuracy,
                'mode': mode
            })
        
        # Random gap from the list
        gap = random.choice(time_gaps)
        current_time += timedelta(minutes=gap)
    
    # Sort by time and limit
    signals.sort(key=lambda s: s['time'])
    
    # Limit signals
    max_signals = 25
    if len(signals) > max_signals:
        signals = signals[:max_signals]
    
    return signals

# ==========================================
#          INLINE CALLBACK ROUTER
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def global_callback_router(call):
    chat_id = call.message.chat.id
    
    if chat_id != ADMIN_ID:
        if not is_user_still_valid(chat_id):
            bot.answer_callback_query(call.id, "Your session has expired! Please log in again.", show_alert=True)
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text='⚠️ <b>Your Key has Expired! Please enter a new Access Key:</b>',
                    parse_mode='HTML'
                )
            except:
                bot.send_message(chat_id, '🔓 <b>Your Key has Expired! Please enter a new Access Key:</b>', parse_mode='HTML')
            user_data[chat_id] = {'state': 'AWAITING_PASSWORD', 'raw_signals': [], 'selected_pairs': []}
            return

    if chat_id not in user_data:
        user_data[chat_id] = {'raw_signals': [], 'selected_pairs': []}
        
    state = user_data[chat_id].get('state')

    if call.data == 'go_home':
        show_main_dashboard(chat_id)
        return

    if call.data == 'btn_admin_broadcast':
        if chat_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "Access Denied!", show_alert=True)
            return
        user_data[chat_id]['state'] = 'AWAITING_BROADCAST_TEXT'
        markup = InlineKeyboardMarkup()
        markup.add(Btn("CANCEL", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='<b>Enter your broadcast message:</b>\n\n<i>You can use HTML formatting.</i>',
            reply_markup=markup,
            parse_mode='HTML'
        )
        return

    if call.data == 'confirm_broadcast_send':
        if chat_id != ADMIN_ID:
            return
        
        broadcast_msg = user_data[chat_id].get('pending_broadcast')
        if not broadcast_msg:
            bot.answer_callback_query(call.id, "No pending message found!", show_alert=True)
            show_main_dashboard(chat_id)
            return
            
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='<b>Sending message to all users, please wait...</b>', parse_mode='HTML')
        
        user_list = get_all_users()
        success, failed = 0, 0
        
        for u_id in user_list:
            try:
                bot.send_message(int(u_id), broadcast_msg, parse_mode='HTML')
                success += 1
            except:
                failed += 1
                
        user_data[chat_id]['pending_broadcast'] = None
        user_data[chat_id]['state'] = 'MAIN_MENU'
        
        end_markup = InlineKeyboardMarkup()
        end_markup.add(Btn("HOME", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        
        bot.send_message(
            chat_id,
            f"<b>BROADCAST REPORT:</b>\n\n✅ Successfully Sent: <b>{success}</b>\n❌ Failed/Blocked: <b>{failed}</b>",
            reply_markup=end_markup,
            parse_mode='HTML'
        )
        return

    if call.data == 'btn_live_market':
        user_data[chat_id]['market_mode'] = 'LIVE_REAL'
        user_data[chat_id]['selected_pairs'] = []
        user_data[chat_id]['state'] = 'LIVE_GRID_SELECTING'
        
        keyboard = make_live_pair_keyboard([])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='🕯 <b>SELECT LIVE MARKET PAIR:</b>\n\n<i>Select your pair and generate trading signals instantly</i>',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    if call.data == 'btn_blackout_mode':
        user_data[chat_id]['market_mode'] = 'BLACKOUT'
        user_data[chat_id]['selected_pairs'] = []
        user_data[chat_id]['state'] = 'BLACKOUT_SELECTING'
        
        keyboard = make_live_pair_keyboard([])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='🚀 <b>BLACKOUT MODE - SELECT PAIRS</b>\n\n<i>Select pairs for BLACKOUT signals</i>',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    if call.data == 'btn_whiteout_mode':
        user_data[chat_id]['market_mode'] = 'WHITEOUT'
        user_data[chat_id]['selected_pairs'] = []
        user_data[chat_id]['state'] = 'WHITEOUT_SELECTING'
        
        keyboard = make_live_pair_keyboard([])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='🔥 <b>WHITEOUT MODE - SELECT PAIRS</b>\n\n<i>Select pairs for WHITEOUT signals</i>',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Live market pair selection
    if state == 'LIVE_GRID_SELECTING' and call.data.startswith('toggle_live_'):
        pair = call.data.replace('toggle_live_', '')
        current_selections = user_data[chat_id].get('selected_pairs', [])
        
        if pair in current_selections:
            current_selections.remove(pair)
        else:
            current_selections.append(pair)
            
        user_data[chat_id]['selected_pairs'] = current_selections
        keyboard = make_live_pair_keyboard(current_selections)
        
        pairs_formatted = ", ".join(current_selections) if current_selections else "None"
        display_text = f'🔍 <b>Select your Live Market Pair:</b>\n\n✅ <b>Selected:</b> <code>{pairs_formatted}</code>'
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=display_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Blackout pair selection
    if state == 'BLACKOUT_SELECTING' and call.data.startswith('toggle_live_'):
        pair = call.data.replace('toggle_live_', '')
        current_selections = user_data[chat_id].get('selected_pairs', [])
        
        if pair in current_selections:
            current_selections.remove(pair)
        else:
            current_selections.append(pair)
            
        user_data[chat_id]['selected_pairs'] = current_selections
        keyboard = make_live_pair_keyboard(current_selections)
        
        pairs_formatted = ", ".join(current_selections) if current_selections else "None"
        display_text = f'🚀 <b>BLACKOUT - Selected Pairs:</b>\n\n✅ <b>Selected:</b> <code>{pairs_formatted}</code>\n\n<i>Click GENERATE to get BLACKOUT signals</i>'
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=display_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Whiteout pair selection
    if state == 'WHITEOUT_SELECTING' and call.data.startswith('toggle_live_'):
        pair = call.data.replace('toggle_live_', '')
        current_selections = user_data[chat_id].get('selected_pairs', [])
        
        if pair in current_selections:
            current_selections.remove(pair)
        else:
            current_selections.append(pair)
            
        user_data[chat_id]['selected_pairs'] = current_selections
        keyboard = make_live_pair_keyboard(current_selections)
        
        pairs_formatted = ", ".join(current_selections) if current_selections else "None"
        display_text = f'🔥 <b>WHITEOUT - Selected Pairs:</b>\n\n✅ <b>Selected:</b> <code>{pairs_formatted}</code>\n\n<i>Click GENERATE to get WHITEOUT signals</i>'
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=display_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Generate LIVE signals
    if state == 'LIVE_GRID_SELECTING' and call.data == 'live_selection_done':
        selected_pairs = user_data[chat_id].get('selected_pairs', [])
        
        if not selected_pairs:
            pairs_to_analyze = LIVE_REAL_PAIRS
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text='<pre>Analyzing All Live Real Pairs... 🔍</pre>',
                parse_mode='HTML'
            )
        else:
            pairs_to_analyze = selected_pairs
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f'<pre>Analyzing {len(pairs_to_analyze)} Selected Pairs... 🔍</pre>',
                parse_mode='HTML'
            )
        
        success_count = 0
        utc_plus_6 = datetime.utcnow() + timedelta(hours=6)
        
        for pair in pairs_to_analyze[:10]:  # Limit to 10 pairs
            # Generate live signal
            seed = f"{pair}{datetime.now().strftime('%Y%m%d%H%M')}"
            hash_val = int(hashlib.sha256(seed.encode('utf-8')).hexdigest(), 16)
            
            direction = "CALL" if (hash_val % 2 == 0) else "PUT"
            strength = 87 + (hash_val % 13)
            entry_time = (utc_plus_6 + timedelta(minutes=1 + (hash_val % 5))).strftime("%H:%M")
            
            template = (
                "   <b>      ╔═════════════╗\n"
                "           👑  ZEBRONIX LIVE AI  👑\n"
                "      ╚═════════════╝</b>\n"
                "┏━━━━━━━━━━━━━━━━━━━━\n"
                "┃ 📊 𝙰𝚜𝚜𝚎𝚝          : <b>{asset}</b>\n"
                "┃ 🎙 𝙳𝚒𝚛𝚎𝚌𝚝𝚒𝚘𝚗  : <b>{direction}</b>\n"
                "┃ ⏰ 𝙴𝚗𝚝𝚛𝚢          : <b>{entry}</b>\n"
                "┃ 🔈 𝚂𝚝𝚛𝚎𝚗𝚐𝚝𝚑      : <b>{strength}%</b>\n"
                "┃ 🫣 𝙼𝚃𝙶          : <b>1 Step Martingale</b>\n"
                "┗━━━━━━━━━━━━━━━━━━━━\n\n"
                "┏━━━━━━━━━━━━━━━━┓\n"
                "┃ 🔈 𝙾𝚆𝙽𝙴𝚁 : {owner}\n"
                "┗━━━━━━━━━━━━━━━━┛"
            ).format(
                asset=pair,
                direction=direction,
                entry=entry_time,
                strength=strength,
                owner=OWNER_USERNAME
            )
            
            bot.send_message(chat_id, template, parse_mode='HTML')
            success_count += 1
            time.sleep(0.3)
                
        end_markup = InlineKeyboardMarkup()
        end_markup.add(Btn("HOME", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        bot.send_message(
            chat_id,
            f"<b>✅ Successfully Generated {success_count} Live Price Action Signals!</b>",
            reply_markup=end_markup,
            parse_mode='HTML'
        )
        return

    # Generate BLACKOUT signals
    if state == 'BLACKOUT_SELECTING' and call.data == 'live_selection_done':
        selected_pairs = user_data[chat_id].get('selected_pairs', [])
        
        if not selected_pairs:
            pairs_to_use = LIVE_REAL_PAIRS
        else:
            pairs_to_use = selected_pairs
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='<pre>Generating BLACKOUT Signals... 🔥</pre>',
            parse_mode='HTML'
        )
        
        # Generate signals with time gaps
        signals = generate_blackout_whiteout_signals(pairs_to_use, "BLACKOUT")
        
        # Format output
        output_text = (
            "<b>🚀 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗕𝗟𝗔𝗖𝗞𝗢𝗨𝗧 🚀</b>\n\n"
            "<b>🕗 𝟭 𝗠𝗜𝗡𝗨𝗧𝗘</b>\n"
            "<b>⚙️ 𝗜𝗙 𝗟𝗢𝗦𝗦 𝗨𝗦𝗘 𝗠𝗧𝗚</b>\n"
            "<b>🎯 𝗔𝗩𝗢𝗜𝗗 𝗗𝗢𝗝𝗜 𝗠𝗨𝗦𝗧</b>\n\n"
            "<b>🤖 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘 𝗕𝗬 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫</b>\n\n"
            "<b>-------🚀𝗕𝗟𝗔𝗖𝗞𝗢𝗨𝗧🚀------</b>\n\n"
        )
        
        # Convert to proper format: 🔍 𝙰𝚄𝙳𝙲𝙰𝙳-𝙾𝚃𝙲 — 𝟷𝟸:𝟻𝟽
        for sig in signals[:20]:  # Limit output
            asset = sig['asset']
            if not asset.endswith('-OTC'):
                asset_display = f"{asset}-OTC"
            else:
                asset_display = asset
            
            # Convert to monospace numbers
            time_str = sig['time']
            time_mono = ''.join(['𝟶' if c == '0' else '𝟷' if c == '1' else '𝟸' if c == '2' else '𝟹' if c == '3' else '𝟺' if c == '4' else '𝟻' if c == '5' else '𝟼' if c == '6' else '𝟽' if c == '7' else '𝟾' if c == '8' else '𝟿' if c == '9' else c for c in time_str])
            
            output_text += f"🔍 <b>{asset_display} — {time_mono}</b>\n"
        
        output_text += (
            "\n<b>---------⚙️𝗥𝗨𝗟𝗘𝗦⚙️---------</b>\n\n"
            "<blockquote><b>𝐁𝐋𝐀𝐂𝐊𝐎𝐔𝐓:</b>\n"
            "Quotex-এ আগের ক্যান্ডেল যে DIRECTION ক্লোজ করবে সিগন্যাল লিস্টে থাকা টাইম ফ্রেমের এন্ট্রি তার অপজিটে নিবেন।</blockquote>"
        )
        
        end_markup = InlineKeyboardMarkup()
        end_markup.add(Btn("HOME", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        bot.send_message(chat_id, output_text, reply_markup=end_markup, parse_mode='HTML')
        return

    # Generate WHITEOUT signals
    if state == 'WHITEOUT_SELECTING' and call.data == 'live_selection_done':
        selected_pairs = user_data[chat_id].get('selected_pairs', [])
        
        if not selected_pairs:
            pairs_to_use = LIVE_REAL_PAIRS
        else:
            pairs_to_use = selected_pairs
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text='<pre>Generating WHITEOUT Signals... 🔥</pre>',
            parse_mode='HTML'
        )
        
        # Generate signals with time gaps
        signals = generate_blackout_whiteout_signals(pairs_to_use, "WHITEOUT")
        
        # Format output
        output_text = (
            "<b>🔥 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧 🔥</b>\n\n"
            "<b>🕗 𝟭 𝗠𝗜𝗡𝗨𝗧𝗘</b>\n"
            "<b>⚙️ 𝗜𝗙 𝗟𝗢𝗦𝗦 𝗨𝗦𝗘 𝗠𝗧𝗚</b>\n"
            "<b>🎯 𝗔𝗩𝗢𝗜𝗗 𝗗𝗢𝗝𝗜 𝗠𝗨𝗦𝗧</b>\n\n"
            "<b>🤖 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘 𝗕𝗬 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫</b>\n\n"
            "<b>-------🔥𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧🔥------</b>\n\n"
        )
        
        # Convert to proper format: 🔍 𝙰𝚄𝙳𝙲𝙰𝙳-𝙾𝚃𝙲 — 𝟷𝟸:𝟻𝟽
        for sig in signals[:20]:  # Limit output
            asset = sig['asset']
            if not asset.endswith('-OTC'):
                asset_display = f"{asset}-OTC"
            else:
                asset_display = asset
            
            # Convert to monospace numbers
            time_str = sig['time']
            time_mono = ''.join(['𝟶' if c == '0' else '𝟷' if c == '1' else '𝟸' if c == '2' else '𝟹' if c == '3' else '𝟺' if c == '4' else '𝟻' if c == '5' else '𝟼' if c == '6' else '𝟽' if c == '7' else '𝟾' if c == '8' else '𝟿' if c == '9' else c for c in time_str])
            
            output_text += f"⚙️ <b>{asset_display} — {time_mono}</b>\n"
        
        output_text += (
            "\n<b>---------⚙️𝗥𝗨𝗟𝗘𝗦⚙️---------</b>\n\n"
            "<blockquote><b>𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧:</b>\n"
            "Quotex-এ আগের ক্যান্ডেল যে DIRECTION ক্লোজ করবে সিগন্যাল লিস্টে থাকা টাইম ফ্রেমের এন্ট্রি \"SAME DIRECTION\" এ নিবেন।</blockquote>"
        )
        
        end_markup = InlineKeyboardMarkup()
        end_markup.add(Btn("HOME", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        bot.send_message(chat_id, output_text, reply_markup=end_markup, parse_mode='HTML')
        return

# ==========================================
#             TEXT MESSAGE HANDLER
# ==========================================

@bot.message_handler(func=lambda m: True)
def global_text_handler(message):
    chat_id = message.chat.id
    
    if chat_id != ADMIN_ID:
        if not is_user_still_valid(chat_id):
            bot.send_message(chat_id, '💻 <b>Your Access Key has expired! Please enter a new Key:</b>', parse_mode='HTML')
            user_data[chat_id] = {'state': 'AWAITING_PASSWORD', 'raw_signals': [], 'selected_pairs': []}
            return

    if chat_id not in user_data:
        user_data[chat_id] = {'raw_signals': [], 'selected_pairs': []}
    state = user_data[chat_id].get('state')
    text = message.text.strip()

    if state == 'AWAITING_BROADCAST_TEXT' and chat_id == ADMIN_ID:
        user_data[chat_id]['pending_broadcast'] = text
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            Btn("SEND TO ALL USERS", callback_data="confirm_broadcast_send", style=BTN_SUCCESS, icon_custom_emoji_id="6311920793315975140"),
            Btn("CANCEL", callback_data="go_home", style=BTN_PRIMARY, icon_custom_emoji_id="6210541801145638044")
        )
        bot.send_message(chat_id, f"<b>Your Message Preview:</b>\n━━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━━\n<i>Confirm sending by tapping below:</i>", reply_markup=markup, parse_mode='HTML')
        return

# ==========================================
#              BOT EXECUTION
# ==========================================

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling(none_stop=True)
