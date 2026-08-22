#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "📦 Installing Linux dependencies (FFmpeg + libsodium)..."
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

# Force install PyNaCl for Discord voice support
echo "🔊 Installing PyNaCl for voice support..."
pip install --force-reinstall PyNaCl>=1.5.0

# Verify voice dependencies
python -c "import nacl; print(f'✅ PyNaCl {nacl.__version__} installed')" || echo "❌ PyNaCl install failed!"

echo "✅ Build Complete!"
