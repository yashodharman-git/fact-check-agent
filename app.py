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
                
                # Check overall dataset health to display top header banner
                all_statuses = [c["status"] for c in parsed_claims]
                if "False" in all_statuses:
                    st.error("🚨 ALERT: Critical anomalies or completely false claims discovered in document text structure.")
                elif "Inaccurate" in all_statuses:
                    st.warning("⚠️ NOTICE: Outdated data strings or technical inconsistencies identified.")
                else:
                    st.success("✨ VALIDATED: All extracted document metrics successfully match live index data.")
                
                # Render clean, customized markup panels for each claim found
                for idx, claim in enumerate(parsed_claims, 1):
                    curr_status = claim["status"]
                    claim_text = claim["claim_text"]
                    evidence = claim["source_evidence"]
                    
                    if curr_status == "Verified":
                        st.success(f"**Claim #{idx}: VERIFIED**\n\n* **Extracted From PDF:** *\"{claim_text}\"*\n\n* **Live Search Evidence:** {evidence}")
                    elif curr_status == "Inaccurate":
                        st.warning(f"**Claim #{idx}: INACCURATE**\n\n* **Extracted From PDF:** *\"{claim_text}\"*\n\n* **Live Search Evidence:** {evidence}")
                    else:
                        st.error(f"**Claim #{idx}: FALSE**\n\n* **Extracted From PDF:** *\"{claim_text}\"*\n\n* **Live Search Evidence:** {evidence}")
            else:
                if raw_response:
                    st.markdown("#### Live Verification Matrix Logs:")
                    st.info(raw_response)
                else:
                    st.error("Failed to extract data blocks. Please confirm your input data structural formatting and re-run.")
    else:
        st.write("Upload a target PDF document on the left panel to initialize the live analysis thread.")
