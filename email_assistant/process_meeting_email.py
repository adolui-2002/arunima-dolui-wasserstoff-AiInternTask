"""
Script to process a specific email and create a calendar event from it.
"""
import re
import os
from datetime import datetime, timedelta
import pytz
from dateutil import parser
from email_assistant.calendar_service import CalendarService
from email_assistant.config import settings
import json
from email_assistant.slack_operations import SlackOperations

# Timezone setup
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

def parse_datetime_with_dateutil(text: str) -> datetime:
    """
    Extract and parse date and time from a given text using dateutil.parser.

    Args:
        text: The input text containing date and time information.

    Returns:
        A datetime object representing the parsed date and time.

    Raises:
        ValueError: If no valid date or time is found in the text.
    """
    # Regular expression to find potential date and time patterns
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # Matches dates like 12-31-2020 or 12/31/20
        r'\b\d{1,2} \w+ \d{2,4}\b',            # Matches dates like 31 December 2020
        r'\b\w+ \d{1,2}, \d{2,4}\b',           # Matches dates like December 31, 2020
        r'\b\d{1,2}:\d{2} ?[APap][mM]?\b',     # Matches times like 12:30 PM or 12:30pm
        r'\b\d{1,2}:\d{2}:\d{2} ?[APap][mM]?\b' # Matches times like 12:30:45 PM
    ]

    # Combine patterns into a single regex
    combined_pattern = '|'.join(date_patterns)

    # Find all matches in the text
    matches = re.findall(combined_pattern, text)

    # Parse and return the first valid date-time
    for match in matches:
        try:
            parsed_date = parser.parse(match)
            return parsed_date
        except ValueError:
            continue  # Skip if parsing fails

    # If no valid date-time is found, raise an error
    raise ValueError(f"No valid date or time found in the text: {text}")

def parse_datetime(date_str: str, time_str: str) -> datetime:
    """
    Parse date and time strings into a datetime object, handling specific formats and ignoring unnecessary characters.
    Supports relative days like "Friday at 3 PM".

    Args:
        date_str: The date string to parse (can include day names like "Friday").
        time_str: The time string to parse.

    Returns:
        A datetime object representing the parsed date and time.

    Raises:
        ValueError: If none of the formats match the input strings.
    """


    # Define possible date and time formats
    date_formats = [
        "%B %d, %Y",  # Example: "April 5, 2025"
        "%d %B %Y",   # Example: "5 April 2025"
        "%Y-%m-%d",   # Example: "2025-04-05"
        "%d/%m/%Y",   # Example: "05/04/2025"
        "%m/%d/%Y",   # Example: "04/05/2025"
        "%A",         # Example: "Friday"
        "%A, %B %d, %Y",  # Example: "Friday, April 5, 2025"
    ]

    time_formats = [
        "%I:%M %p",        # Example: "3:00 PM"
        "%H:%M",           # Example: "15:00"
        "%I:%M %p %Z",     # Example: "3:00 PM IST"
        "%I:%M %p (%Z)",   # Example: "3:00 PM (IST)"
    ]

    # Define relative days
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Clean the date and time strings by removing unnecessary characters
    date_str = re.sub(r"[\/\.,-:]", " ", date_str).strip().lower()
    time_str = re.sub(r"[\/\.,-:]", " ", time_str).strip().lower()

    # Handle relative days like "Friday"
    today = datetime.now()
    if date_str in weekdays:
        target_weekday = weekdays[date_str]
        current_weekday = today.weekday()
        days_until_target = (target_weekday - current_weekday) % 7
        parsed_date = today + timedelta(days=days_until_target)
    else:
        # Try parsing the date
        parsed_date = None
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                break
            except ValueError:
                continue

        if not parsed_date:
            raise ValueError(f"Date string '{date_str}' does not match any known formats.")

    # Try parsing the time
    parsed_time = None
    for time_format in time_formats:
        try:
            parsed_time = datetime.strptime(time_str, time_format).time()
            break
        except ValueError:
            continue

    if not parsed_time:
        raise ValueError(f"Time string '{time_str}' does not match any known formats.")

    # Combine date and time
    combined_datetime = datetime.combine(parsed_date.date(), parsed_time)

    return combined_datetime

