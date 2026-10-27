"""Local MLX-LM chat transport. No MLX imports or model downloads in DASE."""
from dataclasses import dataclass, replace
import math
import os
from time import perf_counter
from urllib.parse import urlsplit

import httpx


DEFAULT_MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"


class InferenceError(RuntimeError):
    """An inference failure which must not become conversation history."""


@dataclass(frozen=True)
class MLXConfig:
    base_url: str = "http://127.0.0.1:8080/v1"
    model: str = DEFAULT_MODEL
    timeout: float = 120.0
    max_tokens: int = 768
    temperature: float = 0.7
    top_p: float = 0.8
    max_history_chars: int = 24000

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                or url.username or url.password or url.query or url.fragment
                or url.path.rstrip("/") != "/v1"):
            raise ValueError("MLX_BASE_URL must be a localhost HTTP URL ending in /v1.")
        # Evaluate the port here so invalid port values fail before a session starts.
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("Invalid MLX server port.")
        if not self.model.strip():
            raise ValueError("An MLX model ID or local model path is required.")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("MLX_TIMEOUT must be positive and finite.")
        if self.max_tokens <= 0 or self.max_history_chars <= 0:
            raise ValueError("MLX token and history limits must be positive.")
        if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("MLX_TEMPERATURE must be between 0 and 2.")
        if not math.isfinite(self.top_p) or not 0 < self.top_p <= 1:
            raise ValueError("MLX_TOP_P must be between 0 and 1.")

    @classmethod
    def from_env(cls, model=None):
        config = cls(
            base_url=os.getenv("MLX_BASE_URL", cls.base_url),
            model=os.getenv("MLX_MODEL", cls.model),
            timeout=float(os.getenv("MLX_TIMEOUT", cls.timeout)),
            max_tokens=int(os.getenv("MLX_MAX_TOKENS", cls.max_tokens)),
            temperature=float(os.getenv("MLX_TEMPERATURE", cls.temperature)),
            top_p=float(os.getenv("MLX_TOP_P", cls.top_p)),
            max_history_chars=int(os.getenv("MLX_MAX_HISTORY_CHARS", cls.max_history_chars)),
        )
        return replace(config, model=model.strip()) if model else config


class MLXProvider:
    def __init__(self, config, transport=None):
        self.config = config
        self.transport = transport

    def complete(self, messages):
        input_chars = sum(len(m["content"]) for m in messages)
        if input_chars > self.config.max_history_chars:
            raise InferenceError(
                f"Local conversation reached MLX_MAX_HISTORY_CHARS "
                f"({input_chars:,} input characters > {self.config.max_history_chars:,} limit). "
                "Save and start a new "
                "exercise, or deliberately increase the limit. No history was discarded."
            )
        started = perf_counter()
        try:
            # Ignore proxy environment variables, never follow redirects to other hosts.
            with httpx.Client(timeout=httpx.Timeout(self.config.timeout, connect=5.0),
                              trust_env=False, follow_redirects=False,
                              transport=self.transport) as client:
                response = client.post(
                    self.config.base_url.rstrip("/") + "/chat/completions",
                    json={"model": self.config.model, "messages": messages,
                          "stream": False, "max_tokens": self.config.max_tokens,
                          "temperature": self.config.temperature, "top_p": self.config.top_p},
                )
                response.raise_for_status()
                data = response.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Empty content")
            if choice.get("finish_reason") == "length":
                raise InferenceError(
                    f"MLX output reached its token limit ({self.config.max_tokens} tokens). "
                    "Retry with a shorter requested "
                    "response or increase MLX_MAX_TOKENS; the partial turn was not committed."
                )
            usage = data.get("usage", {})
            return text.strip(), {"elapsed_seconds": round(perf_counter() - started, 3),
                                  "usage": usage if isinstance(usage, dict) else {},
                                  "finish_reason": choice.get("finish_reason")}
        except httpx.TimeoutException as exc:
            raise InferenceError("MLX request timed out. Check server load or MLX_TIMEOUT.") from exc
        except httpx.ConnectError as exc:
            raise InferenceError("MLX server unavailable. Start mlx_lm.server and check MLX_BASE_URL.") from exc
        except httpx.HTTPStatusError as exc:
            raise InferenceError(f"MLX server returned HTTP {exc.response.status_code}. Check its terminal logs.") from exc
        except httpx.RequestError as exc:
            raise InferenceError("MLX connection failed. Check the local server terminal.") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InferenceError("MLX server returned an invalid or empty chat response.") from exc
