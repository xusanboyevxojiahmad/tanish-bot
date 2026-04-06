import os
import time
import requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import telebot
from telebot import types

# -------------------- 1. SERVER & KEEP ALIVE --------------------
app = Flask('')
@app.route('/')
def home(): return "Bot Builder Active ✅"

def ping_self():
    try:
        url = os.environ.get("SELF_URL", "https://tanish-bot.onrender.com")
        requests.get(url, timeout=5)
    except: pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_self, trigger="interval", seconds=20)
scheduler.start()

def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# -------------------- 2. SUB-BOT LOGIKASI --------------------
def start_sub_bot(token):
    try:
        s_bot = telebot.TeleBot(token)
        # Nusxa bot kodi (bu yerda faqat suhbat funksiyalari bo'ladi)
        s_bot.infinity_polling(non_stop=True)
    except: pass

# -------------------- 3. ASOSIY BOT SOZLAMALARI --------------------
API_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 8770983969))
bot = telebot.TeleBot(API_TOKEN)

user_data = {} # {id: {'gender': None, 'referrals': [], 'is_premium': False}}
waiting_users = []
active_chats = {}
KARTA_RAQAM = "8600000000000000" # O'z kartangizni yozing

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Suhbatdosh topish", "❌ To'xtatish")
    markup.add("👤 Profilim")
    return markup

# -------------------- 4. START VA RO'YXATDAN O'TISH --------------------
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    if uid not in user_data:
        user_data[uid] = {'gender': None, 'referrals': [], 'is_premium': False}
        # Referral tizimi (1 ta do'st)
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            inviter = int(args[1])
            if inviter in user_data and uid not in user_data[inviter]['referrals'] and inviter != uid:
                user_data[inviter]['referrals'].append(uid)
                user_data[inviter]['is_premium'] = True
                bot.send_message(inviter, "🌟 Tabriklaymiz! Do'stingiz qo'shildi, sizga PREMIUM berildi!")

    if user_data[uid]['gender'] is None:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Erkak 👨", callback_data="set_male"),
               types.InlineKeyboardButton("Ayol 👩", callback_data="set_female"))
        bot.send_message(uid, "Jinsingizni tanlang:", reply_markup=kb)
    else:
        bot.send_message(uid, "Asosiy menyu:", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: call.data in ["set_male", "set_female"])
def save_gender(call):
    uid = call.message.chat.id
    user_data[uid]['gender'] = "Erkak" if call.data == "set_male" else "Ayol"
    bot.delete_message(uid, call.message.message_id)
    bot.send_message(uid, f"Profil saqlandi. /bot_yaratish buyrug'i orqali o'z botingizni ochishingiz mumkin.", reply_markup=get_main_menu())

