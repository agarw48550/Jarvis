import rumps
import os
import sys
import threading
from core.wakeword import WakeWordListener
from core.session_manager import JarvisSession

# New imports for macOS power notifications (optional)
try:
    import objc
    from Foundation import NSObject
    from AppKit import NSWorkspace, NSWorkspaceWillSleepNotification
    _HAS_PYOBJC = True
except Exception:
    _HAS_PYOBJC = False

# Ensure we are in the correct directory for relative imports if run directly
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

class JarvisMenuApp(rumps.App):
    def __init__(self):
        # Start in Standby (listening for wake word)
        super(JarvisMenuApp, self).__init__("✦", icon=None)

        self.state = "STANDBY" # STANDBY, ACTIVE

        # Menu Items
        self.status_item = rumps.MenuItem("Status: ✦ Waiting for Wake Word")
        self.wake_item = rumps.MenuItem("Force Wake Up Now", callback=self.manual_wake)
        self.auth_item = rumps.MenuItem("Configure Google Access", callback=self.check_auth)
        self.quit_item = rumps.MenuItem("Quit Jarvis", callback=self.quit_app)

        self.menu = [
            self.status_item,
            rumps.separator,
            self.wake_item,
            rumps.separator,
            self.auth_item,
            rumps.separator,
            self.quit_item,
        ]
        
        # Components
        self.session = JarvisSession(on_status_change=self.on_session_status)
        self.wakeword = None
        
        # Update visibility initially
        self.update_menu_visibility()

        # Register macOS power event handlers if PyObjC is available
        if _HAS_PYOBJC:
            try:
                class _PowerObserver(NSObject):
                    def init(self):
                        self = objc.super(_PowerObserver, self).init()
                        self.app_ref = None
                        return self

                    def setApp_(self, app):
                        self.app_ref = app
                        self.register_observers()

                    def register_observers(self):
                        nc = NSWorkspace.sharedWorkspace().notificationCenter()
                        nc.addObserver_selector_name_object_(self, b'willSleep:', NSWorkspaceWillSleepNotification, None)
                        try:
                            from AppKit import NSWorkspaceDidWakeNotification
                            nc.addObserver_selector_name_object_(self, b'didWake:', NSWorkspaceDidWakeNotification, None)
                        except Exception:
                            pass

                    def willSleep_(self, notification):
                        try:
                            print('[POWER] System will sleep — pausing Jarvis...')
                            # Just pause, don't exit
                            if self.app_ref:
                                self.app_ref.turn_off()
                        except Exception as e:
                            print(f'[POWER] Error handling willSleep: {e}')

                    def didWake_(self, notification):
                        try:
                            print('[POWER] System did wake — resuming Jarvis standby...')
                            if self.app_ref:
                                # Re-initialize audio/wakeword
                                self.app_ref.enter_standby()
                        except Exception as e:
                            print(f'[POWER] Error restarting standby: {e}')

                self._power_observer = _PowerObserver.alloc().init()
                self._power_observer.setApp_(self)
            except Exception as e:
                print(f"[POWER] Failed to register power observer: {e}")

        # Always start in standby
        self.enter_standby()

    def update_menu_visibility(self):
        # Manage which buttons show up based on state
        if self.state == "STANDBY":
            self.status_item.title = "Status: ✦ Waiting for Wake Word"
            self.title = "✦"
        elif self.state == "ACTIVE":
            self.status_item.title = "Status: ◉ AI Session Active"
            self.title = "◉"

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
                return
        
        if not self.wakeword.running:
            self.wakeword.start()

    def manual_wake(self, _=None):
        print("[MENU] Manual Wake Up Triggered...")
        if self.wakeword and self.wakeword.running:
            self.wakeword.stop()
        
        self.start_session()

    def turn_off(self, _=None):
        print("[MENU] Stopping components...")
        self.state = "STANDBY"
        self.set_title_limited("✦")
        self.update_menu_visibility()
        
        # Stop everything
        if self.wakeword and self.wakeword.running:
            self.wakeword.stop()
        
        self.session.stop()

    def quit_app(self, _=None):
        print("[MENU] Quit requested — stopping and exiting")
        try:
            self.turn_off()
        finally:
            rumps.quit_application()

    def start_session(self):
        self.state = "ACTIVE"
        self.set_title_limited("◉")
        self.update_menu_visibility()
        
        os.system("afplay /System/Library/Sounds/Tink.aiff")
        try:
            self.session.start()
        except Exception as e:
            print(f"[MENU] Fatal error starting session: {e}")
            self.enter_standby()

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
            # Always return to standby
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
