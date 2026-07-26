"""
KiroNav Backend — Kiro Gateway (OpenAI-compatible API)

Sends screenshots + prompts to the Kiro models catalog via kiro-gateway,
which runs locally and authenticates with the user's Kiro IDE credentials.
"""

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from openai import AsyncOpenAI

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_BASE_URL = "http://localhost:8100/v1"
DEFAULT_API_KEY = "kironav-local-dev"
DEFAULT_TIMEOUT = 60.0


@dataclass
class GuideResponse:
    """Parsed guidance returned by the model."""

    summary: str = ""
    steps: list[str] = field(default_factory=list)
    done: bool = False
    raw: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_text(self) -> str:
        if self.error:
            return self.error
        if self.steps:
            lines = [self.summary] if self.summary else []
            lines += [f"{i}. {s}" for i, s in enumerate(self.steps, 1)]
            return "\n".join(lines)
        return self.summary or self.raw


class KiroBackend:
    """
    Backend that talks to Kiro Gateway for AI inference with vision.

    Flow:
    1. Screen is captured to a PNG by ScreenCapture
    2. PNG is base64-encoded and sent as an image message
    3. The model returns JSON with summary + steps
    4. Response is parsed into a GuideResponse
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = DEFAULT_API_KEY,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.model = model
        self.timeout = timeout
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        self._history: list[dict] = []

    def reset_session(self):
        """Clear conversation history for a fresh start."""
        self._history = []

    @property
    def has_session(self) -> bool:
        return len(self._history) > 0

    @staticmethod
    def _encode_image(path: str) -> str:
        """Read an image file and return base64-encoded string."""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _parse(text: str) -> GuideResponse:
        """Parse the model's JSON response into a GuideResponse."""
        # Try to extract JSON from the response
        try:
            # Find the first { and last } to extract JSON
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start:end + 1])
                steps = [str(s).strip() for s in data.get("steps") or [] if str(s).strip()]
                return GuideResponse(
                    summary=str(data.get("summary") or "").strip(),
                    steps=steps,
                    done=bool(data.get("done")),
                    raw=text,
                )
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: treat the whole response as prose
        return GuideResponse(summary=text.strip(), raw=text)

    async def ask(
        self,
        prompt: str,
        screenshot_path: Optional[str] = None,
        system_context: str = "",
    ) -> GuideResponse:
        """
        Ask the model for guidance, optionally about a screenshot.

        Args:
            prompt: The user's request
            screenshot_path: Path to a PNG screenshot of the user's screen
            system_context: System prompt (sent only on first call)

        Returns:
            Parsed GuideResponse
        """
        messages = []

        # System message (always include for stateless API calls)
        if system_context:
            messages.append({"role": "system", "content": system_context})

        # Add conversation history
        messages.extend(self._history)

        # Build the user message with text + optional image
        content = []

        if screenshot_path and os.path.exists(screenshot_path):
            image_b64 = self._encode_image(screenshot_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}",
                },
            })

        content.append({
            "type": "text",
            "text": prompt,
        })

        user_message = {"role": "user", "content": content}
        messages.append(user_message)

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )

            answer = response.choices[0].message.content or ""

            # Save to history for multi-turn
            self._history.append(user_message)
            self._history.append({"role": "assistant", "content": answer})

            # Keep history manageable (last 6 turns = 3 exchanges)
            if len(self._history) > 6:
                self._history = self._history[-6:]

            return self._parse(answer)

        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "Connection error" in error_msg:
                return GuideResponse(
                    error="No se pudo conectar al Kiro Gateway.\n"
                    "Asegurate de que esté corriendo: python kiro-gateway/main.py --port 8100"
                )
            return GuideResponse(error=f"Error: {error_msg}")

    async def next_step(
        self,
        screenshot_path: str,
        task: str,
        current_step: int,
        total_steps: int,
    ) -> GuideResponse:
        """
        Ask for the next step of an in-progress task with a fresh screenshot.

        Args:
            screenshot_path: Path to the current screen PNG
            task: What the user is trying to do
            current_step: Step just completed
            total_steps: Total steps given so far

        Returns:
            Parsed GuideResponse
        """
        prompt = (
            f"The user is working on: {task}\n"
            f"They just completed step {current_step} of {total_steps}.\n"
            "Look at the new screenshot and tell them what to do next. "
            'If the task is finished, set "done" to true.'
        )
        return await self.ask(prompt, screenshot_path=screenshot_path)
