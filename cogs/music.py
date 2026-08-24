import asyncio
import functools
import glob
import itertools
import json
import os
import re
import shutil
import sys
import urllib.request
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl


def get_ffmpeg_executable():
    """Find ffmpeg.exe path even if PATH environment variable hasn't refreshed."""
    path = shutil.which("ffmpeg")
    if path and os.path.exists(path):
        return path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*ffmpeg*", "**", "ffmpeg.exe")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            ffmpeg_dir = os.path.dirname(matches[0])
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            return matches[0]

    return "ffmpeg"


FFMPEG_PATH = get_ffmpeg_executable()
print(f"[+] Using FFmpeg: {FFMPEG_PATH}")

# Auto-detect cookies.txt for YouTube authentication
COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cookies.txt')
if os.path.exists(COOKIES_FILE):
    print(f"[+] YouTube cookies found: {COOKIES_FILE}")
else:
    COOKIES_FILE = None
    print("[!] No cookies.txt found — YouTube may show bot detection errors")

# Primary yt-dlp config — Multi-client rotation to bypass bot detection
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'source_address': '0.0.0.0',
    'age_limit': 100,
    'geo_bypass': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['default', 'mediaconnect', 'tv_embedded', 'android_vr'],
            'player_skip': ['web_creator', 'mweb'],
        }
    }
}

# Add cookies if available
if COOKIES_FILE:
    ytdl_format_options['cookiefile'] = COOKIES_FILE

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -reconnect_on_network_error 1',
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
ytdl_fallback = youtube_dl.YoutubeDL({
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'default_search': 'scsearch1'
})

# Universal extractor for all non-YouTube platforms (Instagram, TikTok, Twitter, Facebook, etc.)
ytdl_universal = youtube_dl.YoutubeDL({
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
})


def get_youtube_video_id(search: str):
    """Extract 11-char YouTube video ID from any link or raw ID."""
    clean = search.strip()
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', clean) and not re.search(r'[aeiou]{3,}', clean, re.IGNORECASE):
        return clean
    yt_match = re.search(r'(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|shorts\/|embed\/))([a-zA-Z0-9_-]{11})', clean)
    if yt_match:
        return yt_match.group(1)
    return None


# ── Platform URL Patterns ────────────────────────────────────────────────────
PLATFORM_PATTERNS = {
    'Instagram':   re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/', re.I),
    'TikTok':      re.compile(r'(?:https?://)?(?:www\.)?(?:tiktok\.com/@[^/]+/video/|vm\.tiktok\.com/)', re.I),
    'Twitter':     re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/', re.I),
    'Facebook':    re.compile(r'(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.watch)/', re.I),
    'Twitch':      re.compile(r'(?:https?://)?(?:www\.)?twitch\.tv/(?:videos/|clip)', re.I),
    'Reddit':      re.compile(r'(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/', re.I),
    'Dailymotion': re.compile(r'(?:https?://)?(?:www\.)?dailymotion\.com/video/', re.I),
    'Vimeo':       re.compile(r'(?:https?://)?(?:www\.)?vimeo\.com/\d+', re.I),
    'Rumble':      re.compile(r'(?:https?://)?(?:www\.)?rumble\.com/v', re.I),
    'SoundCloud':  re.compile(r'(?:https?://)?(?:www\.)?soundcloud\.com/', re.I),
    'Spotify':     re.compile(r'(?:https?://)?open\.spotify\.com/(?:track|album|playlist)/', re.I),
    'Pinterest':   re.compile(r'(?:https?://)?(?:www\.)?pinterest\.(?:com|co\.uk)/pin/', re.I),
}