def check_time_slot_availability(service, start_time, duration_hours=1):
    """
    Check if a specific time slot is available and propose alternatives if not.

    Args:
        service: The Google Calendar API service object.
        start_time: The proposed start time (datetime object).
        duration_hours: Duration of the meeting in hours.

    Returns:
        Tuple of (is_available, alternative_slots).
        is_available: Boolean indicating if the time slot is available.
        alternative_slots: List of alternative available time slots if the requested slot is not available.
    """
    try:
        if not service:
            raise Exception("Calendar service not initialized.")

        # Convert to UTC
        start_time_utc = start_time.astimezone(pytz.UTC)
        end_time_utc = start_time_utc + timedelta(hours=duration_hours)

        # Get events for the day
        events_result = service.events().list(
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
            if start_time_utc < event_end and end_time_utc > event_start:
                return False, []

        # If we get here, the time slot is available
        return True, []

    except Exception as e:
        print(f"Error checking time slot availability: {str(e)}")
        return False, []

def propose_meeting_times(self, date, duration_hours=1, num_options=3):
    """Propose available meeting times for a given date."""
    try:
        available_slots = self.find_available_times(date, duration_hours)
        return available_slots[:num_options]
    except Exception as e:
        print(f"Error proposing meeting times: {str(e)}")
        return []

def validate_email(email: str) -> bool:
    """
    Validate an email address using a regular expression.

    Args:
        email: The email address to validate.

    Returns:
        True if the email is valid, False otherwise.
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def process_meeting_email(meeting_details):
    """
    Process meeting details and create a calendar event if start_date and start_time are provided.
    Optional attributes like location, description, and end_time are handled gracefully.

    Args:
        meeting_details: A dictionary containing meeting details.

    Returns:
        A dictionary with the status of the event creation or alternative time slots if unavailable.
    """
    try:
        # Extract and clean meeting details
        summary = meeting_details.get("summary", "No Title Provided")
        location = meeting_details.get("location", "No Location Provided")
        description = meeting_details.get("description", "No Description Provided")
        start_date = meeting_details.get("start_date", "").strip()
        start_time = meeting_details.get("start_time", "").strip()
        end_date = meeting_details.get("end_date", "").strip()
        end_time = meeting_details.get("end_time", "").strip()
        attendees = meeting_details.get("attendees", "").split(",")
        sender_email = meeting_details.get("sender_email", "")

        # Parse start_date and start_time
        try:
            if start_date and start_time:
                start_datetime = parse_datetime_with_dateutil(f"{start_date} {start_time}")
            else:
                raise ValueError("Start date or time is missing or invalid.")
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Error parsing start date and time: {e}",
            }

        # Handle missing end_date and end_time
        try:
            if end_date and end_time:
                end_datetime = parse_datetime_with_dateutil(f"{end_date} {end_time}")
            else:
                end_datetime = start_datetime + timedelta(hours=1)  # Default to 1-hour duration
        except ValueError as e:
            end_datetime = start_datetime + timedelta(hours=1)  # Default to 1-hour duration

        # Parse attendees
        valid_attendees = []
        for attendee in attendees:
            attendee = attendee.strip()
            if validate_email(attendee):
                valid_attendees.append(attendee)

        # Fallback to sender's email if no valid attendees
        if not valid_attendees and validate_email(sender_email):
            valid_attendees = [sender_email]

        print("Initializing CalendarService...")
        # Initialize the CalendarService
        calendar_service = CalendarService()

        # Check if the time slot is available
        is_available, alternative_slots = calendar_service.check_time_slot_availability(
            start_datetime, (end_datetime - start_datetime).total_seconds() / 3600
        )

        if is_available:
            # Create the calendar event
            event_details = {
                "title": summary,
                "location": location,
                "description": description,
                "start_time": start_datetime,
                "end_time": end_datetime,
                "attendees": valid_attendees or ["No Attendees Provided"],
            }
            event_id = calendar_service.create_event(event_details)
            if event_id:
                print(f"✅ Event created successfully with ID: {event_id}")
                return {
                    "status": "success",
                    "message": f"Event created successfully with ID: {event_id}",
                    "event_id": event_id,
                    "summary": summary,
                }
            else:
                print("❌ Failed to create calendar event.")
                return {
                    "status": "error",
                    "message": "Failed to create calendar event.",
                }
        else:
            # Propose alternative time slots
            print("❌ The requested time slot is not available.")
            if alternative_slots:
                print("Here are some alternative available time slots:")
                for slot in alternative_slots:
                    start_time = slot["start"].astimezone(pytz.timezone("Asia/Kolkata"))
                    end_time = slot["end"].astimezone(pytz.timezone("Asia/Kolkata"))
                    print(f"  • {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
                return {
                    "status": "conflict",
                    "message": "The requested time slot is not available.",
                    "alternative_slots": alternative_slots,
                }
            else:
                print("No alternative time slots available for this day.")
                return {
                    "status": "conflict",
                    "message": "The requested time slot is not available, and no alternatives are available.",
                }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {e}",
        }

