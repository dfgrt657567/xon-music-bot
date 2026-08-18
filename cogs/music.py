import asyncio
import functools
import glob
import itertools
import os
import shutil
import sys
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

# Modern yt-dlp configuration with Remote EJS challenge solver to completely bypass YouTube "Sign in to confirm you're not a bot"
ytdl_format_options = {
    'format': 'm4a/bestaudio/best',
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
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web_embedded', 'mweb']
        }
    },
    'remote_components': ['ejs:github'],
    'js_runtimes': {'node': {}}
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


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
        self.uploader = data.get('uploader', 'Unknown Artist')

    @staticmethod
    def parse_duration(duration: int) -> str:
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration_parts = []
        if days > 0:
            duration_parts.append(f"{days}d")
        if hours > 0:
            duration_parts.append(f"{hours}h")
        if minutes > 0:
            duration_parts.append(f"{minutes}m")
        duration_parts.append(f"{seconds}s")
        return " ".join(duration_parts)

    @classmethod
    async def create_source(cls, requester, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        if not search.startswith(('http://', 'https://')):
            query = f"ytsearch1:{search}"
        else:
            query = search

        try:
            partial_extract = functools.partial(ytdl.extract_info, query, download=False)
            data = await loop.run_in_executor(None, partial_extract)
        except Exception as e:
            raise YTDLError(f"Extraction error: {e}")

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
        self.volume = 1.0
        self.dj_role = "DJ"

        self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Disconnect after 3 minutes of idle inactivity
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

        if vc.is_playing() or not player.queue.empty():
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
        embed.add_field(name="👋 `!leave` ya `/leave`", value="Voice channel se disconnect karein", inline=False)
        embed.set_footer(text="Slash Commands & Prefix Commands Supported 🎧")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
