"""Pytest fixtures for E2E tests."""

import logging
import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

# Load test environment
test_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(test_env_path)

# Add services to path
services_path = Path(__file__).parent.parent.parent / "services"
orchestrator_path = services_path / "interview-orchestrator"
google_agent_path = services_path / "google-agent"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def google_agent_server():
    """Start Google agent server via subprocess."""
    logger.info("🚀 Starting Google agent server...")
    process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=google_agent_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get(
                "http://localhost:8001/.well-known/agent-card.json", timeout=2.0
            )
            if response.status_code == 200:
                logger.info("✅ Google agent server ready")
                break
        except Exception:
            if i == max_retries - 1:
                process.kill()
                raise RuntimeError("Google agent server failed to start")
            time.sleep(1)

    yield process

    # Cleanup - force kill if needed
    logger.info("🛑 Stopping Google agent server...")
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server didn't stop gracefully, force killing...")
        process.kill()
        process.wait()
    logger.info("✅ Google agent server stopped")


@pytest.fixture(scope="session")
def orchestrator_server():
    """Start orchestrator WebSocket server via subprocess."""
    logger.info("🚀 Starting orchestrator server...")

    # Use python3 from orchestrator's venv
    orchestrator_venv_python = os.path.join(
        orchestrator_path, ".venv", "bin", "python3"
    )
    if not os.path.exists(orchestrator_venv_python):
        # Fallback to system python if venv doesn't exist
        orchestrator_venv_python = "python3"

    # Load test environment variables
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

    # Use test DATABASE_URL to avoid polluting production
    test_db_url = os.getenv("DATABASE_URL")

    process = subprocess.Popen(
        [
            orchestrator_venv_python,
            "-m",
            "uvicorn",
            "interview_orchestrator.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=orchestrator_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "ENV": "test",
            "AUTO_APPROVE_PAYMENTS": "true",
            "DATABASE_URL": test_db_url,  # Use test database, not production!
        },
    )

    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get("http://localhost:8000/health", timeout=2.0)
            if response.status_code == 200:
                logger.info("✅ Orchestrator server ready")
                break
        except Exception as e:
            if i == max_retries - 1:
                # Capture stderr to see what went wrong
                stderr_output = ""
                stdout_output = ""
                try:
                    stdout_output = process.stdout.read().decode(
                        "utf-8", errors="replace"
                    )[:2000]
                    stderr_output = process.stderr.read().decode(
                        "utf-8", errors="replace"
                    )[:2000]
                except Exception:
                    pass

                process.kill()
                error_msg = f"Orchestrator server failed to start after {max_retries} attempts.\n"
                error_msg += f"Last error: {e}\n"
                if stderr_output:
                    error_msg += f"\n=== STDERR ===\n{stderr_output}\n"
                if stdout_output:
                    error_msg += f"\n=== STDOUT ===\n{stdout_output}\n"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            time.sleep(1)

    yield process

    # Cleanup
    logger.info("🛑 Stopping orchestrator server...")
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server didn't stop gracefully, force killing...")
        process.kill()
        process.wait()
    logger.info("✅ Orchestrator server stopped")

    # Clean up database after orchestrator is fully stopped
    logger.info("🧹 Cleaning up test database...")
    try:
        import asyncio
        import asyncpg

        # Wait a bit to ensure all data is synced
        time.sleep(2)

        # Load test .env to get test DATABASE_URL
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
        db_url = os.getenv("DATABASE_URL")

        if db_url:

            async def cleanup():
                conn = await asyncpg.connect(db_url)
                try:
                    # Truncate all ADK tables (cascading to handle foreign keys)
                    await conn.execute(
                        "TRUNCATE TABLE sessions, events, user_states, app_states CASCADE"
                    )
                    logger.info("✅ Truncated all test tables")
                finally:
                    await conn.close()

            # Run cleanup synchronously
            loop = asyncio.new_event_loop()
            loop.run_until_complete(cleanup())
            loop.close()
    except Exception as e:
        logger.warning(f"Database cleanup failed: {e}")


@pytest.fixture
def test_user_id():
    """Generate test user ID."""
    return "test_user_e2e"


@pytest.fixture
def test_interview_id():
    """Generate unique interview ID for each test."""
    import uuid

    return uuid.uuid4().hex
