// Global variables
let meetings = [];
let currentMeeting = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMeetings();
    setupEventListeners();
});

function setupEventListeners() {
    // Upload form
    document.getElementById('uploadForm').addEventListener('submit', handleUpload);

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        if (e.target.id === 'meetingModal') {
            closeModal();
        }
    });

    // Search on enter
    document.getElementById('searchQuery').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchMeetings();
        }
    });
}

async function handleUpload(e) {
    e.preventDefault();

    const title = document.getElementById('meetingTitle').value;
    const fileInput = document.getElementById('audioFile');
    const file = fileInput.files[0];
    const statusDiv = document.getElementById('uploadStatus');

    if (!file) {
        showStatus('Please select a file', 'error');
        return;
    }

    // Check file size (100MB limit)
    if (file.size > 100 * 1024 * 1024) {
        showStatus('File size exceeds 100MB limit', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('audio_file', file);

    showStatus('Uploading and processing meeting... This may take a few minutes.', 'loading');

    try {
        const response = await fetch('/api/meetings/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const meeting = await response.json();
        showStatus('Meeting processed successfully!', 'success');

        // Reset form
        document.getElementById('uploadForm').reset();

        // Reload meetings
        loadMeetings();

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.textContent = message;
    statusDiv.className = type;
}

async function loadMeetings() {
    try {
        const response = await fetch('/api/meetings');
        meetings = await response.json();
        displayMeetings(meetings);
    } catch (error) {
        console.error('Error loading meetings:', error);
    }
}

function displayMeetings(meetingsList) {
    const container = document.getElementById('meetingsList');

    if (meetingsList.length === 0) {
        container.innerHTML = '<p>No meetings uploaded yet.</p>';
        return;
    }

    container.innerHTML = meetingsList.map(meeting => `
        <div class="meeting-card" onclick="showMeetingDetail(${meeting.id})">
            <h3>${meeting.title}</h3>
            <div class="meeting-date">${formatDate(meeting.created_at)}</div>
            ${meeting.summary ? `<div class="meeting-summary">${meeting.summary.substring(0, 200)}...</div>` : ''}
            <div class="meeting-stats">
                ${meeting.action_items ? `<span class="stat"><strong>${meeting.action_items.length}</strong> Action Items</span>` : ''}
                ${meeting.decisions ? `<span class="stat"><strong>${meeting.decisions.length}</strong> Decisions</span>` : ''}
            </div>
        </div>
    `).join('');
}

async function showMeetingDetail(meetingId) {
    try {
        const response = await fetch(`/api/meetings/${meetingId}`);
        currentMeeting = await response.json();

        const detailDiv = document.getElementById('meetingDetail');
        detailDiv.innerHTML = `
            <div class="meeting-detail-header">
                <h2>${currentMeeting.title}</h2>
                <p class="meeting-date">${formatDate(currentMeeting.created_at)}</p>
            </div>

            <div class="tabs">
                <button class="tab active" onclick="showTab('summary')">Summary</button>
                <button class="tab" onclick="showTab('transcription')">Transcription</button>
                <button class="tab" onclick="showTab('actions')">Action Items</button>
                <button class="tab" onclick="showTab('decisions')">Decisions</button>
                <button class="tab" onclick="showTab('visual')">Visual Summary</button>
                <button class="tab" onclick="showTab('similar')">Similar Meetings</button>
            </div>

            <div id="summary" class="tab-content active">
                <h3>Meeting Summary</h3>
                <p>${currentMeeting.summary || 'No summary available'}</p>
            </div>

            <div id="transcription" class="tab-content">
                <h3>Transcription</h3>
                <div class="translation-controls">
                    <select id="targetLanguage">
                        <option value="">Select language for translation</option>
                        <option value="ka">Georgian</option>
                        <option value="sk">Slovak</option>
                        <option value="sl">Slovenian</option>
                        <option value="lv">Latvian</option>
                        <option value="es">Spanish</option>
                    </select>
                    <button onclick="translateMeeting()">Translate</button>
                </div>
                <div id="transcriptionText">
                    <p>${currentMeeting.transcription || 'No transcription available'}</p>
                </div>
            </div>

            <div id="actions" class="tab-content">
                <h3>Action Items</h3>
                <ul class="action-items">
                    ${currentMeeting.action_items ? currentMeeting.action_items.map(item => `
                        <li>
                            <div>${item.task}</div>
                            ${item.owner ? `<div class="owner">Owner: ${item.owner}</div>` : ''}
                            ${item.deadline ? `<div class="deadline">Deadline: ${item.deadline}</div>` : ''}
                        </li>
                    `).join('') : '<li>No action items</li>'}
                </ul>
            </div>

            <div id="decisions" class="tab-content">
                <h3>Decisions</h3>
                <ul class="decisions">
                    ${currentMeeting.decisions ? currentMeeting.decisions.map(decision => `
                        <li>
                            <div><strong>${decision.decision}</strong></div>
                            ${decision.context ? `<div>${decision.context}</div>` : ''}
                        </li>
                    `).join('') : '<li>No decisions recorded</li>'}
                </ul>
            </div>

            <div id="visual" class="tab-content">
                <h3>Visual Summary</h3>
                <div class="visual-summary">
                    ${currentMeeting.visual_summary_url ?
                        `<img src="${currentMeeting.visual_summary_url}" alt="Visual Summary">` :
                        '<p>No visual summary available</p>'
                    }
                </div>
            </div>

            <div id="similar" class="tab-content">
                <h3>Similar Meetings</h3>
                <div id="similarMeetings">
                    <div class="spinner"></div>
                </div>
            </div>
        `;

        document.getElementById('meetingModal').style.display = 'block';

        // Load similar meetings
        loadSimilarMeetings(meetingId);

    } catch (error) {
        console.error('Error loading meeting detail:', error);
    }
}

function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName).classList.add('active');
}

async function translateMeeting() {
    const targetLanguage = document.getElementById('targetLanguage').value;
    if (!targetLanguage || !currentMeeting) return;

    const transcriptionDiv = document.getElementById('transcriptionText');
    transcriptionDiv.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch('/api/meetings/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                meeting_id: currentMeeting.id,
                target_language: targetLanguage
            })
        });

        if (!response.ok) throw new Error('Translation failed');

        const translation = await response.json();
        transcriptionDiv.innerHTML = `
            <h4>Translated Text (${targetLanguage.toUpperCase()})</h4>
            <p>${translation.translated_text}</p>
            <hr>
            <h4>Original Transcription</h4>
            <p>${currentMeeting.transcription}</p>
        `;

    } catch (error) {
        transcriptionDiv.innerHTML = `<p>Error translating: ${error.message}</p>`;
    }
}

