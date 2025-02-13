import streamlit as st
import sqlite3
from crewai import Agent, Task, Crew, Process
import json
from typing import List, Dict
import pandas as pd

with open('jd.txt', 'r') as f:
    job_description = f.read()

class ResponseAnalysisAgent:
    def __init__(self):
        self.analyst = Agent(
            role="Interview Response Analyst",
            goal="Analyze candidate responses to assess communication skills, clarity, and response quality",
            backstory="""You are an expert in analyzing interview responses and communication patterns. 
            You excel at identifying key themes, assessing response quality, and providing actionable insights 
            from candidate answers. Your analysis helps determine candidate suitability and areas for further discussion.""",
            verbose=True
        )

class ResponseAnalysisTasks:
    @staticmethod
    def analyze_responses(agent, chat_history: str) -> Task:
        return Task(
            description=f"""by analyze the following Job follow up Q and A responses with given JD, provide a detailed assessment.
            
            Job Description : {job_description}
            Chat History: {chat_history}
            
            Provide your analysis in the following JSON format:
            {{
                "overall_score": <score between 0-100>,
                "key_strengths": [<list of 2-3 communication strengths>],
                "areas_of_improvement": [<list of 1-2 areas to improve>],
                "response_quality": {{
                    "clarity": <score between 0-100>,
                    "completeness": <score between 0-100>,
                    "relevance": <score between 0-100>
                }},
                "themes_identified": [<list of 2-3 recurring themes>],
                "recommendations_for_hiring_manager": [<conclutions for hiring manager with special note if needed>],
            }}
            
            Base your analysis on:
            - Response completeness
            - Communication clarity
            - Relevance to questions
            - Consistent themes
            - Areas needing clarification""",
            expected_output="A JSON string containing the analysis of candidate responses including scores, strengths, themes, and recommendations",
            agent=agent
        )

def get_chat_history(db_path: str = 'interviews.db') -> List[Dict]:
    conn = sqlite3.connect(db_path)
    try:
        # Read chat history into a pandas DataFrame
        query = "SELECT * FROM chat_history ORDER BY timestamp"
        df = pd.read_sql_query(query, conn)
        return df.to_dict('records')
    finally:
        conn.close()

def analyze_responses(chat_history: List[Dict]) -> dict:
    # Initialize agent and task
    agent = ResponseAnalysisAgent().analyst
    tasks = ResponseAnalysisTasks()
    
    # Format chat history for analysis
    formatted_history = json.dumps(chat_history, indent=2)
    
    # Create crew with single task
    analysis_crew = Crew(
        agents=[agent],
        tasks=[tasks.analyze_responses(agent, formatted_history)],
        process=Process.sequential,
        verbose=True
    )
    
    # Run analysis
    result = analysis_crew.kickoff()
    
    try:
        # Clean up potential markdown formatting
        cleaned_result = str(result).replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_result)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse analysis result",
            "raw_content": str(result)
        }
    
def cleanup_database(db_path: str = 'interviews.db') -> bool:
    """
    Clean up the database by archiving completed interviews and removing old data.
   
    Args:
        db_path (str): Path to the SQLite database
       
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
       
        # Create archive tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS archived_questions (
            candidate_id TEXT PRIMARY KEY,
            phone_number TEXT,
            questions TEXT,
            created_at TIMESTAMP,
            status TEXT,
            interview_complete BOOLEAN,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
       
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS archived_chat_history (
            id INTEGER PRIMARY KEY,
            candidate_id TEXT,
            question TEXT,
            answer TEXT,
            timestamp TIMESTAMP,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
       
        # Archive completed interviews
        cursor.execute('''
        INSERT INTO archived_questions
        SELECT *, CURRENT_TIMESTAMP
        FROM questions
        WHERE status = 'completed' OR interview_complete = TRUE
        ''')
       
        # Archive associated chat history
        cursor.execute('''
        INSERT INTO archived_chat_history
        SELECT ch.*, CURRENT_TIMESTAMP
        FROM chat_history ch
        INNER JOIN questions q ON ch.candidate_id = q.candidate_id
        WHERE q.status = 'completed' OR q.interview_complete = TRUE
        ''')
       
        # Delete archived records from original tables
        cursor.execute('''
        DELETE FROM chat_history
        WHERE candidate_id IN (
            SELECT candidate_id
            FROM questions
            WHERE status = 'completed' OR interview_complete = TRUE
        )
        ''')
       
        cursor.execute('''
        DELETE FROM questions
        WHERE status = 'completed' OR interview_complete = TRUE
        ''')
       
        conn.commit()
       
        # Vacuum the database to reclaim space
        cursor.execute('VACUUM')
       
        conn.close()
        return True
       
    except Exception as e:
        print(f"Error during database cleanup: {e}")
        return False
 
def main():
    st.title("Interview Response Analysis Dashboard")   
    db_path = 'interviews.db'
    
    try:
        if st.session_state.success==True:
            # Get chat history
            chat_history = get_chat_history(db_path)
            
            if not chat_history:
                st.warning("No chat history found in the database.")
                return
            
            # Display raw chat history in an expander
            with st.expander("View Raw Chat History"):
                st.dataframe(pd.DataFrame(chat_history))
            
            # Analyze button
            if st.button("Analyze Responses"):
                with st.spinner("Analyzing responses..."):
                    analysis_result = analyze_responses(chat_history)
                    
                    if "error" in analysis_result:
                        st.error(f"Analysis failed: {analysis_result['error']}")
                        return
                    
                    # Display results in organized sections
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Relevance Score", f"{analysis_result['response_quality']['relevance']}%")
                    with col2:
                        st.metric("Clarity Score", f"{analysis_result['response_quality']['clarity']}%")
                    with col3:
                        st.metric("Completeness Score", f"{analysis_result['response_quality']['completeness']}%")

                    st.divider()
                    
                    # Strengths and Improvements
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("💪 Key Strengths")
                        for strength in analysis_result['key_strengths']:
                            st.write(f"• {strength}")
                    
                    with col2:
                        st.subheader("🎯 Areas for Improvement")
                        for area in analysis_result['areas_of_improvement']:
                            st.write(f"• {area}")

                    st.divider()
                    
                    
                    st.subheader("📝 Recommendation")
                    for recommendations in analysis_result['recommendations_for_hiring_manager']:
                        st.write(f"• {recommendations}")

                    st.metric("Overall Score", f"{analysis_result['overall_score']}%")

                    if analysis_result['overall_score'] >= 75:
                        st.success("Recomended for the interview") 
                    else:
                        st.warning("Candidate did not meet the expectations")
                    cleanup_database(db_path)    
        else:
            st.warning("Please ensure that the Initial Screening Process is done for the candidate")    
                
    except Exception as e:
        st.error(f"Error accessing database: {str(e)}")
        st.info("Please ensure the interviews.db file is present in the same directory or upload it using the file uploader.")

if __name__ == "__main__":
    main()
