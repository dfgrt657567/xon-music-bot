#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "📦 Installing Linux dependencies (FFmpeg)..."
# Render Linux environment: install static ffmpeg if not present
mkdir -p bin
if [ ! -f "bin/ffmpeg" ]; then
    echo "Downloading static FFmpeg build for Linux..."
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ --strip-components=1 -C bin
fi

export PATH="$PWD/bin:$PATH"

echo "🐍 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build Complete!"
