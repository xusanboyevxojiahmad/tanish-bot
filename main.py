import os
import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import yt_dlp
from aiohttp import web

# --- SOZLAMALAR ---
# Railway Variables bo'limiga TOKEN deb yozgan bo'lsangiz, shu kod uni o'qiydi
TOKEN = os.getenv("TOKEN") 
SUPER_ADMIN = 8329231121 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER (Railway 24/7 o'chib qolmasligi uchun) ---
async def handle(request):
    return web.Response(text="Bot is running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Railway PORTni o'zi beradi, shuni olish shart
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- MA'LUMOTLAR BAZASI ---
db = sqlite3.connect("bot_data.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (id TEXT PRIMARY KEY, name TEXT, url TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_id', ?)", (str(SUPER_ADMIN),))
db.commit()

# --- FUNKSIYALAR ---
def get_current_admin():
    cursor.execute("SELECT value FROM settings WHERE key='admin_id'")
    res = cursor.fetchone()
    return int(res[0]) if res else SUPER_ADMIN

def get_channels():
    cursor.execute("SELECT id, name, url FROM channels")
    return cursor.fetchall()

def download_video(url):
    if not os.path.exists('downloads'): 
        os.makedirs('downloads')
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def is_admin(user_id):
    return user_id == SUPER_ADMIN or user_id == get_current_admin()

# --- ADMIN PANEL ---
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="👤 Adminni o'zgartirish", callback_data="transfer_admin")]
    ])

@dp.message(Command("admin"))
async def open_admin(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("🛠 Boshqaruv paneli:", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "stats")
async def show_stats(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await call.message.answer(f"📊 Jami foydalanuvchilar: {count} ta")
        await call.answer() # Soat belgisi aylanib qolmasligi uchun

@dp.callback_query(F.data == "add_channel")
async def add_ch_prompt(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        await call.message.answer("Format: `ID | Nomi | Link` yuboring.\nMasalan: `-1001234567 | Kanalim | https://t.me/kanal` ")
        await call.answer()

@dp.message(lambda msg: "|" in msg.text)
async def process_add_channel(message: types.Message):
    if is_admin(message.from_user.id):
        try:
            p = message.text.split("|")
            cursor.execute("INSERT INTO channels VALUES (?, ?, ?)", (p[0].strip(), p[1].strip(), p[2].strip()))
            db.commit()
            await message.answer("✅ Kanal qo'shildi!")
        except: 
            await message.answer("❌ Xatolik! ID yoki formatni tekshiring.")

# --- ASOSIY ISHCHI QISM ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    db.commit()
    await message.answer("👋 Salom! Men orqali videolarni yuklab olishingiz mumkin. Link yuboring.")

@dp.message(F.text.contains("http"))
async def handle_dl(message: types.Message):
    user_id = message.from_user.id
    not_sub = []
    
    # Majburiy obunani tekshirish
    channels = get_channels()
    for ch_id, ch_name, ch_url in channels:
        try:
            m = await bot.get_chat_member(ch_id, user_id)
            if m.status not in ["member", "administrator", "creator"]:
                not_sub.append([InlineKeyboardButton(text=ch_name, url=ch_url)])
        except: 
            continue
    
    if not_sub:
        await message.answer("❌ Botdan foydalanish uchun kanallarga a'zo bo'ling:", 
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=not_sub))
        return

    wait = await message.answer("Yuklanmoqda... 📥")
    try:
        # Yuklab olishni alohida taskda bajarish
        file_path = await asyncio.to_thread(download_video, message.text)
        await message.answer_video(video=FSInputFile(file_path), caption="✅ @Andijonliklar_bot orqali yuklab olindi!")
        
        # Faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)
        await wait.delete()
    except Exception as e:
        logging.error(f"Download Error: {e}")
        await wait.edit_text("❌ Xatolik! Link noto'g'ri yoki video juda katta.")

async def main():
    if not os.path.exists('downloads'): 
        os.makedirs('downloads')
    # Web server va Botni birga ishga tushirish
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    
