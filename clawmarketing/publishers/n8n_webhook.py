"""
N8N Webhook Publisher
Acts as a bridge to send formatted content to n8n workflows.
n8n routes content to LinkedIn OAuth, X API, Bluesky, and other platform nodes.
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

from .base_publisher import BasePublisher

logger = logging.getLogger(__name__)


class N8NWebhookPublisher(BasePublisher):
    def __init__(self, webhook_url: str, **kwargs):
        super().__init__("n8n Webhook")
        self.webhook_url = webhook_url

    async def publish(
        self,
        text: str,
        target_account_id: str,
        platform_name: str,
        media_paths: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Sends a payload to n8n.

        Args:
            target_account_id: The specific Postiz/n8n ID for the social media account (e.g. LinkedIn).
            platform_name: 'linkedin', 'bluesky', etc.
        """
        logger.info(
            f"[{self.platform_name}] Sending payload to n8n webhook for account {target_account_id}"
        )

        payload = {
            "action": "schedule_post",
            "content": text,
            "platform": platform_name,
            "account_id": target_account_id,  # <--- 这里就是指定“拿哪个号发”的核心！
            "media": media_paths or [],
        }

        try:
            # We use an async HTTP client to non-blockingly fire the webhook to n8n
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url, json=payload, timeout=10.0
                )
                response.raise_for_status()

            return {
                "status": "success",
                "message": "Successfully handed off to n8n orchestration",
                "n8n_response": response.json() if response.text else "ok",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"n8n webhook failed with status {e.response.status_code}")
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to reach n8n: {e}")
            return {"status": "failed", "error": str(e)}
