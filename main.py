from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
from typing import List
import aiofiles
from datetime import datetime

from database import get_db, Meeting, Translation
from models import (
    MeetingCreate, MeetingResponse, TranslationRequest,
    TranslationResponse, SearchQuery, SearchResult
)
from services.openai_service import OpenAIService
from services.search_service import SearchService

app = FastAPI(title="Meeting Intelligence API")

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse('static/index.html')


@app.post("/api/meetings/upload", response_model=MeetingResponse)
async def upload_meeting(
        title: str = Form(...),
        audio_file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Upload and process a meeting recording"""
    # Validate file size (100MB limit)
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024

    contents = await audio_file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE}MB")

    # Validate file type
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm']
    file_extension = os.path.splitext(audio_file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed types: mp3, wav, m4a")

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{audio_file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)

    # Create meeting record
    meeting = Meeting(
        title=title,
        audio_filename=filename
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Process audio in background (in production, use background tasks)
    try:
        # Transcribe audio
        transcription = await OpenAIService.transcribe_audio(file_path)
        meeting.transcription = transcription

        # Analyze meeting
        analysis = await OpenAIService.analyze_meeting(transcription)
        meeting.summary = analysis['summary']
        meeting.action_items = analysis['action_items']
        meeting.decisions = analysis['decisions']

        # Generate embedding
        embedding_text = f"{title}\n{analysis['summary']}"
        embedding = await OpenAIService.generate_embedding(embedding_text)
        meeting.embedding = json.dumps(embedding)

        # Generate visual summary
        key_points = [item['task'] for item in analysis['action_items'][:3]]
        if not key_points and analysis['decisions']:
            key_points = [dec['decision'] for dec in analysis['decisions'][:3]]

        if key_points:
            visual_url = await OpenAIService.generate_visual_summary(
                analysis['summary'],
                key_points
            )
            meeting.visual_summary_url = visual_url

        db.commit()
        db.refresh(meeting)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing meeting: {str(e)}")

    return meeting


@app.get("/api/meetings", response_model=List[MeetingResponse])
async def get_meetings(db: Session = Depends(get_db)):
    """Get all meetings"""
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    return meetings


@app.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Get a specific meeting"""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@app.post("/api/meetings/search", response_model=List[SearchResult])
async def search_meetings(query: SearchQuery, db: Session = Depends(get_db)):
    """Search meetings using semantic search"""
    results = await SearchService.search_meetings(query.query, db, query.top_k)

    search_results = []
    for meeting, score in results:
        excerpt = meeting.summary[:200] + "..." if meeting.summary and len(meeting.summary) > 200 else meeting.summary
        search_results.append(SearchResult(
            meeting_id=meeting.id,
            title=meeting.title,
            excerpt=excerpt or "",
            similarity_score=float(score),
            created_at=meeting.created_at
        ))

    return search_results


@app.get("/api/meetings/{meeting_id}/similar", response_model=List[SearchResult])
async def get_similar_meetings(meeting_id: int, db: Session = Depends(get_db)):
    """Find similar meetings"""
    results = await SearchService.find_similar_meetings(meeting_id, db)

    similar_meetings = []
    for meeting, score in results:
        excerpt = meeting.summary[:200] + "..." if meeting.summary and len(meeting.summary) > 200 else meeting.summary
        similar_meetings.append(SearchResult(
            meeting_id=meeting.id,
            title=meeting.title,
            excerpt=excerpt or "",
            similarity_score=float(score),
            created_at=meeting.created_at
        ))

    return similar_meetings


@app.post("/api/meetings/translate", response_model=TranslationResponse)
async def translate_meeting(request: TranslationRequest, db: Session = Depends(get_db)):
    """Translate a meeting transcription"""
    meeting = db.query(Meeting).filter(Meeting.id == request.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.transcription:
        raise HTTPException(status_code=400, detail="Meeting has no transcription")

    # Check if translation already exists
    existing = db.query(Translation).filter(
        Translation.meeting_id == request.meeting_id,
        Translation.target_language == request.target_language
    ).first()

    if existing:
        return existing

    # Translate
    translated_text = await OpenAIService.translate_text(
        meeting.transcription,
        request.target_language
    )

    # Save translation
    translation = Translation(
        meeting_id=request.meeting_id,
        target_language=request.target_language,
        translated_text=translated_text
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)

    return translation


@app.get("/api/meetings/{meeting_id}/translations", response_model=List[TranslationResponse])
async def get_translations(meeting_id: int, db: Session = Depends(get_db)):
    """Get all translations for a meeting"""
    translations = db.query(Translation).filter(
        Translation.meeting_id == meeting_id
    ).all()
    return translations


@app.post("/api/insights/cross-meeting")
async def get_cross_meeting_insights(meeting_ids: List[int], db: Session = Depends(get_db)):
    """Get insights across multiple meetings"""
    insights = await SearchService.extract_cross_meeting_insights(meeting_ids, db)
    return insights


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)