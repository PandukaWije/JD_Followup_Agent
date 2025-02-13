import streamlit as st
import requests
import os
from dotenv import load_dotenv
import logging
import PyPDF2
import io
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
if "success" not in st.session_state:
    st.session_state.success = False
# Load environment variables
load_dotenv()

def initialize_session_state():
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'phone_number' not in st.session_state:
        st.session_state.phone_number = ""

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None

def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return None
    
    try:
        # Get the file extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return extract_text_from_pdf(uploaded_file)
        elif file_extension == 'txt':
            return str(uploaded_file.read().decode('utf-8'))
        else:
            st.error(f"Unsupported file format: {file_extension}")
            return None
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        st.error(f"Error processing file: {str(e)}")
        return None

def analyze_profile(cv, jd):
    try:
        response = requests.post(
            "http://localhost:8000/analyze-profile",
            json={"cv": cv, "jd": jd}
        )
        if response.status_code == 200:
            st.session_state.analysis_result = response.json()
            st.session_state.analysis_complete = True
            return True
        else:
            st.error(f"Error in analysis: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        return False

def send_telegram_followup():
    try:
        # Save questions to file
        questions_list = []
        for category in st.session_state.analysis_result['questions'].values():
            questions_list.extend(category)
        
        with open("followup_questions.txt", "w") as f:
            for question in questions_list:
                f.write(f"{question}\n")
        
        # Run Telegram script
        logger.info("Starting Telegram script")
        os.system('python telegram.py')
        st.session_state.success = True
        st.switch_page("pages/Response_Analysis.py")
        return True
    except Exception as e:
        logger.error(f"Error sending follow-up: {str(e)}")
        return False

def job_followup_interface():
    st.header("Job Application Follow-up")
    
    # Initialize session state
    initialize_session_state()
    
    # Input fields
    # st.session_state.phone_number = st.text_input(
    #     "Candidate Phone Number (with country code)", 
    #     value=st.session_state.phone_number,
    #     placeholder="+1234567890"
    # )
    
    # cv = st.text_area("Paste CV", height=200)
    # jd = st.text_area("Paste Job Description", height=200)
    # File upload fields
    cv_file = st.file_uploader("Upload CV (PDF or TXT)", type=['pdf', 'txt'])
    jd_file = st.file_uploader("Upload Job Description (PDF or TXT)", type=['pdf', 'txt'])
    
    # Preview extracted text
    cv = None
    jd = None
    
    if cv_file:
        cv = extract_text_from_file(cv_file)
        with st.expander("Preview CV Text"):
            st.text(cv[:500] + "..." if cv and len(cv) > 500 else cv)
    
    if jd_file:
        jd = extract_text_from_file(jd_file)
        with st.expander("Preview Job Description Text"):
            st.text(jd[:500] + "..." if jd and len(jd) > 500 else jd)
    
    # Analysis button
    if not st.session_state.analysis_complete:
        if st.button("Analyze Compatibility") and cv and jd:
            with st.spinner("Analyzing compatibility..."):
                if analyze_profile(cv, jd):
                    st.rerun()
    
    # Display results if analysis is complete
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Compatibility Score", f"{result['compatibility_score']}%")
        
        with col2:
            if result['compatibility_score'] >= 70:
                st.success("High Compatibility!")
            elif result['compatibility_score'] >= 50:
                st.warning("Moderate Compatibility")
            else:
                st.error("Low Compatibility")
        
        # Display detailed analysis sections
        with st.expander("💪 Strengths", expanded=True):
            for strength in result['strengths']:
                st.write(f"• {strength}")
        
        with st.expander("🔍 Areas to Explore"):
            for concern in result['potential_concerns']:
                st.write(f"• {concern}")
        
        with st.expander("👥 Work Style Indicators"):
            for indicator in result['work_style_indicators']:
                st.write(f"• {indicator}")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📧 Send Follow-up", key="send_followup"):
                # if not st.session_state.phone_number:
                #     st.error("Please enter candidate's phone number!")
                # else:
                    with st.spinner("Sending follow-up questions..."):
                        if send_telegram_followup():
                            st.success("Follow-up questions sent successfully!")
                        else:
                            st.error("Failed to send follow-up questions.")
        
        with col2:
            if st.button("📅 Schedule Call"):
                st.success("Interview scheduling email sent!")
        
        # Reset button
        if st.button("Start New Analysis"):
            st.session_state.analysis_complete = False
            st.session_state.analysis_result = None
            st.rerun()

def main():
    st.title("AI Recruitment Assistant")
    
    mode = st.sidebar.selectbox(
        "Select Mode",
        ["Job Application Follow-up", "Interview Preparation"]
    )
    
    if mode == "Job Application Follow-up":
        job_followup_interface()
    else:
        st.info("Interview Preparation feature coming soon!")

if __name__ == "__main__":
    main()