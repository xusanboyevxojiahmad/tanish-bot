import os
import time
import requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import telebot
from telebot import types

# -------------------- 1. FLASK SERVER --------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot holati: 24/7 ishlayapti ✅"

def ping_self():
    """Render serverini uyquga ketmasligi uchun ping qiladi"""
    try:
        url = os.environ.get("SELF_URL", "https://tanish-bot.onrender.com")
        requests.get(url, timeout=5)
        print("Ping: Bot serveri uyg'otildi ✅")
    except Exception as e:
        print(f"Ping xatosi: {e}")

# Har 90 soniyada ping qilish (1.5 minut)
scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_self, trigger="interval", seconds=90)
scheduler.start()

def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# -------------------- 2. TELEBOT CONFIG --------------------
API_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 8770983969))

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(API_TOKEN)

# -------------------- 3. DATA STRUCTURES --------------------
config = {
    'check_sub': True,
    'show_stats': True,
    'channel_username': '@kanal_username',
    'required_referrals': 3
}

user_data = {}        # foydalanuvchi malumotlari
waiting_users = []    # qidiruvdagi foydalanuvchilar
active_chats = {}     # faol suhbatlar

# -------------------- 4. YORDAMCHI FUNKSIYALAR --------------------
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Suhbatdosh topish", "❌ Suhbatni to'xtatish")
    markup.add("👤 Profilim", "🎁 Premium & Takliflar")
    if user_id == ADMIN_ID:
        markup.add("⚙️ Admin Menyu")
    return markup

def check_sub(user_id):
    if not config['check_sub']: return True
    try:
        status = bot.get_chat_member(chat_id=config['channel_username'], user_id=user_id).status
        return status != 'left'
    except: return True

# -------------------- 5. ADMIN PANEL --------------------
@bot.message_handler(func=lambda m: m.text=="⚙️ Admin Menyu" and m.from_user.id==ADMIN_ID)
def admin_panel(message):
    sub_status = "✅ YOQIQ" if config['check_sub'] else "❌ O'CHIQ"
    stats_status = "✅ YOQIQ" if config['show_stats'] else "❌ O'CHIQ"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(f"Obuna: {sub_status}", callback_data="toggle_sub"),
        types.InlineKeyboardButton(f"Statistika: {stats_status}", callback_data="toggle_stats")
    )
    markup.add(
        types.InlineKeyboardButton(f"📢 Kanal: {config['channel_username']}", callback_data="set_channel"),
        types.InlineKeyboardButton(f"💎 Premium limiti: {config['required_referrals']}", callback_data="change_limit")
    )
    markup.add(types.InlineKeyboardButton("🚀 Reklama yuborish", callback_data="broadcast"))
    markup.add(types.InlineKeyboardButton("🔑 Egalikni o'tkazish", callback_data="transfer"))

    text = f"⚙️ <b>Admin boshqaruv paneli</b>\n\n📊 Jami foydalanuvchilar: {len(user_data)}\n📢 Kanal: {config['channel_username']}"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id
    if uid == ADMIN_ID:
        if call.data == "toggle_sub":
            config['check_sub'] = not config['check_sub']
            bot.delete_message(uid, call.message.message_id)
            admin_panel(call.message)
        elif call.data == "toggle_stats":
            config['show_stats'] = not config['show_stats']
            bot.delete_message(uid, call.message.message_id)
            admin_panel(call.message)
        elif call.data == "set_channel":
            msg = bot.send_message(uid, "Yangi kanal @username yuboring:")
            bot.register_next_step_handler(msg, update_channel)
        elif call.data == "change_limit":
            msg = bot.send_message(uid, "Yangi limitni yuboring:")
            bot.register_next_step_handler(msg, update_limit)
        elif call.data == "broadcast":
            msg = bot.send_message(uid, "Reklama xabarini yozing:")
            bot.register_next_step_handler(msg, send_broadcast)

def update_channel(message):
    if message.text.startswith("@"):
        config['channel_username'] = message.text.strip()
    admin_panel(message)

def update_limit(message):
    try: config['required_referrals'] = int(message.text)
    except: pass
    admin_panel(message)

