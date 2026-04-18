import httpx
import logging
import os
import re
import time
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

TIMEOUT = 60.0  # 60s for long system prompts (MiniMax/Gemini need more time)
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
GROK_MODEL = "grok-3-mini"

# ---------------------------------------------------------------------------
# Provider Health Cache (S05)
# When a provider fails, mark it dead for HEALTH_CACHE_TTL seconds.
# Subsequent calls skip dead providers immediately (0s vs timeout wait).
# ---------------------------------------------------------------------------
HEALTH_CACHE_TTL = 180  # 3 minutes (was 10 — too long, dead providers cached as healthy)

_provider_health: dict[str, float] = {}  # provider_name -> timestamp_marked_dead


def mark_provider_dead(provider: str) -> None:
    """Mark a provider as dead at current time."""
    _provider_health[provider] = time.time()
    logger.warning(f"Marked provider {provider} as dead (TTL={HEALTH_CACHE_TTL}s)")


def is_provider_dead(provider: str) -> bool:
    """Check if a provider is currently marked dead (within TTL)."""
    if provider not in _provider_health:
        return False
    elapsed = time.time() - _provider_health[provider]
    if elapsed >= HEALTH_CACHE_TTL:
        # TTL expired, remove entry and allow retry
        del _provider_health[provider]
        logger.info(f"Provider {provider} TTL expired, allowing retry")
        return False
    return True


def clear_health_cache() -> None:
    """Clear all health cache entries. Useful for testing."""
    _provider_health.clear()


def _load_env_file(filepath: str) -> dict:
    env = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    # Strip surrounding quotes and 'export' prefix
                    k = k.replace("export ", "").strip()
                    v = v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                        v = v[1:-1]
                    env[k] = v
    return env


