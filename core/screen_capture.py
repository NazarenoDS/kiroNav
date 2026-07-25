"""
KiroNav Screen Capture Module

Captures screen frames using mss and sends them to Gemini Live API.
"""

import asyncio
import io
import base64
from typing import Optional

import mss
import PIL.Image


class ScreenCapture:
    """
    Captures screen frames and converts them to JPEG for Gemini Live API.
    
    Usage:
        capture = ScreenCapture()
        frame = await capture.get_frame()
        # frame is a dict with "mime_type" and "data" (base64 encoded JPEG)
    """
    
    def __init__(self, fps: int = 1):
        """
        Initialize screen capture.
        
        Args:
            fps: Frames per second to capture (default: 1, Gemini max is 1)
        """
        self.fps = fps
        self.sct: Optional[mss.mss] = None
        self._running = False
    
    def _init_sct(self):
        """Initialize mss screen capture (must be called from thread)."""
        if self.sct is None:
            self.sct = mss.mss()
    
    def _capture_frame_sync(self) -> Optional[dict]:
        """
        Capture a single screen frame synchronously.
        
        Returns:
            dict with "mime_type" and "data" (base64 encoded JPEG),
            or None if capture failed
        """
        self._init_sct()
        
        if self.sct is None:
            return None
        
        try:
            # Capture the entire screen (monitor 0)
            monitor = self.sct.monitors[0]
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            img = PIL.Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # Resize to reduce bandwidth (max 1024px width)
            img.thumbnail([1024, 1024])
            
            # Convert to JPEG
            image_io = io.BytesIO()
            img.save(image_io, format="JPEG", quality=70)
            image_io.seek(0)
            
            # Encode to base64
            image_bytes = image_io.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            return {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
            
        except Exception as e:
            print(f"[ScreenCapture] Error capturing frame: {e}")
            return None
    
    async def get_frame(self) -> Optional[dict]:
        """
        Capture a single screen frame asynchronously.
        
        Returns:
            dict with "mime_type" and "data" (base64 encoded JPEG),
            or None if capture failed
        """
        return await asyncio.to_thread(self._capture_frame_sync)
    
    async def stream_frames(self, queue: asyncio.Queue, stop_event: asyncio.Event):
        """
        Continuously capture screen frames and put them in a queue.
        
        Args:
            queue: asyncio.Queue to put frames into
            stop_event: asyncio.Event to signal when to stop
        """
        interval = 1.0 / self.fps
        
        while not stop_event.is_set():
            frame = await self.get_frame()
            
            if frame is not None:
                # Put frame in queue, drop oldest if full
                try:
                    queue.put_nowait(frame)
                except asyncio.QueueFull:
                    # Drop oldest frame to keep queue fresh
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    queue.put_nowait(frame)
            
            # Wait before next capture
            await asyncio.sleep(interval)
    
    def cleanup(self):
        """Clean up screen capture resources."""
        if self.sct is not None:
            self.sct.close()
            self.sct = None


# Singleton instance for easy access
screen_capture = ScreenCapture()
