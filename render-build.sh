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

# Force latest yt-dlp for YouTube bypass
echo "🎵 Force upgrading yt-dlp to latest..."
pip install --upgrade yt-dlp

# Verify dependencies
python -c "import nacl; print(f'✅ PyNaCl {nacl.__version__} installed')" || echo "❌ PyNaCl install failed!"
python -c "import yt_dlp; print(f'✅ yt-dlp {yt_dlp.version.__version__} installed')" || echo "❌ yt-dlp check failed!"

echo "✅ Build Complete!"
