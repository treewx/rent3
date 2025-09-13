import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from models import db, EmailLog

logger = logging.getLogger(__name__)

def send_email(recipient_email, subject, html_content, email_type="general"):
    """
    Send an email using Gmail SMTP
    """
    try:
        # Email configuration
        sender_email = os.getenv('EMAIL_SENDER')
        sender_password = os.getenv('EMAIL_PASSWORD')

        if not sender_email or not sender_password:
            logger.warning("Email credentials not configured. Email not sent.")
            if os.getenv('FLASK_ENV') == 'development':
                logger.info(f"DEV MODE: Would send email to {recipient_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Content: {html_content}")
                # Mark as sent in development
                log_email(recipient_email, subject, email_type, True)
                return True
            return False

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email

        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())

        logger.info(f"Email sent successfully to {recipient_email}")
        log_email(recipient_email, subject, email_type, True)
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        log_email(recipient_email, subject, email_type, False, str(e))
        return False

def log_email(recipient_email, subject, email_type, sent_successfully, error_message=None):
    """
    Log email sending attempt to database
    """
    try:
        email_log = EmailLog(
            recipient_email=recipient_email,
            subject=subject,
            email_type=email_type,
            sent_successfully=sent_successfully,
            error_message=error_message
        )
        db.session.add(email_log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log email: {str(e)}")

def send_email_verification(recipient_email, first_name, verification_url):
    """
    Send email verification email
    """
    subject = "Verify Your Email Address - Rent Tracker"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Rent Tracker!</h1>
            </div>
            <p>Hi {first_name},</p>
            <p>Thank you for signing up for Rent Tracker. To complete your registration, please verify your email address by clicking the button below:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            <p>This verification link will expire in 24 hours.</p>
            <p>If you didn't create an account with Rent Tracker, you can safely ignore this email.</p>
            <p>Best regards,<br>The Rent Tracker Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "email_verification")

def send_password_reset_email(recipient_email, first_name, reset_url):
    """
    Send password reset email
    """
    subject = "Reset Your Password - Rent Tracker"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <p>Hi {first_name},</p>
            <p>We received a request to reset your password for your Rent Tracker account. Click the button below to create a new password:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>This password reset link will expire in 24 hours.</p>
            <p>If you didn't request a password reset, you can safely ignore this email.</p>
            <p>Best regards,<br>The Rent Tracker Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "password_reset")

def send_rent_received_notification(recipient_email, property_address, tenant_name, amount, date):
    """
    Send notification when rent is received
    """
    subject = f"Rent Received - {property_address}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .success {{ background-color: #d4edda; color: #155724; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rent Payment Received</h1>
            </div>
            <div class="success">
                <h3>✅ Payment Confirmed</h3>
            </div>
            <p><strong>Property:</strong> {property_address}</p>
            <p><strong>Tenant:</strong> {tenant_name}</p>
            <p><strong>Amount:</strong> ${amount}</p>
            <p><strong>Date:</strong> {date}</p>
            <p>This rent payment has been automatically detected and verified in your bank account.</p>
            <p>Best regards,<br>The Rent Tracker Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "rent_received")

def send_rent_missed_notification(recipient_email, property_address, tenant_name, expected_amount, due_date):
    """
    Send notification when rent is missed
    """
    subject = f"Rent Payment Missed - {property_address}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .warning {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rent Payment Missed</h1>
            </div>
            <div class="warning">
                <h3>⚠️ Payment Not Received</h3>
            </div>
            <p><strong>Property:</strong> {property_address}</p>
            <p><strong>Tenant:</strong> {tenant_name}</p>
            <p><strong>Expected Amount:</strong> ${expected_amount}</p>
            <p><strong>Due Date:</strong> {due_date}</p>
            <p>No rent payment was detected for this property on the expected date. You may want to contact your tenant.</p>
            <p>Best regards,<br>The Rent Tracker Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "rent_missed")

def send_rent_amount_mismatch_notification(recipient_email, property_address, tenant_name, expected_amount, actual_amount, date):
    """
    Send notification when rent amount doesn't match expected
    """
    subject = f"Rent Amount Mismatch - {property_address}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .info {{ background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rent Amount Mismatch</h1>
            </div>
            <div class="info">
                <h3>ℹ️ Payment Amount Differs</h3>
            </div>
            <p><strong>Property:</strong> {property_address}</p>
            <p><strong>Tenant:</strong> {tenant_name}</p>
            <p><strong>Expected Amount:</strong> ${expected_amount}</p>
            <p><strong>Actual Amount:</strong> ${actual_amount}</p>
            <p><strong>Date:</strong> {date}</p>
            <p>A payment was received with the correct keyword but the amount differs from the expected rent amount. Please review this transaction.</p>
            <p>Best regards,<br>The Rent Tracker Team</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "rent_amount_mismatch")

def send_tenant_reminder_email(recipient_email, tenant_name, property_address, amount, landlord_name):
    """
    Send reminder email to tenant when rent is missed
    """
    subject = f"Rent Payment Reminder - {property_address}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .reminder {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rent Payment Reminder</h1>
            </div>
            <div class="reminder">
                <h3>📅 Rent Payment Due</h3>
            </div>
            <p>Hi {tenant_name},</p>
            <p>This is a friendly reminder that your rent payment was due and has not yet been received.</p>
            <p><strong>Property:</strong> {property_address}</p>
            <p><strong>Amount Due:</strong> ${amount}</p>
            <p>If you have already made the payment, please disregard this message. If you have any questions or concerns, please contact your landlord directly.</p>
            <p>Thank you,<br>{landlord_name}</p>
        </div>
    </body>
    </html>
    """

    return send_email(recipient_email, subject, html_content, "tenant_reminder")