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
ADMIN_ID = 8770983969  # Asosiy admin ID

if not API_TOKEN:
    print("XATO: BOT_TOKEN topilmadi!")
    exit()

bot = telebot.TeleBot(API_TOKEN)

# Dinamik Sozlamalar (Admin o'zgartira oladi)
config = {
    'check_sub': True,               # Obunani tekshirish (Yoqiq/O'chiq)
    'channel_username': '@kanal_username', 
    'required_referrals': 3          # Premium uchun nechta do'st kerak
}

# Ma'lumotlar
user_data = {} 
waiting_users = []
active_chats = {}

# --- 3. YORDAMCHI FUNKSIYALAR ---
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Suhbatdosh topish", "❌ Suhbatni to'xtatish")
    markup.add("👤 Profilim", "🎁 Premium & Takliflar")
    if user_id == ADMIN_ID:
        markup.add("⚙️ Bot Sozlamalari")
    return markup

def check_sub(user_id):
    if not config['check_sub']: return True
    try:
        status = bot.get_chat_member(chat_id=config['channel_username'], user_id=user_id).status
        return status != 'left'
    except: return True

# --- 4. ADMIN PANEL (SOZLAMALAR) ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Bot Sozlamalari" and message.from_user.id == ADMIN_ID)
def admin_settings(message):
    sub_status = "✅ YOQIQ" if config['check_sub'] else "❌ O'CHIQ"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Obuna tekshirish: {sub_status}", callback_data="toggle_sub"))
    markup.add(types.InlineKeyboardButton(f"Premium limiti: {config['required_referrals']} ta", callback_data="change_ref_limit"))
    markup.add(types.InlineKeyboardButton("📢 Reklama yuborish", callback_data="broadcast"))
    markup.add(types.InlineKeyboardButton("🔑 Egalikni o'tkazish", callback_data="transfer_owner"))
    
    text = (f"⚙️ **Bot sozlamalari:**\n\n"
            f"📊 Jami foydalanuvchilar: {len(user_data)}\n"
            f"📢 Kanal: {config['channel_username']}\n"
            f"💎 Premium limiti: {config['required_referrals']} ta do'st")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    global ADMIN_ID
    user_id = call.message.chat.id
    
    if call.data == "toggle_sub":
        config['check_sub'] = not config['check_sub']
        bot.answer_callback_query(call.id, "Obuna tekshirish o'zgartirildi")
        admin_settings(call.message) # Menyuni yangilash
        bot.delete_message(user_id, call.message.message_id)

    elif call.data == "change_ref_limit":
        msg = bot.send_message(user_id, "Premium uchun yangi do'stlar sonini kiriting (masalan: 5):")
        bot.register_next_step_handler(msg, update_ref_limit)

    elif call.data == "broadcast":
        msg = bot.send_message(user_id, "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:")
        bot.register_next_step_handler(msg, send_broadcast)

    elif call.data == "transfer_owner":
        msg = bot.send_message(user_id, "Yangi admin ID raqamini yuboring:")
        bot.register_next_step_handler(msg, process_transfer)
        
    elif call.data.startswith("set_"):
        # Jins tanlash logic
        gender = "Erkak" if call.data == "set_male" else "Ayol"
        user_data[user_id]['gender'] = gender
        bot.answer_callback_query(call.id, f"Tanlandi: {gender}")
        bot.edit_message_text(f"Jinsingiz: {gender} ✅", chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, "Endi suhbatdosh topishingiz mumkin!", reply_markup=get_main_menu(user_id))

# --- STEP HANDLERLAR ---
def update_ref_limit(message):
    try:
        new_limit = int(message.text)
        config['required_referrals'] = new_limit
        bot.send_message(ADMIN_ID, f"✅ Premium limiti {new_limit} taga o'zgartirildi.")
    except:
        bot.send_message(ADMIN_ID, "❌ Faqat raqam kiriting!")

def process_transfer(message):
    global ADMIN_ID
    try:
        new_id = int(message.text)
        ADMIN_ID = new_id
        bot.send_message(message.chat.id, f"✅ Egalik huquqi o'tkazildi!")
    except: bot.send_message(ADMIN_ID, "❌ Xato ID.")

def send_broadcast(message):
    count = 0
    for uid in user_data:
        try:
            bot.send_message(uid, message.text)
            count += 1
        except: continue
    bot.send_message(ADMIN_ID, f"📢 Xabar {count} kishiga yuborildi.")

