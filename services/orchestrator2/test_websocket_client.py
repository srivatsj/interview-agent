"""Simple WebSocket client to test the interview POC."""

import asyncio
import json
import websockets


async def test_interview():
    """Test the interview flow via WebSocket."""
    uri = "ws://localhost:8002/ws/test_user"

    print("🔌 Connecting to WebSocket server...")

    async with websockets.connect(uri) as websocket:
        # Wait for connection message
        msg = await websocket.recv()
        print(f"✅ Connected: {msg}\n")

        # Turn 1: Intro phase
        print("📤 Turn 1: Sending intro message...")
        await websocket.send(json.dumps({
            "type": "message",
            "content": "Hi, I'm Alice and I have 5 years of experience"
        }))

        response = await websocket.recv()
        data = json.loads(response)
        print(f"📥 Response: {data.get('content', '')[:200]}...")
        print(f"   Phase: {data.get('phase', 'N/A')}")
        print(f"   Expert calls: {data.get('expert_calls', 0)}\n")

        # Turn 2: Interview phase (expert should be called)
        print("📤 Turn 2: Sending technical answer...")
        await websocket.send(json.dumps({
            "type": "message",
            "content": "I designed a distributed caching system using Redis"
        }))

        response = await websocket.recv()
        data = json.loads(response)
        print(f"📥 Response: {data.get('content', '')[:200]}...")
        print(f"   Phase: {data.get('phase', 'N/A')}")
        print(f"   Expert calls: {data.get('expert_calls', 0)}\n")

        # Turn 3: Another interview turn (expert should be called again)
        print("📤 Turn 3: Sending another technical answer...")
        await websocket.send(json.dumps({
            "type": "message",
            "content": "For scalability, I used consistent hashing"
        }))

        response = await websocket.recv()
        data = json.loads(response)
        print(f"📥 Response: {data.get('content', '')[:200]}...")
        print(f"   Phase: {data.get('phase', 'N/A')}")
        print(f"   Expert calls: {data.get('expert_calls', 0)}\n")

        print("✅ Test complete!")
        print("\n🎯 Expected behavior:")
        print("  - Turn 1: Intro phase, expert_calls = 0")
        print("  - Turn 2: Interview phase, expert_calls = 1")
        print("  - Turn 3: Interview phase, expert_calls = 2")


if __name__ == "__main__":
    asyncio.run(test_interview())
