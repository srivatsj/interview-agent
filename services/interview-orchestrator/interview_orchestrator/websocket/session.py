"""Session management and database synchronization."""

import asyncio
import logging
import os

from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.adk.sessions import DatabaseSessionService

from ..root_agent import root_agent
from ..shared.session_store import active_sessions
from .events import enrich_event_content_with_transcriptions, should_sync_event

logger = logging.getLogger(__name__)

# Application configuration
APP_NAME = "interview_orchestrator"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/interview_db")


async def start_agent_session(user_id: str, interview_id: str, is_audio: bool = False):
    """Start an agent session with InMemoryRunner (fast, zero latency).

    Args:
        user_id: User identifier
        interview_id: Interview identifier
        is_audio: Whether this is an audio session

    Returns:
        Tuple of (live_events, live_request_queue, session_key)
    """
    # Create a Runner per session - InMemory for real-time performance
    runner = InMemoryRunner(app_name=APP_NAME, agent=root_agent)

    # Create session key
    session_key = f"{user_id}:{interview_id}"

    # Create a Session with user_id and interview_id in state
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state={
            "user_id": user_id,  # Store for payment flow
            "interview_id": interview_id,
            "session_key": session_key,  # Store for tool access
        },
    )

    # Store session and runner for later DB sync
    active_sessions[session_key] = {
        "session": session,
        "runner": runner,
        "user_id": user_id,
        "interview_id": interview_id,
    }

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Setup RunConfig
    # NOTE: session_resumption with transparent=True is NOT supported in current Gemini API
    # IMPORTANT: When using test_multiagent, agents already have speech_config in Gemini() wrapper
    # so we should NOT set it again in RunConfig to avoid conflicts

    # Minimal RunConfig - speech_config is in agent models
    run_config = RunConfig(
        streaming_mode="bidi",
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
    )

    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    return live_events, live_request_queue, session_key


async def sync_session_to_database(user_id: str, interview_id: str) -> dict:
    """Sync InMemory session to Neon DB for persistence.

    Called when interview ends. Transfers all session data from memory to database.

    IMPORTANT: Only syncs FINAL text transcriptions (not audio chunks or partial updates).
    This reduces sync time from ~50 minutes to under 2 minutes.

    Args:
        user_id: User identifier
        interview_id: Interview identifier

    Returns:
        dict with sync status and statistics
    """
    session_key = f"{user_id}:{interview_id}"

    # Check if session exists
    if session_key not in active_sessions:
        logger.warning(f"Session {session_key} not found in active sessions")
        return {
            "success": False,
            "error": "Session not found",
            "session_key": session_key,
        }

    try:
        # Get InMemory session data
        session_data = active_sessions[session_key]
        in_memory_session = session_data["session"]

        logger.info(f"Syncing session {session_key} to database...")
        logger.info(f"  Total events in memory: {len(in_memory_session.events)}")

        # Filter events to text transcriptions only
        filtered_events = []
        for event in in_memory_session.events:
            if should_sync_event(event):
                filtered_events.append(event)

        logger.info(f"  Filtered to {len(filtered_events)} text transcription events")

        # Create DatabaseSessionService
        # Note: ADK tables (adk_sessions, adk_events) will be created in public schema
        # because Neon pooler doesn't support search_path in connection options
        db_service = DatabaseSessionService(db_url=DATABASE_URL)

        # Create new session in database with same data
        db_session = await db_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            state=in_memory_session.state,  # Transfer state (includes interview_id)
        )

        logger.info(f"Created DB session: {db_session.id}")

        # Sync filtered events to database in batches
        total_events = len(filtered_events)
        synced_events = 0
        failed_events = 0
        batch_size = 50  # Sync 50 events in parallel per batch

        logger.info(f"Starting batch sync of {total_events} events (batch_size={batch_size})...")

        for i in range(0, total_events, batch_size):
            batch = filtered_events[i : i + batch_size]

            # Enrich events with transcription data before syncing
            # (ADK's append_event only persists content field)
            enriched_batch = [enrich_event_content_with_transcriptions(event) for event in batch]

            # Sync batch in parallel using asyncio.gather
            tasks = [
                db_service.append_event(session=db_session, event=event) for event in enriched_batch
            ]

            try:
                # Execute all tasks in this batch concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes and failures
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_events += 1
                        logger.error(f"Failed to sync event {i + idx + 1}/{total_events}: {result}")
                    else:
                        synced_events += 1

            except Exception as batch_error:
                logger.error(f"Batch sync failed: {batch_error}")
                failed_events += len(batch)

        # Final summary
        logger.info(
            f"Sync complete: {synced_events} succeeded, "
            f"{failed_events} failed, {total_events} total"
        )

        # Cleanup - remove from active sessions
        del active_sessions[session_key]

        return {
            "success": True,
            "session_key": session_key,
            "db_session_id": db_session.id,
            "events_synced": synced_events,
            "events_failed": failed_events,
            "total_events": total_events,
            "state": in_memory_session.state,
        }

    except Exception as e:
        logger.error(f"Failed to sync session {session_key}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "session_key": session_key,
        }
