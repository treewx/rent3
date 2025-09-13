from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DecimalField, BooleanField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError
from models import User
import re

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_password(self, password):
        """
        Validate password strength: 8+ chars, mixed case, numbers, symbols
        """
        password_value = password.data
        if not re.search(r'[A-Z]', password_value):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password_value):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', password_value):
            raise ValidationError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_value):
            raise ValidationError('Password must contain at least one special character.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

    def validate_password(self, password):
        """
        Validate password strength: 8+ chars, mixed case, numbers, symbols
        """
        password_value = password.data
        if not re.search(r'[A-Z]', password_value):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password_value):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', password_value):
            raise ValidationError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_value):
            raise ValidationError('Password must contain at least one special character.')

class AkahuCredentialsForm(FlaskForm):
    app_token = StringField('Akahu App Token', validators=[DataRequired()])
    user_token = StringField('Akahu User Token', validators=[DataRequired()])
    submit = SubmitField('Save Credentials')

class PropertyForm(FlaskForm):
    property_address = TextAreaField('Property Address', validators=[DataRequired()])
    tenant_name = StringField('Tenant Name', validators=[DataRequired(), Length(max=200)])
    tenant_email = StringField('Tenant Email', validators=[DataRequired(), Email()])
    rent_amount = DecimalField('Rent Amount ($)', validators=[DataRequired(), NumberRange(min=0)])
    rent_frequency = SelectField('Rent Frequency',
                                choices=[('Weekly', 'Weekly'), ('Fortnightly', 'Fortnightly'), ('Monthly', 'Monthly')],
                                validators=[DataRequired()])
    rent_due_day_of_week = SelectField('Rent Due Day of Week',
                                     choices=[('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
                                            ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')],
                                     coerce=int)
    rent_due_day = SelectField('Rent Due Day of Month',
                              choices=[(str(i), str(i)) for i in range(1, 32)],
                              coerce=int)
    bank_statement_keyword = StringField('Bank Statement Keyword', validators=[DataRequired(), Length(max=255)])
    send_tenant_reminder = BooleanField('Send email to tenant when rent is missed')
    submit = SubmitField('Save Property')

class TransactionSearchForm(FlaskForm):
    search_term = StringField('Search Term')
    submit = SubmitField('Search Transactions')