#!/usr/bin/env python3
"""
EricAI Proxy Server

Runs on the Windows machine (with EricAI access).
Exposes a simple OpenAI-compatible HTTP API on localhost:9000.
Tunnel this to the Linux game machine via: ssh -R 9000:localhost:9000 user@linux_ip

Usage:
    python ericai_proxy.py [--port 9000] [--model "Qwen/Qwen3-32B-Instruct"]

Model selection (v2, Sep 2026): the "model" field of each request wins; --model is only the default for requests that
omit it. So one proxy instance serves every model of the campaign; the orchestrator's --model (manifest column
orch_args) selects the model per episode, and the served model id is echoed in the response and logged per decision.
Extra sampling fields (top_p, seed, stop, reasoning_effort, ...) are forwarded to EricAI when present.
Requests are served concurrently (ThreadingHTTPServer), so several episodes can share one proxy.
"""

import argparse
import json
import sys
import traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread

# EricAI imports (must be installed: pip install -e /path/to/ericai-client-master)
try:
    from ericai import EricAI
except ImportError:
    print("ERROR: ericai package not installed. Run: pip install -e /path/to/ericai-client-master")
    sys.exit(1)

# Default model
DEFAULT_MODEL = "Qwen/Qwen3.8-27B-FP8-1M"  # Qwen3-32B-Instruct (June 2026) is no longer served


