import os
import sys
import threading

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# #region agent log
def _agent_log(*a, **k):
    try:
        from debug_log import _agent_log as _log
        _log(*a, **k)
    except Exception:
        pass
try:
    from debug_log import _agent_log as _agent_log_impl
    _agent_log = _agent_log_impl
    _agent_log("jarvis_menu.py:start", "script_start", hypothesis_id="H1")
except Exception:
    pass
# #endregion

import rumps
try:
    from core.wakeword import WakeWordListener
    _agent_log("jarvis_menu.py:imports", "wakeword_ok", hypothesis_id="H1")
except Exception as e:
    _agent_log("jarvis_menu.py:imports", "wakeword_import_fail", data={"error": str(e)}, hypothesis_id="H2")
    raise
try:
    from core.session_manager import JarvisSession
    _agent_log("jarvis_menu.py:imports", "session_manager_ok", hypothesis_id="H1")
except Exception as e:
    _agent_log("jarvis_menu.py:imports", "session_manager_import_fail", data={"error": str(e)}, hypothesis_id="H1")
    raise

# New imports for macOS power notifications (optional)
try:
    import objc
    from Foundation import NSObject
    from AppKit import NSWorkspace, NSWorkspaceWillSleepNotification
    _HAS_PYOBJC = True
except Exception:
    _HAS_PYOBJC = False

class UpdateManager(threading.Thread):
    def __init__(self, interval=1800): # 30 mins
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True

    def check_for_updates(self):
        try:
            # Check if we are in a git repo
            if not os.path.exists(os.path.join(os.path.dirname(script_dir), ".git")):
                return False
                
            # git fetch to check remote
            subprocess.run(["git", "fetch"], check=True, capture_output=True, cwd=os.path.dirname(script_dir))
            
            # Compare HEAD with upstream
            local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(script_dir)).decode().strip()
            remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=os.path.dirname(script_dir)).decode().strip()
            
            if local != remote:
                print("🔄 [UPDATE] New version available! Updating...")
                # git pull
                subprocess.run(["git", "pull"], check=True, cwd=os.path.dirname(script_dir))
                
                # Re-install requirements if they changed
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True, cwd=script_dir)
                
                # Notify and Restart
                print("🚀 [UPDATE] Update complete. Restarting Jarvis...")
                restart_script = os.path.join(script_dir, "restart_jarvis.sh")
                if os.path.exists(restart_script):
                    subprocess.Popen(["bash", restart_script])
                return True
        except Exception as e:
            print(f"⚠️ [UPDATE] Check failed: {e}")
        return False

    def run(self):
        # Initial wait to let system settle
        time.sleep(60)
        while self.running:
            if self.check_for_updates():
                break
            time.sleep(self.interval)

def ensure_single_instance():
    """Ensure only one instance of Jarvis is running."""
    import psutil
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if process is python and running jarvis_menu.py
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline'] or []
                if any('jarvis_menu.py' in arg for arg in cmdline):
                    if proc.info['pid'] != current_pid:
                        print(f"⚠️ Found existing instance (PID {proc.info['pid']}). Keying it...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

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

        # Health Check Timer (Run every 5 seconds)
        self.health_timer = rumps.Timer(self.health_check, 5)
        self.health_timer.start()

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
        # #region agent log
        _agent_log("jarvis_menu.py:enter_standby", "enter", hypothesis_id="H2")
        # #endregion
        print("[MENU] Entering Standby Mode...")
        self.state = "STANDBY"
        self.set_title_limited("✦")
        self.update_menu_visibility()
        
        # Start wake word listener
        if not self.wakeword:
            try:
                self.wakeword = WakeWordListener(callback=self.on_wakeword_detected)
                _agent_log("jarvis_menu.py:enter_standby", "wakeword_init_ok", hypothesis_id="H2")
            except Exception as e:
                _agent_log("jarvis_menu.py:enter_standby", "wakeword_init_fail", data={"error": str(e)}, hypothesis_id="H2")
                print(f"⚠️ Wake Word Init Error: {e}")
                return
        
        if not self.wakeword.running:
            try:
                self.wakeword.start()
                _agent_log("jarvis_menu.py:enter_standby", "wakeword_start_ok", hypothesis_id="H2")
            except Exception as e:
                _agent_log("jarvis_menu.py:enter_standby", "wakeword_start_fail", data={"error": str(e)}, hypothesis_id="H2")
                print(f"⚠️ Wake Word Start Error: {e}")

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
        # #region agent log
        _agent_log("jarvis_menu.py:start_session", "enter", hypothesis_id="H3")
        # #endregion
        self.state = "ACTIVE"
        self.set_title_limited("◉")
        self.update_menu_visibility()
        
        try:
            self.session.start()
            _agent_log("jarvis_menu.py:start_session", "session_start_ok", hypothesis_id="H3")
        except Exception as e:
            _agent_log("jarvis_menu.py:start_session", "session_start_fail", data={"error": str(e)}, hypothesis_id="H3")
            print(f"[MENU] Fatal error starting session: {e}")
            self.enter_standby()

    # --- CALLBACKS ---

    def on_wakeword_detected(self):
        """Called when Porcupine detects the keyword"""
        def handle_detection():
            _agent_log("jarvis_menu.py:on_wakeword", "detected", hypothesis_id="H2")
            print("⚡ Wake word triggered! Transitioning to Active AI...")
            if self.wakeword:
                self.wakeword.stop()
            
            # Reduce delay and run audio in background to speed up transition
            import subprocess
            subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])
            
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

    def health_check(self, _):
        """Periodically checks if the system is in a valid state and recovers if not."""
        # Case 1: Active, but session dead
        if self.state == "ACTIVE":
            # Give session thread time to start (avoid race condition)
            if self.session.thread is None:
                # Thread not created yet - might still be initializing
                return
            if not self.session.thread.is_alive():
                print("⚠️ [HEALTH] Session thread died unexpectedly. Resetting to Standby.")
                self.enter_standby()

        # Case 2: Standby, but wake word not running
        elif self.state == "STANDBY":
            if not self.wakeword:
                 print("⚠️ [HEALTH] Wakeword missing. Re-initializing...")
                 self.enter_standby()
            elif not self.wakeword.running:
                 print("⚠️ [HEALTH] Wakeword stopped unexpectedly. Restarting...")
                 try:
                     self.wakeword.start()
                 except Exception as e:
                     print(f"⚠️ [HEALTH] Failed to restart wakeword: {e}")

if __name__ == "__main__":
    try:
        ensure_single_instance()
    except Exception as e:
        print(f"Singleton check failed: {e}")
        
    # Start auto-update manager
    UpdateManager().start()
    
    app = JarvisMenuApp()
    app.run()
