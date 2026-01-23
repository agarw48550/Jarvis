#!/bin/bash
cd "$(dirname "$0")"

echo "🛠️  Setting up Google Assistant Environment..."

if [ -d "assistant_venv" ]; then
    echo "♻️  Removing existing broken assistant_venv..."
    rm -rf assistant_venv
fi

echo "📦 Creating new virtual environment (assistant_venv)..."
python3 -m venv assistant_venv

echo "📥 Installing Google Assistant SDK and dependencies..."
./assistant_venv/bin/pip install --upgrade pip
./assistant_venv/bin/pip install "google-assistant-sdk[samples]" google-auth-oauthlib "tenacity>=8.2.0" "click>=8.1.3" "urllib3>=2.0.0"

# Verify installation
if ./assistant_venv/bin/python3 -c "import googlesamples.assistant.grpc.textinput" 2>/dev/null; then
    echo "✅ Google Assistant SDK installed successfully!"
else
    echo "❌ Installation failed. Please check logs."
    exit 1
fi
