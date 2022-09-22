import discord
import re
import pandas as pd
from datetime import datetime
from discord.ext import commands, tasks

from gsheet_handler import DfHandlerGen
from general_utils import GeneralUtils


mydtformat = '%Y/%m/%d %H:%M'
dfgen = DfHandlerGen()
general_utils = GeneralUtils(dfgen)


class BotLog():
    """An object to manage logging commands and responses."""
    def __init__(self, bot):
        """Registers associated bot."""
        self.owner = general_utils.owner
        self.token = general_utils.token
        self.bot = bot
        self.log_channel = self.bot.get_channel(general_utils.logs)

    async def log(self, message):
        """Extract message object elements to log the command used."""
        if self.log_channel == None:
            self.log_channel = self.bot.get_channel(general_utils.logs)
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
        self.syncpend = False
        self.cleanpend = False
        self.synccheck.start() # Off sync when debugging

    @tasks.loop(seconds=10.0)
    async def synccheck(self):
        """Check if tags DataFrame is pending to synchronise with google sheet.
        If yes, synchronises and returns result in the log channel or heroku logs.
        """
        if self.syncpend: # Check if sync is pending
            return_val = dfgen.sync_tags(self.cleanpend)
            if return_val == 1:
                self.syncpend = False
                self.cleanpend = False
                message = f"Synced success ({datetime.strftime(datetime.now(), mydtformat)})."
            else:
                message = f"Sync error: {return_val} ({datetime.strftime(datetime.now(), mydtformat)})."
            try:
                channel = self.bot.get_channel(general_utils.logs)
                await channel.send(message)
            except AttributeError:
                print(f"Sync_tags channel error. {message}.")

    @commands.command()
    async def sync(self, ctx):
        """(Owner only) Synchronise general sheets."""
        if ctx.message.author.id == general_utils.owner:
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
    async def tagtoggle(self, ctx, *arg):
        """(Owner only) Toggle tag commands to be enabled or disabled."""
        if ctx.message.author.id == general_utils.owner:
            if general_utils.tag_disabled:
                general_utils.tag_disabled = False
                await ctx.send('Tag commands are now enabled.')
            else:
                general_utils.tag_disabled = True
                await ctx.send('Tag commands are now temporarily disabled.')

    @commands.command()
    async def synctoggle(self, ctx, *arg):
        """(Owner only) Toggle tags to be automatically synchronised."""
        if ctx.message.author.id == general_utils.owner:
            if self.synccheck.is_running():
                self.synccheck.stop()
                await ctx.send('Tags are now temporarily desynchronised.')
            else:
                self.synccheck.start()
                await ctx.send('Tags synchronisation has now resumed.')

    @commands.command()
    async def tag(self, ctx, *arg):
        """Tag command to record tags with contents freely added by users."""
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group:
            try:
                await self.log.log(ctx.message)
                # If single tag is too long
            except discord.HTTPException:
                await self.log.send(ctx,
                    'Content is too long. Try to shorten it or separate into smaller tags.')
                return
            if len(arg) == 0:
                await self.log.send(ctx, general_utils.tag_help)
                return
            elif len(arg) == 1:
                keyword = arg[0].lower()
                df = dfgen.tags[dfgen.tags['Group'] == group]
                df = df[df['Tag'] == keyword]
                if len(df) == 0:
                    await self.log.send(ctx,
                        '`=tag keyword contents` to add contents first')
                else:
                    results = []
                    for _, row in df.iterrows():
                        results.append(f"`{row['Serial']}`: {row['Content']}")
                    # Check if total length exceeds limit
                    try:
                        await self.log.send(ctx, '\n'.join(results))
                    except discord.HTTPException:
                        # Prompt user to remove content and provide suggestions
                        await self.log.send(ctx,
                            f"Too much content. Try removing from {', '.join(df['Serial'].astype(str))}.")
            else:
                keyword = arg[0].lower()
                df = dfgen.tags[dfgen.tags['Group'] == group]
                # Find the new serial number
                if len(df):
                    serial = df['Serial'].max() + 1
                else:
                    serial = 1
                df_new = pd.DataFrame([{
                    'Tag': keyword,
                    'Content': ' '.join(arg[1:]),
                    'User': str(ctx.message.author.id),
                    'Serial': serial,
                    'Group': group,
                }])
                dfgen.tags = pd.concat([dfgen.tags, df_new])
                self.syncpend = True
                await self.log.send(ctx, f"Content added to tag {keyword}.")

    @commands.command(aliases=['tags'])
    async def tagserial(self, ctx, *arg):
        """Tag command to retrieve content from a particular serial number."""
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group:
            await self.log.log(ctx.message)
            if len(arg) == 0:
                await self.log.send(ctx, general_utils.tag_help)
                return
            elif not arg[0].isnumeric():
                await self.log.send(ctx, general_utils.tag_help)
                return
            else:
                serial = int(arg[0])
                df = dfgen.tags[dfgen.tags['Group'] == group]
                df_boolean = (df['Serial'] == serial) # Retrieve the tag
                if sum(df_boolean) == 0:
                    await self.log.send(ctx,
                        f"Tag {serial} does not exist.")
                else:
                    content = list(df[df_boolean]['Content'])[0]
                    await self.log.send(ctx, f"`{serial}`: {content}.")

    @commands.command(aliases=['newtags', 'newtag', 'tagrecent', 'recenttags'])
    async def tagnew(self, ctx, *arg):
        """Tag command to return tags recently used."""
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group:
            await self.log.log(ctx.message)
            df = dfgen.tags[dfgen.tags['Group'] == group]
            tags = df['Tag'].unique()
            end_num = 0
            try:
                start_num = int(arg[0])
                try:
                    int(arg[1]) # To check if there is a second number
                    end_num = start_num - 1
                    start_num = int(arg[1])
                except (IndexError, ValueError):
                    pass
            except (IndexError, ValueError):
                start_num = 10
            start_num = min(start_num, end_num + 50)
            if end_num == 0:
                heading = f"**Recent {start_num} tags:**"
                tags_line = ', '.join(tags[-start_num:])
            else:
                heading = f"**Recent {end_num + 1} ~ {start_num} tags:**"
                tags_line = ', '.join(tags[-start_num:-end_num])
            await self.log.send(ctx, '\n'.join((heading, tags_line)))

    @commands.command(aliases=['edittag'])
    async def tagedit(self, ctx, *arg):
        """
        Tag command to edit a tag content by serial number.
        """
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group:
            await self.log.log(ctx.message)
            if len(arg) < 2:
                await self.log.send(ctx, general_utils.tag_help)
                return
            elif not arg[0].isnumeric():
                await self.log.send(ctx, general_utils.tag_help)
                return
            else:
                serial = int(arg[0])
                df = dfgen.tags[dfgen.tags['Group'] == group]
                df_boolean = (df['Serial'] == serial) # Retrieve tag
                if sum(df_boolean) == 0:
                    await self.log.send(ctx,
                        f"Tag {serial} does not exist.")
                else:
                    dfgen.tags.loc[df_boolean[df_boolean].index, 'Content'] = ' '.join(arg[1:])
                    self.syncpend = True
                    await self.log.send(ctx,
                                        f"Content in tag `{serial}` edited.")

    @commands.command(aliases=['removetag', 'tagdelete'])
    async def tagremove(self, ctx, *arg):
        """
        Tag command to remove a tag content by serial number.
        """
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group:
            await self.log.log(ctx.message)
            if len(arg) == 0:
                await self.log.send(ctx, general_utils.tag_help)
                return
            elif not arg[0].isnumeric():
                await self.log.send(ctx, general_utils.tag_help)
                return
            else:
                serial = int(arg[0])
                df = dfgen.tags[dfgen.tags['Group'] == group]
                df_boolean = (df['Serial'] == serial)
                if sum(df_boolean) == 0:
                    await self.log.send(ctx,
                        f"Tag {serial} does not exist.")
                else:
                    dfgen.tags = dfgen.tags.drop(df_boolean[df_boolean].index)
                    self.cleanpend = True
                    self.syncpend = True
                    await self.log.send(ctx,
                                        f"Content removed from tag `{serial}`.")

    @commands.command(aliases=['resettag'])
    async def tagreset(self, ctx, *arg):
        """
        (Owner only) Tag command to remove contents from a tag.
        """
        if general_utils.tag_disabled:
            await ctx.send('Tag commands are currently temporarily disabled.')
            return
        group = general_utils.get_group(ctx)
        if group and ctx.message.author.id == general_utils.owner:
            await self.log.log(ctx.message)
            if len(arg) == 0:
                await self.log.send(ctx, general_utils.tag_help)
                return
            else:
                keyword = ' '.join(arg).lower()
                df = dfgen.tags[dfgen.tags['Group'] == group]
                df_boolean = (dfgen.tags['Tag'] == keyword)
                if sum(df_boolean) == 0:
                    await self.log.send(ctx,
                        f"Tag {keyword} has no contents.")
                else:
                    dfgen.tags = dfgen.tags.drop(df_boolean[df_boolean].index)
                    self.cleanpend = True
                    self.syncpend = True
                    await self.log.send(ctx,
                                        f"Contents removed from tag {keyword}.")

    @commands.command()
    async def checkservers(self, ctx, *arg):
        """(Owner only) Check what servers bot is in."""
        if ctx.message.author.id == general_utils.owner:
            guilds = list(self.bot.guilds)
            guild_names = '\n'.join(f"- {a.name}" for a in guilds)
            await ctx.send(
                f"Connected on {len(guilds)} servers:\n{guild_names}")

    @commands.command(aliases = ['scadd'])
    async def scnew(self, ctx, *arg):
        """(Owner only) Add new shortcut."""
        if ctx.message.author.id == general_utils.owner:
            await ctx.send(general_utils.add_shortcut(*arg))

    @commands.command()
    async def sendmsg(self, ctx, *arg):
        """(Owner only) Send custom message in specific channel."""
        if ctx.message.author.id == general_utils.owner:
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
        if ctx.message.author.id == general_utils.owner:
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
