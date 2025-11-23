// Показываем большое сообщение о статусе
function showBigMessage(text, color = '#4CAF50') {
  const msg = document.createElement('div');
  msg.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0,0,0,0.95);
    color: ${color};
    padding: 30px;
    border-radius: 15px;
    font-size: 18px;
    text-align: center;
    z-index: 10000;
    max-width: 80%;
    font-weight: bold;
    line-height: 1.5;
  `;
  msg.innerHTML = text;
  document.body.appendChild(msg);
  
  setTimeout(() => msg.remove(), 5000);
}

let products = [];
let cart = {};

// Загрузка товаров
async function loadProducts() {
  const productList = document.getElementById("product-list");
  
  try {
    showBigMessage('🔄 Загружаю товары...');
    
    const response = await fetch('/api/products');
    
    showBigMessage(`📡 Ответ сервера:<br>Статус ${response.status}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    products = await response.json();
    
    showBigMessage(`✅ Загружено<br>${products.length} товаров`, '#4CAF50');
    
    if (products.length === 0) {
      productList.innerHTML = '<p style="color: red; text-align: center; padding: 20px; grid-column: 1/-1;">⚠️ Товары не найдены!</p>';
      return;
    }
    
    showAll();
    
  } catch (error) {
    showBigMessage(`❌ ОШИБКА<br>${error.message}`, '#ff5555');
    productList.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: red; padding: 20px;">
        <h3>❌ Ошибка загрузки</h3>
        <p>${error.message}</p>
      </div>
    `;
  }
}

const productList = document.getElementById("product-list");
const modal = document.getElementById("product-modal");
const categoryTitle = document.getElementById("category-title");
const weightInput = document.getElementById("weight-input");
const totalPrice = document.getElementById("total-price");
const buyBtn = document.getElementById("buy-btn");
const cartBadge = document.getElementById("cart-badge");

let currentProduct = null;

function displayProducts(items) {
  productList.innerHTML = "";
  
  if (items.length === 0) {
    productList.innerHTML = '<p style="color: #666; text-align: center; padding: 20px; grid-column: 1/-1;">Товары не найдены</p>';
    return;
  }
  
  items.forEach(p => {
    const card = document.createElement("div");
    card.className = "product";
    
    let imgSrc = p.image || getDefaultImage(p.category);
    
    card.innerHTML = `
      <img src="${imgSrc}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/300x160/2d2d2d/666?text=Фото'">
      <div class="product-info">
        <div class="product-rating">⭐ (0)</div>
        <h3>${p.name}</h3>
        <div class="product-price">${p.price} ₽/кг</div>
        <div class="product-location">${p.category}</div>
      </div>
    `;
    card.onclick = () => openProduct(p);
    productList.appendChild(card);
  });
}

function getDefaultImage(category) {
  const defaults = {
    'Варенье': 'https://cdn-icons-png.flaticon.com/512/415/415733.png',
    'Мёд': 'https://cdn-icons-png.flaticon.com/512/2909/2909762.png',
    'Чай': 'https://cdn-icons-png.flaticon.com/512/590/590836.png'
  };
  return defaults[category] || 'https://cdn-icons-png.flaticon.com/512/3050/3050156.png';
}

function showAll() {
  categoryTitle.textContent = 'Все товары';
  displayProducts(products);
  setActiveButton('all');
  setActiveFooterButton(0);
}

function filterCategory(cat) {
  categoryTitle.textContent = cat;
  displayProducts(products.filter(p => p.category === cat));
  setActiveButton(cat);
}

function setActiveButton(category) {
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
  
  if (category === 'all') {
    document.querySelector('.nav-btn[onclick="showAll()"]').classList.add('active');
  } else {
    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.textContent.includes(category));
    if (btn) btn.classList.add('active');
  }
}

function setActiveFooterButton(index) {
  document.querySelectorAll('.footer-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === index);
  });
}

function openProduct(p) {
  currentProduct = p;
  modal.style.display = "block";
  document.body.style.overflow = "hidden";
  
  document.getElementById("modal-title").textContent = p.name;
  document.getElementById("modal-image").src = p.image || getDefaultImage(p.category);
  document.getElementById("modal-price").textContent = `${p.price} ₽/кг`;
  document.getElementById("modal-description").textContent = p.description || 'Описание отсутствует';
  
  weightInput.value = '1.0';
  updateTotalPrice();
}

function updateTotalPrice() {
  if (!currentProduct) return;
  
  let weight = parseFloat(weightInput.value);
  
  if (isNaN(weight) || weight <= 0) {
    totalPrice.textContent = '0 ₽';
    buyBtn.disabled = true;
    return;
  }
  
  if (weight > 100) {
    weight = 100;
    weightInput.value = '100';
  }
  
  const total = Math.round(currentProduct.price * weight);
  totalPrice.textContent = `${total} ₽`;
  buyBtn.disabled = false;
}

function addToCart() {
  if (!currentProduct) return;
  
  const weight = parseFloat(weightInput.value);
  
  if (isNaN(weight) || weight <= 0) {
    showTelegramAlert("❌ Укажите корректный вес!");
    return;
  }
  
  const total = Math.round(currentProduct.price * weight);
  
  if (cart[currentProduct.id]) {
    cart[currentProduct.id].weight += weight;
  } else {
    cart[currentProduct.id] = { product: currentProduct, weight: weight };
  }
  
  showTelegramAlert(`✅ Добавлено:\n\n${currentProduct.name}\n${weight} кг × ${currentProduct.price} ₽ = ${total} ₽`);
  
  closeModal();
  updateCartBadge();
}

function updateCartBadge() {
  const count = Object.keys(cart).length;
  cartBadge.style.display = count > 0 ? 'block' : 'none';
  cartBadge.textContent = count;
}

function closeModal() {
  modal.style.display = "none";
  document.body.style.overflow = "auto";
  currentProduct = null;
}

function openSupport() {
  showTelegramAlert("💬 Поддержка\n\nСвяжитесь: @your_support");
}

function openCart() {
  setActiveFooterButton(1);
  const items = Object.values(cart);
  
  if (items.length === 0) {
    showTelegramAlert("Корзина пуста 🧺");
    return;
  }
  
  let message = "🧺 Ваша корзина:\n\n";
  let totalSum = 0;
  
  items.forEach(item => {
    const p = item.product;
    const w = item.weight;
    const sum = Math.round(p.price * w);
    totalSum += sum;
    message += `${p.name}\n${w} кг × ${p.price} ₽ = ${sum} ₽\n\n`;
  });
  
  message += `💰 Итого: ${totalSum} ₽`;
  showTelegramAlert(message);
}

function openOrders() {
  setActiveFooterButton(2);
  showTelegramAlert("У вас нет заказов 📦");
}

function showTelegramAlert(text) {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.showAlert(text);
  } else {
    alert(text);
  }
}

window.onclick = (e) => {
  if (e.target == modal) closeModal();
}

// Инициализация Telegram WebApp
if (window.Telegram?.WebApp) {
  const tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
  showBigMessage('✅ Telegram WebApp<br>готов', '#4CAF50');
} else {
  showBigMessage('⚠️ Telegram WebApp<br>недоступен', '#ff9800');
}

// Запуск
console.log('🚀 Запуск приложения');
showBigMessage('🚀 Запуск приложения');
loadProducts();
