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
    
    /* Card/Container styling for file uploader and results */
    .stFileUploader {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 2px dashed #3b82f6;
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
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to extract text directly from a Word (.docx) file
def extract_text_from_docx(file_io):
    try:
        with zipfile.ZipFile(file_io) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text_elements = root.findall('.//w:t', namespaces)
            return "".join([t.text for t in text_elements if t.text])
    except Exception as e:
        return f"Error extracting Word text: {str(e)}"

# 2. Initialize the official Gemini Client using Streamlit Cloud Secrets
try:
    # Check if key exists inside Streamlit Cloud Advanced Settings
    if "GEMINI_API_KEY" in st.secrets:
        MY_API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        # Fallback for local testing environmental variables
        MY_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # If no key found in secrets, fallback to hardcoded string for immediate check
    if not MY_API_KEY or MY_API_KEY == "PASTE_YOUR_KEY_HERE":
        # =========================================================================
        # 🔑 OPTIONAL LOCAL KEY PASTE 🔑
        # If testing locally, you can temporarily swap out the string placeholder below.
        # =========================================================================
        MY_API_KEY = "PASTE_YOUR_KEY_HERE"

    if not MY_API_KEY or MY_API_KEY == "PASTE_YOUR_KEY_HERE":
        st.error("🔑 **API Key Missing!** Please add your `GEMINI_API_KEY` inside your Streamlit Cloud Workspace secrets dashboard.")
        st.stop()
        
    client = genai.Client(api_key=MY_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize GenAI Client: {e}")
    st.stop()

# 3. UI Layout
st.title("✨ AI File Insight Studio")
st.markdown("Upload a document, image, or data file to instantly extract its key details and get a smart AI summary.")
st.write("---")

# File Uploader Widget
uploaded_file = st.file_uploader(
    "Choose a file (PDF, TXT, Images, CSV, Word Documents, etc.)", 
    type=["pdf", "txt", "csv", "png", "jpg", "jpeg", "docx"]
)

if uploaded_file is not None:
    st.success(f"🎉 **File successfully uploaded!**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="File Name", value=uploaded_file.name)
    with col2:
        file_size_kb = round(len(uploaded_file.getvalue()) / 1024, 2)
        st.metric(label="File Size", value=f"{file_size_kb} KB")

    # Custom prompt input for targeted analysis
    user_prompt = st.text_input(
        "Is there anything specific you want the AI to look for?", 
        placeholder="e.g., Summarize the top 3 takeaways, find action items, etc. (Leave blank for general summary)"
    )

    # Action Button
    if st.button("Generate AI Insights 🚀"):
        with st.spinner("Analyzing file content with Gemini... Please wait."):
            try:
                # Construct the prompt instructions
                base_prompt = "You are an expert data and document analyst. Carefully study the attached file details and content. Provide a comprehensive summary, including key themes, important details, and a structural overview."
                if user_prompt:
                    base_prompt += f"\n\nUser specific request: {user_prompt}"

                # ROUTING BY FILE TYPE
                if uploaded_file.name.endswith('.docx'):
                    docx_text = extract_text_from_docx(uploaded_file)
                    contents_payload = [
                        f"Document Content from Word File ({uploaded_file.name}):\n\n{docx_text}",
                        base_prompt
                    ]
                else:
                    file_bytes = uploaded_file.read()
                    file_mime = uploaded_file.type
                    
                    file_part = types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=file_mime
                    )
                    contents_payload = [file_part, base_prompt]

                # Robust request runner with an automatic 3-pass retry for 503 limits
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=contents_payload
                        )
                        # If successful, render output styling and exit the retry cycle
                        st.markdown("### 📊 AI Analysis Summary")
                        st.markdown(f'<div class="insight-box">{response.text}</div>', unsafe_allow_html=True)
                        break
                        
                    except Exception as e:
                        # Handle temporary server load (503) gracefully
                        if "503" in str(e) and attempt < max_retries - 1:
                            st.warning(f"⚠️ Google's servers are busy (Attempt {attempt + 1}/{max_retries}). Retrying in 3 seconds...")
                            time.sleep(3)
                        else:
                            # Throw error if retries are exhausted or it's a completely different issue
                            st.error(f"An error occurred during AI processing: {e}")
                            break

            except Exception as e:
                st.error(f"An error occurred during file reading: {e}")

else:
    st.info("💡 Please upload a file above to begin the analysis.")
