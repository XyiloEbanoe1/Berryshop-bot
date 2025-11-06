import os
import asyncio
import json
import sqlite3
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --------------------------------
# Настройки и окружение
# --------------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
PORT = int(os.getenv("PORT", 8081))
REPLIT_URL = os.getenv("REPLIT_URL", f"http://0.0.0.0:{PORT}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --------------------------------
# Пути и база данных
# --------------------------------
# Корневой каталог относительно этого файла — чтобы приложение видел файлы
# независимо от текущей рабочей директории (CWD)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
IMAGES_DIR = os.path.join(WEB_DIR, "images")
DB_FILE = os.path.join(BASE_DIR, "shop.db")
DATA_JSON = os.path.join(WEB_DIR, "data.json")
# Создаём директорию для изображений, если её ещё нет
os.makedirs(IMAGES_DIR, exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price INTEGER,
        description TEXT,
        image TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --------------------------------
# Вспомогательные функции
# --------------------------------
def get_all_products():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, category, price, description, image FROM products ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_product(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, category, price, description, image FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()
    return row

def update_product_field(pid, field, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE products SET {field}=? WHERE id=?", (value, pid))
    conn.commit()
    conn.close()

def delete_product(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()

def refresh_web_data():
    """Обновляем JSON-файл для сайта"""
    rows = get_all_products()
    out = []
    for r in rows:
        pid, name, cat, price, desc, img = r
        out.append({
            "id": pid,
            "name": name or "",
            "category": cat or "",
            "price": price or 0,
            "description": desc or "",
            "image": f"images/{img}" if img else ""
        })
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

# --------------------------------
# Состояние админки
# --------------------------------
admin_state = {}

def set_admin_state(uid, key, val):
    if uid not in admin_state:
        admin_state[uid] = {}
    admin_state[uid][key] = val

def get_admin(uid):
    return admin_state.get(uid, {})

def clear_admin(uid):
    admin_state.pop(uid, None)

# --------------------------------
# Клавиатуры
# --------------------------------
def build_admin_list_kb():
    kb = InlineKeyboardBuilder()
    for r in get_all_products():
        kb.button(text=f"{r[0]} — {r[1]}", callback_data=f"admin_prod_{r[0]}")
    kb.button(text="➕ Добавить товар", callback_data="admin_add")
    kb.adjust(2)
    return kb.as_markup()

def build_actions_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ название", callback_data="act_name")
    kb.button(text="💰 цена", callback_data="act_price")
    kb.button(text="📝 описание", callback_data="act_desc")
    kb.button(text="📷 фото", callback_data="act_photo")
    kb.button(text="🗑 удалить", callback_data="act_del")
    kb.button(text="↩ назад", callback_data="act_back")
    kb.adjust(2)
    return kb.as_markup()

# --------------------------------
# Команды
# --------------------------------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🛍 Открыть магазин", web_app=types.WebAppInfo(url=f"{REPLIT_URL}/web"))]],
        resize_keyboard=True
    )
    await msg.answer("Добро пожаловать, тебе повезло, с чем же? У нас шишки можно не только курить но и кушать 🌿", reply_markup=kb)

@dp.message(Command("admin"))
async def cmd_admin(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("⛔ Доступ запрещён.")
        return
    await msg.answer("Панель администратора:", reply_markup=build_admin_list_kb())

# --------------------------------
# Callback-и
# --------------------------------
@dp.callback_query(F.data == "admin_add")
async def add_new(call: types.CallbackQuery):
    await call.answer()
    set_admin_state(call.from_user.id, "mode", "new_name")
    await call.message.answer("Введите название нового товара:")

@dp.message()
async def handle_text(msg: types.Message):
    st = get_admin(msg.from_user.id)
    if not st:
        return

    mode = st.get("mode")
    if mode == "new_name":
        name = msg.text.strip()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, category, price, description, image) VALUES (?,?,?,?,?)",
                    (name, "Без категории", 0, "", ""))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        set_admin_state(msg.from_user.id, "pid", pid)
        set_admin_state(msg.from_user.id, "mode", "new_price")
        await msg.answer("Введите цену (руб):")
    elif mode == "new_price":
        try:
            price = int(msg.text.strip())
        except:
            await msg.answer("Введите число.")
            return
        pid = st["pid"]
        update_product_field(pid, "price", price)
        set_admin_state(msg.from_user.id, "mode", "new_desc")
        await msg.answer("описание:")
    elif mode == "new_desc":
        desc = msg.text.strip()
        pid = st["pid"]
        update_product_field(pid, "description", desc)
        set_admin_state(msg.from_user.id, "mode", "new_photo")
        await msg.answer("отправь фото")
    else:
        return

@dp.message(F.photo)
async def save_photo(msg: types.Message):
    st = get_admin(msg.from_user.id)
    if not st:
        return
    pid = st.get("pid")
    if not pid:
        return

    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    path = os.path.join(IMAGES_DIR, f"{pid}.jpg")
    with open(path, "wb") as f:
        f.write(file_bytes.getbuffer())
    update_product_field(pid, "image", f"{pid}.jpg")
    refresh_web_data()
    clear_admin(msg.from_user.id)
    await msg.answer("✅ Добавлено и сохранёно!")

# --------------------------------
# AIOHTTP web
# --------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, 'web')

async def index(request):
    return web.FileResponse(os.path.join(WEB_DIR, 'index.html'))


async def static_handler(request):
    path = request.match_info.get("path")
    full = os.path.join(WEB_DIR, path)
    if os.path.isfile(full):
        return web.FileResponse(full)
    return web.Response(status=404, text="Not found")

async def api_products(request):
    refresh_web_data()
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return web.json_response(data)

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/web", index)
app.router.add_get("/web/{path:.+}", static_handler)
app.router.add_get("/api/products", api_products)

# --------------------------------
# Запуск
# --------------------------------
async def main():
    refresh_web_data()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌍 WebApp: {REPLIT_URL}/web")
    print("🤖 берри ботик запушен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
