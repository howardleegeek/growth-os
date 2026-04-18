"""
X (Twitter) Publisher — pure X API v2 via tweepy.
No CDP, no browser automation. Reads OAuth keys from ~/.oyster-keys/
"""

import os
import logging
from typing import Optional, List, Dict, Any

import tweepy

from .base_publisher import BasePublisher

logger = logging.getLogger(__name__)

KEYS_DIR = os.path.expanduser("~/.oyster-keys")

# Map handle → env file
ACCOUNT_KEY_FILES = {
    "@clawglasses": "x.env",
    "@oysterecosystem": "x_oysterecosystem.env",
}


def _load_env(filepath: str) -> dict:
    env = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _get_client(handle: str) -> tweepy.Client | None:
    key_file = ACCOUNT_KEY_FILES.get(handle.lower())
    if not key_file:
        logger.error(f"No API key file mapped for {handle}")
        return None

    env = _load_env(os.path.join(KEYS_DIR, key_file))

    api_key = env.get("X_API_KEY", "")
    api_secret = env.get("X_API_SECRET", "")
    access_token = env.get("X_ACCESS_TOKEN", "")
    access_secret = env.get("X_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        logger.error(f"Incomplete OAuth keys in {key_file}")
        return None

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


class XApiPublisher(BasePublisher):
    def __init__(self, **kwargs):
        super().__init__("X API")

    async def publish(
        self, text: str, handle: str, media_paths: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:

        logger.info(f"[{self.platform_name}] Publishing to {handle} via API")
        try:
            client = _get_client(handle)
            if not client:
                return {
                    "status": "failed",
                    "error": f"No API keys for {handle}",
                }

            resp = client.create_tweet(text=text)
            posted_id = resp.data["id"]
            url = f"https://x.com/i/web/status/{posted_id}"
            logger.info(f"[{self.platform_name}] Posted: {url}")
            return {"status": "success", "url": url}

        except Exception as e:
            logger.error(f"[{self.platform_name}] Failed: {e}")
            return {"status": "failed", "error": str(e)}
