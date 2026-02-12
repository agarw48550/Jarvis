"""
Diagnostic Tools for Jarvis
Self-healing capabilities: health checks, system status, and auto-fix.
"""

import os
import sys
import time
import platform
import subprocess
import psutil


def run_health_check() -> str:
    """Run a health check on all Jarvis subsystems.
    
    Tests: API keys, database, audio, network, memory, disk space.
    
    Returns:
        Formatted health report
    """
    checks = []
    
    # 1. API Keys
    keys_status = []
    for key_name in ["GEMINI_API_KEY", "GROQ_API_KEY", "PICOVOICE_ACCESS_KEY"]:
        val = os.getenv(key_name)
        if val and len(val) > 5:
            keys_status.append(f"  ✅ {key_name}: configured")
        else:
            keys_status.append(f"  ❌ {key_name}: MISSING")
    checks.append("🔑 API Keys:\n" + "\n".join(keys_status))
    
    # 2. Database
    try:
        from core.memory import init_database
        init_database()
        checks.append("💾 Database: ✅ OK")
    except Exception as e:
        checks.append(f"💾 Database: ❌ {e}")
    
    # 3. Audio subsystem
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        device_count = pa.get_device_count()
        default_input = pa.get_default_input_device_info()
        pa.terminate()
        checks.append(f"🎤 Audio: ✅ {device_count} devices, input: {default_input['name']}")
    except Exception as e:
        checks.append(f"🎤 Audio: ❌ {e}")
    
    # 4. Network
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            checks.append("🌐 Network: ✅ Connected")
        else:
            checks.append("🌐 Network: ❌ No internet connection")
    except Exception:
        checks.append("🌐 Network: ⚠️ Could not check")
    
    # 5. Memory & CPU
    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        checks.append(f"🧠 System: RAM {mem.percent}% used ({mem.available // (1024**3)}GB free), CPU {cpu}%")
    except Exception as e:
        checks.append(f"🧠 System: ⚠️ {e}")
    
    # 6. Disk Space
    try:
        disk = psutil.disk_usage('/')
        checks.append(f"💿 Disk: {disk.percent}% used ({disk.free // (1024**3)}GB free)")
    except Exception as e:
        checks.append(f"💿 Disk: ⚠️ {e}")
    
    # 7. Python Version
    checks.append(f"🐍 Python: {sys.version.split()[0]}")
    
    # 8. Wake word
    try:
        import pvporcupine
        checks.append(f"👂 Porcupine: ✅ v{pvporcupine.LIBRARY_PATH is not None}")
    except ImportError:
        checks.append("👂 Porcupine: ❌ Not installed")
    
    return "🏥 Jarvis Health Report:\n" + "\n".join(checks)


def get_system_status() -> str:
    """Get current system status: CPU, RAM, disk, uptime, battery.
    
    Returns:
        System status report
    """
    lines = ["📊 System Status:"]
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        lines.append(f"  CPU: {cpu_percent}% ({cpu_count} cores)")
        
        # RAM
        mem = psutil.virtual_memory()
        lines.append(f"  RAM: {mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)")
        
        # Disk
        disk = psutil.disk_usage('/')
        lines.append(f"  Disk: {disk.percent}% ({disk.free // (1024**3)}GB free)")
        
        # Battery
        battery = psutil.sensors_battery()
        if battery:
            plug_status = "⚡ Plugged in" if battery.power_plugged else "🔋 On battery"
            lines.append(f"  Battery: {battery.percent}% {plug_status}")
        
        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        lines.append(f"  Uptime: {hours}h {minutes}m")
        
        # macOS version
        lines.append(f"  OS: macOS {platform.mac_ver()[0]}")
        
    except Exception as e:
        lines.append(f"  Error: {e}")
    
    return "\n".join(lines)


def fix_common_issues() -> str:
    """Attempt to automatically fix common Jarvis issues.
    
    Fixes attempted:
    - Restart audio subsystem
    - Re-initialize database
    - Clear stale sessions
    - Reset stuck state
    
    Returns:
        Report of fixes attempted
    """
    fixes = ["🔧 Auto-Fix Report:"]
    
    # 1. Re-initialize database
    try:
        from core.memory import init_database
        init_database()
        fixes.append("  ✅ Database re-initialized")
    except Exception as e:
        fixes.append(f"  ❌ Database fix failed: {e}")
    
    # 2. Kill any zombie PyAudio instances
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        pa.terminate()
        fixes.append("  ✅ Audio subsystem reset")
    except Exception as e:
        fixes.append(f"  ⚠️ Audio reset: {e}")
    
    # 3. Clear temp files
    try:
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.gettempdir()) / 'jarvis'
        if tmp.exists():
            count = 0
            for f in tmp.iterdir():
                if f.is_file() and (time.time() - f.stat().st_mtime) > 3600:
                    f.unlink()
                    count += 1
            fixes.append(f"  ✅ Cleared {count} stale temp files")
    except Exception as e:
        fixes.append(f"  ⚠️ Temp cleanup: {e}")
    
    # 4. Check and fix permissions on data directory
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if os.path.exists(data_dir):
            os.chmod(data_dir, 0o755)
            fixes.append("  ✅ Data directory permissions OK")
    except Exception as e:
        fixes.append(f"  ⚠️ Permission fix: {e}")
    
    return "\n".join(fixes)
