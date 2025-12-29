"""Tests for simple interview POC.

Tests the stability and reliability of:
1. Sequential agent phase transitions
2. Custom agent forced tool calls
3. Multi-turn conversation flow
"""

import logging

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestSimpleInterviewFlow:
    """Test the complete interview flow is deterministic and stable."""

    async def test_complete_flow_deterministic(self):
        """Test that interview phases execute in guaranteed order."""
        from orchestrator2.agents.simple_interview import root_agent

        # Create session service and session
        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )

        # Create runner
        runner = Runner(
            agent=root_agent,
            app_name="test_app",
            session_service=session_service
        )

        # Helper to run a message and get session state
        async def run_message(text: str):
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session",
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=text)]
                ),
            ):
                pass  # Process all events

            # Get session state
            sessions_response = await session_service.list_sessions(app_name="test_app", user_id="test_user")
            return sessions_response.sessions[0].state

        # Turn 1: Should trigger intro phase
        state1 = await run_message("Hi, I'm Alice and I have 5 years of experience")

        # Verify intro phase completed
        assert "candidate_name" in state1, "Intro should collect name"
        assert state1["candidate_name"] == "Alice"
        assert state1["candidate_experience"] == 5
        assert state1["phase_complete"] == "intro"

        logger.info(f"✅ Phase 1 (Intro) complete: {state1}")

        # Turn 2: Should trigger interview phase with forced expert call
        state2 = await run_message("I designed a distributed caching system using Redis")

        # Verify expert was called
        assert "expert_calls" in state2, "Expert should be called"
        assert state2["expert_calls"] >= 1, "Expert called at least once"
        assert "expert_feedback" in state2, "Expert feedback stored"

        logger.info(f"✅ Phase 2 (Interview) complete: {state2}")
        logger.info(f"✅ Expert calls: {state2['expert_calls']}")

        # Turn 3: Another interview turn - expert MUST be called again
        state3 = await run_message("For scalability, I used consistent hashing")

        # Verify expert called again
        assert state3["expert_calls"] >= 2, "Expert should be called for each turn"

        logger.info(f"✅ Turn 3 complete: Expert calls={state3['expert_calls']}")

    async def test_forced_expert_calls_every_turn(self):
        """Test that expert is ALWAYS called, never skipped."""
        from orchestrator2.agents.simple_interview import root_agent

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )

        runner = Runner(
            agent=root_agent,
            app_name="test_app",
            session_service=session_service
        )

        async def run_message(text: str):
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session",
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=text)]
                ),
            ):
                pass
            sessions_response = await session_service.list_sessions(app_name="test_app", user_id="test_user")
            return sessions_response.sessions[0].state

        # Intro phase
        await run_message("I'm Bob with 3 years experience")

        # Multiple interview turns
        test_messages = [
            "I use microservices architecture",
            "I handle errors with circuit breakers",
            "I monitor with Prometheus and Grafana",
            "I deploy using Kubernetes"
        ]

        for i, msg in enumerate(test_messages, 1):
            state = await run_message(msg)

            # Verify expert called for THIS turn
            expert_calls = state.get("expert_calls", 0)
            assert expert_calls == i, \
                f"Expert should be called for turn {i} (got {expert_calls})"

            logger.info(f"✅ Turn {i}: Expert called (total: {expert_calls})")

        logger.info("✅ ALL turns forced expert calls - 100% reliability!")

    async def test_state_persistence_across_phases(self):
        """Test that state persists correctly across sequential phases."""
        from orchestrator2.agents.simple_interview import root_agent

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )

        runner = Runner(
            agent=root_agent,
            app_name="test_app",
            session_service=session_service
        )

        async def run_message(text: str):
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session",
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=text)]
                ),
            ):
                pass
            sessions_response = await session_service.list_sessions(app_name="test_app", user_id="test_user")
            return sessions_response.sessions[0].state

        # Intro: Set candidate info
        state1 = await run_message("I'm Charlie, 7 years experience")

        candidate_name = state1.get("candidate_name")
        assert candidate_name == "Charlie"

        # Interview: Candidate name should still be available
        state2 = await run_message("I design REST APIs")

        # Verify name persisted
        assert state2.get("candidate_name") == "Charlie"
        assert "expert_feedback" in state2

        # Expert feedback should mention the candidate's name
        feedback = state2["expert_feedback"]
        assert "Charlie" in feedback, "Expert should use candidate name"

        logger.info("✅ State persists correctly across phases")


@pytest.mark.asyncio
class TestPatternStability:
    """Test that patterns are more stable than LLM-based approaches."""

    async def test_sequential_never_skips_phases(self):
        """Sequential agent GUARANTEES all phases run."""
        from orchestrator2.agents.simple_interview import root_agent

        session_service = InMemorySessionService()

        # Run 10 times to verify consistency
        for run in range(10):
            await session_service.create_session(
                app_name="test_app",
                user_id=f"test_user_{run}",
                session_id=f"test_session_{run}"
            )

            runner = Runner(
                agent=root_agent,
                app_name="test_app",
                session_service=session_service
            )

            async def run_message(text: str):
                async for event in runner.run_async(
                    user_id=f"test_user_{run}",
                    session_id=f"test_session_{run}",
                    new_message=genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_text(text=text)]
                    ),
                ):
                    pass
                sessions_response = await session_service.list_sessions(app_name="test_app", user_id=f"test_user_{run}")
                return sessions_response.sessions[0].state

            # Intro
            state1 = await run_message(f"I'm User{run} with {run} years")

            assert state1.get("phase_complete") == "intro", \
                f"Run {run}: Intro phase should complete"

            # Interview
            state2 = await run_message("Technical answer here")

            assert state2.get("expert_calls", 0) >= 1, \
                f"Run {run}: Expert should be called"

        logger.info("✅ 10/10 runs: Phases executed in order - 100% reliability")

    async def test_custom_agent_never_skips_tool(self):
        """Custom agent GUARANTEES tool is called."""
        from orchestrator2.agents.simple_interview import root_agent

        session_service = InMemorySessionService()

        # Run 20 interview turns across multiple sessions
        total_turns = 0
        total_expert_calls = 0

        for session_num in range(5):
            await session_service.create_session(
                app_name="test_app",
                user_id=f"test_user_{session_num}",
                session_id=f"test_session_{session_num}"
            )

            runner = Runner(
                agent=root_agent,
                app_name="test_app",
                session_service=session_service
            )

            async def run_message(text: str):
                async for event in runner.run_async(
                    user_id=f"test_user_{session_num}",
                    session_id=f"test_session_{session_num}",
                    new_message=genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_text(text=text)]
                    ),
                ):
                    pass
                sessions_response = await session_service.list_sessions(app_name="test_app", user_id=f"test_user_{session_num}")
                return sessions_response.sessions[0].state

            # Intro
            await run_message(f"I'm User{session_num} with 5 years")

            # 4 interview turns per session
            for turn in range(4):
                state = await run_message(f"Technical answer {turn}")
                total_turns += 1

            total_expert_calls += state.get("expert_calls", 0)

        # EVERY turn should have called expert
        assert total_expert_calls == total_turns, \
            f"Expected {total_turns} expert calls, got {total_expert_calls}"

        logger.info(f"✅ {total_turns}/{total_turns} turns called expert - 100% reliability")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
