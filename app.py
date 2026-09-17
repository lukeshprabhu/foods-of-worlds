from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import create_database, create_tables, get_connection
from config import Config
from datetime import datetime
import os, uuid

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

create_database()
create_tables()

def query(sql, params=(), fetch=False, many=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
        result = cur.fetchall() if fetch else None
        conn.commit()
        return result
    finally:
        cur.close(); conn.close()

def login_required():
    return "user_id" in session

@app.context_processor
def common():
    return {"now": datetime.now()}

@app.route("/")
def index():
    foods = query("""SELECT f.*, c.name category FROM foods f LEFT JOIN categories c ON f.category_id=c.id
                    WHERE f.is_available=1 ORDER BY f.id DESC""", fetch=True)
    offers = query("""SELECT * FROM offers WHERE is_active=1 AND valid_from<=NOW() AND valid_until>=NOW()
                      ORDER BY id DESC LIMIT 3""", fetch=True)
    return render_template("index.html", foods=foods, offers=offers)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        phone=request.form.get("phone","").strip(); password=request.form["password"]
        if query("SELECT id FROM users WHERE email=%s",(email,),True):
            flash("Email already registered.","error")
        else:
            query("INSERT INTO users(name,email,phone,password_hash) VALUES(%s,%s,%s,%s)",
                  (name,email,phone,generate_password_hash(password)))
            flash("Registration successful. Please login.","success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); password=request.form["password"]
        rows=query("SELECT * FROM users WHERE email=%s",(email,),True)
        if rows and check_password_hash(rows[0]["password_hash"],password):
            u=rows[0]; session.update(user_id=u["id"],user_name=u["name"],user_email=u["email"])
            return redirect(url_for("index"))
        flash("Invalid email or password.","error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/foods")
def foods():
    cats=query("SELECT * FROM categories ORDER BY name",fetch=True)
    rows=query("""SELECT f.*,c.name category FROM foods f LEFT JOIN categories c ON f.category_id=c.id
                  WHERE f.is_available=1 ORDER BY c.name,f.name""",fetch=True)
    return render_template("foods.html",foods=rows,categories=cats)

@app.route("/search")
def search():
    q=request.args.get("q","").strip()
    rows=query("""SELECT f.*,c.name category FROM foods f LEFT JOIN categories c ON f.category_id=c.id
                  WHERE f.is_available=1 AND (f.name LIKE %s OR f.description LIKE %s OR c.name LIKE %s)
                  ORDER BY f.name""",(f"%{q}%",f"%{q}%",f"%{q}%"),True)
    return render_template("foods.html",foods=rows,categories=[],search_query=q)

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route("/checkout")
def checkout():
    if not login_required(): return redirect(url_for("login"))
    addresses=query("SELECT * FROM addresses WHERE user_id=%s ORDER BY is_default DESC,id DESC",(session["user_id"],),True)
    return render_template("checkout.html",addresses=addresses)

@app.route("/save-address",methods=["POST"])
def save_address():
    if not login_required(): return jsonify(ok=False,error="Login required"),401
    data=request.get_json() or {}
    address=data.get("address","").strip()
    if not address: return jsonify(ok=False,error="Address required"),400
    query("UPDATE addresses SET is_default=0 WHERE user_id=%s",(session["user_id"],))
    query("""INSERT INTO addresses(user_id,label,address,latitude,longitude,phone,is_default)
             VALUES(%s,%s,%s,%s,%s,%s,1)""",
          (session["user_id"],data.get("label","Home"),address,data.get("latitude"),data.get("longitude"),data.get("phone","")))
    return jsonify(ok=True)

@app.route("/place-order",methods=["POST"])
def place_order():
    if not login_required(): return jsonify(ok=False,error="Login required"),401
    data=request.get_json() or {}; cart=data.get("cart",[])
    address=data.get("address","").strip(); phone=data.get("phone","").strip()
    payment=data.get("payment","Cash on Delivery"); coupon=(data.get("coupon_code") or "").strip().upper()
    if not cart or not address: return jsonify(ok=False,error="Cart and address are required"),400

    subtotal=0; items=[]
    conn=get_connection(); cur=conn.cursor(dictionary=True)
    try:
        for item in cart:
            cur.execute("SELECT id,name,price,is_available FROM foods WHERE id=%s",(item.get("id"),))
            food=cur.fetchone()
            if not food or not food["is_available"]: return jsonify(ok=False,error="Food unavailable"),400
            qty=max(1,int(item.get("quantity",1))); line=float(food["price"])*qty
            subtotal+=line; items.append((food,qty,line))
        discount=0
        if coupon:
            cur.execute("""SELECT * FROM offers WHERE coupon_code=%s AND is_active=1
                           AND valid_from<=NOW() AND valid_until>=NOW() AND min_order<=%s""",(coupon,subtotal))
            offer=cur.fetchone()
            if offer:
                discount=(subtotal*float(offer["discount_value"])/100 if offer["discount_type"]=="percent" else float(offer["discount_value"]))
                discount=min(discount,subtotal)
            else:
                return jsonify(ok=False,error="Invalid or expired coupon"),400
        delivery=50 if subtotal<999 else 0
        total=subtotal+delivery-discount
        order_no="WOF-"+uuid.uuid4().hex[:10].upper()
        cur.execute("""INSERT INTO orders(order_number,user_id,address,phone,subtotal,delivery_fee,discount,coupon_code,total_amount,payment_method)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (order_no,session["user_id"],address,phone,subtotal,delivery,discount,coupon or None,total,payment))
        oid=cur.lastrowid
        for food,qty,line in items:
            cur.execute("""INSERT INTO order_items(order_id,food_id,food_name,price,quantity,line_total)
                           VALUES(%s,%s,%s,%s,%s,%s)""",(oid,food["id"],food["name"],food["price"],qty,line))
        conn.commit()
        return jsonify(ok=True,order_id=oid,order_number=order_no)
    finally:
        cur.close(); conn.close()

@app.route("/order-success/<int:order_id>")
def order_success(order_id):
    if not login_required(): return redirect(url_for("login"))
    rows=query("""SELECT o.*,u.name customer FROM orders o JOIN users u ON o.user_id=u.id
                  WHERE o.id=%s AND o.user_id=%s""",(order_id,session["user_id"]),True)
    if not rows: return "Order not found",404
    items=query("SELECT * FROM order_items WHERE order_id=%s",(order_id,),True)
    return render_template("order_success.html",order=rows[0],items=items)

@app.route("/my-orders")
def my_orders():
    if not login_required(): return redirect(url_for("login"))
    rows=query("SELECT * FROM orders WHERE user_id=%s ORDER BY id DESC",(session["user_id"],),True)
    return render_template("my_orders.html",orders=rows)

@app.route("/favorites")
def favorites():
    if not login_required(): return redirect(url_for("login"))
    rows=query("""SELECT f.*,c.name category FROM favorites v JOIN foods f ON v.food_id=f.id
                  LEFT JOIN categories c ON f.category_id=c.id WHERE v.user_id=%s""",(session["user_id"],),True)
    return render_template("favorites.html",foods=rows)

@app.route("/favorite/<int:food_id>",methods=["POST"])
def favorite(food_id):
    if not login_required(): return jsonify(ok=False),401
    exists=query("SELECT id FROM favorites WHERE user_id=%s AND food_id=%s",(session["user_id"],food_id),True)
    if exists: query("DELETE FROM favorites WHERE user_id=%s AND food_id=%s",(session["user_id"],food_id))
    else: query("INSERT INTO favorites(user_id,food_id) VALUES(%s,%s)",(session["user_id"],food_id))
    return jsonify(ok=True,favorited=not bool(exists))

# ---------- ADMIN ----------
def admin_required():
    return "admin_id" in session

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        username=request.form["username"].strip()
        rows=query("SELECT * FROM admins WHERE username=%s",(username,),True)
        if rows and check_password_hash(rows[0]["password_hash"],request.form["password"]):
            session["admin_id"]=rows[0]["id"]; session["admin_username"]=username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin login.","error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id",None); session.pop("admin_username",None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@app.route("/admin/dashboard")
def admin_dashboard():
    if not admin_required(): return redirect(url_for("admin_login"))
    stats={
        "foods":query("SELECT COUNT(*) n FROM foods",fetch=True)[0]["n"],
        "users":query("SELECT COUNT(*) n FROM users",fetch=True)[0]["n"],
        "orders":query("SELECT COUNT(*) n FROM orders",fetch=True)[0]["n"],
        "employees":query("SELECT COUNT(*) n FROM employees",fetch=True)[0]["n"]
    }
    return render_template("admin/dashboard.html",stats=stats)

@app.route("/admin/foods")
def admin_foods():
    if not admin_required(): return redirect(url_for("admin_login"))
    rows=query("""SELECT f.*,c.name category FROM foods f LEFT JOIN categories c ON f.category_id=c.id ORDER BY f.id DESC""",fetch=True)
    cats=query("SELECT * FROM categories ORDER BY name",fetch=True)
    return render_template("admin/foods.html",foods=rows,categories=cats)

@app.route("/admin/food/add",methods=["POST"])
def add_food():
    if not admin_required(): return redirect(url_for("admin_login"))
    name=request.form["name"]; cat=int(request.form["category_id"]); desc=request.form.get("description","")
    price=float(request.form["price"]); available=1 if request.form.get("is_available") else 0
    query("INSERT INTO foods(name,category_id,description,price,is_available) VALUES(%s,%s,%s,%s,%s)",(name,cat,desc,price,available))
    return redirect(url_for("admin_foods"))

@app.route("/admin/food/delete/<int:food_id>",methods=["POST"])
def delete_food(food_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    query("DELETE FROM foods WHERE id=%s",(food_id,)); return redirect(url_for("admin_foods"))

@app.route("/admin/orders")
def admin_orders():
    if not admin_required(): return redirect(url_for("admin_login"))
    rows=query("""SELECT o.*,u.name customer,u.email FROM orders o JOIN users u ON o.user_id=u.id ORDER BY o.id DESC""",fetch=True)
    return render_template("admin/orders.html",orders=rows)

@app.route("/admin/order-status/<int:order_id>",methods=["POST"])
def order_status(order_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    query("UPDATE orders SET order_status=%s WHERE id=%s",(request.form["status"],order_id))
    return redirect(url_for("admin_orders"))

@app.route("/admin/employees")
def admin_employees():
    if not admin_required(): return redirect(url_for("admin_login"))
    rows=query("SELECT * FROM employees ORDER BY id DESC",fetch=True)
    return render_template("admin/employees.html",employees=rows)

@app.route("/admin/employee/add",methods=["GET","POST"])
def admin_employee_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    if request.method=="POST":
        fields=["employee_number","full_name","phone","email","date_of_birth","nationality","designation",
                "employment_status","joining_date","address","emergency_contact","emergency_phone",
                "passport_number","passport_issue_date","passport_expiry_date","visa_number","visa_issue_date",
                "visa_expiry_date","id_number","id_issue_date","id_expiry_date"]
        vals=[request.form.get(x) or None for x in fields]
        placeholders=",".join(["%s"]*len(fields))
        query(f"INSERT INTO employees({','.join(fields)}) VALUES({placeholders})",tuple(vals))
        flash("Employee added.","success"); return redirect(url_for("admin_employees"))
    return render_template("admin/add_employee.html")

@app.route("/admin/employee/delete/<int:employee_id>",methods=["POST"])
def admin_employee_delete(employee_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    query("DELETE FROM employees WHERE id=%s",(employee_id,)); return redirect(url_for("admin_employees"))

@app.route("/admin/employee/<int:employee_id>/documents",methods=["GET","POST"])
def employee_documents(employee_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    emp=query("SELECT * FROM employees WHERE id=%s",(employee_id,),True)
    if not emp: return "Employee not found",404
    if request.method=="POST":
        f=request.files.get("document")
        if not f or not f.filename: flash("Choose a file.","error")
        else:
            dtype=request.form.get("document_type","Other")
            safe=secure_filename(f.filename)
            folder=os.path.join(app.config["UPLOAD_FOLDER"],"employees",dtype.lower().replace(" ","_"))
            os.makedirs(folder,exist_ok=True)
            filename=f"{uuid.uuid4().hex}_{safe}"
            f.save(os.path.join(folder,filename))
            rel=os.path.relpath(os.path.join(folder,filename),app.config["UPLOAD_FOLDER"])
            query("""INSERT INTO employee_documents(employee_id,document_type,document_name,file_path,expiry_date)
                     VALUES(%s,%s,%s,%s,%s)""",(employee_id,dtype,safe,rel,request.form.get("expiry_date") or None))
            flash("Document uploaded.","success")
    docs=query("SELECT * FROM employee_documents WHERE employee_id=%s ORDER BY id DESC",(employee_id,),True)
    return render_template("admin/employee_documents.html",employee=emp[0],documents=docs)

@app.route("/admin/document/delete/<int:doc_id>",methods=["POST"])
def document_delete(doc_id):
    if not admin_required(): return redirect(url_for("admin_employees"))
    rows=query("SELECT * FROM employee_documents WHERE id=%s",(doc_id,),True)
    if rows:
        p=os.path.join(app.config["UPLOAD_FOLDER"],rows[0]["file_path"])
        if os.path.exists(p): os.remove(p)
        query("DELETE FROM employee_documents WHERE id=%s",(doc_id,))
    return redirect(request.referrer or url_for("admin_employees"))

@app.route("/admin/document/<int:doc_id>/download")
def document_download(doc_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    rows=query("SELECT * FROM employee_documents WHERE id=%s",(doc_id,),True)
    if not rows: return "Not found",404
    doc=rows[0]; full=os.path.join(app.config["UPLOAD_FOLDER"],doc["file_path"])
    return send_from_directory(os.path.dirname(full),os.path.basename(full),as_attachment=True)

@app.route("/admin/offers",methods=["GET","POST"])
def admin_offers():
    if not admin_required(): return redirect(url_for("admin_login"))
    if request.method=="POST":
        query("""INSERT INTO offers(title,coupon_code,description,discount_type,discount_value,min_order,valid_from,valid_until,is_active)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,1)""",
              (request.form["title"],request.form["coupon_code"].upper(),request.form.get("description",""),
               request.form["discount_type"],request.form["discount_value"],request.form.get("min_order",0),
               request.form["valid_from"],request.form["valid_until"]))
        return redirect(url_for("admin_offers"))
    offers=query("SELECT * FROM offers ORDER BY id DESC",fetch=True)
    return render_template("admin/offers.html",offers=offers)

if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
