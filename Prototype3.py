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
    # Ensure the 'flood_images' directory exists
    if not os.path.exists('flood_images'):
        os.makedirs('flood_images')
    
    # Define the path where the image will be saved
    image_path = os.path.join('flood_images', image_name)
    
    # Save the image to the defined path
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

# Main app flow

if option == "Main Page":
    # Page title
    st.image("Project Logo FloodGuard AI.png", width=200)
    st.markdown("<h1 style='text-align: center;'>FLOODGUARD AI</h1>", unsafe_allow_html=True)

    st.markdown("<p style='text-align: center;'>This tool provides resources to stay safe during floods and report flood incidents in your area using the power of AI. </p>", unsafe_allow_html=True)
    
    # Description of features
    st.markdown("<h2>Explore the Key Features:</h2>", unsafe_allow_html=True)
    
    # Create columns for a modern layout
    col1, col2, col3 = st.columns(3)

    with col1:
        st.button("Flood Information Extractor", key="Flood Information Extractor")
        st.write("Extract information from a given website that provides flooding information.")
        
    with col2:
        st.button("Flood Preparedness Advisor", key="Flood Preparedness Advisor")
        st.write("Personalized flooding preparedness information from Santa Clara Valley Water.")
        
    with col3:
        st.button("Preparedness Checklist", key="preparedness_checklist")
        st.write("Real-time flood reporting allows you to report incidents as they happen. Provide details such as location and severity to assist authorities in responding quickly.")
    
    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)

    # Call to action message
    st.markdown("<h3 style='text-align: center; color: '>Explore each feature to stay informed, prepared, and safe during flood emergencies! </h3>", unsafe_allow_html=True)

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

    # User inputs for URL, keyword, and maximum paragraphs to display
    st.session_state.url_input = st.text_input("Enter the URL of the flood-related website:", st.session_state.url_input)
    st.session_state.keyword_input = st.text_input("Optional: Specify a flood-related term:", st.session_state.keyword_input)
    max_paragraphs = st.slider("Number of key points to display:", 1, 20, 5)

    # Button to extract flood information
    if st.button("Extract Flood Info"):
        if st.session_state.url_input:
            # Extract title, key points, and summary from the URL
            title, st.session_state.key_points, st.session_state.summary = extract_flood_info_from_url(
                st.session_state.url_input, 
                keyword=st.session_state.keyword_input, 
                max_paragraphs=max_paragraphs
            )
            
            # Display title and summary
            st.write(f"**Page Title:** {title}")
            st.write("### Summary of Flood Information:")
            st.write(st.session_state.summary if st.session_state.summary else "No summary available.")
            
            # Display key flood information as bullet points
            st.write("### Key Flood Information:")
            for i, point in enumerate(st.session_state.key_points, 1):
                st.write(f"{i}. {point}")

    # Input for user question
    st.session_state.question_input = st.text_input("Ask a specific question about this page's content:", st.session_state.question_input)
    
    # Button to generate an answer based on the question input
    if st.button("Get Answer") and st.session_state.question_input:
        st.session_state.answer = answer_question_about_content(
            f"{st.session_state.summary} {' '.join(st.session_state.key_points)}", 
            st.session_state.question_input
        )
        st.write("### Answer:")
        st.write(st.session_state.answer)


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
    with st.spinner('Processing your report...'):
        # Simulate some delay (like API call or image upload)
        time.sleep(2)
    st.sidebar.header("Report a Flood")
    with st.sidebar.form("flood_form"):
        street_address = st.text_input("Street Address")
        flood_type = st.selectbox("Cause of Flood", ["Storm Drain Blockage", "Well/Reservoir Overflow", "Pipe Burst", "Debris", "Other"])
        
        # Conditional text input for custom flood type
        if flood_type == "Other":
            custom_flood_type = st.text_input("Please specify the cause of flooding")
        else:
            custom_flood_type = flood_type  # Use selected flood type if it's not "Other"
        
        severity = st.slider("Flood Severity (1 = Minor, 5 = Severe)", min_value=1, max_value=5)
        
        # Image uploader
        flood_image = st.file_uploader("Upload an image of the flood", type=["jpg", "png", "jpeg"])
        
        submitted = st.form_submit_button("Submit Report")
    
    # If a user submits a new report, save it to the CSV file
    if submitted and street_address:
        # Geocode the address to get latitude and longitude
        lat, lon = geocode_address(street_address)
        
        if lat and lon:
            # If an image is uploaded, save it to the flood_images folder
            if flood_image:
                image_name = f"{street_address.replace(' ', '_')}_{flood_type}.jpg"  # Name the image based on address and flood type
                image_path = save_image(flood_image, image_name)  # Save the image and get the file path
            else:
                image_path = None  # No image uploaded
            
            # Create a new report with latitude, longitude, and other details
            new_report = {
                "lat": lat,
                "lon": lon,
                "address": street_address,
                "type": custom_flood_type,
                "severity": severity,
                "image_path": image_path  # Store the path to the image
            }
            
            # Append the new report to the existing data
            flood_data = read_flood_data()  # Get current data from the CSV
            flood_data.append(new_report)  # Add the new report
            
            # Save the updated data to the CSV file
            save_flood_data(flood_data)
            
            # Display a success message
            st.success(f"Flood report added for {street_address}. See it on the map below.")
            
            # Display the image if it was uploaded
            if flood_image:
                st.image(flood_image, caption="Uploaded Flood Image", use_container_width=True)
        else:
            st.error("Could not geocode the address. Please try again.")
    
    # Load and display all flood data (including images) from the CSV
    flood_data = read_flood_data()
    
    # If there is any flood data, show the map
    if flood_data:
        # Create DataFrame for pydeck map rendering
        df = pd.DataFrame(flood_data)
        
        # Convert the 'lat' and 'lon' columns to numeric types
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    
        # Set fixed zoom level and initial view for the map (for consistency)
        initial_lat = df['lat'].mean() if len(df) > 0 else 37.7749  # Default latitude (San Francisco)
        initial_lon = df['lon'].mean() if len(df) > 0 else -122.4194  # Default longitude (San Francisco)
        
        # Set a wider zoom level for a more "wide" map (e.g., zoom=8)
        view = pdk.ViewState(latitude=initial_lat, longitude=initial_lon, zoom=10)  # Wider zoom level
        
        # Define a layer for the flood reports
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_radius=100,  # Adjust the radius for visibility
            get_fill_color=[255, 0, 0],  # Red color for flood markers
            pickable=True,  # Allows interaction with the markers
            radius_min_pixels=5
        )
        
        # Mapbox style for street map
        map_style = "mapbox://styles/mapbox/streets-v11"  # Street map style from Mapbox
    
        # Create the pydeck deck with the specified map style
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            map_style=map_style  # Set the street map style
        )
        
        # Render the map in Streamlit
        st.pydeck_chart(deck)
    
    # Display the flood reports in a user-friendly format
    if flood_data:
        st.header("Flood Reports")
        
        # Create a table to display the reports
        for report in flood_data:
            with st.expander(f"Details for {report['address']}"):  # Make each report expandable
                st.subheader(f"Address: {report['address']}")
                st.write(f"Flood Type: {report['type']}")
                st.write(f"Severity: {report['severity']}/5")
                
                # Display image if available
                if report["image_path"]:
                    st.image(report["image_path"], caption="Flood Image", use_container_width=True)
                
                st.write("----")
    
    else:
        st.info("No flood reports available.")    
        
    
