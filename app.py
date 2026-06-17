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
        # Read a max of 15 pages to keep larger files from hitting processing timeouts
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
        "and use your Google Search tool to verify if they are accurate against current live data. "
        "Format your entire response clearly using the marker [CLAIM_START] before each claim, "
        "and separate fields with [STATUS], [EVIDENCE], and [CLAIM_END]."
    )

    prompt = f"""
    Analyze this text snippet. Extract exactly 3 major technical, economic, date-based, or statistical claims.
    Use your built-in Google Search tool to check them against live web data.
    
    Format your response EXACTLY like this for each of the 3 claims:
    
    [CLAIM_START]
    [TEXT] Write the exact wording or specific data point found in the document here.
    [STATUS] Write either Verified or Inaccurate or False here.
    [EVIDENCE] Explain what the live internet data actually states. Provide current statistics as proof.
    [CLAIM_END]

    Document Text to Analyze:
    \"\"\"{document_text[:6000]}\"\"\"
    """

    try:
        # Enable Live Google Search Grounding natively
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
    """Parses custom tag system into structured content block listings."""
    claims_list = []
    if not response_text:
        return claims_list
        
    raw_blocks = response_text.split("[CLAIM_START]")
    for block in raw_blocks:
        if "[CLAIM_END]" in block:
            try:
                # Isolate the data strings programmatically
                text_part = block.split("[TEXT]")[1].split("[STATUS]")[0].strip()
                status_part = block.split("[STATUS]")[1].split("[EVIDENCE]")[0].strip()
                evidence_part = block.split("[EVIDENCE]")[1].split("[CLAIM_END]")[0].strip()
                
                # Dynamic normalization sanitization
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
                parsed_claims = parse_text_response(raw_response)
            
            if parsed_claims:
                st.balloons()
                st.markdown("#### System Evaluation Matrix:")
                
                for idx, claim in enumerate(parsed_claims, 1):
                    curr_status = claim["status"]
                    claim_text = claim["claim_text"]
                    evidence = claim["source_evidence"]
                    
                    # Assigned fixed, matched variables to prevent template crashes
                    if curr_status == "Verified":
                        color_hex = "#d4edda"
                        text_hex = "#155724"
                        border_hex = "#c3e6cb"
                        badge = "✅ VERIFIED"
                    elif curr_status == "Inaccurate":
                        color_hex = "#fff3cd"
                        text_hex = "#856404"
                        border_hex = "#ffeeba"
                        badge = "⚠️ INACCURATE / OUTDATED"
                    else:
                        color_hex = "#f8d7da"
                        text_hex = "#721c24"
                        border_hex = "#f5c6cb"
                        badge = "❌ FALSE"
                    
                    st.markdown(f"""
                    <div style="background-color: {color_hex}; color: {text_hex}; border: 1px solid {border_hex}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin-top: 0;">Claim #{idx}: {badge}</h4>
                        <p><strong>Extracted From PDF:</strong> "<em>{claim_text}</em>"</p>
                        <p><strong>Live Web Context & Evidence:</strong> {evidence}</p>
                    </div>
                    """, unsafe_with_html=True)
            else:
                if raw_response:
                    st.markdown("#### Live Verification Logs:")
                    st.info(raw_response)
                else:
                    st.error("Failed to generate a valid validation matrix structure. Please try again.")
    else:
        st.write("Upload a target PDF document on the left panel to initialize the live analysis thread.")
