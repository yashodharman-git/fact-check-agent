import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

# ==========================================
# 1. UI CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Truth Layer - Automated Factchecker",
    page_icon="🛡️",
    layout="wide"
)

# Isolated CSS configuration text string to prevent Streamlit parsing engine conflicts
css_rules = """
<style>
.reportview-container {
    background: #f8f9fa;
}
div.stButton > button:first-child {
    background-color: #ff4b4b !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1) !important;
    transition: all 0.2s !important;
    border: none !important;
}
div.stButton > button:first-child:hover {
    background-color: #e04141 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 8px -1px rgba(0,0,0,0.15) !important;
}
.custom-card {
    background-color: white;
    border: 1px solid #e9ecef;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    margin-bottom: 20px;
}
.metric-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 12px;
}
</style>
"""

# Render custom styles cleanly
st.markdown(css_rules, unsafe_with_html=True)

# Main Hero Header Module
header_html = """
<div style="background-color: white; padding: 24px; border-radius: 12px; border: 1px solid #e9ecef; margin-bottom: 25px;">
    <h1 style="margin: 0 0 8px 0; font-size: 2.3rem;">🛡️ The 'Truth Layer' Fact-Checking Agent</h1>
    <p style="color: #6c757d; margin: 0; font-size: 1.1rem;">Upload a marketing or technical PDF to automatically extract, search, and verify live factual claims against the real-time web index.</p>
</div>
"""
st.markdown(header_html, unsafe_with_html=True)

# Initialize Gemini Client securely via Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🔑 Missing Gemini API Key! Please configure 'GEMINI_API_KEY' in your Streamlit Advanced Settings / Secrets.")
    st.stop()

# ==========================================
# 2. HELPER FUNCTIONS (CORE ENGINE)
# ==========================================
def extract_text_from_pdf(uploaded_file):
    """Safely extracts visible text characters from an uploaded PDF file with structural fallbacks."""
    try:
        reader = PdfReader(uploaded_file)
        full_text = ""
        max_pages = min(len(reader.pages), 15)
        
        for i in range(max_pages):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text.strip()
    except Exception as e:
        st.error(f"Failed to read the PDF file structure: {str(e)}")
        return None

def analyze_and_verify_claims(document_text):
    """
    Uses Gemini 2.5 Flash with live Google Search Grounding to pull, 
    verify, and format ALL major technical and statistical claims.
    """
    system_instruction = (
        "You are an expert investigative fact-checker and analytics engine. "
        "Your task is to thoroughly review the provided document, extract ALL core factual claims "
        "(such as statistics, dates, financial assertions, or technical figures), and use your "
        "Google Search tool to verify if they match live, real-world data."
    )

    prompt = f"""
    Thoroughly analyze this text snippet. Extract every major technical, economic, date-based, or statistical claim present.
    Use your built-in Google Search tool to cross-reference and verify each claim against live web data.
    
    For EVERY claim you find, format your response EXACTLY like the block template below. Do not use markdown headings (###) for individual claims.
    Separate every single field with its explicit bracket
