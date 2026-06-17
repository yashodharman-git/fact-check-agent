# Truth Layer - Automated Fact-Checking Agent

An AI-driven automated evaluation engine designed to protect brands from outdated or hallucinated information by cross-referencing document claims against live web search grounding. Developed as a core technical solution for the CogCulture PM assessment.

## Key Product Features
**Automated Extraction:** Intelligently reads multi-page PDF documents and extracts core verifiable claims (stats, dates, financial figures).
* **Live Search Grounding:** Powers real-time verifications using the `gemini-2.5-flash` model natively connected to live Google Search engines.
**Color-Coded Matrix:** Displays validation states with intuitive visual cues: Green (Verified), Yellow (Inaccurate), and Red (False).

## Technical Stack
**Frontend Interface:** Streamlit Framework
**Core Intelligence Engine:** Google GenAI SDK (`gemini-2.5-flash`)
**Real-time Data Access:** Google Search Tool Grounding API
**Parsing Layer:** PyPDF Document Extraction Utility
