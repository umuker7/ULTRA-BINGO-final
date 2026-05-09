import telebot
from telebot import types, apihelper
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import threading
import os

# 1. መሠረታዊ መረጃዎች
API_TOKEN = '8628233636:AAFF1w2zNlMKOnCoqDqFHiKu1ej2S2OCFL4'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__, static_folder='.')
CORS(app)

DB_PATH = 'ultra_bingo.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ዳታቤዝ መፍጠሪያ
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, first_name TEXT, phone TEXT, 
        balance REAL DEFAULT 10.0, has_deposited INTEGER DEFAULT 0)''')
    conn.commit()
init_db()

# --- የቴሌግራም ቦት ክፍል ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = get_db().execute('SELECT * FROM users WHERE user_id = ?', (uid,)).fetchone()
    if user:
        send_menu(message, f"እንኳን ደህና መጡ {message.from_user.first_name}!")
    else:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("📱 ተመዝገብ / Register", request_contact=True))
        bot.send_message(uid, "እንኳን ወደ ⚡️ ULTRA BINGO መጡ! ለመመዝገብና የ10 ብር ቦነስ ለማግኘት ስልክዎን ያጋሩ።", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid = message.chat.id
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO users (user_id, first_name, phone, balance) VALUES (?, ?, ?, ?)',
                 (uid, message.from_user.first_name, message.contact.phone_number, 10.0))
    conn.commit()
    bot.send_message(uid, "🎉 የ 10 ብር ቦነስ አግኝተዋል!")
    send_menu(message, "አሁኑኑ ይጫወቱ! 👇")

def send_menu(message, text):
    markup = types.InlineKeyboardMarkup()
    # Render ሲጫን የሚሰጥህ ሊንክ እዚህ ይገባል
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"
    markup.add(types.InlineKeyboardButton("🎮 PLAY BINGO", web_app=types.WebAppInfo(url=url)))
    bot.send_message(message.chat.id, text, reply_markup=markup)

# --- የዌብሳይቱ API ክፍል ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/get_balance')
def balance():
    uid = request.args.get('user_id')
    user = get_db().execute('SELECT balance, has_deposited FROM users WHERE user_id = ?', (uid,)).fetchone()
    return jsonify({"balance": user['balance'] if user else 0, "has_deposited": user['has_deposited'] if user else 0})

@app.route('/deduct_balance', methods=['POST'])
def deduct():
    data = request.json
    uid, amt = data.get('user_id'), data.get('amount')
    conn = get_db()
    user = conn.execute('SELECT balance FROM users WHERE user_id = ?', (uid,)).fetchone()
    if user and user['balance'] >= amt:
        conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amt, uid))
        conn.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "በቂ ብር የለዎትም!"}), 400

@app.route('/deposit_request', methods=['POST'])
def deposit():
    data = request.json
    uid = data.get('user_id')
    conn = get_db()
    conn.execute('UPDATE users SET has_deposited = 1 WHERE user_id = ?', (uid,))
    conn.commit()
    return jsonify({"success": True, "message": "ጥያቄዎ ተልኳል!"})

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)