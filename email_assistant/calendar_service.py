"""
Google Calendar integration for meeting scheduling.
"""
import os
import pickle
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email_assistant.config import settings
import re
from typing import Dict, List, Optional, Tuple
import json
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalendarService:
    """Service for handling Google Calendar operations."""



    def __init__(self):
        self.service = self._get_calendar_service()

    def _get_calendar_service(self):
        """Initialize the Calendar API service."""
        try:
            creds = None
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists(settings.GOOGLE_TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(settings.GOOGLE_TOKEN_FILE, settings.GOOGLE_CALENDAR_SCOPES)

            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GOOGLE_CREDENTIALS_FILE, settings.GOOGLE_CALENDAR_SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(settings.GOOGLE_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())

            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"❌ Error initializing calendar service: {str(e)}")
            return None

    def detect_meeting_request(self, email_content: str) -> Optional[Dict]:
        """
        Detect if an email contains a meeting request and extract meeting details.

        Args:
            email_content: The content of the email to analyze

        Returns:
            Dictionary containing meeting details if found, None otherwise
        """
        try:
            # Common meeting-related phrases
            meeting_phrases = [
                r'(?i)meeting\s+(?:on|at|for)',
                r'(?i)schedule\s+(?:a\s+)?meeting',
                r'(?i)let\'s\s+meet',
                r'(?i)would\s+you\s+like\s+to\s+meet',
                r'(?i)propose\s+a\s+time',
                r'(?i)set\s+up\s+a\s+call',
                r'(?i)arrange\s+a\s+meeting'
            ]

            # Check if email contains meeting-related phrases
            if not any(re.search(phrase, email_content) for phrase in meeting_phrases):
                return None

            # Extract date and time
            date_patterns = [
                r'(?i)(?:on\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
                r'(?i)(?:on\s+)?\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)',
                r'(?i)(?:on\s+)?\d{1,2}/\d{1,2}/\d{2,4}',
                r'(?i)(?:on\s+)?\d{1,2}-\d{1,2}-\d{2,4}'
            ]

            time_patterns = [
                r'(?i)\d{1,2}(?::\d{2})?\s*(?:am|pm)',
                r'(?i)\d{1,2}(?::\d{2})?\s*(?:in\s+the\s+)?(?:morning|afternoon|evening)',
                r'(?i)\d{1,2}(?::\d{2})?\s*(?:o\'clock)?'
            ]

            # Extract date and time
            date_match = None
            time_match = None

            for pattern in date_patterns:
                match = re.search(pattern, email_content)
                if match:
                    date_match = match.group()
                    break

            for pattern in time_patterns:
                match = re.search(pattern, email_content)
                if match:
                    time_match = match.group()
                    break

            # Extract title (use subject or first line of content)
            title = email_content.split('\n')[0][:100]  # Limit title length

            # Extract attendees (look for email addresses)
            attendees = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', email_content)

            # Extract duration (default to 1 hour if not specified)
            duration_match = re.search(r'(?i)(\d+)\s*(?:hour|hr)s?', email_content)
            duration = int(duration_match.group(1)) if duration_match else 1

            return {
                'title': title,
                'date': date_match,
                'time': time_match,
                'duration': duration,
                'attendees': attendees
            }

        except Exception as e:
            logger.error(f"❌ Error detecting meeting request: {str(e)}")
            return None

    def create_event(self, event_details):
        """Create a calendar event."""
        try:
            if not self.service:
                raise Exception("Calendar service not initialized")

            # Convert string date/time to datetime if needed
            start_time = event_details['start_time']
            if isinstance(start_time, str):
                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')

            end_time = event_details.get('end_time')
            if not end_time:
                end_time = start_time + timedelta(hours=1)
            elif isinstance(end_time, str):
                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

            event = {
                'summary': event_details['title'],
                'location': event_details.get('location', ''),
                'description': event_details.get('description', ''),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in event_details.get('attendees', [])],
                'reminders': {
                    'useDefault': True
                },
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"✅ Event created: {event.get('htmlLink')}")
            return event['id']

        except Exception as e:
            logger.error(f"❌ Error creating calendar event: {str(e)}")
            return None

    def get_available_slots(self, duration_minutes: int = 60, days_ahead: int = 7) -> List[Dict]:
        """
        Get available time slots for scheduling.

        Args:
            duration_minutes: Duration of the meeting in minutes
            days_ahead: Number of days to look ahead for availability

        Returns:
            List of available time slots
        """
        try:
            now = datetime.utcnow()
            end_time = now + timedelta(days=days_ahead)

            # Get busy slots
            freebusy_query = {
                "timeMin": now.isoformat() + 'Z',
                "timeMax": end_time.isoformat() + 'Z',
                "timeZone": 'UTC',
                "items": [{"id": "primary"}]
            }

            freebusy = self.service.freebusy().query(body=freebusy_query).execute()
            busy_slots = freebusy['calendars']['primary']['busy']

            # Generate available slots
            available_slots = []
            current_time = now

            while current_time < end_time:
                slot_end = current_time + timedelta(minutes=duration_minutes)

                # Check if the slot overlaps with any busy times
                is_available = True
                for busy in busy_slots:
                    busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                    busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))

                    if (current_time < busy_end and slot_end > busy_start):
                        is_available = False
                        current_time = busy_end
                        break

                if is_available:
                    available_slots.append({
                        'start': current_time,
                        'end': slot_end
                    })
                    current_time = slot_end
                else:
                    current_time = slot_end

            return available_slots

        except Exception as e:
            logger.error(f"❌ Error getting available slots: {str(e)}")
            return []

    def propose_times(self, meeting_details: Dict) -> List[Dict]:
        """
        Propose available meeting times based on the meeting details.

        Args:
            meeting_details: Dictionary containing meeting preferences
                {
                    'duration_minutes': int,
                    'preferred_days': List[str],
                    'preferred_times': List[str]
                }

        Returns:
            List of proposed time slots
        """
        try:
            available_slots = self.get_available_slots(
                duration_minutes=meeting_details.get('duration_minutes', 60)
            )

            # Filter slots based on preferences
            preferred_slots = []
            for slot in available_slots:
                day = slot['start'].strftime('%A')
                time = slot['start'].strftime('%H:%M')

                if (day in meeting_details.get('preferred_days', []) and
                    time in meeting_details.get('preferred_times', [])):
                    preferred_slots.append(slot)

            return preferred_slots

        except Exception as e:
            logger.error(f"❌ Error proposing times: {str(e)}")
            return []

    def find_available_times(self, date, duration_hours=1, working_hours=(9, 17)):
        """Find available time slots for a given date."""
        try:
            if not self.service:
                raise Exception("Calendar service not initialized")

            # Set time boundaries for the search
            start_time = datetime.combine(date, datetime.min.time().replace(hour=working_hours[0]))
            end_time = datetime.combine(date, datetime.min.time().replace(hour=working_hours[1]))

            # Convert to UTC for Google Calendar API
            start_time_utc = start_time.astimezone(pytz.UTC)
            end_time_utc = end_time.astimezone(pytz.UTC)

            # Get existing events for the day
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time_utc.isoformat(),
                timeMax=end_time_utc.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            # Find available slots
            available_slots = []
            current_time = start_time_utc

            for event in events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date'))).astimezone(pytz.UTC)
                event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date'))).astimezone(pytz.UTC)

                # Check if there's enough time before this event
                if (event_start - current_time).total_seconds() >= duration_hours * 3600:
                    available_slots.append({
                        'start': current_time,
                        'end': current_time + timedelta(hours=duration_hours)
                    })
                current_time = event_end

            # Add final slot if there's enough time
            if (end_time_utc - current_time).total_seconds() >= duration_hours * 3600:
                available_slots.append({
                    'start': current_time,
                    'end': current_time + timedelta(hours=duration_hours)
                })

            return available_slots

        except Exception as e:
            logger.error(f"❌ Error finding available times: {str(e)}")
            return []

    def check_time_slot_availability(self, start_time, duration_hours=1):
        """
        Check if a specific time slot is available and propose alternatives if not.

        Args:
            start_time: The proposed start time (datetime object)
            duration_hours: Duration of the meeting in hours

        Returns:
            Tuple of (is_available, alternative_slots)
            is_available: Boolean indicating if the time slot is available
            alternative_slots: List of alternative available time slots if the requested slot is not available
        """
        try:
            if not self.service:
                raise Exception("Calendar service not initialized")

            # Convert to UTC
            start_time_utc = start_time.astimezone(pytz.UTC)
            end_time_utc = start_time_utc + timedelta(hours=duration_hours)

            # Get events for the day
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time_utc.isoformat(),
                timeMax=end_time_utc.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            # Check for conflicts
            for event in events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date'))).astimezone(pytz.UTC)
                event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date'))).astimezone(pytz.UTC)

                # Check if there's any overlap
                if (start_time_utc < event_end and end_time_utc > event_start):
                    # Time slot is not available, get alternative slots
                    alternative_slots = self.find_available_times(
                        start_time_utc.date(),
                        duration_hours
                    )
                    return False, alternative_slots

            # If we get here, the time slot is available
            return True, []

        except Exception as e:
            logger.error(f"❌ Error checking time slot availability: {str(e)}")
            return False, []

    def propose_meeting_times(self, date, duration_hours=1, num_options=3):
        """Propose available meeting times for a given date."""
        try:
            available_slots = self.find_available_times(date, duration_hours)
            return available_slots[:num_options]
        except Exception as e:
            logger.error(f"❌ Error proposing meeting times: {str(e)}")
            return []