"""
KiroNav Audio Handler Module

Manages audio input (microphone) and output (speakers) for Gemini Live API.
"""

import asyncio
from typing import Optional

import pyaudio


# Audio configuration (from Gemini Live API docs)
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # Input: 16kHz
RECEIVE_SAMPLE_RATE = 24000  # Output: 24kHz
CHUNK_SIZE = 1024


class AudioHandler:
    """
    Handles audio input and output for Gemini Live API.
    
    Usage:
        audio = AudioHandler()
        await audio.start()
        
        # Audio input goes to queue for sending to Gemini
        # Audio output comes from queue received from Gemini
    """
    
    def __init__(self):
        self.pya: Optional[pyaudio.PyAudio] = None
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def _init_pyaudio(self):
        """Initialize PyAudio (must be called from thread)."""
        if self.pya is None:
            self.pya = pyaudio.PyAudio()
    
    async def start(self):
        """Start audio input and output streams."""
        self._init_pyaudio()
        
        if self.pya is None:
            raise RuntimeError("Failed to initialize PyAudio")
        
        # Get default input device
        try:
            mic_info = self.pya.get_default_input_device_info()
            device_index = mic_info["index"]
        except Exception as e:
            print(f"[AudioHandler] No microphone found: {e}")
            device_index = None
        
        # Open input stream (microphone)
        if device_index is not None:
            self.input_stream = await asyncio.to_thread(
                self.pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK_SIZE,
            )
        
        # Open output stream (speakers)
        self.output_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        
        self._running = True
    
    async def listen_audio(self, stop_event: asyncio.Event):
        """
        Continuously read audio from microphone and put in input queue.
        
        Args:
            stop_event: asyncio.Event to signal when to stop
        """
        if self.input_stream is None:
            print("[AudioHandler] No input stream available")
            return
        
        while not stop_event.is_set() and self._running:
            try:
                data = await asyncio.to_thread(
                    self.input_stream.read,
                    CHUNK_SIZE,
                    exception_on_overflow=False
                )
                
                payload = {
                    "data": data,
                    "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"
                }
                
                # Put in queue, drop oldest if full to keep real-time
                try:
                    self.input_queue.put_nowait(payload)
                except asyncio.QueueFull:
                    try:
                        self.input_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    self.input_queue.put_nowait(payload)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AudioHandler] Input error: {e}")
                await asyncio.sleep(0.1)
    
    async def play_audio(self, stop_event: asyncio.Event):
        """
        Continuously play audio from output queue to speakers.
        
        Args:
            stop_event: asyncio.Event to signal when to stop
        """
        if self.output_stream is None:
            print("[AudioHandler] No output stream available")
            return
        
        while not stop_event.is_set() and self._running:
            try:
                bytestream = await self.output_queue.get()
                await asyncio.to_thread(self.output_stream.write, bytestream)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AudioHandler] Output error: {e}")
                await asyncio.sleep(0.1)
    
    def cleanup(self):
        """Clean up audio resources."""
        self._running = False
        
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except:
                pass
        
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except:
                pass
        
        if self.pya:
            try:
                self.pya.terminate()
            except:
                pass


# Singleton instance for easy access
audio_handler = AudioHandler()
