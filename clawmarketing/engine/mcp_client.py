"""
Postiz MCP Client — Direct HTTP interface to Postiz MCP endpoint.

Bypasses CLI subprocess overhead. Gives access to:
  - integrationSchedulePostTool: schedule posts with HTML content
  - generateImageTool: AI image generation (300/month)
  - generateVideoTool: AI video generation (Veo3, 30/month)
  - integrationList: list connected integrations
  - integrationSchema: get platform rules/settings schema

Usage:
    from engine.mcp_client import PostizMCP
    mcp = PostizMCP()
    await mcp.initialize()
    result = await mcp.schedule_post(integration_id, content_html, date_utc)
    image = await mcp.generate_image("ClawGlasses AI vision wearable, product shot")
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _load_mcp_url() -> str:
    """Load Postiz MCP URL from env file."""
    url = os.environ.get("POSTIZ_MCP_URL", "")
    if url:
        return url
    env_path = os.path.expanduser("~/.oyster-keys/postiz.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("POSTIZ_MCP_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class PostizMCP:
    """Direct HTTP client for Postiz MCP endpoint."""

    def __init__(self):
        self.mcp_url = _load_mcp_url()
        self.session_id: Optional[str] = None
        self._request_id = 0
        self._initialized = False
        self._client: Optional[httpx.AsyncClient] = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client (session cookies persist)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def _call(self, method: str, params: Dict[str, Any] = None, _retry: bool = True) -> Any:
        """Send a JSON-RPC request to the MCP endpoint."""
        if not self.mcp_url:
            raise RuntimeError("POSTIZ_MCP_URL not configured")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }

        client = await self._get_client()
        resp = await client.post(self.mcp_url, json=payload, headers=headers)

        # Session expired → close client, re-initialize with fresh connection, retry once
        if resp.status_code == 400 and "session" in resp.text.lower() and _retry:
            logger.warning("[MCP] Session expired, creating fresh connection...")
            if self._client and not self._client.is_closed:
                await self._client.aclose()
            self._client = None
            self.session_id = None
            self._initialized = False
            await self.initialize()
            # Small delay for server-side session propagation
            import asyncio as _asyncio
            await _asyncio.sleep(0.5)
            return await self._call(method, params, _retry=False)

        # Check HTTP status — 4xx/5xx should not be silently swallowed
        if resp.status_code >= 400:
            raise RuntimeError(
                f"MCP HTTP {resp.status_code}: {resp.text[:300]}"
            )

        # Capture session ID
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid

        content_type = resp.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # Parse SSE — extract last data line
            for line in resp.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "result" in data:
                            return data["result"]
                        if "error" in data:
                            raise RuntimeError(f"MCP error: {data['error']}")
                    except json.JSONDecodeError:
                        pass
            return None
        else:
            data = resp.json()
            if "result" in data:
                return data["result"]
            if "error" in data:
                raise RuntimeError(f"MCP error: {data['error']}")
            return data

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session. Must be called first."""
        result = await self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "clawmarketing", "version": "1.0"},
        })
        # MCP protocol requires "initialized" notification after handshake
        client = await self._get_client()
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        await client.post(self.mcp_url, json=notif, headers=headers)
        self._initialized = True
        logger.info(f"[MCP] Initialized: {result.get('serverInfo', {}).get('name', 'Postiz')}")
        return result

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    async def _call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call an MCP tool by name."""
        await self._ensure_initialized()
        result = await self._call("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        # MCP tool results are in content[0].text
        if isinstance(result, dict) and "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except (json.JSONDecodeError, TypeError):
                        return item["text"]
        return result

    # ── High-Level API ────────────────────────────────────────────

    async def list_integrations(self) -> List[Dict[str, str]]:
        """List all connected integrations."""
        result = await self._call_tool("integrationList")
        if isinstance(result, dict):
            return result.get("output", [])
        return []

    async def get_platform_schema(self, platform: str, is_premium: bool = True) -> Dict[str, Any]:
        """Get platform schema (rules, maxLength, settings, tools)."""
        result = await self._call_tool("integrationSchema", {
            "isPremium": is_premium,
            "platform": platform,
        })
        if isinstance(result, dict):
            return result.get("output", result)
        return {}

    async def schedule_post(
        self,
        integration_id: str,
        content_html: str,
        date_utc: str,
        attachments: Optional[List[str]] = None,
        comments: Optional[List[str]] = None,
        settings: Optional[List[Dict[str, Any]]] = None,
        post_type: str = "schedule",
        is_premium: bool = True,
        short_link: bool = True,
    ) -> Dict[str, Any]:
        """
        Schedule a post via MCP.

        Args:
            integration_id: Postiz integration ID
            content_html: Post content in HTML (<p>text</p>)
            date_utc: ISO 8601 UTC datetime string
            attachments: List of image/video URLs
            comments: List of comment HTML strings (first is self-reply)
            settings: Platform-specific settings (e.g. [{"key":"who_can_reply_post","value":"everyone"}])
            post_type: "schedule", "draft", or "now"
        """
        posts_and_comments = [
            {"content": content_html, "attachments": attachments or []}
        ]
        if comments:
            for comment in comments:
                posts_and_comments.append(
                    {"content": comment, "attachments": []}
                )

        post_entry = {
            "integrationId": integration_id,
            "isPremium": is_premium,
            "date": date_utc,
            "shortLink": short_link,
            "type": post_type,
            "postsAndComments": posts_and_comments,
            "settings": settings or [],
        }

        result = await self._call_tool("integrationSchedulePostTool", {
            "socialPost": [post_entry],
        })
        return result

    async def schedule_batch(
        self,
        posts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Schedule multiple posts in one MCP call.

        Each post dict should have:
            - integration_id: str
            - content_html: str
            - date_utc: str
            - attachments: list[str] (optional)
            - comments: list[str] (optional)
            - settings: list[dict] (optional)
        """
        social_posts = []
        for p in posts:
            posts_and_comments = [
                {"content": p["content_html"], "attachments": p.get("attachments", [])}
            ]
            for comment in p.get("comments", []):
                posts_and_comments.append({"content": comment, "attachments": []})

            social_posts.append({
                "integrationId": p["integration_id"],
                "isPremium": p.get("is_premium", True),
                "date": p["date_utc"],
                "shortLink": p.get("short_link", True),
                "type": p.get("type", "schedule"),
                "postsAndComments": posts_and_comments,
                "settings": p.get("settings", []),
            })

        result = await self._call_tool("integrationSchedulePostTool", {
            "socialPost": social_posts,
        })
        return result

    async def generate_image(self, prompt: str) -> Dict[str, str]:
        """
        Generate an AI image via Postiz (300/month limit).
        Returns {"id": "...", "path": "https://uploads.postiz.com/..."}.
        """
        result = await self._call_tool("generateImageTool", {"prompt": prompt})
        return result if isinstance(result, dict) else {}

    async def get_video_options(self) -> List[Dict[str, Any]]:
        """List available video generation options (Veo3, Image Slides, etc.)."""
        result = await self._call_tool("generateVideoOptions")
        if isinstance(result, dict):
            return result.get("video", [])
        return []

    async def generate_video(
        self,
        identifier: str,
        orientation: str = "horizontal",
        custom_params: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """
        Generate an AI video via Postiz (30/month limit for Veo3).
        Returns {"url": "https://..."}.
        """
        result = await self._call_tool("generateVideoTool", {
            "identifier": identifier,
            "output": orientation,
            "customParams": custom_params or [],
        })
        return result if isinstance(result, dict) else {}

    async def find_slot(self, integration_id: str) -> str:
        """
        Find the next available posting slot for a channel.
        Uses Postiz REST API (not MCP) — GET /public/v1/find-slot/{id}
        Returns ISO 8601 date string of next available slot.
        """
        import os
        api_key = os.environ.get("POSTIZ_API_KEY", "")
        if not api_key:
            env_path = os.path.expanduser("~/.oyster-keys/postiz.env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export "):
                            line = line[7:]
                        if line.startswith("POSTIZ_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"https://api.postiz.com/public/v1/find-slot/{integration_id}",
                headers={"Authorization": api_key},
            )
        if resp.status_code >= 400:
            logger.warning(f"find-slot failed for {integration_id}: HTTP {resp.status_code}")
            return ""
        data = resp.json()
        return data.get("date", "")

    async def ask_agent(self, message: str) -> str:
        """Ask the Postiz agent a question."""
        result = await self._call_tool("ask_postiz", {"message": message})
        return str(result) if result else ""


def text_to_html(text: str) -> str:
    """Convert plain text to Postiz HTML format (each line wrapped in <p>)."""
    lines = text.strip().split("\n")
    html_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            html_parts.append("<p></p>")
        else:
            html_parts.append(f"<p>{line}</p>")
    return "".join(html_parts)
