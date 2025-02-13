# agents.py
from crewai import Agent, Task, Crew, Process
from typing import List, Dict, Optional

class JobAgents:
    def __init__(self):
        # Profile Analyzer Agent
        self.profile_analyzer = Agent(
            role="Cultural Fit Analyzer",
            goal="Analyze CV and job description to determine workplace compatibility and cultural fit",
            backstory="""You are an expert in organizational psychology and cultural fit 
            assessment. You excel at understanding both explicit and implicit indicators 
            of how well someone might adapt to different work environments, team dynamics, 
            and organizational cultures. You look beyond technical skills to understand 
            the whole person.""",
            verbose=True
        )

        # Question Generator Agent
        self.question_generator = Agent(
            role="Behavioral Interview Specialist",
            goal="Generate insightful questions to assess cultural fit and adaptability",
            backstory="""You are a skilled interviewer who specializes in understanding 
            how candidates handle real-world situations. You know how to craft questions 
            that reveal working style, collaboration preferences, problem-solving approaches, 
            and adaptation to change. You focus on understanding the person behind the 
            resume.""",
            verbose=True
        )

        # Communication Agent
        self.communication_agent = Agent(
            role="Engagement Coordinator",
            goal="Create personalized and engaging candidate communications",
            backstory="""You excel at creating communications that build rapport and 
            encourage open dialogue. You know how to make candidates feel comfortable 
            while maintaining professionalism. You're skilled at crafting messages 
            that elicit honest and meaningful responses.""",
            verbose=True
        )
        
class InterviewAgents:
    def __init__(self):
        # Interview Coach Agent
        self.coach = Agent(
            role="Interview Coach",
            goal="Guide candidates through interview preparation",
            backstory="""You are an experienced interview coach who has helped
            countless candidates prepare for technical and behavioral interviews.
            You know how to simulate realistic interview conditions.""",
            verbose=True
        )

        # Q&A Agent
        self.qa_agent = Agent(
            role="Interview Simulator",
            goal="Conduct realistic interview simulations",
            backstory="""You are an expert interviewer with experience across
            multiple industries. You know how to ask challenging questions and
            create realistic interview scenarios.""",
            verbose=True
        )

        # Feedback Agent
        self.feedback_agent = Agent(
            role="Interview Feedback Provider",
            goal="Provide constructive feedback on interview responses",
            backstory="""You are skilled at providing detailed, constructive
            feedback that helps candidates improve. You can identify both
            strengths and areas for improvement.""",
            verbose=True
        )

# tasks.py
class JobTasks:
    @staticmethod
    def analyze_profile(agent, cv: str, jd: str) -> Task:
        return Task(
            description=f"""Analyze the following CV against the job description:
            CV: {cv}
            JD: {jd}
            
            Provide:
            1. Match score (0-100)
            2. Key matching skills
            3. Identified gaps
            4. Areas needing clarification""",
            agent=agent
        )

    @staticmethod
    def generate_questions(agent, analysis: str) -> Task:
        return Task(
            description=f"""Based on the following analysis, generate follow-up questions:
            Analysis: {analysis}
            
            Generate:
            1. 3-5 specific questions about gaps
            2. 2-3 questions about experience details
            3. 1-2 questions about relevant projects""",
            agent=agent
        )

    @staticmethod
    def prepare_communication(agent, questions: str, match_score: int) -> Task:
        return Task(
            description=f"""Prepare a communication plan based on:
            Questions: {questions}
            Match Score: {match_score}
            
            Create:
            1. Initial follow-up message
            2. Question sequence
            3. Next steps recommendation""",
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
            agent=agent
        )