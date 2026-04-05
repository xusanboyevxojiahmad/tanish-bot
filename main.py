import telebot
from telebot import types
import sqlite3
import time

# --- SOZLAMALAR ---
API_TOKEN = 'BOT_TOKENINI_SHU_YERGA_YOZING'
ADMIN_ID = 123456789  # O'zingizning ID raqamingizni yozing
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
        'must_sub': "Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
        'check_btn': "Tekshirish ✅",
        'not_sub': "Siz hali barcha kanallarga a'zo bo'lmadingiz! ❌",
        'finding': "Suhbatdosh qidirilmoqda... /stop orqali to'xtatish mumkin.",
        'found': "Suhbatdosh topildi! Salom deb yozishingiz mumkin.",
        'stop': "Suhbat tugatildi.",
        'no_prem': "Bu funksiya faqat Premium uchun! 2 ta do'st taklif qiling.",
        'partner_left': "Suhbatdosh suhbatni tark etdi."
    },
    'ru': {
        'welcome': "Добро пожаловать! Введите имя и фамилию:",
        'select_lang': "Выберите язык:",
        'main_menu': "Главное меню",
        'search': "🔍 Поиск собеседника",
        'friends': "👥 Мои друзья",
        'premium': "🎁 Премиум и приглашения",
        'must_sub': "Для использования бота подпишитесь на каналы:",
        'check_btn': "Проверить ✅",
        'not_sub': "Вы еще не подписались на все каналы! ❌",
        'finding': "Поиск собеседника... Можно остановить через /stop.",
        'found': "Собеседник найден! Можете поздороваться.",
        'stop': "Чат завершен.",
        'no_prem': "Эта функция только для Премиум! Пригласите 2 друзей.",
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
        'finding': "Searching... You can stop with /stop.",
        'found': "Partner found! You can say hello.",
        'stop': "Chat ended.",
        'no_prem': "This feature is for Premium only! Invite 2 friends.",
        'partner_left': "Your partner left the chat."
    }
}

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, full_name TEXT, age INTEGER, gender TEXT,
        is_searching TEXT DEFAULT NULL, partner_id INTEGER DEFAULT NULL,
        invite_count INTEGER DEFAULT 0, premium_until INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0, lang TEXT DEFAULT 'uz')''')
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS friends (u1 INTEGER, u2 INTEGER, PRIMARY KEY(u1, u2))')
    conn.commit()
    conn.close()

def get_user(uid):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    conn.close()
    return res

# --- KANAL TEKSHIRUV ---
def check_subs(uid):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    conn.close()
    for (ch_id,) in channels:
        try:
            if bot.get_chat_member(ch_id, uid).status == 'left': return False
        except: continue
    return True

# --- ASOSIY HANDLERLAR ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = get_user(uid)
    
    # Referal tizimi
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and not user:
        ref_id = int(args[1])
        if ref_id != uid:
            conn = sqlite3.connect('dating_bot.db')
            c = conn.cursor()
            c.execute("UPDATE users SET invite_count = invite_count + 1 WHERE user_id = ?", (ref_id,))
            c.execute("SELECT invite_count, premium_until FROM users WHERE user_id = ?", (ref_id,))
            cnt, prem = c.fetchone()
            if cnt >= 2:
                new_p = max(prem, time.time()) + (30*24*3600)
                c.execute("UPDATE users SET premium_until = ?, invite_count = 0 WHERE user_id = ?", (new_p, ref_id))
                bot.send_message(ref_id, "🎁 +30 kun Premium!")
            conn.commit()
            conn.close()

    if not user:
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("UZ 🇺🇿", callback_data="slang_uz"),
              types.InlineKeyboardButton("RU 🇷🇺", callback_data="slang_ru"),
              types.InlineKeyboardButton("EN 🇺🇸", callback_data="slang_en"))
        bot.send_message(uid, "Select Language / Tilni tanlang:", reply_markup=m)
    else:
        if check_subs(uid): main_menu(uid)
        else: show_sub_channels(uid)

def show_sub_channels(uid):
    user = get_user(uid)
    lang = user[9] if user else 'uz'
    m = types.InlineKeyboardMarkup()
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    for (ch,) in cursor.fetchall():
        m.add(types.InlineKeyboardButton("Kanalga o'tish", url=f"https://t.me/{ch[1:]}"))
    m.add(types.InlineKeyboardButton(STRINGS[lang]['check_btn'], callback_data="recheck"))
    bot.send_message(uid, STRINGS[lang]['must_sub'], reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data.startswith('slang_'))
def set_lang(call):
    lang = call.data.split('_')[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, STRINGS[lang]['welcome'])
    bot.register_next_step_handler(msg, reg_name, lang)

def reg_name(message, lang):
    name = message.text
    msg = bot.send_message(message.chat.id, "Yoshingizni kiriting / Введите возраст:")
    bot.register_next_step_handler(msg, reg_age, lang, name)

def reg_age(message, lang, name):
    age = message.text
    if not age.isdigit():
        msg = bot.send_message(message.chat.id, "Raqam yozing:")
        bot.register_next_step_handler(msg, reg_age, lang, name)
        return
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    m.add("Erkak 👨", "Ayol 👩")
    msg = bot.send_message(message.chat.id, "Jins / Пол:", reply_markup=m)
    bot.register_next_step_handler(msg, reg_final, lang, name, age)

def reg_final(message, lang, name, age):
    gender = "erkak" if "Erkak" in message.text else "ayol"
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, full_name, age, gender, lang) VALUES (?,?,?,?,?)",
                   (message.chat.id, name, age, gender, lang))
    conn.commit()
    conn.close()
    main_menu(message.chat.id)

def main_menu(uid):
    user = get_user(uid)
    lang = user[9]
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(STRINGS[lang]['search'])
    m.add(STRINGS[lang]['friends'], STRINGS[lang]['premium'])
    if uid == ADMIN_ID: m.add("⚙️ Admin")
    bot.send_message(uid, STRINGS[lang]['main_menu'], reply_markup=m)

# --- CHAT VA QIDIRUV ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'voice', 'video'])
def global_handler(message):
    uid = message.chat.id
    user = get_user(uid)
    if not user: return
    lang = user[9]

    # Kanal tekshiruvi
    if not check_subs(uid):
        show_sub_channels(uid)
        return

    # Menyu tugmalari
    if message.text == STRINGS[lang]['search']:
        m = types.ReplyKeyboardMarkup(resize_keyboard=True)
        m.add("🎲 Random")
        if user[7] > time.time():
            m.add("👨 Erkak", "👩 Ayol")
        else:
            m.add("🔒 Erkak (Premium)", "🔒 Ayol (Premium)")
        m.add("⬅️ Back")
        bot.send_message(uid, "Search:", reply_markup=m)
        return

    if "Random" in message.text or "Erkak" in message.text or "Ayol" in message.text:
        target = "any"
        if "Erkak" in message.text: target = "erkak"
        if "Ayol" in message.text: target = "ayol"
        
        conn = sqlite3.connect('dating_bot.db')
        c = conn.cursor()
        query = "SELECT user_id FROM users WHERE is_searching IS NOT NULL AND user_id != ?"
        params = [uid]
        if target != "any": query += " AND gender = ?"; params.append(target)
        
        c.execute(query + " LIMIT 1", params)
        partner = c.fetchone()
        if partner:
            p_id = partner[0]
            c.execute("UPDATE users SET is_searching = NULL, partner_id = ? WHERE user_id = ?", (p_id, uid))
            c.execute("UPDATE users SET is_searching = NULL, partner_id = ? WHERE user_id = ?", (uid, p_id))
            bot.send_message(uid, STRINGS[lang]['found'], reply_markup=chat_kb())
            bot.send_message(p_id, STRINGS[get_user(p_id)[9]]['found'], reply_markup=chat_kb())
        else:
            c.execute("UPDATE users SET is_searching = ? WHERE user_id = ?", (target, uid))
            bot.send_message(uid, STRINGS[lang]['finding'])
        conn.commit()
        conn.close()
        return

    if message.text == "❌ Stop" or message.text == "/stop":
        if user[5]:
            p_id = user[5]
            bot.send_message(p_id, STRINGS[get_user(p_id)[9]]['partner_left'])
            conn = sqlite3.connect('dating_bot.db')
            c = conn.cursor()
            c.execute("UPDATE users SET partner_id = NULL WHERE user_id IN (?,?)", (uid, p_id))
            conn.commit()
            conn.close()
        bot.send_message(uid, STRINGS[lang]['stop'])
        main_menu(uid)
        return

    # Xabarni yuborish
    if user[5]:
        bot.copy_message(user[5], uid, message.message_id)

def chat_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("❌ Stop")
    return m

# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == '__main__':
    init_db()
    print("Bot is running...")
    bot.infinity_polling()
  
