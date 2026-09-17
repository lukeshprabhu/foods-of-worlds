function money(n){return "₹"+Number(n).toFixed(2)}
let cart=JSON.parse(localStorage.getItem("wof_cart")||"[]");
function saveCart(){localStorage.setItem("wof_cart",JSON.stringify(cart));renderCartCount()}
function addToCart(id,name,price){let x=cart.find(i=>i.id===id);if(x)x.quantity++;else cart.push({id,name,price:Number(price),quantity:1});saveCart();alert(name+" added to cart");}
function renderCartCount(){let n=cart.reduce((a,b)=>a+b.quantity,0);document.querySelectorAll(".cart-count").forEach(x=>x.textContent=n)}
document.addEventListener("DOMContentLoaded",renderCartCount);
function toggleFavorite(id){fetch("/favorite/"+id,{method:"POST"}).then(r=>r.json()).then(x=>alert(x.favorited?"Added to favorites":"Removed from favorites"))}
