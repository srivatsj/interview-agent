# ADK Quick Start Examples

## Minimal Agent

```python
from google.adk.agents import Agent

root_agent = Agent(
    name='hello_agent',
    model='gemini-2.5-flash',
    description='A simple greeting agent',
    instruction='Greet users warmly and answer their questions'
)
```

Test with:
```bash
adk run agent_module.root_agent "Hello!"
```

## Agent with Custom Tool

```python
from google.adk.agents import Agent

def get_current_time(timezone: str = "UTC") -> dict:
    """
    Get current time in specified timezone.
    
    Use this when the user asks for the current time or date.
    
    Args:
        timezone: Timezone name (e.g., "UTC", "America/New_York", "Asia/Tokyo")
    
    Returns:
        dict with current_time, current_date, and timezone
    """
    from datetime import datetime
    import pytz
    
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timezone": timezone
    }

root_agent = Agent(
    name='time_agent',
    model='gemini-2.5-flash',
    description='Tells current time in any timezone',
    instruction='Use the get_current_time tool to answer time-related queries',
    tools=[get_current_time]
)
```

## Sequential Pipeline

```python
from google.adk.agents import LlmAgent, SequentialAgent

# Step 1: Generate content
generator = LlmAgent(
    name="ContentGenerator",
    model="gemini-2.5-flash",
    instruction="Generate a short blog post about the given topic",
    output_key="draft_content"
)

# Step 2: Review content
reviewer = LlmAgent(
    name="ContentReviewer",
    model="gemini-2.5-flash",
    instruction="""Review the content: {draft_content}
    
    Check for:
    - Grammar and spelling
    - Clarity and coherence
    - Engaging tone
    
    Provide specific feedback.""",
    output_key="review_feedback"
)

# Step 3: Revise based on feedback
reviser = LlmAgent(
    name="ContentReviser",
    model="gemini-2.5-flash",
    instruction="""Revise the content based on feedback:
    
    Original: {draft_content}
    Feedback: {review_feedback}
    
    Produce the final, polished version."""
)

# Combine into pipeline
root_agent = SequentialAgent(
    name="ContentPipeline",
    sub_agents=[generator, reviewer, reviser],
    description="Generates, reviews, and refines blog content"
)
```

## Parallel Data Gathering

```python
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import GoogleSearchTool

# Create search tool
search_tool = GoogleSearchTool()

# Define parallel researchers
tech_researcher = LlmAgent(
    name="TechResearcher",
    model="gemini-2.5-flash",
    instruction="Research the latest technology trends using Google Search",
    tools=[search_tool],
    output_key="tech_findings"
)

market_researcher = LlmAgent(
    name="MarketResearcher",
    model="gemini-2.5-flash",
    instruction="Research market analysis and business trends using Google Search",
    tools=[search_tool],
    output_key="market_findings"
)

# Run researchers in parallel
parallel_research = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[tech_researcher, market_researcher]
)

# Synthesize results
synthesizer = LlmAgent(
    name="ReportSynthesizer",
    model="gemini-2.5-flash",
    instruction="""Synthesize research findings into a cohesive report:
    
    Technology Trends: {tech_findings}
    Market Analysis: {market_findings}
    
    Create a structured report with key insights and recommendations."""
)

# Complete workflow
root_agent = SequentialAgent(
    name="ResearchWorkflow",
    sub_agents=[parallel_research, synthesizer],
    description="Conducts parallel research and synthesizes findings"
)
```

## Coordinator with Specialists

```python
from google.adk.agents import LlmAgent

# Define specialist agents
weather_agent = LlmAgent(
    name="WeatherSpecialist",
    model="gemini-2.5-flash",
    description="Provides weather information and forecasts for any location",
    instruction="Use weather data tools to provide accurate weather information",
    tools=[get_weather_tool, get_forecast_tool]
)

calculator_agent = LlmAgent(
    name="CalculatorSpecialist", 
    model="gemini-2.5-flash",
    description="Performs mathematical calculations and data analysis",
    instruction="Solve mathematical problems and analyze numerical data",
    tools=[calculator_tool]
)

translator_agent = LlmAgent(
    name="TranslatorSpecialist",
    model="gemini-2.5-flash",
    description="Translates text between languages",
    instruction="Translate text accurately while preserving meaning and tone",
    tools=[translate_tool]
)

# Coordinator routes to appropriate specialist
root_agent = LlmAgent(
    name="Coordinator",
    model="gemini-2.5-flash",
    description="Intelligent coordinator that routes requests to specialized agents",
    instruction="""Analyze user requests and delegate to the appropriate specialist:
    
    - WeatherSpecialist: For weather, forecasts, climate queries
    - CalculatorSpecialist: For math, calculations, data analysis
    - TranslatorSpecialist: For language translation
    
    Transfer control to the specialist agent best suited for the task.""",
    sub_agents=[weather_agent, calculator_agent, translator_agent]
)
```

## Loop-Based Refinement

