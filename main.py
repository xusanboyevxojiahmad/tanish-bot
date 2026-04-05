import os
import telebot
from telebot import types
import sqlite3
import threading
import http.server
import socketserver

# --- RENDER UCHUN PORT ---
def run_port():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_port, daemon=True).start()

# --- SOZLAMALAR ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8329231121 # Sizning ID
PREMIUM_LIMIT = 5    # Nechta do'st uchun premium beriladi

bot = telebot.TeleBot(API_TOKEN)

# --- BAZA BILAN ISHLASH ---
def get_db():
    return sqlite3.connect('dating_bot.db', check_same_thread=False)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, full_name TEXT, 
        invite_count INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'uz')''')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    # Admin ID va Premium tizimi holati (1 - yoqiq, 0 - o'chiq)
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("admin_id", ?)', (str(ADMIN_ID),))
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("premium_system", "1")')
    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

# --- YORDAMCHI FUNKSIYALAR ---
def get_user_data(uid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    conn.close()
    return res

def show_main_menu(uid):
    user = get_user_data(uid)
    lang = user[4] if user else 'uz'
    premium_icon = "🌟" if user and user[3] == 1 else "👤"
    
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔍 Suhbatdosh topish")
    m.add("👥 Do'stlarim", "🎁 Premium & Takliflar")
    if int(uid) == ADMIN_ID:
        m.add("⚙️ Admin Panel")
    
    bot.send_message(uid, f"{premium_icon} Asosiy menyu", reply_markup=m)

# --- START VA REFERAL ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    uid = message.chat.id
    user = get_user_data(uid)
    
    if not user:
        # Referalni tekshirish
        if len(message.text.split()) > 1:
            ref_id = message.text.split()[1]
            if ref_id.isdigit() and int(ref_id) != uid:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET invite_count = invite_count + 1 WHERE user_id = ?", (ref_id,))
                
                # Premium berishni tekshirish (faqat tizim yoqiq bo'lsa)
                if get_setting("premium_system") == "1":
                    cursor.execute("SELECT invite_count FROM users WHERE user_id = ?", (ref_id,))
                    c = cursor.fetchone()
                    if c and c[0] >= PREMIUM_LIMIT:
                        cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (ref_id,))
                        try: bot.send_message(ref_id, "🌟 Tabriklaymiz! 5 ta do'st taklif qildingiz va Premium statusiga ega bo'ldingiz!")
                        except: pass
                conn.commit()
                conn.close()

        msg = bot.send_message(uid, "Xush kelibsiz! Ismingizni kiriting:")
        bot.register_next_step_handler(msg, save_user)
    else:
        show_main_menu(uid)

def save_user(message):
    uid = message.chat.id
    name = message.text
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, full_name) VALUES (?,?)", (uid, name))
    conn.commit()
    conn.close()
    show_main_menu(uid)

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.chat.id == ADMIN_ID)
def admin_panel(message):
    status = "YOQIQ ✅" if get_setting("premium_system") == "1" else "O'CHIQ ❌"
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(f"Premium Tizimi: {status}", callback_data="toggle_prem"))
    bot.send_message(ADMIN_ID, "Admin boshqaruv paneli:", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "toggle_prem")
def toggle_prem(call):
    current = get_setting("premium_system")
    new_val = "0" if current == "1" else "1"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'premium_system'", (new_val,))
    conn.commit()
    conn.close()
    
    status_text = "YOQIQ ✅" if new_val == "1" else "O'CHIQ ❌"
    bot.edit_message_text(f"Admin boshqaruv paneli:\nPremium Tizimi: {status_text}", 
                         call.message.chat.id, call.message.message_id, 
                         reply_markup=call.message.reply_markup)
    bot.answer_callback_query(call.id, "Holat o'zgardi!")

# --- TUGMALAR ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.chat.id
    user = get_user_data(uid)
    if not user: return

    if message.text == "🎁 Premium & Takliflar":
        if get_setting("premium_system") == "0":
            bot.send_message(uid, "⚠️ Premium tizimi vaqtincha o'chirilgan. Tez orada yoqiladi!")
            return
            
        bot_user = bot.get_me().username
        link = f"https://t.me/{bot_user}?start={uid}"
        count = user[2]
        is_prem = "🌟 FAOL" if user[3] == 1 else "Oddiy foydalanuvchi"
        
        msg = (f"Sizning holatingiz: {is_prem}\n"
               f"Taklif qilgan do'stlaringiz: {count} ta\n\n"
               f"Sovg'a: {PREMIUM_LIMIT} ta do'st taklif qiling va Premium oling!\n"
               f"Sizning linkingiz:\n`{link}`")
        bot.send_message(uid, msg, parse_mode="Markdown")

    elif message.text == "🔍 Suhbatdosh topish":
        bot.send_message(uid, "🔍 Suhbatdosh qidirilmoqda... (Tez kunda ishga tushadi)")

# --- ISHGA TUSHIRISH ---
if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
    
