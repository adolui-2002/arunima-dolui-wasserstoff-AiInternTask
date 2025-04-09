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
- API rate limits for Google web search or Google Calendar.

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


## Getting Started

### Prerequisites
- Python 3.11 or higher
- A Google API key
- A Google searcg ID
- A Slack BOT Token
- A Email address
- A Email Password

### Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/adolui-2002/arunima-dolui-wasserstoff-AiInternTask.git
    cd email_assistant
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up environment variables:
    - Create a `.env` file in the root directory with the following content:
      ```env
      GOOGLE_API_KEY = your_google_api_key
      GOOGLE_SEARCH_ID = your_google_sear_id
      SLACK_BOT_TOKEN = your_slack_bot_token
      EMAIL_ADDRESS= your_email_address
      EMAIL_PASSWORD= your_email_password
      
      ```

### Running the Application
1. Start the Streamlit application:
    ```sh
    streamlit run streamlit_app.py
    ```

2. Open your web browser and navigate to `http://localhost:8501` to interact with the chatbot.



## Contributing
Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.



