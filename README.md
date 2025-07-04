# Meeting Intelligence Platform

A comprehensive meeting intelligence platform that leverages OpenAI's APIs to transcribe, analyze, search, and visualize meeting content.

## Features

### Core Features
1. **Audio Transcription** (Whisper API)
   - Upload meeting recordings (MP3, WAV, M4A)
   - Automatic transcription of 20-30 minute files
   - Support for files up to 100MB

2. **Content Analysis** (GPT-4 with Function Calling)
   - Automatic meeting summarization
   - Extract action items with owners and deadlines
   - Identify key decisions with context

3. **Semantic Search** (Embeddings API)
   - Search across all meetings using natural language
   - Find similar meetings automatically
   - Cross-meeting insights and analytics

4. **Visual Summaries** (DALL-E 3)
   - Generate visual infographics for meeting summaries
   - Create presentation-ready assets

### Advanced Features
- **Multi-language Translation**: Translate transcriptions to Georgian, Slovak, Slovenian, Latvian, and more
- **Cross-meeting Analytics**: Aggregate insights across multiple meetings

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Pure HTML, CSS, JavaScript
- **Database**: SQLite
- **APIs**: OpenAI (Whisper, GPT-4, Embeddings, DALL-E 3)
- **Testing**: pytest

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd meeting-intelligence
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite:///./meeting_intelligence.db
UPLOAD_FOLDER=uploads
MAX_FILE_SIZE_MB=100
```

5. Create the uploads directory:
```bash
mkdir uploads
```

## Running the Application

Start the FastAPI server:
```bash
python main.py
```

The application will be available at `http://localhost:8000`

## API Documentation

### Endpoints

#### Upload Meeting
- **POST** `/api/meetings/upload`
- Upload an audio file with a title
- Returns processed meeting with transcription, summary, action items, and visual summary

#### Get All Meetings
- **GET** `/api/meetings`
- Returns list of all meetings

#### Get Meeting by ID
- **GET** `/api/meetings/{meeting_id}`
- Returns detailed meeting information

#### Search Meetings
- **POST** `/api/meetings/search`
- Body: `{"query": "search text", "top_k": 5}`
- Returns semantically similar meetings

#### Find Similar Meetings
- **GET** `/api/meetings/{meeting_id}/similar`
- Returns meetings similar to the specified one

#### Translate Meeting
- **POST** `/api/meetings/translate`
- Body: `{"meeting_id": 1, "target_language": "fr"}`
- Supported languages: ka, sk, sl, lv, es, fr, de, it, pt, nl, pl, ru, ja, ko, zh

#### Get Translations
- **GET** `/api/meetings/{meeting_id}/translations`
- Returns all translations for a meeting

#### Cross-Meeting Insights
- **POST** `/api/insights/cross-meeting`
- Body: `[1, 2, 3]` (array of meeting IDs)
- Returns aggregated insights across meetings

## Testing

Run the test suite:
```bash
pytest tests/
```

## Project Structure

```
meeting-intelligence/
├── main.py              # FastAPI application
├── test_all.py          # All tests for application
├── database.py          # Database models and configuration
├── models.py            # Pydantic models
├── services/
│   ├── openai_service.py    # OpenAI API integrations
│   └── search_service.py    # Search and similarity functions
├── static/
│   ├── index.html      # Frontend interface
│   ├── style.css       # Styling
│   └── script.js       # Frontend logic
└── uploads/            # Uploaded audio files
```

## Usage Guide

1. **Upload a Meeting**:
   - Enter a meeting title
   - Select an audio file (MP3, WAV, or M4A)
   - Click "Upload & Process"
   - Wait for processing (may take a few minutes)

2. **Search Meetings**:
   - Use the search bar to find meetings by content
   - Results are ranked by semantic similarity

3. **View Meeting Details**:
   - Click on any meeting card
   - View transcription, summary, action items, and decisions
   - See visual summary generated by DALL-E 3
   - Find similar meetings

4. **Translate Meetings**:
   - Open a meeting detail
   - Go to the Transcription tab
   - Select target language and click Translate

## Best Practices

1. **Audio Quality**: For best transcription results, use clear audio with minimal background noise
2. **Meeting Titles**: Use descriptive titles for easier searching
3. **File Size**: Keep audio files under 100MB
4. **API Usage**: Monitor your OpenAI API usage to manage costs

## Troubleshooting

### Common Issues

1. **File Upload Fails**:
   - Check file size (< 100MB)
   - Ensure file format is supported
   - Verify API key is valid

2. **Transcription Errors**:
   - Check audio quality
   - Ensure file is not corrupted
   - Verify OpenAI API status

3. **Search Not Working**:
   - Ensure meetings have been fully processed
   - Check that embeddings were generated

## Security Considerations

- Store API keys securely in environment variables
- Validate file uploads to prevent malicious files
- Implement rate limiting in production
- Add authentication for multi-user scenarios

## Future Enhancements

- Real-time transcription support
- Speaker diarization
- Email integration for meeting summaries
- Calendar integration
- Advanced analytics dashboard
- Mobile application

## License

This project is provided as-is for educational and demonstration purposes.