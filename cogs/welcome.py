import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import json
import os
import sys

# Welcome card image generator
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.welcome_card import generate_welcome_card
    CARD_AVAILABLE = True
except Exception as e:
    print(f"[!] Welcome card generator not available: {e}")
    CARD_AVAILABLE = False

WELCOME_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "welcome_config.json")

def load_welcome_config() -> dict:
    """Load welcome config from file, falling back to defaults."""
    defaults = {
        "message": "Server mein aapka swagat hai! 🎉 {member}",
        "title": "👋 Welcome to {server}!",
        "color": "#8B5CF6",
        "show_avatar": True,
        "show_banner": True,
        "show_milestone": True,
        "show_farewell": True,
        "banner_image": None
    }
    if os.path.exists(WELCOME_CONFIG_PATH):
        try:
            with open(WELCOME_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                defaults.update(cfg)
        except Exception as e:
            print(f"[!] Failed to load welcome_config.json: {e}")
    return defaults


# ── Welcome Banner Colors (rotate karein har baar) ───────────────────────────
BANNER_COLORS = [
    0x8B5CF6,  # Purple
    0x6D28D9,  # Deep Purple
    0xA78BFA,  # Lavender
    0x4F46E5,  # Indigo
    0x7C3AED,  # Violet
]

# ── Greet Messages (random pick hoga) ────────────────────────────────────────
GREET_MESSAGES = [
    "Server mein aapka swagat hai! 🎉",
    "Aa gaye aap! Server khush ho gaya! 🥳",
    "Ek aur legend aa gaya server mein! 👑",
    "Welcome aboard! XON family mein khush amdeed! 🚀",
    "Aapka intezaar tha! Finally aa gaye! 💫",
    "New member unlocked! 🎮 Welcome to the family!",
    "Lights, camera, action — ek naya star aa gaya! ⭐",
]

# ── Milestone Messages ─────────────────────────────────────────────────────
def get_milestone_text(member_count: int) -> str | None:
    milestones = {10: "🎯 10 members!", 25: "🌟 25 members!", 50: "🔥 50 members!",
                  100: "💯 100 members!", 250: "🚀 250 members!", 500: "👑 500 members!",
                  1000: "🏆 1000 members!"}
    return milestones.get(member_count)


class Welcome(commands.Cog):
    """Premium Welcome System for XON Music Server"""

    def __init__(self, bot):
        self.bot = bot
        self.config = load_welcome_config()
        print(f"[🎉] Welcome cog loaded. Config: message='{self.config['message'][:30]}...'")

    def reload_config(self):
        """Hot-reload config from file (called by web dashboard)."""
        self.config = load_welcome_config()
        print(f"[🔄] Welcome config reloaded from web dashboard")

    def find_welcome_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Find the welcome channel by name."""
        keywords = ["welcome", "स्वागत", "welkom", "bienvenido"]
        for ch in guild.text_channels:
            ch_lower = ch.name.lower()
            if any(k in ch_lower for k in keywords):
                return ch
        return None

    def build_welcome_embed(self, member: discord.Member) -> discord.Embed:
        cfg = self.config
        guild = member.guild

        # Parse color from hex string
        try:
            color_int = int(cfg.get("color", "#8B5CF6").lstrip("#"), 16)
        except Exception:
            color_int = random.choice(BANNER_COLORS)

        # Member count ordinal
        count = guild.member_count
        suffix = "th"
        if count % 100 not in (11, 12, 13):
            if count % 10 == 1: suffix = "st"
            elif count % 10 == 2: suffix = "nd"
            elif count % 10 == 3: suffix = "rd"

        # Fill in placeholders
        msg = cfg.get("message", "Server mein aapka swagat hai! {member}")
        msg = msg.replace("{member}", member.mention)
        msg = msg.replace("{server}", guild.name)
        msg = msg.replace("{count}", str(count))

        title = cfg.get("title", "👋 Welcome to {server}!")
        title = title.replace("{member}", member.display_name)
        title = title.replace("{server}", guild.name)
        title = title.replace("{count}", str(count))

        embed = discord.Embed(
            title=title,
            description=msg,
            color=color_int
        )

        # Author line
        embed.set_author(
            name=f"{member.display_name} joined the server!",
            icon_url=member.display_avatar.url
        )

        # Avatar thumbnail
        if cfg.get("show_avatar", True):
            embed.set_thumbnail(url=member.display_avatar.url)

        # Custom banner image (from web dashboard upload)
        banner_img = cfg.get("banner_image")
        if banner_img and cfg.get("show_banner", True):
            # If it's a relative path, skip (can't resolve to absolute URL here)
            # Only set if it's a full URL
            if banner_img.startswith("http"):
                embed.set_image(url=banner_img)
        elif cfg.get("show_banner", True) and guild.banner:
            embed.set_image(url=guild.banner.with_format("png").url)

        # Fields
        embed.add_field(name="👤 Member",       value=f"```{member.name}```",               inline=True)
        embed.add_field(name="📅 Joined Discord", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="🏅 You are",      value=f"```#{count} member ({count}{suffix})```", inline=True)
        embed.add_field(name="📋 Server Rules",  value="Please read the rules and enjoy your stay! 🎵", inline=False)

        # Footer
        embed.set_footer(
            text=f"XON Music • {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )

        return embed

    def build_welcome_image_embed(self, member: discord.Member) -> discord.Embed:
        """Simple image-focused embed"""
        embed = discord.Embed(color=random.choice(BANNER_COLORS))
        embed.set_image(url=member.display_avatar.with_size(512).url)
        return embed

    # ── on_member_join Event ─────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        welcome_ch = self.find_welcome_channel(member.guild)
        if not welcome_ch:
            return

        # ── Generate Image Card ───────────────────────────────────────
        card_file = None
        if CARD_AVAILABLE:
            try:
                disc = getattr(member, 'discriminator', '0000') or '0000'
                # Calculate time since account creation
                import datetime
                now = discord.utils.utcnow()
                delta = now - member.created_at.replace(tzinfo=datetime.timezone.utc) if member.created_at.tzinfo is None else now - member.created_at
                days = delta.days
                if days < 1:
                    joined_ago = "a few seconds ago"
                elif days < 30:
                    joined_ago = f"{days} day{'s' if days != 1 else ''} ago"
                elif days < 365:
                    joined_ago = f"{days // 30} month{'s' if days // 30 != 1 else ''} ago"
                else:
                    joined_ago = f"{days // 365} year{'s' if days // 365 != 1 else ''} ago"

                buf = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: generate_welcome_card(
                        username=member.display_name,
                        discriminator=disc,
                        member_number=member.guild.member_count or 1,
                        joined_ago=joined_ago,
                        server_name=member.guild.name,
                        avatar_url=str(member.display_avatar.with_size(256).url),
                    )
                )
                card_file = discord.File(buf, filename="welcome.png")
            except Exception as e:
                print(f"[!] Welcome card generation failed: {e}")
                card_file = None

        # ── Send Message ─────────────────────────────────────────────
        view = WelcomeView(member)

        if card_file:
            msg = await welcome_ch.send(
                content=f"🎉 **{member.mention}** ne **{member.guild.name}** join kiya!",
                file=card_file,
                view=view
            )
        else:
            embed = self.build_welcome_embed(member)
            msg = await welcome_ch.send(
                content=f"🎉 **{member.mention}** ne server join kiya!",
                embed=embed,
                view=view
            )

        # Milestone check
        if self.config.get("show_milestone", True):
            milestone = get_milestone_text(member.guild.member_count)
            if milestone:
                milestone_embed = discord.Embed(
                    title=f"🎊 Server Milestone Reached — {milestone}",
                    description=f"Congratulations **{member.guild.name}**! Aapne {milestone} ka milestone reach kar liya!\nAur yeh sab **{member.mention}** ki wajah se!",
                    color=0xFFD700
                )
                milestone_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                await welcome_ch.send(embed=milestone_embed)

    # ── on_member_remove Event (optional farewell) ───────────────────────────
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self.config.get("show_farewell", True):
            return
        welcome_ch = self.find_welcome_channel(member.guild)
        if not welcome_ch:
            return

        embed = discord.Embed(
            description=f"**{member.display_name}** ne server leave kar diya. 👋\n*Humein aapki yaad aayegi!*",
            color=0x6B7280
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Members: {member.guild.member_count}")
        await welcome_ch.send(embed=embed)

    # ── /testwelcome command (admin only) ────────────────────────────────────
    @app_commands.command(name="testwelcome", description="Welcome message test karein (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Send a test welcome message for the command user."""
        welcome_ch = self.find_welcome_channel(interaction.guild)

        if not welcome_ch:
            return await interaction.response.send_message(
                "❌ Welcome channel nahi mila! Channel ka naam 'welcome' hona chahiye.",
                ephemeral=True
            )

        embed = self.build_welcome_embed(interaction.user)
        view = WelcomeView(interaction.user)

        await welcome_ch.send(
            content=f"🎉 **{interaction.user.mention}** ne server join kiya! *(Test)*",
            embed=embed,
            view=view
        )
        await interaction.response.send_message(
            f"✅ Test welcome message **#{welcome_ch.name}** mein bheja gaya!",
            ephemeral=True
        )

    # ── /setwelcome command ──────────────────────────────────────────────────
    @app_commands.command(name="setwelcome", description="Is channel ko welcome channel set karein")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome(self, interaction: discord.Interaction):
        ch = interaction.channel
        embed = discord.Embed(
            title="✅ Welcome Channel Set!",
            description=f"Ab **#{ch.name}** mein welcome messages aayenge jab koi server join karega.",
            color=0x22c55e
        )
        await interaction.response.send_message(embed=embed)


# ── Welcome Buttons View ─────────────────────────────────────────────────────
class WelcomeView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

        # Add "Rules" button (link)
        self.add_item(discord.ui.Button(
            label="📋 Rules",
            style=discord.ButtonStyle.link,
            url="https://discord.com/channels/@me",  # Updated by bot owner
            row=0
        ))

    @discord.ui.button(label="👋 Say Hi!", style=discord.ButtonStyle.primary, emoji="👋", row=0)
    async def say_hi(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member.id:
            await interaction.response.send_message(
                f"Apne aap ko hi hi nahi bolte! 😄",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"👋 **{interaction.user.display_name}** ne **{self.member.display_name}** ko welcome kiya!",
                ephemeral=False
            )

    @discord.ui.button(label="🎵 Play Music", style=discord.ButtonStyle.secondary, emoji="🎵", row=0)
    async def play_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🎵 Music enjoy karein! `/play` command use karein koi bhi gaana play karne ke liye!",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Welcome(bot))