def send_broadcast(message):
    for uid in user_data:
        try: bot.send_message(uid, message.text)
        except: continue
    bot.send_message(ADMIN_ID, "📢 Reklama yuborildi.")

# -------------------- 6. SUHBAT LOGIKASI (1-ga-1) --------------------
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    if uid not in user_data:
        user_data[uid] = {'gender': None, 'referrals': [], 'is_premium': False}
        args = message.text.split()
        if len(args) > 1:
            try:
                inviter = int(args[1])
                if inviter in user_data and uid not in user_data[inviter]['referrals'] and inviter != uid:
                    user_data[inviter]['referrals'].append(uid)
                    if len(user_data[inviter]['referrals'])>=config['required_referrals']:
                        user_data[inviter]['is_premium'] = True
                        bot.send_message(inviter, "🎁 Tabriklaymiz! Sizga PREMIUM statusi berildi!")
            except: pass

    if config['check_sub'] and not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kanalga a'zo bo'lish", url=f"https://t.me/{config['channel_username'].replace('@','')}"))
        bot.send_message(uid, "⚠️ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=markup)
        return

    if user_data[uid]['gender'] is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Erkak 👨", callback_data="set_male"),
                   types.InlineKeyboardButton("Ayol 👩", callback_data="set_female"))
        bot.send_message(uid, "Jinsingizni tanlang:", reply_markup=markup)
        return

    bot.send_message(uid, "Xush kelibsiz!", reply_markup=get_main_menu(uid))

@bot.message_handler(func=lambda m: m.text=="🔍 Suhbatdosh topish")
def find_menu(message):
    uid = message.chat.id
    if uid in active_chats: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ayol 👩", callback_data="find_female"),
               types.InlineKeyboardButton("Erkak 👨", callback_data="find_male"))
    markup.add(types.InlineKeyboardButton("Tasodifiy 🎲", callback_data="find_random"))
    bot.send_message(uid, "Kim bilan suhbatlashmoqchisiz?", reply_markup=markup)

def search_partner(uid, mode, msg_id):
    if uid in waiting_users or uid in active_chats: return
    found = False
    for partner_id in waiting_users:
        p_gender = user_data[partner_id]['gender']
        match = (mode=="random") or (mode=="female" and p_gender=="Ayol") or (mode=="male" and p_gender=="Erkak")
        if match:
            waiting_users.remove(partner_id)
            active_chats[uid], active_chats[partner_id] = partner_id, uid
            bot.edit_message_text("🔍 Suhbatdosh topildi!", chat_id=uid, message_id=msg_id)
            bot.send_message(uid, f"Sherik jinsi: {p_gender if user_data[uid]['is_premium'] else '🔒 Faqat Premium'}")
            bot.send_message(partner_id, f"Sherik jinsi: {user_data[uid]['gender'] if user_data[partner_id]['is_premium'] else '🔒 Faqat Premium'}")
            found=True; break
    if not found:
        waiting_users.append(uid)
        bot.edit_message_text("🔍 Suhbatdosh qidirilmoqda...", chat_id=uid, message_id=msg_id)

@bot.message_handler(func=lambda m: m.text=="❌ Suhbatni to'xtatish")
def stop(message):
    uid = message.chat.id
    if uid in active_chats:
        p_id = active_chats.pop(uid)
        active_chats.pop(p_id)
        bot.send_message(uid, "To'xtatildi.", reply_markup=get_main_menu(uid))
        bot.send_message(p_id, "Sherik chiqib ketdi.", reply_markup=get_main_menu(p_id))
    elif uid in waiting_users:
        waiting_users.remove(uid)
        bot.send_message(uid, "Qidiruv to'xtatildi.")

@bot.message_handler(func=lambda m: True)
def echo(message):
    uid = message.chat.id
    if uid in active_chats:
        try: bot.send_message(active_chats[uid], message.text)
        except: bot.send_message(uid, "Xabar yuborilmadi.")

# -------------------- 7. BOTNI 24/7 ISHGA TUSHIRISH --------------------
if __name__=="__main__":
    keep_alive()
    print("Bot 24/7 rejimda ishga tushdi...")
    while True:
        try:
            bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=5)
        except Exception as e:
            print(f"Xato yuz berdi: {e} | 2 soniyadan keyin qayta ishga tushadi")
            time.sleep(2)
