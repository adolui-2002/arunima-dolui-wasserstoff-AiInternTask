import re
from typing import Dict, Optional, Any
import uuid
import logging

from email_assistant.models import Email
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
import numpy as np
import faiss
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from email_assistant.config import settings
from email_assistant.process_meeting_email import process_meeting_email
# from email_assistant.web_search_service import WebSearchService
# from email_assistant.save_draft_email import save_draft_if_needed
logging.getLogger("httpx").setLevel(logging.WARNING)

results = {}

def setup_vector_store(chunks):
    embeddings = OllamaEmbeddings(model='deepseek-r1:1.5b', base_url="http://localhost:11434")
    vectors = np.array([embeddings.embed_query(text) for text in chunks], dtype="float32")
    print("Generated embeddings:", vectors)

    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    print("FAISS index created and vectors added.")

    docstore = InMemoryDocstore()
    index_to_docstore_id = {}

    for i, text in enumerate(chunks):
        doc_id = str(uuid.uuid4())
        doc = Document(page_content=text)
        docstore.add({doc_id: doc})
        index_to_docstore_id[i] = doc_id

    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )
    print("Vector store setup complete.")
    return vector_store

def create_rag_chain(retriever):
    prompt = """
        You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.understand the context and analyze whole data throughly before answering the question.
        If you don't know the answer, just say that you don't know.
        Answer concisely and directly without including any additional explanations or thought processes. Use the following pieces of retrieved context to answer the question.Try to be as concise as possible.try to give answer in one word if in details is not mentioned in the question. Don't give any extra information or detailed answer when it is not mentioned.Strictly follow the answer format asked in question.

        ### Question: {question}

        ### Context: {context}

        ### Answer:
    """
    model = ChatOllama(model="deepseek-r1:1.5b", base_url="http://localhost:11434")
    prompt_template = ChatPromptTemplate.from_template(prompt)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_template
        | model
        | StrOutputParser()
    )
    print("RAG chain created successfully.")
    return chain

def chatbot_interaction(question: str) -> str:
    vector_sto = setup_vector_store([question])
    retriever = vector_sto.as_retriever(search_type="mmr", search_kwargs={'k': 3})
    rag_chain = create_rag_chain(retriever)
    answer = ""  # Initialize an empty string to collect chunks
    question = "Give me answer in detail in 4-5 line" + question
    print(f"Question: {question}")

    for chunk in rag_chain.stream(question):
            answer += chunk  # Append each chunk to the answer
    cleaned_response = clean_response(answer)  # Clean the response
    print(f"\n\nExtracted Questions: {cleaned_response}")
    return cleaned_response  # Return the cleaned response


def chat_model(email_id: int, question: str) -> str:
    """
    Process a question using the RAG chain and return the cleaned response.

    Args:
        email_id: The ID of the email being processed.
        question: The question to ask the RAG chain.

    Returns:
        The cleaned response from the RAG chain.
    """
    try:
        # Set up database connection
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()



        email_data = get_email_from_db(session, email_id)
        if not email_data:
            logging.error(f"Email with ID {email_id} not found.")
            return

        logging.info(f"Processing email: {email_data['subject']}")
        data = f"email subject: {email_data['subject']}\nemail body: {email_data['body']}"


        vector_sto = setup_vector_store([data])
        retriever = vector_sto.as_retriever(search_type="mmr", search_kwargs={'k': 3})
        rag_chain = create_rag_chain(retriever)
        answer = ""  # Initialize an empty string to collect chunks
        print(f"Question: {question}")

        for chunk in rag_chain.stream(question):
            answer += chunk  # Append each chunk to the answer
        cleaned_response = clean_response(answer)  # Clean the response
        print(f"\n\nExtracted Questions: {cleaned_response}")
        return cleaned_response  # Return the cleaned response
    except Exception as e:
        print(f"Error processing question: {e}")
        return "Error processing question"
# def extract_question(rag_chain):
#     """
#     Extract questions from the email using the RAG chain.

#     Args:
#         rag_chain: The RAG chain to query for questions.

#     Returns:
#         None
#     """
#     prompt1 = "Send a list of questions or the information is asked by sender or any topic for discussion on in the email. If there are multiple questions, your answer should be in this format: 1. question1, 2. question2, 3. question3."

#     answer2 = ""  # Initialize an empty string to collect chunks
#     print(f"Question: {prompt1}")
#     try:
#         for chunk in rag_chain.stream(prompt1):
#             answer2 += chunk  # Append each chunk to the answer
#         cleaned_response = clean_response(answer2)  # Clean the response
#         print(f"\n\nExtracted Questions: {cleaned_response}")

#         # Perform web search and summarize the questions
#         web_search = WebSearchService()
#         web_search.search_and_summarize(cleaned_response)
#     except Exception as e:
#         print(f"Error extracting questions: {e}")

