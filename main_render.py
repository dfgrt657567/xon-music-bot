import asyncio
import json
import os
import site
import sys
import threading
import http.server
import socketserver
import urllib.request
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. Background Web Server — Static Files + Admin API Routes
# ==============================================================================
PORT = int(os.environ.get("PORT", 8000))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
XON_GUILD_ID = os.environ.get("XON_GUILD_ID", "")

# Shared bot reference (set after bot boots)
bot_instance = None


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress access logs

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_preflight(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _verify_discord_admin(self, access_token):
        """Verify user is admin/owner of XON guild via Discord API."""
        if not access_token or not XON_GUILD_ID:
            return False, None
        try:
            # Get user guilds
            req = urllib.request.Request(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}", "User-Agent": "XONBot/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                guilds = json.loads(res.read().decode("utf-8"))

            # Get user info
            req2 = urllib.request.Request(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}", "User-Agent": "XONBot/2.0"}
            )
            with urllib.request.urlopen(req2, timeout=5) as res2:
                user = json.loads(res2.read().decode("utf-8"))

            for g in guilds:
                if str(g["id"]) == str(XON_GUILD_ID):
                    perms = int(g.get("permissions", 0))
                    is_owner = g.get("owner", False)
                    is_admin = (perms & 0x8) == 0x8  # ADMINISTRATOR bit
                    is_manage = (perms & 0x20) == 0x20  # MANAGE_GUILD bit
                    if is_owner or is_admin or is_manage:
                        return True, user
            return False, user
        except Exception as e:
            print(f"[!] Admin verify error: {e}")
            return False, None

    def do_OPTIONS(self):
        self._send_cors_preflight()

    def do_GET(self):
        # ── API: Guild Info ──────────────────────────────────────────────
        if self.path == "/api/guild":
            if not bot_instance or not XON_GUILD_ID:
                return self._send_json({"error": "Bot not ready or guild not configured"}, 503)
            guild = bot_instance.get_guild(int(XON_GUILD_ID))
            if not guild:
                return self._send_json({"error": "Guild not found"}, 404)
            icon = f"https://cdn.discordapp.com/icons/{guild.id}/{guild.icon}.png" if guild.icon else None
            return self._send_json({
                "id": str(guild.id),
                "name": guild.name,
                "icon": icon,
                "member_count": guild.member_count,
                "owner_id": str(guild.owner_id)
            })

        # ── API: Channels List ──────────────────────────────────────────
        if self.path == "/api/channels":
            auth = self.headers.get("Authorization", "").replace("Bearer ", "")
            is_admin, user = self._verify_discord_admin(auth)
            if not is_admin:
                return self._send_json({"error": "Access denied. XON server Admin/Owner required."}, 403)
            if not bot_instance or not XON_GUILD_ID:
                return self._send_json({"error": "Bot not ready"}, 503)
            guild = bot_instance.get_guild(int(XON_GUILD_ID))
            if not guild:
                return self._send_json({"error": "Guild not found"}, 404)
            channels = []
            for cat in guild.categories:
                cat_channels = []
                for ch in cat.text_channels:
                    cat_channels.append({"id": str(ch.id), "name": ch.name, "position": ch.position})
                if cat_channels:
                    channels.append({"category": cat.name, "channels": sorted(cat_channels, key=lambda x: x["position"])})
            # Uncategorized channels
            uncategorized = [
                {"id": str(ch.id), "name": ch.name, "position": ch.position}
                for ch in guild.text_channels if ch.category is None
            ]
            if uncategorized:
                channels.insert(0, {"category": "General", "channels": sorted(uncategorized, key=lambda x: x["position"])})
            return self._send_json({"channels": channels, "user": {"id": user["id"], "username": user.get("global_name") or user["username"]}})

        # ── API: AntiSpam Config (GET) ────────────────────────────────
        if self.path == "/api/antispam/config":
            auth = self.headers.get("Authorization", "").replace("Bearer ", "")
            is_admin, _ = self._verify_discord_admin(auth)
            if not is_admin:
                return self._send_json({"error": "Access denied."}, 403)
            import json as _json
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antispam_config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    return self._send_json(_json.load(f))
            return self._send_json({"channels": {}})

        # Serve static files
        super().do_GET()

    def do_POST(self):
        # ── API: Clear Messages ──────────────────────────────────────────
        if self.path == "/api/clear":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                channel_id = body.get("channel_id")
                amount = min(int(body.get("amount", 10)), 500)
                auth = self.headers.get("Authorization", "").replace("Bearer ", "")

                is_admin, user = self._verify_discord_admin(auth)
                if not is_admin:
                    return self._send_json({"error": "Access denied."}, 403)

                if not bot_instance or not channel_id:
                    return self._send_json({"error": "Bot not ready or missing channel_id"}, 400)

                channel = bot_instance.get_channel(int(channel_id))
                if not channel:
                    return self._send_json({"error": "Channel not found"}, 404)

                # Run purge in the bot's event loop
                future = asyncio.run_coroutine_threadsafe(
                    channel.purge(limit=amount),
                    bot_instance.loop
                )
                deleted = future.result(timeout=30)
                uname = user.get("global_name") or user.get("username", "Unknown")
                print(f"[🗑️] {uname} cleared {len(deleted)} msgs from #{channel.name} via web dashboard")
                return self._send_json({"success": True, "deleted": len(deleted), "channel": channel.name})

            except Exception as e:
                print(f"[!] Clear API error: {e}")
                return self._send_json({"error": str(e)}, 500)

        # ── API: AntiSpam Config (POST) ──────────────────────────────────
        if self.path == "/api/antispam/config":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                auth = self.headers.get("Authorization", "").replace("Bearer ", "")
                is_admin, _ = self._verify_discord_admin(auth)
                if not is_admin:
                    return self._send_json({"error": "Access denied."}, 403)

                ch_id       = str(body.get("channel_id", ""))
                enabled     = bool(body.get("enabled", True))
                threshold   = max(2, min(int(body.get("threshold", 5)), 20))
                window_s    = max(2, min(int(body.get("window", 5)), 30))
                timeout_s   = max(10, min(int(body.get("timeout_secs", 30)), 3600))

                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antispam_config.json")
                cfg = {"channels": {}}
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r") as f:
                        cfg = json.load(f)

                cfg["channels"][ch_id] = {
                    "enabled": enabled,
                    "threshold": threshold,
                    "window": window_s,
                    "timeout_secs": timeout_s
                }
                with open(cfg_path, "w") as f:
                    json.dump(cfg, f, indent=2)

                # Reload cog config if bot is running
                if bot_instance:
                    cog = bot_instance.cogs.get("AntiSpam")
                    if cog:
                        cog.reload_config()

                ch_name = "unknown"
                if bot_instance:
                    ch = bot_instance.get_channel(int(ch_id))
                    if ch: ch_name = ch.name

                return self._send_json({"success": True, "channel_name": ch_name})
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        self.send_response(404)
        self.end_headers()

