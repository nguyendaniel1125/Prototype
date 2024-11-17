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
import folium
from streamlit_folium import st_folium
from PIL import Image
from PyPDF2 import PdfReader
import csv
import time
import pydeck as pdk

# Initialize Firebase app
cred = credentials.Certificate("floodguard-ai-firebase-adminsdk-1gehw-297a26cec3.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Initialize Firestore client
db = firestore.client()

# Initialize OpenCage Geocoder
geocoder = OpenCageGeocode("469906be508849a68838fbcb10c31ce0")

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
st.set_page_config(page_title="Flood Preparedness & Reporting System", layout="wide")

# Main navigation
st.sidebar.title("Navigation")
option = st.sidebar.selectbox("Choose a tab", [
    "Main Page", 
    "Flood Information Extractor", 
    "Flood Preparedness Advisor", 
    "Community Flood Reporting Map"
])

# Helper functions (openai, geocode, extraction, etc.)

# Function to read existing flood data from CSV
def read_flood_data():
    try:
        with open("flood_data.csv", mode="r") as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except FileNotFoundError:
        return []  # Return an empty list if the file doesn't exist

# Function to save updated flood data to CSV
def save_flood_data(data):
    with open("flood_data.csv", mode="w", newline='') as file:
        fieldnames = ["lat", "lon", "address", "type", "severity", "image_path"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()  # Write header row
        writer.writerows(data)  # Write the rows of data

# Function to save the uploaded image to the 'flood_images/' directory
def save_image(image, image_name):
    if not os.path.exists('flood_images'):
        os.makedirs('flood_images')
    image_path = os.path.join('flood_images', image_name)
    with open(image_path, "wb") as img_file:
        img_file.write(image.getbuffer())
    return image_path

# Geocode address to get latitude and longitude
def geocode_address(address):
    result = geocoder.geocode(address)
    if result:
        lat = result[0]['geometry']['lat']
        lon = result[0]['geometry']['lng']
        return lat, lon
    return None, None

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

# Main app flow

if option == "Main Page":
    # Page title
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>FLOOD PREPAREDNESS & REPORTING SYSTEM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFFFFF;'>This tool provides resources to stay safe during floods and report flood incidents in your area.</p>", unsafe_allow_html=True)
    
    # Description of features
    st.markdown("<h2 style='color: #1f77b4;'>Explore the Key Features:</h2>", unsafe_allow_html=True)
    
    # Create columns for a modern layout
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
    
    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)

    # Call to action message
    st.markdown("<h3 style='text-align: center; color: #FFFFFF;'>Explore each feature to stay informed, prepared, and safe during flood emergencies. Click on a feature to get started!</h3>", unsafe_allow_html=True)

elif option == "Flood Information Extractor":
    st.subheader("Flood Information Extractor")

    # Session state for URL input, keyword, etc.
    st.session_state.url_input = st.text_input("Enter the URL of the flood-related website:", "")
    st.session_state.keyword_input = st.text_input("Optional: Specify a flood-related term:", "")
    max_paragraphs = st.slider("Number of key points to display:", 1, 20, 5)

    # Button to extract flood information
    if st.button("Extract Flood Info"):
        # Call extraction and display results here (similar to original code)
        pass

elif option == "Flood Preparedness Advisor":
    st.subheader("Flood Preparedness Advisor")

    # Path to the PDF file and extraction function (as per the original code)
    pdf_path = r"Valley Water Dataset.pdf"
    pdf_content = extract_text_from_pdf(pdf_path)

    # Form for user inputs (same structure as in the original code)
    with st.form(key="advisor_form"):
        zip_code = st.text_input("Enter your zip code (Santa Clara County only)")
        residence_type = st.selectbox("Type of residence", ["House", "Apartment", "Mobile Home", "Other"])
        has_pets = st.checkbox("Do you have pets?")
        wheelchair_accessibility = st.checkbox("Wheelchair accessibility considerations")
        health_risks = st.text_area("List any health risks you might have during flooding")
        
        submitted = st.form_submit_button("Get Preparedness Advice")
        
        if submitted and zip_code in santa_clara_zip_codes:
            response = get_preparedness_advice_from_pdf(
                pdf_content, zip_code, residence_type, has_pets, wheelchair_accessibility, health_risks
            )
            st.write(response)

elif option == "Community Flood Reporting Map": 
    st.set_page_config(
    page_title="Flood Report System",
    page_icon="🌊",  # Optional: You can specify an icon here
    layout="wide",  # Optional: 'centered' or 'wide'
    initial_sidebar_state="expanded",  # Optional: 'collapsed', 'expanded'
)

    with st.spinner('Processing your report...'):
        # Simulate some delay (like API call or image upload)
        time.sleep(2)
    st.success('Your flood report has been successfully added!')


