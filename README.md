# Rent Tracker

A web-based application that automatically tracks rent payments from bank accounts and notifies landlords when payments are received or missed.

## Features

- **User Authentication**: Secure registration with email verification and password reset
- **Bank Integration**: Connect to your bank account via Akahu API
- **Property Management**: Add and manage multiple rental properties
- **Automated Rent Tracking**: Daily checks for rent payments in bank transactions
- **Email Notifications**: Automatic alerts for received, missed, or mismatched payments
- **Tenant Reminders**: Optional automated reminder emails to tenants
- **Subscription System**: Stripe-powered premium subscriptions for unlimited properties

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Authentication**: Flask-Login with email verification
- **Payments**: Stripe for subscription management
- **Bank Integration**: Akahu API for NZ banks
- **Email**: Gmail SMTP
- **Frontend**: Bootstrap 5 with responsive design
- **Task Scheduling**: APScheduler for daily rent checks

## Setup Instructions

### 1. Clone and Install

```bash
git clone <repository-url>
cd rent3
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Database
DATABASE_URL=sqlite:///rent_tracker.db

# Flask
SECRET_KEY=your-secret-key-here

# Email Configuration (Gmail)
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# Development
FLASK_ENV=development
```

### 3. Email Setup (Gmail)

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this password in `EMAIL_PASSWORD`

### 4. Stripe Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Set up a webhook endpoint pointing to `/stripe_webhook`
4. Configure webhook to listen for:
   - `customer.subscription.deleted`
   - `customer.subscription.updated`

### 5. Akahu Setup

1. Visit https://developers.akahu.nz/
2. Create a developer account
3. Create an application to get App Token
4. Generate User Tokens for bank access
5. Users will enter these tokens in the app

### 6. Database Initialization

```bash
python app.py
```

The database will be created automatically on first run.

### 7. Running the Application

**Development:**
```bash
python app.py
```

**Production (example with Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Usage

### For Landlords

1. **Register Account**: Sign up with email verification
2. **Connect Bank**: Enter Akahu credentials in Bank Setup
3. **Add Properties**:
   - Enter property details
   - Set rent amount and frequency
   - Define bank statement keyword for identification
   - Optionally enable tenant reminders
4. **Monitor**: Receive daily email notifications about rent status

### Property Configuration

- **Rent Frequency**: Weekly, Fortnightly, or Monthly
- **Due Dates**: Specific days of week/month
- **Bank Keywords**: Text to identify rent payments in statements
- **Tenant Reminders**: Automated emails to tenants for missed payments

### Subscription Plans

- **Free**: 1 property, basic notifications
- **Premium ($10/month)**: Unlimited properties, tenant reminders, priority support

## System Architecture

### Daily Rent Checking Process

1. **Scheduler**: Runs at 9 AM daily (configurable)
2. **Property Check**: Determines which properties have rent due
3. **Bank Integration**: Fetches previous day's transactions via Akahu
4. **Payment Matching**: Searches for transactions matching keywords/amounts
5. **Notifications**: Sends appropriate emails to landlords and tenants

### Email Notifications

- **Rent Received**: Confirmation with amount and date
- **Rent Missed**: Alert with expected amount and due date
- **Amount Mismatch**: Notification when payment amount differs
- **Tenant Reminders**: Automated reminders for missed payments

## File Structure

```
rent3/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── forms.py               # WTForms form definitions
├── email_service.py       # Email sending functionality
├── rent_checker.py        # Rent payment checking logic
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── add_property.html
│   ├── edit_property.html
│   ├── akahu_setup.html
│   └── upgrade_subscription.html
└── README.md
```

## Security Features

- **Password Security**: Strong password requirements with hashing
- **Email Verification**: Required before account activation
- **Rate Limiting**: Protection against brute force attacks
- **CSRF Protection**: Secure form submissions
- **Secure Tokens**: Cryptographically secure token generation
- **Input Validation**: Comprehensive form validation

## Deployment Considerations

### Production Environment

1. **Database**: Upgrade to PostgreSQL for production
2. **Email Service**: Consider using dedicated email service (SendGrid, Mailgun)
3. **Monitoring**: Implement logging and error tracking
4. **SSL/HTTPS**: Required for Stripe integration
5. **Environment Variables**: Use proper secrets management
6. **Backup Strategy**: Regular database backups

### Scaling

- Use Redis for session storage and caching
- Implement database connection pooling
- Consider containerization with Docker
- Set up load balancing for high availability

## API Integration

### Akahu API

The application integrates with Akahu's banking API for New Zealand banks:
- Transaction fetching
- Account balance queries (future feature)
- Real-time webhook support (future feature)

### Stripe API

Handles subscription management:
- Checkout sessions
- Customer creation
- Subscription lifecycle
- Webhook event handling

## Development

### Adding New Features

1. **Database Changes**: Update models.py and run migrations
2. **Forms**: Add new forms in forms.py
3. **Routes**: Implement new endpoints in app.py
4. **Templates**: Create corresponding HTML templates
5. **Tests**: Add appropriate test coverage

### Testing

```bash
# Run rent checker manually for testing
python rent_checker.py

# Test specific user
python -c "from rent_checker import run_rent_check_for_user; run_rent_check_for_user(1)"
```

## Support

For issues or questions:
1. Check the application logs
2. Verify environment configuration
3. Test email and Stripe connectivity
4. Review Akahu API documentation

## License

This project is proprietary software. All rights reserved.