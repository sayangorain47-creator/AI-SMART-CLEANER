import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-smart-cleaner-dev-insecure-key-change-in-prod-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'smart_cleaner.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max request size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    UPLOAD_BEFORE_FOLDER = os.path.join(UPLOAD_FOLDER, 'before')
    UPLOAD_AFTER_FOLDER = os.path.join(UPLOAD_FOLDER, 'after')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB per image
    
    # Application Defaults
    DEFAULT_DEADLINE_HOURS = 12
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Rate Limiting Settings
    RATELIMIT_STORAGE_URI = "memory://"
    
    # Contact Info Defaults
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'support@aismartcleaner.org')
    CONTACT_PHONE = os.environ.get('CONTACT_PHONE', '+1 (800) 555-0199')
    MUNICIPAL_HELPLINE = os.environ.get('MUNICIPAL_HELPLINE', '1916')

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance', 'test_uploads')
    UPLOAD_BEFORE_FOLDER = os.path.join(UPLOAD_FOLDER, 'before')
    UPLOAD_AFTER_FOLDER = os.path.join(UPLOAD_FOLDER, 'after')
