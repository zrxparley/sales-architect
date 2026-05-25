"""
LLM API calling with SSE streaming support.
Compatible with any Anthropic Messages API endpoint.
"""

import json
import sys
import time


def call_llm_streaming(base_url: str, api_key: str, model: str,
                       system: str, user: str,
                       max_tokens: int = 8192,
                       on_chunk=None) -> str:
    """Call LLM API with streaming. Returns full text.

    Args:
        base_url: API base URL (e.g. https://api.anthropic.com)
        api_key: API key
        model: Model name
        system: System prompt
        user: User message
        max_tokens: Max output tokens
        on_chunk: Callback for each text chunk (for real-time display)

    Returns:
        Complete response text
    """
    try:
        import httpx
    except ImportError:
        return _fallback_no_httpx(base_url, api_key, model, system, user, max_tokens)

    url = base_url.rstrip("/") + "/v1/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "stream": True,
    }

    full_text = ""
    retries = 0
    max_retries = 3

    while retries <= max_retries:
        try:
            with httpx.Client(timeout=300.0) as client:
                with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code == 429:
                        retries += 1
                        if retries <= max_retries:
                            wait = 30 * retries
                            if on_chunk:
                                on_chunk(f"\n⏳ 限流，等待 {wait} 秒后重试 ({retries}/{max_retries})...\n")
                            time.sleep(wait)
                            continue
                        else:
                            return "❌ API 限流，多次重试失败。请稍后再试。"

                    if resp.status_code == 401:
                        return "❌ API Key 无效。请运行 `sa config` 重新配置。"

                    if resp.status_code != 200:
                        body = resp.read().decode("utf-8", errors="replace")
                        return f"❌ API 错误 ({resp.status_code}): {body[:200]}"

                    # Parse SSE stream
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                event = json.loads(data_str)
                                if event.get("type") == "content_block_delta":
                                    delta = event.get("delta", {})
                                    text = delta.get("text", "")
                                    if text:
                                        full_text += text
                                        if on_chunk:
                                            on_chunk(text)
                            except json.JSONDecodeError:
                                continue

            return full_text

        except Exception as e:
            err_str = str(e)
            if "ConnectError" in err_str or "connect" in err_str.lower():
                return f"❌ 无法连接到 {base_url}。请检查网络和 API 端点配置。\n   运行 `sa config` 修改端点。"
            if "Timeout" in err_str or "timeout" in err_str.lower():
                retries += 1
                if retries <= max_retries:
                    if on_chunk:
                        on_chunk(f"\n⏳ 请求超时，重试 ({retries}/{max_retries})...\n")
                    continue
                return "❌ 请求超时，多次重试失败。请检查网络或 API 端点。"
            return f"❌ 未知错误: {e}"

    return "❌ 请求失败。"


def _fallback_no_httpx(base_url, api_key, model, system, user, max_tokens):
    """Fallback using urllib when httpx is not available."""
    import urllib.request
    import urllib.error

    url = base_url.rstrip("/") + "/v1/messages"
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("content", [])
            text_parts = [block.get("text", "") for block in content if block.get("type") == "text"]
            return "".join(text_parts)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return f"❌ API 错误 ({e.code}): {body}"
    except urllib.error.URLError as e:
        return f"❌ 网络错误: {e.reason}"
    except Exception as e:
        return f"❌ 错误: {e}"
