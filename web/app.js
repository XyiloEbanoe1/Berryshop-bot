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
const buyBtn = document.getElementById("buy-btn");
const cartBadge = document.getElementById("cart-badge");

let currentProduct = null;
let selectedWeight = null;
let selectedDiscount = 0;

function getImagePath(p) {
  if (p.image) {
    const clean = p.image.replace('images/', '');
    return `/images/${clean}`;
  }
  return '/images/placeholder.jpg';
}

// Функция для умного определения веса
function parseSmartWeight(inputValue) {
  const value = parseFloat(inputValue);
  
  if (isNaN(value)) return { weight: null, error: "Введите число" };
  
  // Дробные числа 0.2-49.9 → кг
  if (value.toString().includes('.') && value >= 0.2 && value <= 49.9) {
    return { weight: value, unit: 'kg' };
  }
  
  // Целые числа 1-50 → кг
  if (Number.isInteger(value) && value >= 1 && value <= 50) {
    return { weight: value, unit: 'kg' };
  }
  
  // Целые числа 200-999 → граммы
  if (Number.isInteger(value) && value >= 200 && value <= 999) {
    return { weight: value / 1000, unit: 'g' };
  }
  
  // Ошибка для непонятных значений
  if (value >= 50 && value <= 199) {
    return { weight: null, error: "Непонятный вес. Введите:\n• 200-999 (граммы)\n• 0.2-50 (килограммы)" };
  }
  
  return { weight: null, error: "Введите вес от 200г до 50кг" };
}

// Функция для определения логики цены по категории
function getPriceLogic(category) {
  const logic = {
    "Варенье": {
      display: (price) => `${Math.round(price / 10)} ₽/100г`,
      modalDisplay: (price) => `${Math.round(price / 10)} ₽/100г`, // ИЗМЕНИЛ - теперь за 100г
      calculate: (price, weight) => (price / 10) * weight * 10, // цена за 100г × вес в кг × 10
      minWeight: 0.2, // 200г
      maxWeight: 50,
      step: 0.1,
      placeholder: "Введите вес (200-999г или 0.2-50кг)"
    },
    "Мёд": {
      display: (price) => `${price} ₽/кг`,
      modalDisplay: (price) => `${price} ₽/кг`,
      calculate: (price, weight) => price * weight,
      minWeight: 0.2, // 200г
      maxWeight: 50,
      step: 0.1,
      placeholder: "Введите вес (200-999г или 0.2-50кг)"
    },
    "Чай": {
      display: (price) => `${price} ₽/100г`,
      modalDisplay: (price) => `${price} ₽/100г`,
      calculate: (price, weight) => price * weight * 10, // 500 руб за 100г = 5000 руб за кг
      minWeight: 0.025,
      maxWeight: 1,
      step: 0.025,
      placeholder: "Введите вес (0.025-1 кг)"
    }
  };
  return logic[category] || logic["Варенье"];
}

function displayProducts(items) {
  productList.innerHTML = "";
  
  if (items.length === 0) {
    productList.innerHTML = '<p style="color: #666; text-align: center; padding: 20px; grid-column: 1/-1;">Товары не найдены</p>';
    return;
  }
  
  let currentCategory = "";
  
  items.forEach(p => {
    // Если категория изменилась - добавляем заголовок категории
    if (p.category !== currentCategory) {
      currentCategory = p.category;
      
      const categoryHeader = document.createElement("div");
      categoryHeader.className = "category-header";
      categoryHeader.style.gridColumn = "1 / -1";
      categoryHeader.style.marginTop = "20px";
      categoryHeader.style.marginBottom = "10px";
      categoryHeader.style.paddingLeft = "10px";
      categoryHeader.style.borderLeft = "4px solid #4CAF50";
      
      let emoji = "📦";
      if (p.category === "Варенье") emoji = "🍓";
      if (p.category === "Мёд") emoji = "🍯";
      if (p.category === "Чай") emoji = "🍵";
      
      categoryHeader.innerHTML = `
        <h3 style="color: #4CAF50; font-size: 18px; font-weight: bold; margin: 0;">
          ${emoji} ${p.category}
        </h3>
        <div style="color: #666; font-size: 12px; margin-top: 2px;">
          ${getCategoryDescription(p.category)}
        </div>
      `;
      productList.appendChild(categoryHeader);
    }
    
    const card = document.createElement("div");
    card.className = "product";

    const imgSrc = getImagePath(p);
    const priceLogic = getPriceLogic(p.category);
    
    card.innerHTML = `
      <img src="${imgSrc}" alt="${p.name}"
           onerror="this.src='/images/placeholder.jpg'">
      <div class="product-info">
        <div class="product-rating">⭐ (0)</div>
        <h3>${p.name}</h3>
        <div class="product-price">${priceLogic.display(p.price)}</div>
      </div>
    `;
    card.onclick = () => openProduct(p);
    productList.appendChild(card);
  });
}

