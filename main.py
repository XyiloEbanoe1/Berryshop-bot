import os
import sys
import asyncio
import json
import sqlite3
from datetime import datetime
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

print("=" * 60)
print("🚀 СТАРТ ПРИЛОЖЕНИЯ")
print("=" * 60)

# --------------------------------
# Настройки и окружение
# --------------------------------
print("📋 Загрузка переменных окружения...")
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://0.0.0.0:{PORT}")

print(f"✅ BOT_TOKEN: {'✓ установлен' if BOT_TOKEN else '✗ ОТСУТСТВУЕТ'}")
print(f"✅ ADMIN_IDS: {ADMIN_IDS_STR}")
print(f"✅ PORT: {PORT}")
print(f"✅ RENDER_EXTERNAL_URL: {RENDER_EXTERNAL_URL}")

if not BOT_TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не установлен!")
    sys.exit(1)

ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]
print(f"✅ Админы (ID): {ADMIN_IDS}")

print("\n📦 Инициализация бота...")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
print("✅ Бот инициализирован")

# --------------------------------
# Пути и база данных
# --------------------------------
print("\n📂 Настройка путей...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
IMAGES_DIR = os.path.join(WEB_DIR, "images")
DB_FILE = os.path.join(BASE_DIR, "shop.db")
DATA_JSON = os.path.join(WEB_DIR, "data.json")

print(f"BASE_DIR: {BASE_DIR}")
print(f"WEB_DIR: {WEB_DIR}")
print(f"DB_FILE: {DB_FILE}")
print(f"DATA_JSON: {DATA_JSON}")

os.makedirs(IMAGES_DIR, exist_ok=True)
print("✅ Директории созданы")

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    print("\n🗄️  Инициализация базы данных...")
    conn = get_conn()
    cur = conn.cursor()
    
    # Таблица товаров
    cur.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price INTEGER,
        description TEXT,
        image TEXT
    )""")
    
    # Таблица сообщений поддержки
    cur.execute("""CREATE TABLE IF NOT EXISTS support_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        message TEXT,
        timestamp TEXT,
        is_read INTEGER DEFAULT 0,
        from_admin INTEGER DEFAULT 0
    )""")
    
    # Таблица заказов
    cur.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        products_json TEXT,
        total_price INTEGER,
        timestamp TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    
    # Таблица покупок (история)
    cur.execute("""CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_id INTEGER,
        timestamp TEXT
    )""")
    
    conn.commit()
    conn.close()
    print("✅ Все таблицы созданы/проверены")

def seed_database_from_json():
    """Заполняет БД из data.json если БД пустая"""
    print("\n📦 Проверка наполнения БД...")
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]
    
    print(f"📊 В базе данных товаров: {count}")
    
    if count == 0:
        print("📦 База данных пустая, загружаем товары из data.json...")
        
        if os.path.exists(DATA_JSON):
            print(f"✅ Файл {DATA_JSON} найден")
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                products = json.load(f)
            
            print(f"📄 Найдено товаров в data.json: {len(products)}")
            
            for i, p in enumerate(products):
                cur.execute(
                    "INSERT INTO products (name, category, price, description, image) VALUES (?,?,?,?,?)",
                    (p.get("name", ""), p.get("category", ""), p.get("price", 0), 
                     p.get("description", ""), p.get("image", "").replace("images/", ""))
                )
                if i < 3:
                    print(f"  - {p.get('name')} ({p.get('category')}, {p.get('price')} ₽)")
            
            conn.commit()
            print(f"✅ Загружено {len(products)} товаров в базу данных!")
        else:
            print(f"⚠️ ФАЙЛ НЕ НАЙДЕН: {DATA_JSON}")
    else:
        print(f"✅ В базе уже есть {count} товаров")
    
    conn.close()

print("\n" + "=" * 60)
print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
print("=" * 60)

init_db()
seed_database_from_json()

# --------------------------------
# Вспомогательные функции для товаров
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
# Функции для поддержки
# --------------------------------
def save_support_message(user_id, username, message, from_admin=0):
    conn = get_conn()
    cur = conn.cursor()
    timestamp = datetime.now().strftime("%d.%m.%y %H:%M")
    cur.execute(
        "INSERT INTO support_messages (user_id, username, message, timestamp, from_admin) VALUES (?,?,?,?,?)",
        (user_id, username, message, timestamp, from_admin)
    )
    conn.commit()
    conn.close()

def get_support_users():
    """Получить список пользователей с непрочитанными сообщениями"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT user_id, username, MAX(timestamp) as last_time
        FROM support_messages
        WHERE from_admin = 0
        GROUP BY user_id
        ORDER BY last_time DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_support_messages(user_id):
    """Получить все сообщения пользователя"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT message, timestamp, from_admin FROM support_messages WHERE user_id=? ORDER BY timestamp",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

# --------------------------------
# Функции для заказов
# --------------------------------
def create_order(user_id, username, cart_data, total_price):
    conn = get_conn()
    cur = conn.cursor()
    timestamp = datetime.now().strftime("%d.%m.%y %H:%M")
    products_json = json.dumps(cart_data, ensure_ascii=False)
    
    cur.execute(
        "INSERT INTO orders (user_id, username, products_json, total_price, timestamp, status) VALUES (?,?,?,?,?,?)",
        (user_id, username, products_json, total_price, timestamp, "pending")
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_pending_orders():
    """Получить все заказы со статусом pending или in_progress"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, username, products_json, total_price, timestamp, status FROM orders WHERE status != 'completed' ORDER BY timestamp DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, username, products_json, total_price, timestamp, status FROM orders WHERE id=?",
        (order_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def update_order_status(order_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    
    # Если заказ выполнен - добавляем в историю покупок
    if status == "completed":
        cur.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
        user_id = cur.fetchone()[0]
        timestamp = datetime.now().strftime("%d.%m.%y %H:%M")
        cur.execute("INSERT INTO purchases (user_id, order_id, timestamp) VALUES (?,?,?)",
                   (user_id, order_id, timestamp))
        conn.commit()
    
    conn.close()

def get_user_purchases(user_id):
    """Получить историю покупок пользователя"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.products_json, o.total_price, p.timestamp
        FROM purchases p
        JOIN orders o ON p.order_id = o.id
        WHERE p.user_id = ?
        ORDER BY p.timestamp DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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
def build_main_kb():
    """Главная клавиатура для пользователя"""
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🛍 Открыть магазин", web_app=types.WebAppInfo(url=f"{RENDER_EXTERNAL_URL}/shop"))],
            [types.KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )
    return kb

def build_admin_main_kb():
    """Главная админ-панель с 3 кнопками"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🍓 Ягоды", callback_data="admin_products")
    kb.button(text="💬 Поддержка", callback_data="admin_support")
    kb.button(text="📦 Заказы", callback_data="admin_orders")
    kb.adjust(1)
    return kb.as_markup()

def build_admin_list_kb():
    """Список товаров"""
    kb = InlineKeyboardBuilder()
    rows = get_all_products()
    if not rows:
        kb.button(text="➕ Добавить первый товар", callback_data="admin_add")
    else:
        for r in rows:
            kb.button(text=f"{r[0]} — {r[1]}", callback_data=f"admin_prod_{r[0]}")
        kb.button(text="➕ Добавить товар", callback_data="admin_add")
    kb.button(text="↩ Назад", callback_data="admin_main")
    kb.adjust(2)
    return kb.as_markup()

def build_actions_kb(pid):
    """Действия с товаром"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ название", callback_data=f"edit_name_{pid}")
    kb.button(text="📂 категория", callback_data=f"edit_cat_{pid}")
    kb.button(text="💰 цена", callback_data=f"edit_price_{pid}")
    kb.button(text="📝 описание", callback_data=f"edit_desc_{pid}")
    kb.button(text="📷 фото", callback_data=f"edit_photo_{pid}")
    kb.button(text="🗑 удалить", callback_data=f"del_{pid}")
    kb.button(text="↩ назад", callback_data="admin_products")
    kb.adjust(2)
    return kb.as_markup()

def build_support_list_kb():
    """Список пользователей в поддержке"""
    kb = InlineKeyboardBuilder()
    users = get_support_users()
    
    if not users:
        kb.button(text="Нет сообщений", callback_data="noop")
    else:
        for user_id, username, last_time in users:
            display_name = f"@{username}" if username else f"ID: {user_id}"
            kb.button(text=f"{display_name} ({last_time})", callback_data=f"support_user_{user_id}")
    
    kb.button(text="↩ Назад", callback_data="admin_main")
    kb.adjust(1)
    return kb.as_markup()

def build_orders_list_kb():
    """Список заказов"""
    kb = InlineKeyboardBuilder()
    orders = get_pending_orders()
    
    if not orders:
        kb.button(text="Нет активных заказов", callback_data="noop")
    else:
        for order_id, user_id, username, products_json, total_price, timestamp, status in orders:
            display_name = f"@{username}" if username else f"ID: {user_id}"
            status_emoji = "🆕" if status == "pending" else "⏳"
            kb.button(text=f"{status_emoji} {display_name} — {total_price} ₽", callback_data=f"order_view_{order_id}")
    
    kb.button(text="↩ Назад", callback_data="admin_main")
    kb.adjust(1)
    return kb.as_markup()

# --------------------------------
# Команды
# --------------------------------
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    await msg.answer("Добро пожаловать! 🌿 У нас шишки можно не только курить, но и кушать 😋", reply_markup=build_main_kb())

@dp.message(Command("admin"))
async def cmd_admin(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("⛔ Доступ запрещён")
        return
    await msg.answer("⚙️ Админ-панель:", reply_markup=build_admin_main_kb())

@dp.message(Command("resetdb"))
async def cmd_resetdb(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("⛔ Доступ запрещён")
        return
    
    await msg.answer("🔄 Пересоздаю базу данных...")
    
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        seed_database_from_json()
        refresh_web_data()
        
        count = len(get_all_products())
        await msg.answer(f"✅ База пересоздана!\n📦 Товаров в базе: {count}")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(F.text == "💬 Поддержка")
async def cmd_support(msg: types.Message):
    set_admin_state(msg.from_user.id, "mode", "support_message")
    await msg.answer("💬 Напишите ваше сообщение в поддержку:")

# --------------------------------
# Callback handlers - админ панель
# --------------------------------
@dp.callback_query(F.data == "admin_main")
async def admin_main(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text("⚙️ Админ-панель:", reply_markup=build_admin_main_kb())

@dp.callback_query(F.data == "admin_products")
async def admin_products(call: types.CallbackQuery):
    await call.answer()
    clear_admin(call.from_user.id)
    await call.message.edit_text("📦 Список товаров:", reply_markup=build_admin_list_kb())

@dp.callback_query(F.data == "admin_support")
async def admin_support(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text("💬 Поддержка — список пользователей:", reply_markup=build_support_list_kb())

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 Заказы:", reply_markup=build_orders_list_kb())

# --------------------------------
# Поддержка - просмотр диалога
# --------------------------------
@dp.callback_query(F.data.startswith("support_user_"))
async def view_support_user(call: types.CallbackQuery):
    await call.answer()
    user_id = int(call.data.split("_")[2])
    
    messages = get_user_support_messages(user_id)
    
    if not messages:
        await call.message.answer("Нет сообщений")
        return
    
    # Получаем username
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username FROM support_messages WHERE user_id=? LIMIT 1", (user_id,))
    result = cur.fetchone()
    conn.close()
    username = result[0] if result else "неизвестен"
    
    text = f"💬 Диалог с @{username}\n\n"
    
    for message, timestamp, from_admin in messages:
        if from_admin:
            text += f"👨‍💼 Админ ({timestamp}):\n{message}\n\n"
        else:
            text += f"👤 Пользователь ({timestamp}):\n{message}\n\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Ответить", callback_data=f"support_reply_{user_id}")
    kb.button(text="↩ Назад", callback_data="admin_support")
    kb.adjust(1)
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("support_reply_"))
async def support_reply(call: types.CallbackQuery):
    await call.answer()
    user_id = int(call.data.split("_")[2])
    
    set_admin_state(call.from_user.id, "mode", "support_reply")
    set_admin_state(call.from_user.id, "target_user", user_id)
    
    await call.message.answer("✍️ Введите ответ пользователю:")

# --------------------------------
# Заказы - просмотр
# --------------------------------
@dp.callback_query(F.data.startswith("order_view_"))
async def view_order(call: types.CallbackQuery):
    await call.answer()
    order_id = int(call.data.split("_")[2])
    
    order = get_order(order_id)
    
    if not order:
        await call.message.answer("❌ Заказ не найден")
        return
    
    order_id, user_id, username, products_json, total_price, timestamp, status = order
    
    products = json.loads(products_json)
    
    text = f"📦 Заказ #{order_id}\n\n"
    text += f"👤 От: @{username}\n"
    text += f"🕐 Время: {timestamp}\n"
    text += f"📊 Статус: {status}\n\n"
    text += f"🛒 Состав заказа:\n\n"
    
    for item in products:
        text += f"• {item['name']}\n"
        text += f"  Вес: {item['weight']} кг\n"
        text += f"  Цена: {item['price']} ₽\n\n"
    
    text += f"💰 Итого: {total_price} ₽"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Написать клиенту", callback_data=f"order_msg_{order_id}")
    kb.button(text="✅ Заказ выполнен", callback_data=f"order_complete_{order_id}")
    kb.button(text="↩ Назад", callback_data="admin_orders")
    kb.adjust(1)
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("order_msg_"))
async def order_message(call: types.CallbackQuery):
    await call.answer()
    order_id = int(call.data.split("_")[2])
    
    order = get_order(order_id)
    user_id = order[1]
    
    set_admin_state(call.from_user.id, "mode", "order_message")
    set_admin_state(call.from_user.id, "target_user", user_id)
    set_admin_state(call.from_user.id, "order_id", order_id)
    
    await call.message.answer("✍️ Введите сообщение клиенту (по заказу):")

@dp.callback_query(F.data.startswith("order_complete_"))
async def order_complete(call: types.CallbackQuery):
    await call.answer()
    order_id = int(call.data.split("_")[2])
    
    update_order_status(order_id, "completed")
    
    await call.message.answer("✅ Заказ отмечен как выполненный!")
    await call.message.edit_reply_markup(reply_markup=build_orders_list_kb())

@dp.callback_query(F.data == "noop")
async def noop(call: types.CallbackQuery):
    await call.answer()
# --------------------------------
# Callback handlers - товары
# --------------------------------
@dp.callback_query(F.data.startswith("admin_prod_"))
async def view_product(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    p = get_product(pid)
    if not p:
        await call.message.answer("❌ Товар не найден")
        return
    
    text = (
        f"🔹 ID: {p[0]}\n"
        f"📦 Название: {p[1]}\n"
        f"📂 Категория: {p[2]}\n"
        f"💰 Цена: {p[3]} ₽\n"
        f"📝 Описание: {p[4]}\n"
        f"📷 Фото: {p[5]}\n"
    )
    await call.message.edit_text(text, reply_markup=build_actions_kb(pid))

@dp.callback_query(F.data == "admin_add")
async def admin_add(call: types.CallbackQuery):
    await call.answer()
    set_admin_state(call.from_user.id, "mode", "add_name")
    await call.message.answer("➕ Введите название нового товара:")

@dp.callback_query(F.data.startswith("edit_name_"))
async def edit_name(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_name")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer(f"✏️ Введите новое название для товара #{pid}:")

@dp.callback_query(F.data.startswith("edit_cat_"))
async def edit_cat(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_cat")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer(f"📂 Введите новую категорию для товара #{pid}:")

@dp.callback_query(F.data.startswith("edit_price_"))
async def edit_price(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_price")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer(f"💰 Введите новую цену для товара #{pid}:")

@dp.callback_query(F.data.startswith("edit_desc_"))
async def edit_desc(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_desc")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer(f"📝 Введите новое описание для товара #{pid}:")

@dp.callback_query(F.data.startswith("edit_photo_"))
async def edit_photo(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[2])
    set_admin_state(call.from_user.id, "mode", "edit_photo")
    set_admin_state(call.from_user.id, "pid", pid)
    await call.message.answer(f"📷 Отправьте новое фото для товара #{pid}:")

@dp.callback_query(F.data.startswith("del_"))
async def delete_product_confirm(call: types.CallbackQuery):
    await call.answer()
    pid = int(call.data.split("_")[1])
    delete_product(pid)
    refresh_web_data()
    await call.message.answer(f"✅ Товар #{pid} удалён!")
    await call.message.edit_text("📦 Список товаров:", reply_markup=build_admin_list_kb())

# --------------------------------
# Обработчик текстовых сообщений
# --------------------------------
@dp.message(F.text)
async def handle_text(msg: types.Message):
    uid = msg.from_user.id
    state = get_admin(uid)
    mode = state.get("mode")
    
    # ========== ПОДДЕРЖКА ==========
    if mode == "support_message":
        # Пользователь отправляет сообщение в поддержку
        username = msg.from_user.username or "неизвестен"
        save_support_message(uid, username, msg.text, from_admin=0)
        
        # Уведомляем всех админов
        for admin_id in ADMIN_IDS:
            try:
                kb = InlineKeyboardBuilder()
                kb.button(text="✍️ Ответить", callback_data=f"support_reply_{uid}")
                
                await bot.send_message(
                    admin_id,
                    f"💬 Новое сообщение в поддержку!\n\n"
                    f"От: @{username}\n"
                    f"Сообщение: {msg.text}",
                    reply_markup=kb.as_markup()
                )
            except:
                pass
        
        clear_admin(uid)
        await msg.answer("✅ Ваше сообщение отправлено в поддержку!")
        return
    
    if mode == "support_reply":
        # Админ отвечает пользователю
        target_user = state.get("target_user")
        
        # Сохраняем ответ админа
        admin_username = msg.from_user.username or "admin"
        save_support_message(target_user, admin_username, msg.text, from_admin=1)
        
        # Отправляем пользователю уведомление
        kb = InlineKeyboardBuilder()
        kb.button(text="✍️ Ответить", callback_data="support_from_notification")
        
        try:
            await bot.send_message(
                target_user,
                f"💬 Новое сообщение от поддержки!\n\n{msg.text}",
                reply_markup=kb.as_markup()
            )
        except:
            pass
        
        clear_admin(uid)
        await msg.answer("✅ Ответ отправлен пользователю!")
        return
    
    if mode == "order_message":
        # Админ пишет клиенту по заказу
        target_user = state.get("target_user")
        order_id = state.get("order_id")
        
        # Обновляем статус заказа на in_progress
        update_order_status(order_id, "in_progress")
        
        # Отправляем сообщение клиенту
        try:
            await bot.send_message(
                target_user,
                f"📦 Сообщение по вашему заказу #{order_id}:\n\n{msg.text}"
            )
        except:
            pass
        
        clear_admin(uid)
        await msg.answer("✅ Сообщение отправлено клиенту!")
        return
    
    # ========== ТОВАРЫ ==========
    if mode == "add_name":
        set_admin_state(uid, "new_name", msg.text)
        set_admin_state(uid, "mode", "add_cat")
        await msg.reply("📂 Введите категорию:")
        return
    
    if mode == "add_cat":
        set_admin_state(uid, "new_cat", msg.text)
        set_admin_state(uid, "mode", "add_price")
        await msg.reply("💰 Введите цену:")
        return
    
    if mode == "add_price":
        try:
            price = int(msg.text)
            set_admin_state(uid, "new_price", price)
            set_admin_state(uid, "mode", "add_desc")
            await msg.reply("📝 Введите описание:")
        except ValueError:
            await msg.reply("❌ Цена должна быть числом!")
        return
    
    if mode == "add_desc":
        set_admin_state(uid, "new_desc", msg.text)
        set_admin_state(uid, "mode", "add_photo")
        await msg.reply("📷 Отправьте фото товара:")
        return
    
    if mode == "edit_name":
        pid = state.get("pid")
        update_product_field(pid, "name", msg.text)
        refresh_web_data()
        clear_admin(uid)
        await msg.reply(f"✅ Название товара #{pid} обновлено!")
        return
    
    if mode == "edit_cat":
        pid = state.get("pid")
        update_product_field(pid, "category", msg.text)
        refresh_web_data()
        clear_admin(uid)
        await msg.reply(f"✅ Категория товара #{pid} обновлена!")
        return
    
    if mode == "edit_price":
        pid = state.get("pid")
        try:
            price = int(msg.text)
            update_product_field(pid, "price", price)
            refresh_web_data()
            clear_admin(uid)
            await msg.reply(f"✅ Цена товара #{pid} обновлена!")
        except ValueError:
            await msg.reply("❌ Цена должна быть числом!")
        return
    
    if mode == "edit_desc":
        pid = state.get("pid")
        update_product_field(pid, "description", msg.text)
        refresh_web_data()
        clear_admin(uid)
        await msg.reply(f"✅ Описание товара #{pid} обновлено!")
        return

# --------------------------------
# Обработчик фото
# --------------------------------
@dp.message(F.photo)
async def handle_photo(msg: types.Message):
    uid = msg.from_user.id
    state = get_admin(uid)
    mode = state.get("mode")
    
    if mode == "add_photo":
        photo = msg.photo[-1]
        file = await bot.get_file(photo.file_id)
        filename = f"{photo.file_id}.jpg"
        dest = os.path.join(IMAGES_DIR, filename)
        await bot.download_file(file.file_path, dest)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, category, price, description, image) VALUES (?,?,?,?,?)",
            (state["new_name"], state["new_cat"], state["new_price"], state["new_desc"], filename)
        )
        conn.commit()
        conn.close()
        
        refresh_web_data()
        clear_admin(uid)
        await msg.reply("✅ Товар добавлен!")
        return
    
    if mode == "edit_photo":
        pid = state.get("pid")
        photo = msg.photo[-1]
        file = await bot.get_file(photo.file_id)
        filename = f"{photo.file_id}.jpg"
        dest = os.path.join(IMAGES_DIR, filename)
        await bot.download_file(file.file_path, dest)
        
        update_product_field(pid, "image", filename)
        refresh_web_data()
        clear_admin(uid)
        await msg.reply(f"✅ Фото товара #{pid} обновлено!")
        return

@dp.callback_query(F.data == "support_from_notification")
async def support_from_notification(call: types.CallbackQuery):
    await call.answer()
    set_admin_state(call.from_user.id, "mode", "support_message")
    await call.message.answer("✍️ Напишите ваш ответ:")
# --------------------------------
# AIOHTTP web - API endpoints
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
    print(f"📡 API /api/products вернул {len(data)} товаров")
    return web.json_response(data)

async def api_support_send(request):
    """Отправка сообщения в поддержку из WebApp"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        username = data.get("username", "неизвестен")
        message = data.get("message")
        
        if not user_id or not message:
            return web.json_response({"error": "Missing data"}, status=400)
        
        # Сохраняем в БД
        save_support_message(user_id, username, message, from_admin=0)
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                kb = InlineKeyboardBuilder()
                kb.button(text="✍️ Ответить", callback_data=f"support_reply_{user_id}")
                
                await bot.send_message(
                    admin_id,
                    f"💬 Новое сообщение в поддержку (из WebApp)!\n\n"
                    f"От: @{username}\n"
                    f"Сообщение: {message}",
                    reply_markup=kb.as_markup()
                )
            except:
                pass
        
        return web.json_response({"success": True})
    
    except Exception as e:
        print(f"❌ Ошибка API support/send: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_support_history(request):
    """Получить историю сообщений пользователя"""
    try:
        user_id = int(request.query.get("user_id"))
        messages = get_user_support_messages(user_id)
        
        result = []
        for message, timestamp, from_admin in messages:
            result.append({
                "message": message,
                "timestamp": timestamp,
                "from_admin": bool(from_admin)
            })
        
        return web.json_response({"messages": result})
    
    except Exception as e:
        print(f"❌ Ошибка API support/history: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_order_create(request):
    """Создание заказа из WebApp"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        username = data.get("username", "неизвестен")
        cart = data.get("cart", [])
        total_price = data.get("total_price", 0)
        
        if not user_id or not cart:
            return web.json_response({"error": "Missing data"}, status=400)
        
        # Создаём заказ
        order_id = create_order(user_id, username, cart, total_price)
        
        # Уведомляем админов
        order_text = f"📦 Новый заказ #{order_id}!\n\n"
        order_text += f"От: @{username}\n"
        order_text += f"Товары:\n"
        
        for item in cart:
            order_text += f"• {item['name']} ({item['weight']} кг) — {item['price']} ₽\n"
        
        order_text += f"\n💰 Итого: {total_price} ₽"
        
        for admin_id in ADMIN_IDS:
            try:
                kb = InlineKeyboardBuilder()
                kb.button(text="📋 Посмотреть заказ", callback_data=f"order_view_{order_id}")
                
                await bot.send_message(admin_id, order_text, reply_markup=kb.as_markup())
            except:
                pass
        
        return web.json_response({"success": True, "order_id": order_id})
    
    except Exception as e:
        print(f"❌ Ошибка API order/create: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_profile(request):
    """Получить данные профиля пользователя"""
    try:
        user_id = int(request.query.get("user_id"))
        username = request.query.get("username", "неизвестен")
        
        # Получаем историю покупок
        purchases = get_user_purchases(user_id)
        
        result = {
            "username": username,
            "purchases": []
        }
        
        for products_json, total_price, timestamp in purchases:
            products = json.loads(products_json)
            result["purchases"].append({
                "products": products,
                "total_price": total_price,
                "timestamp": timestamp
            })
        
        return web.json_response(result)
    
    except Exception as e:
        print(f"❌ Ошибка API profile: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def webhook_handler(request):
    try:
        update_dict = await request.json()
        update = types.Update(**update_dict)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
        return web.Response(status=500)

# --------------------------------
# Настройка маршрутов
# --------------------------------
app = web.Application()
app.router.add_post(f"/webhook/{BOT_TOKEN}", webhook_handler)
app.router.add_get("/", index)
app.router.add_get("/web", index)
app.router.add_get("/web/{path:.+}", static_handler)
app.router.add_get("/shop", index)
app.router.add_get("/shop/{path:.+}", static_handler)
app.router.add_get("/api/products", api_products)
app.router.add_post("/api/support/send", api_support_send)
app.router.add_get("/api/support/history", api_support_history)
app.router.add_post("/api/order/create", api_order_create)
app.router.add_get("/api/profile", api_profile)
app.router.add_static("/images/", IMAGES_DIR)
print("✅ Маршруты настроены")

# --------------------------------
# Запуск
# --------------------------------
async def main():
    print("\n" + "=" * 60)
    print("ЗАПУСК СЕРВЕРА")
    print("=" * 60)
    
    print("\n🔄 Обновление data.json...")
    refresh_web_data()
    print("✅ data.json обновлён")

    print("\n🔄 Удаление старого webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Старый webhook удалён")
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{BOT_TOKEN}"
    print(f"\n🔄 Установка нового webhook: {webhook_url}")
    await bot.set_webhook(webhook_url)
    print("✅ Webhook установлен")

    print("\n🔄 Запуск AIOHTTP сервера...")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Сервер запущен на порту {PORT}")

    print("\n" + "=" * 60)
    print("🎉 ВСЁ ГОТОВО!")
    print("=" * 60)
    print(f"🌐 WebApp: {RENDER_EXTERNAL_URL}/web")
    print(f"📡 API: {RENDER_EXTERNAL_URL}/api/products")
    print("🍓 Бот готов к работе!")
    print("=" * 60)

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        print("\n▶️  Запуск asyncio.run(main())...")
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)