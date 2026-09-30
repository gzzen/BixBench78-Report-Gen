"""Minimal DeepSeek chat-completions client (OpenAI-compatible API, stdlib only).

Config comes from .env / environment:
    DEEPSEEK_API_KEY   (required)
    DEEPSEEK_BASE_URL  (default https://api.deepseek.com)
    DEEPSEEK_MODEL     (default deepseek-chat)
"""
import json
import os
import time
import urllib.error
import urllib.request

from .config import load_dotenv


class DeepSeekError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=120, retries=3):
        load_dotenv()
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise DeepSeekError("DEEPSEEK_API_KEY not set (put it in .env, see .env.example)")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
        self.timeout, self.retries = timeout, retries

    def chat(self, messages, temperature=0.0, json_mode=False, max_tokens=800):
        """Return (text, usage_dict). Retries on 429/5xx/network errors with backoff."""
        body = {"model": self.model, "messages": messages, "temperature": temperature,
                "max_tokens": max_tokens}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        last = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"], data.get("usage", {})
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
                last = repr(e)
            time.sleep(2 ** attempt)
        raise DeepSeekError(last)
