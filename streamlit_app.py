import streamlit as st
from email_assistant.rag_setup import chat_model,extract_meeting_details,chatbot_interaction
from email_assistant.models import db
from sqlalchemy.sql import text
from email_assistant.store_emails import store_emails,start_email_monitor
from email_assistant.slack_operations import SlackOperations

from email_assistant.save_draft_email import save_draft_if_needed
from email_assistant.web_search_service import WebSearchService
# from email_assistant.process_meeting_email import process_email_to_calendar
# from .store_emails import store_emails , start_email_monitor

# Initialize AI Service


# Streamlit App Title
st.title("AI-Powered Email Assistant")

# Sidebar Navigation
st.sidebar.title("Navigation")
options = st.sidebar.radio(
    "Go to",
    [
        "Home",
        "Fetch Emails",
        "View Emails",
        "Summarize Email",
        "Draft Reply",
        "Web Search",
        "Slack Integration",
        "Schedule Meeting",
        "Chat with Chatbot",
    ],
)

# Home Page
if options == "Home":
    st.header("Welcome to the AI-Powered Email Assistant!")
    st.write(
        """
        This application helps you manage your emails efficiently by:
        - Fetching and storing emails.
        - Summarizing email content.
        - Drafting replies.
        - Scheduling meetings.
        - Forwarding important emails to Slack.
        - Performing web searches for unanswered questions.
        """
    )

# Fetch Emails
elif options == "Fetch Emails":
    st.header("Fetch Emails from Gmail")
    if st.button("Fetch Emails"):
        try:
            st.write("Fetching emails...")
            store_emails()
            st.success("Emails fetched and stored successfully!")
        except Exception as e:
            st.error(f"Error fetching emails: {str(e)}")

# View Emails
elif options == "View Emails":
    st.header("View Stored Emails")
    try:
        session = db()  # Use the scoped session
        emails = session.execute(text("SELECT id, sender, subject, timestamp FROM emails")).fetchall()
        if emails:
            for email in emails:
                st.write(f"**Email ID:** {email[0]}")
                st.write(f"**Sender:** {email[1]}")
                st.write(f"**Subject:** {email[2]}")
                st.write(f"**Timestamp:** {email[3]}")
                st.write("---")
        else:
            st.warning("No emails found in the database.")
    except Exception as e:
        st.error(f"Error retrieving emails: {str(e)}")

# Summarize Email
elif options == "Summarize Email":
    st.header("Summarize Email")
    email_id = st.number_input("Enter Email ID to Summarize", min_value=1, step=1)
    if st.button("Summarize Email"):
        try:
            session = db()  # Use the scoped session
            email_data = session.execute(text(f"SELECT body FROM emails WHERE id = {email_id}")).fetchone()
            if email_data:

                summary = chat_model(email_id,"Summarize the email content")
                st.write("### Email Summary")
                st.write(summary)
            else:
                st.warning(f"No email found with ID {email_id}.")
        except Exception as e:
            st.error(f"Error summarizing email: {str(e)}")

# Draft Reply
elif options == "Draft Reply":
    st.header("Draft Reply to an Email")
    email_id = st.number_input("Enter Email ID to Draft Reply", min_value=1, step=1)
    if st.button("Draft Reply"):
        try:
            session = db()  # Use the scoped session
            email_data,sender = session.execute(text(f"SELECT body, sender FROM emails WHERE id = {email_id}")).fetchone()

            if email_data:

                draft = chat_model(email_id,"Draft a reply of the email or acknowledgement of the mail to the email to the sender. Understand the email context, what type of reply is sender asking for or what type of reply needed.Draft mail by adressing sender name in original as receipent of drafted reply mail.")
                st.write("### Drafted Reply")
                st.text_area("Drafted Email", value=draft, height=200)
                save_draft_if_needed("Reply to your email", draft, sender)
                st.success("Draft saved to Gmail successfully!")
            else:
                st.warning(f"No email found with ID {email_id}.")
        except Exception as e:
            st.error(f"Error drafting reply: {str(e)}")

