import telebot
import os
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. RENDER UCHUN FLASK ---
app = Flask('')

@app.route('/')
def home():
    return "Bot holati: Faol!"

def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. SOZLAMALAR ---
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 8770983969 

if not API_TOKEN:
    print("XATO: BOT_TOKEN topilmadi!")
    exit()

bot = telebot.TeleBot(API_TOKEN)

config = {
    'check_sub': True,
    'show_stats': True,
    'channel_username': '@kanal_username', 
    'required_referrals': 3
}

user_data = {} 
waiting_users = []
active_chats = {}

# --- 3. YORDAMCHI FUNKSIYALAR ---
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

# --- 4. ADMIN PANEL ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Menyu" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    sub_btn = "Obuna: ✅ YOQIQ" if config['check_sub'] else "Obuna: ❌ O'CHIQ"
    stats_btn = "Statistika: ✅ YOQIQ" if config['show_stats'] else "Statistika: ❌ O'CHIQ"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(sub_btn, callback_data="toggle_sub"))
    markup.add(types.InlineKeyboardButton(stats_btn, callback_data="toggle_stats"))
    markup.add(types.InlineKeyboardButton(f"Premium limiti: {config['required_referrals']}", callback_data="change_limit"))
    markup.add(types.InlineKeyboardButton("📢 Reklama yuborish", callback_data="broadcast"))
    markup.add(types.InlineKeyboardButton("🔑 Egalikni o'tkazish", callback_data="transfer"))
    
    text = "⚙️ <b>Admin boshqaruv paneli</b>"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.message.chat.id
    if user_id == ADMIN_ID:
        if call.data == "toggle_sub":
            config['check_sub'] = not config['check_sub']
            bot.delete_message(user_id, call.message.message_id)
            admin_panel(call.message)
        elif call.data == "toggle_stats":
            config['show_stats'] = not config['show_stats']
            bot.delete_message(user_id, call.message.message_id)
            admin_panel(call.message)
        elif call.data == "broadcast":
            msg = bot.send_message(user_id, "Xabar yozing:")
            bot.register_next_step_handler(msg, send_broadcast)
        elif call.data == "change_limit":
            msg = bot.send_message(user_id, "Yangi limit:")
            bot.register_next_step_handler(msg, update_limit)
        elif call.data == "transfer":
            msg = bot.send_message(user_id, "Yangi admin ID:")
            bot.register_next_step_handler(msg, process_transfer)

    if call.data.startswith("set_"):
        gender = "Erkak" if call.data == "set_male" else "Ayol"
        user_data[user_id]['gender'] = gender
        bot.edit_message_text(f"Jinsi: {gender} ✅", chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, "Tayyor!", reply_markup=get_main_menu(user_id))

def send_broadcast(message):
    for uid in user_data:
        try: bot.send_message(uid, message.text)
        except: continue
    bot.send_message(ADMIN_ID, "Yuborildi.")

def update_limit(message):
    try: config['required_referrals'] = int(message.text)
    except: pass
    bot.send_message(ADMIN_ID, "Saqlandi.")

def process_transfer(message):
    global ADMIN_ID
    try: ADMIN_ID = int(message.text)
    except: pass
    bot.send_message(message.chat.id, "O'tkazildi.")

# --- 5. ASOSIY LOGIKA (QIDIRUV VA PREMIUM) ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {'gender': None, 'referrals': [], 'is_premium': False}
        args = message.text.split()
        if len(args) > 1:
            try:
                inviter = int(args[1])
                if inviter in user_data and user_id not in user_data[inviter]['referrals']:
                    user_data[inviter]['referrals'].append(user_id)
                    if len(user_data[inviter]['referrals']) >= config['required_referrals']:
                        user_data[inviter]['is_premium'] = True
            except: pass

    if config['check_sub'] and not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("A'zo bo'lish", url=f"https://t.me/{config['channel_username'].replace('@', '')}"))
        bot.send_message(user_id, "⚠️ Kanalga a'zo bo'ling!", reply_markup=markup)
        return

    if user_data[user_id]['gender'] is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Erkak 👨", callback_data="set_male"),
                   types.InlineKeyboardButton("Ayol 👩", callback_data="set_female"))
        bot.send_message(user_id, "Jinsingizni tanlang:", reply_markup=markup)
        return

    bot.send_message(user_id, "Xush kelibsiz!", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "🔍 Suhbatdosh topish")
