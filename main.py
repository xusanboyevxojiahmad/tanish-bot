import os  # Bu kutubxona o'zgaruvchilarni o'qish uchun kerak
import telebot
from telebot import types
import sqlite3
import time

# --- SOZLAMALAR ---
# Tokenni Render "Variables" bo'limidan oladi
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8329231121 # Sizning ID raqamingiz

bot = telebot.TeleBot(API_TOKEN)

# --- TILLAR LUG'ATI ---
STRINGS = {
    'uz': {
        'welcome': "Xush kelibsiz! Ism va familiyangizni kiriting:",
        'select_lang': "Tilni tanlang:",
        'main_menu': "Asosiy menyu",
        'search': "🔍 Suhbatdosh topish",
        'friends': "👥 Do'stlarim",
        'premium': "🎁 Premium & Takliflar",
        'must_sub': "Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz shart:",
        'check_btn': "Tekshirish ✅",
        'not_sub': "Siz hali barcha kanallarga a'zo bo'lmadingiz! ❌",
        'finding': "Suhbatdosh qidirilmoqda...",
        'found': "Suhbatdosh topildi! Salom deb yozishingiz mumkin.",
        'stop': "Suhbat tugatildi.",
        'partner_left': "Suhbatdosh suhbatni tark etdi."
    },
    'ru': {
        'welcome': "Добро пожаловать! Введите имя и фамилию:",
        'select_lang': "Выберите язык:",
        'main_menu': "Главное меню",
        'search': "🔍 Поиск собеседника",
        'friends': "👥 Мои друзья",
        'premium': "🎁 Премиум и приглашения",
        'must_sub': "Чтобы пользоваться ботом, подпишитесь на каналы:",
        'check_btn': "Проверить ✅",
        'not_sub': "Вы еще не подписались на все каналы! ❌",
        'finding': "Поиск собеседника...",
        'found': "Собеседник найден! Можете поздороваться.",
        'stop': "Чат завершен.",
        'partner_left': "Собеседник покинул чат."
    },
    'en': {
        'welcome': "Welcome! Enter your full name:",
        'select_lang': "Select language:",
        'main_menu': "Main menu",
        'search': "🔍 Find a partner",
        'friends': "👥 My Friends",
        'premium': "🎁 Premium & Invites",
        'must_sub': "To use the bot, please subscribe to these channels:",
        'check_btn': "Check ✅",
        'not_sub': "You haven't subscribed to all channels yet! ❌",
        'finding': "Searching...",
        'found': "Partner found! You can say hello.",
        'stop': "Chat ended.",
        'partner_left': "Your partner left the chat."
    }
}

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, full_name TEXT, age INTEGER, gender TEXT,
        is_searching TEXT DEFAULT NULL, partner_id INTEGER DEFAULT NULL,
        invite_count INTEGER DEFAULT 0, premium_until INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0, lang TEXT DEFAULT 'uz')''')
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY)')
    # Adminni bazada saqlash (topshirish funksiyasi uchun)
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("admin_id", ?)', (str(ADMIN_ID),))
    conn.commit()
    conn.close()

def get_current_admin():
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_id'")
    res = cursor.fetchone()
    conn.close()
    return int(res[0]) if res else ADMIN_ID

def get_user_data(uid):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    conn.close()
    return res

# --- KANALGA A'ZOLIKNI TEKSHIRISH ---
def is_subscribed(uid):
    current_admin = get_current_admin()
    if uid == current_admin: return True
    
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    conn.close()
    
    for (ch_id,) in channels:
        try:
            status = bot.get_chat_member(ch_id, uid).status
            if status == 'left': return False
        except Exception:
            continue
    return True

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin" and m.chat.id == get_current_admin())
def admin_menu(message):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("📢 Kanallar sozlamasi", "👤 Adminlikni topshirish")
    m.add("⬅️ Orqaga")
    bot.send_message(get_current_admin(), "Admin bo'limi:", reply_markup=m)

# --- ADMINLIKNI TOPSHIRISH ---
@bot.message_handler(func=lambda m: m.text == "👤 Adminlikni topshirish" and m.chat.id == get_current_admin())
def transfer_admin(message):
    msg = bot.send_message(get_current_admin(), "Yangi adminning Telegram ID raqamini yuboring:\n(Ehtiyot bo'ling, bu amalni ortga qaytarib bo'lmaydi!)")
    bot.register_next_step_handler(msg, process_transfer)

def process_transfer(message):
    new_id = message.text
    if new_id.isdigit():
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'admin_id'", (new_id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"Adminlik huquqi {new_id} ga muvaffaqiyatli topshirildi! ✅")
        bot.send_message(int(new_id), "Tabriklaymiz! Siz ushbu botning yangi admini etib tayinlandingiz. ⚙️")
    else:
        bot.send_message(message.chat.id, "Xato ID! Faqat raqamlardan iborat bo'lishi kerak.")

# --- KANAL SOZLAMALARI ---
@bot.message_handler(func=lambda m: m.text == "📢 Kanallar sozlamasi" and m.chat.id == get_current_admin())
def channel_settings(message):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    rows = cursor.fetchall()
    conn.close()
    
    txt = "Majburiy kanallar ro'yxati:\n\n" + "\n".join([r[0] for r in rows]) if rows else "Kanallar yo'q."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Qo'shish", callback_data="add"),
               types.InlineKeyboardButton("🗑 O'chirish", callback_data="del"))
    bot.send_message(get_current_admin(), txt, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "add")
def add_ch(call):
    msg = bot.send_message(get_current_admin(), "Kanal userini yuboring (Masalan: @kanal_nomi):")
    bot.register_next_step_handler(msg, save_ch)

def save_ch(message):
    if message.text.startswith("@"):
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO channels VALUES (?)", (message.text,))
        conn.commit()
        conn.close()
        bot.send_message(get_current_admin(), "Kanal bazaga qo'shildi! ✅")
    else:
        bot.send_message(get_current_admin(), "Xato! Link @ bilan boshlanishi shart.")

@bot.callback_query_handler(func=lambda c: c.data == "del")
def del_ch(call):
    msg = bot.send_message(get_current_admin(), "O'chirmoqchi bo'lgan kanal userini yuboring:")
    bot.register_next_step_handler(msg, remove_ch)

def remove_ch(message):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (message.text,))
    conn.commit()
    conn.close()
    bot.send_message(get_current_admin(), "Kanal o'chirildi! 🗑")

# --- START VA ASOSIY LOGIKA ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.chat.id
    user = get_user_data(uid)
    
    if not user:
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("UZ 🇺🇿", callback_data="l_uz"),
              types.InlineKeyboardButton("RU 🇷🇺", callback_data="l_ru"),
              types.InlineKeyboardButton("EN 🇺🇸", callback_data="l_en"))
        bot.send_message(uid, "Tilni tanlang / Выберите язык:", reply_markup=m)
    else:
        if is_subscribed(uid): show_main_menu(uid)
        else: force_sub_msg(uid)

def show_main_menu(uid):
    user = get_user_data(uid)
    lang = user[9]
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(STRINGS[lang]['search'])
    m.add(STRINGS[lang]['friends'], STRINGS[lang]['premium'])
    if uid == get_current_admin(): m.add("⚙️ Admin")
    bot.send_message(uid, STRINGS[lang]['main_menu'], reply_markup=m)

def force_sub_msg(uid):
    user = get_user_data(uid)
    lang = user[9] if user else 'uz'
    m = types.InlineKeyboardMarkup()
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    for (ch,) in cursor.fetchall():
        m.add(types.InlineKeyboardButton("Kanalga a'zo bo'lish ➡️", url=f"https://t.me/{ch[1:]}"))
    m.add(types.InlineKeyboardButton(STRINGS[lang]['check_btn'], callback_data="verify"))
    bot.send_message(uid, STRINGS[lang]['must_sub'], reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify_sub(call):
    if is_subscribed(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "Siz hali a'zo emassiz! ❌", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith('l_'))
def select_lang(call):
    lang = call.data.split('_')[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, STRINGS[lang]['welcome'])
    bot.register_next_step_handler(msg, get_name, lang)

def get_name(message, lang):
    name = message.text
    msg = bot.send_message(message.chat.id, "Yoshingizni yozing:")
    bot.register_next_step_handler(msg, get_age, lang, name)

def get_age(message, lang, name):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "Faqat raqam!")
        bot.register_next_step_handler(msg, get_age, lang, name)
        return
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    m.add("Erkak 👨", "Ayol 👩")
    msg = bot.send_message(message.chat.id, "Jinsingiz:", reply_markup=m)
    bot.register_next_step_handler(msg, finish_reg, lang, name, message.text)

def finish_reg(message, lang, name, age):
    gender = "erkak" if "Erkak" in message.text else "ayol"
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, full_name, age, gender, lang) VALUES (?,?,?,?,?)",
                   (message.chat.id, name, int(age), gender, lang))
    conn.commit()
    conn.close()
    show_main_menu(message.chat.id)

# --- CHAT MANAGER ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'voice', 'video'])
def main_handler(message):
    uid = message.chat.id
    user = get_user_data(uid)
    if not user: return
    lang = user[9]

    if not is_subscribed(uid):
        force_sub_msg(uid)
        return

    if message.text == "⬅️ Orqaga":
        show_main_menu(uid)
        return

    if user[5]: # Suhbatdosh bo'lsa
        if message.text == "❌ Stop" or message.text == "/stop":
            p_id = user[5]
            bot.send_message(p_id, STRINGS[get_user_data(p_id)[9]]['partner_left'])
            conn = sqlite3.connect('dating_bot.db')
            c = conn.cursor()
            c.execute("UPDATE users SET partner_id = NULL WHERE user_id IN (?,?)", (uid, p_id))
            conn.commit()
            conn.close()
            bot.send_message(uid, STRINGS[lang]['stop'])
            show_main_menu(uid)
        else:
            bot.copy_message(user[5], uid, message.message_id)

if __name__ == '__main__':
    init_db()
    print("Bot muvaffaqiyatli yondi...")
    bot.infinity_polling()
    
