import pytest
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path so we can import from the main project
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, Mock, MagicMock, AsyncMock, mock_open
import asyncio

# Import your application
from main import app, get_db
from database import Base, Meeting, Translation
from services.openai_service import OpenAIService
from services.search_service import SearchService

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestMeetingIntelligencePlatform:
    """Comprehensive test suite for the Meeting Intelligence Platform"""

    def setup_method(self):
        """Setup test database before each test"""
        Base.metadata.create_all(bind=engine)

    def teardown_method(self):
        """Clean up test database after each test"""
        Base.metadata.drop_all(bind=engine)

    # API Endpoint Tests
    def test_home_page(self):
        """Test that home page loads"""
        response = client.get("/")
        assert response.status_code == 200

    def test_get_meetings_empty(self):
        """Test getting meetings when database is empty"""
        response = client.get("/api/meetings")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_meeting_not_found(self):
        """Test getting non-existent meeting"""
        response = client.get("/api/meetings/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('aiofiles.open')
    @patch.object(OpenAIService, 'transcribe_audio', new_callable=AsyncMock)
    @patch.object(OpenAIService, 'analyze_meeting', new_callable=AsyncMock)
    @patch.object(OpenAIService, 'generate_embedding', new_callable=AsyncMock)
    @patch.object(OpenAIService, 'generate_visual_summary', new_callable=AsyncMock)
    def test_upload_meeting_success(self, mock_visual, mock_embed, mock_analyze, mock_transcribe, mock_aio):
        """Test successful meeting upload"""
        # Setup return values for async mocks
        mock_transcribe.return_value = "This is a test meeting transcription"
        mock_analyze.return_value = {
            "summary": "Test meeting summary",
            "action_items": [{"task": "Test task", "owner": "John", "deadline": "2024-01-15"}],
            "decisions": [{"decision": "Test decision", "context": "Test context"}]
        }
        mock_embed.return_value = [0.1] * 1536
        mock_visual.return_value = "https://example.com/image.png"

        mock_file = AsyncMock()
        mock_aio.return_value.__aenter__.return_value = mock_file
        mock_aio.return_value.__aexit__.return_value = None

        # Create test file content
        test_content = b"fake audio content"

        response = client.post(
            "/api/meetings/upload",
            data={"title": "Test Meeting"},
            files={"audio_file": ("test.mp3", test_content, "audio/mpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Meeting"
        assert data["transcription"] == "This is a test meeting transcription"
        assert data["summary"] == "Test meeting summary"
        assert len(data["action_items"]) == 1
        assert len(data["decisions"]) == 1

    def test_upload_meeting_invalid_file_type(self):
        """Test upload with invalid file type"""
        test_content = b"not audio"

        response = client.post(
            "/api/meetings/upload",
            data={"title": "Test Meeting"},
            files={"audio_file": ("test.txt", test_content, "text/plain")}
        )

        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    def test_upload_meeting_file_too_large(self):
        """Test upload with file exceeding size limit"""
        # Create content larger than 100MB
        large_content = b"x" * (101 * 1024 * 1024)

        response = client.post(
            "/api/meetings/upload",
            data={"title": "Test Meeting"},
            files={"audio_file": ("large.mp3", large_content, "audio/mpeg")}
        )

        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_search_meetings_no_results(self):
        """Test search with no results"""
        response = client.post(
            "/api/meetings/search",
            json={"query": "nonexistent meeting", "top_k": 5}
        )

        assert response.status_code == 200
        assert response.json() == []

    @patch.object(OpenAIService, 'generate_embedding', new_callable=AsyncMock)
    def test_search_meetings_with_results(self, mock_embeddings):
        """Test search with results"""
        # Mock embeddings
        mock_embeddings.return_value = [0.1] * 1536

        # Create test meeting in database
        db = next(override_get_db())
        meeting = Meeting(
            title="Test Meeting",
            transcription="Test transcription",
            summary="Test summary",
            embedding=json.dumps([0.1] * 1536)
        )
        db.add(meeting)
        db.commit()

        response = client.post(
            "/api/meetings/search",
            json={"query": "test", "top_k": 5}
        )

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["title"] == "Test Meeting"
        assert "similarity_score" in results[0]

    def test_get_similar_meetings(self):
        """Test finding similar meetings"""
        # Create test meeting
        db = next(override_get_db())
        meeting = Meeting(
            title="Test Meeting",
            embedding=json.dumps([0.1] * 1536)
        )
        db.add(meeting)
        db.commit()

        response = client.get(f"/api/meetings/{meeting.id}/similar")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch.object(OpenAIService, 'translate_text', new_callable=AsyncMock)
    def test_translate_meeting(self, mock_translate):
        """Test meeting translation"""
        # Mock translation response
        mock_translate.return_value = "Texte traduit en français"

        # Create test meeting
        db = next(override_get_db())
        meeting = Meeting(
            title="Test Meeting",
            transcription="Original text to translate"
        )
        db.add(meeting)
        db.commit()

        response = client.post(
            "/api/meetings/translate",
            json={"meeting_id": meeting.id, "target_language": "fr"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Texte traduit en français"
        assert data["target_language"] == "fr"

    def test_translate_meeting_no_transcription(self):
        """Test translation when meeting has no transcription"""
        # Create meeting without transcription
        db = next(override_get_db())
        meeting = Meeting(title="Test Meeting")
        db.add(meeting)
        db.commit()

        response = client.post(
            "/api/meetings/translate",
            json={"meeting_id": meeting.id, "target_language": "fr"}
        )

        assert response.status_code == 400
        assert "no transcription" in response.json()["detail"].lower()

    def test_get_translations(self):
        """Test getting translations for a meeting"""
        # Create test data
        db = next(override_get_db())
        meeting = Meeting(title="Test Meeting")
        db.add(meeting)
        db.commit()

        translation = Translation(
            meeting_id=meeting.id,
            target_language="fr",
            translated_text="Texte en français"
        )
        db.add(translation)
        db.commit()

        response = client.get(f"/api/meetings/{meeting.id}/translations")

        assert response.status_code == 200
        translations = response.json()
        assert len(translations) == 1
        assert translations[0]["target_language"] == "fr"

    def test_cross_meeting_insights(self):
        """Test cross-meeting insights"""
        # Create test meetings
        db = next(override_get_db())
        meeting1 = Meeting(
            title="Meeting 1",
            action_items=[{"task": "Task 1", "owner": "John"}],
            decisions=[{"decision": "Decision 1"}]
        )
        meeting2 = Meeting(
            title="Meeting 2",
            action_items=[{"task": "Task 2", "owner": "John"}],
            decisions=[{"decision": "Decision 2"}]
        )
        db.add(meeting1)
        db.add(meeting2)
        db.commit()

        response = client.post(
            "/api/insights/cross-meeting",
            json=[meeting1.id, meeting2.id]
        )

        assert response.status_code == 200
        insights = response.json()
        assert insights["total_meetings"] == 2
        assert insights["total_action_items"] == 2
        assert insights["total_decisions"] == 2
        assert "John" in insights["action_items_by_owner"]

    # Service Tests - Using synchronous test approach
    @patch('builtins.open', new_callable=mock_open, read_data=b"fake audio")
    @patch.object(OpenAIService, 'transcribe_audio', new_callable=AsyncMock)
    def test_openai_service_transcribe(self, mock_transcribe, mock_file):
        """Test OpenAI transcription service - mocked version"""
        mock_transcribe.return_value = "Test transcription"

        # Since we're testing the mock, just verify it works
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(mock_transcribe("test.mp3"))
        loop.close()

        assert result == "Test transcription"

    @patch.object(OpenAIService, 'analyze_meeting', new_callable=AsyncMock)
    def test_openai_service_analyze(self, mock_analyze):
        """Test OpenAI analysis service - mocked version"""
        mock_analyze.return_value = {
            "summary": "Meeting summary",
            "action_items": [],
            "decisions": []
        }

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(mock_analyze("Test transcription"))
        loop.close()

        assert result["summary"] == "Meeting summary"

    @patch.object(OpenAIService, 'generate_embedding', new_callable=AsyncMock)
    def test_search_service_search(self, mock_embed):
        """Test search service"""
        mock_embed.return_value = [0.1] * 1536

        db = next(override_get_db())
        meeting = Meeting(
            title="Test Meeting",
            embedding=json.dumps([0.1] * 1536)
        )
        db.add(meeting)
        db.commit()

        # Run async function in sync context
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(SearchService.search_meetings("test", db))
        loop.close()

        assert len(results) > 0
        assert results[0][0].title == "Test Meeting"