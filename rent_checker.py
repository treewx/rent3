from datetime import datetime, timedelta, date
import logging
import requests
from models import db, User, Property, RentCheck, AkahuCredentials
from email_service import send_rent_received_notification, send_rent_missed_notification, send_rent_amount_mismatch_notification, send_tenant_reminder_email
from decimal import Decimal

logger = logging.getLogger(__name__)

class RentChecker:
    def __init__(self):
        self.akahu_base_url = "https://api.akahu.nz/v1"

    def check_all_rent_payments(self):
        """
        Main function to check rent payments for all users
        Runs daily and checks previous day's transactions
        """
        logger.info("Starting daily rent payment check")

        # Get yesterday's date (the day we're checking for rent payments)
        yesterday = date.today() - timedelta(days=1)
        logger.info(f"Checking rent payments for {yesterday}")

        # Get all users who have Akahu credentials
        users_with_credentials = User.query.join(AkahuCredentials).all()

        for user in users_with_credentials:
            try:
                self.check_user_rent_payments(user, yesterday)
            except Exception as e:
                logger.error(f"Error checking rent for user {user.id}: {str(e)}")

    def check_user_rent_payments(self, user, check_date):
        """
        Check rent payments for a specific user on a specific date
        """
        logger.info(f"Checking rent payments for user {user.id} on {check_date}")

        # Get all properties for this user
        properties = Property.query.filter_by(user_id=user.id).all()

        for property in properties:
            try:
                # Check if rent was due on this date
                if self.is_rent_due(property, check_date):
                    logger.info(f"Rent due for property {property.id} on {check_date}")
                    self.check_property_rent_payment(user, property, check_date)
                else:
                    logger.debug(f"No rent due for property {property.id} on {check_date}")
            except Exception as e:
                logger.error(f"Error checking property {property.id}: {str(e)}")

    def is_rent_due(self, property, check_date):
        """
        Determine if rent is due for a property on a specific date
        """
        if property.rent_frequency == 'Weekly':
            # Check if the day of week matches
            return check_date.weekday() == property.rent_due_day_of_week

        elif property.rent_frequency == 'Fortnightly':
            # For fortnightly, we need to calculate based on a reference date
            # This is simplified - in practice you'd want to store a reference date
            return check_date.weekday() == property.rent_due_day_of_week and check_date.day % 14 == 0

        elif property.rent_frequency == 'Monthly':
            # Check if it's the right day of the month
            return check_date.day == property.rent_due_day

        return False

    def check_property_rent_payment(self, user, property, check_date):
        """
        Check if rent payment was received for a specific property on a specific date
        """
        # Check if we've already processed this property for this date
        existing_check = RentCheck.query.filter_by(
            property_id=property.id,
            check_date=check_date
        ).first()

        if existing_check:
            logger.info(f"Rent check already exists for property {property.id} on {check_date}")
            return

        # Get bank transactions for the check date
        transactions = self.get_bank_transactions(user, check_date)

        # Look for matching transactions
        rent_payment = self.find_rent_payment(transactions, property)

        # Create rent check record
        rent_check = RentCheck(
            property_id=property.id,
            check_date=check_date,
            rent_due_date=check_date,
            payment_found=rent_payment is not None
        )

        if rent_payment:
            rent_check.payment_amount = Decimal(str(abs(rent_payment['amount'])))
            rent_check.payment_keyword_match = True
            rent_check.amount_matches = abs(rent_payment['amount']) == float(property.rent_amount)

        db.session.add(rent_check)
        db.session.commit()

        # Send notifications
        self.send_notifications(user, property, rent_check, rent_payment)

    def get_bank_transactions(self, user, check_date):
        """
        Fetch bank transactions from Akahu for a specific date
        """
        try:
            credentials = user.akahu_credentials
            if not credentials:
                logger.error(f"No Akahu credentials for user {user.id}")
                return []

            headers = {
                'Authorization': f'Bearer {credentials.user_token}',
                'X-Akahu-ID': credentials.app_token
            }

            # Format date for API
            start_date = check_date.strftime('%Y-%m-%d')
            end_date = (check_date + timedelta(days=1)).strftime('%Y-%m-%d')

            url = f"{self.akahu_base_url}/transactions"
            params = {
                'start': start_date,
                'end': end_date
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            else:
                logger.error(f"Akahu API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            return []

    def find_rent_payment(self, transactions, property):
        """
        Find a transaction that matches the rent payment criteria
        """
        keyword = property.bank_statement_keyword.lower()

        for transaction in transactions:
            # Check if transaction description contains the keyword
            description = transaction.get('description', '').lower()

            if keyword in description:
                # This is a potential rent payment
                amount = abs(transaction.get('amount', 0))

                # Return the first matching transaction
                # In a more sophisticated system, you might want to handle multiple matches
                return transaction

        return None

    def send_notifications(self, user, property, rent_check, rent_payment):
        """
        Send appropriate notifications based on rent check results
        """
        try:
            if rent_check.payment_found:
                if rent_check.amount_matches:
                    # Rent received - correct amount
                    send_rent_received_notification(
                        user.email,
                        property.property_address,
                        property.tenant_name,
                        rent_check.payment_amount,
                        rent_check.check_date.strftime('%Y-%m-%d')
                    )
                    rent_check.notification_sent = True
                else:
                    # Rent received - wrong amount
                    send_rent_amount_mismatch_notification(
                        user.email,
                        property.property_address,
                        property.tenant_name,
                        property.rent_amount,
                        rent_check.payment_amount,
                        rent_check.check_date.strftime('%Y-%m-%d')
                    )
                    rent_check.notification_sent = True
            else:
                # No rent payment found
                send_rent_missed_notification(
                    user.email,
                    property.property_address,
                    property.tenant_name,
                    property.rent_amount,
                    rent_check.check_date.strftime('%Y-%m-%d')
                )
                rent_check.notification_sent = True

                # Send tenant reminder if enabled
                if property.send_tenant_reminder:
                    send_tenant_reminder_email(
                        property.tenant_email,
                        property.tenant_name,
                        property.property_address,
                        property.rent_amount,
                        f"{user.first_name} {user.last_name}"
                    )
                    rent_check.tenant_notification_sent = True

            db.session.commit()

        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")

def run_daily_rent_check():
    """
    Function to be called by the scheduler
    """
    try:
        checker = RentChecker()
        checker.check_all_rent_payments()
        logger.info("Daily rent check completed successfully")
    except Exception as e:
        logger.error(f"Daily rent check failed: {str(e)}")

# For manual testing
def run_rent_check_for_user(user_id, check_date=None):
    """
    Run rent check for a specific user (for testing)
    """
    if check_date is None:
        check_date = date.today() - timedelta(days=1)

    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return

    checker = RentChecker()
    checker.check_user_rent_payments(user, check_date)
    logger.info(f"Rent check completed for user {user_id}")

if __name__ == "__main__":
    # For testing purposes
    run_daily_rent_check()