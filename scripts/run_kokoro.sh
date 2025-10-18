#!/usr/bin/env bash
set -euo pipefail

# Start Kokoro FastAPI TTS server with sanity checks.
# Usage: scripts/run_kokoro.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

# Choose venv (prefer 3.12 one)
KOKORO_VENV="jarvisai-kokoro-venv312"
if [[ ! -d "$KOKORO_VENV" ]]; then
  echo "[kokoro] Python 3.12 venv '$KOKORO_VENV' not found. Create it with:" >&2
  echo "python3.12 -m venv jarvisai-kokoro-venv312" >&2
  echo "jarvisai-kokoro-venv312/bin/pip install --upgrade pip" >&2
  echo "jarvisai-kokoro-venv312/bin/pip install 'fastapi<0.120' uvicorn numpy soundfile pydantic requests librosa onnxruntime-silicon kokoro-onnx" >&2
  exit 1
fi

# Ensure model/voices paths resolve
DEFAULT_MODEL="tools/kokoro/models/kokoro-v1.0.onnx"
DEFAULT_VOICES="tools/kokoro/voices/voices.bin"

MODEL_PATH="${KOKORO_MODEL_PATH:-$DEFAULT_MODEL}"
VOICES_PATH="${KOKORO_VOICES_PATH:-$DEFAULT_VOICES}"

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "[kokoro] Base model not found at '$MODEL_PATH'." >&2
  echo "Place kokoro-v1.0.onnx there or set KOKORO_MODEL_PATH=/abs/path/to/kokoro-v1.0.onnx" >&2
  exit 1
fi
if [[ ! -f "$VOICES_PATH" ]]; then
  echo "[kokoro] Voices file not found at '$VOICES_PATH'." >&2
  echo "Place voices.bin there or set KOKORO_VOICES_PATH=/abs/path/to/voices.bin" >&2
  exit 1
fi

echo "[kokoro] Using model:  $MODEL_PATH"
echo "[kokoro] Using voices: $VOICES_PATH"

# Run server
exec "$KOKORO_VENV/bin/uvicorn" tools.kokoro.app:app --host 127.0.0.1 --port 8000
