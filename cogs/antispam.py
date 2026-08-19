import asyncio
import json
import os
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

# Config file path
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'antispam_config.json')

def load_config() -> dict:
    """Load antispam config from JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"channels": {}}  # {channel_id: {enabled, threshold, window, timeout_secs}}

def save_config(cfg: dict):
    """Save antispam config to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def default_channel_config():
    return {
        "enabled": True,
        "threshold": 5,       # messages
        "window": 5,          # seconds
        "timeout_secs": 30    # timeout duration
    }


class AntiSpam(commands.Cog):
    """Anti-Spam System — Auto timeout spammers"""

    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        # Track: {guild_id: {channel_id: {user_id: deque([timestamps])}}}
        self.message_tracker = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
        # Track who's already timed out to avoid duplicate actions
        self.timed_out_users = set()  # {(guild_id, user_id)}

    def reload_config(self):
        self.config = load_config()

    def is_spam(self, guild_id: int, channel_id: int, user_id: int) -> bool:
        """Check if user is spamming based on config thresholds."""
        ch_cfg = self.config.get("channels", {}).get(str(channel_id))
        if not ch_cfg or not ch_cfg.get("enabled", False):
            return False

        threshold = ch_cfg.get("threshold", 5)
        window    = ch_cfg.get("window", 5)

        now = time.time()
        msgs = self.message_tracker[guild_id][channel_id][user_id]

        # Add current timestamp
        msgs.append(now)

        # Remove old timestamps outside the window
        while msgs and msgs[0] < now - window:
            msgs.popleft()

        return len(msgs) >= threshold

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        # Skip admins
        if message.author.guild_permissions.administrator:
            return

        guild_id   = message.guild.id
        channel_id = message.channel.id
        user_id    = message.author.id
        key        = (guild_id, user_id)

        ch_cfg = self.config.get("channels", {}).get(str(channel_id))
        if not ch_cfg or not ch_cfg.get("enabled", False):
            return

        if self.is_spam(guild_id, channel_id, user_id):
            if key not in self.timed_out_users:
                self.timed_out_users.add(key)
                timeout_secs = ch_cfg.get("timeout_secs", 30)
                await self._apply_timeout(message, timeout_secs)
                # Release after timeout
                await asyncio.sleep(timeout_secs + 5)
                self.timed_out_users.discard(key)
                # Clear tracker
                self.message_tracker[guild_id][channel_id].pop(user_id, None)

    async def _apply_timeout(self, message: discord.Message, secs: int):
        member = message.author
        try:
            duration = discord.utils.utcnow() + __import__('datetime').timedelta(seconds=secs)
            await member.timeout(duration, reason=f"[XON Anti-Spam] Spam detected in #{message.channel.name}")

            embed = discord.Embed(
                title="🚨 Anti-Spam Action",
                description=f"{member.mention} ko **{secs} seconds** ka timeout diya gaya!\n**Reason:** Spam detected in <#{message.channel.id}>",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 User", value=f"`{member.name}`", inline=True)
            embed.add_field(name="⏱️ Timeout", value=f"`{secs} seconds`", inline=True)
            embed.add_field(name="📢 Channel", value=f"<#{message.channel.id}>", inline=True)
            embed.set_footer(text="XON Anti-Spam System • Auto-moderation")

            warn = await message.channel.send(embed=embed)
            await asyncio.sleep(10)
            try:
                await warn.delete()
            except Exception:
                pass

        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"[AntiSpam] Timeout error: {e}")

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="antispam", description="Channel mein anti-spam on/off karein (Admin only)")
    @app_commands.describe(
        channel="Channel select karein",
        enabled="On ya Off karein",
        threshold="Kitne messages spam count honge (default: 5)",
        window="Kitne seconds mein (default: 5)",
        timeout="Timeout duration seconds mein (default: 30)"
    )
    @app_commands.default_permissions(administrator=True)
    async def antispam_cmd(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        enabled: bool,
        threshold: int = 5,
        window: int = 5,
        timeout: int = 30
    ):
        if "channels" not in self.config:
            self.config["channels"] = {}

        self.config["channels"][str(channel.id)] = {
            "enabled": enabled,
            "threshold": max(2, min(threshold, 20)),
            "window": max(2, min(window, 30)),
            "timeout_secs": max(10, min(timeout, 3600))
        }
        save_config(self.config)

        status = "✅ **ENABLED**" if enabled else "❌ **DISABLED**"
        embed = discord.Embed(
            title="🛡️ Anti-Spam Config Updated",
            description=f"**#{channel.name}** mein Anti-Spam: {status}",
            color=discord.Color.green() if enabled else discord.Color.gray()
        )
        embed.add_field(name="💬 Threshold", value=f"`{threshold} messages`", inline=True)
        embed.add_field(name="⏱️ Window", value=f"`{window} seconds`", inline=True)
        embed.add_field(name="🔇 Timeout", value=f"`{timeout} seconds`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="antispamlist", description="Anti-spam configured channels list (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def antispam_list(self, interaction: discord.Interaction):
        channels = self.config.get("channels", {})
        if not channels:
            return await interaction.response.send_message("❌ Koi channel configure nahi hai.", ephemeral=True)

        embed = discord.Embed(title="🛡️ Anti-Spam Configuration", color=0x8B5CF6)
        for ch_id, cfg in channels.items():
            ch = self.bot.get_channel(int(ch_id))
            ch_name = f"#{ch.name}" if ch else f"#unknown({ch_id})"
            status = "✅ ON" if cfg.get("enabled") else "❌ OFF"
            embed.add_field(
                name=f"{ch_name} — {status}",
                value=f"Threshold: `{cfg.get('threshold',5)} msgs` | Window: `{cfg.get('window',5)}s` | Timeout: `{cfg.get('timeout_secs',30)}s`",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
