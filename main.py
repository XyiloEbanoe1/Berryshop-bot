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
PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://0.0.0.0:{PORT}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --------------------------------
# Пути и база данных
# --------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
IMAGES_DIR = os.path.join(WEB_DIR, "images")
DB_FILE = os.path.join(BASE_DIR, "shop.db")
DATA_JSON = os.path.join(WEB_DIR, "data.json")
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
    rows = get_all_products()
    if not rows:
        kb.button(text="➕ Добавить первый товар", callback_data="admin_add")
    else:
        for r in rows:
            kb.button(text=f"{r[0]} — {r[1]}", callback_data=f"admin_prod_{r[0]}")
        kb.button(text="➕ Добавить товар", callback_data="admin_add")
    kb.adjust(2)
    return kb.as_markup()

def build_actions_kb(pid):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ название", callback_data=f"edit_name_{pid}")
    kb.button(text="📂 категория", callback_data=f"edit_cat_{pid}")
    kb.button(text="💰 цена", callback_data=f"edit_price_{pid}")
    kb.button(text="📝 описание", callback_data=f"edit_desc_{pid}")
    kb.button(text="📷 фото", callback_data=f"edit_photo_{pid}")
    kb.button(text="🗑 удалить", callback_data=f"del_{pid}")
    kb.button(text="↩ назад", callback_data="admin_back")
    kb.adjust(2)
    return kb.as_markup()

# --------------------------------
# Команды
# --------------------------------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🛍 Открыть магазин", web_app=types.WebAppInfo(url=f"{RENDER_EXTERNAL_URL}/web"))]],
        resize_keyboard=True
    )
    await msg.answer("Добро пожаловать! 🌿 У нас шишки можно не только курить, но и кушать 😋", reply_markup=kb)

