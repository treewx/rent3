from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from wtforms import StringField, PasswordField, SubmitField, SelectField, DecimalField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from email_validator import validate_email, EmailNotValidError
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import requests
import stripe
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from models import db, User, PasswordResetToken, UserSettings, AkahuCredentials, Property, RentCheck, EmailLog
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, AkahuCredentialsForm, PropertyForm, TransactionSearchForm
from email_service import send_email_verification, send_password_reset_email
from rent_checker import run_daily_rent_check

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///rent_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler for rent checking
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_daily_rent_check,
    trigger="cron",
    hour=9,  # Run at 9 AM every day
    minute=0,
    id='daily_rent_check'
)

# Start scheduler if not in debug mode or during testing
if not app.debug:
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Create new user
            user = User(
                email=form.email.data.lower(),
                password_hash=generate_password_hash(form.password.data),
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email_verification_token=secrets.token_urlsafe(32),
                email_verification_expires=datetime.utcnow() + timedelta(hours=24)
            )

            db.session.add(user)
            db.session.commit()

            # Send verification email
            verification_url = url_for('verify_email', token=user.email_verification_token, _external=True)
            if send_email_verification(user.email, user.first_name, verification_url):
                flash('Registration successful! Please check your email to verify your account.', 'success')
            else:
                flash('Registration successful! However, we could not send the verification email. Please contact support.', 'warning')

            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.email_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html', form=form)

            user.last_login = datetime.utcnow()
            db.session.commit()

            login_user(user, remember=True)
            flash('Logged in successfully!', 'success')

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/verify_email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        flash('Invalid verification token.', 'error')
        return redirect(url_for('login'))

    if user.email_verification_expires and user.email_verification_expires < datetime.utcnow():
        flash('Verification token has expired. Please request a new one.', 'error')
        return redirect(url_for('resend_verification'))

    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.session.commit()

    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('login'))

