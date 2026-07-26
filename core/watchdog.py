"""
KiroNav Watchdog — Auto-advance detection

Periodically re-captures the screen and asks the model if the user
completed the current step. Stops polling after 2 consecutive "not done"
checks (user probably left or is stuck).
"""

import asyncio
from typing import Callable, Optional

POLL_INTERVAL = 15.0  # seconds between checks
MAX_IDLE_CHECKS = 2   # stop after this many "not done" responses


class Watchdog:
    """
    Watches for step completion by periodically checking the screen.

    Usage:
        watchdog = Watchdog(on_step_done=callback, on_stuck=stuck_callback)
        watchdog.start(check_fn)
        # ... later ...
        watchdog.stop()
    """

    def __init__(
        self,
        on_step_done: Optional[Callable] = None,
        on_stuck: Optional[Callable] = None,
        interval: float = POLL_INTERVAL,
        max_idle: int = MAX_IDLE_CHECKS,
    ):
        """
        Args:
            on_step_done: Async callback when the model says step is complete
            on_stuck: Async callback when max idle checks reached (user stuck/away)
            interval: Seconds between checks
            max_idle: Stop polling after this many "not done" responses
        """
        self._on_step_done = on_step_done
        self._on_stuck = on_stuck
        self._interval = interval
        self._max_idle = max_idle
        self._task: Optional[asyncio.Task] = None
        self._idle_count = 0
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, check_fn: Callable):
        """
        Start the watchdog polling loop.

        Args:
            check_fn: Async function that returns True if step is done, False otherwise
        """
        self.stop()
        self._idle_count = 0
        self._running = True
        self._task = asyncio.ensure_future(self._loop(check_fn))

    def stop(self):
        """Stop the watchdog."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._idle_count = 0

    def reset(self):
        """Reset idle counter (called when user manually advances)."""
        self._idle_count = 0

    async def _loop(self, check_fn: Callable):
        """Internal polling loop."""
        await asyncio.sleep(self._interval)  # initial wait before first check

        while self._running:
            try:
                step_done = await check_fn()

                if step_done:
                    self._idle_count = 0
                    if self._on_step_done:
                        await self._on_step_done()
                    # After advancing, wait before checking again
                    await asyncio.sleep(self._interval)
                else:
                    self._idle_count += 1
                    print(f"[Watchdog] Idle check {self._idle_count}/{self._max_idle}")

                    if self._idle_count >= self._max_idle:
                        print("[Watchdog] Max idle reached, stopping.")
                        self._running = False
                        if self._on_stuck:
                            await self._on_stuck()
                        return

                    await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                return
            except Exception as e:
                print(f"[Watchdog] Error: {e}")
                await asyncio.sleep(self._interval)
