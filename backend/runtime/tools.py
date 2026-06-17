import math
import httpx
from datetime import datetime
from langchain_core.tools import tool

from config import settings


@tool
def web_search(query: str) -> str:
    """Search the web for current information. Returns top results."""
    if not settings.TAVILY_API_KEY:
        return "Web search unavailable: TAVILY_API_KEY not set in .env."
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query, max_results=5)
        results = response.get("results", [])
        if not results:
            return "No results found."
        output = []
        for r in results:
            output.append(f"**{r.get('title', '')}**\n{r.get('url', '')}\n{r.get('content', '')}")
        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely. Example: '2 + 2 * 10'"""
    # Whitelist safe names
    safe_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    safe_names.update({"abs": abs, "round": round, "pow": pow, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, safe_names)
        return str(result)
    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def get_current_datetime() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")


@tool
def http_request(url: str, method: str = "GET", body: str = "") -> str:
    """Make an HTTP request to a URL. Returns the response body (first 2000 chars)."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.request(method.upper(), url, content=body or None)
        return response.text[:2000]
    except Exception as e:
        return f"HTTP request error: {str(e)}"


TOOL_REGISTRY: dict = {
    "web_search": web_search,
    "calculator": calculator,
    "get_current_datetime": get_current_datetime,
    "http_request": http_request,
}


def get_tools_for_agent(tool_names: list) -> list:
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]


AVAILABLE_TOOLS = list(TOOL_REGISTRY.keys())