async function loadSimilarMeetings(meetingId) {
    const container = document.getElementById('similarMeetings');

    try {
        const response = await fetch(`/api/meetings/${meetingId}/similar`);
        const similar = await response.json();

        if (similar.length === 0) {
            container.innerHTML = '<p>No similar meetings found</p>';
            return;
        }

        container.innerHTML = similar.map(result => `
            <div class="meeting-card" onclick="showMeetingDetail(${result.meeting_id})">
                <h4>${result.title}</h4>
                <div class="similarity-score">Similarity: ${(result.similarity_score * 100).toFixed(1)}%</div>
                <p>${result.excerpt}</p>
            </div>
        `).join('');

    } catch (error) {
        container.innerHTML = '<p>Error loading similar meetings</p>';
    }
}

async function searchMeetings() {
    const query = document.getElementById('searchQuery').value;
    if (!query) return;

    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch('/api/meetings/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: 5
            })
        });

        const results = await response.json();

        if (results.length === 0) {
            resultsDiv.innerHTML = '<p>No results found</p>';
            return;
        }

        resultsDiv.innerHTML = '<h3>Search Results</h3>' + results.map(result => `
            <div class="meeting-card" onclick="showMeetingDetail(${result.meeting_id})">
                <h4>${result.title}</h4>
                <div class="similarity-score">Relevance: ${(result.similarity_score * 100).toFixed(1)}%</div>
                <p>${result.excerpt}</p>
            </div>
        `).join('');

    } catch (error) {
        resultsDiv.innerHTML = `<p>Error searching: ${error.message}</p>`;
    }
}

function closeModal() {
    document.getElementById('meetingModal').style.display = 'none';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}