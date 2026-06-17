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

st.title("🛡️ The 'Truth Layer' Fact-Checking Agent")
st.markdown("### Upload a marketing or technical PDF to automatically extract, search, and verify live factual claims.")
st.write("---")

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
    Uses Gemini 2.5 Flash with live Google Search Grounding to pull and verify exactly 3 claims.
    """
    system_instruction = (
        "You are an expert investigative fact-checker and analytics engine. "
        "Your task is to review the provided text, extract exactly 3 core distinct factual claims, "
        "and use your Google Search tool to verify if they are accurate against current live data."
    )

    prompt = f"""
    Analyze this text snippet. Extract exactly 3 major technical, economic, date-based, or statistical claims.
    Use your built-in Google Search tool to check them against live web data.
    
    Format your response cleanly using markdown headings for each claim. Inside each claim section, 
    prominently include one of these exact text labels so the interface highlights it correctly:
    - **VERIFICATION STATUS: VERIFIED**
    - **VERIFICATION STATUS: INACCURATE**
    - **VERIFICATION STATUS: FALSE**

    Include detailed sections explaining what the text claimed vs what live Google Search grounding discovered.
    
    Document Text to Analyze:
    \"\"\"{document_text[:6000]}\"\"\"
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

# ==========================================
# 3. INTERFACE RENDERING & ORCHESTRATION
# ==========================================
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.subheader("📥 Document Dropzone")
    uploaded_file = st.file_uploader("Choose a PDF document", type=["pdf"])
    
    if uploaded_file:
        st.success(f"Successfully loaded: {uploaded_file.name}")
        with st.spinner("Parsing document structure..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
        
        if extracted_text:
            st.info(f"Character metric count: {len(extracted_text)} characters identified.")
            with st.expander("👀 View Extracted Raw Text"):
                st.text_area("Raw Text Content", extracted_text, height=250, disabled=True)

with col2:
    st.subheader("📊 Live 'Truth Layer' Analysis Dashboard")
    
    if uploaded_file and extracted_text:
        if st.button("🚀 Execute Automated Factcheck", type="primary"):
            with st.spinner("Extracting claims and querying live search engines..."):
                raw_response = analyze_and_verify_claims(extracted_text)
            
            if raw_response:
                st.balloons()
                st.markdown("#### System Evaluation Matrix:")
                
                # Dynamic background styling box based on overall content findings
                if "STATUS: FALSE" in raw_response:
                    st.error("🚨 ALERT: Critical anomalies or false claims discovered in document text structure.")
                elif "STATUS: INACCURATE" in raw_response:
                    st.warning("⚠️ NOTICE: Outdated data strings or inconsistencies identified.")
                else:
                    st.success("✨ VALIDATED: Document integrity checked against live index metrics.")
                
                # Render the full, un-chopped analysis output window
                st.markdown(raw_response)
            else:
                st.error("Failed to generate an evaluation matrix. Please check your configuration and try again.")
    else:
        st.write("Upload a target PDF document on the left panel to initialize the live analysis thread.")
