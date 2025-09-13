from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.Text)
    email_verification_expires = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_active = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255))
    subscription_id = db.Column(db.String(255))

    # Relationships
    properties = db.relationship('Property', backref='landlord', lazy=True, cascade='all, delete-orphan')
    akahu_credentials = db.relationship('AkahuCredentials', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', backref='user', lazy=True, cascade='all, delete-orphan')

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    setting_key = db.Column(db.Text, nullable=False)
    setting_value = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint('user_id', 'setting_key'),)

class AkahuCredentials(db.Model):
    __tablename__ = 'akahu_credentials'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    app_token = db.Column(db.Text, nullable=False)
    user_token = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_address = db.Column(db.Text, nullable=False)
    tenant_name = db.Column(db.String(200), nullable=False)
    tenant_email = db.Column(db.String(255), nullable=False)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    rent_frequency = db.Column(db.String(20), nullable=False)  # Weekly, Fortnightly, Monthly
    rent_due_day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday (for Weekly/Fortnightly)
    rent_due_day = db.Column(db.Integer)  # Day of month (for Monthly)
    bank_statement_keyword = db.Column(db.String(255), nullable=False)
    send_tenant_reminder = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rent_checks = db.relationship('RentCheck', backref='property', lazy=True, cascade='all, delete-orphan')

class RentCheck(db.Model):
    __tablename__ = 'rent_checks'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    check_date = db.Column(db.Date, nullable=False)
    rent_due_date = db.Column(db.Date, nullable=False)
    payment_found = db.Column(db.Boolean, default=False)
    payment_amount = db.Column(db.Numeric(10, 2))
    payment_keyword_match = db.Column(db.Boolean, default=False)
    amount_matches = db.Column(db.Boolean, default=False)
    notification_sent = db.Column(db.Boolean, default=False)
    tenant_notification_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmailLog(db.Model):
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    email_type = db.Column(db.String(50), nullable=False)  # verification, password_reset, rent_notification, etc.
    sent_successfully = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)