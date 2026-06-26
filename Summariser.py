import os
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import xml.etree.ElementTree as ET
import time
from google import genai
from google.genai import types
from PIL import Image
import io

# PDF Preview support setup
try:
    from pdf2image import convert_from_bytes
    PDF_PREVIEW_SUPPORTED = True
except ImportError:
    PDF_PREVIEW_SUPPORTED = False

# Initialize Session State for app routing mode
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

# 1. Page Configuration & Custom "Bright & Appealing" Styling
st.set_page_config(
    page_title="AI Insight Hub",
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
    
    /* Bright, appealing Action Button Styling */
    div.stButton > button {
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
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 78, 80, 0.6) !important;
    }
    
    /* Specific styling for the large selection buttons on landing page */
    .landing-box {
        background-color: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 20px;
        border-top: 4px solid #3b82f6;
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
    
    /* Preview box framing */
    .preview-container {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Floating "Go to Top" Button Component (HTML + JS + CSS)
components.html(
    """
    <button onclick="scrollToTop()" id="scrollTopBtn" title="Go to top">▲</button>
    
    <script>
    var mybutton = document.getElementById("scrollTopBtn");
    window.parent.onscroll = function() { scrollFunction() };
    function scrollFunction() {
        if (window.parent.pageYOffset > 300) {
            mybutton.style.display = "block";
        } else {
            mybutton.style.display = "none";
        }
    }
    function scrollToTop() {
        window.parent.scrollTo({ top: 0, behavior: 'smooth' });
    }
    </script>
    
    <style>
    #scrollTopBtn {
        display: none; 
        position: fixed; 
        bottom: 30px; 
        right: 30px; 
        z-index: 99999; 
        border: none; 
        outline: none; 
        background: linear-gradient(45deg, #ff4e50, #f9d423); 
        color: white; 
        cursor: pointer; 
        padding: 15px; 
        border-radius: 50%; 
        font-size: 18px; 
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(255, 78, 80, 0.4);
        transition: all 0.3s ease;
        width: 50px;
        height: 50px;
    }
    #scrollTopBtn:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(255, 78, 80, 0.6);
    }
    </style>
    """,
    height=0,
)

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

# Helper function to handle content generation with 503 retries
def call_gemini_with_retry(client, contents_payload):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents_payload
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                st.warning(f"⚠️ Google's servers are busy (Attempt {attempt + 1}/{max_retries}). Retrying...")
                time.sleep(3)
            else:
                st.error(f"AI Processing error: {e}")
                return None

# UI Header Layout
st.title("✨ AI Insight Hub")

# 🔑 Dynamic Sidebar API Key Input
with st.sidebar:
    st.header("🔑 Authentication")
    api_key_input = st.text_input("Enter Gemini API Key", type="password", placeholder="AIzaSy...")
    st.markdown("[Get a free key from Google AI Studio](https://google.com)")

# ==================== ROUTING LOGIC ====================

# SCREEN 1: LANDING SELECTION
if st.session_state.app_mode is None:
    st.markdown("### Select an AI Assistant Mode to get started:")
    st.write("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="landing-box"><h3>📁 File Analyst</h3><p>Upload files, view previews, and extract structured summaries.</p></div>', unsafe_allow_html=True)
        if st.button("Open File Analyst Studio", key="go_to_file"):
            st.session_state.app_mode = "file_studio"
            st.rerun()
            
    with col2:
        st.markdown('<div class="landing-box"><h3>🔍 General Search</h3><p>Ask freeform questions or assign open-ended tasks directly.</p></div>', unsafe_allow_html=True)
        if st.button("Open General AI Search", key="go_to_search"):
            st.session_state.app_mode = "general_search"
            st.rerun()

# SCREEN 2A: FILE STUDIO WORKSPACE
elif st.session_state.app_mode == "file_studio":
    if st.button("← Back to Mode Selection", key="back_from_file"):
        st.session_state.app_mode = None
        st.rerun()
        
    st.markdown("## 📁 File Insight Studio")
    st.markdown("Upload a document, image, or data file to instantly preview it and get a smart AI summary.")
    
    uploaded_file = st.file_uploader(
        "Choose a file", 
        type=["pdf", "txt", "csv", "png", "jpg", "jpeg", "docx"],
        key="file_uploader"
    )

    if uploaded_file is not None:
        st.success(f"🎉 **File successfully uploaded!**")
        file_bytes_data = uploaded_file.getvalue()
        
        # --- PREVIEW AREA ---
        st.markdown("### 👁️ File Preview")
        with st.container():
            st.markdown('<div class="preview-container">', unsafe_allow_html=True)
            
            if uploaded_file.type.startswith("image/"):
                image = Image.open(io.BytesIO(file_bytes_data))
                st.image(image, caption="Uploaded Image Preview", use_container_width=True)
            
            elif uploaded_file.name.endswith(".pdf"):
                if PDF_PREVIEW_SUPPORTED:
                    try:
                        pages = convert_from_bytes(file_bytes_data, first_page=1, last_page=1)
                        if pages:
                            st.image(pages, caption="PDF Page 1 Preview", use_container_width=True)
                    except Exception as e:
                        st.info("💡 Could not render visual layout preview for this PDF.")
                else:
                    st.info("💡 PDF visual preview requires the `pdf2image` library package.")
            
            elif uploaded_file.name.endswith((".txt", ".csv")):
                try:
                    text_preview = file_bytes_data[:1000].decode("utf-8")
                    st.text_area("File Snippet Preview", text_preview, height=150, disabled=True)
                except Exception:
                    st.info("📝 Binary text data cannot be previewed directly.")
            
            elif uploaded_file.name.endswith(".docx"):
                docx_preview_text = extract_text_from_docx(io.BytesIO(file_bytes_data))
                st.text_area("Document Text Preview", docx_preview_text[:1000], height=150, disabled=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
        # --- END OF PREVIEW AREA ---

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="File Name", value=uploaded_file.name)
        with col2:
            file_size_kb = round(len(file_bytes_data) / 1024, 2)
            st.metric(label="File Size", value=f"{file_size_kb} KB")

        user_prompt = st.text_input(
            "Is there anything specific you want the AI to look for?", 
            placeholder="e.g., Summarize the top 3 takeaways...",
            key="file_prompt"
        )
if st.button("Generate AI Insights 🚀", key="file_btn"):
if not api_key_input:
