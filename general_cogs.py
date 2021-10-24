import discord
import re
import pandas as pd
from datetime import datetime
from discord.ext import commands

from gsheet_handler import DfHandlerGen
from general_utils import GeneralUtils
from id_dict import id_dict

dfgen = DfHandlerGen()
general_utils = GeneralUtils(dfgen, id_dict)


class BotLog():
    """An object to manage logging commands and responses."""
    def __init__(self, bot):
        """Registers associated bot."""
        self.bot = bot
        self.log_channel = self.bot.get_channel(id_dict['Logs'])

    async def log(self, message):
        """Extract message object elements to log the command used."""
        if self.log_channel == None:
            self.log_channel = self.bot.get_channel(id_dict['Logs'])
        if message.guild == None:
            embed = discord.Embed(title= f"{message.channel}")
        else:
            embed = discord.Embed(title= f"{message.guild} | {message.channel}")
        embed.add_field(name='Content', value=message.content)
        embed.add_field(name='Author', value=message.author)
        embed.add_field(name='Time', value=datetime.strftime(datetime.now(),
                        '%Y/%m/%d %H:%M'))
        await self.log_channel.send(embed=embed)

    async def send(self, ctx, content=None, embed=None):
        """Send the same content to both the intended channel and the log
        channel.
        """
        await ctx.send(content, embed=embed)
        await self.log_channel.send(content, embed=embed)


class TestCommands(commands.Cog):
    """Discord cog with test commands."""
    def __init__(self, bot):
        """Registers associated bot."""
        self.bot = bot

    @commands.command()
    async def emotes(self, ctx, *arg):
        """Main purpose is to get animated emote ids without nitro."""
        emotes = [str(a) for a in ctx.message.guild.emojis]
        try:
            if arg[0] == 'raw':
                await ctx.send(f"`{' '.join(emotes)}`")
        except IndexError:
            await ctx.send(' '.join(emotes))

    @commands.command()
    async def teststr(self, ctx):
        embed = discord.Embed()
        embed.description = 'abcd'
        await ctx.send(embed = embed)

    @commands.command()
    async def testcommand(self, ctx, member: discord.Member):
        await ctx.send(member.id)

class GeneralCommands(commands.Cog):
    """Discord cog with general purpose commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command()
    async def sync(self, ctx):
        """(Owner only) Synchronise general sheets."""
        if ctx.message.author.id == id_dict['Owner']:
            dfgen.sync()
            await ctx.send('Google sheet synced for general data.')

    @commands.command()
    async def ping(self, ctx):
        """Standard ping command."""
        await self.log.log(ctx.message)
        await self.log.send(ctx, f"Pong! {round(self.bot.latency * 1000)} ms")

    @commands.command()
    async def invite(self, ctx):
        await self.log.log(ctx.message)
        await self.log.send(ctx, ''.join((
            'Not sure what your purpose is but if you want to invite the bot ',
            'to your server. Contact the owner (read `=help`).'
        )))

    @commands.command(aliases=['calc', 'eval'])
    async def math(self, ctx, *arg):
        """Standard math command."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try adding some mathematical formula.')
            return
        argstr = ' '.join(arg).strip('`')
        mathstr = general_utils.math(argstr)
        try:
            float(mathstr)
        except ValueError:
            if mathstr not in general_utils.math_errors:
                # If called with only string with no operations.
                glare_emote = '<:blobthinkingglare:801974273236926524>'
                await self.log.send(ctx, f"<@{ctx.author.id}> {glare_emote}")
                return
        await self.log.send(ctx, f"`{argstr} = {mathstr}`")

    @commands.command()
    async def tag(self, ctx, *arg):
        """Tag command to record tags with contents freely added by users."""
        if ctx.guild.id in list(dfgen.ids[dfgen.ids['Type'] == 'Tag']['ID']):
            await self.log.log(ctx.message)
            if len(arg) == 0:
                await self.log.send(ctx, '\n'.join((
                    '`=tag keyword` to call contents of a tag, or',
                    '`=tag keyword contents` to add contents to a tag.'
                )))
                return
            elif len(arg) == 1:
                df = dfgen.tags[dfgen.tags['Tag'] == arg[0]]
                if len(df) == 0:
                    await self.log.send(ctx,
                        '`=tag keyword contents` to add contents first')
                else:
                    await self.log.send(ctx, '\n'.join(df['Content']))
            else:
                dfgen.add_tag(
                    arg[0],
                    ' '.join(arg[1:]),
                    str(ctx.message.author.id)
                )
                await self.log.send(ctx, f"Content added to tag {arg[0]}.")

    @commands.command()
    async def checkservers(self, ctx, *arg):
        """(Owner only) Check what servers bot is in."""
        if ctx.message.author.id == id_dict['Owner']:
            guilds = list(self.bot.guilds)
            guild_names = '\n'.join(f"- {a.name}" for a in guilds)
            await ctx.send(
                f"Connected on {len(guilds)} servers:\n{guild_names}")

    @commands.command(aliases = ['scadd'])
    async def scnew(self, ctx, *arg):
        """(Owner only) Add new shortcut."""
        if ctx.message.author.id == id_dict['Owner']:
            await ctx.send(general_utils.add_shortcut(*arg))

    @commands.command()
    async def sendmsg(self, ctx, *arg):
        """(Owner only) Send custom message in specific channel."""
        if ctx.message.author.id == id_dict['Owner']:
            try:
                channel = self.bot.get_channel(int(arg[0]))
                arg = arg[1:]
            except ValueError:
                channel = self.bot.get_channel(
                    general_utils.get_shortcut(arg[0]))
                arg = arg[1:]
            if len(arg) == 0:
                msg = 'Hi.'
            else:
                msg = general_utils.message_process(' '.join(arg))
            await channel.send(msg)

    @commands.command()
    async def delmsg(self, ctx, *arg):
        """(Owner only) Delete specific message in specific channel."""
        if ctx.message.author.id == id_dict['Owner']:
            if len(arg) == 1:
                msg = await ctx.fetch_message(int(arg[0]))
            elif len(arg) == 2:
                try:
                    channel = self.bot.get_channel(int(arg[0]))
                except ValueError:
                    channel = self.bot.get_channel(
                        general_utils.get_shortcut(arg[0]))
            try:
                try:
                    msg = await channel.fetch_message(int(arg[1]))
                except AttributeError:
                    await ctx.send('Channel not found.')
                    return
                await msg.delete()
                await ctx.send('Message deleted.')
            except discord.NotFound:
                await ctx.send('Message not found.')
