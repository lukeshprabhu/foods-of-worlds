function renderCart(){let el=document.getElementById("cart");if(!el)return;let subtotal=0;el.innerHTML=cart.length?"":"<p>Your cart is empty.</p>";cart.forEach((x,i)=>{subtotal+=x.price*x.quantity;el.innerHTML+=`<div class="card"><b>${x.name}</b><p>${money(x.price)} × <button onclick="changeQty(${i},-1)">−</button> ${x.quantity} <button onclick="changeQty(${i},1)">+</button> <button onclick="removeItem(${i})">Remove</button></p></div>`});let s=document.getElementById("subtotal");if(s)s.textContent=money(subtotal)}
function changeQty(i,d){cart[i].quantity+=d;if(cart[i].quantity<=0)cart.splice(i,1);saveCart();renderCart()}
function removeItem(i){cart.splice(i,1);saveCart();renderCart()}
document.addEventListener("DOMContentLoaded",renderCart);
