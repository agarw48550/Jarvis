import os
import sys
import tempfile

def main():
    try:
        import requests
    except Exception:
        print("[kokoro_test] The 'requests' package is not installed in this venv.")
        print("Activate 'jarvisai-venv' and run: pip install -r requirements.txt")
        sys.exit(1)

    base = os.getenv('KOKORO_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    voice = os.getenv('KOKORO_VOICE', 'daniel')
    speed = float(os.getenv('KOKORO_SPEED', '1.0'))

    # 1) Health check
    try:
        r = requests.get(base + '/health', timeout=5)
        ok = False
        try:
            data = r.json()
            ok = bool(data.get('ok'))
        except Exception:
            pass
        if not ok:
            print(f"[kokoro_test] Health check failed: {r.status_code} {r.text[:200]}")
            sys.exit(2)
        print("[kokoro_test] Health OK")
    except Exception as e:
        print(f"[kokoro_test] Health request error: {e}")
        sys.exit(2)

    # 2) Synthesize
    payload = {"text": "Hello from Kokoro.", "voice": voice, "speed": speed}
    try:
        r = requests.post(base + '/synthesize', json=payload, timeout=15)
        r.raise_for_status()
        ctype = r.headers.get('content-type', '')
        ext = '.mp3' if ('mpeg' in ctype or 'mp3' in ctype) else '.wav'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            out = f.name
            f.write(r.content)
        print(f"[kokoro_test] Wrote {out}")
        # Try to play it on macOS
        try:
            import subprocess
            subprocess.run(['afplay', out], check=False)
        except Exception:
            pass
        print("[kokoro_test] Success")
    except Exception as e:
        print(f"[kokoro_test] Synthesize error: {e}")
        sys.exit(3)


if __name__ == '__main__':
    main()