# --- 5. ASOSIY LOGIKA ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {'gender': None, 'referrals': [], 'is_premium': False}
        
        # Referal tizimi
        args = message.text.split()
        if len(args) > 1:
            try:
                inviter_id = int(args[1])
                if inviter_id in user_data and inviter_id != user_id:
                    if user_id not in user_data[inviter_id]['referrals']:
                        user_data[inviter_id]['referrals'].append(user_id)
                        # Dinamik limitga ko'ra premium berish
                        if len(user_data[inviter_id]['referrals']) >= config['required_referrals']:
                            user_data[inviter_id]['is_premium'] = True
                            bot.send_message(inviter_id, "🎁 Tabriklaymiz! Do'stlaringiz soni yetarli bo'ldi va sizga PREMIUM berildi!")
            except: pass

    if config['check_sub'] and not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kanalga a'zo bo'lish", url=f"https://t.me/{config['channel_username'].replace('@', '')}"))
        bot.send_message(user_id, "⚠️ Botdan foydalanish uchun kanalimizga obuna bo'ling!", reply_markup=markup)
        return

    if user_data[user_id]['gender'] is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Erkak 👨", callback_data="set_male"),
                   types.InlineKeyboardButton("Ayol 👩", callback_data="set_female"))
        bot.send_message(user_id, "Davom etish uchun jinsingizni tanlang:", reply_markup=markup)
        return

    bot.send_message(user_id, "Asosiy menyu:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "👤 Profilim")
def profile(message):
    uid = message.chat.id
    data = user_data.get(uid, {})
    status = "Premium ✨" if data.get('is_premium') else "Oddiy"
    text = (f"👤 **Profilingiz:**\n\n"
            f"🆔 ID: `{uid}`\n"
            f"👫 Jinsi: {data.get('gender')}\n"
            f"💎 Status: {status}\n"
            f"👥 Takliflar: {len(data.get('referrals', []))}/{config['required_referrals']}")
    bot.send_message(uid, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Premium & Takliflar")
def premium_page(message):
    uid = message.chat.id
    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start={uid}"
    bot.send_message(uid, f"🎁 **Premium olish uchun {config['required_referrals']} ta do'st taklif qiling!**\n\nSizning havolangiz:\n{link}")

@bot.message_handler(func=lambda message: message.text == "🔍 Suhbatdosh topish")
def search(message):
    user_id = message.chat.id
    if user_id in active_chats:
        bot.send_message(user_id, "Siz allaqachon suhbatdasiz!")
        return
    if user_id in waiting_users:
        bot.send_message(user_id, "🔍 Qidirilmoqda... kuting.")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        bot.send_message(user_id, f"🔍 Suhbatdosh topildi!\nJinsi: {user_data[partner_id]['gender']}", reply_markup=get_main_menu(user_id))
        bot.send_message(partner_id, f"🔍 Suhbatdosh topildi!\nJinsi: {user_data[user_id]['gender']}", reply_markup=get_main_menu(partner_id))
    else:
        if user_data[user_id].get('is_premium'):
            waiting_users.insert(0, user_id)
        else:
            waiting_users.append(user_id)
        bot.send_message(user_id, "🔍 Suhbatdosh qidirilmoqda...", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "❌ Suhbatni to'xtatish")
def stop_chat(message):
    user_id = message.chat.id
    if user_id in active_chats:
        p_id = active_chats.pop(user_id)
        if p_id in active_chats: active_chats.pop(p_id)
        bot.send_message(user_id, "Suhbat to'xtatildi.", reply_markup=get_main_menu(user_id))
        bot.send_message(p_id, "Suhbatdosh suhbatni to'xtatdi.", reply_markup=get_main_menu(p_id))
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        bot.send_message(user_id, "Qidiruv to'xtatildi.", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: True)
def echo(message):
    user_id = message.chat.id
    if user_id in active_chats:
        try:
            bot.send_message(active_chats[user_id], message.text)
        except:
            bot.send_message(user_id, "Xabar yuborilmadi.")
    else:
        bot.send_message(user_id, "Tugmalardan foydalaning 👇", reply_markup=get_main_menu(user_id))

# --- 6. ISHGA TUSHIRISH ---
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(none_stop=True)