// Функция для описания категорий
function getCategoryDescription(category) {
  const descriptions = {
    "Варенье": "Натуральные ягодные варенья из северных лесов",
    "Мёд": "Свежий мёд от местных пасечников", 
    "Чай": "Ароматные травяные сборы"
  };
  return descriptions[category] || "Категория товаров";
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
    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b =>
      b.textContent.includes(category)
    );
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
  selectedWeight = null;
  selectedDiscount = 0;
  
  modal.style.display = "block";
  document.body.style.overflow = "hidden";

  document.getElementById("modal-title").textContent = p.name;
  document.getElementById("modal-image").src = getImagePath(p);
  
  const priceLogic = getPriceLogic(p.category);
  document.getElementById("modal-price").textContent = priceLogic.modalDisplay(p.price);
  
  document.getElementById("modal-description").innerHTML = (p.description || 'Описание отсутствует').replace(/\n/g, '<br>');

  // Показываем блок выбора веса
  showWeightOptions();
}

function showWeightOptions() {
  const container = document.getElementById("weight-container");
  const priceLogic = getPriceLogic(currentProduct.category);
  
  // Для чая убираем готовые варианты (только кастомный ввод)
  if (currentProduct.category === "Чай") {
    container.innerHTML = `
      <div id="custom-weight-input" style="margin-top: 15px;">
        <label for="weight-input">⚖️ Укажите вес:</label>
        <input 
          type="number" 
          id="weight-input" 
          min="${priceLogic.minWeight}" 
          max="${priceLogic.maxWeight}" 
          step="${priceLogic.step}" 
          placeholder="${priceLogic.placeholder}"
          oninput="updateCustomPrice()">
        <div id="weight-error" style="color: #ff5555; font-size: 12px; margin-top: 5px; display: none;"></div>
      </div>
      
      <div id="total-price-block" style="display: none; margin-top: 15px;">
        <div class="total-price">
          Итого: <span id="total-price">0 ₽</span>
        </div>
      </div>
    `;
  } else {
    // Для варенья и мёда - готовые варианты + кастомный
    container.innerHTML = `
      <div class="weight-options">
        <button class="weight-option-btn" onclick="selectWeight(1.4, 0)">
          <span class="weight-value">~1.4 кг</span>
          <span class="weight-price">${Math.round(priceLogic.calculate(currentProduct.price, 1.4))} ₽</span>
        </button>
        
        <button class="weight-option-btn" onclick="selectWeight(2.1, 5)">
          <span class="weight-value">~2.1 кг</span>
          <span class="weight-discount">-5%</span>
          <span class="weight-price">${Math.round(priceLogic.calculate(currentProduct.price, 2.1) * 0.95)} ₽</span>
        </button>
        
        <button class="weight-option-btn" onclick="selectWeight(2.8, 10)">
          <span class="weight-value">~2.8 кг</span>
          <span class="weight-discount">-10%</span>
          <span class="weight-price">${Math.round(priceLogic.calculate(currentProduct.price, 2.8) * 0.9)} ₽</span>
        </button>
        
        <button class="weight-option-btn custom" onclick="showCustomInput()">
          <span class="weight-value">✏️ Свой вариант</span>
        </button>
      </div>
      
      <div id="custom-weight-input" style="display: none; margin-top: 15px;">
        <label for="weight-input">⚖️ Укажите вес:</label>
        <input 
          type="number" 
          id="weight-input" 
          step="0.001"
          placeholder="${priceLogic.placeholder}"
          oninput="updateCustomPrice()">
        <div id="weight-error" style="color: #ff5555; font-size: 12px; margin-top: 5px; display: none;"></div>
        <div style="color: #666; font-size: 11px; margin-top: 5px;">
          Примеры: 350 (граммы) или 1.5 (килограммы)
        </div>
      </div>
      
      <div id="total-price-block" style="display: none; margin-top: 15px;">
        <div class="total-price">
          Итого: <span id="total-price">0 ₽</span>
        </div>
      </div>
    `;
  }
  
  buyBtn.disabled = true;
  buyBtn.style.opacity = '0.5';
}

function selectWeight(weight, discount) {
  selectedWeight = weight;
  selectedDiscount = discount;
  
  // Скрываем custom input если был открыт
  document.getElementById("custom-weight-input").style.display = "none";
  
  // Подсвечиваем выбранную кнопку
  document.querySelectorAll('.weight-option-btn').forEach(btn => {
    btn.classList.remove('selected');
  });
  event.target.closest('.weight-option-btn').classList.add('selected');
  
  // Показываем итоговую цену
  updateTotalPrice();
}

