import openai
import os
from typing import List, Dict, Any
import json
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()


class OpenAIService:
    @staticmethod
    async def transcribe_audio(file_path: str) -> str:
        """Transcribe audio using Whisper API"""
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript

    @staticmethod
    async def analyze_meeting(transcription: str) -> Dict[str, Any]:
        """Analyze meeting using GPT-4 with function calling"""
        functions = [
            {
                "name": "extract_meeting_insights",
                "description": "Extract key insights from meeting transcription",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A concise summary of the meeting"
                        },
                        "action_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string"},
                                    "owner": {"type": "string"},
                                    "deadline": {"type": "string"}
                                }
                            },
                            "description": "List of action items from the meeting"
                        },
                        "decisions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "decision": {"type": "string"},
                                    "context": {"type": "string"}
                                }
                            },
                            "description": "Key decisions made during the meeting"
                        }
                    },
                    "required": ["summary", "action_items", "decisions"]
                }
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a meeting analyst. Extract key insights, action items, and decisions from meeting transcriptions."
                },
                {
                    "role": "user",
                    "content": f"Analyze this meeting transcription and extract insights:\n\n{transcription}"
                }
            ],
            functions=functions,
            function_call={"name": "extract_meeting_insights"}
        )

        function_call = response.choices[0].message.function_call
        return json.loads(function_call.arguments)

    @staticmethod
    async def generate_embedding(text: str) -> List[float]:
        """Generate text embedding using OpenAI Embeddings API"""
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    @staticmethod
    async def generate_visual_summary(meeting_summary: str, key_points: List[str]) -> str:
        """Generate visual summary using DALL-E 3"""
        prompt = f"Create a professional infographic-style visual summary of a meeting. The meeting summary: {meeting_summary}. Key points to highlight: {', '.join(key_points[:3])}. Use corporate colors, clean design, and visual metaphors for the concepts discussed."

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        return response.data[0].url

    @staticmethod
    async def translate_text(text: str, target_language: str) -> str:
        """Translate text to target language using GPT-4"""
        language_names = {
            "ka": "Georgian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "lv": "Latvian",
            "es": "Spanish",
        }

        target_lang_name = language_names.get(target_language, target_language)

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate the following text to {target_lang_name}. Maintain the original meaning and tone."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return response.choices[0].message.content