PLATFORM_EMOJIS = {
    'Instagram': '📸', 'TikTok': '🎵', 'Twitter': '🐦',
    'Facebook': '👤', 'Twitch': '🟣', 'Reddit': '🤖',
    'Dailymotion': '🎥', 'Vimeo': '🎦', 'Rumble': '📢',
    'SoundCloud': '☁️', 'Spotify': '💚', 'Pinterest': '📌',
    'YouTube': '📺', 'Search': '🔍',
}


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to. Returns platform name or None."""
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return None


def is_instagram_url(search: str) -> bool:
    return bool(PLATFORM_PATTERNS['Instagram'].search(search.strip()))


def get_instagram_shortcode(search: str):
    m = re.search(r'instagram\.com/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)', search)
    return m.group(1) if m else None


def fetch_spotify_title(url: str):
    """Extract Spotify track title via oEmbed API for YouTube search fallback."""
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            title = data.get('title', '')
            artist = data.get('author_name', '')
            return f"{title} {artist}".strip() if title else None
    except Exception:
        return None


def fetch_oembed_title(video_id: str):
    """Fetch real YouTube video title via public oEmbed API."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data.get('title')
    except Exception:
        return None


def normalize_music_query(search: str) -> str:
    """Normalize URLs (all platforms) or search queries."""
    clean = search.strip()
    # Strip Discord markdown junk: backticks, quotes, angle brackets from both ends
    clean = re.sub(r'^[`\'"<>\s]+|[`\'"<>\s]+$', '', clean)
    clean = re.sub(r'^[\U0001F000-\U0001FFFF\s]+', '', clean).strip()
    clean = re.sub(r'^Joined \w+ & playing\s+', '', clean, flags=re.IGNORECASE).strip()

    # Any supported platform URL — pass directly to create_source
    if clean.startswith(('http://', 'https://')):
        return clean

    video_id = get_youtube_video_id(clean)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return f"ytsearch1:{clean}"


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester=None, volume=1.0):
        super().__init__(source, volume)
        self.data = data
        self.requester = requester
        self.title = data.get('title', 'Unknown Title')
        self.url = data.get('webpage_url', data.get('url', ''))
        self.duration = self.parse_duration(int(data.get('duration', 0))) if data.get('duration') else 'Live Stream'
        self.thumbnail = data.get('thumbnail', None)
        self.uploader = data.get('uploader', data.get('channel', 'Unknown Artist'))

    @staticmethod
    def parse_duration(duration: int) -> str:
        # BUG-01 FIX: Correct hours/minutes/seconds calculation
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration_parts = []
        if days > 0:
            duration_parts.append(f"{days}d")
        if hours > 0:                                    # was checking 'minutes' twice — fixed to 'hours'
            duration_parts.append(f"{hours}h")
        if minutes > 0:
            duration_parts.append(f"{minutes}m")
        duration_parts.append(f"{seconds}s")
        return " ".join(duration_parts)

    @classmethod
    async def create_source(cls, requester, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()
        query = normalize_music_query(search)
        video_id = get_youtube_video_id(search)
        platform = detect_platform(query) if query.startswith(('http://', 'https://')) else None

        data = None
        emoji = PLATFORM_EMOJIS.get(platform or 'Search', '🔍')

        # ── Spotify: extract title via oEmbed then search YouTube ──────────────────────
        if platform == 'Spotify':
            print(f"[💚] Spotify link detected, fetching title...")
            spotify_title = await loop.run_in_executor(None, lambda: fetch_spotify_title(query))
            if spotify_title:
                yt_query = f"ytsearch1:{spotify_title}"
                try:
                    partial_sp = functools.partial(ytdl.extract_info, yt_query, download=False)
                    sp_data = await loop.run_in_executor(None, partial_sp)
                    if sp_data and 'entries' in sp_data and sp_data['entries']:
                        data = sp_data['entries'][0]
                except Exception as sp_err:
                    print(f"[!] Spotify YouTube search failed: {sp_err}")
            if not data:
                raise YTDLError(f"💚 Spotify track nahi mil paya. Song naam se search karein: `{search}`")
            stream_url = data.get('url')
            if not stream_url:
                raise YTDLError("Spotify audio stream URL nahi mili.")
            audio_source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH, **ffmpeg_options)
            return cls(audio_source, data=data, requester=requester, volume=1.0)

        # ── All other external platform URLs (Instagram, TikTok, Twitter, Facebook, etc.) ───
        if platform and platform not in ('YouTube',):
            print(f"[{emoji}] {platform} URL detected: {query}")
            try:
                partial_ext = functools.partial(ytdl_universal.extract_info, query, download=False)
                data = await loop.run_in_executor(None, partial_ext)
                if data and 'entries' in data:
                    data = data['entries'][0] if data['entries'] else None
            except Exception as ext_err:
                print(f"[!] {platform} extraction failed: {ext_err}")
                data = None

            # Fallback: search by title on YouTube if direct extraction failed
            if not data:
                print(f"[!] {platform} direct extraction failed, trying YouTube title search...")
                # For Instagram, use shortcode as search hint
                if platform == 'Instagram':
                    sc = get_instagram_shortcode(query)
                    fb_q = f"ytsearch1:instagram reel {sc}" if sc else None
                else:
                    fb_q = None

                if fb_q:
                    try:
                        partial_fb = functools.partial(ytdl.extract_info, fb_q, download=False)
                        fb_data = await loop.run_in_executor(None, partial_fb)
                        if fb_data and 'entries' in fb_data and fb_data['entries']:
                            data = fb_data['entries'][0]
                    except Exception as fb_err:
                        print(f"[-] {platform} fallback search failed: {fb_err}")

            if not data:
                raise YTDLError(
                    f"{emoji} {platform} link se audio nahi mila. "
                    f"Public content hai? Ya song naam se search karein: `{search}`"
                )

            stream_url = data.get('url')
            if not stream_url:
                raise YTDLError(f"{emoji} {platform} audio stream URL nahi mili.")

            audio_source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH, **ffmpeg_options)
            return cls(audio_source, data=data, requester=requester, volume=1.0)

        # ── YouTube / Text Search ───────────────────────────────────────────────
        # 1. Primary extraction
        data = None
        try:
            partial_extract = functools.partial(ytdl.extract_info, query, download=False)
            data = await loop.run_in_executor(None, partial_extract)
        except Exception as primary_err:
            print(f"[!] Primary extraction failed on {query}: {primary_err}")

            # 2. Retry with different YouTube client if bot detection
            if 'Sign in to confirm' in str(primary_err) or 'bot' in str(primary_err).lower():
                print("[!] YouTube bot detection — retrying with android client...")
                try:
                    retry_ytdl = youtube_dl.YoutubeDL({
                        **ytdl_format_options,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['android', 'ios', 'tv'],
                                'player_skip': ['web', 'web_creator', 'mweb'],
                            }
                        }
                    })
                    partial_retry = functools.partial(retry_ytdl.extract_info, query, download=False)
                    data = await loop.run_in_executor(None, partial_retry)
                except Exception as retry_err:
                    print(f"[!] Retry extraction also failed: {retry_err}")

        # 3. Resilient fallback (oEmbed title → YouTube search → SoundCloud)
        if not data or ('entries' in data and not data['entries']):
            search_term = None
            if video_id:
                oembed_title = await loop.run_in_executor(None, lambda: fetch_oembed_title(video_id))
                if oembed_title:
                    search_term = oembed_title
                    print(f"[🔄] Fallback: Got title via oEmbed: {oembed_title}")
            if not search_term and not search.startswith(('http://', 'https://')):
                search_term = search.strip()

            if search_term:
                # Try YouTube search by title (search queries bypass bot detection)
                try:
                    yt_search_query = f"ytsearch1:{search_term}"
                    partial_yt_fb = functools.partial(ytdl.extract_info, yt_search_query, download=False)
                    data = await loop.run_in_executor(None, partial_yt_fb)
                    if data and 'entries' in data and data['entries']:
                        print(f"[✅] YouTube search fallback worked: {search_term}")
                except Exception as yt_fb_err:
                    print(f"[-] YouTube search fallback failed: {yt_fb_err}")

            # Last resort: SoundCloud
            if (not data or ('entries' in data and not data['entries'])) and search_term:
                try:
                    fallback_query = f"scsearch1:{search_term}"
                    partial_fb = functools.partial(ytdl_fallback.extract_info, fallback_query, download=False)
                    data = await loop.run_in_executor(None, partial_fb)
                    if data:
                        print(f"[✅] SoundCloud fallback worked: {search_term}")
                except Exception as fb_err:
                    print(f"[-] SoundCloud fallback failed: {fb_err}")

        if data is None:
            raise YTDLError(f"Koi gaana nahi mila: `{search}`")

        if 'entries' in data:
            if not data['entries']:
                raise YTDLError(f"Koi gaana nahi mila: `{search}`")
            data = data['entries'][0]

        stream_url = data.get('url')
        if not stream_url:
            raise YTDLError("Audio stream URL nahi mil paya.")

        audio_source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH, **ffmpeg_options)
        return cls(audio_source, data=data, requester=requester, volume=1.0)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self, status: str = "Now Playing"):
        embed = discord.Embed(
            title=f"🎵 {status}",
            description=f"[{self.source.title}]({self.source.url})",
            color=discord.Color.blurple()
        )
        embed.add_field(name="⏱️ Duration", value=self.source.duration, inline=True)
        embed.add_field(name="👤 Requested By", value=self.requester.mention if self.requester else "Unknown", inline=True)
        embed.add_field(name="🎤 Artist/Channel", value=self.source.uploader, inline=True)
        if self.source.thumbnail:
            embed.set_thumbnail(url=self.source.thumbnail)
        return embed


