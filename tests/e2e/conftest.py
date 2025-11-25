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

    # Write logs to temp files instead of PIPE to avoid buffer issues
    import tempfile

    stdout_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="_google_stdout.log")
    stderr_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="_google_stderr.log")

    process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=google_agent_path,
        stdout=stdout_file,
        stderr=stderr_file,
    )

    # Store file handles for cleanup
    process._stdout_file = stdout_file
    process._stderr_file = stderr_file

    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get("http://localhost:8001/.well-known/agent-card.json", timeout=2.0)
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

    # Clean up temp log files
    try:
        if hasattr(process, "_stdout_file"):
            process._stdout_file.close()
            os.unlink(process._stdout_file.name)
        if hasattr(process, "_stderr_file"):
            process._stderr_file.close()
            os.unlink(process._stderr_file.name)
    except Exception as e:
        logger.warning(f"Could not clean up Google agent log files: {e}")


@pytest.fixture(scope="session")
def orchestrator_server():
    """Start orchestrator WebSocket server via subprocess."""
    logger.info("🚀 Starting orchestrator server...")

    # Use python3 from orchestrator's venv
    orchestrator_venv_python = os.path.join(orchestrator_path, ".venv", "bin", "python3")
    if not os.path.exists(orchestrator_venv_python):
        # Fallback to system python if venv doesn't exist
        orchestrator_venv_python = "python3"

    # Load test environment variables
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

    # Use test DATABASE_URL to avoid polluting production
    test_db_url = os.getenv("DATABASE_URL")

    # Write logs to temp files instead of PIPE to avoid buffer issues
    import tempfile

    stdout_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="_orch_stdout.log")
    stderr_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="_orch_stderr.log")

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
        stdout=stdout_file,
        stderr=stderr_file,
        env={
            **os.environ,
            "ENV": "test",
            "AUTO_APPROVE_PAYMENTS": "true",
            "DATABASE_URL": test_db_url,  # Use test database, not production!
        },
    )

    # Store file handles for cleanup
    process._stdout_file = stdout_file
    process._stderr_file = stderr_file

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
                # Read from temp files to see what went wrong
                stderr_output = ""
                stdout_output = ""
                try:
                    stdout_file.flush()
                    stderr_file.flush()
                    stdout_file.seek(0)
                    stderr_file.seek(0)
                    stdout_output = stdout_file.read()[:2000]
                    stderr_output = stderr_file.read()[:2000]
                except Exception as read_error:
                    logger.warning(f"Could not read log files: {read_error}")

                process.kill()
                error_msg = f"Orchestrator server failed to start after {max_retries} attempts.\n"
                error_msg += f"Last error: {e}\n"
                if stderr_output:
                    error_msg += f"\n=== STDERR ===\n{stderr_output}\n"
                if stdout_output:
                    error_msg += f"\n=== STDOUT ===\n{stdout_output}\n"
                logger.error(error_msg)

                # Clean up temp files
                stdout_file.close()
                stderr_file.close()
                os.unlink(stdout_file.name)
                os.unlink(stderr_file.name)

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

    # Clean up temp log files
    try:
        if hasattr(process, "_stdout_file"):
            process._stdout_file.close()
            os.unlink(process._stdout_file.name)
        if hasattr(process, "_stderr_file"):
            process._stderr_file.close()
            os.unlink(process._stderr_file.name)
    except Exception as e:
        logger.warning(f"Could not clean up log files: {e}")

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


@pytest.fixture
def get_session(orchestrator_server):
    """Get session state and tool calls for assertions.

    Returns dict with 'state' and 'tool_calls'.
    """

    def _get_session(user_id: str, interview_id: str) -> dict:
        import httpx

        try:
            response = httpx.get(
                f"http://localhost:8000/debug/session/{user_id}/{interview_id}", timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return {
                    "state": data.get("state", {}),
                    "tool_calls": data.get("tool_calls", []),
                }
            else:
                logger.warning(f"⚠️ {data.get('error')}")
                return {"state": {}, "tool_calls": []}
        except Exception as e:
            logger.warning(f"⚠️ Failed to get session: {e}")
            return {"state": {}, "tool_calls": []}

    return _get_session