def run_web_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[+] Render Web Server is listening on port {PORT}")
        httpd.serve_forever()

web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# ==============================================================================
# 2. Main Discord Bot Runner
# ==============================================================================
import discord
from discord.ext import commands

def init_opus():
    if not discord.opus.is_loaded():
        try:
            discord.opus._load_default()
        except Exception:
            pass
        if not discord.opus.is_loaded():
            candidates = []
            try:
                candidates.extend(site.getsitepackages())
            except Exception:
                pass
            local_app = os.environ.get('LOCALAPPDATA', '')
            if local_app:
                candidates.append(os.path.join(local_app, 'Packages', 'PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0', 'LocalCache', 'local-packages', 'Python313', 'site-packages'))
            for sp in candidates:
                for dll_name in ['libopus-0.x64.dll', 'opus.dll', 'libopus.so.0', 'libopus.so']:
                    dll_path = os.path.join(sp, 'discord', 'bin', dll_name)
                    if os.path.exists(dll_path):
                        try:
                            discord.opus.load_opus(dll_path)
                            print(f"[+] Loaded Opus DLL: {dll_path}")
                            break
                        except Exception:
                            pass
                if discord.opus.is_loaded():
                    break
    print(f"[+] Opus Audio Loaded on Render: {discord.opus.is_loaded()}")

init_opus()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True  # Required for on_member_join (Welcome system)

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    help_command=None
)

@bot.event
async def on_ready():
    global bot_instance
    bot_instance = bot  # Expose bot to web API handler

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

    bot.loop.create_task(anti_sleep_keepalive())

async def anti_sleep_keepalive():
    await bot.wait_until_ready()
    import urllib.request
    render_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://xon-music-bot.onrender.com"
    print(f"[+] Anti-Sleep 24/7 Keep-Alive active: Pinging {render_url} every 8 minutes...")
    while not bot.is_closed():
        await asyncio.sleep(480) # 8 minutes
        try:
            req = urllib.request.Request(render_url, headers={'User-Agent': 'XONMusic-AntiSleep-KeepAlive/2.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                print(f"[+] Anti-Sleep Heartbeat: HTTP {res.status} OK (Bot Kept Awake 24/7)")
        except Exception as e:
            print(f"[!] Anti-Sleep ping failed: {e}")

async def main():
    async with bot:
        try:
            await bot.load_extension("cogs.music")
            print("[+] Cog 'cogs.music' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.music: {e}")

        try:
            await bot.load_extension("cogs.moderation")
            print("[+] Cog 'cogs.moderation' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.moderation: {e}")

        try:
            await bot.load_extension("cogs.welcome")
            print("[+] Cog 'cogs.welcome' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.welcome: {e}")

        try:
            await bot.load_extension("cogs.antispam")
            print("[+] Cog 'cogs.antispam' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.antispam: {e}")

        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("[-] DISCORD_TOKEN is missing in Render Environment Variables!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot stopped.")