@dp.message(Command("admin"))
async def cmd_admin(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("⛔ Доступ запрещён")
        return
    await msg.answer("📦 Админ панель — список товаров:", reply_markup=build_admin_list_kb())

# --------------------------------
# Callback для добавления товара
# --------------------------------
@dp.callback_query(F.data == "admin_add")
async def add_new(call: types.CallbackQuery):
    await call.answer()
    set_admin_state(call.from_user.id, "mode", "new_name")
    await call.message.answer("📝 Введите название нового товара:")

@dp.callback_query(F.data == "admin_back")
async def back_to_list(call: types.CallbackQuery):
    await call.answer()
    clear_admin(call.from_user.id)
    await call.message.edit_text("📦 Админ панель — список товаров:", reply_markup=build_admin_list_kb())

# Просмотр товара
@dp.callback_query(F.data.startswith("admin_prod_"))
async def view_product(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    prod = get_product(pid)
    if not prod:
        await call.message.answer("❌ Товар не найден")
        return
    
    pid, name, cat, price, desc, img = prod
    text = f"🏷 <b>{name}</b>\n📂 Категория: {cat}\n💰 Цена: {price} ₽\n📝 {desc}"
    
    if img:
        photo_path = os.path.join(IMAGES_DIR, img)
        if os.path.exists(photo_path):
            await call.message.answer_photo(
                photo=types.FSInputFile(photo_path),
                caption=text,
                reply_markup=build_actions_kb(pid)
            )
        else:
            await call.message.answer(text, reply_markup=build_actions_kb(pid))
    else:
        await call.message.answer(text, reply_markup=build_actions_kb(pid))

# Удаление товара
@dp.callback_query(F.data.startswith("del_"))
async def delete_prod(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[1])
    delete_product(pid)
    refresh_web_data()
    await call.message.answer("🗑 Товар удалён!")
    await call.message.answer("📦 Админ панель:", reply_markup=build_admin_list_kb())

# Редактирование полей
@dp.callback_query(F.data.startswith("edit_name_"))
async def edit_name(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_name")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer("✏️ Введите новое название:")

@dp.callback_query(F.data.startswith("edit_cat_"))
async def edit_cat(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_cat")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer("📂 Введите категорию (Варенье, Мёд, Чай):")

@dp.callback_query(F.data.startswith("edit_price_"))
async def edit_price(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_price")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer("💰 Введите новую цену:")

@dp.callback_query(F.data.startswith("edit_desc_"))
async def edit_desc(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_desc")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer("📝 Введите новое описание:")

@dp.callback_query(F.data.startswith("edit_photo_"))
async def edit_photo(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_photo")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer("📷 Отправьте новое фото:")

# --------------------------------
# Обработка текстовых сообщений
# --------------------------------
@dp.message(F.text)
async def handle_text(msg: types.Message):
    st = get_admin(msg.from_user.id)
    if not st:
        return

    mode = st.get("mode")
    
    # Добавление нового товара
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
        set_admin_state(msg.from_user.id, "mode", "new_cat")
        await msg.answer("📂 Введите категорию (Варенье, Мёд, Чай):")
        
    elif mode == "new_cat":
        cat = msg.text.strip()
        pid = st["pid"]
        update_product_field(pid, "category", cat)
        set_admin_state(msg.from_user.id, "mode", "new_price")
        await msg.answer("💰 Введите цену (в рублях):")
        
    elif mode == "new_price":
        try:
            price = int(msg.text.strip())
        except:
            await msg.answer("❌ Введите число.")
            return
        pid = st["pid"]
        update_product_field(pid, "price", price)
        set_admin_state(msg.from_user.id, "mode", "new_desc")
        await msg.answer("📝 Введите описание:")
        
    elif mode == "new_desc":
        desc = msg.text.strip()
        pid = st["pid"]
        update_product_field(pid, "description", desc)
        set_admin_state(msg.from_user.id, "mode", "new_photo")
        await msg.answer("📷 Теперь отправьте фото товара (или напишите 'пропустить'):")
    
    # Редактирование существующего товара
    elif mode == "edit_name":
        pid = st["pid"]
        update_product_field(pid, "name", msg.text.strip())
        refresh_web_data()
        clear_admin(msg.from_user.id)
        await msg.answer("✅ Название обновлено!")
        
    elif mode == "edit_cat":
        pid = st["pid"]
        update_product_field(pid, "category", msg.text.strip())
        refresh_web_data()
        clear_admin(msg.from_user.id)
        await msg.answer("✅ Категория обновлена!")
        
    elif mode == "edit_price":
        try:
            price = int(msg.text.strip())
        except:
            await msg.answer("❌ Введите число.")
            return
        pid = st["pid"]
        update_product_field(pid, "price", price)
        refresh_web_data()
        clear_admin(msg.from_user.id)
        await msg.answer("✅ Цена обновлена!")
        
    elif mode == "edit_desc":
        pid = st["pid"]
        update_product_field(pid, "description", msg.text.strip())
        refresh_web_data()
        clear_admin(msg.from_user.id)
        await msg.answer("✅ Описание обновлено!")

# --------------------------------
# Обработка фото
# --------------------------------
@dp.message(F.photo)
async def save_photo(msg: types.Message):
    st = get_admin(msg.from_user.id)
    if not st or st.get("mode") not in ["new_photo", "edit_photo"]:
        return
    
    pid = st.get("pid")
    if not pid:
        return

    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    path = os.path.join(IMAGES_DIR, f"{pid}.jpg")
    with open(path, "wb") as f:
        f.write(file_bytes.read())
    
    update_product_field(pid, "image", f"{pid}.jpg")
    refresh_web_data()
    clear_admin(msg.from_user.id)
    await msg.answer("✅ Фото сохранено!")

# --------------------------------
# AIOHTTP web
# --------------------------------
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

# ❗ КРИТИЧЕСКИ ВАЖНО: Обработчик webhook
async def webhook_handler(request):
    try:
        update_dict = await request.json()
        update = types.Update(**update_dict)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
        return web.Response(status=500)

app = web.Application()
app.router.add_post(f"/webhook/{BOT_TOKEN}", webhook_handler)  # ❗ ДОБАВЛЕНО
app.router.add_get("/", index)
app.router.add_get("/web", index)
app.router.add_get("/web/{path:.+}", static_handler)
app.router.add_get("/api/products", api_products)

# --------------------------------
# Запуск с webhook
# --------------------------------
async def main():
    refresh_web_data()

    # Очистка старого webhook
    await bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{BOT_TOKEN}"
    
    # Установка webhook
    webhook_info = await bot.set_webhook(webhook_url)
    print(f"🤖 Webhook установлен: {webhook_url}")

    # AIOHTTP сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🌐 WebApp: {RENDER_EXTERNAL_URL}/web")
    print(f"📡 API: {RENDER_EXTERNAL_URL}/api/products")
    print("🍓 Бот запущен успешно!")

    # Бесконечное ожидание
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