async def _call_zai_glm(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    # Use GLM-5 via Anthropic-compatible API from zai-glm.env
    env = _load_env_file(os.path.expanduser("~/.oyster-keys/zai-glm.env"))
    api_key = env.get("ZAI_API_KEY", "")
    base_url = env.get("ZAI_BASE_URL", "https://api.z.ai/api/anthropic/v1/messages")

    if not api_key:
        logger.debug("No ZAI_API_KEY set, skipping Z.AI GLM")
        return None

    # Z.AI uses Anthropic spec
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        if not base_url.endswith("messages"):
            base_url = base_url.rstrip("/") + "/v1/messages"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(base_url, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", [])
            if content and content[0].get("type") == "text":
                return content[0]["text"].strip()
        logger.warning(f"ZAI GLM error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"ZAI GLM request failed: {e}")
    return None


async def _call_grok(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    api_key = os.getenv("GROK_API_KEY", "")
    if not api_key:
        env = _load_env_file(os.path.expanduser("~/.oyster-keys/grok.env"))
        api_key = env.get("GROK_API_KEY", env.get("XAI_API_KEY", ""))

    if not api_key:
        logger.debug("No GROK_API_KEY set, skipping Grok")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    combined = f"{system_prompt}\n\n{user_message}"

    payload = {
        "model": GROK_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": combined}],
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions", json=payload, headers=headers
            )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        logger.warning(f"Grok error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Grok request failed: {e}")
    return None


async def _call_minimax(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    api_key = os.getenv("MINIMAX_API_KEY", "")
    # Skip proxy keys (same pattern as _call_anthropic)
    if api_key.startswith("sk-cp-"):
        api_key = ""
    if not api_key:
        env_openclaw = _load_env_file(os.path.expanduser("~/.openclaw/.env"))
        env_oyster = _load_env_file(os.path.expanduser("~/.oyster-keys/minimax.env"))
        api_key = env_openclaw.get("MINIMAX_API_KEY") or env_oyster.get(
            "MINIMAX_API_KEY", ""
        )

    if not api_key:
        logger.debug("No MINIMAX_API_KEY set, skipping Minimax")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Minimax.io (international / OpenAI-compatible endpoint)
    payload = {
        "model": "MiniMax-M2.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.minimax.io/v1/chat/completions",
                json=payload,
                headers=headers,
            )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        logger.warning(f"Minimax error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Minimax request failed: {e}")
    return None


async def _call_kimi(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    api_key = os.getenv("KIMI_API_KEY", "")
    if not api_key:
        logger.debug("No KIMI_API_KEY set, skipping Kimi")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "moonshot-v1-8k",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.moonshot.cn/v1/chat/completions",
                json=payload,
                headers=headers,
            )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        logger.warning(f"Kimi error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Kimi request failed: {e}")
    return None


async def _call_anthropic(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    """Call Anthropic Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        env = _load_env_file(os.path.expanduser("~/.openclaw/.env"))
        api_key = env.get("ANTHROPIC_API_KEY", "")
        # Skip proxy keys
        if api_key.startswith("sk-cp-"):
            api_key = ""

    if not api_key:
        logger.debug("No ANTHROPIC_API_KEY set, skipping Anthropic")
        return None

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages", json=payload, headers=headers
            )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", [])
            if content and content[0].get("type") == "text":
                return content[0]["text"].strip()
        logger.warning(f"Anthropic error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Anthropic request failed: {e}")
    return None


async def _call_gemini(*, system_prompt: str, user_message: str, max_tokens: int = 512) -> str | None:
    """Call Google Gemini API. Tier 1 — primary content engine."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        env = _load_env_file(os.path.expanduser("~/.oyster-keys/gemini.env"))
        api_key = env.get("GEMINI_API_KEY", "")

    if not api_key:
        logger.debug("No GEMINI_API_KEY set, skipping Gemini")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_message}"}]}
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        logger.warning(f"Gemini error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Gemini request failed: {e}")
    return None


BROWSER_GATEWAY_URL = os.getenv(
    "BROWSER_GATEWAY_URL", "http://100.91.32.29:8100"
)  # MAC-2 Browser LLM Gateway via Tailscale

# Cache gateway + per-model availability to avoid repeated 30s timeouts
_gateway_alive: bool | None = None
_model_dead: set[str] = set()  # Models that failed — skip for this session


async def _call_browser_gateway(
    *, system_prompt: str, user_message: str, model: str = "gemini", max_tokens: int = 512
) -> str | None:
    """Tier 1: Call the Browser LLM Gateway (Custom Gateway)."""
    global _gateway_alive
    if not BROWSER_GATEWAY_URL:
        return None

    # Skip models already known dead this session
    if model in _model_dead:
        return None

    # Fast health check — skip if already known dead this session
    if _gateway_alive is False:
        return None
    if _gateway_alive is None:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                probe = await client.get(f"{BROWSER_GATEWAY_URL}/health")
            if probe.status_code == 200:
                _gateway_alive = True
                # Pre-check which models are alive from health response
                health = probe.json()
                models_status = health.get("models", {})
                for m, alive in models_status.items():
                    if not alive:
                        _model_dead.add(m)
                        logger.warning(f"Browser Gateway: {m} not available")
            else:
                _gateway_alive = False
        except Exception:
            _gateway_alive = False
        if not _gateway_alive:
            logger.warning(f"Browser Gateway unreachable — skipping for this session")
            return None
        if model in _model_dead:
            return None

    payload = {
        "model": model,
        "prompt": user_message,
        "system_prompt": system_prompt,
        "max_wait_seconds": 30,
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:  # Browser gateway needs more time (queue + LLM generation)
            resp = await client.post(f"{BROWSER_GATEWAY_URL}/generate", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("text", "")
            if text and not str(text).startswith("Error:"):
                logger.info(f"Browser Gateway ({model}) returned {len(text)} chars")
                return text.strip()
            if text and str(text).startswith("Error:"):
                # Model failed (session expired, selector broken, etc.)
                _model_dead.add(model)
                logger.warning(
                    f"Browser Gateway ({model}) failed — disabling for this session: {text[:80]}"
                )
                return None
        logger.warning(
            f"Browser Gateway ({model}) error {resp.status_code}: {resp.text[:200]}"
        )
    except Exception as e:
        logger.warning(f"Browser Gateway ({model}) unreachable: {e}")
    return None


async def _try_provider(
    provider_name: str,
    call_fn,
    *,
    system_prompt: str,
    user_message: str,
    **kwargs,
) -> str | None:
    """Try a provider, respecting health cache. Mark dead on failure."""
    if is_provider_dead(provider_name):
        dead_at = _provider_health.get(provider_name, 0)
        logger.info(
            f"Skipping {provider_name}: marked dead at {time.strftime('%H:%M:%S', time.localtime(dead_at))}"
        )
        return None

    res = await call_fn(system_prompt=system_prompt, user_message=user_message, **kwargs)
    if res:
        # Strip <think> blocks from reasoning models (MiniMax, Grok-mini, DeepSeek, etc.)
        res = re.sub(r"<think>.*?</think>\s*", "", res, flags=re.DOTALL).strip()
        res = re.sub(r"<think>.*", "", res, flags=re.DOTALL).strip()
        return res if res else None

    # Provider failed -- mark it dead
    mark_provider_dead(provider_name)
    return None


async def generate_text(
    system_prompt: str, user_message: str, prefer_grok: bool = False,
    max_tokens: int = 512,
) -> str | None:
    """
    Generate text. Priority:
      If prefer_grok: Grok API -> Browser Gateway -> API fallbacks
      Else: Browser Gateway -> API fallbacks

    Health cache: failed providers are skipped for 3 minutes.
    max_tokens: Platform-specific (twitter=600, linkedin=1200, report=800).
    """
    if prefer_grok:
        res = await _try_provider(
            "grok", _call_grok,
            system_prompt=system_prompt, user_message=user_message,
            max_tokens=max_tokens,
        )
        if res:
            return res

    # === Tier 1: Browser Gateway ===
    if BROWSER_GATEWAY_URL:
        gw_model = "grok" if prefer_grok else "gemini"

        res = await _try_provider(
            "browser_gateway", _call_browser_gateway,
            system_prompt=system_prompt, user_message=user_message,
            model=gw_model, max_tokens=max_tokens,
        )
        if res:
            return res

    # === Tier 2: API Fallbacks ===
    res = await _try_provider(
        "gemini", _call_gemini,
        system_prompt=system_prompt, user_message=user_message,
        max_tokens=max_tokens,
    )
    if res:
        return res

    res = await _try_provider(
        "minimax", _call_minimax,
        system_prompt=system_prompt, user_message=user_message,
        max_tokens=max_tokens,
    )
    if res:
        return res

    res = await _try_provider(
        "zai_glm", _call_zai_glm,
        system_prompt=system_prompt, user_message=user_message,
        max_tokens=max_tokens,
    )
    if res:
        return res

    if prefer_grok:
        return await _try_provider(
            "kimi", _call_kimi,
            system_prompt=system_prompt, user_message=user_message,
            max_tokens=max_tokens,
        )
    else:
        res = await _try_provider(
            "anthropic", _call_anthropic,
            system_prompt=system_prompt, user_message=user_message,
            max_tokens=max_tokens,
        )
        if res:
            return res
        return await _try_provider(
            "grok", _call_grok,
            system_prompt=system_prompt, user_message=user_message,
            max_tokens=max_tokens,
        )