class GuildMusicPlayer:
    """Manages audio playback and song queue per Discord Server (Guild)."""

    def __init__(self, bot, guild, channel, cog):
        self.bot = bot
        self.guild = guild
        self.channel = channel
        self.cog = cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.current = None
        self.loop = False
        self.mode_247 = True  # 24/7 mode is ON by default
        self.volume = 1.0
        self.dj_role = "DJ"

        self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # BUG-04 FIX: In 24/7 mode, periodically check if vc is still alive (prevent zombie loop)
                if self.mode_247:
                    while True:
                        try:
                            async with asyncio.timeout(30):
                                song = await self.queue.get()
                            break  # got a song, proceed
                        except asyncio.TimeoutError:
                            # Check if voice client is still connected — reconnect if dropped
                            vc = self.guild.voice_client
                            if not vc or not vc.is_connected():
                                try:
                                    await self.channel.send("⚠️ Voice connection drop hua! `/join` karke wapas connect karein.")
                                except Exception:
                                    pass
                                await self.destroy(self.guild)
                                return
                else:
                    async with asyncio.timeout(180):
                        song = await self.queue.get()
            except asyncio.TimeoutError:
                if self.guild.voice_client and not self.guild.voice_client.is_playing():
                    try:
                        await self.channel.send("⏱️ Inactivity ki wajah se bot voice channel chhod raha hai. 👋")
                    except Exception:
                        pass
                    await self.destroy(self.guild)
                return

            self.current = song

            if not self.guild.voice_client:
                return

            def after_playing(error):
                if error:
                    print(f"Playback error: {error}")
                self.bot.loop.call_soon_threadsafe(self.next.set)

            self.guild.voice_client.play(song.source, after=after_playing)

            try:
                embed = song.create_embed("Now Playing")
                await self.channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending now playing embed: {e}")

            await self.next.wait()

            # Handle looping
            if self.loop and self.current:
                try:
                    new_source = await YTDLSource.create_source(
                        song.requester,
                        self.current.source.url,
                        loop=self.bot.loop
                    )
                    await self.queue.put(Song(new_source))
                except Exception as e:
                    print(f"Error looping song: {e}")

            if song.source:
                try:
                    song.source.cleanup()
                except Exception:
                    pass
            self.current = None

    async def destroy(self, guild):
        # BUG-02 FIX: Properly disconnect voice client before cleanup
        try:
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
        except Exception:
            pass
        return self.cog.cleanup(guild)