```python
from google.adk.agents import LlmAgent, LoopAgent

# Generator creates content
generator = LlmAgent(
    name="StoryGenerator",
    model="gemini-2.5-flash",
    instruction="Generate a creative short story based on the user's prompt",
    output_key="story"
)

# Critic evaluates quality
critic = LlmAgent(
    name="StoryCritic",
    model="gemini-2.5-flash",
    instruction="""Evaluate the story: {story}
    
    Rate on a scale of 1-10 for:
    - Creativity
    - Coherence
    - Engagement
    
    If average score is below 7, suggest specific improvements.
    If score is 7 or above, respond with "APPROVED".""",
    output_key="critique"
)

# Reviser improves content
reviser = LlmAgent(
    name="StoryReviser",
    model="gemini-2.5-flash",
    instruction="""Improve the story based on critique:
    
    Original: {story}
    Feedback: {critique}
    
    Create an improved version.""",
    output_key="story"
)

# Termination condition
def is_approved(context) -> bool:
    critique = context.state.get('critique', '')
    return 'APPROVED' in critique.upper()

# Loop until approved or max iterations
root_agent = LoopAgent(
    name="StoryRefinementLoop",
    sub_agents=[generator, critic, reviser],
    termination_condition=is_approved,
    max_iterations=3
)
```

## Agent with Built-in Tools

```python
from google.adk.agents import Agent
from google.adk.tools import GoogleSearchTool, CodeExecutionTool

root_agent = Agent(
    name='research_assistant',
    model='gemini-2.5-flash',
    description='Research assistant with search and computation capabilities',
    instruction="""You are a research assistant that can:
    1. Search the web for current information
    2. Execute Python code for calculations and data processing
    
    Use these tools to provide accurate, well-researched answers.""",
    tools=[
        GoogleSearchTool(),
        CodeExecutionTool()
    ]
)
```

## Multi-Model Agent

```python
from google.adk.agents import LlmAgent, SequentialAgent

# Fast model for simple task
greeter = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash",  # Fast model
    instruction="Greet the user warmly",
    output_key="greeting"
)

# Advanced model for complex task
analyzer = LlmAgent(
    name="RequestAnalyzer",
    model="gemini-2.5-flash",  # Advanced model
    instruction="""Analyze the user's request in detail.
    
    Greeting: {greeting}
    
    Determine the intent, required actions, and best approach."""
)

root_agent = SequentialAgent(
    name="MultiModelWorkflow",
    sub_agents=[greeter, analyzer]
)
```

## Agent with Session State

```python
from google.adk.agents import Agent

root_agent = Agent(
    name='stateful_assistant',
    model='gemini-2.5-flash',
    description='Assistant that remembers conversation context',
    instruction="""You are a helpful assistant. 
    
    Track the following in session state:
    - User preferences (stored as state['user_prefs'])
    - Conversation topics (stored as state['topics'])
    - Important facts mentioned (stored as state['facts'])
    
    Reference these to provide personalized responses."""
)

# In tool or callback, access/modify state:
# context.state['user_prefs'] = {'theme': 'dark', 'language': 'en'}
# context.state['topics'] = ['weather', 'sports']
```

## Custom Tool with Error Handling

```python
import requests
from typing import Optional

def fetch_api_data(endpoint: str, params: Optional[dict] = None) -> dict:
    """
    Fetch data from external API with robust error handling.
    
    Use this to retrieve data from the company API.
    
    Args:
        endpoint: API endpoint path (e.g., "users", "products/123")
        params: Optional query parameters as dictionary
    
    Returns:
        dict with status, data (if successful), or error message
    """
    base_url = "https://api.example.com"
    
    try:
        response = requests.get(
            f"{base_url}/{endpoint}",
            params=params or {},
            timeout=10
        )
        response.raise_for_status()
        
        return {
            "status": "success",
            "data": response.json()
        }
        
    except requests.HTTPError as e:
        return {
            "status": "error",
            "error_type": "http_error",
            "status_code": e.response.status_code,
            "message": f"API returned error: {e.response.status_code}",
            "suggestion": "Verify the endpoint path and try again"
        }
        
    except requests.Timeout:
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Request timed out after 10 seconds",
            "suggestion": "Try again or check API status"
        }
        
    except requests.RequestException as e:
        return {
            "status": "error",
            "error_type": "network_error",
            "message": f"Network error: {str(e)}",
            "suggestion": "Check internet connection and retry"
        }

root_agent = Agent(
    name='api_agent',
    model='gemini-2.5-flash',
    tools=[fetch_api_data]
)
```

## Testing Agent Programmatically

```python
import asyncio
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService

async def test_agent():
    # Setup
    session_service = InMemorySessionService()
    runner = InMemoryRunner(session_service=session_service)
    
    # Run agent
    print("Testing agent...")
    events = []
    async for event in runner.run(
        agent=root_agent,
        app_name="test_app",
        user_id="test_user",
        query="What's the weather like today?"
    ):
        events.append(event)
        if event.type == "model_response":
            print(f"Response: {event.data.text}")
    
    print(f"Total events: {len(events)}")
    
    # Access session state
    session = await session_service.get_session(
        app_name="test_app",
        user_id="test_user"
    )
    print(f"Final state: {session.state}")

# Run test
asyncio.run(test_agent())
```