@app.route('/resend_verification', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def resend_verification():
    form = ForgotPasswordForm()  # Reuse the email form

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and not user.email_verified:
            # Generate new verification token
            user.email_verification_token = secrets.token_urlsafe(32)
            user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
            db.session.commit()

            # Send verification email
            verification_url = url_for('verify_email', token=user.email_verification_token, _external=True)
            if send_email_verification(user.email, user.first_name, verification_url):
                flash('Verification email sent! Please check your inbox.', 'success')
            else:
                flash('Could not send verification email. Please try again later.', 'error')

        else:
            # Don't reveal if email exists or is already verified
            flash('If that email address exists and is not verified, a verification email has been sent.', 'info')

        return redirect(url_for('login'))

    return render_template('resend_verification.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user:
            # Create password reset token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.add(reset_token)
            db.session.commit()

            # Send password reset email
            reset_url = url_for('reset_password', token=reset_token.token, _external=True)
            send_password_reset_email(user.email, user.first_name, reset_url)

        # Always show the same message for security
        flash('If that email address exists, a password reset link has been sent.', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()

    if not reset_token or reset_token.expires_at < datetime.utcnow():
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user = User.query.get(reset_token.user_id)
        user.password_hash = generate_password_hash(form.password.data)

        reset_token.used = True
        db.session.commit()

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    properties = Property.query.filter_by(user_id=current_user.id).all()
    property_count = len(properties)
    can_add_property = current_user.subscription_active or property_count == 0

    return render_template('dashboard.html',
                         properties=properties,
                         property_count=property_count,
                         can_add_property=can_add_property)

@app.route('/akahu_setup', methods=['GET', 'POST'])
@login_required
def akahu_setup():
    form = AkahuCredentialsForm()

    if current_user.akahu_credentials:
        form.app_token.data = current_user.akahu_credentials.app_token
        form.user_token.data = current_user.akahu_credentials.user_token

    if form.validate_on_submit():
        try:
            if current_user.akahu_credentials:
                # Update existing credentials
                current_user.akahu_credentials.app_token = form.app_token.data
                current_user.akahu_credentials.user_token = form.user_token.data
                current_user.akahu_credentials.updated_at = datetime.utcnow()
            else:
                # Create new credentials
                credentials = AkahuCredentials(
                    user_id=current_user.id,
                    app_token=form.app_token.data,
                    user_token=form.user_token.data
                )
                db.session.add(credentials)

            db.session.commit()
            flash('Akahu credentials saved successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Akahu credentials error: {str(e)}")
            flash('An error occurred while saving credentials. Please try again.', 'error')

    return render_template('akahu_setup.html', form=form)

@app.route('/add_property', methods=['GET', 'POST'])
@login_required
def add_property():
    # Check if user can add property
    property_count = Property.query.filter_by(user_id=current_user.id).count()
    if not current_user.subscription_active and property_count >= 1:
        flash('You need to upgrade your account to add more properties.', 'warning')
        return redirect(url_for('upgrade_subscription'))

    form = PropertyForm()

    if form.validate_on_submit():
        try:
            property = Property(
                user_id=current_user.id,
                property_address=form.property_address.data,
                tenant_name=form.tenant_name.data,
                tenant_email=form.tenant_email.data,
                rent_amount=form.rent_amount.data,
                rent_frequency=form.rent_frequency.data,
                rent_due_day_of_week=form.rent_due_day_of_week.data if form.rent_frequency.data in ['Weekly', 'Fortnightly'] else None,
                rent_due_day=form.rent_due_day.data if form.rent_frequency.data == 'Monthly' else None,
                bank_statement_keyword=form.bank_statement_keyword.data,
                send_tenant_reminder=form.send_tenant_reminder.data
            )

            db.session.add(property)
            db.session.commit()

            flash('Property added successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Add property error: {str(e)}")
            flash('An error occurred while adding the property. Please try again.', 'error')

    return render_template('add_property.html', form=form)

@app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    property = Property.query.filter_by(id=property_id, user_id=current_user.id).first_or_404()
    form = PropertyForm(obj=property)

    if form.validate_on_submit():
        try:
            form.populate_obj(property)
            property.updated_at = datetime.utcnow()

            # Set correct due day fields based on frequency
            if property.rent_frequency in ['Weekly', 'Fortnightly']:
                property.rent_due_day = None
            else:  # Monthly
                property.rent_due_day_of_week = None

            db.session.commit()
            flash('Property updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Edit property error: {str(e)}")
            flash('An error occurred while updating the property. Please try again.', 'error')

    return render_template('edit_property.html', form=form, property=property)

@app.route('/delete_property/<int:property_id>')
@login_required
def delete_property(property_id):
    property = Property.query.filter_by(id=property_id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(property)
        db.session.commit()
        flash('Property deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete property error: {str(e)}")
        flash('An error occurred while deleting the property. Please try again.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/upgrade_subscription')
@login_required
def upgrade_subscription():
    return render_template('upgrade_subscription.html')

@app.route('/search_transactions')
@login_required
def search_transactions():
    # This will be implemented to search Akahu transactions
    # For now, return a placeholder
    return jsonify({"message": "Transaction search not yet implemented"})

@app.route('/create_checkout_session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        # Create Stripe customer if doesn't exist
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=f"{current_user.first_name} {current_user.last_name}"
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'nzd',
                    'recurring': {
                        'interval': 'month',
                    },
                    'product_data': {
                        'name': 'Rent Tracker Premium',
                        'description': 'Unlimited properties and advanced features',
                    },
                    'unit_amount': 1000,  # $10.00 NZD in cents
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('subscription_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('upgrade_subscription', _external=True),
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}")
        flash('An error occurred while setting up payment. Please try again.', 'error')
        return redirect(url_for('upgrade_subscription'))

@app.route('/subscription_success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')

    if session_id:
        try:
            # Retrieve the session
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                # Update user subscription status
                current_user.subscription_active = True
                current_user.subscription_id = session.subscription
                db.session.commit()

                flash('Subscription activated successfully! You can now add unlimited properties.', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"Stripe session retrieval error: {str(e)}")

    flash('There was an issue with your subscription. Please contact support.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/manage_subscription')
@login_required
def manage_subscription():
    if not current_user.subscription_active:
        flash('You do not have an active subscription.', 'info')
        return redirect(url_for('upgrade_subscription'))

    try:
        # Create a billing portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for('dashboard', _external=True),
        )

        return redirect(portal_session.url, code=303)

    except Exception as e:
        logger.error(f"Stripe portal error: {str(e)}")
        flash('Unable to access billing portal. Please contact support.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Find user by subscription ID and deactivate
        user = User.query.filter_by(subscription_id=subscription['id']).first()
        if user:
            user.subscription_active = False
            user.subscription_id = None
            db.session.commit()
            logger.info(f"Deactivated subscription for user {user.id}")

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        user = User.query.filter_by(subscription_id=subscription['id']).first()
        if user:
            # Update subscription status based on current state
            user.subscription_active = subscription['status'] == 'active'
            db.session.commit()
            logger.info(f"Updated subscription status for user {user.id}: {subscription['status']}")

    return 'Success', 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)