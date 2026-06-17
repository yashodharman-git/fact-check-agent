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

# FIXED: Removed f-string declaration from raw CSS strings to avoid Streamlit template parsing engine crashes
st.markdown("""
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
""", unsafe_with_html=True)

# Hero Header Module
st.markdown("""
    <div style="background-color: white; padding: 24px; border-radius: 12px; border: 1px solid #e9ecef; margin-bottom: 25px;">
        <h1 style="margin: 0 0 8px 0; font-size: 2.3rem;">🛡️ The 'Truth Layer' Fact-Checking Agent</h1>
        <p style="color: #6c757d; margin: 0; font-size: 1.1rem;">Upload a marketing or technical PDF to automatically extract, search, and verify live factual claims against the real-time web index.</p>
    </div>
""", unsafe_with_html=True)

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
    Separate every single field with its explicit bracketed label like this:

    [CLAIM_START]
    [TEXT] Write the exact claim, stat, date, or figure extracted from the PDF here.
    [STATUS] Write exactly ONE of these words: Verified, Inaccurate, or False.
    - Use 'Verified' if it matches live real-world data.
    - Use 'Inaccurate' if it contains outdated statistics or minor discrepancies.
    - Use 'False' if there is no evidence found or if it is a complete lie.
    [EVIDENCE] Explain what the live internet data discovered. Provide real-world current statistics, context, and proof.
    [CLAIM_END]

    Document Text to Analyze:
    \"\"\"{document_text[:8000]}\"\"\"
    """

    try:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        
        return response.text
    except Exception as e:
        st.error(f"Error communicating with AI verification engine: {str(e)}")
        return None

def parse_text_response(response_text):
    """Safely extracts data segments without breaking on structural changes or missing metrics."""
    claims_list = []
    if not response_text:
        return claims_list
        
    raw_blocks = response_text.split("[CLAIM_START]")
    for block in raw_blocks:
        if "[CLAIM_END]" in block:
            try:
                text_part = block.split("[TEXT]")[1].split("[STATUS]")[0].strip()
                status_part = block.split("[STATUS]")[1].split("[EVIDENCE]")[0].strip()
                evidence_part = block.split("[EVIDENCE]")[1].split("[CLAIM_END]")[0].strip()
                
                # Normalize values to safeguard against rendering exceptions
                status_clean = "False"
                if "Verified" in status_part:
                    status_clean = "Verified"
                elif "Inaccurate" in status_part:
                    status_clean = "Inaccurate"
                    
                claims_list.append({
                    "claim_text": text_part,
                    "status": status_clean,
                    "source_evidence": evidence_part
                })
            except Exception:
                continue
    return claims_list

# ==========================================
# 3. INTERFACE RENDERING & ORCHESTRATION
# ==========================================
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown('<div class="custom-card">', unsafe_with_html=True)
    st.subheader("📥 Document Dropzone")
    uploaded_file = st.file_uploader("Choose a PDF document", type=["pdf"], label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f"Successfully loaded: {uploaded_file.name}")
        with st.spinner("Parsing document structure..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
        
        if extracted_text:
            st.info(f"📊 Character metric count: {len(extracted_text)} identified.")
            with st.expander("👀 View Extracted Raw Text"):
                st.text_area("Raw Text Content", extracted_text, height=250, disabled=True)
    st.markdown('</div>', unsafe_with_html=True)

with col2:
    st.markdown('<div class="custom-card">', unsafe_with_html=True)
    st.subheader("📊 Live 'Truth Layer' Analysis Dashboard")
    
    if uploaded_file and extracted_text:
        if st.button("🚀 Execute Automated Factcheck", type="primary"):
            
            # FIXED: Custom loading element formatted without using curly brackets inside f-string blocks
            loading_placeholder = st.empty()
            loading_placeholder.markdown
