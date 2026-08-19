import asyncio
import discord
from discord import app_commands
from discord.ext import commands


class Moderation(commands.Cog):
    """Server Moderation Commands - Clear/Purge Chat, etc."""

    def __init__(self, bot):
        self.bot = bot

    # ─── /clear (Slash Command) ───────────────────────────────────────────────

    @app_commands.command(name="clear", description="Channel ke messages delete karein")
    @app_commands.describe(amount="Kitne messages delete karne hain (1-500)")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_clear(self, interaction: discord.Interaction, amount: int):
        """Delete a specified number of messages from the current channel."""
        if amount < 1 or amount > 500:
            return await interaction.response.send_message(
                "❌ Amount **1 se 500** ke beech hona chahiye.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=amount)
            count = len(deleted)

            embed = discord.Embed(
                title="🗑️ Chat Clear Ho Gayi!",
                description=f"**{count}** messages successfully delete kar diye gaye.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Cleared by: {interaction.user.display_name}")

            confirm = await interaction.followup.send(embed=embed, ephemeral=False)

            # Auto-delete the confirmation message after 5 seconds
            await asyncio.sleep(5)
            try:
                await confirm.delete()
            except Exception:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot ko `Manage Messages` permission nahi hai!",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Messages delete karne me error: `{e}`",
                ephemeral=True
            )

    @app_commands.command(name="clearall", description="Poori channel ki saari messages delete karein (Max 500)")
    @app_commands.default_permissions(administrator=True)
    async def slash_clearall(self, interaction: discord.Interaction):
        """Delete all messages (up to 500) from the current channel."""
        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=500)
            count = len(deleted)

            embed = discord.Embed(
                title="🔥 Full Channel Clear!",
                description=f"**{count}** messages delete kar diye gaye.",
                color=discord.Color.dark_red()
            )
            embed.set_footer(text=f"Cleared by: {interaction.user.display_name}")

            confirm = await interaction.followup.send(embed=embed, ephemeral=False)
            await asyncio.sleep(5)
            try:
                await confirm.delete()
            except Exception:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot ko `Manage Messages` permission nahi hai!",
                ephemeral=True
            )

    @app_commands.command(name="clearuser", description="Kisi specific user ke messages delete karein")
    @app_commands.describe(
        user="Jis user ke messages delete karne hain",
        amount="Kitne messages scan karne hain (1-200)"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def slash_clearuser(self, interaction: discord.Interaction, user: discord.Member, amount: int = 100):
        """Delete messages from a specific user in the current channel."""
        if amount < 1 or amount > 200:
            return await interaction.response.send_message(
                "❌ Amount **1 se 200** ke beech hona chahiye.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        def check(msg):
            return msg.author.id == user.id

        try:
            deleted = await interaction.channel.purge(limit=amount, check=check)
            count = len(deleted)

            embed = discord.Embed(
                title="🗑️ User Messages Clear!",
                description=f"**{user.display_name}** ke **{count}** messages delete kar diye gaye.",
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Cleared by: {interaction.user.display_name}")

            confirm = await interaction.followup.send(embed=embed, ephemeral=False)
            await asyncio.sleep(5)
            try:
                await confirm.delete()
            except Exception:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot ko `Manage Messages` permission nahi hai!",
                ephemeral=True
            )

    # ─── Prefix Commands (!clear, !clearall, !clearuser) ────────────────────

    @commands.command(name="clear", aliases=["purge", "c"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        """Delete specified number of messages. Usage: !clear <amount>"""
        if amount < 1 or amount > 500:
            return await ctx.send("❌ Amount **1 se 500** ke beech hona chahiye.", delete_after=5)

        # Delete the command message first
        try:
            await ctx.message.delete()
        except Exception:
            pass

        deleted = await ctx.channel.purge(limit=amount)
        count = len(deleted)

        embed = discord.Embed(
            title="🗑️ Chat Clear Ho Gayi!",
            description=f"**{count}** messages delete kar diye gaye.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Cleared by: {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass

    @commands.command(name="clearall")
    @commands.has_permissions(administrator=True)
    async def clearall(self, ctx):
        """Delete all messages (up to 500). Usage: !clearall"""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        deleted = await ctx.channel.purge(limit=500)
        count = len(deleted)

        embed = discord.Embed(
            title="🔥 Full Channel Clear!",
            description=f"**{count}** messages delete kar diye gaye.",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"Cleared by: {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass

    @commands.command(name="clearuser", aliases=["cu"])
    @commands.has_permissions(manage_messages=True)
    async def clearuser(self, ctx, member: discord.Member, amount: int = 100):
        """Delete messages from a specific user. Usage: !clearuser @user <amount>"""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        def check(msg):
            return msg.author.id == member.id

        deleted = await ctx.channel.purge(limit=amount, check=check)
        count = len(deleted)

        embed = discord.Embed(
            title="🗑️ User Messages Clear!",
            description=f"**{member.display_name}** ke **{count}** messages delete kar diye gaye.",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Cleared by: {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass

    # ─── Error Handlers ───────────────────────────────────────────────────────

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Aapke paas `Manage Messages` permission nahi hai!", delete_after=5)
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Sirf number dein. Example: `!clear 50`", delete_after=5)

    @clearall.error
    async def clearall_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Yeh command sirf Admins use kar sakte hain!", delete_after=5)

    @clearuser.error
    async def clearuser_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Aapke paas `Manage Messages` permission nahi hai!", delete_after=5)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ User nahi mila. `@mention` se user specify karein.", delete_after=5)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