def search(message):
    user_id = message.chat.id
    if user_id in active_chats:
        bot.send_message(user_id, "Siz suhbatdasiz!")
        return
    if user_id in waiting_users:
        bot.send_message(user_id, "🔍 Qidirilmoqda...")
        return

    if waiting_users:
        p_id = waiting_users.pop(0)
        active_chats[user_id], active_chats[p_id] = p_id, user_id
        
        # Jinsni ko'rsatish mantiqi:
        u_gender = user_data[user_id]['gender']
        p_gender = user_data[p_id]['gender']
        
        # Foydalanuvchi premium bo'lsa sherigining jinsini ko'radi, aks holda yo'q
        u_msg = f"🔍 Suhbatdosh topildi!\n👫 Sherik jinsi: {p_gender if user_data[user_id]['is_premium'] else '🔒 Faqat Premium uchun'}"
        p_msg = f"🔍 Suhbatdosh topildi!\n👫 Sherik jinsi: {u_gender if user_data[p_id]['is_premium'] else '🔒 Faqat Premium uchun'}"
        
        bot.send_message(user_id, u_msg, reply_markup=get_main_menu(user_id))
        bot.send_message(p_id, p_msg, reply_markup=get_main_menu(p_id))
    else:
        if user_data[user_id].get('is_premium'): waiting_users.insert(0, user_id)
        else: waiting_users.append(user_id)
        bot.send_message(user_id, "🔍 Qidirilmoqda...")

@bot.message_handler(func=lambda message: message.text == "👤 Profilim")
def profile(message):
    uid = message.chat.id
    data = user_data.get(uid, {})
    stats_text = f"\n📊 Bot a'zolari: {len(user_data)}" if config['show_stats'] else ""
    status = "Premium ✨" if data.get('is_premium') else "Oddiy"
    text = (f"👤 <b>Profilingiz:</b>\n\n🆔 ID: <code>{uid}</code>\n"
            f"👫 Jinsi: {data.get('gender')}\n💎 Status: {status}\n"
            f"👥 Takliflar: {len(data.get('referrals', []))}/{config['required_referrals']}{stats_text}")
    bot.send_message(uid, text, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "🎁 Premium & Takliflar")
def premium_page(message):
    uid = message.chat.id
    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start={uid}"
    text = (f"🎁 <b>Premium oling!</b>\n\n"
            f"Premium afzalliklari:\n1. Sherik jinsini ko'rish 👫\n2. Qidiruvda navbatsiz ulanish ⚡\n\n"
            f"Limit: <b>{config['required_referrals']} ta</b> do'st.\n🔗 Havola: {link}")
    bot.send_message(uid, text, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == "❌ Suhbatni to'xtatish")
def stop(message):
    uid = message.chat.id
    if uid in active_chats:
        p_id = active_chats.pop(uid)
        if p_id in active_chats: active_chats.pop(p_id)
        bot.send_message(uid, "Suhbat to'xtatildi.", reply_markup=get_main_menu(uid))
        bot.send_message(p_id, "Suhbatdosh tark etdi.", reply_markup=get_main_menu(p_id))
    elif uid in waiting_users:
        waiting_users.remove(uid)
        bot.send_message(uid, "Bekor qilindi.")

@bot.message_handler(func=lambda message: True)
def echo(message):
    uid = message.chat.id
    if uid in active_chats:
        try: bot.send_message(active_chats[uid], message.text)
        except: bot.send_message(uid, "Xabar bormadi.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True)
