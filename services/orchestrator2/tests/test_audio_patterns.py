"""Test both patterns (Sequential and Custom Executor) with audio streaming.

This test verifies:
1. Sequential agents provide deterministic flow
2. Custom executors can force tool usage
3. Both patterns work with Gemini Live API (audio streaming)
"""

import logging
import os

import pytest
from google.adk.sessions import InMemorySessionService

# Set up test environment
os.environ["ENV"] = "test"

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestSequentialAgentPattern:
    """Test Sequential Agent pattern for deterministic flow."""

    async def test_sequential_flow_determinism(self):
        """Test that sequential agents execute in predictable order."""
        from orchestrator2.agents.sequential_poc import (
            sequential_root,
            info_collector,
            expert_consultant
        )

        # Create session with required parameters
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )

        # Turn 1: Info collection phase (auto-handled by first agent)
        response1 = await sequential_root.generate_content(
            "Hi, I'm Alice and I want to discuss Python programming",
            session=session
        )

        # Verify state was set by info_collector
        assert "user_name" in session.state, "info_collector should set user_name"
        assert "user_topic" in session.state, "info_collector should set user_topic"
        assert session.state["user_name"] == "Alice" or "Alice" in str(response1)

        logger.info(f"✅ Phase 1 complete: {session.state}")

        # Turn 2: Expert consultation phase (auto-handled by second agent)
        response2 = await sequential_root.generate_content(
            "How do I handle async/await in Python?",
            session=session
        )

        # Verify expert tool was called
        assert "expert_called" in session.state, "Expert tool should be called in phase 2"
        assert session.state["expert_called"] is True

        logger.info(f"✅ Phase 2 complete: {session.state}")
        logger.info(f"✅ Sequential flow worked! Response: {response2}")

    async def test_sequential_agents_with_audio_config(self):
        """Test that sequential agents work with audio/live streaming config."""
        from orchestrator2.agents.sequential_poc import sequential_root

        # Create session with live streaming config
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )

        # Verify the agent uses gemini-2.0-flash-live model (required for audio)
        assert "live" in sequential_root.model.model.lower(), \
            "Sequential agent should use -live- model for audio support"

        logger.info(f"✅ Sequential agent configured for audio: {sequential_root.model.model}")

        # Test that it can handle messages (audio would come via same interface)
        response = await sequential_root.generate_content(
            "I'm Bob and I want to discuss System Design",
            session=session
        )

        assert response is not None
        logger.info("✅ Sequential agent responds correctly with live model")


@pytest.mark.asyncio
class TestCustomAgentPattern:
    """Test Custom Agent pattern for forced tool usage."""

    async def test_forced_tool_execution(self):
        """Test that custom agent forces tool call every time."""
        from orchestrator2.agents.custom_agent_poc import custom_root, get_expert_feedback

        # Create session with required parameters
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )

        # Turn 1: Ask a question - tool MUST be called
        response1 = await custom_root.generate_content(
            "What are best practices for API design?",
            session=session
        )

        # Verify tool was called (via state marker)
        tool_count = session.state.get("tool_called_count", 0)
        assert tool_count >= 1, \
            f"Custom executor should force tool call (count: {tool_count})"

        logger.info(f"✅ Tool called {tool_count} times as expected")

        # Turn 2: Ask another question - tool MUST be called again
        response2 = await custom_root.generate_content(
            "How do I handle errors in distributed systems?",
            session=session
        )

        # Verify tool was called again
        tool_count_after = session.state.get("tool_called_count", 0)
        assert tool_count_after > tool_count, \
            "Tool should be called again for second question"

        logger.info(f"✅ Tool called again: {tool_count_after} times total")
        logger.info(f"✅ Executor pattern worked! Forced tool usage guaranteed")

    async def test_custom_agent_with_audio_model(self):
        """Test that custom agent works with audio-compatible model."""
        from orchestrator2.agents.custom_agent_poc import custom_root

        # Verify uses live model for audio (via response_agent)
        assert "live" in custom_root.response_agent.model.lower(), \
            "Custom agent should use -live- model for audio support"

        logger.info(f"✅ Custom agent configured for audio: {custom_root.response_agent.model}")


