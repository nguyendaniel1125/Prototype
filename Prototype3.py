import streamlit as st
import os
import requests
from openai import OpenAI
from bs4 import BeautifulSoup
import pandas as pd
from opencage.geocoder import OpenCageGeocode
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
from PyPDF2 import PdfReader

# Initialize Firebase app
cred = credentials.Certificate("floodguard-ai-firebase-adminsdk-1gehw-297a26cec3.json")  # Update with your Firebase credentials path
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()

# Initialize OpenCage Geocoder
geocoder = OpenCageGeocode("469906be508849a68838fbcb10c31ce0")  # Replace with your OpenCage API key

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Santa Clara County zip codes
santa_clara_zip_codes = {
    "95002", "95008", "95013", "95014", "95020", "95032", "95035", "95037",
    "95046", "95101", "95110", "95111", "95112", "95113", "95116", "95117",
    "95118", "95119", "95120", "95121", "95122", "95123", "95124", "95125",
    "95126", "95127", "95128", "95129", "95130", "95131", "95132", "95133",
    "95134", "95135", "95136", "95138", "95139", "95140", "95141", "95148",
    "95150", "95151", "95152", "95153", "95154", "95155", "95156", "95157",
    "95158", "95159", "95160", "95161", "95164", "95170", "95172", "95173",
    "95190", "95191", "95192", "95193", "95194", "95196"
}

# Streamlit page configuration
st.set_page_config(page_title="Flood Preparedness & Reporting", layout="wide")

# Main navigation
st.sidebar.title("Navigation")
option = st.sidebar.selectbox("Choose a tab", ["Main Page", "Flood Information Extractor", "Flood Preparedness Advisor"])

# Wrapper function for OpenAI API completion
def get_completion(prompt, model="gpt-3.5-turbo"):
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "You are a flood preparedness expert."},
                      {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating advice: {str(e)}"

# Function to extract flood-related information from a URL
def extract_flood_info_from_url(url, keyword=None, max_paragraphs=5):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else 'No title found'
        paragraphs = [para.get_text().strip() for para in soup.find_all('p') if para.get_text().strip()]
        
        if keyword:
            paragraphs = [para for para in paragraphs if keyword.lower() in para.lower()]
        
        content_text = " ".join(paragraphs[:max_paragraphs])
        summary = summarize_text(content_text)  # Generate summary of the content

        return title, paragraphs[:max_paragraphs], summary
    except Exception as e:
        return str(e), [], None

# Function to generate a summary of the flood-related information
def summarize_text(text, max_tokens=100):
    try:
        prompt = f"Summarize the following flood-related information:\n\n{text}"
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a summarizer for flood-related content."},
                      {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating summary: {str(e)}"
    
# Add a function to handle user questions about the page content
def answer_question_about_content(content, question):
    try:
        prompt = f"Based on the following flood-related information, answer the question:\n\nContent: {content}\n\nQuestion: {question}"
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a flood preparedness expert answering questions."},
                      {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error answering question: {str(e)}"
    
# Function to extract text from PDF    
def extract_text_from_pdf(pdf_path):
    try:
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page].extract_text()
        return text
    except Exception as e:
        return f"Error reading the PDF: {str(e)}"

# Function to get preparedness advice from PDF content
def get_preparedness_advice_from_pdf(pdf_content, zip_code, residence_type, has_pets, wheelchair_accessibility, health_risks):
    try:
        prompt = (
            f"Using the following flood preparedness PDF content, provide advice:\n\n{pdf_content}\n\n"
            f"Considerations: Zip code {zip_code}, residence type {residence_type}, "
            f"pets: {'Yes' if has_pets else 'No'}, "
            f"wheelchair accessibility: {'Yes' if wheelchair_accessibility else 'No'}, "
            f"health risks: {health_risks}."
        )
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a flood preparedness advisor using PDF-based information."},
                      {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating advice: {str(e)}"

# Handle different options
if option == "Main Page":
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>FLOOD PREPAREDNESS & REPORTING SYSTEM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFFFFF;'>This tool provides resources to stay safe during floods and report flood incidents in your area.</p>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='color: #1f77b4;'>Explore the Key Features:</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Flood Risk Mapping", key="flood_risk_mapping")
        st.write("Interactive flood map showing flood-prone areas. Use this feature to identify areas with high risk and prepare accordingly.")
        
    with col2:
        st.button("Flood Reporting", key="flood_reporting")
        st.write("Real-time flood reporting allows you to report incidents as they happen. Provide details such as location and severity to assist authorities in responding quickly.")
        
    with col3:
        st.button("Preparedness Checklist", key="preparedness_checklist")
        st.write("Comprehensive checklist to ensure you're ready for a flood. This feature helps you track your supplies and plan your evacuation strategy.")

elif option == "Flood Information Extractor":
    st.subheader("Flood Information Extractor")
    # Initialize session state variables if they don’t exist
    if 'url_input' not in st.session_state:
        st.session_state.url_input = ''
    if 'keyword_input' not in st.session_state:
        st.session_state.keyword_input = ''
    if 'summary' not in st.session_state:
        st.session_state.summary = ''
    if 'key_points' not in st.session_state:
        st.session_state.key_points = []
    if 'question_input' not in st.session_state:
        st.session_state.question_input = ''
    if 'answer' not in st.session_state:
        st.session_state.answer = ''

    st.session_state.url_input = st.text_input("Enter the URL of the flood-related website:", st.session_state.url_input)
    st.session_state.keyword_input = st.text_input("Optional: Specify a flood-related term:", st.session_state.keyword_input)
    max_paragraphs = st.slider("Number of key points to display:", 1, 20, 5)

    if st.button("Extract Flood Info"):
        if st.session_state.url_input:
            title, st.session_state.key_points, st.session_state.summary = extract_flood_info_from_url(
                st.session_state.url_input, 
                keyword=st.session_state.keyword_input, 
                max_paragraphs=max_paragraphs
            )
            st.write(f"**Page Title:** {title}")
            st.write("### Summary of Flood Information:")
            st.write(st.session
