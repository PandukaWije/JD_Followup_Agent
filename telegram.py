from telethon import TelegramClient, events
from telethon.tl.types import User
import asyncio
import sqlite3
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
import json
from telethon import errors
import random
import time
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
with open("question_starters.txt", "r", encoding="utf-8") as file:
    question_starters = file.readlines()
# Configuration
API_ID = os.getenv('TELEGRAM_APP_API_ID_PANDUKA')
API_HASH = os.getenv('TELEGRAM_APP_API_HASH_PANDUKA')
DB_PATH = 'interviews.db'

class InterviewClient:
    def __init__(self, api_id: str, api_hash: str):
        self.client = TelegramClient('interview_session', api_id, api_hash)
        self.active_interviews = {}
        self.init_sqlite()

    def init_sqlite(self):
        """Initialize SQLite database and tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create questions table with additional fields
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            candidate_id TEXT PRIMARY KEY,
            phone_number TEXT,
            questions TEXT,
            created_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            interview_complete BOOLEAN DEFAULT FALSE
        )
        ''')

        # Create chat history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT,
            question TEXT,
            answer TEXT,
            timestamp TIMESTAMP
        )
        ''')

        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")

    async def connect(self):
        """Connect to Telegram"""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            logger.info("First time setup - you'll need to authenticate")
            await self.client.start()
        logger.info("Client connected successfully")

    async def start(self):
        """Start the client and register handlers"""
        await self.connect()
        
        @self.client.on(events.NewMessage())
        async def handle_message(event):
            if event.is_private:
                sender = await event.get_sender()
                if isinstance(sender, User):
                    await self.process_message(event, sender)

        logger.info("Message handlers registered")
        await self.client.run_until_disconnected()

    async def send_welcome_message(self, user_id: int):
        """Send a welcome message with instructions"""
        welcome_message = (
            "👋 Welcome to our automated Job Follow-up process!\n\n"
            "🔍 Here's what you need to know:\n"
            "1. Type /start to begin your interview\n"
            "2. You'll receive questions one at a time\n"
            "3. Take your time to answer thoughtfully\n"
            "4. Type /pause to pause the interview\n"
            "5. Type /resume to continue where you left off\n"
            "6. Type /help for assistance\n\n"
            "Ready to begin? Type /start when you're ready!"
        )
        await self.client.send_message(user_id, welcome_message)

    async def add_candidate(self, phone_number: str, questions: list):
        """Add a new candidate to the system"""
        try:
            if not self.client.is_connected():
                await self.connect()
            await asyncio.sleep(2)
            try:
                # Resolve phone number to Telegram ID with flood control handling
                input_entity = await self.client.get_input_entity(phone_number)
                print(input_entity)
                contact = await self.client.get_entity(input_entity)
            except errors.FloodWaitError as e:
                logger.warning(f"Need to wait {e.seconds} seconds before retrying")
                await asyncio.sleep(e.seconds)  # Wait for the required time

                # Resolve phone number to Telegram ID
                input_entity = await self.client.get_input_entity(phone_number)
                print(input_entity)
                contact = await self.client.get_entity(input_entity)
            candidate_id = str(contact.id)
            
            # Store in SQLite
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO questions 
            (candidate_id, phone_number, questions, created_at, status)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                candidate_id,
                phone_number,
                json.dumps(questions),
                datetime.utcnow().isoformat(),
                'pending'
            ))
            
            conn.commit()
            conn.close()
            
            # Send welcome message to the candidate
            await self.send_welcome_message(int(candidate_id))
            
            logger.info(f"Added candidate: {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error adding candidate: {e}")
            return False

    async def process_message(self, event, sender: User):
        """Process incoming messages with enhanced command handling"""
        user_id = str(sender.id)
        message = event.message.text.lower()

        # Check if user exists in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM questions WHERE candidate_id = ?', (user_id,))
        user_exists = cursor.fetchone()
        conn.close()

        if not user_exists and message != "/help":
            await self.client.send_message(
                int(user_id),
                "⚠️ You're not registered for an followup. Please contact the HR team for registration."
            )
            return

        # Handle commands
        if message == "/start":
            await self.start_interview(user_id)
        elif message == "/help":
            await self.send_help_message(int(user_id))
        elif message == "/pause":
            await self.pause_interview(user_id)
        elif message == "/resume":
            await self.resume_interview(user_id)
        elif user_id in self.active_interviews:
            await self.handle_response(user_id, event.message.text)

    async def send_help_message(self, user_id: int):
        """Send help message to user"""
        help_message = (
            "🆘 Need help? Here are the available commands:\n\n"
            "/start - Begin or restart your interview\n"
            "/pause - Pause your interview\n"
            "/resume - Resume a paused interview\n"
            "/help - Show this help message\n\n"
            "If you're experiencing technical issues, please contact support at support@example.com"
        )
        await self.client.send_message(user_id, help_message)

    async def pause_interview(self, user_id: str):
        """Pause the ongoing interview"""
        if user_id in self.active_interviews:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE questions SET status = ? WHERE candidate_id = ?',
                ('paused', user_id)
            )
            conn.commit()
            conn.close()

            self.active_interviews[user_id]['paused'] = True
            await self.client.send_message(
                int(user_id),
                "⏸️ Session paused. Type /resume when you're ready to continue."
            )
        else:
            await self.client.send_message(
                int(user_id),
                "No active Session to pause. Type /start to begin an Session."
            )

    async def resume_interview(self, user_id: str):
        """Resume a paused Session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT status FROM questions WHERE candidate_id = ? AND status = ?',
            (user_id, 'paused')
        )
        paused_interview = cursor.fetchone()
        conn.close()

        if paused_interview:
            if user_id in self.active_interviews:
                self.active_interviews[user_id]['paused'] = False
                await self.send_next_question(user_id,question_starters)
            else:
                await self.start_interview(user_id)
        else:
            await self.client.send_message(
                int(user_id),
                "No paused Session found. Type /start to begin a new Session."
            )

    async def start_interview(self, user_id: str):
        """Start or restart an interview"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT questions FROM questions WHERE candidate_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            await self.client.send_message(
                int(user_id),
                "⚠️ No followup questions found. Please contact HR for assistance."
            )
            return

        questions = json.loads(result[0])
        self.active_interviews[user_id] = {
            "current_index": 0,
            "questions": questions,
            "paused": False
        }

        # Update status
        cursor.execute(
            'UPDATE questions SET status = ? WHERE candidate_id = ?',
            ('in_progress', user_id)
        )
        conn.commit()
        conn.close()

        await self.client.send_message(
            int(user_id),
            "🎯 Your followup is starting now. Take your time to answer each question thoughtfully."
        )
        await self.send_next_question(user_id,question_starters)

    async def handle_response(self, user_id: str, answer: str):
        """Handle interview responses"""
        if user_id not in self.active_interviews or self.active_interviews[user_id].get('paused'):
            return

        interview = self.active_interviews[user_id]
        current_question = interview["questions"][interview["current_index"]]

        # Save response
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO chat_history (candidate_id, question, answer, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (
            user_id,
            current_question,
            answer,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()

        # Move to next question
        interview["current_index"] += 1
        await self.send_next_question(user_id,question_starters)

    async def send_next_question(self, user_id: str,question_starters):
        """Send the next question with progress indicator"""
        interview = self.active_interviews[user_id]
        total_questions = len(interview["questions"])
        if interview["current_index"] < total_questions:
            question = interview["questions"][interview["current_index"]]
            # progress = f"Question {interview['current_index'] + 1} of {total_questions}"
            if (interview["current_index"]+1)!=1:
                index=interview["current_index"]+1
                progress=question_starters[index]
            else:
                progress='Thank you for joining. Here’s your first question.'
            message = f"📝 {progress}\n\n{question}\n\n(Type /pause if you need a break)"
            await self.client.send_message(int(user_id), message)
            time.sleep(random.randint(3,5))

        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE questions SET status = ?, interview_complete = ? WHERE candidate_id = ?',
                ('completed', True, user_id)
            )
            conn.commit()
            conn.close()

            completion_message = (
                "🎉 Congratulations! You've completed the followup.\n\n"
                "Thank you for your time and thoughtful responses. "
                "Our team will review your answers and get back to you soon.\n\n"
                "Best of luck! 🍀"
            )
            await self.client.send_message(int(user_id), completion_message)
            del self.active_interviews[user_id]
            logger.info("All questions sent. Terminating..")
            os._exit(0)


async def read_questions_from_file(filename: str = "followup_questions.txt") -> list:
    """
    Read questions from a text file.
    
    Args:
        filename (str): Name of the file containing questions
        
    Returns:
        list: List of questions
    """
    try:
        with open(filename, 'r') as f:
            # Read lines and remove empty lines and whitespace
            questions = [line.strip() for line in f.readlines() if line.strip()]
        return questions
    except FileNotFoundError:
        logger.error(f"Questions file {filename} not found")
        return []
    except Exception as e:
        logger.error(f"Error reading questions file: {e}")
        return []

async def test_interview():
    client = InterviewClient(API_ID, API_HASH)
    await client.connect()
    
    # Read questions from file
    questions = await read_questions_from_file()
    
    if not questions:
        logger.error("No questions loaded from file. Exiting...")
        return
    
    # Add test candidate
    test_phone = "+94714479827"  # Replace with actual phone number
    await asyncio.sleep(5)
    
    success = await client.add_candidate(test_phone, questions)
    
    if success:
        logger.info("Test candidate added successfully")
        await client.start()
        client.disconnect()
    else:
        logger.error("Failed to add test candidate")

if __name__ == "__main__":
    asyncio.run(test_interview())