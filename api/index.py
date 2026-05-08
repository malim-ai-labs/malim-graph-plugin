import sys
import os

# Ensure the local 'src' directory is in the Python path for Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from malimgraph.plugin import mcp
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Expose the ASGI application using the FastMCP SSE application method
# Vercel's Serverless Python runtime looks for the 'app' variable explicitly.
app = mcp.sse_app()

# Add CORS Middleware to allow web clients (like Claude Web) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def health_handler(request):
    return JSONResponse({"status": "online"})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MalimGraph MCP Status</title>
    <style>
        body {
            background-color: #000000;
            color: #d0d0d0;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            padding: 5rem 2rem;
            line-height: 1.7;
            margin: 0;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
            -webkit-font-smoothing: antialiased;
        }
        h1 {
            color: #ffffff;
            font-weight: 500;
            font-size: 2rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }
        .description {
            color: #888888;
            font-size: 1.05rem;
            margin-bottom: 3.5rem;
            max-width: 650px;
        }
        .status-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 4rem;
            padding: 1.5rem 0;
            border-top: 1px solid #1a1a1a;
            border-bottom: 1px solid #1a1a1a;
        }
        .status-text {
            font-size: 0.85rem;
            font-family: 'Courier New', Courier, monospace;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #666;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #444; 
        }
        .status-dot.active {
            background-color: #00ff41;
            box-shadow: 0 0 8px #00ff41, 0 0 16px #00ff41;
            animation: pulse-green 2.5s infinite ease-in-out;
        }
        .status-dot.offline {
            background-color: #ff3333;
            box-shadow: 0 0 8px #ff3333, 0 0 16px #ff3333;
            animation: pulse-red 2.5s infinite ease-in-out;
        }
        @keyframes pulse-green {
            0% { opacity: 1; box-shadow: 0 0 8px #00ff41; }
            50% { opacity: 0.4; box-shadow: 0 0 2px #00ff41; }
            100% { opacity: 1; box-shadow: 0 0 8px #00ff41; }
        }
        @keyframes pulse-red {
            0% { opacity: 1; box-shadow: 0 0 8px #ff3333; }
            50% { opacity: 0.4; box-shadow: 0 0 2px #ff3333; }
            100% { opacity: 1; box-shadow: 0 0 8px #ff3333; }
        }
        h2 {
            font-size: 0.95rem;
            color: #ffffff;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 3.5rem;
            margin-bottom: 1rem;
        }
        p {
            color: #999999;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }
        pre {
            background: #080808;
            padding: 1.25rem;
            border-radius: 4px;
            overflow-x: auto;
            color: #e0e0e0;
            border: 1px solid #1f1f1f;
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
        }
        .prompt::before {
            content: "$ ";
            color: #555;
        }
        footer {
            margin-top: 6rem;
            padding-top: 2rem;
            background: transparent;
            border-top: 1px solid #1a1a1a;
            font-size: 0.8rem;
            color: #444;
            display: flex;
            justify-content: space-between;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        a {
            color: #666;
            text-decoration: none;
            transition: color 0.2s ease;
        }
        a:hover {
            color: #fff;
        }
    </style>
</head>
<body>
    <h1>MalimGraph Plugin</h1>
    <div class="description">
        Advanced agentic knowledge infrastructure pipeline designed to extract, analyze, and orchestrate relationships from unstructured PDFs natively using the Model Context Protocol (MCP).
    </div>

    <div class="status-wrapper">
        <div class="status-dot" id="statusIndicator"></div>
        <div class="status-text" id="statusText">AWAITING BACKEND ...</div>
    </div>

    <h2>Browser Inspector UI</h2>
    <p>To debug or test this remote MCP server visually in your browser:</p>
    <pre><code class="prompt">npx -y @modelcontextprotocol/inspector https://mcpserver.malim.my/api/sse</code></pre>

    <h2>Claude Desktop (Local Stdio)</h2>
    <p>Claude Desktop officially requires mounting a local <code>stdio</code> command bridge. To natively integrate the plugin locally right now, append this to your <code>claude_desktop_config.json</code>:</p>
    <pre><code>{
  "mcpServers": {
    "malimgraph": {
      "command": "uvx",
      "args": ["malimgraph", "malimgraph-plugin"]
    }
  }
}</code></pre>

    <footer>
        <div>&copy; 2026 Malim AI Labs Limited SE. All rights reserved.</div>
        <div>
            <a href="https://github.com/malim-ai-labs/malim-graph-plugin" target="_blank">Repository</a> &nbsp; &bull; &nbsp; 
            <a href="https://ailabs.malim.my" target="_blank">Documentation</a>
        </div>
    </footer>

    <script>
        async function runHealthCheck() {
            const indicator = document.getElementById('statusIndicator');
            const text = document.getElementById('statusText');
            try {
                // Time-bound fetch request to avoid silent indefinite hangs
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 4000);
                
                const response = await fetch('/health', { 
                    signal: controller.signal,
                    headers: { 'Cache-Control': 'no-cache' }
                });
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    indicator.className = 'status-dot active';
                    text.innerText = 'MCP BACKEND OPERATIONAL';
                    text.style.color = '#00ff41'; // match neon green
                } else {
                    throw new Error('Server returned non-200 code');
                }
            } catch (error) {
                indicator.className = 'status-dot offline';
                text.innerText = 'MCP BACKEND UNREACHABLE';
                text.style.color = '#ff3333'; // match neon red
            }
        }
        
        // Fire health-check initially and poll every 10 seconds
        runHealthCheck();
        setInterval(runHealthCheck, 10000);
    </script>
</body>
</html>
"""

async def root_handler(request):
    return HTMLResponse(content=HTML_TEMPLATE)

app.routes.append(Route("/", endpoint=root_handler))
app.routes.append(Route("/health", endpoint=health_handler))
