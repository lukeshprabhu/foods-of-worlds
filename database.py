import mysql.connector
from mysql.connector import Error
from config import Config

def server_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD
    )

def get_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )

def create_database():
    conn = server_connection()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    cur.close()
    conn.close()

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    statements = [
    """CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
        email VARCHAR(180) NOT NULL UNIQUE, phone VARCHAR(30),
        password_hash VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS admins (
        id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS categories (
        id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS foods (
        id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(160) NOT NULL,
        category_id INT, description TEXT, price DECIMAL(10,2) NOT NULL,
        image VARCHAR(255), is_available BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
    )""",
    """CREATE TABLE IF NOT EXISTS addresses (
        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
        label VARCHAR(50) DEFAULT 'Home', address TEXT NOT NULL,
        latitude DECIMAL(10,7), longitude DECIMAL(10,7),
        phone VARCHAR(30), is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS favorites (
        id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, food_id INT NOT NULL,
        UNIQUE KEY uq_favorite(user_id, food_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(food_id) REFERENCES foods(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS offers (
        id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(160) NOT NULL,
        coupon_code VARCHAR(60) UNIQUE, description TEXT,
        discount_type ENUM('percent','fixed') DEFAULT 'percent',
        discount_value DECIMAL(10,2) NOT NULL, min_order DECIMAL(10,2) DEFAULT 0,
        valid_from DATETIME NOT NULL, valid_until DATETIME NOT NULL,
        is_active BOOLEAN DEFAULT TRUE
    )""",
    """CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY, order_number VARCHAR(40) NOT NULL UNIQUE,
        user_id INT NOT NULL, address TEXT NOT NULL, phone VARCHAR(30),
        subtotal DECIMAL(10,2) NOT NULL, delivery_fee DECIMAL(10,2) DEFAULT 50,
        discount DECIMAL(10,2) DEFAULT 0, coupon_code VARCHAR(60),
        total_amount DECIMAL(10,2) NOT NULL,
        payment_method VARCHAR(40) NOT NULL DEFAULT 'Cash on Delivery',
        order_status VARCHAR(40) NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, food_id INT NOT NULL,
        food_name VARCHAR(160) NOT NULL, price DECIMAL(10,2) NOT NULL,
        quantity INT NOT NULL, line_total DECIMAL(10,2) NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY(food_id) REFERENCES foods(id)
    )""",
    """CREATE TABLE IF NOT EXISTS employees (
        id INT AUTO_INCREMENT PRIMARY KEY, employee_number VARCHAR(50) UNIQUE NOT NULL,
        full_name VARCHAR(160) NOT NULL, phone VARCHAR(30), email VARCHAR(180),
        date_of_birth DATE, nationality VARCHAR(100), designation VARCHAR(100),
        employment_status VARCHAR(50) DEFAULT 'Active', joining_date DATE,
        address TEXT, emergency_contact VARCHAR(100), emergency_phone VARCHAR(30),
        passport_number VARCHAR(80), passport_issue_date DATE, passport_expiry_date DATE,
        visa_number VARCHAR(80), visa_issue_date DATE, visa_expiry_date DATE,
        id_number VARCHAR(100), id_issue_date DATE, id_expiry_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS employee_documents (
        id INT AUTO_INCREMENT PRIMARY KEY, employee_id INT NOT NULL,
        document_type VARCHAR(60) NOT NULL, document_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL, expiry_date DATE, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )"""
    ]
    for sql in statements:
        cur.execute(sql)

    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        for name in ["Burgers", "Pizza", "Indian", "Chinese", "Japanese", "Arabic", "Mexican", "Desserts", "Drinks"]:
            cur.execute("INSERT INTO categories(name) VALUES(%s)", (name,))

    cur.execute("SELECT COUNT(*) FROM foods")
    if cur.fetchone()[0] == 0:
        samples = [
            ("Classic Chicken Burger","Burgers","Crispy chicken burger with fresh vegetables",249),
            ("Margherita Pizza","Pizza","Cheese, tomato and basil",299),
            ("Butter Chicken","Indian","Creamy Indian chicken curry",349),
            ("Chicken Biryani","Indian","Fragrant basmati rice and chicken",299),
            ("Chicken Sushi Roll","Japanese","Fresh sushi roll with chicken and vegetables",329),
            ("Chicken Shawarma","Arabic","Grilled chicken with garlic sauce",199),
            ("Tacos","Mexican","Three seasoned chicken tacos",229),
            ("Chocolate Brownie","Desserts","Warm chocolate brownie",149),
            ("Fresh Lime","Drinks","Refreshing lime drink",79)
        ]
        for name, cat, desc, price in samples:
            cur.execute("SELECT id FROM categories WHERE name=%s", (cat,))
            cid = cur.fetchone()[0]
            cur.execute("""INSERT INTO foods(name,category_id,description,price)
                           VALUES(%s,%s,%s,%s)""", (name,cid,desc,price))

    cur.execute("SELECT COUNT(*) FROM admins")
    if cur.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        cur.execute("INSERT INTO admins(username,password_hash) VALUES(%s,%s)",
                    ("admin", generate_password_hash("admin123")))

    conn.commit()
    cur.close()
    conn.close()
