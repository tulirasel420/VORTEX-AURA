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

API_TOKEN = os.environ.get("BOT_TOKEN", "8159698797:AAGCcna_LGG3KNRWdjJN3XM6JQQxBm2T9UY")
ADMIN_ID = 8280240170

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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, joined_at TEXT)''')
    conn.commit()
    conn.close()

def save_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [str(row[0]) for row in c.fetchall()]
    conn.close()
    return users

def is_valid_key(key):
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

def is_user_still_valid(chat_id):
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
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for pair in LIVE_REAL_PAIRS:
        is_selected = pair in selected_pairs
        btn_style = BTN_DANGER if is_selected else BTN_PRIMARY
        emoji_id = "6213053622574392612" if is_selected else "6172369471848588525"
        
        buttons.append(Btn(
            text=pair,
            callback_data=f"toggle_live_{pair}",
            style=btn_style,
            icon_custom_emoji_id=emoji_id
        ))
    
    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])
    
    markup.add(Btn(
        "NEXT STEP ➔",
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
    if chat_id not in user_data:
        user_data[chat_id] = {'selected_pairs': []}
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
        "<b>😍 𝙿𝚘𝚠𝚎𝚛𝚎𝚍 𝚋𝚢 @RASUU_QXB ✅</b>"
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
        user_data[chat_id] = {'state': 'AWAITING_PASSWORD', 'selected_pairs': []}

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
            if not line.strip(): continue
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
                    valid = time.time() < float(exp_ts)
                
                if valid:
                    new_lines.append(f"{parts[0]}|{parts[1]}|{chat_id}\n")
                    continue
            new_lines.append(line)
            
        with open(KEYS_FILE, 'w') as f:
            f.writelines(new_lines)

    if valid:
        save_user(chat_id)
        bot.send_message(chat_id, '💰 <b>Access Granted!</b>', parse_mode='HTML')
        show_main_dashboard(chat_id)
    else:
        bot.send_message(chat_id, '⚠️ <b>Invalid or Expired Key!</b>', parse_mode='HTML')

# ==========================================
#          GENERATE SIGNALS LOGIC
# ==========================================

def generate_blackout_whiteout_signals(pairs, mode, start_str, end_str):
    """Generate signals step-by-step between start_time and end_time with proper gaps."""
    signals = []
    
    today = datetime.now().date()
    start_dt = datetime.strptime(f"{today} {start_str}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{today} {end_str}", "%Y-%m-%d %H:%M")
    
    # If end time is smaller than start time, assume it spans to next day
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
        
    # Gaps required: 3, 4, 6, 7, 9, 11, 14, 18, 21 minutes
    time_gaps = [3, 4, 6, 7, 9, 11, 14, 18, 21]
    
    current_time = start_dt
    
    while current_time <= end_dt:
        selected_pair = random.choice(pairs)
        time_formatted = current_time.strftime("%H:%M")
        
        signals.append({
            'asset': selected_pair,
            'time': time_formatted,
            'mode': mode
        })
        
        gap = random.choice(time_gaps)
        current_time += timedelta(minutes=gap)
    
    return signals

# ==========================================
#          INLINE CALLBACK ROUTER
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def global_callback_router(call):
    chat_id = call.message.chat.id
    
    if chat_id != ADMIN_ID and not is_user_still_valid(chat_id):
        bot.answer_callback_query(call.id, "Session expired!", show_alert=True)
        return

    if chat_id not in user_data:
        user_data[chat_id] = {'selected_pairs': []}
        
    state = user_data[chat_id].get('state')

    if call.data == 'go_home':
        show_main_dashboard(chat_id)
        return

    if call.data in ['btn_blackout_mode', 'btn_whiteout_mode']:
        mode = 'BLACKOUT' if call.data == 'btn_blackout_mode' else 'WHITEOUT'
        user_data[chat_id]['market_mode'] = mode
        user_data[chat_id]['selected_pairs'] = []
        user_data[chat_id]['state'] = f'{mode}_SELECTING'
        
        keyboard = make_live_pair_keyboard([])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f'🚀 <b>{mode} MODE - SELECT PAIRS</b>\n\n<i>Select pairs for {mode} signals</i>',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Toggle selection
    if call.data.startswith('toggle_live_'):
        pair = call.data.replace('toggle_live_', '')
        current_selections = user_data[chat_id].get('selected_pairs', [])
        
        if pair in current_selections:
            current_selections.remove(pair)
        else:
            current_selections.append(pair)
            
        user_data[chat_id]['selected_pairs'] = current_selections
        keyboard = make_live_pair_keyboard(current_selections)
        
        pairs_formatted = ", ".join(current_selections) if current_selections else "None"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f'🔍 <b>Selected Pairs:</b> <code>{pairs_formatted}</code>',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Finish pair selection -> Ask Start Time
    if call.data == 'live_selection_done':
        if not user_data[chat_id].get('selected_pairs'):
            user_data[chat_id]['selected_pairs'] = LIVE_REAL_PAIRS[:5]
            
        user_data[chat_id]['state'] = 'AWAITING_START_TIME'
        
        msg_text = (
            "📊<b>𝙴𝙽𝚃𝙴𝚁 𝚂𝚃𝙰𝚁𝚃 𝚃𝙸𝙼𝙴</b> 📊\n"
            "━━━━━━━━━━━━━━\n\n"
            "⏰ <b>𝚂𝚝𝚎𝚙 𝟷 — 𝚂𝚝𝚊𝚛𝚝 𝚃𝚒𝚖𝚎</b>\n\n"
            "😧 <b>𝙴𝚗𝚝𝚎𝚛 𝚜𝚒𝚐𝚗𝚊𝚕 𝚜𝚝𝚊𝚛𝚝 𝚝𝚒𝚖𝚎:</b>\n"
            "<code>HH:MM</code> e.g. <code>09:00</code>\n\n"
            "⬇️<b>𝚃𝚘 𝙽𝚎𝚡𝚝 𝚂𝚝𝚎𝚙 𝚂𝚊𝚖𝚎 𝙿𝚛𝚘𝚌𝚎𝚜𝚜</b>⌛"
        )
        bot.send_message(chat_id, msg_text, parse_mode='HTML')
        return

# ==========================================
#             TEXT MESSAGE HANDLER
# ==========================================

@bot.message_handler(func=lambda m: True)
def global_text_handler(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {'selected_pairs': []}
        
    state = user_data[chat_id].get('state')
    text = message.text.strip()

    # Handle Start Time Input
    if state == 'AWAITING_START_TIME':
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', text):
            bot.send_message(chat_id, "❌ <b>Invalid format! Please enter time in HH:MM format (e.g., 09:00).</b>", parse_mode='HTML')
            return
            
        user_data[chat_id]['start_time'] = text
        user_data[chat_id]['state'] = 'AWAITING_END_TIME'
        
        msg_text = (
            "🧪<b>𝙴𝙽𝚃𝙴𝚁 𝙴𝙽𝙳 𝚃𝙸𝙼𝙴</b>🧪\n"
            "━━━━━━━━━━━━━━\n\n"
            "⏰ <b>𝚂𝚝𝚎𝚙 𝟸 — 𝙴𝚗𝚝𝚎𝚛 𝚎𝚗𝚍 𝚃𝚒𝚖𝚎</b>\n\n"
            "⏰<b>𝙴𝚗𝚝𝚎𝚛 𝚜𝚒𝚐𝚗𝚊𝚕 𝚎𝚗𝚍 𝚝𝚒𝚖𝚎:</b> <code>HH:MM</code> e.g. <code>09:00</code>\n\n"
            "⚖️<b>𝙽𝚘𝚠 𝙶𝚎𝚗𝚎𝚛𝚊𝚝𝚎 𝚂𝚒𝚐𝚗𝚊𝚕𝚜 𝚒𝚗 𝚜𝚎𝚌𝚘𝚗𝚍</b>⌛"
        )
        bot.send_message(chat_id, msg_text, parse_mode='HTML')
        return

    # Handle End Time Input & Signal Generation
    if state == 'AWAITING_END_TIME':
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', text):
            bot.send_message(chat_id, "❌ <b>Invalid format! Please enter time in HH:MM format (e.g., 10:30).</b>", parse_mode='HTML')
            return
            
        start_time = user_data[chat_id].get('start_time')
        end_time = text
        mode = user_data[chat_id].get('market_mode', 'BLACKOUT')
        selected_pairs = user_data[chat_id].get('selected_pairs', LIVE_REAL_PAIRS)
        
        bot.send_message(chat_id, "⏳ <b>Generating Signals... Please wait.</b>", parse_mode='HTML')
        
        signals = generate_blackout_whiteout_signals(selected_pairs, mode, start_time, end_time)
        
        # Build Output Format
        icon = "🚀" if mode == "BLACKOUT" else "🔥"
        output_text = (
            f"<b>{icon} 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 {mode} {icon}</b>\n\n"
            "<b>🕗 𝟭 𝗠𝗜𝗡𝗨𝗧𝗘</b>\n"
            "<b>⚙️ 𝗜𝗙 𝗟𝗢𝗦𝗦 𝗨𝗦𝗘 𝗠𝗧𝗚</b>\n"
            "<b>🎯 𝗔𝗩𝗢𝗜𝗗 𝗗𝗢𝗧𝗝𝗜 𝗠𝗨𝗦𝗧</b>\n\n"
            "<b>🤖 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘 𝗕𝗬 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫</b>\n\n"
            f"<b>-------{icon}{mode}{icon}------</b>\n\n"
        )
        
        # Format time to math monospace format
        mono_map = {'0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺', '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'}
        
        for sig in signals:
            asset = sig['asset']
            asset_display = asset if asset.endswith('-OTC') else f"{asset}-OTC"
            time_str = sig['time']
            time_mono = "".join(mono_map.get(c, c) for c in time_str)
            
            bullet_icon = "🔍" if mode == "BLACKOUT" else "⚙️"
            output_text += f"{bullet_icon} <b>{asset_display} — {time_mono}</b>\n"
            
        rule_desc = (
            "Quotex-এ আগের ক্যান্ডেল যে DIRECTION ক্লোজ করবে সিগন্যাল লিস্টে থাকা টাইম ফ্রেমের এন্ট্রি তার অপজিটে নিবেন।"
            if mode == "BLACKOUT" else
            "Quotex-এ আগের ক্যান্ডেল যে DIRECTION ক্লোজ করবে সিগন্যাল লিস্টে থাকা টাইম ফ্রেমের এন্ট্রি SAME DIRECTION এ নিবেন।"
        )
        
        output_text += (
            "\n<b>---------⚙️𝗥𝗨𝗟𝗘𝗦⚙️---------</b>\n\n"
            f"<blockquote><b>{mode}:</b>\n{rule_desc}</blockquote>"
        )
        
        end_markup = InlineKeyboardMarkup()
        end_markup.add(Btn("HOME", callback_data="go_home", style=BTN_DANGER, icon_custom_emoji_id="6199608695605699161"))
        
        bot.send_message(chat_id, output_text, reply_markup=end_markup, parse_mode='HTML')
        user_data[chat_id]['state'] = 'MAIN_MENU'
        return

# ==========================================
#              BOT EXECUTION
# ==========================================

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling(none_stop=True)
