"""
KiroNav Kiro CLI Backend

Uses Kiro CLI as the AI backend instead of Gemini Live API.
Captures screen → saves as image → asks Kiro CLI → parses response.
"""

import asyncio
import os
import re
import subprocess
import tempfile
from typing import Optional, Callable


class KiroCLIBackend:
    """
    Backend that uses Kiro CLI for AI inference.
    
    Flow:
    1. Capture screen → save as PNG
    2. Call kiro-cli with prompt + screenshot reference
    3. Parse response
    4. Return to UI
    """
    
    def __init__(
        self,
        model: str = "claude-haiku-4.5",
        project_dir: Optional[str] = None,
    ):
        """
        Initialize Kiro CLI backend.
        
        Args:
            model: Kiro model to use (default: claude-haiku-4.5 for speed)
            project_dir: Project directory for Kiro CLI context
        """
        self.model = model
        self.project_dir = project_dir or os.path.dirname(os.path.dirname(__file__))
        self._tool_callbacks: dict[str, Callable] = {}
    
    def on_tool_call(self, tool_name: str, callback: Callable):
        """Register tool callback."""
        self._tool_callbacks[tool_name] = callback
    
    def _clean_response(self, raw_output: str) -> str:
        """Extract clean response text from Kiro CLI output."""
        # Remove ANSI escape codes
        cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_output)
        cleaned = re.sub(r'\x1b\[[?][0-9]*[a-zA-Z]', '', cleaned)
        
        # Split on "> " to get response segments
        parts = cleaned.split('> ')
        
        # Find the longest meaningful segment (actual response)
        best = ""
        for part in parts:
            part = part.strip()
            # Remove trailing noise
            part = re.sub(r'All tools are now trusted.*', '', part, flags=re.DOTALL)
            part = re.sub(r'▸?\s*Credits:.*', '', part, flags=re.DOTALL)
            part = re.sub(r'Reading images:.*', '', part, flags=re.DOTALL)
            part = re.sub(r'\(using tool:.*?\)', '', part)
            part = re.sub(r'✓.*', '', part)
            part = re.sub(r'- Completed in.*', '', part)
            part = re.sub(r'Learn more at.*', '', part)
            part = re.sub(r'Agents can.*risks\.?', '', part)
            part = re.sub(r'\[.*?\]', '', part)
            part = part.strip()
            
            if len(part) > len(best):
                best = part
        
        return best if best else "No response received"
    
    async def ask_with_screenshot(
        self,
        prompt: str,
        screenshot_path: str,
        system_context: str = "",
    ) -> str:
        """
        Send a prompt with a screenshot to Kiro CLI.
        
        Args:
            prompt: The question/instruction
            screenshot_path: Path to screenshot PNG
            system_context: Optional system context
            
        Returns:
            Response text
        """
        # Build the full prompt
        full_prompt = prompt
        if system_context:
            full_prompt = f"{system_context}\n\nUser request: {prompt}"
        
        # Add screenshot reference
        rel_path = os.path.relpath(screenshot_path, self.project_dir)
        full_prompt += f"\n\nI'm looking at the screenshot in {rel_path}. Analyze it and respond."
        
        # Run Kiro CLI
        cmd = [
            "kiro-cli", "chat",
            "--no-interactive",
            "--trust-all-tools",
            "--model", self.model,
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=full_prompt.encode()),
                timeout=60.0
            )
            
            raw_output = stdout.decode() + stderr.decode()
            response = self._clean_response(raw_output)
            
            print(f"[KiroCLI] Response: {response[:100]}...")
            return response
            
        except asyncio.TimeoutError:
            return "Error: Kiro CLI timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def ask_text_only(
        self,
        prompt: str,
        system_context: str = "",
    ) -> str:
        """
        Send a text-only prompt to Kiro CLI (no screenshot).
        
        Args:
            prompt: The question/instruction
            system_context: Optional system context
            
        Returns:
            Response text
        """
        full_prompt = prompt
        if system_context:
            full_prompt = f"{system_context}\n\nUser request: {prompt}"
        
        cmd = [
            "kiro-cli", "chat",
            "--no-interactive",
            "--trust-all-tools",
            "--model", self.model,
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=full_prompt.encode()),
                timeout=60.0
            )
            
            raw_output = stdout.decode() + stderr.decode()
            return self._clean_response(raw_output)
            
        except asyncio.TimeoutError:
            return "Error: Kiro CLI timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def guide_step(
        self,
        screenshot_path: str,
        task: str,
        current_step: int,
        total_steps: int,
    ) -> dict:
        """
        Get guidance for a specific step with screenshot context.
        
        Args:
            screenshot_path: Current screen state
            task: What the user is trying to do
            current_step: Current step number
            total_steps: Total steps
            
        Returns:
            dict with instruction, highlights, and next_action
        """
        prompt = f"""I'm helping a user complete this task: {task}
This is step {current_step} of {total_steps}.

Look at the screenshot and tell me:
1. What should the user do NEXT (one clear instruction)
2. Where on screen they should look/click (describe location)
3. After they do it, what's the sign that the step succeeded

Format your response as:
ACTION: [instruction]
LOCATION: [where to look/click]
SUCCESS_SIGN: [how to know it worked]"""
        
        response = await self.ask_with_screenshot(prompt, screenshot_path)
        
        # Parse structured response
        result = {
            "instruction": response,
            "location": "",
            "success_sign": "",
        }
        
        for line in response.split('\n'):
            if line.startswith('ACTION:'):
                result["instruction"] = line.replace('ACTION:', '').strip()
            elif line.startswith('LOCATION:'):
                result["location"] = line.replace('LOCATION:', '').strip()
            elif line.startswith('SUCCESS_SIGN:'):
                result["success_sign"] = line.replace('SUCCESS_SIGN:', '').strip()
        
        return result


# Singleton
kiro_backend = KiroCLIBackend()
