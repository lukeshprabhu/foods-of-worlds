# FOODS OF WORLDS

A starter full-stack restaurant ordering and employee document management system using Flask + MySQL + HTML/CSS/JavaScript.

## 1. Requirements
- Python 3.10+
- MySQL Server
- MySQL username/password

## 2. Install
Open Command Prompt in this folder:

    py -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

## 3. Configure MySQL
Edit `config.py` if your MySQL password is not empty.

## 4. Start
    python app.py

Open:
    http://127.0.0.1:5000

## Admin
First-run default:
    Username: admin
    Password: admin123

Change the admin password in production.

## Customer
Register at `/register`, then login and order.

## Important
This is a functional starter package. Before production use, add CSRF protection, stronger validation, secure production secrets, HTTPS, payment gateway integration, image upload validation, backups, audit logs and production WSGI deployment.
