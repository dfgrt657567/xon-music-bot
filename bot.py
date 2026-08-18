import asyncio
import os
import site
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load libopus for crystal-clear Discord voice encoding
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
                for dll_name in ['libopus-0.x64.dll', 'opus.dll']:
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
    print(f"[+] Opus Audio Loaded: {discord.opus.is_loaded()}")

init_opus()

# Load environment variables from .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
    print("=" * 60)
    print("[-] ERROR: DISCORD_TOKEN nahi mila!")
    print("Kripya '.env' file me apna Discord Bot Token paste karein.")
    print("=" * 60)

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True  # Required for !play
intents.voice_states = True     # Required for voice channels
intents.guilds = True

# Initialize bot instance
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print("=" * 50)
    print(f"[+] Bot Online: {bot.user.name} (ID: {bot.user.id})")
    print(f"[+] Connected Servers: {len(bot.guilds)}")
    print(f"[+] Command Prefix: '{PREFIX}'")
    
    # Sync Slash Commands with Discord Global Tree
    try:
        synced = await bot.tree.sync()
        print(f"[+] Synced {len(synced)} Slash Commands (/play, /pause, /skip, etc.)")
    except Exception as e:
        print(f"[-] Error syncing slash commands: {e}")

    print("=" * 50)

    # Set bot status/activity
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"/play & {PREFIX}play | XON Music"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands silently
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Kripya pura command likhein. Jaise: `{PREFIX}play <song-name>`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Thoda wait karein ({error.retry_after:.1f}s bache hain).")
    else:
        print(f"[-] Command Error ({ctx.command}): {error}")


async def main():
    async with bot:
        # Load the music cog
        try:
            await bot.load_extension("cogs.music")
            print("[+] Cog 'cogs.music' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.music: {e}")

        # Start the bot
        if TOKEN:
            await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot band kar diya gaya. Goodbye!")