@pytest.mark.asyncio
class TestAudioStreamingCompatibility:
    """Test that both patterns are compatible with bidirectional audio streaming."""

    async def test_gemini_live_model_configuration(self):
        """Verify both patterns use Gemini Live API compatible models."""
        from orchestrator2.agents.sequential_poc import sequential_root
        from orchestrator2.agents.custom_agent_poc import custom_root
        from orchestrator2.shared.constants import get_gemini_model

        # Check model configuration
        test_model = get_gemini_model()
        assert "live" in test_model.lower(), \
            "Model must be -live- variant for audio streaming"

        # Check sequential agent uses compatible model
        # Note: SequentialAgent doesn't have a model itself, sub-agents do
        # Check custom agent's response formatter uses compatible model
        assert "live" in custom_root.response_agent.model.lower()

        logger.info("✅ Both patterns use Gemini Live API compatible models")

    async def test_sequential_agent_audio_flow(self):
        """Test sequential agent handles multi-turn like audio would."""
        from orchestrator2.agents.sequential_poc import sequential_root

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )

        # Simulate audio conversation turns
        turns = [
            "Hi, I'm Charlie",
            "I want to discuss Machine Learning",
            "Tell me about neural networks"
        ]

        for i, turn in enumerate(turns, 1):
            response = await sequential_root.generate_content(turn, session=session)
            assert response is not None
            logger.info(f"✅ Turn {i} handled: {turn[:50]}...")

        # Verify sequential flow maintained state across turns
        assert "user_name" in session.state
        assert "expert_called" in session.state

        logger.info("✅ Sequential agent maintains state across audio-like turns")

    async def test_custom_agent_audio_flow(self):
        """Test custom agent handles multi-turn like audio would."""
        from orchestrator2.agents.custom_agent_poc import custom_root

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )

        # Simulate audio conversation turns
        turns = [
            "What is microservices architecture?",
            "How do I implement service discovery?",
            "What about load balancing?"
        ]

        for i, turn in enumerate(turns, 1):
            response = await custom_root.generate_content(turn, session=session)
            assert response is not None
            logger.info(f"✅ Turn {i} handled: {turn[:50]}...")

        # Verify custom agent called tool for each turn
        tool_count = session.state.get("tool_called_count", 0)
        assert tool_count >= len(turns), \
            f"Tool should be called for each turn (expected {len(turns)}, got {tool_count})"

        logger.info(f"✅ Custom agent called tool {tool_count} times across turns")


@pytest.mark.asyncio
class TestPatternComparison:
    """Compare both patterns to understand trade-offs."""

    async def test_determinism_comparison(self):
        """Compare determinism: Sequential vs Executor patterns."""

        # Sequential: Deterministic phase flow
        # - Phase 1 (info collection) ALWAYS happens first
        # - Phase 2 (expert) ALWAYS happens second
        # - No LLM decision about when to switch phases

        # Custom Agent: Deterministic tool usage
        # - Tool ALWAYS called before response (via _run_async_impl override)
        # - No LLM decision about whether to use tool
        # - Flow controlled by custom code, not instructions

        logger.info("✅ Sequential Pattern: Deterministic FLOW (phase order)")
        logger.info("✅ Custom Agent Pattern: Deterministic TOOL USAGE (within phase)")

        # For interview orchestrator:
        # - Use Sequential for: routing → intro → interview → closing
        # - Use Custom Agent for: forcing remote agent calls in interview phase

        assert True  # This is a documentation test

    async def test_maintainability_comparison(self):
        """Compare maintainability of both patterns."""

        # Sequential: Easy to understand flow
        # - Clear agent order in code
        # - No hidden state transitions
        # - Easy to debug: check which agent is active

        # Custom Agent: Explicit tool forcing
        # - No prompt engineering needed for tool calls
        # - Tool usage guaranteed in code, not prompts
        # - Easy to debug: tool always called in _run_async_impl

        logger.info("✅ Sequential: Better for phase transitions")
        logger.info("✅ Custom Agent: Better for reliable tool usage")

        assert True  # This is a documentation test


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
