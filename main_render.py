import asyncio
import os
import sys
import threading
import http.server
import socketserver
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. Background Web Server for Render Health Check & Dashboard
# ==============================================================================
PORT = int(os.environ.get("PORT", 8000))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Minimal logging
        pass

def run_web_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[+] Render Web Server is listening on port {PORT}")
        httpd.serve_forever()

# Start web server in a background daemon thread
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# ==============================================================================
# 2. Main Discord Bot Runner
# ==============================================================================
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    help_command=None
)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"[+] XON Music Bot ONLINE on Render: {bot.user.name} (ID: {bot.user.id})")
    print(f"[+] Connected Servers: {len(bot.guilds)}")
    
    try:
        synced = await bot.tree.sync()
        print(f"[+] Synced {len(synced)} Slash Commands successfully.")
    except Exception as e:
        print(f"[-] Slash commands sync error: {e}")
        
    print("=" * 50)
    
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"/play & {PREFIX}play | xonmusic.onrender.com"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)

async def main():
    async with bot:
        try:
            await bot.load_extension("cogs.music")
            print("[+] Cog 'cogs.music' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.music: {e}")

        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("[-] DISCORD_TOKEN is missing in Render Environment Variables!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot stopped.")