class Music(commands.Cog):
    """Commands for Discord Music Player (Supports Prefix & Slash Commands)"""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.dj_roles = {}

    def cleanup(self, guild):
        try:
            state = self.players.get(guild.id)
            if state:
                del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, guild, channel):
        try:
            player = self.players[guild.id]
            player.channel = channel
        except KeyError:
            player = GuildMusicPlayer(self.bot, guild, channel, self)
            player.dj_role = self.dj_roles.get(guild.id, "DJ")
            self.players[guild.id] = player
        return player

    def _has_dj_permission(self, member, guild):
        """Check if user is Admin, Owner, or has the DJ role."""
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild or guild.owner_id == member.id:
            return True
        dj_name = self.dj_roles.get(guild.id, "DJ").lower()
        return any(role.name.lower() == dj_name for role in member.roles)

    async def _ensure_voice(self, user, guild):
        """Helper to ensure member is in voice and bot connects immediately."""
        member = guild.get_member(user.id) if hasattr(user, 'id') else user
        if not member or not hasattr(member, 'voice') or not member.voice or not member.voice.channel:
            return None, "❌ Pehle aapko kisi Voice Channel me judna hoga!"

        target_channel = member.voice.channel
        voice_client = guild.voice_client

        if not voice_client:
            try:
                voice_client = await target_channel.connect(timeout=20.0, reconnect=True)
            except Exception as e:
                return None, f"❌ Voice channel connect karne me error: `{e}`"
        elif voice_client.channel.id != target_channel.id:
            try:
                await voice_client.move_to(target_channel)
            except Exception as e:
                return None, f"❌ Voice channel switch karne me error: `{e}`"

        return voice_client, None

    # ----------------- PLAY LOGIC (SHARED) -----------------
    async def _play_internal(self, user, guild, channel, search: str, reply_fn):
        vc, err = await self._ensure_voice(user, guild)
        if err:
            return await reply_fn(err)

        player = self.get_player(guild, channel)

        try:
            source = await YTDLSource.create_source(user, search, loop=self.bot.loop)
        except Exception as e:
            return await reply_fn(f"❌ Gaana load karne me error: `{e}`")

        song = Song(source)

        # BUG-03 FIX: Also check vc.is_paused() so paused bot queues correctly
        if vc.is_playing() or vc.is_paused() or not player.queue.empty():
            await player.queue.put(song)
            embed = discord.Embed(
                title="📋 Queue Me Add Ho Gaya",
                description=f"[{song.source.title}]({song.source.url})",
                color=discord.Color.green()
            )
            embed.add_field(name="⏱️ Duration", value=song.source.duration, inline=True)
            embed.add_field(name="👤 Requested By", value=user.mention, inline=True)
            if song.source.thumbnail:
                embed.set_thumbnail(url=song.source.thumbnail)
            await reply_fn(embed=embed)
        else:
            await player.queue.put(song)
            await reply_fn(f"🔊 Joined **{vc.channel.name}** & playing **{song.source.title}** 🎶")

    # ----------------- SLASH COMMANDS -----------------

    @app_commands.command(name="setdj", description="Server ke liye custom DJ role configure karein")
    @app_commands.describe(role="DJ role ka naam ya mention")
    async def slash_setdj(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Yeh command sirf Server Admins use kar sakte hain!", ephemeral=True)
        self.dj_roles[interaction.guild.id] = role.name
        player = self.get_player(interaction.guild, interaction.channel)
        player.dj_role = role.name
        await interaction.response.send_message(f"✅ Server DJ Role set to: **@{role.name}**! Ab is role wale members music control kar sakte hain.")

    @app_commands.command(name="join", description="Bot ko apne Voice Channel me bulayein")
    async def slash_join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc, err = await self._ensure_voice(interaction.user, interaction.guild)
        if err:
            return await interaction.followup.send(err)
        await interaction.followup.send(f"🔊 **{vc.channel.name}** me jud gaya!")

    @app_commands.command(name="play", description="YouTube URL ya song name search karke play karein")
    @app_commands.describe(query="Song ka naam ya YouTube link")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        async def reply_fn(content=None, embed=None):
            try:
                if embed:
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(content)
            except Exception as e:
                print(f"Error in slash followup send: {e}")

        await self._play_internal(interaction.user, interaction.guild, interaction.channel, query, reply_fn)

    @app_commands.command(name="pause", description="Currently playing gaane ko pause karein")
    async def slash_pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Abhi koi gaana nahi chal raha hai.", ephemeral=True)
        vc.pause()
        await interaction.response.send_message("⏸️ Music pause ho gaya! Resume karne ke liye `/resume` use karein.")

    @app_commands.command(name="resume", description="Paused gaane ko resume karein")
    async def slash_resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            return await interaction.response.send_message("❌ Music pause nahi hai.", ephemeral=True)
        vc.resume()
        await interaction.response.send_message("▶️ Music wapas chal gaya!")

    @app_commands.command(name="skip", description="Current gaane ko skip karein")
    async def slash_skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Koi gaana nahi chal raha skip karne ke liye.", ephemeral=True)
        vc.stop()
        await interaction.response.send_message("⏭️ Gaana skip kar diya gaya!")

    @app_commands.command(name="stop", description="Music stop karein aur queue clear karein")
    async def slash_stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild, interaction.channel)
        while not player.queue.empty():
            try:
                player.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏹️ Playback stop kar diya aur queue clear ho gayi.")

    @app_commands.command(name="queue", description="Current song queue list dekhein")
    async def slash_queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild, interaction.channel)
        if player.queue.empty() and not player.current:
            return await interaction.response.send_message("📭 Queue bilkul khali hai!", ephemeral=True)

        upcoming = list(itertools.islice(player.queue._queue, 0, 10))
        fmt = '\n'.join(f"**{i + 1}.** [{song.source.title}]({song.source.url}) | Requested by: {song.requester.mention}" for i, song in enumerate(upcoming))

        embed = discord.Embed(title=f"🎶 Music Queue for {interaction.guild.name}", color=discord.Color.gold())
        if player.current:
            embed.add_field(name="▶️ Now Playing", value=f"[{player.current.source.title}]({player.current.source.url}) | `{player.current.source.duration}`", inline=False)
        embed.add_field(name="⏳ Up Next", value=fmt if fmt else "Koi gaana queue me nahi hai.", inline=False)
        total_songs = player.queue.qsize() + (1 if player.current else 0)
        dj_name = self.dj_roles.get(interaction.guild.id, "DJ")
        embed.set_footer(text=f"Total Songs: {total_songs} | DJ Role: @{dj_name} | Looping: {'✅ ON' if player.loop else '❌ OFF'}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Currently playing gaane ki details dekhein")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild, interaction.channel)
        if not player.current:
            return await interaction.response.send_message("❌ Abhi koi gaana nahi chal raha hai.", ephemeral=True)
        embed = player.current.create_embed("Now Playing")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Volume adjust karein (0-100)")
    @app_commands.describe(volume="Volume level 0 se 100")
    async def slash_volume(self, interaction: discord.Interaction, volume: int):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Abhi koi gaana nahi chal raha.", ephemeral=True)
        if not 0 <= volume <= 100:
            return await interaction.response.send_message("❌ Volume 0 se 100 ke beech hona chahiye.", ephemeral=True)

        player = self.get_player(interaction.guild, interaction.channel)
        player.volume = volume / 100
        if vc.source:
            vc.source.volume = volume / 100
        await interaction.response.send_message(f"🔊 Volume set ho gaya: **{volume}%**")

    @app_commands.command(name="loop", description="Current gaane ko repeat mode par lagayein")
    async def slash_loop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild, interaction.channel)
        player.loop = not player.loop
        status = "ON (Repeat 🔁)" if player.loop else "OFF ➡️"
        await interaction.response.send_message(f"🔁 Loop mode: **{status}**")

    @app_commands.command(name="leave", description="Bot ko voice channel se disconnect karein")
    async def slash_leave(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ Bot voice channel me nahi hai.", ephemeral=True)
        await self.get_player(interaction.guild, interaction.channel).destroy(interaction.guild)
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Voice channel se disconnect ho gaya!")

    @app_commands.command(name="247", description="Toggle 24/7 mode (Bot never leaves voice channel)")
    async def slash_247(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild, interaction.channel)
        player.mode_247 = not player.mode_247
        status = "ON ✅ (Ab bot hamesha Voice Channel me rahega)" if player.mode_247 else "OFF ❌ (Bot idle hone par leave kar dega)"
        await interaction.response.send_message(f"🎧 24/7 Mode: **{status}**")

    # ----------------- PREFIX COMMANDS (!play, !join, !setdj, etc.) -----------------

    @commands.command(name='setdj', aliases=['djrole'])
    async def set_dj(self, ctx, *, role_name: str):
        if not ctx.author.guild_permissions.manage_guild and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Yeh command sirf Server Admins use kar sakte hain!")
        clean_role = role_name.strip('@')
        self.dj_roles[ctx.guild.id] = clean_role
        self.get_player(ctx.guild, ctx.channel).dj_role = clean_role
        await ctx.send(f"✅ Server DJ Role set ho gaya: **@{clean_role}**! Is role wale members website & Discord se music play/control kar sakte hain.")

    @commands.command(name='join', aliases=['j', 'connect'])
    async def join(self, ctx):
        vc, err = await self._ensure_voice(ctx.author, ctx.guild)
        if err:
            return await ctx.send(err)
        await ctx.send(f"🔊 **{vc.channel.name}** me jud gaya!")

    @commands.command(name='play', aliases=['p', 'sing'])
    async def play(self, ctx, *, search: str):
        async def reply_fn(content=None, embed=None):
            if embed:
                await ctx.send(embed=embed)
            else:
                await ctx.send(content)
        await self._play_internal(ctx.author, ctx.guild, ctx.channel, search, reply_fn)

    @commands.command(name='pause')
    async def pause(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Abhi koi gaana nahi chal raha hai.")
        ctx.voice_client.pause()
        await ctx.send("⏸️ Music pause ho gaya! Resume karne ke liye `!resume` likhein.")

    @commands.command(name='resume', aliases=['unpause'])
    async def resume(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_paused():
            return await ctx.send("❌ Music pause nahi hai.")
        ctx.voice_client.resume()
        await ctx.send("▶️ Music wapas chal gaya!")

    @commands.command(name='skip', aliases=['s', 'next'])
    async def skip(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Koi gaana nahi chal raha skip karne ke liye.")
        ctx.voice_client.stop()
        await ctx.send("⏭️ Gaana skip kar diya gaya!")

    @commands.command(name='stop')
    async def stop(self, ctx):
        player = self.get_player(ctx.guild, ctx.channel)
        while not player.queue.empty():
            try:
                player.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        if ctx.voice_client:
            ctx.voice_client.stop()
        await ctx.send("⏹️ Playback stop kar diya aur queue clear ho gayi.")

    @commands.command(name='queue', aliases=['q'])
    async def queue_info(self, ctx):
        player = self.get_player(ctx.guild, ctx.channel)
        if player.queue.empty() and not player.current:
            return await ctx.send("📭 Queue bilkul khali hai!")
        upcoming = list(itertools.islice(player.queue._queue, 0, 10))
        fmt = '\n'.join(f"**{i + 1}.** [{song.source.title}]({song.source.url}) | Requested by: {song.requester.mention}" for i, song in enumerate(upcoming))
        embed = discord.Embed(title=f"🎶 Music Queue for {ctx.guild.name}", color=discord.Color.gold())
        if player.current:
            embed.add_field(name="▶️ Now Playing", value=f"[{player.current.source.title}]({player.current.source.url}) | `{player.current.source.duration}`", inline=False)
        embed.add_field(name="⏳ Up Next", value=fmt if fmt else "Koi gaana queue me nahi hai.", inline=False)
        total_songs = player.queue.qsize() + (1 if player.current else 0)
        dj_name = self.dj_roles.get(ctx.guild.id, "DJ")
        embed.set_footer(text=f"Total Songs: {total_songs} | DJ Role: @{dj_name} | Looping: {'✅ ON' if player.loop else '❌ OFF'}")
        await ctx.send(embed=embed)

    @commands.command(name='nowplaying', aliases=['np', 'current'])
    async def now_playing(self, ctx):
        player = self.get_player(ctx.guild, ctx.channel)
        if not player.current:
            return await ctx.send("❌ Abhi koi gaana nahi chal raha hai.")
        embed = player.current.create_embed("Now Playing")
        await ctx.send(embed=embed)

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, volume: int):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Abhi koi gaana nahi chal raha.")
        if not 0 <= volume <= 100:
            return await ctx.send("❌ Volume 0 se 100 ke beech me hona chahiye.")
        player = self.get_player(ctx.guild, ctx.channel)
        player.volume = volume / 100
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Volume set ho gaya: **{volume}%**")

    @commands.command(name='loop', aliases=['repeat'])
    async def toggle_loop(self, ctx):
        player = self.get_player(ctx.guild, ctx.channel)
        player.loop = not player.loop
        status = "ON (Repeat 🔁)" if player.loop else "OFF ➡️"
        await ctx.send(f"🔁 Loop mode: **{status}**")

    @commands.command(name='leave', aliases=['disconnect', 'dc'])
    async def leave(self, ctx):
        if not ctx.voice_client:
            return await ctx.send("❌ Bot kisi bhi Voice Channel me nahi hai.")
        await self.get_player(ctx.guild, ctx.channel).destroy(ctx.guild)
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Voice channel se disconnect ho gaya!")

    @commands.command(name='247')
    async def toggle_247(self, ctx):
        player = self.get_player(ctx.guild, ctx.channel)
        player.mode_247 = not player.mode_247
        status = "ON ✅ (Ab bot hamesha Voice Channel me rahega)" if player.mode_247 else "OFF ❌ (Bot idle hone par leave kar dega)"
        await ctx.send(f"🎧 24/7 Mode: **{status}**")

    @commands.command(name='musichelp', aliases=['mhelp', 'music'])
    async def music_help(self, ctx):
        embed = discord.Embed(
            title="🎵 XON Music Bot - Commands",
            description="Aap Prefix (`!`) ya Slash (`/`) commands dono use kar sakte hain:",
            color=discord.Color.purple()
        )
        embed.add_field(name="🛡️ `!setdj <role>` ya `/setdj`", value="Server ke liye custom DJ role set karein", inline=False)
        embed.add_field(name="🔊 `!join` ya `/join`", value="Bot ko voice channel me bulayein", inline=False)
        embed.add_field(name="▶️ `!play` ya `/play <song>`", value="Song name ya YouTube URL play karein", inline=False)
        embed.add_field(name="⏸️ `!pause` ya `/pause`", value="Music ko pause karein", inline=False)
        embed.add_field(name="▶️ `!resume` ya `/resume`", value="Paused music resume karein", inline=False)
        embed.add_field(name="⏭️ `!skip` ya `/skip`", value="Agla song play karein", inline=False)
        embed.add_field(name="⏹️ `!stop` ya `/stop`", value="Music stop karein & queue clear karein", inline=False)
        embed.add_field(name="📋 `!queue` ya `/queue`", value="Upcoming songs list dekhein", inline=False)
        embed.add_field(name="🎶 `!np` ya `/nowplaying`", value="Current song details", inline=False)
        embed.add_field(name="🔊 `!volume` ya `/volume <0-100>`", value="Volume adjust karein", inline=False)
        embed.add_field(name="🔁 `!loop` ya `/loop`", value="Song loop toggle karein", inline=False)
        embed.add_field(name="🎧 `!247` ya `/247`", value="Toggle 24/7 Always Active mode", inline=False)
        embed.add_field(name="👋 `!leave` ya `/leave`", value="Voice channel se disconnect karein", inline=False)
        embed.set_footer(text="Slash Commands & Prefix Commands Supported 🎧")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
