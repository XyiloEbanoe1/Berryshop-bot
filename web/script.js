let products = [];
let cart = {};
let currentCategory = 'Все товары';

// Debug элемент
function showDebug(msg, isError = false) {
  const debugDiv = document.getElementById('debug-info') || createDebugDiv();
  const color = isError ? '#ff5555' : '#4CAF50';
  debugDiv.innerHTML += `<div style="color: ${color}; font-size: 12px; margin: 5px 0;">${msg}</div>`;
  console.log(msg);
}

function createDebugDiv() {
  const div = document.createElement('div');
  div.id = 'debug-info';
  div.style.cssText = 'position: fixed; bottom: 100px; left: 10px; right: 10px; background: rgba(0,0,0,0.9); padding: 10px; border-radius: 8px; z-index: 1000; max-height: 200px; overflow-y: auto;';
  document.body.appendChild(div);
  return div;
}

// Загрузка данных из API
async function loadProducts() {
  showDebug('🔄 Начинаем загрузку...');
  
  try {
    showDebug('📡 Запрос к /api/products');
    const response = await fetch('/api/products');
    
    showDebug(`📊 Статус ответа: ${response.status}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    products = await response.json();
    showDebug(`✅ Загружено товаров: ${products.length}`);
    
    if (products.length === 0) {
      showDebug('⚠️ Массив товаров пустой!', true);
    } else {
      showDebug(`Первый товар: ${products[0].name}`);
    }
    
    showAll();
  } catch (error) {
    showDebug(`❌ ОШИБКА: ${error.message}`, true);
    document.getElementById('product-list').innerHTML = 
      `<p style="color: #ff5555; text-align: center; padding: 20px; grid-column: 1/-1;">
        Ошибка загрузки товаров<br><br>
        ${error.message}
      </p>`;
  }
}

const productList = document.getElementById("product-list");
const modal = document.getElementById("product-modal");
const categoryTitle = document.getElementById("category-title");
const modalTitle = document.getElementById("modal-title");
const modalImage = document.getElementById("modal-image");
const modalPrice = document.getElementById("modal-price");
const modalDesc = document.getElementById("modal-description");
const weightInput = document.getElementById("weight-input");
const totalPrice = document.getElementById("total-price");
const buyBtn = document.getElementById("buy-btn");
const cartBadge = document.getElementById("cart-badge");

let currentProduct = null;

function displayProducts(items) {
  showDebug(`📦 Отображаем ${items.length} товаров`);
  productList.innerHTML = "";
  
  if (items.length === 0) {
    productList.innerHTML = '<p style="color: #666; text-align: center; padding: 20px; grid-column: 1/-1;">Товары не найдены 🤷‍♂️</p>';
    return;
  }
  
  items.forEach((p, index) => {
    showDebug(`Товар ${index + 1}: ${p.name} - ${p.price} ₽`);
    
    const card = document.createElement("div");
    card.className = "product";
    
    let imgSrc = p.image || getDefaultImage(p.category);
    
    card.innerHTML = `
      <img src="${imgSrc}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/300x160/2d2d2d/666?text=Нет+фото'">
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
  currentCategory = 'Все товары';
  categoryTitle.textContent = currentCategory;
  displayProducts(products);
  setActiveButton('all');
  setActiveFooterButton(0);
}

function filterCategory(cat) {
  currentCategory = cat;
  categoryTitle.textContent = cat;
  const filtered = products.filter(p => p.category === cat);
  displayProducts(filtered);
  setActiveButton(cat);
}

function setActiveButton(category) {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  if (category === 'all') {
    document.querySelector('.nav-btn[onclick="showAll()"]').classList.add('active');
  } else {
    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.textContent.includes(category));
    if (btn) btn.classList.add('active');
  }
}

function setActiveFooterButton(index) {
  document.querySelectorAll('.footer-btn').forEach((btn, i) => {
    if (i === index) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

function openProduct(p) {
  currentProduct = p;
  modal.style.display = "block";
  document.body.style.overflow = "hidden";
  
  modalTitle.textContent = p.name;
  modalImage.src = p.image || getDefaultImage(p.category);
  modalImage.onerror = () => {
    modalImage.src = 'https://via.placeholder.com/400x220/2d2d2d/666?text=Нет+фото';
  };
  modalPrice.textContent = `${p.price} ₽/кг`;
  modalDesc.textContent = p.description || 'Описание отсутствует';
  
  weightInput.value = '1.0';
  updateTotalPrice();
}

function updateTotalPrice() {
  if (!currentProduct) return;
  
  let weight = parseFloat(weightInput.value);
  
  if (isNaN(weight) || weight <= 0) {
    weight = 0;
    totalPrice.textContent = '0 ₽';
    totalPrice.style.color = '#999';
    buyBtn.disabled = true;
    buyBtn.style.opacity = '0.5';
    return;
  }
  
  if (weight > 100) {
    weight = 100;
    weightInput.value = '100';
  }
  
  const total = Math.round(currentProduct.price * weight);
  totalPrice.textContent = `${total} ₽`;
  totalPrice.style.color = '#4CAF50';
  buyBtn.disabled = false;
  buyBtn.style.opacity = '1';
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
    cart[currentProduct.id] = {
      product: currentProduct,
      weight: weight
    };
  }
  
  showTelegramAlert(`✅ Добавлено в корзину:\n\n${currentProduct.name}\n${weight} кг × ${currentProduct.price} ₽ = ${total} ₽`);
  
  closeModal();
  updateCartBadge();
}

function updateCartBadge() {
  const count = Object.keys(cart).length;
  if (count > 0) {
    cartBadge.textContent = count;
    cartBadge.style.display = 'block';
  } else {
    cartBadge.style.display = 'none';
  }
}

function closeModal() {
  modal.style.display = "none";
  document.body.style.overflow = "auto";
  currentProduct = null;
}

function openSupport() {
  showTelegramAlert("💬 Поддержка\n\nСвяжитесь с нами:\n@your_support_bot");
}

function openCart() {
  setActiveFooterButton(1);
  const items = Object.values(cart);
  
  if (items.length === 0) {
    showTelegramAlert("Корзина пока пуста 🧺\n\nДобавьте товары из каталога!");
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
  showTelegramAlert("У вас нет заказов 📦\n\nОформите первый заказ!");
}

function showTelegramAlert(text) {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.showAlert(text);
  } else {
    alert(text);
  }
}

window.onclick = function(e) {
  if (e.target == modal) {
    closeModal();
  }
}

// Инициализация Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
  const tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#2d2d2d');
  tg.setBackgroundColor('#1a1a1a');
  showDebug('✅ Telegram WebApp инициализирован');
} else {
  showDebug('⚠️ Telegram WebApp недоступен', true);
}

// Загрузка при старте
showDebug('🚀 Запуск приложения');
loadProducts();
