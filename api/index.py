import sys
import os

# Ensure the local 'src' directory is in the Python path for Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from malimgraph.plugin import mcp
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Vercel's Serverless Python runtime looks for the 'app' variable explicitly.

class AsgiHostRewrite:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = []
            has_host = False
            for k, v in scope.get("headers", []):
                if k.lower() == b"host":
                    headers.append((b"host", b"localhost"))
                    has_host = True
                else:
                    headers.append((k, v))
            if not has_host:
                headers.append((b"host", b"localhost"))
            scope["headers"] = headers
        return await self.app(scope, receive, send)

_internal_app = mcp.sse_app()

# Add CORS Middleware to allow web clients (like Claude Web) to connect
_internal_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app = AsgiHostRewrite(_internal_app)

async def health_handler(request):
    return JSONResponse({"status": "online"})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MalimGraph Plugin</title>
    <style>
        body {
            background-color: #000000;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }
        main {
            text-align: center;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            width: 100%;
        }
        .logo {
            width: 80px;
            height: 80px;
            margin-bottom: 2.5rem;
            object-fit: contain;
        }
        .label {
            color: #555555;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 1rem;
            font-weight: 500;
        }
        .code-container {
            position: relative;
            background: #080808;
            border: 1px solid #1a1a1a;
            border-radius: 8px;
            padding: 1.25rem 1.5rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .code-container:hover {
            border-color: #333;
            background: #111;
        }
        code {
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 0.95rem;
            color: #e0e0e0;
        }
        .prompt::before {
            content: "$ ";
            color: #444;
        }
        .copy-icon {
            color: #555;
            transition: color 0.2s ease;
        }
        .code-container:hover .copy-icon {
            color: #fff;
        }
        .toast {
            position: fixed;
            top: 2.5rem;
            background: #00ff41;
            color: #000;
            padding: 0.6rem 1.2rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        footer {
            width: 100%;
            padding: 2.5rem;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            border-top: 1px solid #0f0f0f;
            background: #000;
        }
        .status-text {
            font-size: 0.75rem;
            font-family: 'Courier New', Courier, monospace;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #444;
            transition: color 0.3s ease;
        }
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: #222;
        }
        .status-dot.active {
            background-color: #00ff41;
            box-shadow: 0 0 8px #00ff41;
            animation: pulse-green 2.5s infinite ease-in-out;
        }
        .status-dot.offline {
            background-color: #ff3333;
            box-shadow: 0 0 8px #ff3333;
            animation: pulse-red 2s infinite ease-in-out;
        }
        @keyframes pulse-green {
            0% { opacity: 1; box-shadow: 0 0 8px #00ff41; }
            50% { opacity: 0.3; box-shadow: 0 0 2px #00ff41; }
            100% { opacity: 1; box-shadow: 0 0 8px #00ff41; }
        }
        @keyframes pulse-red {
            0% { opacity: 1; box-shadow: 0 0 8px #ff3333; }
            50% { opacity: 0.3; box-shadow: 0 0 2px #ff3333; }
            100% { opacity: 1; box-shadow: 0 0 8px #ff3333; }
        }
    </style>
</head>
<body>
    <div id="toast" class="toast">Copied to clipboard</div>
    
    <main>
        <img src="/favicon.ico" alt="MalimGraph Logo" class="logo" onerror="this.style.display='none'">
        
        <div class="label">Install Plugin via Claude</div>
        
        <div class="code-container" onclick="copyCommand()">
            <code class="prompt" id="commandText">/plugin marketplace add malim-ai-labs/malim-graph-plugin</code>
            <svg class="copy-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
        </div>
    </main>

    <footer>
        <div class="status-dot" id="statusIndicator"></div>
        <div class="status-text" id="statusText">AWAITING BACKEND</div>
    </footer>

    <script>
        function copyCommand() {
            const text = document.getElementById('commandText').innerText;
            navigator.clipboard.writeText(text).then(() => {
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            });
        }

        async function runHealthCheck() {
            const indicator = document.getElementById('statusIndicator');
            const text = document.getElementById('statusText');
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 4000);
                
                const response = await fetch('/health', { 
                    signal: controller.signal,
                    headers: { 'Cache-Control': 'no-cache' }
                });
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    indicator.className = 'status-dot active';
                    text.innerText = 'MCP SERVER OPERATIONAL';
                } else {
                    throw new Error('Server non-200');
                }
            } catch (error) {
                indicator.className = 'status-dot offline';
                text.innerText = 'MCP SERVER UNREACHABLE';
            }
        }
        
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
