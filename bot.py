import asyncio
import os
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
        name=f"/play & !play | {PREFIX}musichelp"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for prefix commands."""
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"⚠️ Argument missing hai! Sahi format ke liye `{PREFIX}musichelp` dekhein.")

    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Thoda wait karein ({error.retry_after:.1f}s remaining).")

    if isinstance(error, commands.CheckFailure):
        return

    print(f"[Command Error in {ctx.command}]: {error}")


async def main():
    async with bot:
        # Load the music cog
        try:
            await bot.load_extension("cogs.music")
            print("[+] Cog 'cogs.music' successfully loaded.")
        except Exception as e:
            print(f"[-] Failed to load cogs.music: {e}")

        if TOKEN and TOKEN != "YOUR_DISCORD_BOT_TOKEN_HERE":
            try:
                await bot.start(TOKEN)
            except discord.errors.PrivilegedIntentsRequired:
                print("=" * 65)
                print("⚠️ [ACTION REQUIRED] Discord Developer Portal Settings:")
                print("Bot ko commands read karne ke liye Privileged Intents enable karni hogi:")
                print("1. https://discord.com/developers/applications par jaayein")
                print("2. Apne Bot par click karein -> Left menu se 'Bot' tab kholein")
                print("3. Neeche scroll karke 'Privileged Gateway Intents' me:")
                print("   [x] Message Content Intent  <-- (Isko ENABLE karein)")
                print("   [x] Server Members Intent")
                print("4. 'Save Changes' par click karein aur bot dobara run karein!")
                print("=" * 65)
            except discord.errors.LoginFailure:
                print("❌ Invalid Bot Token! Kripya .env me sahi token dalein.")
            except Exception as e:
                print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot stop ho gaya.")
