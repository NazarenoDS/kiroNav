"""
KiroNav Gemini Live Session

Manages the WebSocket connection to Gemini Live API.
"""

import asyncio
import os
from typing import Optional, Callable, Any

from google import genai
from google.genai import types

from .screen_capture import ScreenCapture
from .audio_handler import AudioHandler


class GeminiLiveSession:
    """
    Manages a live session with Gemini Live API.
    
    Handles:
    - WebSocket connection
    - Screen frame streaming
    - Audio streaming (input/output)
    - Function calling (tools)
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-live-preview",
        voice: str = "Zephyr",
    ):
        """
        Initialize Gemini Live session.
        
        Args:
            api_key: Google AI Studio API key
            model: Model to use (default: gemini-3.1-flash-live-preview)
            voice: Voice for audio output (default: Zephyr)
        """
        self.api_key = api_key
        self.model = model
        self.voice = voice
        
        # Initialize client
        self.client = genai.Client(api_key=api_key)
        
        # State
        self.session: Any = None
        self.screen_capture = ScreenCapture()
        self.audio_handler = AudioHandler()
        self._connected = False
        self._listening = False
        self._tool_callbacks: dict[str, Callable] = {}
    
    def on_tool_call(self, tool_name: str, callback: Callable):
        """
        Register a callback for when Gemini calls a tool.
        
        Args:
            tool_name: Name of the tool (e.g., "highlight_region")
            callback: Async function to call with tool name and arguments
        """
        self._tool_callbacks[tool_name] = callback
    
    def _get_tools(self) -> list:
        """Get tool declarations for Gemini."""
        from tools.function_tools import KIRONAV_TOOLS
        return [types.Tool(function_declarations=KIRONAV_TOOLS)]
    
    def _get_config(self, system_instruction: str) -> types.LiveConnectConfig:
        """Build LiveConnectConfig."""
        return types.LiveConnectConfig(
            system_instruction=system_instruction,
            tools=self._get_tools(),
            response_modalities=["AUDIO", "TEXT"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice
                    )
                )
            ),
        )
    
    async def connect(self, system_instruction: str):
        """
        Connect to Gemini Live API and start a session.
        
        Args:
            system_instruction: System prompt for the AI
        """
        config = self._get_config(system_instruction)
        
        self.session = self.client.aio.live.connect(
            model=self.model,
            config=config,
        )
        
        # Start audio streams
        await self.audio_handler.start()
        
        self._connected = True
        print("[GeminiLive] Connected to Gemini Live API")
    
    async def send_screen_frame(self):
        """Send current screen frame to Gemini."""
        if not self._connected or self.session is None:
            return
        
        frame = await self.screen_capture.get_frame()
        if frame:
            await self.session.send_client_content(
                turns=types.LiveClientContent(
                    role="user",
                    parts=[types.Part(
                        inline_data=types.Blob(
                            mime_type=frame["mime_type"],
                            data=frame["data"]
                        )
                    )]
                )
            )
    
    async def send_audio_chunk(self, audio_data: bytes):
        """
        Send audio chunk to Gemini.
        
        Args:
            audio_data: PCM audio bytes
        """
        if not self._connected or self.session is None:
            return
        
        await self.session.send_realtime_input(
            audio=types.Blob(
                mime_type="audio/pcm;rate=16000",
                data=audio_data
            )
        )
    
    async def listen_for_responses(self):
        """Listen for responses from Gemini and handle tool calls."""
        if not self._connected or self.session is None:
            return
        
        while self._connected:
            try:
                async for response in self.session.receive():
                    # Handle server content (audio/text)
                    if response.server_content:
                        model_turn = response.server_content.model_turn
                        
                        for part in model_turn.parts:
                            # Handle audio response
                            if part.inline_data:
                                await self.audio_handler.output_queue.put(
                                    part.inline_data.data
                                )
                            
                            # Handle text response (for debugging)
                            if part.text:
                                print(f"[GeminiLive] Text: {part.text}")
                    
                    # Handle tool calls
                    if response.tool_call:
                        function_calls = response.tool_call.function_calls
                        
                        for fc in function_calls:
                            await self._handle_tool_call(fc.name, fc.args)
                    
                    # Handle tool call cancellation
                    if response.tool_call_cancellation:
                        print(f"[GeminiLive] Tool call cancelled: {response.tool_call_cancellation.ids}")
                        
            except Exception as e:
                print(f"[GeminiLive] Error receiving response: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_tool_call(self, tool_name: str, args: dict):
        """
        Handle a tool call from Gemini.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
        """
        print(f"[GeminiLive] Tool called: {tool_name}({args})")
        
        # Call registered callback
        if tool_name in self._tool_callbacks:
            result = await self._tool_callbacks[tool_name](args)
        else:
            result = {"status": "ok", "tool": tool_name, "args": args}
        
        # Send result back to Gemini
        await self.session.send_tool_response(
            function_responses=[
                types.FunctionResponse(
                    name=tool_name,
                    response=result
                )
            ]
        )
    
    async def send_text(self, text: str):
        """
        Send text message to Gemini.
        
        Args:
            text: Text to send
        """
        if not self._connected or self.session is None:
            return
        
        await self.session.send_client_content(
            turns=types.LiveClientContent(
                role="user",
                parts=[types.Part(text=text)]
            )
        )
    
    async def disconnect(self):
        """Disconnect from Gemini Live API."""
        self._connected = False
        
        if self.session:
            await self.session.close()
            self.session = None
        
        self.audio_handler.cleanup()
        self.screen_capture.cleanup()
        
        print("[GeminiLive] Disconnected")


async def test_connection():
    """Quick test to verify connection works."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GOOGLE_API_KEY environment variable")
        return
    
    session = GeminiLiveSession(api_key=api_key)
    
    try:
        print("Connecting to Gemini Live API...")
        await session.connect(
            system_instruction="You are a helpful assistant named KiroNav. Speak briefly and clearly."
        )
        print("Connected! Sending test message...")
        
        await session.send_text("Hello, say 'test' to confirm you're working.")
        
        # Listen for a few seconds
        await asyncio.sleep(5)
        
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(test_connection())
