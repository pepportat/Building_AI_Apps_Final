import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Dict, Any
import json
from database import Meeting
from services.openai_service import OpenAIService


class SearchService:
    @staticmethod
    async def search_meetings(query: str, db_session, top_k: int = 5) -> List[Tuple[Meeting, float]]:
        """Search meetings using semantic similarity"""
        # Generate embedding for search query
        query_embedding = await OpenAIService.generate_embedding(query)

        # Get all meetings from database
        meetings = db_session.query(Meeting).all()

        if not meetings:
            return []

        # Calculate similarities
        similarities = []
        for meeting in meetings:
            if meeting.embedding:
                meeting_embedding = json.loads(meeting.embedding)
                similarity = cosine_similarity(
                    [query_embedding],
                    [meeting_embedding]
                )[0][0]
                similarities.append((meeting, similarity))

        # Sort by similarity score
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    @staticmethod
    async def find_similar_meetings(meeting_id: int, db_session, top_k: int = 3) -> List[Tuple[Meeting, float]]:
        """Find meetings similar to a given meeting"""
        # Get the target meeting
        target_meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not target_meeting or not target_meeting.embedding:
            return []

        target_embedding = json.loads(target_meeting.embedding)

        # Get all other meetings
        other_meetings = db_session.query(Meeting).filter(Meeting.id != meeting_id).all()

        similarities = []
        for meeting in other_meetings:
            if meeting.embedding:
                meeting_embedding = json.loads(meeting.embedding)
                similarity = cosine_similarity(
                    [target_embedding],
                    [meeting_embedding]
                )[0][0]
                similarities.append((meeting, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    @staticmethod
    async def extract_cross_meeting_insights(meeting_ids: List[int], db_session) -> Dict[str, Any]:
        """Extract insights across multiple meetings"""
        meetings = db_session.query(Meeting).filter(Meeting.id.in_(meeting_ids)).all()

        all_action_items = []
        all_decisions = []

        for meeting in meetings:
            if meeting.action_items:
                all_action_items.extend(meeting.action_items)
            if meeting.decisions:
                all_decisions.extend(meeting.decisions)

        # Group action items by owner
        action_items_by_owner = {}
        for item in all_action_items:
            owner = item.get('owner', 'Unassigned')
            if owner not in action_items_by_owner:
                action_items_by_owner[owner] = []
            action_items_by_owner[owner].append(item)

        return {
            "total_meetings": len(meetings),
            "total_action_items": len(all_action_items),
            "total_decisions": len(all_decisions),
            "action_items_by_owner": action_items_by_owner,
            "meetings": [{"id": m.id, "title": m.title, "date": m.created_at} for m in meetings]
        }