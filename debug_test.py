"""Debug script to show conversation flow in detail."""
import asyncio
import base64
import httpx
from pathlib import Path
import sys
sys.path.insert(0, "/Users/srivatsj/personal-projects/interview-agent/tests")
from e2e.websocket_helper import WebSocketTestClient

async def main():
    test_user_id = "debug_user"
    test_interview_id = "debug_interview_123"

    client = WebSocketTestClient(test_user_id, test_interview_id)

    try:
        print("=" * 80)
        print("CONNECTING TO WEBSOCKET")
        print("=" * 80)
        await client.connect()

        # Phase 1: Routing
        print("\n" + "=" * 80)
        print("PHASE 1: ROUTING - User says hello")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("Hello, I want to practice interviews")
        llm_response = client.get_text_responses()
        print(f"LLM Response ({len(llm_response)} chars):")
        print(f"  {llm_response[:300]}...")
        print(f"✅ Received {len(client.messages)} WebSocket messages")

        # Phase 2: Payment
        print("\n" + "=" * 80)
        print("PHASE 2: PAYMENT - User selects Google system design")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait("I'd like a Google system design interview")
        llm_response = client.get_text_responses()
        print(f"LLM Response ({len(llm_response)} chars):")
        print(f"  {llm_response[:300]}...")
        print(f"✅ Received {len(client.messages)} WebSocket messages")

        # Get session state
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"http://localhost:8000/debug/session/{test_user_id}/{test_interview_id}"
            )
            session = resp.json()
            print(f"\n📊 SESSION STATE:")
            print(f"  Phase: {session['state'].get('interview_phase')}")
            print(f"  Payment: {session['state'].get('payment_completed')}")
            print(f"  Tool calls: {[tc['name'] for tc in session['tool_calls']]}")

        # Phase 3: Intro - Multi-turn
        print("\n" + "=" * 80)
        print("PHASE 3: INTRO - Collecting candidate info")
        print("=" * 80)

        client.messages.clear()
        await client.send_and_wait("My name is John")
        llm_response = client.get_text_responses()
        print(f"\nTurn 1 - 'My name is John':")
        print(f"  LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        client.messages.clear()
        await client.send_and_wait("I have 5 years of experience")
        llm_response = client.get_text_responses()
        print(f"\nTurn 2 - '5 years experience':")
        print(f"  LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        client.messages.clear()
        await client.send_and_wait("I work in distributed systems")
        llm_response = client.get_text_responses()
        print(f"\nTurn 3 - 'distributed systems':")
        print(f"  LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        client.messages.clear()
        await client.send_and_wait("I've built URL shorteners and caching systems", wait_for_complete=True)
        llm_response = client.get_text_responses()
        print(f"\nTurn 4 - 'URL shorteners':")
        print(f"  LLM ({len(llm_response)} chars): {llm_response[:200]}...")

        # Get session state after intro
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"http://localhost:8000/debug/session/{test_user_id}/{test_interview_id}"
            )
            session = resp.json()
            print(f"\n📊 SESSION STATE AFTER INTRO:")
            print(f"  Phase: {session['state'].get('interview_phase')}")
            print(f"  Candidate info: {session['state'].get('candidate_info')}")
            print(f"  Interview question: {session['state'].get('interview_question')}")
            print(f"  Tool calls: {[tc['name'] for tc in session['tool_calls']]}")

        await asyncio.sleep(0.5)

        # Phase 4: Design
        print("\n" + "=" * 80)
        print("PHASE 4: DESIGN - User presents architecture")
        print("=" * 80)
        client.messages.clear()
        await client.send_and_wait(
            "Here's my URL shortener architecture. What do you think?",
            wait_for_complete=True,
            timeout=45.0
        )
        llm_response = client.get_text_responses()
        print(f"\nDesign Question Response:")
        print(f"  LLM ({len(llm_response)} chars): {llm_response[:400]}...")
        print(f"  Received {len(client.messages)} WebSocket messages")

        # Get final session state
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"http://localhost:8000/debug/session/{test_user_id}/{test_interview_id}"
            )
            session = resp.json()
            print(f"\n📊 FINAL SESSION STATE:")
            print(f"  Phase: {session['state'].get('interview_phase')}")
            print(f"  Remote initialized: {session['state'].get('remote_session_initialized')}")
            print(f"  Tool calls: {[tc['name'] for tc in session['tool_calls']]}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
