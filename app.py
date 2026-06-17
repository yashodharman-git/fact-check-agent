import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types
import json

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
    """Safely extracts all visible text characters from an uploaded PDF file."""
    try:
        reader = PdfReader(uploaded_file)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text.strip()
    except Exception as e:
        st.error(f"Failed to read the PDF file structure: {str(e)}")
        return None

def analyze_and_verify_claims(document_text):
    """
    Uses Gemini 2.5 Flash to pull exactly 3 key claims and concurrently
    verifies them utilizing integrated live Google Search Grounding.
    """
    # Define a bulletproof instruction telling the model how to parse and ground the data
    system_instruction = (
        "You are an expert investigative fact-checker and analytics engine. "
        "Your task is to review the provided text, extract exactly 3 core distinct factual claims, "
        "and immediately use your Google Search tool to verify if they are accurate against current live data. "
        "You must return the final analysis formatted strictly as a JSON object containing a 'claims' array."
    )

    prompt = f"""
    Analyze this text snippet. Extract exactly 3 major technical, economic, date-based, or statistical claims.
    Use your built-in Google Search tool to check them against live web data.
    
    Return the output strictly matching this JSON schema blueprint:
    {{
        "claims": [
            {{
                "claim_text": "The exact wording or specific data point found in the document",
                "status": "Verified" or "Inaccurate" or "False",
                "source_evidence": "Explain what the live internet data actually states. Provide proof or current statistics.",
                "confidence_score": "0-100%"
            }}
        ]
    }}

    Document Text to Analyze:
    \"\"\"{document_text[:6000]}\"\"\"
    """

    try:
        # Enable Live Google Search Grounding natively inside the generation request
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
            temperature=0.1
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        
        # Parse output data cleanly
        return json.loads(response.text)
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
            # Preview box for user sanity
            with st.expander("👀 View Extracted Raw Text"):
                st.text_area("Raw Text Content", extracted_text, height=250, disabled=True)
        else:
            st.warning("The PDF appears to be entirely blank or contains unreadable scanned imagery.")

with col2:
    st.subheader("📊 Live 'Truth Layer' Analysis Dashboard")
    
    if uploaded_file and extracted_text:
        if st.button("🚀 Execute Automated Factcheck", type="primary"):
            with st.spinner("Extracting claims and querying live search engines..."):
                results = analyze_and_verify_claims(extracted_text)
            
            if results and "claims" in results:
                st.balloons()
                st.markdown("#### System Evaluation Matrix:")
                
                # Loop over the response list and render color-coded output UI blocks
                for idx, claim in enumerate(results["claims"], 1):
                    status = claim.get("status", "False")
                    claim_text = claim.get("claim_text", "N/A")
                    evidence = claim.get("source_evidence", "No validating data returned.")
                    confidence = claim.get("confidence_score", "N/A")
                    
                    # Determine styling dynamically based on status criteria
                    if status == "Verified":
                        color_hex = "#d4edda"
                        text_hex = "#155724"
                        border_hex = "#c3e6cb"
                        badge = "✅ VERIFIED"
                    elif status == "Inaccurate":
                        color_hex = "#fff3cd"
                        text_hex = "#856404"
                        border_hex = "#ffeeba"
                        badge = "⚠️ INACCURATE / OUTDATED"
                    else:
                        color_hex = "#f8d7da"
                        text_hex = "#721c24"
                        border_hex = "#f5c6cb"
                        badge = "❌ FALSE"
                    
                    # Clean Markdown rendering block injection
                    st.markdown(f"""
                    <div style="background-color: {color_hex}; color: {text_hex}; border: 1px solid {border_hex}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="margin-top: 0;">Claim #{idx}: {badge}</h4>
                        <p><strong>Extracted From PDF:</strong> "<em>{claim_text}</em>"</p>
                        <p><strong>Live Web Context & Evidence:</strong> {evidence}</p>
                        <p style="margin-bottom: 0;"><small>System Accuracy Confidence: {confidence}</small></p>
                    </div>
                    """, unsafe_with_html=True)
            else:
                st.error("Failed to generate a valid validation matrix structure. Please try again.")
    else:
        st.write("Upload a target PDF document on the left panel to initialize the live analysis thread.")
