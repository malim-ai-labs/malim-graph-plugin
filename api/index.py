import sys
import os

# Ensure the local 'src' directory is in the Python path for Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from malimgraph.plugin import mcp

# Expose the ASGI application using the FastMCP SSE application method
# Vercel's Serverless Python runtime looks for the 'app' variable explicitly.
app = mcp.sse_app()