class EricAIProxy:
    """Wraps EricAI client for simple chat completions."""
    
    def __init__(self, model: str):
        self.model = model
        self.client = EricAI()
        print(f"[EricAI Proxy] Initialized with model: {model}")
        print(f"[EricAI Proxy] Testing connection...")
        # Quick test
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            print(f"[EricAI Proxy] Connection OK! Model responded.")
        except Exception as e:
            print(f"[EricAI Proxy] WARNING: Connection test failed: {e}")
            print(f"[EricAI Proxy] Will retry on actual requests.")
    
    FORWARDED_FIELDS = ("top_p", "seed", "stop", "presence_penalty", "frequency_penalty", "reasoning_effort",
                        "response_format", "n", "extra_body")

    # Models whose reasoning ("thinking") mode should be turned off unless the
    # caller explicitly asks for it. Matched as substrings of the model id.
    THINKING_MODELS = ("Qwen3", "DeepSeek-R1", "DeepSeek-V4", "gpt-oss", "Kimi")

    # When thinking is left enabled, guarantee enough budget for reasoning + the
    # final answer so responses don't get truncated with finish_reason=length.
    THINKING_MIN_TOKENS = 8000

    @staticmethod
    def _thinking_explicitly_requested(extra):
        """True if the caller explicitly opted into reasoning for this request."""
        if not extra:
            return False
        # Explicit reasoning_effort (other than "none") means the caller wants it.
        eff = extra.get("reasoning_effort")
        if eff and str(eff).lower() != "none":
            return True
        # Explicit enable_thinking flag anywhere in the request / extra_body.
        eb = extra.get("extra_body") or {}
        ctk = eb.get("chat_template_kwargs") or {}
        for src in (extra, eb, ctk):
            if isinstance(src, dict) and src.get("enable_thinking") is True:
                return True
        # A /think directive in the latest user message.
        return False

    def chat_completion(self, messages, temperature=0.3, max_tokens=500, model=None, extra=None):
        """Call EricAI and return OpenAI-compatible response dict. `model` overrides the default per request."""
        model = model or self.model
        kwargs = {k: v for k, v in (extra or {}).items() if k in self.FORWARDED_FIELDS and v is not None}

        # Decide whether reasoning/thinking should run for this request.
        is_thinking_model = any(t in model for t in self.THINKING_MODELS)
        thinking_requested = self._thinking_explicitly_requested(extra)
        requested_max_tokens = max_tokens

        if is_thinking_model and not thinking_requested:
            # Turn thinking OFF by default. Cover the common backend switches so it
            # works across Qwen / DeepSeek / gpt-oss style models.
            extra_body = dict(kwargs.get("extra_body") or {})
            ctk = dict(extra_body.get("chat_template_kwargs") or {})
            ctk["enable_thinking"] = False        # Qwen / DeepSeek chat-template switch
            extra_body["chat_template_kwargs"] = ctk
            kwargs["extra_body"] = extra_body
            # gpt-oss style models use reasoning_effort instead of a template flag.
            if "gpt-oss" in model:
                kwargs.setdefault("reasoning_effort", "low")
            print(f"[EricAI Proxy] Thinking OFF (default) for {model}")
        elif is_thinking_model and thinking_requested:
            # Thinking is on: make sure the budget is large enough to finish.
            if max_tokens < self.THINKING_MIN_TOKENS:
                print(f"[EricAI Proxy] Thinking ON: raising max_tokens "
                      f"{max_tokens} -> {self.THINKING_MIN_TOKENS} for {model}")
                max_tokens = self.THINKING_MIN_TOKENS

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            # Convert to dict (already OpenAI-compatible)
            choice = response.choices[0]
            msg = choice.message
            content = msg.content

            # Reasoning-style models often leave `content` empty and put the text
            # (or their chain-of-thought) in a `reasoning_content` field. The OpenAI
            # SDK message schema has no such field, so it lands in pydantic's extras
            # (model_extra) rather than as a normal attribute. Check both, plus a
            # couple of alternate names different backends use.
            extra_fields = getattr(msg, "model_extra", None) or {}
            reasoning = (
                getattr(msg, "reasoning_content", None)
                or extra_fields.get("reasoning_content")
                or extra_fields.get("reasoning")
                or extra_fields.get("thinking")
            )
            # Only when the model finished normally: a truncated (finish_reason=length) chain of thought must not be
            # handed to the caller as the answer (the orchestrator would parse reasoning text as an action).
            if content is None and reasoning and choice.finish_reason == "stop":
                content = reasoning
            message_dict = {
                "role": "assistant",
                "content": content,
            }
            if reasoning:
                message_dict["reasoning_content"] = reasoning
            return {
                "id": response.id,
                "object": "chat.completion",
                "model": getattr(response, "model", None) or model,
                "choices": [{
                    "index": 0,
                    "message": message_dict,
                    "finish_reason": choice.finish_reason,
                }],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                # Effective server-side settings, logged per decision by the orchestrator (llm_server_info)
                "proxy_settings": {
                    "proxy_version": "v2-2026-09-27",
                    "thinking": bool(is_thinking_model and thinking_requested),
                    "thinking_model": is_thinking_model,
                    "max_tokens_requested": requested_max_tokens,
                    "max_tokens_effective": max_tokens,
                    "forwarded": sorted(k for k in kwargs if k != "extra_body"),
                    "extra_body": kwargs.get("extra_body"),
                },
            }
        except Exception as e:
            return {
                "error": {
                    "message": str(e),
                    "type": "ericai_error",
                }
            }


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler that mimics OpenAI's /v1/chat/completions endpoint."""
    
    proxy: EricAIProxy = None  # Set at class level
    
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            self.handle_chat_completions()
        else:
            self.send_error(404, f"Not found: {self.path}")
    
    def do_GET(self):
        if self.path == "/v1/models":
            self.handle_models()
        elif self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "model": self.proxy.model}).encode())
        else:
            self.send_error(404)
    
    def handle_chat_completions(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            request = json.loads(body)
        except json.JSONDecodeError as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return
        
        messages = request.get("messages", [])
        temperature = request.get("temperature", 0.3)
        max_tokens = request.get("max_tokens", 500)
        model = request.get("model") or self.proxy.model

        print(f"[EricAI Proxy] Chat request: model={model}, {len(messages)} messages, temp={temperature}, max_tokens={max_tokens}")
        
        result = self.proxy.chat_completion(messages, temperature, max_tokens, model=model, extra=request)
        
        if "error" in result:
            print(f"[EricAI Proxy] Error: {result['error']['message']}")
            self.send_response(500)
        else:
            choice = result["choices"][0]
            content = choice["message"].get("content")
            finish = choice.get("finish_reason")
            usage = result.get("usage", {})
            preview = (content[:100] if content else "<empty>")
            print(f"[EricAI Proxy] Response: {preview} "
                  f"(finish_reason={finish}, tokens={usage.get('completion_tokens', 0)})")
            self.send_response(200)
        
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def handle_models(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        models = {
            "data": [{"id": self.proxy.model, "object": "model", "note": "default; any EricAI model id can be requested per call"}]
        }
        self.wfile.write(json.dumps(models).encode())
    
    def log_message(self, format, *args):
        # Suppress default HTTP logging, we have our own
        pass


def main():
    parser = argparse.ArgumentParser(description="EricAI Proxy - OpenAI-compatible endpoint")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="EricAI model to use")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    # Initialize proxy
    proxy = EricAIProxy(args.model)
    ProxyHandler.proxy = proxy
    
    # Start server
    server = ThreadingHTTPServer((args.host, args.port), ProxyHandler)
    print(f"\n[EricAI Proxy] Listening on {args.host}:{args.port}")
    print(f"[EricAI Proxy] Endpoint: http://localhost:{args.port}/v1/chat/completions")
    print(f"[EricAI Proxy] Default model: {args.model} (each request may name another model)")
    print(f"\n[EricAI Proxy] To tunnel to Linux machine, run:")
    print(f"  ssh -R {args.port}:localhost:{args.port} user@LINUX_MACHINE_IP")
    print(f"\n[EricAI Proxy] Press Ctrl+C to stop.\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[EricAI Proxy] Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
