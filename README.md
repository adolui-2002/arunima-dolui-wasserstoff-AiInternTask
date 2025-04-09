# Email Assistant Project

## Overview
The **Email_Assistant** project is designed to automate email-related tasks using advanced AI models and tools. It integrates various components such as email fetching, natural language processing (NLP) using large language models (LLMs), meeting scheduling, and chatbot interaction. The system is built to streamline email management, extract actionable insights, and provide intelligent responses.

The project uses `rag_setup` for Retrieval-Augmented Generation (RAG) tasks, which enables the system to retrieve relevant context and generate accurate responses.

## Key Features

### Email Management:
- Fetch and store emails in a database.
- Extract key details such as sender, recipient, subject, and body.

### AI-Powered Analysis:
- Use RAG-based models for summarization, question extraction, and agenda detection.
- Determine if a reply is needed or if meeting details are present.

### Meeting Scheduling:
- Extract meeting details (e.g., agenda, time, location) and schedule events in Google Calendar.
- Handle missing or incomplete meeting details gracefully.

### Chatbot Interaction:
- Provide a conversational interface for users to interact with the AI assistant.
- Answer user queries and provide detailed responses.

### Web Search Integration:
- Perform web searches for additional context or answers to questions found in emails.

### Draft Email Replies:
- Automatically draft polite and professional email responses based on the email content.

## System Architecture

### Components

#### Database:
- Stores email data, including sender, recipient, subject, body, and metadata.
- SQLAlchemy is used for ORM (Object-Relational Mapping).

#### RAG Integration:
- The `rag_setup` module is used for Retrieval-Augmented Generation tasks.
- It retrieves relevant context from a vector store and generates responses using a language model.

#### Google Calendar API:
- Used for scheduling meetings and checking time slot availability.

#### Streamlit:
- Provides a user-friendly interface for interacting with the assistant.

#### Web Search Service:
- Searches the web for additional context or answers to questions.

### Workflow

#### Email Fetching:
- Emails are fetched from a source (e.g., Gmail API) and stored in the database.
- Each email is assigned a unique ID for processing.

#### Email Processing:
- The email body is analyzed using the `rag_setup` module to extract:
  - Summary or agenda.
  - Questions asked in the email.
  - Meeting details (e.g., time, location, attendees).
- The system determines if a reply is needed or if an action is required.

#### Meeting Scheduling:
- If meeting details are found, the system schedules the meeting in Google Calendar.
- Missing details (e.g., end time) are handled with default values.

#### Chatbot Interaction:
- Users can interact with the assistant via a chat interface.
- The chatbot uses the `chatbot_interaction` function from `rag_setup` to generate responses.

#### Web Search:
- If questions are found in the email, the system performs a web search to find answers.

#### Drafting Replies:
- If a reply is needed, the system drafts a professional response using the `rag_setup` module.

## Major Components

### 1. Email Management

#### Fetching Emails:
- Emails are fetched using APIs (e.g., Gmail API) and stored in a database.
- The `get_email_from_db` function retrieves emails for processing.

#### Database Schema:
The `Email` model defines the schema for storing email data:
- `id`: Unique identifier.
- `sender`: Email sender.
- `recipient`: Email recipient.
- `subject`: Email subject.
- `body`: Email body.
- `timestamp`: Time the email was sent.

### 2. RAG Integration

#### RAG Setup:
- The `rag_setup` module is used for Retrieval-Augmented Generation tasks.
- It retrieves relevant context from a vector store and generates responses using a language model.

#### Key Functions:
- `setup_vector_store`: Sets up a vector store for storing and retrieving embeddings.
- `create_rag_chain`: Creates a RAG chain for generating responses.
- `chatbot_interaction`: Handles user interaction with the chatbot.
- `extract_meeting_details`: Extracts meeting details from email content.

### 3. Meeting Scheduling

#### Google Calendar Integration:
- The `process_meeting_email` function schedules meetings in Google Calendar.
- Missing details (e.g., end time) are handled with default values.

#### Key Functions:
- `parse_datetime_with_dateutil`: Parses date and time strings into datetime objects.
- `check_time_slot_availability`: Checks if a time slot is available in the calendar.
- `create_event`: Creates a calendar event.

### 4. Chatbot Interaction

#### Chat Interface:
- Users can interact with the assistant via a chat interface in the Streamlit app.
- The `chatbot_interaction` function generates responses to user queries.

#### RAG Integration:
- The `chatbot_interaction` function uses the RAG chain to retrieve relevant context and generate responses.

### 5. Web Search Integration

#### Web Search Service:
- The `WebSearchService` class performs web searches for additional context or answers to questions.

### 6. Drafting Replies

#### Draft Email:
- The `draft_email` function generates a professional email response based on the email content.

## Challenges and Solutions

### 1. Authentication Issues
#### Challenge:
- Missing or invalid credentials for Google Calendar API or Hugging Face API.

#### Solution:
- Ensure that the `credentials.json` file contains valid credentials.
- Refresh tokens periodically to avoid expiration.

### 2. Rate Limits
#### Challenge:
- API rate limits for Hugging Face or Google Calendar.

#### Solution:
- Implement retry logic with exponential backoff for API calls.

### 3. LLM Output Formatting
#### Challenge:
- LLM responses may contain unexpected or invalid formats.

#### Solution:
- Use regular expressions and validation functions to clean and validate LLM outputs.

### 4. Missing Meeting Details
#### Challenge:
- Emails may lack complete meeting details (e.g., end time, attendees).

#### Solution:
- Use default values for missing details (e.g., 1-hour duration for meetings).

### 5. Complex Email Parsing
#### Challenge:
- Parsing unstructured email content to extract actionable insights.

#### Solution:
- Use advanced NLP models and regular expressions to extract relevant information.

## Tools and Libraries

- **Ollama**: Runs and manages local LLMs efficiently, enabling offline inference for the project.
- **DeepSeekR1**: Serves as the main language model for understanding and generating natural language responses.
- **LangChain**: Used for RAG (Retrieval-Augmented Generation) tasks.
- **Google Calendar API**: Used for scheduling meetings and checking time slot availability.
- **SQLAlchemy**: ORM for managing the database.
- **Streamlit**: Provides a user-friendly interface for interacting with the assistant.
- **Dateutil**: Used for parsing date and time strings.
- **Pytz**: Handles timezone conversions.

## Assumptions

- **Email Content**: Emails contain sufficient information for processing (e.g., meeting details, questions).
- **RAG Accuracy**: The RAG chain provides accurate and relevant responses.
- **API Availability**: External APIs (e.g., Google Calendar, LangChain) are available and responsive.