def extract_meeting_details(data: str) -> str :
    """
    Extract meeting details such as agenda, location, description, start/end date and time, and attendees.

    Args:
        rag_chain: The RAG chain to query for meeting details.

    Returns:
        A dictionary containing the extracted meeting details.
    """
    vector_sto = setup_vector_store([data])
    retriever = vector_sto.as_retriever(search_type="mmr", search_kwargs={'k': 3})
    rag_chain = create_rag_chain(retriever)

    meeting_details = {}
    questions = {
        "summary": "What is the agenda of the meeting?",
        "location": "What is the location of the meeting?",
        "description": "What is the description of the meeting?",
        "start_date": "What is the start date of the meeting? Please send reply in dd-mm-yyyy format in one word only.If date is not present then find out day of the week and send reply in one word only.",
        "start_time": "What is the start time of the meeting?Please send reply in hh:mm am/pm format in one word only",
        "end_date": "What is the end date of the meeting? Please send reply in dd-mm-yyyy format in one word only",
        "end_time": "What is the end time of the meeting? Please send reply in hh:mm am/pm format in one word only.",
        "attendees": "Who is/are the attendees of the meeting? If there are multiple attendees, please separate them with commas.If attendees email id is present then please send email id of attendees in one word, If not then please send name of attendees separeted with comma in 2 words.",
    }

    for key, question in questions.items():
        response = ""
        print(f"Question: {question}")
        try:
            for chunk in rag_chain.stream(question):
                response += chunk  # Append each chunk to the response
            cleaned_response = clean_response(response)
            meeting_details[key] = cleaned_response.strip()  # Store the cleaned response
            print(f"{key.capitalize()}: {cleaned_response}")
        except Exception as e:
            print(f"Error extracting {key}: {e}")
            meeting_details[key] = "Error extracting information"

    print("\n\nExtracted Meeting Details:", meeting_details)
    process_meeting_email(meeting_details)
    return "success"

def clean_response(response: str) -> str:
    """
    Remove any '<think>' sections from the model's response.

    Args:
        response: The raw response from the model.

    Returns:
        The cleaned response without '<think>' sections.
    """
    # Remove everything between <think> and </think>
    cleaned_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    return cleaned_response

def get_email_from_db(session, email_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve an email from the database by its ID.

    Args:
        session: The database session to use.
        email_id: The ID of the email to retrieve.

    Returns:
        A dictionary containing the email data, or None if not found.
    """
    try:
        email = session.query(Email).filter_by(id=email_id).first()
        if email:
            print(f"Email found: {email.subject}")
            return {
                "thread_id": email.thread_id,
                "message_id": email.message_id,
                "sender": email.sender,
                "recipient": email.recipient,
                "subject": email.subject,
                "timestamp": email.timestamp,
                "body": email.body,
                "is_important": email.is_important,
                "priority": email.priority,
                "intent": email.intent,
                "summary": email.summary,
                "no_response": email.no_response,
                "status": email.status,
            }
        else:
            print(f"Email with ID {email_id} not found.")
            return None
    except Exception as e:
        print(f"Error retrieving email: {e}")
        return None



# def process_email(session, email_id: int):
#     """
#     Process an email to extract relevant information and perform actions.

#     Args:
#         session: The database session to use.
#         email_id: The ID of the email to process.
#     """
#     try:
#         email_data = get_email_from_db(session, email_id)
#         if not email_data:
#             logging.error(f"Email with ID {email_id} not found.")
#             return

#         logging.info(f"Processing email: {email_data['subject']}")
#         data = f"email subject: {email_data['subject']}\nemail body: {email_data['body']}"


#         vector_sto = setup_vector_store([data])
#         retriever = vector_sto.as_retriever(search_type="mmr", search_kwargs={'k': 3})
#         rag_chain = create_rag_chain(retriever)

#         prompt1 = "What is the summary of the email? answer in 1 line"
#         raw_response1 = ""
#         print(f"Question: {prompt1}")
#         for chunk in rag_chain.stream(prompt1):
#             raw_response1 += chunk
#         cleaned_response1 = clean_response(raw_response1)
#         print(f"Answer: {cleaned_response1}")

#         # Repeat for other prompts
#         prompt2 = "Is sender discuss abbout some question or asking about any information or some question under discussion on or some question- answer of which is not present in email? reply in one word - say yes or no."
#         raw_response2 = ""
#         print(f"\n\nQuestion: {prompt2}")
#         for chunk in rag_chain.stream(prompt2):
#             raw_response2 += chunk
#         cleaned_response2 = clean_response(raw_response2)
#         print(f"\n\nAnswer: {cleaned_response2}")
#         if "yes" in cleaned_response2.lower():
#             extract_question(rag_chain)
#         else:
#             print("No additional questions found.")

#         prompt3 = "is theere meeting keyword present in the email? reply in one word - say yes or no."
#         raw_response3 = ""
#         print(f"\n\nQuestion: {prompt3}")
#         for chunk in rag_chain.stream(prompt3):
#             raw_response3 += chunk
#         cleaned_response3 = clean_response(raw_response3)
#         print(f"Answer: {cleaned_response3}")
#         if "yes" in cleaned_response3.lower():
#             extract_meeting_details(rag_chain)
#         else:
#             print("No meeting  found.")

#         prompt4 = "Is there reply of email is needed or action needed in the email?reply in one word -  say yes or no."
#         raw_response4 = ""
#         print(f"Question: {prompt4}")
#         for chunk in rag_chain.stream(prompt4):
#             raw_response4 += chunk
#         cleaned_response4 = clean_response(raw_response4)
#         print(f"Answer: {cleaned_response4}")
#         if "yes" in cleaned_response4.lower():
#             prompt5 = "Draft a short, polite reply to the sender as a answer of acknowledgement of email."
#             raw_response5 = ""
#             print(f"Question: {prompt5}")
#             for chunk in rag_chain.stream(prompt5):
#                 raw_response5 += chunk
#             cleaned_response5 = clean_response(raw_response5)
#             print(f"Answer: {cleaned_response5}")
#             save_draft_if_needed(email_data["subject"], cleaned_response5, email_data["sender"])
#         else:
#             print("No reply needed.")

#     except Exception as e:
#         logging.error(f"Error processing email: {e}")

# def rag_model(email_id: int):

#     try:
#         # Set up database connection
#         engine = create_engine(settings.DATABASE_URL)
#         Session = sessionmaker(bind=engine)
#         session = Session()

#         # Initialize the processing
#         process_email(session, email_id)
#     except Exception as e:
#         print(f"Error processing email with ID {email_id}: {e}")



