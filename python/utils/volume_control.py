import subprocess

class VolumeController:
    """
    Controls system and media player volume on macOS via AppleScript.
    Used for ducking audio when the AI speaks.
    """

    def __init__(self):
        self._ducked = False
        self._original_vol_spotify = None
        self._original_vol_music = None

    def _run_applescript(self, script):
        try:
            cmd = ['osascript', '-e', script]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            print(f"Volume Control Error: {e}")
            return None

    def _is_app_running(self, app_name):
        """Return True if a process with app_name is running."""
        script = f'tell application "System Events" to (exists process "{app_name}")'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() == "true"
        except subprocess.CalledProcessError:
            return False

    def duck_media(self, target_percent=5):
        """Lower media volume to target_percent (0-100)"""
        if self._ducked:
            return

        # Check Spotify
        if self._is_app_running("Spotify"):
            try:
                state = self._run_applescript('tell application "Spotify" to player state')
                if state == "playing":
                    vol = self._run_applescript('tell application "Spotify" to sound volume')
                    if vol and vol.isdigit():
                        self._original_vol_spotify = int(vol)
                        self._run_applescript(f'tell application "Spotify" to set sound volume to {target_percent}')
            except Exception:
                pass

        # Check Music (Apple Music)
        if self._is_app_running("Music"):
            try:
                state = self._run_applescript('tell application "Music" to player state')
                if state == "playing":
                    vol = self._run_applescript('tell application "Music" to sound volume')
                    if vol and vol.isdigit():
                        self._original_vol_music = int(vol)
                        self._run_applescript(f'tell application "Music" to set sound volume to {target_percent}')
            except Exception:
                pass

        self._ducked = True

    def restore_media(self):
        """Restore media volume to original levels"""
        if not self._ducked:
            return

        if self._original_vol_spotify is not None and self._is_app_running("Spotify"):
            self._run_applescript(f'tell application "Spotify" to set sound volume to {self._original_vol_spotify}')
            self._original_vol_spotify = None

        if self._original_vol_music is not None and self._is_app_running("Music"):
            self._run_applescript(f'tell application "Music" to set sound volume to {self._original_vol_music}')
            self._original_vol_music = None

        self._ducked = False
