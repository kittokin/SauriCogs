import discord

from typing import Any
from discord.utils import get

from redbot.core import Config, checks, commands

from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)


class UniqueName(Cog):
    """Deny members' names to be the same as your Moderators'."""

    __author__ = "saurichable"
    __version__ = "1.1.3"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=58462132145646132, force_registration=True
        )

        self.config.register_guild(toggle=False, roles=[], name="username", channel=None)
        self.config.register_global(guilds=[])

    @commands.group(autohelp=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @checks.bot_has_permissions(manage_nicknames=True)
    async def unset(self, ctx: commands.Context):
        """Admin settings for ModName."""
        pass

    @unset.command(name="role")
    async def unset_role(self, ctx: commands.Context, role: discord.Role):
        """Add a role to the original list (f.e. Moderator or Admin role)."""
        async with self.config.guild(ctx.guild).roles() as roles:
            roles.append(role.id)
        await ctx.tick()

    @unset.command(name="channel")
    async def unset_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for warnings.

        If the channel is not provided, logging will be disabled."""
        if channel:
            await self.config.guild(ctx.guild).channel.set(channel.id)
        else:
            await self.config.guild(ctx.guild).channel.set(None)
        await ctx.tick()

    @unset.command(name="name")
    async def unset_name(self, ctx: commands.Context, name: str):
        """Set a default name that will be set."""
        await self.config.guild(ctx.guild).name.set(name)
        await ctx.tick()

    @unset.command(name="toggle")
    async def unset_toggle(self, ctx: commands.Context, on_off: bool = None):
        """Toggle UniqueName for this server. 

        If `on_off` is not provided, the state will be flipped."""
        target_state = (
            on_off
            if on_off is not None
            else not (await self.config.guild(ctx.guild).toggle())
        )
        await self.config.guild(ctx.guild).toggle.set(target_state)
        async with self.config.guilds() as guilds:
            guilds.append(ctx.guild.id)
        if target_state:
            await ctx.send("UniqueName is now enabled.")
        else:
            await ctx.send("UniqueName is now disabled.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if await self.config.guild(before.guild).toggle() is False:
            return
        config_roles = await self.config.guild(before.guild).roles()
        if len(config_roles) == 0:
            return
        if len(before.roles) == 0:
            pass
        else:
            for role in before.roles:
                if role.id in config_roles:
                    return
        names = await self._build_name_list(before.guild)
        name = await self.config.guild(before.guild).name()
        if after.nick is None:
            return
        if after.nick not in names:
            return
        await after.edit(nick=name, reason="UniqueName cog")
        channel = before.guild.get_channel(await self.config.guild(before.guild).channel())
        if channel is None:
            return
        warning_text = f"""**UniqueName warning:**
        
        Discovered a forbidden name: '{after.display_name}'. 
        User: {after.mention} - `{after.name}#{after.discriminator} ({after.id})`"""
        await channel.send(warning_text)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        guilds = await self.config.guilds()
        if len(guilds) == 0:
            return
        for gid in guilds:
            guild = self.bot.get_guild(gid)
            if guild is not None:
                member = guild.get_member(before.id)
                if member is None:
                    return
                if await self.config.guild(guild).toggle() is False:
                    return
                config_roles = await self.config.guild(guild).roles()
                if len(config_roles) == 0:
                    return
                if len(member.roles) != 0:
                    for role in member.roles:
                        if role.id in config_roles:
                            return
                names = await self._build_name_list(guild)
                name = await self.config.guild(guild).name()
                if after.name is None:
                    return
                if after.name not in names:
                    return
                await member.edit(nick=name, reason="UniqueName cog")
                channel = guild.get_channel(await self.config.guild(guild).channel())
                if channel is None:
                    return
                warning_text = f"""**UniqueName warning:**
                
                Discovered a forbidden name: '{after.name}'. 
                User: {after.mention} - `{after.name}#{after.discriminator} ({after.id})`"""
                await channel.send(warning_text)

    async def _build_name_list(self, guild):
        names = []
        for rid in await self.config.guild(guild).roles():
            role = guild.get_role(rid)
            if role is not None:
                for member in role.members:
                    names.append(member.nick)
                    names.append(member.name)
        return names
