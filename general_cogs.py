import discord, re
import pandas as pd
from discord.ext import commands
from gsheet_handler import DfHandlerGen
from general_utils import logs_embed, GeneralUtils
from id_dict import id_dict

dfgen = DfHandlerGen()
general_utils = GeneralUtils(dfgen, id_dict)

class TestCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def emotes(self, ctx, *arg):
        # Mostly to get animated emote ids
        emotes = [str(a) for a in ctx.message.guild.emojis]
        try:
            if arg[0] == 'raw':
                await ctx.send(f"`{' '.join(emotes)}`")
        except IndexError:
            await ctx.send(' '.join(emotes))

    @commands.command()
    async def teststr(self, ctx):
        # Test specific bot responses
        embed = discord.Embed()
        embed.description = 'abcd'
        await ctx.send(embed = embed)

    @commands.command()
    async def testcommand(self, ctx, member: discord.Member):
        await ctx.send(member.id)

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sync(self, ctx):
        if ctx.message.author.id == id_dict['Owner']:
            # Synchronise general sheets
            dfgen.sync()
            await ctx.send('Google sheet synced for general data.')

    @commands.command()
    async def ping(self, ctx):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)} ms")

    @commands.command(aliases=['calc', 'eval'])
    async def math(self, ctx, *arg):
        # Standard math command
        if len(arg) == 0:
            await ctx.send('Try adding some mathematical formula.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        argstr = ' '.join(arg).strip('`')
        mathstr = general_utils.math(argstr)
        try:
            float(mathstr)
        except ValueError:
            if mathstr not in general_utils.math_errors:
                # If only called with 1 string with no operations
                await ctx.send(f"<@{ctx.author.id}> <:blobthinkingglare:801974273236926524>")
                return
        await ctx.send(f"`{argstr} = {mathstr}`")

    @commands.command()
    async def checkservers(self, ctx, *arg):
        if ctx.message.author.id == id_dict['Owner']:
        # Check what servers bot is in
            guilds = list(self.bot.guilds)
            guild_names = '\n'.join(f"- {a.name}" for a in guilds)
            await ctx.send(f"Connected on {len(guilds)} servers:\n{guild_names}")

    @commands.command(aliases = ['scadd'])
    async def scnew(self, ctx, *arg):
        if ctx.message.author.id == id_dict['Owner']:
        # New shortcut into worksheet
            await ctx.send(general_utils.add_shortcut(*arg))

    @commands.command()
    async def sendmsg(self, ctx, *arg):
        if ctx.message.author.id == id_dict['Owner']:
        # Send customised message in specific channel
            try:
                channel = self.bot.get_channel(int(arg[0]))
                arg = arg[1:]
            except ValueError:
                channel = self.bot.get_channel(general_utils.get_shortcut(arg[0]))
                arg = arg[1:]
            if len(arg) == 0:
                msg = 'Hi.'
            else:
                msg = general_utils.msg_process(' '.join(arg))
            await channel.send(msg)

    @commands.command()
    async def delmsg(self, ctx, *arg):
        if ctx.message.author.id == id_dict['Owner']:
        # Delete specific message by the bot
            if len(arg) == 1:
                msg = await ctx.fetch_message(int(arg[0]))
            elif len(arg) == 2:
                try:
                    channel = self.bot.get_channel(int(arg[0]))
                except ValueError:
                    channel = self.bot.get_channel(general_utils.get_shortcut(arg[0]))
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
