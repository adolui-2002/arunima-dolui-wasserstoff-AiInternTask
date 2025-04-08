"""
Slack operations for sending notifications and messages.
"""
import logging
from email_assistant.config import settings
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from email_assistant.models import Email, db
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SlackOperations:
    def __init__(self):
        """Initialize Slack client with bot token."""
        if not settings.SLACK_BOT_TOKEN:
            raise ValueError("Slack bot token not configured")

        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.channel = settings.SLACK_CHANNEL

        # Verify token and channel on initialization
        try:
            self.client.auth_test()
            logger.info("✅ Slack authentication successful")
        except SlackApiError as e:
            logger.error(f"❌ Slack authentication failed: {str(e)}")
            raise

    def send_message(self, message: str) -> bool:
        """
        Send a simple message to the configured Slack channel.

        Args:
            message: The message to send

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message
            )
            logger.info(f"✅ Message sent successfully: {message[:30]}...")
            return True
        except SlackApiError as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            if e.response['error'] == 'not_authed':
                logger.error("Please check your Slack bot token and permissions")
            elif e.response['error'] == 'channel_not_found':
                logger.error(f"Channel {self.channel} not found. Make sure the bot is invited to the channel")
            return False



    # def send_search_notification(self, results: list, query: str) -> bool:
    #     """
    #     Send search results to Slack.

    #     Args:
    #         results: List of search result dictionaries
    #         query: The search query used

    #     Returns:
    #         bool: True if successful, False otherwise
    #     """
    #     try:
    #         if not results:
    #             message = f"🔍 No results found for query: {query}"
    #         else:
    #             message = f"🔍 Search results for: {query}\n\n"
    #             for i, result in enumerate(results, 1):
    #                 message += f"{i}. *{result.get('title', 'No Title')}*\n"
    #                 message += f"   {result.get('snippet', 'No snippet available')}\n"
    #                 message += f"   <{result.get('link', '#')}|View Result>\n\n"

    #         response = self.client.chat_postMessage(
    #             channel=self.channel,
    #             text=message,
    #             parse="mrkdwn"
    #         )
    #         logger.info("✅ Search results sent successfully")
    #         return True
    #     except SlackApiError as e:
    #         logger.error(f"❌ Error sending search results: {str(e)}")
    #         if e.response['error'] == 'not_authed':
    #             logger.error("Please check your Slack bot token and permissions")
    #         elif e.response['error'] == 'channel_not_found':
    #             logger.error(f"Channel {self.channel} not found. Make sure the bot is invited to the channel")
    #         return False
    #     except Exception as e:
    #         logger.error(f"❌ Unexpected error: {str(e)}")
    #         return False

    # def send_event_details(self, event_details: dict) -> bool:
    #     """
    #     Send event details to Slack.

    #     Args:
    #         event_details (dict): Dictionary containing event details.

    #     Returns:
    #         bool: True if successful, False otherwise.
    #     """
    #     try:
    #         # Format the message
    #         message = (
    #             f"📅 *New Calendar Event Created*\n\n"
    #             f"*Title:* {event_details.get('title', 'No Title')}\n"
    #             f"*Start Time:* {event_details.get('start_time').strftime('%Y-%m-%d %H:%M')}\n"
    #             f"*End Time:* {event_details.get('end_time').strftime('%Y-%m-%d %H:%M')}\n"
    #             f"*Location:* {event_details.get('location', 'No Location')}\n"
    #             f"*Description:* {event_details.get('description', 'No Description')}\n"
    #             f"*Attendees:* {', '.join(event_details.get('attendees', []))}"
    #         )

    #         # Send the message to Slack
    #         return self.send_message(message)
    #     except Exception as e:
    #         logger.error(f"❌ Error sending event details to Slack: {str(e)}")
    #         return False