"""
Main module for the email assistant application.
"""

import logging
from email_assistant.config import settings
from email_assistant.models import db
from email_assistant.rag_setup import rag_model
import time
from datetime import datetime
from sqlalchemy.sql import text  # Import the text function
from .store_emails import store_emails , start_email_monitor




logging.basicConfig(
level=logging.INFO,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_stored_emails():
    """
    Process stored emails one by one, starting from the last stored email.
    """
    try:


        # Use the scoped session directly
        session = db  # Use the scoped_session object

        # Retrieve all stored email IDs from the database in descending order
        email_ids = session.execute(text("SELECT id FROM emails ORDER BY id DESC")).fetchall()

        # Process each email ID
        for email_id_tuple in email_ids:
            email_id = email_id_tuple[0]  # Extract the email ID from the tuple
            logger.info(f"Processing email with ID: {email_id}")
            try:
               rag_model(email_id)  # Send email_id to AIService
               time .sleep(60)  # Sleep for 1 second between processing emails
            except Exception as e:
                logger.error(f"Error processing email with ID {email_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in processing stored emails: {str(e)}")

def main():
    """Main function to run the email assistant."""
    store_emails()

    # Start the email monitor
    start_email_monitor()
    try:
        # Process emails
        while True:
            # Process stored emails from last to first
            process_stored_emails()

            # Sleep for 5 minutes before checking again
            time.sleep(300)
    except Exception as e:
        logger.error(f"Critical error in main loop: {str(e)}")

if __name__ == "__main__":


    # Run the main email assistant logic
    main()