function showCustomInput() {
  // Убираем выделение с кнопок
  document.querySelectorAll('.weight-option-btn').forEach(btn => {
    btn.classList.remove('selected');
  });
  event.target.closest('.weight-option-btn').classList.add('selected');
  
  selectedWeight = null;
  selectedDiscount = 0;
  
  document.getElementById("custom-weight-input").style.display = "block";
  document.getElementById("weight-input").focus();
  document.getElementById("total-price-block").style.display = "none";
  
  buyBtn.disabled = true;
  buyBtn.style.opacity = '0.5';
}

function updateCustomPrice() {
  const input = document.getElementById("weight-input");
  const errorDiv = document.getElementById("weight-error");
  const priceLogic = getPriceLogic(currentProduct.category);
  
  const result = parseSmartWeight(input.value);
  
  // Убираем ошибку
  errorDiv.style.display = "none";
  
  // Проверка на ошибки
  if (result.error) {
    errorDiv.textContent = result.error;
    errorDiv.style.display = "block";
    document.getElementById("total-price-block").style.display = "none";
    buyBtn.disabled = true;
    buyBtn.style.opacity = '0.5';
    return;
  }
  
  const weight = result.weight;
  
  // Дополнительная проверка минимума и максимума
  if (weight < priceLogic.minWeight) {
    errorDiv.textContent = `⚠️ Минимальный вес: ${priceLogic.minWeight} кг (${priceLogic.minWeight * 1000}г)`;
    errorDiv.style.display = "block";
    document.getElementById("total-price-block").style.display = "none";
    buyBtn.disabled = true;
    buyBtn.style.opacity = '0.5';
    return;
  }
  
  if (weight > priceLogic.maxWeight) {
    errorDiv.textContent = `⚠️ Максимальный вес: ${priceLogic.maxWeight} кг`;
    errorDiv.style.display = "block";
    document.getElementById("total-price-block").style.display = "none";
    buyBtn.disabled = true;
    buyBtn.style.opacity = '0.5';
    return;
  }
  
  // Показываем понятный вес в поле ввода
  if (result.unit === 'g') {
    input.value = weight * 1000; // показываем в граммах
  } else {
    input.value = weight; // показываем в кг
  }
  
  selectedWeight = weight;
  selectedDiscount = 0;
  updateTotalPrice();
}

function updateTotalPrice() {
  if (!selectedWeight) return;
  
  const priceBlock = document.getElementById("total-price-block");
  const totalPriceSpan = document.getElementById("total-price");
  const priceLogic = getPriceLogic(currentProduct.category);
  
  // Расчёт с учётом скидки
  const basePrice = priceLogic.calculate(currentProduct.price, selectedWeight);
  const discount = basePrice * (selectedDiscount / 100);
  const finalPrice = Math.round(basePrice - discount);
  
  let priceText = `${finalPrice} ₽`;
  
  if (selectedDiscount > 0) {
    priceText = `<span style="text-decoration: line-through; color: #999; font-size: 18px;">${Math.round(basePrice)} ₽</span> ${finalPrice} ₽`;
  }
  
  totalPriceSpan.innerHTML = priceText;
  priceBlock.style.display = "block";
  
  buyBtn.disabled = false;
  buyBtn.style.opacity = '1';
}

function addToCart() {
  if (!currentProduct || !selectedWeight) {
    showTelegramAlert("❌ Выберите вес!");
    return;
  }
  
  const priceLogic = getPriceLogic(currentProduct.category);
  const basePrice = priceLogic.calculate(currentProduct.price, selectedWeight);
  const discount = basePrice * (selectedDiscount / 100);
  const finalPrice = Math.round(basePrice - discount);
  
  if (cart[currentProduct.id]) {
    cart[currentProduct.id].weight += selectedWeight;
    cart[currentProduct.id].totalPrice += finalPrice;
  } else {
    cart[currentProduct.id] = { 
      product: currentProduct, 
      weight: selectedWeight,
      totalPrice: finalPrice,
      discount: selectedDiscount
    };
  }
  
  // Показываем вес в понятном формате
  let displayWeight = selectedWeight >= 1 ? 
    `${selectedWeight} кг` : 
    `${Math.round(selectedWeight * 1000)} г`;
  
  let message = `✅ Добавлено:\n\n${currentProduct.name}\n${displayWeight}`;
  
  if (selectedDiscount > 0) {
    message += ` (-${selectedDiscount}% скидка)`;
  }
  
  message += `\n💰 ${finalPrice} ₽`;
  
  showTelegramAlert(message);
  
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
  selectedWeight = null;
  selectedDiscount = 0;
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
    const price = item.totalPrice;
    totalSum += price;
    
    // Показываем вес в понятном формате
    const displayWeight = w >= 1 ? `${w} кг` : `${Math.round(w * 1000)} г`;
    
    message += `${p.name}\n${displayWeight}`;
    if (item.discount > 0) {
      message += ` (-${item.discount}%)`;
    }
    message += `\n${price} ₽\n\n`;
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
