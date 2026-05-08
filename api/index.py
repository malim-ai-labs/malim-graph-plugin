import sys
import os

# Ensure the local 'src' directory is in the Python path for Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from malimgraph.plugin import mcp
from starlette.routing import Route
from starlette.responses import HTMLResponse

# Expose the ASGI application using the FastMCP SSE application method
# Vercel's Serverless Python runtime looks for the 'app' variable explicitly.
app = mcp.sse_app()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MalimGraph MCP Status</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: 'Courier New', Courier, monospace; padding: 2rem; line-height: 1.6; }
        h1, h2 { color: #58a6ff; font-weight: normal; }
        .success { color: #3fb950; font-weight: bold; }
        .container { max-width: 800px; margin: 0 auto; border: 1px solid #30363d; padding: 2rem; border-radius: 6px; background-color: #161b22; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        pre { background: #010409; padding: 1rem; border-radius: 4px; overflow-x: auto; color: #e6edf3; border: 1px solid #30363d; font-size: 0.95em; }
        .prompt::before { content: "$ "; color: #3fb950; font-weight: bold; }
        .highlight { color: #d2a8ff; }
        .blink { animation: blinker 1s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>&gt; MalimGraph MCP Server <span class="blink">_</span></h1>
        <p>SYSTEM.STATUS_CHECK()   -> <span class="success">[ONLINE]</span></p>
        <p>CONNECTION.TRANSPORT()  -> <span class="highlight">HTTP Server-Sent Events (SSE)</span></p>
        <p>CONNECTION.ENDPOINT()   -> <span class="highlight">/api/sse</span></p>
        
        <hr style="border: 0; border-top: 1px dashed #30363d; margin: 2rem 0;">
        
        <h2>// INSTALLATION.CLAUDE_CODE()</h2>
        <p>To connect Claude Code locally to this remote Vercel-hosted MCP endpoint:</p>
        <pre><code class="prompt">npx -y @modelcontextprotocol/inspector https://mcpserver.malim.my/api/sse</code></pre>

        <h2>// INSTALLATION.CLAUDE_DESKTOP()</h2>
        <p>Append the following to your <code>claude_desktop_config.json</code> using a remote proxy tool if supported, or point it to your Vercel deployment URL using a proxy runner:</p>
        <pre><code>{
  "mcpServers": {
    "malimgraph-remote": {
      "command": "npx",
      "args": [
        "-y", 
        "@modelcontextprotocol/inspector", 
        "https://mcpserver.malim.my/api/sse"
      ]
    }
  }
}</code></pre>
        
        <hr style="border: 0; border-top: 1px dashed #30363d; margin: 2rem 0;">
        <p style="font-size: 0.85em; opacity: 0.8; text-align: center;">Powered by Malim AI Labs Agentic Framework</p>
    </div>
</body>
</html>
"""

async def root_handler(request):
    return HTMLResponse(content=HTML_TEMPLATE)

app.routes.append(Route("/", endpoint=root_handler))
