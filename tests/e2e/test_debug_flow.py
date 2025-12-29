"""Debug test to show conversation flow."""
import pytest
from websocket_helper import WebSocketTestClient


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_show_conversation_flow(
    orchestrator_server,
    google_agent_server,
    test_user_id,
    test_interview_id,
    get_session,
):
    """Show the full conversation flow with LLM responses."""
    client = WebSocketTestClient(test_user_id, test_interview_id)

    try:
        await client.connect()

        # Phase 1: Routing
        print("\n" + "=" * 80)
        print("USER: Hello, I want to practice interviews")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("Hello, I want to practice interviews")
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:300]}...")

        # Phase 2: Payment
        print("\n" + "=" * 80)
        print("USER: I'd like a Google system design interview")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("I'd like a Google system design interview")
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:300]}...")

        session = get_session(test_user_id, test_interview_id)
        print(f"\n✅ Phase: {session['state']['interview_phase']}, Payment: {session['state']['payment_completed']}")

        # Phase 3: Intro
        print("\n" + "=" * 80)
        print("USER: My name is John")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("My name is John")
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        print("\n" + "=" * 80)
        print("USER: I have 5 years of experience")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("I have 5 years of experience")
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        print("\n" + "=" * 80)
        print("USER: I work in distributed systems")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("I work in distributed systems")
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        print("\n" + "=" * 80)
        print("USER: I've built URL shorteners and caching systems")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("I've built URL shorteners and caching systems", wait_for_complete=True)
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        session = get_session(test_user_id, test_interview_id)
        print(f"\n✅ Phase: {session['state']['interview_phase']}")
        print(f"✅ Candidate info: {session['state'].get('candidate_info')}")
        print(f"✅ Interview question: {session['state'].get('interview_question')}")
        print(f"✅ Tool calls: {[tc['name'] for tc in session['tool_calls']]}")

        # Phase 4: Design
        import asyncio
        await asyncio.sleep(0.5)

        client.messages.clear()
        print("\n" + "=" * 80)
        print("USER: Here's my URL shortener architecture. What do you think?")
        print("=" * 80)
        await client.send_and_wait(
            "Here's my URL shortener architecture. What do you think?",
            wait_for_complete=True,
            timeout=45.0
        )
        llm_response = client.get_text_responses()
        print(f"LLM ({len(llm_response)} chars): {llm_response[:400]}...")

        session = get_session(test_user_id, test_interview_id)
        print(f"\n✅ Final Phase: {session['state']['interview_phase']}")
        print(f"✅ Remote initialized: {session['state'].get('remote_session_initialized', 'NOT SET')}")
        print(f"✅ All tool calls: {[tc['name'] for tc in session['tool_calls']]}")

    finally:
        await client.close()