# -------------------- 5. QIDIRUV LOGIKASI (PREMIUM VA ODDIY) --------------------
@bot.message_handler(func=lambda m: m.text == "🔍 Suhbatdosh topish")
def find_menu(message):
    uid = message.chat.id
    if uid in active_chats: return
    
    is_premium = user_data[uid].get('is_premium') or uid == ADMIN_ID
    markup = types.InlineKeyboardMarkup()
    
    # Premium tugmalar
    text_f = "Ayol 👩" if is_premium else "Ayol 👩 (🔒 Premium)"
    text_m = "Erkak 👨" if is_premium else "Erkak 👨 (🔒 Premium)"
    
    markup.add(types.InlineKeyboardButton(text_f, callback_data="find_female"),
               types.InlineKeyboardButton(text_m, callback_data="find_male"))
    # Hamma uchun tugma
    markup.add(types.InlineKeyboardButton("Tasodifiy 🎲 (Jinsi berkitilgan)", callback_data="find_random"))
    bot.send_message(uid, "Qidiruv turini tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("find_"))
def handle_finding(call):
    uid = call.message.chat.id
    mode = call.data.split("_")[1]
    is_p = user_data[uid].get('is_premium') or uid == ADMIN_ID

    if mode in ["female", "male"] and not is_p:
        bot.answer_callback_query(call.id, "❌ Jinsni tanlab qidirish faqat Premiumlar uchun!", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    search_partner(uid, mode, call.message.message_id)

def search_partner(uid, mode, msg_id):
    if uid in waiting_users: return
    found = False
    for p_id in waiting_users:
        if p_id == uid: continue
        p_gen = user_data[p_id].get('gender')
        
        # Qidiruv sharti
        match = (mode == "random") or \
                (mode == "female" and p_gen == "Ayol") or \
                (mode == "male" and p_gen == "Erkak")
        
        if match:
            waiting_users.remove(p_id)
            active_chats[uid], active_chats[p_id] = p_id, uid
            
            # Tasodifiy bo'lsa jinsini aytmaymiz
            gender_info = f"Sherik jinsi: {p_gen}" if mode != "random" else "Sherik jinsi: 🔒 Berkitilgan"
            
            bot.edit_message_text(f"🔍 Suhbatdosh topildi!\n{gender_info}", uid, msg_id)
            bot.send_message(p_id, "🔍 Suhbatdosh topildi! Salom deb yozing...")
            found = True; break
            
    if not found:
        waiting_users.append(uid)
        bot.edit_message_text("⏳ Suhbatdosh qidirilmoqda...", uid, msg_id)

# -------------------- 6. BOT YARATISH (FAQAT KOMANDA) --------------------
@bot.message_handler(commands=['bot_yaratish'])
def create_bot_cmd(message):
    uid = message.chat.id
    user = user_data.get(uid, {})
    
    if user.get('is_premium') or uid == ADMIN_ID:
        msg = bot.send_message(uid, "🤖 Token yuboring (@BotFather dan olingan):")
        bot.register_next_step_handler(msg, process_new_bot)
    else:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💳 15,000 so'm to'lash", callback_data="buy_premium"))
        ref_link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
        bot.send_message(uid, f"❌ Bot yaratish uchun Premium kerak!\n\n1. To'lov qiling (15k)\n2. Yoki 1 ta do'st taklif qiling.\n\nLink: {ref_link}", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "buy_premium")
def buy_p(call):
    text = f"💰 To'lov: 15,000 so'm\n💳 Karta: `{KARTA_RAQAM}`\n\nChekni adminga yuboring."
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.send_message(ADMIN_ID, f"🔔 To'lov kutilmoqda: {call.from_user.id}\nRuxsat berish: /give_{call.message.chat.id}")

def process_new_bot(message):
    token = message.text.strip()
    if ":" in token:
        Thread(target=start_sub_bot, args=(token,), daemon=True).start()
        bot.send_message(message.chat.id, "✅ Botingiz muvaffaqiyatli yoqildi!")
    else:
        bot.send_message(message.chat.id, "❌ Xato token.")

# -------------------- 7. ADMIN VA PROFIL --------------------
@bot.message_handler(func=lambda m: m.text.startswith("/give_") and m.from_user.id == ADMIN_ID)
def admin_give(message):
    try:
        tid = int(message.text.split("_")[1])
        user_data[tid]['is_premium'] = True
        bot.send_message(tid, "💎 To'lov tasdiqlandi! Endi /bot_yaratish mumkin.")
        bot.send_message(ADMIN_ID, "Tayyor.")
    except: pass

@bot.message_handler(func=lambda m: m.text == "👤 Profilim")
def my_profile(message):
    u = user_data[message.chat.id]
    status = "💎 Premium" if u['is_premium'] else "📝 Oddiy"
    bot.send_message(message.chat.id, f"ID: {message.chat.id}\nStatus: {status}\nTakliflar: {len(u['referrals'])}/1")

@bot.message_handler(func=lambda m: m.text == "❌ To'xtatish")
def stop_chat(message):
    uid = message.chat.id
    if uid in active_chats:
        p_id = active_chats.pop(uid); active_chats.pop(p_id)
        bot.send_message(uid, "Suhbat yakunlandi."); bot.send_message(p_id, "Sherik chiqib ketdi.")
    elif uid in waiting_users:
        waiting_users.remove(uid); bot.send_message(uid, "Qidiruv to'xtatildi.")

@bot.message_handler(func=lambda m: True)
def chat_relay(m):
    if m.chat.id in active_chats:
        try: bot.send_message(active_chats[m.chat.id], m.text)
        except: pass

# -------------------- RUN --------------------
if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    bot.infinity_polling()
