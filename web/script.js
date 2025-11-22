let products = [];
let cart = {}; // Корзина: {productId: {product, weight}}

// Загрузка данных из API
async function loadProducts() {
  try {
    const response = await fetch('/api/products');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    products = await response.json();
    console.log('✅ Загружено товаров:', products.length);
    showAll();
  } catch (error) {
    console.error('❌ Ошибка загрузки:', error);
    document.getElementById('product-list').innerHTML = 
      '<p style="color: red; text-align: center; padding: 20px;">Ошибка загрузки товаров. Проверьте соединение.</p>';
  }
}

const productList = document.getElementById("product-list");
const modal = document.getElementById("product-modal");
const modalTitle = document.getElementById("modal-title");
const modalImage = document.getElementById("modal-image");
const modalPrice = document.getElementById("modal-price");
const modalDesc = document.getElementById("modal-description");
const weightInput = document.getElementById("weight-input");
const totalPrice = document.getElementById("total-price");
const buyBtn = document.getElementById("buy-btn");

let currentProduct = null;

function displayProducts(items) {
  productList.innerHTML = "";
  
  if (items.length === 0) {
    productList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Товары не найдены 🤷‍♂️</p>';
    return;
  }
  
  items.forEach(p => {
    const card = document.createElement("div");
    card.className = "product";
    
    // Используем изображение из базы или дефолтное по категории
    let imgSrc = p.image || getDefaultImage(p.category);
    
    card.innerHTML = `
      <img src="${imgSrc}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/160x120?text=Нет+фото'">
      <h3>${p.name}</h3>
      <p><strong>${p.price} ₽/кг</strong></p>
    `;
    card.onclick = () => openProduct(p);
    productList.appendChild(card);
  });
}

// Дефолтные картинки по категориям
function getDefaultImage(category) {
  const defaults = {
    'Варенье': 'https://cdn-icons-png.flaticon.com/512/415/415733.png',
    'Мёд': 'https://cdn-icons-png.flaticon.com/512/2909/2909762.png',
    'Чай': 'https://cdn-icons-png.flaticon.com/512/590/590836.png'
  };
  return defaults[category] || 'https://cdn-icons-png.flaticon.com/512/3050/3050156.png';
}

function showAll() {
  displayProducts(products);
  setActiveButton('all');
}

function filterCategory(cat) {
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
    document.querySelector(`.nav-btn[onclick="filterCategory('${category}')"]`).classList.add('active');
  }
}

function openProduct(p) {
  currentProduct = p;
  modal.style.display = "block";
  modalTitle.textContent = p.name;
  modalImage.src = p.image || getDefaultImage(p.category);
  modalImage.onerror = () => {
    modalImage.src = 'https://via.placeholder.com/400x200?text=Нет+фото';
  };
  modalPrice.textContent = `${p.price} ₽/кг`;
  modalDesc.textContent = p.description || 'Описание отсутствует';
  
  // Сбрасываем вес и цену
  weightInput.value = '1.0';
  updateTotalPrice();
}

// Обновление итоговой цены при изменении веса
function updateTotalPrice() {
  if (!currentProduct) return;
  
  let weight = parseFloat(weightInput.value);
  
  // Валидация веса
  if (isNaN(weight) || weight <= 0) {
    weight = 0;
    totalPrice.textContent = '0 ₽';
    totalPrice.style.color = '#999';
    buyBtn.disabled = true;
    buyBtn.style.opacity = '0.5';
    return;
  }
  
  // Ограничение максимального веса
  if (weight > 100) {
    weight = 100;
    weightInput.value = '100';
  }
  
  const total = Math.round(currentProduct.price * weight);
  totalPrice.textContent = `${total} ₽`;
  totalPrice.style.color = '#8bc34a';
  buyBtn.disabled = false;
  buyBtn.style.opacity = '1';
}

function addToCart() {
  if (!currentProduct) return;
  
  const weight = parseFloat(weightInput.value);
  
  if (isNaN(weight) || weight <= 0) {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.showAlert("❌ Укажите корректный вес!");
    } else {
      alert("❌ Укажите корректный вес!");
    }
    return;
  }
  
  const total = Math.round(currentProduct.price * weight);
  
  // Добавляем в корзину (или обновляем)
  if (cart[currentProduct.id]) {
    cart[currentProduct.id].weight += weight;
  } else {
    cart[currentProduct.id] = {
      product: currentProduct,
      weight: weight
    };
  }
  
  // Уведомление
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.showAlert(`✅ Добавлено в корзину:\n\n${currentProduct.name}\n${weight} кг × ${currentProduct.price} ₽ = ${total} ₽`);
  } else {
    alert(`✅ Добавлено в корзину:\n\n${currentProduct.name}\n${weight} кг × ${currentProduct.price} ₽ = ${total} ₽`);
  }
  
  closeModal();
  updateCartCount();
}

function updateCartCount() {
  const count = Object.keys(cart).length;
  // Можно добавить badge на кнопку корзины
  console.log('Товаров в корзине:', count);
}

function closeModal() {
  modal.style.display = "none";
  currentProduct = null;
}

function openSupport() {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.openTelegramLink("https://t.me/your_support_bot");
  } else {
    alert("Поддержка скоро будет доступна 💬");
  }
}

function openCart() {
  const items = Object.values(cart);
  
  if (items.length === 0) {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.showAlert("Корзина пока пуста 🧺\n\nДобавьте товары из каталога!");
    } else {
      alert("Корзина пока пуста 🧺");
    }
    return;
  }
  
  // Формируем список заказа
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
  
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.showAlert(message);
  } else {
    alert(message);
  }
}

function openOrders() {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.showAlert("У вас нет заказов 📦\n\nОформите первый заказ!");
  } else {
    alert("У вас нет заказов 📦");
  }
}

// Закрытие модалки при клике вне её
window.onclick = function(e) {
  if (e.target == modal) {
    modal.style.display = "none";
  }
}

// Инициализация Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
  const tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
  
  // Применяем тему Telegram
  document.body.style.backgroundColor = tg.themeParams.bg_color || '#f5f5f5';
}

// ЗАПУСК: загружаем данные при старте
loadProducts();
