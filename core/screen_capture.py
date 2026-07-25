"""
KiroNav Screen Capture Module

Captures screen frames and hands them to the AI backend as image files.

Backend selection:
- Wayland sessions use `grim`, because `mss` reads the Xwayland root window and
  returns a uniform black frame under compositors like Hyprland/Sway.
- Everything else falls back to `mss`.
"""

import asyncio
import base64
import io
import os
import shutil
import subprocess
import tempfile
from typing import Optional

import PIL.Image

# Max width/height sent to the model. Keeps the request small enough to stay fast
# while leaving UI text legible.
MAX_DIMENSION = 1280
JPEG_QUALITY = 75

# A capture whose brightest pixel is below this is treated as a failed grab
# (this is exactly the black-frame symptom mss produces on Wayland).
BLACK_FRAME_THRESHOLD = 8


class ScreenCaptureError(RuntimeError):
    """Raised when the screen could not be captured."""


def _is_wayland() -> bool:
    """Detect a Wayland session."""
    return bool(os.environ.get("WAYLAND_DISPLAY")) or (
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )


class ScreenCapture:
    """
    Captures the screen to an image file for the AI backend.

    Usage:
        capture = ScreenCapture()
        path = await capture.save_frame("/tmp/shot.png")
    """

    def __init__(self, fps: int = 1):
        """
        Initialize screen capture.

        Args:
            fps: Frames per second used by stream_frames()
        """
        self.fps = fps
        self._sct = None
        self._backend = self._detect_backend()
        print(f"[ScreenCapture] Backend: {self._backend}")

    @property
    def backend(self) -> str:
        """Name of the active capture backend."""
        return self._backend

    def _detect_backend(self) -> str:
        """Pick the capture backend for the current session."""
        if _is_wayland():
            if shutil.which("grim"):
                return "grim"
            print(
                "[ScreenCapture] WARNING: Wayland session without `grim`. "
                "Falling back to mss, which usually captures a black screen here. "
                "Install grim (e.g. `sudo pacman -S grim`)."
            )
        return "mss"

    # ---------------------------------------------------------------- capture

    def _capture_grim(self, path: str) -> None:
        """Capture the screen with grim (Wayland)."""
        result = subprocess.run(
            ["grim", path],
            capture_output=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise ScreenCaptureError(
                f"grim failed (exit {result.returncode}): {result.stderr.decode().strip()}"
            )

    def _capture_mss(self, path: str) -> None:
        """Capture the screen with mss (X11 / Windows / macOS)."""
        import mss

        if self._sct is None:
            self._sct = mss.mss()

        monitor = self._sct.monitors[0]
        shot = self._sct.grab(monitor)
        PIL.Image.frombytes("RGB", shot.size, shot.rgb).save(path)

    def _capture_sync(self, path: str) -> str:
        """
        Capture the screen to `path`, downscaled and re-encoded.

        Returns:
            The path the image was written to.

        Raises:
            ScreenCaptureError: capture failed or produced a black frame.
        """
        raw_path = path + ".raw.png"

        try:
            if self._backend == "grim":
                self._capture_grim(raw_path)
            else:
                self._capture_mss(raw_path)

            img = PIL.Image.open(raw_path).convert("RGB")

            # A uniformly black frame means the compositor refused the grab.
            # Surfacing it is far better than sending the model a blank image
            # and letting it hallucinate a UI.
            if img.convert("L").getextrema()[1] < BLACK_FRAME_THRESHOLD:
                raise ScreenCaptureError(
                    f"Capture via '{self._backend}' returned a black frame. "
                    "On Wayland this means the compositor blocked the grab."
                )

            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
            img.save(path, format="PNG", optimize=True)
            return path

        finally:
            if os.path.exists(raw_path):
                os.remove(raw_path)

    # ------------------------------------------------------------------- api

    async def save_frame(self, path: Optional[str] = None) -> str:
        """
        Capture the screen to a PNG file.

        Args:
            path: Destination path. Defaults to a temp file.

        Returns:
            Path to the written PNG.

        Raises:
            ScreenCaptureError: capture failed or produced a black frame.
        """
        if path is None:
            path = os.path.join(tempfile.gettempdir(), "kironav_screenshot.png")
        return await asyncio.to_thread(self._capture_sync, path)

    async def get_frame(self) -> Optional[dict]:
        """
        Capture a single frame as base64 JPEG.

        Returns:
            dict with "mime_type" and "data", or None if capture failed.
        """
        try:
            path = await self.save_frame()
        except ScreenCaptureError as e:
            print(f"[ScreenCapture] {e}")
            return None

        img = PIL.Image.open(path).convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY)

        return {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
        }

    async def stream_frames(self, queue: asyncio.Queue, stop_event: asyncio.Event):
        """
        Continuously capture frames into a queue, dropping stale frames.

        Args:
            queue: Queue to put frames into
            stop_event: Event that stops the loop
        """
        interval = 1.0 / self.fps

        while not stop_event.is_set():
            frame = await self.get_frame()

            if frame is not None:
                try:
                    queue.put_nowait(frame)
                except asyncio.QueueFull:
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    queue.put_nowait(frame)

            await asyncio.sleep(interval)

    def cleanup(self):
        """Release capture resources."""
        if self._sct is not None:
            self._sct.close()
            self._sct = None
