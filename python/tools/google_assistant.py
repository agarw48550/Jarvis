#!/usr/bin/env python3
"""
Google Assistant Tool
Allows Jarvis to control smart home devices via Google Assistant SDK.
"""

import os
import sys
import json
import uuid
import subprocess
from pathlib import Path

# Paths to credentials
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / 'google_credentials.json' # User provided OAuth2 credentials


ASSISTANT_VENV_PYTHON = BASE_DIR / 'assistant_venv' / 'bin' / 'python3'

def send_assistant_command(command: str) -> str:
    """
    Sends a text command to Google Assistant and returns the text response.
    Uses google-assistant-sdk text input.
    """
    print(f"📡 Sending command to Google Assistant: '{command}'")

    if not CREDENTIALS_FILE.exists():
        return "Error: google_credentials.json not found in jarvis/python/ directory."

    if not ASSISTANT_VENV_PYTHON.exists():
        return "Error: assistant_venv not found. Please run the setup script to create the assistant environment."

    # Compatibility fix: create a token file without the 'token' field if the sdk is old
    token_path = BASE_DIR / 'google_token.json'
    compat_token_path = BASE_DIR / 'google_token_assistant.json'

    if token_path.exists():
        try:
            with open(token_path, 'r') as f:
                data = json.load(f)

            # If 'token' exists, remove it for the legacy environment to avoid conflict
            # "got multiple values for keyword argument 'token'"
            if 'token' in data:
                del data['token']
                with open(compat_token_path, 'w') as f:
                    json.dump(data, f)
                token_path = compat_token_path
            else:
                pass
        except Exception as e:
            print(f"Warning: Failed to process token for compatibility: {e}")

    try:
        # Construct the command using the isolated environment's python
        # Note: textinput sample reads from stdin, it does not have a --query argument.
        cmd = [
            str(ASSISTANT_VENV_PYTHON), '-m', 'googlesamples.assistant.grpc.textinput',
            '--device-model-id', 'jarvis-v3',
            '--device-id', f'jarvis-{uuid.uuid4()}',
            '--credentials', str(token_path)
        ]

        process = subprocess.run(
            cmd, 
            input=f"{command}\n", # Send command via stdin
            capture_output=True,
            text=True,
            timeout=25, # Slightly longer timeout
            cwd=str(BASE_DIR)
        )

        output = process.stdout
        stderr = process.stderr

        # The tool might return partial success or just abort on EOF/Audio issue.
        # If we see conversational turns in stdout, we might consider it a success.

        if process.returncode == 0:
            return f"Assistant executed: {command}. Output: {output[:200]}..."

        if output and ("<you>" in output or "AssistResponse" in output or "Turn" in output):
             # Likely succeeded but crashed on audio/exit
             return f"Assistant executed (with warnings): {command}. Output: {output[:200]}..."

        if "no module named" in stderr.lower() or "not found" in stderr.lower():
             return f"Error: Google Assistant module not found in assistant_venv ({stderr.strip()})"
        if "credentials" in stderr.lower():
             return "Error: Google Assistant credentials invalid or not authorized."

        return f"Error executing command (Exit Code {process.returncode}): {stderr} \nOutput: {output}"

    except subprocess.TimeoutExpired:
        return "Error: Google Assistant command timed out."
    except Exception as e:
        return f"Error: {e}"


# Add a thin adapter expected by the rest of the codebase
def control_device(command: str) -> str:
    """Compatibility wrapper used by tool registry.

    Checks whether Google OAuth has been configured and returns helpful messages
    if not. Otherwise forwards the command to send_assistant_command.
    """
    try:
        # Lazy import to avoid a hard dependency at module import time
        from google_auth import is_authenticated
    except Exception:
        # If google_auth is missing or broken, just attempt to run and return any errors
        is_auth = False
    else:
        try:
            is_auth = is_authenticated()
        except Exception:
            is_auth = False

    if not is_auth:
        return "Google Assistant not configured or authentication expired. Please run google_auth.py to authorize."

    return send_assistant_command(command)

# Fallback/alternative using a more direct library approach if the sample is not robust
# But for now, let's stick to the simplest integration.