# Web Search
elif options == "Web Search":
    st.header("Perform Web Search Based on Email Content")
    email_id = st.number_input("Enter Email ID to Analyze for Web Search", min_value=1, step=1)
    if st.button("Analyze and Search"):
        try:
            # Retrieve email content from the database
            session = db()  # Use the scoped session
            email_data = session.execute(text(f"SELECT body FROM emails WHERE id = {email_id}")).fetchone()

            if email_data:
                email_body = email_data[0]

                # Use chat_model to determine if a web search is needed
                st.write("Analyzing email content to determine if a web search is required...")
                search_needed = chat_model(email_id, "Does this email include a question or request for information that is not provided in the email itself, and would require searching the web to answer? or Does this email include a question or request for information that is not provided in the email itself, and would require searching the web to answer?  Respond with 'Yes' or 'No' - onw word only.")

                if search_needed.strip().lower() == "yes":
                    st.write("Web search is required. Performing search...")

                    # Extract the question or topic for the web search
                    question = chat_model(email_id, "Extract the question or topic from the email for web search.")
                    st.write(f"Extracted Question/Topic: {question}")

                    # Perform the web search
                    web_search = WebSearchService()
                    results = web_search.search_and_summarize(question)

                    st.text_area("Web search result", value=results, height=800)
                    # Display the search results
                    # if isinstance(results, list) and all(isinstance(result, dict) for result in results):
                    #     if results:
                    #         st.write("### Search Results")
                    #         for result in results:
                    #             if "title" in result and "link" in result:
                    #                 st.write(f"- [{result['title']}]({result['link']})")
                    #             else:
                    #                 st.warning("Malformed result: Missing 'title' or 'link'.")
                    #     else:
                    #         st.warning("No results found.")
                    # else:
                    #     st.error("Unexpected format for search results. Please check the WebSearchService implementation.")
                else:
                    st.info("No web search is required for this email.")
            else:
                st.warning(f"No email found with ID {email_id}.")
        except Exception as e:
            st.error(f"Error performing web search: {str(e)}")

# Slack Integration
elif options == "Slack Integration":
    st.header("Forward Important Emails to Slack")
    email_id = st.number_input("Enter Email ID to Check and Forward to Slack", min_value=1, step=1)


    if st.button("Check and Forward to Slack"):
        try:
            # Retrieve email content from the database
            session = db()  # Use the scoped session
            email_data = session.execute(text(f"SELECT body FROM emails WHERE id = {email_id}")).fetchone()

            if email_data:

                # Check if the email is important using chat_model
                st.write("Analyzing email to determine if it is important...")
                is_important = chat_model(email_id, "Is this email important? Respond with 'Yes' or 'No'.")

                if is_important.strip().lower() == "yes":
                    st.write("The email is marked as important.")

                    # Extract the summary of the email
                    st.write("Extracting summary of the email...")
                    email_summary = chat_model(email_id, "Summarize the email content.")
                    st.write(f"Email Summary: {email_summary}")

                    # Send the summary to Slack
                    slack_service = SlackOperations()
                    success = slack_service.send_message(email_summary)

                    if success:
                        st.success(f"Email summary forwarded to Slack channel  successfully!")
                    else:
                        st.error("Failed to forward email to Slack. Please check the Slack token and channel.")
                else:
                    st.info("The email is not marked as important. No action taken.")
            else:
                st.warning(f"No email found with ID {email_id}.")
        except Exception as e:
            st.error(f"Error forwarding email to Slack: {str(e)}")

# Schedule Meeting
elif options == "Schedule Meeting":
    st.header("Schedule a Meeting")
    email_id = st.number_input("Enter Email ID to Schedule Meeting", min_value=1, step=1)
    if st.button("Schedule Meeting"):
        try:
            # Retrieve email content from the database
            session = db()  # Use the scoped session
            email_data = session.execute(text(f"SELECT body FROM emails WHERE id = {email_id}")).fetchone()

            if email_data:
                email_body = email_data[0]

                # Check if the email is about meeting scheduling
                st.write("Analyzing email to determine if it contains meeting details...")
                is_meeting_email = chat_model(email_id, "Does the contain word - meeting? Respond with 'Yes' or 'No'.")

                if is_meeting_email.strip().lower() == "yes":
                    st.write("Meeting details detected in the email.")

                    # Extract meeting details using extract_meeting_details

                    meeting_details = extract_meeting_details(email_body)

                    if meeting_details:
                        st.write("### Extracted Meeting Details")
                        st.write(meeting_details)

                        st.success("Meeting scheduled successfully!")
                    else:
                        st.warning("Could not extract meeting details from the email.")
                else:
                    st.info("The email does not contain meeting details. No action taken.")
            else:
                st.warning(f"No email found with ID {email_id}.")
        except Exception as e:
            st.error(f"Error scheduling meeting: {str(e)}")

# Chat with Chatbot
elif options == "Chat with Chatbot":
    st.header("Chat with the AI Assistant")
    st.write("You can ask any question or have a conversation with the AI assistant.")


    # Initialize the AIService


    # Create a chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # User input
    user_input = st.text_input("You:", placeholder="Type your message here...")

    if st.button("Send"):
        if user_input.strip():
            # Add user input to chat history
            st.session_state.chat_history.append({"sender": "You", "message": user_input})

            # Get chatbot response
            with st.spinner("AI Assistant is typing..."):
                chatbot_response = chatbot_interaction(user_input)

            # Add chatbot response to chat history
            st.session_state.chat_history.append({"sender": "AI Assistant", "message": chatbot_response})

    # Display chat history
    for chat in st.session_state.chat_history:
        if chat["sender"] == "You":
            st.write(f"**You:** {chat['message']}")
        else:
            st.write(f"**AI Assistant:** {chat['message']}")