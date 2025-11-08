const products = [
  {
    id: 1,
    name: "Клубника",
    category: "berries",
    price: 350,
    img: "https://cdn-icons-png.flaticon.com/512/415/415733.png",
    desc: "Сочная спелая клубника, выращенная с любовью."
  },
  {
    id: 2,
    name: "Черника",
    category: "berries",
    price: 420,
    img: "https://cdn-icons-png.flaticon.com/512/415/415747.png",
    desc: "Свежая черника — вкусная и полезная для зрения."
  },
  {
    id: 3,
    name: "Мёд липовый",
    category: "honey",
    price: 600,
    img: "https://cdn-icons-png.flaticon.com/512/2909/2909762.png",
    desc: "Натуральный липовый мёд, собранный в экологичных районах."
  },
  {
    id: 4,
    name: "Чай ягодный",
    category: "tea",
    price: 250,
    img: "https://cdn-icons-png.flaticon.com/512/590/590836.png",
    desc: "Тёплый ароматный чай с ягодами и травами."
  }
];

const productList = document.getElementById("product-list");
const modal = document.getElementById("product-modal");
const modalTitle = document.getElementById("modal-title");
const modalImage = document.getElementById("modal-image");
const modalPrice = document.getElementById("modal-price");
const modalDesc = document.getElementById("modal-description");

function displayProducts(items) {
  productList.innerHTML = "";
  items.forEach(p => {
    const card = document.createElement("div");
    card.className = "product";
    card.innerHTML = `
      <img src="${p.img}" alt="${p.name}">
      <h3>${p.name}</h3>
      <p>${p.price} ₽/кг</p>
    `;
    card.onclick = () => openProduct(p);
    productList.appendChild(card);
  });
}

function showAll() {
  displayProducts(products);
}

function filterCategory(cat) {
  displayProducts(products.filter(p => p.category === cat));
}

function openProduct(p) {
  modal.style.display = "block";
  modalTitle.textContent = p.name;
  modalImage.src = p.img;
  modalPrice.textContent = `${p.price} ₽/кг`;
  modalDesc.textContent = p.desc;
}

function closeModal() {
  modal.style.display = "none";
}

function openSupport() {
  alert("Поддержка скоро будет доступна 💬");
}

function openCart() {
  alert("Корзина пока пуста 🧺");
}

function openOrders() {
  alert("У вас нет заказов 📦");
}

window.onclick = function(e) {
  if (e.target == modal) modal.style.display = "none";
}

showAll();
