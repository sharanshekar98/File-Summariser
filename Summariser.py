import os
import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import time
from google import genai
from google.genai import types

# 1. Page Configuration & Custom "Bright & Appealing" Styling
st.set_page_config(
    page_title="AI File Insight Studio",
    page_icon="✨",
    layout="centered"
)

# Custom CSS to inject a bright, energetic, and clean aesthetic
st.markdown("""
    <style>
    /* Main background and font styling */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Header styling */
    h1 {
        color: #1e3a8a !important;
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Bright & Appealing File Uploader Card */
    [data-testid="stFileUploader"] {
        background-color: #ffffff !important;
        padding: 25px !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.15) !important;
        border: 3px dashed #3b82f6 !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #2563eb !important;
        box-shadow: 0 10px 35px rgba(59, 130, 246, 0.25) !important;
    }
    
    /* Bright & Appealing Text Area Search Input */
    div[data-testid="stTextArea"] textarea {
        background-color: #ffffff !important;
        color: #1f2937 !important;
        border: 2.5px solid #10b981 !important; /* Bright Emerald Green Border */
        border-radius: 14px !important;
        padding: 15px !important;
        font-size: 15px !important;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.1) !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #059669 !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.25) !important;
    }
    /* Style label for the search area */
    div[data-testid="stTextArea"] label p {
        color: #065f46 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
    }
    
    /* Bright, appealing Button Styling */
    div.stButton > button:first-child {
        background: linear-gradient(45deg, #ff4e50, #f9d423) !important;
        color: white !important;
        border: none !important;
        padding: 12px 30px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border-radius: 25px !important;
        box-shadow: 0 4px 15px rgba(255, 78, 80, 0.4) !important;
        transition: all 0.3s ease !important;
        width: 100%;
        margin-top: 10px;
    }
    
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 78, 80, 0.6) !important;
    }
    
    /* Response box styling */
    .insight-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid #ff4e50;
        box-shadow: 0 5px 15px rgba(0,0,0,0.04);
        margin-top: 20px;
        color: #1f2937;
        white-space: pre-wrap;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to extract text directly from a Word (.docx) file
def extract_text_from_docx(file_io):
    try:
        with zipfile.ZipFile(file_io) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://openxmlformats.org'}
            text_elements = root.findall('.//w:t', namespaces)
            return " ".join([t.text for t in text_elements if t.text])
    except Exception as e:
        return f"Error extracting Word text: {str(e)}"

# 3. UI Layout
st.title("✨ AI File Insight Studio")
st.markdown("Upload a document or ask a text question to instantly get smart AI summaries and insights.")
st.write("---")

# 🔑 Dynamic Sidebar API Key Input
with st.sidebar:
    st.header("🔑 Authentication")
    api_key_input = st.text_input("Enter Gemini API Key", type="password", placeholder="AIzaSy...")
    st.markdown("[Get a free key from Google AI Studio](https://google.com)")

# --- Interactive Input Section ---
# Bright File Uploader Container
uploaded_file = st.file_uploader(
    "Choose a file (PDF, TXT, Images, CSV, Word Documents, etc.)", 
    type=["pdf", "txt", "csv", "png", "jpg", "jpeg", "docx"]
)

st.write("") # Extra spacing spacer

# Bright Text Search Container
text_query = st.text_area(
    "🔍 Search or Ask AI with Text",
    placeholder="Ask a question, paste text to summarize, or specify what to find in your uploaded file...",
    height=110
)

# Track if we have any usable input to trigger the button
has_input = uploaded_file is not None or text_query.strip() != ""

if uploaded_file is not None:
    st.success(f"🎉 **File successfully uploaded!**")
    file_bytes_data = uploaded_file.getvalue()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="File Name", value=uploaded_file.name)
    with col2:
        file_size_kb = round(len(file_bytes_data) / 1024, 2)
        st.metric(label="File Size", value=f"{file_size_kb} KB")

# Action Button
if st.button("Generate AI Insights 🚀", disabled=not has_input):
    if not api_key_input:
        st.error("Please enter your Gemini API Key in the left sidebar first!")
    else:
        with st.spinner("Analyzing with Gemini... Please wait."):
            try:
                client = genai.Client(api_key=api_key_input)
                contents_payload = []

                # Build system instructions depending on what inputs are available
                if uploaded_file is not None and text_query.strip() != "":
                    base_prompt = f"You are an expert analyst. Answer the user's specific request using the provided file.\n\nUser request: {text_query}"
                elif uploaded_file is not None:
                    base_prompt = "You are an expert data and document analyst. Carefully study the attached file details and content. Provide a comprehensive summary, including key themes, important details, and a structural overview."
                else:
                    base_prompt = f"You are a helpful AI assistant. Respond to the following text query:\n\n{text_query}"

                # Handle file attachments if a file exists
                if uploaded_file is not None:
                    if uploaded_file.name.endswith('.docx'):
                        docx_text = extract_text_from_docx(uploaded_file)
                        contents_payload.append(f"Document Content from Word File ({uploaded_file.name}):\n\n{docx_text}")
                    else:
                        file_part = types.Part.from_bytes(
                            data=file_bytes_data,
                            mime_type=uploaded_file.type
                        )
                        contents_payload.append(file_part)

                # Append the instructions to the text payload
                contents_payload.append(base_prompt)

                # Robust request runner with an automatic 3-pass retry for 503 limits
                max_retries = 3
                response_text = None
                
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=contents_payload
                        )
                        response_text = response.text
                        break
                        
                    except Exception as e:
                        if "503" in str(e) and attempt < max_retries - 1:
                            st.warning(f"⚠️ Google's servers are busy (Attempt {attempt + 1}/{max_retries}). Retrying in 3 seconds...")
                            time.sleep(3)
                        else:
                            st.error(f"An error occurred during AI processing: {e}")
                            break

                if response_text:
                    st.markdown("### 📊 AI Analysis Summary")
                    st.markdown(f'<div class="insight-box">{response_text}</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred during file reading: {e}")

# Info message shown if no input is present
if not has_input:
    st.info("💡 Please upload a file or type a text query above to begin.")
