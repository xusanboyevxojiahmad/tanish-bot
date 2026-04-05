import telebot
import os
from telebot import types, apihelper

# --- SOZLAMALAR ---
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 8770983969  # Sizning ID raqamingiz

if not API_TOKEN:
    print("XATO: BOT_TOKEN topilmadi!")
    exit()

bot = telebot.TeleBot(API_TOKEN)

# Ma'lumotlar
user_data = {} 
waiting_users = []
active_chats = {}
settings = {'check_sub': True, 'channel_username': '@kanal_username'}

def get_main_menu():
    """Asosiy menyu klaviaturasini yaratish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Suhbatdosh topish", "❌ Suhbatni to'xtatish")
    markup.add("👥 Do'stlarim", "🎁 Premium & Takliflar")
    return markup

def check_sub(user_id):
    if not settings['check_sub']: return True
    try:
        status = bot.get_chat_member(chat_id=settings['channel_username'], user_id=user_id).status
        return status != 'left'
    except: return True

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {'referrals': [], 'is_premium': False}
        if len(message.text.split()) > 1:
            inviter_id = int(message.text.split()[1])
            if inviter_id in user_data and inviter_id != user_id:
                if user_id not in user_data[inviter_id]['referrals']:
                    user_data[inviter_id]['referrals'].append(user_id)

    if settings['check_sub'] and not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kanalga a'zo bo'lish", url=f"https://t.me/{settings['channel_username'].replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data="check_sub_now"))
        bot.send_message(user_id, "Botdan foydalanish uchun kanalga a'zo bo'ling:", reply_markup=markup)
        return

    bot.send_message(user_id, "Asosiy menyu ochildi:", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "🔍 Suhbatdosh topish")
def search_handler(message):
    user_id = message.chat.id
    if user_id in active_chats:
        bot.send_message(user_id, "Siz allaqachon suhbatdasiz!")
        return
    
    if user_id in waiting_users:
        bot.send_message(user_id, "Suhbatdosh qidirilmoqda... kuting.")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        bot.send_message(user_id, "🔍 Suhbatdosh topildi!", reply_markup=get_main_menu())
        bot.send_message(partner_id, "🔍 Suhbatdosh topildi!", reply_markup=get_main_menu())
    else:
        waiting_users.append(user_id)
        bot.send_message(user_id, "🔍 Suhbatdosh qidirilmoqda... (tez orada suxbatdosh topiladi...)", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "❌ Suhbatni to'xtatish")
def stop_handler(message):
    user_id = message.chat.id
    if user_id in active_chats:
        p_id = active_chats.pop(user_id)
        active_chats.pop(p_id)
        bot.send_message(user_id, "Suhbat to'xtatildi.", reply_markup=get_main_menu())
        bot.send_message(p_id, "Suhbatdosh suhbatni to'xtatdi.", reply_markup=get_main_menu())
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        bot.send_message(user_id, "Qidiruv bekor qilindi.", reply_markup=get_main_menu())
    else:
        bot.send_message(user_id, "Siz hozir suhbatda emassiz.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    user_id = message.chat.id
    # Agar suhbatda bo'lsa - xabarni yuborish
    if user_id in active_chats:
        try:
            bot.send_message(active_chats[user_id], message.text)
        except:
            bot.send_message(user_id, "Xabar yuborilmadi (sherigingiz botni bloklagan bo'lishi mumkin).")
    else:
        # Agar suhbatda bo'lmasa va menyu tugmasidan boshqa narsa yozsa
        bot.send_message(user_id, "Suhbat boshlash uchun tugmalardan foydalaning 👇", reply_markup=get_main_menu())

# Qolgan funksiyalar (admin, premium, friends...) yuqoridagi kod bilan bir xil davom etadi

bot.polling(none_stop=True)
