"""Shared session storage to avoid circular imports."""

# Store active sessions for post-interview sync
# This is imported by both app.py and routing.py
active_sessions = {}
