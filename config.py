import os

class Config:
    SECRET_KEY = os.environ.get("WOF_SECRET_KEY", "change-this-secret-key")
    MYSQL_HOST = os.environ.get("WOF_DB_HOST", "localhost")
    MYSQL_USER = os.environ.get("WOF_DB_USER", "root")
    MYSQL_PASSWORD = os.environ.get("WOF_DB_PASSWORD", "aniprabhu")
    MYSQL_DATABASE = os.environ.get("WOF_DB_NAME", "foods_of_worlds")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
