from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class AIProvider(ABC):
    """Interface for AI text completion providers."""

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        ...


class ClaudeCodeProvider(AIProvider):
    """Invokes the Claude Code CLI as a subprocess."""

    name = "claude-code"

    def is_available(self) -> bool:
        return shutil.which("claude") is not None

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        claude_bin = shutil.which("claude") or "claude"
        cmd = [claude_bin, "--print", "--output-format", "text"]
        if system:
            cmd += ["--system-prompt", system]
        # Pass prompt via stdin to avoid shell quoting issues on Windows
        use_shell = platform.system() == "Windows"
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
            shell=use_shell,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Claude Code CLI failed (exit {result.returncode}): {result.stderr}"
            )
        return result.stdout


class ClaudeAPIProvider(AIProvider):
    """Uses the Anthropic Python SDK directly."""

    name = "api"

    def is_available(self) -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        import anthropic

        client = anthropic.Anthropic()
        kwargs: dict = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 16384,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = client.messages.create(**kwargs)
        return message.content[0].text


class ManualProvider(AIProvider):
    """Writes prompt to a file for the user to process manually."""

    name = "manual"

    def __init__(self, output_path: Path | None = None) -> None:
        self._output_path = output_path

    def is_available(self) -> bool:
        return True

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        if self._output_path is None:
            raise ValueError("ManualProvider requires an output_path")
        content = ""
        if system:
            content += f"# System Instructions\n\n{system}\n\n---\n\n"
        content += prompt
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(content, encoding="utf-8")
        raise ManualFallback(self._output_path)


class ManualFallback(Exception):
    """Raised when the manual provider writes a prompt file instead of completing."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Prompt written to {path}")


def get_provider(override: str | None = None) -> AIProvider:
    """Return the best available AI provider, with optional override."""
    if override:
        providers = {
            "claude-code": ClaudeCodeProvider,
            "api": ClaudeAPIProvider,
            "manual": lambda: ManualProvider(),
        }
        if override not in providers:
            raise ValueError(f"Unknown provider: {override!r}. Choose from: {', '.join(providers)}")
        provider = providers[override]()
        if not provider.is_available():
            raise RuntimeError(f"Provider {override!r} is not available")
        return provider

    # Cascade: Claude Code CLI -> API -> Manual
    for provider_cls in [ClaudeCodeProvider, ClaudeAPIProvider]:
        provider = provider_cls()
        if provider.is_available():
            return provider
    return ManualProvider()
