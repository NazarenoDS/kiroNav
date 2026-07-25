"""
KiroNav Kiro CLI Backend

Uses Kiro CLI as the AI backend: capture screen -> ask kiro-cli -> parse guidance.

Session continuity notes (measured against kiro-cli, not assumed):
- `--resume-id <uuid>` does NOT create a session, so a fresh UUID silently loses
  all context. Only `--resume` reliably continues the previous conversation from
  the same working directory.
- Because `--resume` is scoped per directory, KiroNav uses its own session
  directory so it never picks up an unrelated conversation.
- The CLI renders markdown, which strips the ``` fences off a fenced code block.
  The parser therefore extracts the first balanced JSON object instead of
  matching fences.
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

# Response text is followed by this banner, which marks the end of the answer.
_END_BANNER = "All tools are now trusted"

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# Tool-progress chatter the CLI prints around the answer.
_NOISE_PATTERNS = [
    re.compile(r"^\s*Reading images:.*$", re.MULTILINE),
    re.compile(r"^\s*\(using tool:.*?\)\s*$", re.MULTILINE),
    re.compile(r"^\s*✓.*$", re.MULTILINE),
    re.compile(r"^\s*-\s*Completed in.*$", re.MULTILINE),
    re.compile(r"^\s*▸\s*Credits:.*$", re.MULTILINE),
    re.compile(r"^\s*Agents can sometimes do unexpected things.*$", re.MULTILINE),
    re.compile(r"^\s*Learn more at.*$", re.MULTILINE),
    # Leading prompt markers, plus the bare "json" left over from a stripped fence.
    re.compile(r"^\s*>\s*(json)?\s*$", re.MULTILINE),
    re.compile(r"^\s*>\s*"),
]

DEFAULT_MODEL = "claude-haiku-4.5"
DEFAULT_TIMEOUT = 120.0

# Directory used only for KiroNav's own kiro-cli conversation, so `--resume`
# never resumes the user's unrelated sessions in the project root.
SESSION_DIR_NAME = ".kironav-session"


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
        """True when the call succeeded."""
        return self.error is None

    def as_text(self) -> str:
        """Human-readable rendering, used when there are no parsable steps."""
        if self.error:
            return self.error
        if self.steps:
            lines = [self.summary] if self.summary else []
            lines += [f"{i}. {s}" for i, s in enumerate(self.steps, 1)]
            return "\n".join(lines)
        return self.summary or self.raw


class KiroCLIBackend:
    """
    Backend that uses Kiro CLI for AI inference.

    Flow:
    1. Screen is captured to a PNG by ScreenCapture
    2. kiro-cli is asked about that PNG
    3. The JSON answer is parsed into a GuideResponse
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        project_dir: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Kiro CLI backend.

        Args:
            model: Kiro model to use (haiku by default, for latency)
            project_dir: Project root; the session directory is created inside it
            timeout: Per-call timeout in seconds
        """
        self.model = model
        self.timeout = timeout
        self.project_dir = project_dir or os.path.dirname(os.path.dirname(__file__))
        self.session_dir = os.path.join(self.project_dir, SESSION_DIR_NAME)
        os.makedirs(self.session_dir, exist_ok=True)

        # False until the first successful call; controls the --resume flag.
        self._has_session = False

    # -------------------------------------------------------------- lifecycle

    def reset_session(self):
        """Forget the current conversation so the next call starts fresh."""
        self._has_session = False

    @property
    def has_session(self) -> bool:
        """True when a conversation is already in progress."""
        return self._has_session

    # ---------------------------------------------------------------- parsing

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape sequences."""
        return _ANSI_RE.sub("", text)

    @classmethod
    def _clean_response(cls, raw_output: str) -> str:
        """
        Extract the answer text from kiro-cli's terminal output.

        Cuts at the trust banner that always follows the answer, then removes
        tool-progress lines. Deliberately avoids guessing which chunk is longest.
        """
        text = cls._strip_ansi(raw_output)

        end = text.find(_END_BANNER)
        if end != -1:
            text = text[:end]

        for pattern in _NOISE_PATTERNS:
            text = pattern.sub("", text)

        return text.strip()

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """
        Extract the first balanced JSON object from `text`.

        Fence markers are unreliable because the CLI renders markdown and drops
        them, so this scans braces while ignoring braces inside strings.
        """
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False

        for i, char in enumerate(text[start:], start):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
                    return parsed if isinstance(parsed, dict) else None

        return None

    @classmethod
    def _parse(cls, cleaned: str) -> GuideResponse:
        """Turn cleaned CLI output into a GuideResponse."""
        data = cls._extract_json(cleaned)

        if data is None:
            # The model answered in prose. Keep it rather than dropping the turn.
            return GuideResponse(summary=cleaned, raw=cleaned)

        steps = [str(s).strip() for s in data.get("steps") or [] if str(s).strip()]

        return GuideResponse(
            summary=str(data.get("summary") or "").strip(),
            steps=steps,
            done=bool(data.get("done")),
            raw=cleaned,
        )

    # ------------------------------------------------------------------ calls

    def _build_command(self) -> list[str]:
        """Build the kiro-cli command, resuming when a session already exists."""
        cmd = [
            "kiro-cli", "chat",
            "--no-interactive",
            "--trust-all-tools",
            "--model", self.model,
        ]
        if self._has_session:
            cmd.append("--resume")
        return cmd

    async def _run(self, prompt: str) -> GuideResponse:
        """
        Run kiro-cli with `prompt` on stdin and parse the answer.

        Args:
            prompt: Full prompt text

        Returns:
            GuideResponse; `error` is set when the call failed.
        """
        cmd = self._build_command()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.session_dir,
            )
        except FileNotFoundError:
            return GuideResponse(
                error="kiro-cli was not found. Install it and make sure it is on PATH."
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return GuideResponse(
                error=f"Kiro CLI timed out after {self.timeout:.0f}s. Try again."
            )

        raw_output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
        cleaned = self._clean_response(raw_output)

        if not cleaned:
            return GuideResponse(error="Kiro CLI returned an empty response.")

        # Only mark the session as live once there is something to resume.
        self._has_session = True

        return self._parse(cleaned)

    async def ask(
        self,
        prompt: str,
        screenshot_path: Optional[str] = None,
        system_context: str = "",
    ) -> GuideResponse:
        """
        Ask Kiro CLI for guidance, optionally about a screenshot.

        Args:
            prompt: The user request
            screenshot_path: Absolute path to a PNG of the current screen
            system_context: System prompt; only sent on the first call, since
                later calls resume the same conversation

        Returns:
            Parsed GuideResponse
        """
        parts = []

        if system_context and not self._has_session:
            parts.append(system_context)

        parts.append(f"User request: {prompt}")

        if screenshot_path:
            # An absolute path is used on purpose: it is verified to work with
            # kiro-cli's image reader regardless of the working directory.
            parts.append(
                f"Screenshot of the user's current screen: {screenshot_path}\n"
                "Read that image and base your answer on what is actually visible in it."
            )

        return await self._run("\n\n".join(parts))

    async def next_step(
        self,
        screenshot_path: str,
        task: str,
        current_step: int,
        total_steps: int,
    ) -> GuideResponse:
        """
        Ask for the next step of an in-progress task, using a fresh screenshot.

        Args:
            screenshot_path: Absolute path to a PNG of the current screen
            task: What the user is trying to do
            current_step: Step the user just completed
            total_steps: Total steps in the current guide

        Returns:
            Parsed GuideResponse
        """
        prompt = (
            f"The user is working on: {task}\n"
            f"They just completed step {current_step} of {total_steps}.\n"
            "Look at the new screenshot and tell them what to do next. "
            "If the task is finished, set \"done\" to true."
        )
        return await self.ask(prompt, screenshot_path=screenshot_path)
