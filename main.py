import os
import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import yt_dlp

# --- SOZLAMALAR ---
TOKEN = "BOT_TOKENINGIZ" # @BotFather dan olingan token
# Siz bergan ID raqami asosiy admin sifatida
SUPER_ADMIN = 8329231121 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (id TEXT PRIMARY KEY, name TEXT, url TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

# Adminni bazaga yozish
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_id', ?)", (str(SUPER_ADMIN),))
db.commit()

# --- YORDAMCHI FUNKSIYALAR ---
def get_current_admin():
    cursor.execute("SELECT value FROM settings WHERE key='admin_id'")
    res = cursor.fetchone()
    return int(res[0]) if res else SUPER_ADMIN

def get_channels():
    cursor.execute("SELECT id, name, url FROM channels")
    return cursor.fetchall()

def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- ADMIN PANEL KLAVIATURASI ---
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="❌ Kanalni o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton(text="👤 Adminni o'zgartirish", callback_data="transfer_admin")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="✉️ Reklama yuborish", callback_data="broadcast")]
    ])

# --- ADMIN TEKSHIRUVI ---
def is_admin(user_id):
    return user_id == SUPER_ADMIN or user_id == get_current_admin()

# --- ADMIN KOMANDALARI ---
@dp.message(Command("admin"))
async def open_admin(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("🛠 **Boshqaruv paneli**\nSiz tizimda to'liq huquqqa egasiz.", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "stats")
async def show_stats(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await call.message.edit_text(f"📊 **Statistika**\n\nJami foydalanuvchilar: {count} ta", reply_markup=admin_keyboard())

# Kanal qo'shish jarayoni
@dp.callback_query(F.data == "add_channel")
async def add_ch_prompt(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        await call.message.answer("Kanalni quyidagi formatda yuboring:\n`ID | Nomi | Link` \n\nMisol:\n`-10021345678 | Primetime | https://t.me/p_time` ")

@dp.message(lambda msg: "|" in msg.text)
async def process_add_channel(message: types.Message):
    if is_admin(message.from_user.id):
        try:
            parts = message.text.split("|")
            ch_id, name, url = parts[0].strip(), parts[1].strip(), parts[2].strip()
            cursor.execute("INSERT INTO channels VALUES (?, ?, ?)", (ch_id, name, url))
            db.commit()
            await message.answer("✅ Yangi kanal majburiy obunaga qo'shildi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {e}")

# Adminni o'zgartirish
@dp.callback_query(F.data == "transfer_admin")
async def transfer_prompt(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        await call.message.answer("Yangi adminning **ID raqamini** yuboring:")

@dp.message(lambda msg: msg.text.isdigit())
async def process_transfer(message: types.Message):
    if is_admin(message.from_user.id):
        new_admin = message.text
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'admin_id'", (new_admin,))
        db.commit()
        await message.answer(f"✅ Qo'shimcha admin tayinlandi: {new_admin}")

# --- ASOSIY ISHCHI QISM ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    db.commit()
    await message.answer("👋 Salom! Men orqali ijtimoiy tarmoqlardan video yuklashingiz mumkin.\n\nLink yuboring:")

@dp.message(F.text.contains("http"))
async def handle_dl(message: types.Message):
    user_id = message.from_user.id
    channels = get_channels()
    
    # Majburiy obunani tekshirish
    not_sub = []
    for ch_id, ch_name, ch_url in channels:
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_sub.append([InlineKeyboardButton(text=ch_name, url=ch_url)])
        except:
            continue # Bot kanalda admin bo'lmasa yoki xato bo'lsa o'tkazib yuboradi
    
    if not_sub:
        kb = InlineKeyboardMarkup(inline_keyboard=not_sub)
        await message.answer("❌ Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz shart:", reply_markup=kb)
        return

    wait = await message.answer("Xabaringiz qayta ishlanmoqda... 📥")
    try:
        # Videoni yuklab olish
        file_path = await asyncio.to_thread(download_video, message.text)
        await message.answer_video(video=FSInputFile(file_path), caption="✅ Yuklab berildi!")
        os.remove(file_path)
        await wait.delete()
    except:
        await wait.edit_text("❌ Xatolik! Video topilmadi yoki bu sayt qo'llab-quvvatlanmaydi.")

async def main():
    if not os.path.exists('downloads'): os.makedirs('downloads')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
