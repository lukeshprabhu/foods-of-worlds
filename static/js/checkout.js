async function placeOrder(){
 const address=document.getElementById("address").value.trim(),phone=document.getElementById("phone").value.trim();
 const payment=document.getElementById("payment").value,coupon=document.getElementById("coupon").value.trim();
 if(!cart.length||!address){alert("Please add food and delivery address.");return}
 const r=await fetch("/place-order",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({cart,address,phone,payment,coupon_code:coupon})});
 const x=await r.json(); if(x.ok){localStorage.removeItem("wof_cart");location.href="/order-success/"+x.order_id}else alert(x.error||"Order failed");
}
async function saveLocation(){
 if(!navigator.geolocation){alert("Location is not supported.");return}
 navigator.geolocation.getCurrentPosition(async p=>{
   const address=prompt("Enter your delivery address:");
   if(!address)return;
   await fetch("/save-address",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({address,latitude:p.coords.latitude,longitude:p.coords.longitude,phone:document.getElementById("phone")?.value||""})});
   alert("Location saved.");
 },()=>alert("Location permission was not granted."));
}
