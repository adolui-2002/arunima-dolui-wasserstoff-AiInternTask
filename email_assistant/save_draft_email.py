import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# Define the scopes for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def authenticate_gmail():
    """Authenticate and return the Gmail API service."""
    creds = None
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token_draft.json'):
        creds = Credentials.from_authorized_user_file('token_draft.json', SCOPES)
    # If no valid credentials, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token_draft.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def create_draft(service, user_id, subject, body, recipient):
    """Create and save a draft in Gmail."""
    try:
        # Create the email message
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Save the draft
        draft = service.users().drafts().create(
            userId=user_id,
            body={'message': {'raw': raw_message}}
        ).execute()

        print(f"Draft created with ID: {draft['id']}")
    except Exception as e:
        print(f"An error occurred: {e}")

def save_draft_if_needed( agenda, drafted_email, recipient):
    """
    Save the drafted email to Gmail's Drafts section if a reply is needed.

    Args:
        email_id: The ID of the email being processed.
        agenda: The subject or agenda of the email.
        drafted_email: The drafted email body.
        recipient: The recipient of the email.
    """
    # Authenticate and initialize the Gmail API service
    service = authenticate_gmail()

    # Save the draft
    create_draft(service, 'me', agenda, drafted_email, recipient)


