"""
Script to read emails from Gmail and store them in the database.
"""
from email_assistant.models import Email
from email_assistant.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import logging
import re
from typing import Dict, Any
import time
import threading
from sqlalchemy.exc import IntegrityError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to track the last email ID
last_email_id = None

def connect_to_gmail():
    """Connect to Gmail using IMAP."""
    try:
        # Connect to Gmail's IMAP server
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        logger.info("✅ Successfully connected to Gmail")
        return imap
    except Exception as e:
        logger.error(f"❌ Failed to connect to Gmail: {str(e)}")
        return None

def analyze_email_content(subject: str, body: str) -> Dict[str, Any]:
    """
    Analyze email content to determine importance, intent, and generate summary.
    """
    # Initialize analysis results
    analysis = {
        'is_important': False,
        'priority': 'normal',
        'intent': None,
        'summary': None,  # Will be empty initially
        'no_response': False
    }

    # Check for importance indicators
    important_keywords = ['urgent', 'important', 'asap', 'critical', 'emergency']
    subject_lower = subject.lower()
    body_lower = body.lower()

    # Check for priority
    if any(keyword in subject_lower or keyword in body_lower for keyword in important_keywords):
        analysis['is_important'] = True
        analysis['priority'] = 'high'

    # Determine intent
    intent_patterns = {
        'meeting_request': r'(meeting|schedule|appointment|call)',
        'task_request': r'(task|todo|to-do|action item)',
        'question': r'\?',
        'feedback': r'(feedback|review|comment)',
        'report': r'(report|summary|update)'
    }

    for intent, pattern in intent_patterns.items():
        if re.search(pattern, subject_lower) or re.search(pattern, body_lower):
            analysis['intent'] = intent
            break

    # Check for no-response indicators
    no_response_keywords = ['no reply needed', 'no response required', 'for your information', 'fyi', 'notification']
    if any(keyword in subject_lower or keyword in body_lower for keyword in no_response_keywords):
        analysis['no_response'] = True

    return analysis

def parse_email_message(msg) -> Dict[str, Any]:
    """Parse email message and extract relevant information."""
    try:
        # Get email subject
        subject = decode_header(msg["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        # Get sender
        sender = decode_header(msg["from"])[0][0]
        if isinstance(sender, bytes):
            sender = sender.decode()

        # Get recipient
        recipient = decode_header(msg["to"])[0][0]
        if isinstance(recipient, bytes):
            recipient = recipient.decode()

        # Get message ID
        message_id = msg["message-id"]

        # Validate critical fields
        if not message_id or not sender or not subject:
            logger.warning(f"⚠️ Skipping email due to missing fields (Message ID: {message_id})")
            return None

        # Get thread ID (using references or in-reply-to)
        thread_id = msg.get("references", msg.get("in-reply-to", message_id))

        # Get timestamp
        date_str = msg["date"]
        try:
            timestamp = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        except:
            timestamp = datetime.now()

        # Get email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Analyze email content
        analysis = analyze_email_content(subject, body)

        # Combine all data
        email_data = {
            "thread_id": thread_id,
            "message_id": message_id,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "timestamp": timestamp,
            "body": body,
            "is_important": analysis['is_important'],
            "priority": analysis['priority'],
            "intent": analysis['intent'],
            "summary": analysis['summary'],
            "no_response": analysis['no_response'],
            "status": "unread"
        }

        return email_data
    except Exception as e:
        logger.error(f"❌ Error parsing email (Message ID: {msg.get('message-id', 'Unknown')}): {str(e)}")
        return None

def store_emails(num_emails=50):
    """Read emails from Gmail and store them in the database."""
    # Connect to Gmail
    imap = connect_to_gmail()
    if not imap:
        return

    try:
        # Select the inbox
        imap.select("INBOX")
        logger.info("✅ Selected INBOX")

        # Search for all emails
        _, message_numbers = imap.search(None, "ALL")
        email_list = message_numbers[0].split()

        # Get the most recent emails
        recent_emails = email_list[-num_emails:]
        logger.info(f"Found {len(recent_emails)} recent emails")

        # Create database session
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            stored_count = 0
            skipped_count = 0
            for num in recent_emails:
                # Fetch email message
                _, msg_data = imap.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)

                # Parse email
                email_data = parse_email_message(msg)
                if not email_data:
                    skipped_count += 1
                    continue

                # Check if email already exists
                existing = session.query(Email).filter_by(
                    message_id=email_data["message_id"]
                ).first()

                if not existing:
                    try:
                        # Create new email record
                        email_record = Email(**email_data)
                        session.add(email_record)
                        session.commit()
                        stored_count += 1
                        logger.info(f"✅ Stored email: {email_data['subject']} (Sender: {email_data['sender']})")
                    except IntegrityError:
                        session.rollback()
                        logger.warning(f"⚠️ Duplicate email detected during commit: {email_data['message_id']}")
                else:
                    skipped_count += 1
                    logger.info(f"⚠️ Skipping duplicate email: {email_data['subject']} (Message ID: {email_data['message_id']})")

            logger.info(f"✅ Successfully stored {stored_count} new emails, skipped {skipped_count} emails")

        except Exception as e:
            logger.error(f"❌ Error storing emails: {str(e)}")
            session.rollback()
        finally:
            session.close()

    except Exception as e:
        logger.error(f"❌ Error reading emails: {str(e)}")
    finally:
        imap.close()
        imap.logout()
        logger.info("✅ Closed Gmail connection")

def start_email_monitor(check_interval=300):
    """
    Start a background thread to monitor for new emails.

    Args:
        check_interval: Time in seconds between checks (default: 5 minutes)
    """
    def monitor_thread():
        logger.info(f"Starting email monitor (checking every {check_interval} seconds)")
        while True:
            store_emails()
            time.sleep(check_interval)

    # Start the monitor thread
    thread = threading.Thread(target=monitor_thread, daemon=True)
    thread.start()
    logger.info("✅ Email monitor started")
    return thread

