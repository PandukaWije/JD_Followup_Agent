# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import json
import re
from crewai import Crew, Process
from agents import JobAgents
from tasks import JobTasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class CVAnalysisRequest(BaseModel):
    cv: str
    jd: str

class CompatibilityResponse(BaseModel):
    compatibility_score: int
    strengths: List[str]
    potential_concerns: List[str]
    work_style_indicators: List[str]
    culture_fit_aspects: List[str]
    adaptability_signals: List[str]
    questions: Dict[str, List[str]]
    next_steps: str  # Added this required field

def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text, handling various formats."""
    try:
        # Try to find JSON pattern in the text
        json_pattern = r'\{[\s\S]*\}'
        json_match = re.search(json_pattern, text)
        
        if json_match:
            # Clean up the extracted JSON string
            json_str = json_match.group()
            # Remove markdown code blocks if present
            json_str = json_str.replace('```json', '').replace('```', '')
            return json.loads(json_str)
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {str(e)}")
    
    # Return default structure if parsing fails
    return {
        "compatibility_score": 50,
        "strengths": ["Candidate shows potential", "Review needed for specific details"],
        "potential_concerns": ["Further assessment recommended"],
        "work_style_indicators": ["Need more information"],
        "culture_fit_aspects": ["To be determined"],
        "adaptability_signals": ["Requires further evaluation"],
        "questions": {
            "situational": ["Could you describe a challenging work situation and how you handled it?"],
            "cultural_fit": ["What type of work environment helps you perform your best?"],
            "adaptability": ["How do you handle unexpected changes in priorities?"],
            "collaboration": ["How do you prefer to work within a team?"],
            "growth": ["What are your learning goals for the next year?"]
        }
    }

@app.post("/analyze-profile", response_model=CompatibilityResponse)
async def analyze_profile(request: CVAnalysisRequest):
    try:
        logger.info("Starting compatibility analysis")
        job_agents = JobAgents()
        
        # Run analysis
        analysis_crew = Crew(
            agents=[job_agents.profile_analyzer],
            tasks=[JobTasks.analyze_profile(job_agents.profile_analyzer, request.cv, request.jd)],
            process=Process.sequential,
            verbose=True
        )
        
        analysis_result = analysis_crew.kickoff()
        logger.info(f"Raw analysis result: {analysis_result}")
        
        # Parse analysis result
        parsed_analysis = extract_json_from_text(str(analysis_result))
        logger.info(f"Parsed analysis: {parsed_analysis}")
        
        # Generate questions
        questions_crew = Crew(
            agents=[job_agents.question_generator],
            tasks=[JobTasks.generate_questions(
                job_agents.question_generator,
                json.dumps(parsed_analysis)
            )],
            process=Process.sequential,
            verbose=True
        )
        
        questions_result = questions_crew.kickoff()
        logger.info(f"Raw questions result: {questions_result}")
        
        # Parse questions result
        parsed_questions = extract_json_from_text(str(questions_result))
        logger.info(f"Parsed questions: {parsed_questions}")
        
        # Determine next steps based on compatibility score
        compatibility_score = parsed_analysis.get('compatibility_score', 50)
        if compatibility_score >= 80:
            next_steps = "Schedule immediate follow-up interview"
        elif compatibility_score >= 60:
            next_steps = "Schedule initial screening call"
        else:
            next_steps = "Review additional candidates before proceeding"
        
        # Combine results
        return CompatibilityResponse(
            compatibility_score=compatibility_score,
            strengths=parsed_analysis.get('strengths', []),
            potential_concerns=parsed_analysis.get('potential_concerns', []),
            work_style_indicators=parsed_analysis.get('work_style_indicators', []),
            culture_fit_aspects=parsed_analysis.get('culture_fit_aspects', []),
            adaptability_signals=parsed_analysis.get('adaptability_signals', []),
            questions=parsed_questions.get('questions', {
                'situational': [],
                'cultural_fit': [],
                'adaptability': [],
                'collaboration': [],
                'growth': []
            }),
            next_steps=next_steps  # Added this field to the response
        )
        
    except Exception as e:
        logger.error(f"Error in analyze_profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing profile: {str(e)}"
        )