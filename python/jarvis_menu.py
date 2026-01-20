
import rumps
import os
import sys
import threading
from core.wakeword import WakeWordListener
from core.session_manager import JarvisSession

# Ensure we are in the correct directory for relative imports if run directly
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

class JarvisMenuApp(rumps.App):
    def __init__(self):
        # Start with the Robot icon (OFF state)
        super(JarvisMenuApp, self).__init__("🤖", icon=None)
        
        self.state = "OFF" # OFF, STANDBY, ACTIVE
        
        # Menu Items
        self.status_item = rumps.MenuItem("Status: Offline")
        self.standby_item = rumps.MenuItem("Activate Standby Mode", callback=self.enter_standby)
        self.wake_item = rumps.MenuItem("Force Wake Up Now", callback=self.manual_wake)
        self.off_item = rumps.MenuItem("Turn Off Everything", callback=self.turn_off)
        self.auth_item = rumps.MenuItem("Configure Google Access", callback=self.check_auth)
        
        self.menu = [
            self.status_item,
            rumps.separator,
            self.standby_item,
            self.wake_item,
            self.off_item,
            rumps.separator,
            self.auth_item,
            rumps.separator,
            "Quit"
        ]
        
        # Components
        self.session = JarvisSession(on_status_change=self.on_session_status)
        self.wakeword = None
        
        # Update visibility initially
        self.update_menu_visibility()

    def update_menu_visibility(self):
        # Manage which buttons show up based on state
        if self.state == "OFF":
            self.standby_item.set_callback(self.enter_standby)
            self.wake_item.set_callback(self.manual_wake)
            self.off_item.set_callback(None)
            self.status_item.title = "Status: 🤖 Offline"
        elif self.state == "STANDBY":
            self.standby_item.set_callback(None)
            self.wake_item.set_callback(self.manual_wake)
            self.off_item.set_callback(self.turn_off)
            self.status_item.title = "Status: ✦ Waiting for Wake Word"
        elif self.state == "ACTIVE":
            self.standby_item.set_callback(None)
            self.wake_item.set_callback(None)
            self.off_item.set_callback(self.turn_off)
            self.status_item.title = "Status: ◉ AI Session Active"

    def set_title_limited(self, symbol):
        # Update the menu bar title with JUST the symbol
        self.title = symbol

    # --- STATE ACTIONS ---
    
    def enter_standby(self, _=None):
        print("[MENU] Entering Standby Mode...")
        self.state = "STANDBY"
        self.set_title_limited("✦")
        self.update_menu_visibility()
        
        # Start wake word listener
        if not self.wakeword:
            try:
                self.wakeword = WakeWordListener(callback=self.on_wakeword_detected)
            except Exception as e:
                rumps.alert("Wake Word Error", str(e))
                self.turn_off()
                return
        
        if not self.wakeword.running:
            self.wakeword.start()

    def manual_wake(self, _=None):
        print("[MENU] Manual Wake Up Triggered...")
        if self.wakeword and self.wakeword.running:
            self.wakeword.stop()
        
        self.start_session()

    def turn_off(self, _=None):
        print("[MENU] Turning Off...")
        self.state = "OFF"
        self.set_title_limited("🤖")
        self.update_menu_visibility()
        
        # Stop everything
        if self.wakeword and self.wakeword.running:
            self.wakeword.stop()
        
        self.session.stop()

    def start_session(self):
        self.state = "ACTIVE"
        self.set_title_limited("◉")
        self.update_menu_visibility()
        
        os.system("afplay /System/Library/Sounds/Tink.aiff")
        try:
            self.session.start()
        except Exception as e:
            print(f"[MENU] Fatal error starting session: {e}")
            self.turn_off()

    # --- CALLBACKS ---

    def on_wakeword_detected(self):
        """Called when Porcupine detects the keyword"""
        def handle_detection():
            print("⚡ Wake word triggered! Transitioning to Active AI...")
            if self.wakeword:
                self.wakeword.stop()
            
            import time
            time.sleep(0.3) 
            self.start_session()
            
        threading.Thread(target=handle_detection, daemon=True).start()

    def on_session_status(self, status, extra=None):
        print(f"[MENU] AI Status: {status}")
        
        if status == "STOPPED":
            # Go back to STANDBY (waiting for next wake) instead of OFF
            self.enter_standby()
            
        elif status == "LISTENING":
            self.set_title_limited("◉")
        elif status == "SPEAKING":
            self.set_title_limited("◍")
        elif status == "PROCESSING":
            self.set_title_limited("◌")

    def check_auth(self, _):
        import subprocess
        import shlex
        script_path = os.path.join(script_dir, "google_auth.py")
        # Use subprocess.run with argument list to avoid shell injection
        activate_script = 'tell application "Terminal" to activate'
        do_script = f'tell application "Terminal" to do script "cd {shlex.quote(script_dir)} && ./venv/bin/python3 {shlex.quote(script_path)}"'
        subprocess.run(["osascript", "-e", activate_script, "-e", do_script], check=False)
        rumps.notification("Jarvis Setup", "Opening Terminal", "Please follow instructions to authorize Google.")

if __name__ == "__main__":
    app = JarvisMenuApp()
    app.run()
