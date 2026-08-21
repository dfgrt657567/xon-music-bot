import asyncio
import json
import os
import re
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

# Config file path
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'antispam_config.json')

# URL detection regex
URL_PATTERN = re.compile(
    r'(https?://[^\s<>]+|www\.[^\s<>]+|[a-zA-Z0-9-]+\.(com|net|org|io|gg|xyz|co|me|tv|dev|app|in|info|store|pro|live|online|cc|ru|tk|ml|ga|cf|gq|link|click|top|site|space|fun|club|buzz|tech|vip|ws|biz|ly|bit\.ly|t\.co|discord\.gg|youtu\.be|tinyurl\.com)[/\w\-._~:/?#\[\]@!$&\'()*+,;=%]*)',
    re.IGNORECASE
)

# Discord invite pattern
INVITE_PATTERN = re.compile(
    r'(discord\.gg/[^\s]+|discord\.com/invite/[^\s]+|discordapp\.com/invite/[^\s]+)',
    re.IGNORECASE
)


def load_config() -> dict:
    """Load antispam config from JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"channels": {}, "automod": {}}


def save_config(cfg: dict):
    """Save antispam config to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


class AntiSpam(commands.Cog):
    """Anti-Spam + Auto-Mod System"""

    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.message_tracker = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
        self.timed_out_users = set()

    def reload_config(self):
        self.config = load_config()

    def is_spam(self, guild_id: int, channel_id: int, user_id: int) -> bool:
        ch_cfg = self.config.get("channels", {}).get(str(channel_id))
        if not ch_cfg or not ch_cfg.get("enabled", False):
            return False
        threshold = ch_cfg.get("threshold", 5)
        window = ch_cfg.get("window", 5)
        now = time.time()
        msgs = self.message_tracker[guild_id][channel_id][user_id]
        msgs.append(now)
        while msgs and msgs[0] < now - window:
            msgs.popleft()
        return len(msgs) >= threshold

    def _check_automod(self, message: discord.Message) -> str | None:
        """Check if message violates automod rules. Returns violation type or None."""
        guild_id = str(message.guild.id)
        automod = self.config.get("automod", {}).get(guild_id, {})

        if not automod.get("enabled", False):
            return None

        # Check whitelisted channels
        whitelist = automod.get("whitelist_channels", [])
        if str(message.channel.id) in whitelist:
            return None

        # Check links
        if automod.get("block_links", False):
            if URL_PATTERN.search(message.content):
                return "link"
            if INVITE_PATTERN.search(message.content):
                return "invite"

        # Check images/attachments
        if automod.get("block_images", False):
            if message.attachments:
                for att in message.attachments:
                    if att.content_type and ("image" in att.content_type or "video" in att.content_type or "gif" in att.content_type):
                        return "image"
            # Check embeds with images
            if message.embeds:
                for e in message.embeds:
                    if e.image or e.thumbnail:
                        return "image"

        # Check Discord invites specifically
        if automod.get("block_invites", False):
            if INVITE_PATTERN.search(message.content):
                return "invite"

        return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        # Skip admins
        if message.author.guild_permissions.administrator:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id
        user_id = message.author.id
        key = (guild_id, user_id)

        # ── Auto-Mod: Link / Image / Invite Blocking ────────────────────
        violation = self._check_automod(message)
        if violation:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            except Exception:
                pass

            violation_msgs = {
                "link": "🔗 **Links/URLs** bhejne ki permission nahi hai!",
                "image": "🖼️ **Images/Videos** bhejne ki permission nahi hai!",
                "invite": "🚫 **Discord invite links** bhejne ki permission nahi hai!"
            }
            embed = discord.Embed(
                description=f"{message.author.mention} — {violation_msgs.get(violation, 'Not allowed!')}",
                color=discord.Color.orange()
            )
            embed.set_footer(text="XON Auto-Mod • Admin se permission lein")
            try:
                warn = await message.channel.send(embed=embed)
                await asyncio.sleep(5)
                await warn.delete()
            except Exception:
                pass
            return  # Don't process further

        # ── Anti-Spam Check ──────────────────────────────────────────────
        ch_cfg = self.config.get("channels", {}).get(str(channel_id))
        if not ch_cfg or not ch_cfg.get("enabled", False):
            return

        if self.is_spam(guild_id, channel_id, user_id):
            if key not in self.timed_out_users:
                self.timed_out_users.add(key)
                timeout_secs = ch_cfg.get("timeout_secs", 30)
                await self._apply_timeout(message, timeout_secs)
                await asyncio.sleep(timeout_secs + 5)
                self.timed_out_users.discard(key)
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

    # ══════════════════════════════════════════════════════════════════════
    # Slash Commands
    # ══════════════════════════════════════════════════════════════════════

    # ── /antispam ─────────────────────────────────────────────────────────
    @app_commands.command(name="antispam", description="Channel mein anti-spam on/off karein (Admin only)")
    @app_commands.describe(
        channel="Channel select karein",
        enabled="On ya Off karein",
        threshold="Kitne messages spam count honge (default: 5)",
        window="Kitne seconds mein (default: 5)",
        timeout="Timeout duration seconds mein (default: 30)"
    )
    @app_commands.default_permissions(administrator=True)
    async def antispam_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel,
                           enabled: bool, threshold: int = 5, window: int = 5, timeout: int = 30):
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

    # ── /automod — Link/Image/Invite blocking ────────────────────────────
    @app_commands.command(name="automod", description="Auto-Mod: Links, images, invites block karein (Admin only)")
    @app_commands.describe(
        enabled="Auto-Mod on/off karein",
        block_links="URLs/Links block karein",
        block_images="Images/Videos block karein",
        block_invites="Discord invite links block karein"
    )
    @app_commands.default_permissions(administrator=True)
    async def automod_cmd(self, interaction: discord.Interaction,
                          enabled: bool,
                          block_links: bool = True,
                          block_images: bool = True,
                          block_invites: bool = True):
        guild_id = str(interaction.guild.id)
        if "automod" not in self.config:
            self.config["automod"] = {}

        existing = self.config["automod"].get(guild_id, {})
        existing_whitelist = existing.get("whitelist_channels", [])

        self.config["automod"][guild_id] = {
            "enabled": enabled,
            "block_links": block_links,
            "block_images": block_images,
            "block_invites": block_invites,
            "whitelist_channels": existing_whitelist
        }
        save_config(self.config)

        status = "✅ **ENABLED**" if enabled else "❌ **DISABLED**"
        embed = discord.Embed(
            title="🛡️ Auto-Mod Config Updated",
            description=f"Server Auto-Mod: {status}",
            color=discord.Color.green() if enabled else discord.Color.gray()
        )
        embed.add_field(name="🔗 Block Links", value="✅ Yes" if block_links else "❌ No", inline=True)
        embed.add_field(name="🖼️ Block Images", value="✅ Yes" if block_images else "❌ No", inline=True)
        embed.add_field(name="🚫 Block Invites", value="✅ Yes" if block_invites else "❌ No", inline=True)

        if existing_whitelist:
            wl_text = ", ".join([f"<#{c}>" for c in existing_whitelist])
            embed.add_field(name="✅ Whitelisted Channels", value=wl_text, inline=False)
        else:
            embed.add_field(name="ℹ️ Note", value="Koi channel whitelist nahi hai — sab channels pe active.\n`/automod_whitelist` se channels add karein jahan links allowed hain.", inline=False)

        embed.set_footer(text="⚠️ Admins are always exempt")
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ── /automod_whitelist — Allow certain channels ──────────────────────
    @app_commands.command(name="automod_whitelist", description="Channel ko automod se exempt karein (Admin only)")
    @app_commands.describe(
        channel="Channel jahan links/images allowed hain",
        action="Add ya Remove karein"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add (allow links)", value="add"),
        app_commands.Choice(name="Remove (block links)", value="remove")
    ])
    @app_commands.default_permissions(administrator=True)
    async def automod_whitelist_cmd(self, interaction: discord.Interaction,
                                     channel: discord.TextChannel,
                                     action: app_commands.Choice[str]):
        guild_id = str(interaction.guild.id)
        if "automod" not in self.config:
            self.config["automod"] = {}
        if guild_id not in self.config["automod"]:
            self.config["automod"][guild_id] = {"enabled": False, "block_links": True, "block_images": True, "block_invites": True, "whitelist_channels": []}

        wl = self.config["automod"][guild_id].get("whitelist_channels", [])
        ch_id = str(channel.id)

        if action.value == "add":
            if ch_id not in wl:
                wl.append(ch_id)
            msg = f"✅ **#{channel.name}** whitelist mein add kiya — links/images allowed!"
            color = discord.Color.green()
        else:
            if ch_id in wl:
                wl.remove(ch_id)
            msg = f"❌ **#{channel.name}** whitelist se hata diya — links/images blocked!"
            color = discord.Color.red()

        self.config["automod"][guild_id]["whitelist_channels"] = wl
        save_config(self.config)

        embed = discord.Embed(description=msg, color=color)
        if wl:
            embed.add_field(name="📋 Current Whitelist", value=", ".join([f"<#{c}>" for c in wl]))
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ── /automod_status — Check current config ───────────────────────────
    @app_commands.command(name="automod_status", description="Auto-Mod ki current status check karein (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def automod_status_cmd(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        automod = self.config.get("automod", {}).get(guild_id)

        if not automod:
            return await interaction.response.send_message(
                "❌ Auto-Mod configure nahi hai. `/automod` command se enable karein.",
                ephemeral=True
            )

        status = "✅ ON" if automod.get("enabled") else "❌ OFF"
        embed = discord.Embed(
            title=f"🛡️ Auto-Mod Status — {status}",
            color=0x8B5CF6 if automod.get("enabled") else 0x6B7280
        )
        embed.add_field(name="🔗 Block Links", value="✅" if automod.get("block_links") else "❌", inline=True)
        embed.add_field(name="🖼️ Block Images", value="✅" if automod.get("block_images") else "❌", inline=True)
        embed.add_field(name="🚫 Block Invites", value="✅" if automod.get("block_invites") else "❌", inline=True)

        wl = automod.get("whitelist_channels", [])
        if wl:
            embed.add_field(name="✅ Whitelisted Channels", value=", ".join([f"<#{c}>" for c in wl]), inline=False)
        else:
            embed.add_field(name="ℹ️ Whitelist", value="Koi channel exempt nahi hai", inline=False)

        embed.set_footer(text="Admins are always exempt • /automod to configure")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
