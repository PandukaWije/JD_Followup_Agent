# tasks.py
from crewai import Task
import json

# tasks.py
from crewai import Task
import json

class JobTasks:
    @staticmethod
    def analyze_profile(agent, cv: str, jd: str) -> Task:
        return Task(
            description=f"""You are analyzing a CV against a job description to determine workplace compatibility.
            
            CV: {cv}
            JD: {jd}
            
            Provide a detailed analysis in the following JSON format:
            {{
                "compatibility_score": <score between 0-100>,
                "strengths": [<list of 2-3 key strengths>],
                "potential_concerns": [<list of 1-2 areas to explore>],
                "work_style_indicators": [<list of 2-3 work style observations>],
                "culture_fit_aspects": [<list of 2-3 cultural alignment points>],
                "adaptability_signals": [<list of 1-2 adaptability indicators>],
                "next_steps": "<recommended next action>"
            }}
            
            Format your response EXACTLY as shown above, with valid JSON.
            Base the compatibility score on:
            - Alignment of past experiences with job requirements
            - Evidence of cultural fit
            - Demonstrated adaptability
            - Team collaboration indicators
            
            For next_steps, recommend one of:
            - "Schedule immediate follow-up interview" (for scores 80+)
            - "Schedule initial screening call" (for scores 60-79)
            - "Review additional candidates before proceeding" (for scores below 60)""",
            expected_output="A JSON string containing compatibility analysis",
            agent=agent
        )
    
    @staticmethod
    def generate_questions(agent, analysis_result: str) -> Task:
        return Task(
            description=f"""Based on this compatibility analysis, generate relevant questions.
            
            Analysis: {analysis_result}
            
            Provide your response in the following JSON format:
            {{
                "questions": {{
                    "situational": [<list of 1-2 situation-based questions>],
                    "cultural_fit": [<list of 1-2 culture-focused questions>],
                    "adaptability": [<list of 1-2 adaptability questions>],
                    "collaboration": [<list of 1-2 team-focused questions>],
                    "growth": [<list of 1-2 growth-mindset questions>]
                }}
            }}
            
            Format your response EXACTLY as shown above, with valid JSON.
            Make questions:
            - Open-ended
            - Non Technical
            - Behavioral-based
            - Specific to the candidate's background
            - Focused on real workplace scenarios""",
            expected_output="A JSON string containing categorized questions",
            agent=agent
        )
    
class InterviewTasks:
    @staticmethod
    def prepare_interview(agent, cv: str, jd: str) -> Task:
        return Task(
            description=f"""Prepare an interview plan based on:
            CV: {cv}
            JD: {jd}
            
            Create:
            1. Interview structure
            2. Key areas to focus on
            3. Difficulty progression plan""",
            expected_output="""A detailed interview plan including:
            - Interview structure
            - Focus areas
            - Question progression""",
            agent=agent
        )

    @staticmethod
    def conduct_interview(agent, response: str, interview_plan: str) -> Task:
        return Task(
            description=f"""Based on the candidate's response and interview plan:
            Response: {response}
            Plan: {interview_plan}
            
            Provide:
            1. Next question
            2. Expected key points in answer
            3. Follow-up questions if needed""",
            expected_output="""Interview response analysis including:
            - Next question to ask
            - Expected answer points
            - Potential follow-ups""",
            agent=agent
        )

    @staticmethod
    def provide_feedback(agent, response: str, expected_answer: str) -> Task:
        return Task(
            description=f"""Analyze the response against expectations:
            Response: {response}
            Expected: {expected_answer}
            
            Provide:
            1. Strengths in response
            2. Areas for improvement
            3. Specific suggestions
            4. Overall score (0-100)""",
            expected_output="""Detailed feedback including:
            - List of strengths
            - Areas for improvement
            - Specific action items
            - Numerical score""",
            agent=agent
        )

def parse_json_safely(json_str: str) -> dict:
    """Safely parse JSON output from agents."""
    try:
        # Clean up potential markdown formatting
        cleaned = json_str.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Fallback structure if parsing fails
        return {
            "error": "Failed to parse JSON",
            "raw_content": json_str
        }