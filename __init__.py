import os
from datetime import datetime, timezone
from flask import Flask, render_template, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from app.models import db, User, Notification, AppSetting

login_manager = LoginManager()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_BEFORE_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_AFTER_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please sign in to access this portal."
    login_manager.login_message_category = "warning"

    # Register Blueprints
    from app.public import public_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.worker import worker_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(worker_bp)

    # Context processors for global template variables
    @app.context_processor
    def inject_global_data():
        unread_count = 0
        user_notifications = []
        if current_user.is_authenticated:
            user_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                .order_by(Notification.created_at.desc()).limit(5).all()
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

        contact_email = AppSetting.get_value('contact_email', app.config.get('CONTACT_EMAIL'))
        contact_phone = AppSetting.get_value('contact_phone', app.config.get('CONTACT_PHONE'))
        emergency_helpline = AppSetting.get_value('emergency_helpline', app.config.get('MUNICIPAL_HELPLINE'))

        return {
            'current_year': datetime.now(timezone.utc).year,
            'unread_notifications_count': unread_count,
            'recent_notifications': user_notifications,
            'app_contact_email': contact_email,
            'app_contact_phone': contact_phone,
            'app_emergency_helpline': emergency_helpline
        }

    # Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
