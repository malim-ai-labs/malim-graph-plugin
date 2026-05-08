import sys
import os

# Ensure the local 'src' directory is in the Python path for Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from malimgraph.plugin import mcp
from starlette.routing import Route
from starlette.responses import JSONResponse

# Expose the ASGI application using the FastMCP SSE application method
# Vercel's Serverless Python runtime looks for the 'app' variable explicitly.
app = mcp.sse_app()

async def root_handler(request):
    return JSONResponse({
        "status": "MalimGraph MCP Server is running",
        "endpoints": ["/sse", "/messages"],
        "instructions": "Connect your MCP client to the /sse endpoint."
    })

app.routes.append(Route("/", endpoint=root_handler))
