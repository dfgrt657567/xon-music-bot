"""
YouTube Cookie Export Script for XON Music Bot
===============================================
Run this script ONCE on your PC where YouTube is logged in.
It will create a cookies.txt file that yt-dlp uses on Render.

Usage: python export_cookies.py
"""
import os
import sys
import subprocess
import shutil


def export_cookies():
    print("=" * 60)
    print("🍪 YouTube Cookie Export for XON Music Bot")
    print("=" * 60)

    cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

    # Try different browsers
    browsers = ['chrome', 'edge', 'firefox', 'brave', 'opera', 'chromium']

    for browser in browsers:
        print(f"\n[🔍] Trying {browser}...")
        try:
            # Close browser first for cookie access
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp",
                 "--cookies-from-browser", browser,
                 "--skip-download",
                 "--cookies", cookies_file,
                 "https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                capture_output=True, text=True, timeout=30
            )
            if os.path.exists(cookies_file) and os.path.getsize(cookies_file) > 100:
                print(f"[✅] Cookies exported from {browser}!")
                print(f"[📁] File: {cookies_file}")
                print(f"[📏] Size: {os.path.getsize(cookies_file)} bytes")
                print()
                print("=" * 60)
                print("✅ DONE! Now run these commands:")
                print("   git add cookies.txt")
                print("   git commit -m 'Add YouTube cookies'")
                print("   git push origin main")
                print("   Then redeploy on Render!")
                print("=" * 60)
                return True
            else:
                print(f"[❌] {browser} - cookies file empty or missing")
        except subprocess.TimeoutExpired:
            print(f"[⏱️] {browser} - timeout")
        except Exception as e:
            print(f"[❌] {browser} - {e}")

    # Manual method fallback
    print()
    print("=" * 60)
    print("❌ Automatic export failed!")
    print()
    print("🔧 MANUAL METHOD:")
    print("1. Install this Chrome/Edge extension:")
    print("   https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
    print()
    print("2. Go to https://www.youtube.com (make sure you're logged in)")
    print()
    print("3. Click the extension icon → 'Export' → save as 'cookies.txt'")
    print()
    print(f"4. Put cookies.txt in: {os.path.dirname(os.path.abspath(__file__))}")
    print()
    print("5. Then run:")
    print("   git add cookies.txt")
    print("   git commit -m 'Add YouTube cookies'")
    print("   git push origin main")
    print("=" * 60)
    return False


if __name__ == "__main__":
    export_cookies()
