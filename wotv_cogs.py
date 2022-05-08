import discord
import random
import itertools
import pandas as pd
from discord.ext import commands, tasks
from datetime import datetime

from gsheet_handler import DfHandlerWotv
from wotv_utils import WotvUtils
from id_dict import id_dict

dfwotv = DfHandlerWotv()
wotv_utils = WotvUtils(dfwotv, id_dict)
mydtformat = '%Y/%m/%d %H:%M'
printdtformat = '%b %d, %H:%M'


class WotvGeneral(commands.Cog):
    """Discord cog with WOTV general commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log
        self.bot.remove_command('help')
        self.newscheck.start()

    @tasks.loop(minutes=1.0)
    async def newscheck(self):
        """Checks for news every minute and post to designated channels."""
        soup = wotv_utils.get_news()
        articles = soup.find_all("article")
        id_list = []
        news_list = []
        for article in articles:
            if article['data-id'] not in wotv_utils.news_entries.union(id_list):
                id_list.append(article['data-id'])
                news_list.append((
                    article['data-id'],
                    article.find('time').text.strip(' \n\t'),
                    article.find('h2').text
                ))
        if len(news_list) > 0:
            wotv_utils.news_entries = [
                article['data-id'] for article in articles]
            for channel_id in dfwotv.ids['WOTV Newsfeed']:
                await self.bot.get_channel(channel_id).send('\n'.join([
                    f":newspaper: {news[1]} - {news[2]} - <https://players.wotvffbe.com/{news[0]}/>" for news in news_list
                ]))

    @commands.command()
    async def wotvsync(self, ctx, *arg):
        """(Owner only) Synchronise WOTV sheets."""
        if ctx.message.author.id == id_dict['Owner']:
            if len(arg) == 0:
                # Synchronise WOTV sheets
                dfwotv.sync()
                await ctx.send('Google sheet synced for WOTV data.')
            elif arg[0] == 'text':
                wotv_utils.update_text()
                await ctx.send('Text updated. (If Google sheet is updated.)')
            elif arg[0] == 'esper':
                # Update the set of effects per column in Esper
                wotv_utils.dicts['esper_sets'] = \
                    wotv_utils.esper_sets(dfwotv.esper)
                await ctx.send('Esper keyword sets updated.')
            elif arg[0] == 'events':
                dfwotv.sync_events()
                await ctx.send('Google sheet synced for WOTV events.')

    @commands.command(aliases=['help', 'about', 'info', 'aboutme', 'readme'])
    async def wotvhelp(self, ctx, *arg):
        """Customised help command."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed.title = 'Ildyra Bot Help'
        help_tuples = wotv_utils.help_general
        if len(arg) > 0:
            if arg[0].lower() == 'vc':
                help_tuples = wotv_utils.help_vc
            elif arg[0].lower() == 'esper':
                help_tuples = wotv_utils.help_esper
            elif arg[0].lower() == 'eq':
                help_tuples = wotv_utils.help_eq
            elif arg[0].lower() == 'param':
                help_tuples = wotv_utils.help_param
            elif arg[0].lower() in ('stars', 'ramada', 'moore'):
                help_tuples = wotv_utils.help_ramada
            elif arg[0].lower() == 'events':
                help_tuples = wotv_utils.help_events
            elif arg[0].lower() in ('engel', 'char', 'tamagotchi'):
                await self.log.send(ctx, 'The function is discontinued.')
                return
        for a, b in help_tuples:
            embed.add_field(name=a, value=b, inline=False)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['materia', 'rune', 'materias', 'runes'])
    async def wotvmaterias(self, ctx, *arg):
        """Command to call info regarding materias."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed.title = 'Ildyra Bot Help'
        materia_tuples = wotv_utils.materia_set
        if len(arg) > 0:
            if arg[0].lower() in ('substat', 'sub', 'substats', 's'):
                materia_tuples = wotv_utils.materia_substat
                for a, b in materia_tuples:
                    if a == 'General Info':
                        embed.description = b
                    else:
                        embed.add_field(name=a, value=b, inline=True)
                await self.log.send(ctx, embed=embed)
                return
            elif arg[0].lower() in ('passive', 'passives', 'recraft', 'p'):
                materia_tuples = wotv_utils.materia_passive
        for a, b in materia_tuples:
            embed.add_field(name=a, value=b, inline=False)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['addevent'])
    async def wotvaddevent(self, ctx, *arg):
        """Add event to calendar for authorized people."""
        await self.log.log(ctx.message)
        if ctx.message.author.id in dfwotv.ids['WOTV Events']:
            try:
                # Parse arguments.
                arg = [a.strip() for a in ' '.join(arg).split('|')]
                eventstr = arg[0]
                eventstart = datetime.strptime(arg[1], mydtformat)
                if len(arg) == 2:
                    eventend = eventstart
                    arg = (*arg, arg[1])
                else:
                    eventend = datetime.strptime(arg[2], mydtformat)
                # Check end time is later than start time.
                if eventstart <= eventend:
                    dfwotv.add_event(arg)
                    await self.log.send(ctx, 'Event added.')
                else:
                    await self.log.send(ctx,
                        'Ending time must be later than starting time.')
            except (IndexError, ValueError):
                await self.log.send(ctx, 'Incorrect format.')
        else:
            await self.log.send(ctx, 'Permission denied.')

    @commands.command(aliases=['events', 'calendar', 'timer', 'countdown',
                               'date'])
    async def wotvevents(self, ctx, *arg):
        """Check ongoing or upcoming events."""
        await self.log.log(ctx.message)
        dt_bool = 0
        sp_bool = 0
        if len(arg) > 0:
            if arg[0] in ('date', 'time', 'upcoming',
                'up-coming', 'ongoing', 'on-going'):
                dt_bool = 1
            elif arg[0] in ('embed', 'format'):
                dt_bool = 2
        events = {
            'on-going': [],
            'up-coming': []
        }
        # Goes through the dataframe
        for _, row in dfwotv.events.iterrows():
            if datetime.now() <= datetime.strptime(row['End'], mydtformat):
                # Search keyword to decide on the emote prefix.
                eventprefix = ':calendar:'
                for event_keywords, event_emote in \
                        wotv_utils.dicts['event_tuples']:
                    for event_keyword in event_keywords:
                        if event_keyword in row['Event'].lower():
                            eventprefix = \
                                wotv_utils.dicts['emotes'][event_emote]
                            break
                    if eventprefix != ':calendar:':
                        break
                eventname = f"{eventprefix} {row['Event']}"
                # Check if it is up-coming or on-going.
                if datetime.now() < \
                        datetime.strptime(row['Start'], mydtformat):
                    events['up-coming'].append((
                        eventname,
                        datetime.strptime(row['Start'], mydtformat),
                        datetime.strptime(row['End'], mydtformat),
                    ))
                elif datetime.now() <= \
                        datetime.strptime(row['End'], mydtformat):
                    events['on-going'].append((
                        eventname,
                        datetime.strptime(row['Start'], mydtformat),
                        datetime.strptime(row['End'], mydtformat),
                    ))
        events['on-going'].sort(key=lambda a: a[2])
        events['up-coming'].sort(key=lambda a: a[1])
        if dt_bool == 2:
            # Generate reply embed.
            embed = discord.Embed(
                colour = wotv_utils.dicts['embed']['default_colour']
            )
            embed.title = 'WOTV JP Calendar'
            for k, v in events.items():
                if len(v) == 0:
                    continue
                namelist = []
                startlist = []
                endlist = []
                event_count = 0
                for eventname, eventstart, eventend in v:
                    event_count += 1
                    namelist.append(eventname)
                    startlist.append(datetime.strftime(
                        eventstart, printdtformat))
                    endlist.append(datetime.strftime(
                        eventend, printdtformat))
                    # Add new field every 10 counts for character limit.
                    if event_count == 10:
                        embed.add_field(name=k.capitalize(),
                                        value='\n'.join(namelist))
                        embed.add_field(name='Start',
                                        value='\n'.join(startlist))
                        embed.add_field(name='End', value='\n'.join(endlist))
                        namelist = []
                        startlist = []
                        endlist = []
                        event_count = 0
                if event_count > 0:
                    embed.add_field(name=k.capitalize(),
                                    value='\n'.join(namelist))
                    embed.add_field(name='Start', value='\n'.join(startlist))
                    embed.add_field(name='End', value='\n'.join(endlist))
            await self.log.send(ctx, embed=embed)
        else:
            # Generate reply string.
            replystr_list = ['']
            for k, v in events.items():
                if len(replystr_list) > 1:
                    replystr_list.append('\n\n')
                if len(v) == 0:
                    replystr_list.append(f"*No {k} events.*")
                else:
                    replystr_list.append(f"**{k.capitalize()} Events**")
                    for event in v:
                        if dt_bool == 1:
                            eventstart = datetime.strftime(
                                event[1], printdtformat)
                            eventend = datetime.strftime(
                                event[2], printdtformat)
                            replystr_list.append(''.join((
                                f"\n{event[0]} - ",
                                f"`{eventstart}` to `{eventend}`")))
                        else:
                            replystr_list.append(f"\n{event[0]} -")
                            if k == 'on-going':
                                eventdd = event[2] - datetime.now()
                            else:
                                eventdd = event[1] - datetime.now()
                            eventddsplit = (
                                ('day', eventdd.days),
                                ('hour', eventdd.seconds // 3600),
                                ('minute', eventdd.seconds % 3600 // 60)
                            )
                            for eventddstr, eventddnum in eventddsplit:
                                if eventddnum > 1:
                                    replystr_list.append(
                                        f" `{eventddnum} {eventddstr}s`")
                                elif eventddnum == 1:
                                    replystr_list.append(
                                        f" `{eventddnum} {eventddstr}`")
                        replystr = ''.join(replystr_list)
                        if len(replystr) > 1800:
                            await self.log.send(ctx, replystr)
                            replystr_list = ['(Cont.)']
            if len(replystr_list) > 1:
                await self.log.send(ctx, ''.join(replystr_list))

    @commands.command(aliases=['rand', 'random', 'choice'])
    async def wotvrand(self, ctx, *arg):
        """Fluff command to pick a number or string from users."""
        await self.log.log(ctx.message)
        embed = discord.Embed()
        # Check command is called in a FFBE server.
        if ctx.guild.id in dfwotv.ids['FFBE Server']:
            ffbe = 1
        else:
            ffbe = 0
        npctup = wotv_utils.rand(ffbe, *arg)
        embed.title = f"Random {npctup[1]}"
        embed.colour = wotv_utils.dicts['colours'][npctup[2]]
        embed.set_thumbnail(url=npctup[3])
        if npctup[0]:
            embed.description = '\n'.join((
                f"{npctup[4]} Give us either:",
                "- one or two numbers",
                "- two or more choices"))
        else:
            embed.description = npctup[4]
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['fortune', 'stars', 'ramada', 'moore'])
    async def wotvramada(self, ctx, *arg):
        """Fluff command to read fortune."""
        await self.log.log(ctx.message)
        # Check if Moore or Ramada is specified.
        reader = ctx.message.content.lstrip('=+').split()[0]
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        fortunestr, fortunetitle, fortuneurl = wotv_utils.ramada(reader)
        embed.title = fortunetitle
        embed.description = fortunestr
        embed.set_thumbnail(url=fortuneurl)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['changelog', 'version'])
    async def wotvchangelog(self, ctx, *arg):
        """Return recent changelogs."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed.title = 'Ildyra Bot Changelog'
        try:
            entry_num = int(arg[0])
        except IndexError:
            entry_num = 3
        num = 0
        for _, row in dfwotv.text[dfwotv.text['Key'] == 'changelog'].iterrows():
            if num == entry_num:
                break
            embed.add_field(name=row['Title'], value=row['Body'], inline=False)
            num += 1
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['weekly', 'week', 'day', 'weekday', 'daily'])
    async def wotvweekly(self, ctx, *arg):
        """Reply pre-set message of day of the week bonuses."""
        await self.log.log(ctx.message)
        await self.log.send(ctx, wotv_utils.weekly)

    @commands.command(aliases=['news'])
    async def wotvnews(self, ctx, *arg):
        """Reply pre-set link to news."""
        await self.log.log(ctx.message)
        if len(arg) > 0:
            if arg[0].lower() == 'gl':
                news_str = 'https://site.na.wotvffbe.com//whatsnew'
            else:
                news_str = '\n'.join(('https://site.wotvffbe.com//whatsnew',
                                      '<https://players.wotvffbe.com/>'))
        else:
            news_str = '\n'.join(('https://site.wotvffbe.com//whatsnew',
                                '<https://players.wotvffbe.com/>'))
        await self.log.send(ctx, news_str)

    @commands.command(aliases=['param', 'acc', 'eva', 'crit', 'params'])
    async def wotvparam(self, ctx, *arg):
        """Calculate acc, eva, crit and crit avoid from
        dex, agi, luck and equipment stats.
        """
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help param`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        params = {k: v[0] for k, v in wotv_utils.dicts['paramcalc'].items()}
        args = ' '.join(arg)
        embed.title = args
        # Convert arg list to split with | instead.
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number.
            re_match = wotv_utils.revalues.search(argstr)
            try:
                paramval = int(re_match.group())
                paramstr = argstr[0:re_match.start()].strip()
                for k, v in wotv_utils.dicts['paramcalc'].items():
                    if paramstr in v[1]:
                        if k not in ('agi', 'dex', 'luck') or paramval >= 0:
                            # Disallow negative values for the three stats.
                            params[k] = paramval
                        break
            except AttributeError:
                pass
        # Actual calculations.
        results = (
            ('ACC', (11*params['dex']**0.2/20 + params['luck']**0.96/200
                - 1)*100 + params['acc']),
            ('EVA', (11*params['agi']**0.9/1000 + params['luck']**0.96/200
                - 1)*100 + params['eva']),
            ('CRIT', (params['dex']**0.35/4 - 1) * 100 + params['crit']),
            ('C.AVO', (params['luck']**0.37/5 - 1) * 100 + params['c.avo'])
        )
        # Present results.
        embed.add_field(name='Inputs', value='\n'.join([
            f"`{k.upper(): <5}` {v}" for k, v in params.items()]), inline=True)
        embed.add_field(name='Results', value='\n'.join([
            f"`{k: <5}` {v: .1f}%" for k, v in results]), inline=True)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=[
        'engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp',
        'engelrep', 'petrep', 'tamagotchirep', 'tamarep', 'charrep',
        'engel', 'pet', 'tamagotchi', 'tama', 'char',
        'engelberthelp', 'engelbertrepeat', 'engelbert',
        ])
    async def wotv_discontinued(self, ctx, *arg):
        """Function to respond that the corresponding functionality has
        already been discontinued.
        """
        await self.log.log(ctx.message)
        await self.log.send(ctx, 'The pet function has been discontinued.')


class WotvEquipment(commands.Cog):
    """Discord cog with WOTV equipment commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['we', 'eq', 'equipment', 'Eq', 'Equipment'])
    async def wotveq(self, ctx, *arg):
        """General equipment search command, has multiple modes
        depending on inputs.
        """
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help eq`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        # Find the specific equipment.
        rowfound, row = wotv_utils.find_row(dfwotv.eq, arg)
        if rowfound == 0:
            # Not found.
            if row == '':
                # Second chance to find by potential character name
                rowfound, row = wotv_utils.find_row(dfwotv.eq, arg[0].rstrip("'s"))
                if rowfound == 0:
                    embed.title = ' '.join(arg)
                    embed.description = ''.join((
                        'No match found. ',
                        'Or did you mean to use `=es` or `=el`?'))
            else:
                embed.title = ' '.join(arg)
                embed.description = ''.join((
                    'Too many results. ',
                    'Please try the following:\n',
                    row))
        if rowfound:
            # Process equipment info.
            embed.title = row.name
            description_list = [f"{wotv_utils.name_str(row, name='', alias=2)}"]
            eff_list = []
            if row['Condition'] != '':
                description_list.append(f"*Restriction: {row['Condition']}*")
            condition = ''
            for eff in row['Special'].split(' / '):
                match_brackets = wotv_utils.reconditions.findall(eff)
                if len(match_brackets) == 1:
                    condition = match_brackets[0]
                    eff_list.append(eff)
                elif condition == '':
                    eff_list.append(eff)
                else:
                    eff_list.append(f"{condition} {eff}")
            description_list.extend(eff_list)
            if row['Extra'] != '':
                description_list.append(f"{wotv_utils.dicts['emotes']['heartquartzs']} {row['Extra']}")
            embed.description = '\n'.join(description_list)
            embed.add_field(name='Acquisition', value=row['Acquisition'],
                            inline=True)
            # Craft materials.
            embed_text_list = []
            for col in ['Regular', 'Rare', 'Cryst', 'Ore']:
                if row[col] != '':
                    if col == 'Cryst':
                        embed_text_list.append(wotv_utils.get_cryst(row))
                    else:
                        engstr = dfwotv.mat.loc[row[col]]['Aliases'] \
                            .split(' / ')[0]
                        embed_text_list.append(
                            f"- {row[col]} ({engstr})")
            embed.add_field(name='List of materials',
                            value='\n'.join(embed_text_list),
                            inline=True)
            if row['Url'] != '':
                embed.set_thumbnail(url=row['Url'])
            if row['English'] != '':
                embed.add_field(
                    name='WOTV-CALC',
                    value=wotv_utils.calc_url('equipment', row['English']),
                    inline=False)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['wel', 'eql', 'el', 'El'])
    async def wotveqlist(self, ctx, *arg):
        """Search equipment by type, acquisition, material,
        upgradeable with heartquartzs.
        """
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help eq`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        eq_str_list = []
        result_type = 1
        if arg[0].lower() in {'list', 'l'}:
            result_type = 0
            if len(arg) == 1:
                # Print list of lists.
                embed.title = f"List of lists"
                embed.description = '\n'.join(
                    wotv_utils.dicts['eq_lists'].keys())
            else:
                # Print list of searchable items in the column.
                argstr = ' '.join(arg[1:]).lower()
                rowfound = 0
                for k, v in wotv_utils.dicts['eq_lists'].items():
                    if argstr in v or argstr == k.lower():
                        argstr = k
                        rowfound = 1
                        break
                if rowfound:
                    embed.title = f"List of {argstr}s"
                    text_list = list(wotv_utils.dicts['mat_sets'][argstr])
                    if argstr not in ['Type', 'Acquisition']:
                        text_list = [''.join((f"{a} (",
                            f"{dfwotv.mat.loc[a]['Aliases'].split(' / ')[0]})"\
                            )) for a in text_list]
                    embed.description = '\n'.join(text_list)
                else:
                    # No match. Print list of lists.
                    embed.title = f"List of lists"
                    embed.description = '\n'.join(
                        wotv_utils.dicts['eq_lists'].keys())
        elif arg[0].lower() in ['hq', 'heartquartzs', '+6']:
            rows = dfwotv.eq[dfwotv.eq['Extra'] != '']
            for index, row in rows.iterrows():
                eq_str_list.append(f"{wotv_utils.name_str(row, name='', alias=2)} - {row['Special']} {wotv_utils.dicts['emotes']['heartquartzs']} {row['Extra']}")
        # Check if type search
        elif arg[0].lower() in ['type', 't', 'acquisition', 'a'] \
                and len(arg) > 1:
            if arg[0].lower() in ['type', 't']:
                colstr = 'Type'
            else:
                colstr = 'Acquisition'
            # Process query
            argstr = ' '.join(arg[1:])
            embed.title = argstr
            argstr = argstr.lower()
            for index, row in dfwotv.eq_type.iterrows():
                argstr = argstr.replace(index, row['VC'])
            # Find eq that match and add to the list
            for index, row in dfwotv.eq.iterrows():
                if argstr in row[colstr].lower():
                    eq_str_list.append(f"{wotv_utils.name_str(row, name='', alias=2)} - {row['Special']}")
        else:
            # Material search
            if arg[0].lower() in {'m', 'mat', 'material'} and len(arg) > 1:
                argstr = ' '.join(arg[1:])
            else:
                argstr = ' '.join(arg)
            matstr = ('',)
            rowfound, row = wotv_utils.find_row(dfwotv.mat, arg)
            if rowfound:
                # Print all eq that use said materials.
                matstr = (row.name, row['Type'], row['Aliases'].split(' / ')[0])
                embed.title = f"Recipes w/ {matstr[2]}"
                for index, row in dfwotv.eq.iterrows():
                    if row[matstr[1]] == matstr[0] or (matstr[1] == 'Cryst' \
                            and matstr[0] in row[matstr[1]]):
                        eq_str_list.append(f"{wotv_utils.name_str(row, name='', alias=2)} - {row['Special']}")
        if result_type and len(eq_str_list) > 0:
            field_value = '\n'.join(eq_str_list)
            checkpoint_list = [0]
            # Split if too long.
            if len(field_value) > 1020:
                field_value_length = -2
                for i, field_entry in enumerate(eq_str_list):
                    field_value_length += len(field_entry) + 2
                    if field_value_length > 1000:
                        field_value_length = len(field_entry)
                        checkpoint_list.append(i)
            for i, checkpoint in enumerate(checkpoint_list, start=1):
                if checkpoint == 0:
                    field_name = 'Equipment'
                else:
                    field_name = 'Equipment (cont.)'
                if i == len(checkpoint_list):
                    field_value = '\n'.join(eq_str_list[checkpoint:])
                else:
                    field_value = '\n'.join(
                        eq_str_list[checkpoint:checkpoint_list[i]])
                embed.add_field(name=field_name, value=field_value, inline=True)
                if i % 2 == 0:
                    embed.add_field(name='\u200b', value='\u200b', inline=True)
        elif result_type:
            embed.description = "Not found. Try checking with `=el l`."
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['wes', 'eqs', 'es', 'Es'])
    async def wotveqsearch(self, ctx, *arg):
        """Search equipment by effect."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help eq`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        if len(arg) == 1:
            # Check if it is a shortcut keyword.
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        embed.title = args.title()
        args = args.lower()
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        for k, v in wotv_utils.dicts['colours'].items():
            if k in args:
                embed.colour = v
                break
        # Search each equipment for their effects.
        eq_str_list = []
        for _, row in dfwotv.eq.iterrows():
            in_list = 0
            eff_list = row['Special'].split(' / ')
            for eff in eff_list:
                if args in eff.lower():
                    eq_str_list.append(f"{wotv_utils.name_str(row, name='', alias=2)} - {row['Special']}")
                    break
            if not in_list:
                if args in row['Extra'].lower():
                    eq_str_list.append(f"{wotv_utils.name_str(row, name='', alias=2)} - {row['Special']} {wotv_utils.dicts['emotes']['heartquartzs']} {row['Extra']}")
        field_value = '\n'.join(eq_str_list)
        checkpoint_list = [0]
        # Split if too long.
        if len(field_value) > 1020:
            field_value_length = -2
            for i, field_entry in enumerate(eq_str_list):
                field_value_length += len(field_entry) + 2
                if field_value_length > 1000:
                    field_value_length = len(field_entry)
                    checkpoint_list.append(i)
        for i, checkpoint in enumerate(checkpoint_list, start=1):
            if checkpoint == 0:
                field_name = 'Equipment'
            else:
                field_name = 'Equipment (cont.)'
            if i == len(checkpoint_list):
                field_value = '\n'.join(eq_str_list[checkpoint:])
            else:
                field_value = '\n'.join(
                    eq_str_list[checkpoint:checkpoint_list[i]])
            embed.add_field(name=field_name, value=field_value, inline=True)
            if i % 2 == 0:
                embed.add_field(name='\u200b', value='\u200b', inline=True)
        try:
            await self.log.send(ctx, embed=embed)
        except discord.HTTPException:
            await self.log.send(ctx,
                'Too many results. Please refine the search.')

class WotvVc(commands.Cog):
    """Discord cog with WOTV vision card commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['wvs', 'vcs', 'vs', 'VCS', 'Vcs'])
    async def wotvvcsearch(self, ctx, *arg):
        """Search vision cards by effect."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help vc`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        df = dfwotv.vc
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/cards',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        # Initialise empty lists.
        vc_dict_p_ur = {k: [] for k in wotv_utils.dicts['colours'].keys()}
        vc_dict_u_ur = {k: [] for k in wotv_utils.dicts['colours'].keys()}
        vc_dict_p = {k: [] for k in wotv_utils.dicts['colours'].keys()}
        vc_dict_u = {k: [] for k in wotv_utils.dicts['colours'].keys()}
        if len(arg) == 1:
            # Check if it is a shortcut keyword.
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        embed.title = args.title()
        args = args.lower()
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        # Search each VC.
        for _, row in df.iterrows():
            vc_ele = ''
            vc_party_list = []
            vc_unit_list = []
            for col in {'Party Max', 'Party', 'Unit'}:
                eff_list = row[col].split(' / ')
                # Default icon unless condition found.
                eff_prefix = []
                for eff in eff_list:
                    # Have to process the brackets first, because
                    # might match 2nd conditional effect.
                    new_effect = 1
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if len(match_brackets) == 1:
                        conditions = match_brackets[0] \
                                     .strip('[]').lower().split('/')
                        for condition in conditions:
                             # Remove previous conditions if new effect with conditions
                            if new_effect == 1:
                                eff_prefix = []
                                new_effect = 0
                            if condition in wotv_utils.dicts['colours'].keys():
                                eff_prefix.append(
                                    wotv_utils.dicts['emotes'][condition]
                                )
                                if vc_ele == '':
                                    vc_ele = condition
                                elif vc_ele != condition:
                                    vc_ele = 'neutral'
                            if len(eff_prefix) == 0:
                                eff_prefix = [match_brackets[0]]
                    if args in eff.lower():
                        eff_suffix = '' # Actual effect numbers.
                        match_numbers = wotv_utils.revalues.findall(eff)
                        universal = 0
                        if len(eff_prefix) == 0:
                            universal = 1
                            eff_prefix = [wotv_utils.dicts['emotes']['allele']]
                        if len(match_numbers) == 1:
                            eff_suffix = match_numbers[0]
                        if col == 'Unit':
                            vc_unit_list.append((
                                f"{''.join(eff_prefix)}{wotv_utils.name_str(row, name='')} - {eff_suffix}",
                                universal))
                        elif col == 'Party':
                            vc_party_list.append((
                                f"{''.join(eff_prefix)}{wotv_utils.name_str(row, name='')} - {eff_suffix}",
                                universal))
                        else: # Party Max
                            vc_party_list.append((
                                f"{''.join(eff_prefix)}{wotv_utils.name_str(row, name='')} - {wotv_utils.dicts['emotes']['vcmax']} {eff_suffix}",
                                universal))
            # Add entries to corresponding element and rarity
            if vc_ele == '' and row['Rarity'] == 'UR':
                vc_dict_p_ur['neutral'].extend([
                    vc_str for vc_str, _ in vc_party_list])
                vc_dict_u_ur['neutral'].extend([
                    vc_str for vc_str, _ in vc_unit_list])
            elif vc_ele == '':
                vc_dict_p['neutral'].extend([
                    vc_str for vc_str, _ in vc_party_list])
                vc_dict_u['neutral'].extend([
                    vc_str for vc_str, _ in vc_unit_list])
            elif row['Rarity'] == 'UR':
                vc_dict_p_ur[vc_ele].extend([
                    f"{vc_str} {wotv_utils.dicts['emotes'][vc_ele]}"
                    if universal else vc_str
                    for (vc_str, universal) in vc_party_list
                ])
                vc_dict_u_ur[vc_ele].extend([
                    f"{vc_str} {wotv_utils.dicts['emotes'][vc_ele]}"
                    if universal else vc_str
                    for (vc_str, universal) in vc_unit_list
                ])
            else:
                vc_dict_p[vc_ele].extend([
                    f"{vc_str} {wotv_utils.dicts['emotes'][vc_ele]}"
                    if universal else vc_str
                    for (vc_str, universal) in vc_party_list
                ])
                vc_dict_u[vc_ele].extend([
                    f"{vc_str} {wotv_utils.dicts['emotes'][vc_ele]}"
                    if universal else vc_str
                    for (vc_str, universal) in vc_unit_list
                ])
        # Combine entries of each element
        vc_party_str_list = list(itertools.chain.from_iterable([
            vc_str_list for _, vc_str_list in vc_dict_p_ur.items()] + [
            vc_str_list for _, vc_str_list in vc_dict_p.items()]))
        vc_unit_str_list = list(itertools.chain.from_iterable([
            vc_str_list for _, vc_str_list in vc_dict_u_ur.items()] + [
            vc_str_list for _, vc_str_list in vc_dict_u.items()]))
        # Print from each list if non-empty.
        empty_list = 1
        for k, v in (('Party', vc_party_str_list), ('Unit', vc_unit_str_list)):
            if len(v) > 0:
                empty_list = 0
                field_value = '\n'.join(v)
                if len(field_value) < 1020:
                    embed.add_field(name=k, value=field_value, inline=False)
                else:
                    # Split if too long.
                    checkpoint = 0
                    field_value_length = -2
                    field_name = k
                    for i, v_entry in enumerate(v):
                        field_value_length += len(v_entry) + 2
                        if field_value_length > 1000:
                            field_value = '\n'.join(v[checkpoint:i])
                            embed.add_field(name=field_name, value=field_value)
                            field_value_length = len(v_entry)
                            checkpoint = i
                            field_name = f"{k} (cont.)"
                    field_value = '\n'.join(v[checkpoint:])
                    embed.add_field(name=field_name, value=field_value)
        if empty_list:
            embed.description = ''.join((
                'No match found. Try checking `=help vc`. ',
                'Or did you mean to use `=vc`?'))
        # Fluff to change embed colour if requested effect is elemental.
        for k, v in wotv_utils.dicts['colours'].items():
            if k in args:
                embed.colour = v
                embed.add_field(name='Note:',
                    value=f"`=ve {k}` instead to list element-locked effects."
                )
                break
        try:
            await self.log.send(ctx, embed=embed)
        except discord.HTTPException:
            await self.log.send(ctx,
                'Too many results. Please refine the search.')

    @commands.command(aliases=['wve', 'vce', 've', 'VCE', 'Vce'])
    async def wotvvcelement(self, ctx, *arg):
        """Search vision cards by element."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help vc`.')
            return
        embed = discord.Embed()
        df = dfwotv.vc
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/cards',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        # Initialise empty lists.
        col_tuples = {
            'Party': '',
            'Party Max': wotv_utils.dicts['emotes']['vcmax']
        }
        effect_sort = 0
        if len(arg) > 1:
            if arg[0].lower() in {'s', 'sort'}:
                effect_sort = 1
                arg = arg[1:]
        ele = arg[0].lower().replace('lightning', 'thunder')
        try:
            embed.title = ' '.join((
                wotv_utils.dicts['emotes'][ele], arg[0].title()))
            embed.colour = wotv_utils.dicts['colours'][ele]
        except KeyError:
            embed.description = \
                'No element found. Or did you mean to use `=vs` or `=vc`?'
            await ctx.send(embed = embed)
            return
        # Search each VC.
        vc_tuples = []
        for index, row in df.iterrows():
            vc_eff_tuples = []
            for col, col_prefix in col_tuples.items():
                col_eff_list = row[col].split(' / ')
                eff_prefix = []
                ele_found = 0
                condition_found = 0
                for eff in col_eff_list:
                    new_effect = 1
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if len(match_brackets) == 1:
                        condition_found = 1
                        conditions = match_brackets[0] \
                                     .strip('[]').lower().split('/')
                        for condition in conditions:
                             # Remove previous conditions if new effect with conditions
                            if new_effect == 1:
                                eff_prefix = []
                                new_effect = 0
                                ele_found = 0
                            if condition == ele:
                                ele_found = 1
                            elif condition in \
                                    wotv_utils.dicts['colours'].keys():
                                eff_prefix.append(
                                    wotv_utils.dicts['emotes'][condition]
                                )
                            else:
                                eff_prefix.append(
                                    f"[{condition.title()}]"
                                )
                        eff_text = eff.replace(match_brackets[0], '').strip()
                    else:
                        eff_text = eff
                    if ele_found and len(eff_prefix) > 0:
                        final_prefix = f"{''.join(eff_prefix)} "
                    elif not condition_found:
                        final_prefix = f"{wotv_utils.dicts['emotes']['allele']} "
                    else:
                        final_prefix = ''
                    vc_eff_tuples.append((
                        f"{wotv_utils.name_str(row, name='')} - {col_prefix}{final_prefix}",
                        eff_text
                    ))
            if ele_found:
                vc_tuples.extend(vc_eff_tuples)
        # Print while keeping track of characters.
        if effect_sort == 1:
            vc_tuples = sorted(vc_tuples, key=lambda tup: tup[1])
        vc_str_list = [''.join([a, b]) for a, b in vc_tuples]
        field_value = '\n'.join(vc_str_list)
        if len(field_value) < 1020:
            embed.add_field(name='\u200b', value=field_value, inline=False)
        else:
            # Split if too long.
            field_num = 0
            checkpoint = 0
            field_value_length = -2
            for i, vc_str in enumerate(vc_str_list):
                field_value_length += len(vc_str) + 2
                if field_value_length > 1000:
                    field_value = '\n'.join(vc_str_list[checkpoint:i])
                    embed.add_field(name='\u200b', value=field_value,
                                    inline=True)
                    field_num += 1
                    if field_num % 2 == 0:
                        embed.add_field(name='\u200b', value='\u200b',
                                        inline=True)
                    field_value_length = len(vc_str)
                    checkpoint = i
            field_value = '\n'.join(vc_str_list[checkpoint:])
            embed.add_field(name='\u200b', value=field_value, inline=True)
            field_num += 1
            if field_num % 2 == 0:
                embed.add_field(name='\u200b', value='\u200b', inline=True)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['wv', 'vc', 'VC', 'Vc'])
    async def wotvvc(self, ctx, *arg):
        """Search vision card by name."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help vc`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        df = dfwotv.vc
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/cards',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        rowfound, row = wotv_utils.find_row(df, arg)
        if rowfound == 0:
            if row == '':
                embed.title = ' '.join(arg)
                embed.description = \
                    'No match found. Or did you mean to use `=vs` or `=ve`?'
            else:
                embed.title = ' '.join(arg)
                embed.description = '\n'.join((
                    'Too many results. Please try the following:', row))
        else:
            embed.title = wotv_utils.name_str(row, alias=0)
            embed_colours = []
            for col in ('Unit', 'Party', 'Party Max', 'Skill'):
                if row[col] == '':
                    continue
                eff_list = row[col].split(' / ')
                eff_list_processed = []
                eff_prefix = []
                for eff in eff_list:
                    new_effect = 1
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if len(match_brackets) == 1:
                        conditions = match_brackets[0] \
                                     .strip('[]').lower().split('/')
                        for condition in conditions:
                             # Remove previous conditions if new effect with conditions
                            if new_effect == 1:
                                eff_prefix = []
                                new_effect = 0
                            if condition in wotv_utils.dicts['colours'].keys():
                                eff_prefix.append(
                                    wotv_utils.dicts['emotes'][condition]
                                )
                                embed_colours.append(
                                    wotv_utils.dicts['colours'][condition]
                                )
                            if len(eff_prefix) == 0:
                                eff_prefix = [match_brackets[0]]
                        eff_text = eff.replace(match_brackets[0], '').strip()
                    else:
                        eff_text = eff
                    eff_list_processed.append(
                        f"{' '.join(eff_prefix)} {eff_text}"
                    )
                field_value = '\n'.join(eff_list_processed)
                embed.add_field(name=col, value=field_value)
            if row['Url'] != '':
                embed.set_thumbnail(url=row['Url'])
            if len(embed_colours) > 0:
                embed.colour = random.choice(embed_colours)
            if row['English'] != '':
                embed.add_field(
                    name='WOTV-CALC',
                    value=wotv_utils.calc_url('card', row['English']),
                    inline=False)
        await self.log.send(ctx, embed=embed)


class WotvEsper(commands.Cog):
    """Discord cog with WOTV esper commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['magicite', 'magicites', 'espermagicite'])
    async def wotvmagicite(self, ctx, *arg):
        """Calculate required amount of magicites from inputs."""
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help esper`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        magicites = {k: 0 for k in wotv_utils.dicts['magicites'].keys()}
        esper_start = 1
        bonus = 100
        neutral = 0
        args = ' '.join(arg)
        embed.title = args
        # Convert arg list to split with | instead.
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number.
            if argstr == 'neutral':
                neutral = 1
                continue
            re_match = wotv_utils.revalues.search(argstr.rstrip('%'))
            try:
                paramval = int(re_match.group())
                paramstr = argstr[0:re_match.start()].strip()
                if paramstr in ('star', 'stars') and paramval in (1, 2, 3):
                    esper_start = paramval
                elif paramstr in ('bonus',) and 0 <= paramval <= 100:
                    bonus = paramval
                else:
                    for k in wotv_utils.dicts['magicites'].keys():
                        if paramstr == k.lower():
                            magicites[k] = max(paramval, 0)
                            break
            except AttributeError:
                pass
        # Actual calculations.
        req_exp = sum([wotv_utils.dicts['esper_exp'][a] for a in \
            range(esper_start, 4, 1)])
        total_exp = 0
        for k, v in magicites.items():
            if neutral:
                total_exp += int(v * wotv_utils.dicts['magicites'][k]
                                 * (100+bonus) / 100 * 0.75)
            else:
                total_exp += (v * wotv_utils.dicts['magicites'][k]
                              * int((100+bonus) / 100))
        if neutral:
            xl_exp = (wotv_utils.dicts['magicites']['XL'] * (100+bonus) / 100
                      * 0.75)
        else:
            xl_exp = wotv_utils.dicts['magicites']['XL'] * (100+bonus) / 100
        # Present results.
        field_list = [
            f"Starting from `{esper_start}-star`",
            f"Bonus: `{bonus}%`",
        ] + [f"{k} Magicites: `{v}`" for k, v in magicites.items()]
        if neutral:
            field_list.append('Neutral Esper')
        embed.add_field(name='Inputs', value='\n'.join(field_list),
                        inline=True)
        field_list = [
            f"Required EXP: `{req_exp}` (`{req_exp / xl_exp:.1f}` XL)",
            f"Total EXP: `{total_exp}` (`{total_exp / xl_exp:.1f}` XL)",
        ]
        if total_exp > req_exp:
            field_list.append(''.join(('Enough with leftovers of ',
                f"`{(total_exp - req_exp) / xl_exp:.1f}` XL.")))
        elif req_exp > total_exp:
            field_list.append(''.join(('Insufficient of ',
                f"`{(req_exp - total_exp) / xl_exp:.1f}` XL.")))
        embed.add_field(name='Results', value='\n'.join(field_list),
                        inline=True)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['esper', 'Esper', 'espers', 'Espers'])
    async def wotvesper(self, ctx, *arg):
        """General esper search command, has multiple modes
        depending on inputs.
        """
        await self.log.log(ctx.message)
        if len(arg) == 0:
            await self.log.send(ctx, 'Try `=help esper`.')
            return
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/espers',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        df = dfwotv.esper
        # Check arguments
        if arg[0] in {'m', 'mobile'}:
            mobile_bool = 1
            arg = arg[1:]
        else:
            mobile_bool = 0
        if arg[0] in {'sort', 's', 'rank', 'r', 'filter', 'f'} and \
                len(arg) > 1:
            # Ranking mode
            if mobile_bool == 0 and arg[1] in ['m', 'mobile']:
                mobile_bool = 1
                args = ' '.join(arg[2:])
            else:
                args = ' '.join(arg[1:])
            embed.title = args
            # convert arg list to split with | instead
            arg = [a.lower().strip() for a in args.split('|')]
            # Check for shortcuts or replacements
            for i, argstr in enumerate(arg):
                if len(argstr.split()) == 1:
                    arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
                for index, row in dfwotv.replace.iterrows():
                    arg[i] = arg[i].replace(index, row['VC'])
            # Function to find which column the said effect should be
            while len(arg) > 0:
                col, first_arg = wotv_utils.esper_findcol(arg[0])
                if col == 'NOTFOUND':
                    arg = arg[1:]
                else:
                    break
            if col == 'NOTFOUND':
                embed.description = \
                    'Esper effect not found or ambiguous. Try `=help esper`.'
            else:
                if first_arg == 'STAT':
                    row_df = df.nlargest(20, col)
                else:
                    row_df = df[df[col].str.lower().str.contains(first_arg)]
                if first_arg in ('y', 'n'):
                    arg = arg[1:]
                if len(arg) > 2:
                    # Force into mobile mode otherwise can't fit
                    mobile_bool = 1
                tuples_list = []
                if len(arg) > 0:
                    for argstr in arg:
                        if argstr.upper() in wotv_utils.dicts['esper_stats']:
                            tuples_list.append((argstr.upper(), 'STAT'))
                        else:
                            tup = wotv_utils.esper_findcol(argstr)
                            if tup[0] != 'NOTFOUND':
                                tuples_list.append(tup)
                list_lists = []
                for index, row in row_df.iterrows():
                    # Initialise for each row with only name.
                    filter_state = 0 # 0: First argument
                    row_list = [index]
                    for tupcol, tuparg in tuples_list:
                        # Find value and add to row list.
                        if tuparg == 'STAT':
                            row_list.append(str(row[tupcol]))
                            filter_state = 1
                        elif tuparg in row[tupcol].lower():
                            eff_list = row[tupcol].split(' / ')
                            for eff in eff_list:
                                if tuparg in eff.lower():
                                    re_match = wotv_utils.revalues.findall(eff)
                                    row_list.append(re_match[0])
                                    break
                            # To filter accuracy/evasion 7
                            if tuparg in 'accuracy' or tuparg in 'evasion':
                                if filter_state == 0:
                                    if int(re_match[0]) < 8:
                                        filter_state = 2
                                        break
                            filter_state = 1
                        else:
                            row_list.append('-')
                    if filter_state == 1:
                        list_lists.append(row_list)
                # Sort list
                if first_arg not in {'y', 'n'}:
                    list_lists.sort(key=lambda a: int(a[1]), reverse=True)
                # Print based on display mode
                if mobile_bool:
                    for row_list in list_lists:
                        field_name = \
                            wotv_utils.name_str(row_df.loc[row_list[0]])
                        field_list = []
                        for argname, argvalue in zip(arg, row_list[1:]):
                            if argvalue != '-':
                                field_list.append(
                                    f"**{argname.title()}**: {argvalue}")
                        embed.add_field(name=field_name,
                                        value='\n'.join(field_list),
                                        inline=False)
                elif len(list_lists) > 0:
                    transpose_list = list(map(list, zip(*list_lists)))
                    esper_list = [wotv_utils.name_str(row_df.loc[a], alias=0) \
                        for a in transpose_list[0]]
                    field_value = '\n'.join(esper_list)
                    checkpoint_list = [0]
                    # Split if too long.
                    if len(field_value) > 1020:
                        field_value_length = -2
                        for i, field_entry in enumerate(esper_list):
                            field_value_length += len(field_entry) + 2
                            if field_value_length > 1000:
                                field_value_length = len(field_entry)
                                checkpoint_list.append(i)
                    for i, checkpoint in enumerate(checkpoint_list, start=1):
                        if checkpoint == 0:
                            field_name = 'Esper'
                        else:
                            embed.add_field(name='\u200B', value='\u200B',
                                            inline=False)
                            field_name = 'Esper (cont.)'
                        if i == len(checkpoint_list):
                            field_value = '\n'.join(esper_list[checkpoint:])
                        else:
                            field_value = '\n'.join(
                                esper_list[checkpoint:checkpoint_list[i]])
                        embed.add_field(name=field_name, value=field_value,
                                        inline=True)
                        for field_name, field_list in \
                                zip(arg, transpose_list[1:]):
                            if i == len(checkpoint_list):
                                field_value = '\n'.join(
                                    field_list[checkpoint:])
                            else:
                                field_value = '\n'.join(field_list \
                                    [checkpoint:checkpoint_list[i]])
                            embed.add_field(name=field_name.capitalize(),
                                            value=field_value, inline=True)
                elif first_arg in {'y', 'n'}:
                    field_name = 'Esper'
                    esper_list = [
                        wotv_utils.name_str(row_df_row, alias=0)
                        for _, row_df_row in row_df.iterrows()
                        ]
                    field_value = '\n'.join(esper_list)
                    embed.add_field(name=field_name, value=field_value,
                                    inline=True)
                else:
                    embed.description = ' '.join((
                        'Esper effect not found or ambiguous.',
                        'Try `=help esper`.'
                    ))
        elif arg[0] in {'compare', 'c'} and len(arg) > 1:
            # Comparison mode.
            if mobile_bool == 0 and arg[1] in {'m', 'mobile'}:
                mobile_bool = 1
                args = ' '.join(arg[2:])
            else:
                args = ' '.join(arg[1:])
            embed.title = args
            # Convert arg list to split with | instead.
            arg = [a.lower().strip() for a in args.split('|')]
            # Check for shortcuts.
            for i, argstr in enumerate(arg):
                if len(argstr.split()) == 1:
                    arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
            row_list = []
            list_espers = []
            extra_stats = []
            # Parse arguments.
            default_extra = 1
            for argstr in arg:
                if argstr[0] == '+':
                    # Additional line.
                    default_extra = 0
                    extra_arg = argstr.lstrip('+ ')
                    if extra_arg.rstrip('s') in ['all atk', 'atk']:
                        extra_stats.append('ALL ATK Up')
                    elif extra_arg.rstrip('s') in ['all killer', 'killer']:
                        extra_stats.append('ALL Killer')
                    elif extra_arg.rstrip('s') in ['all stat', 'stat']:
                        extra_stats.append('ALL Stat Up')
                    elif extra_arg.rstrip('s') in ['all res', 'res']:
                        extra_stats.append('ALL RES Up')
                    elif extra_arg == 'all':
                        extra_stats = extra_stats + ['ALL ATK Up',
                            'ALL Killer', 'ALL Stat Up', 'ALL RES Up']
                    else:
                        extra_stats.append(extra_arg)
                else:
                    # Find esper.
                    rowfound, row = wotv_utils.find_row(df, argstr)
                    if rowfound == 1:
                        row_list.append(row)
                        list_espers.append(wotv_utils.name_str(row, alias=0))
                    else:
                        default_extra = 0
            if default_extra:
                extra_stats = ['ALL ATK Up', 'ALL Killer', 'ALL Stat Up',
                    'ALL RES Up']
            if len(list_espers) > 2:
                # Force into mobile mode otherwise can't fit.
                mobile_bool = 1
            tuples_list = []
            for colstat in extra_stats:
                tup = wotv_utils.esper_findcol(colstat)
                if tup[0] != 'NOTFOUND':
                    tuples_list.append(tup)
            list_stats = []
            list_effects = {a: dict() for a in \
                wotv_utils.dicts['esper_colsuffix'].keys()}
            # Process each esper.
            for i, row in enumerate(row_list):
                list_stats.append([str(row[col]) for col in \
                    wotv_utils.dicts['esper_stats']])
                for tupcol, tuparg in tuples_list:
                    eff_list = row[tupcol].split(' / ')
                    for eff in eff_list:
                        if tuparg == 'ALL' or tuparg in eff.lower():
                            re_match = wotv_utils.revalues.search(eff)
                            if re_match == None:
                                continue
                            effstr = ''.join((eff[:re_match.start()],
                                wotv_utils.dicts['esper_colsuffix'][tupcol]))
                            if effstr in list_effects[tupcol].keys():
                                list_effects[tupcol][effstr][i] = \
                                    re_match.group()
                            else:
                                list_effects[tupcol][effstr] = \
                                    {i: re_match.group()}
            # Combine stats data and effects data.
            list_effects_combined = {k: v for _, a in list_effects.items() \
                for k, v in a.items()}
            stat_list = wotv_utils.dicts['esper_stats'] + \
                list(list_effects_combined.keys())
            for _, effstr_dict in list_effects_combined.items():
                for i, row_stats in enumerate(list_stats):
                    if i in effstr_dict.keys():
                        row_stats.append(effstr_dict[i])
                    else:
                        row_stats.append('-')
            # Print based on display mode.
            if mobile_bool:
                transpose_list = list(map(list, zip(*list_stats)))
                embed.add_field(name='Stat', value=' | '.join(list_espers),
                                inline=False)
                for field_name, stat_list in zip(stat_list, transpose_list):
                    field_list = [str(a) for a in stat_list]
                    embed.add_field(name=field_name,
                                    value=' | '.join(field_list), inline=False)
            else:
                embed.add_field(name='Stat', value='\n'.join(stat_list),
                                inline=True)
                for field_name, stat_list in zip(list_espers, list_stats):
                    field_list = [str(a) for a in stat_list]
                    embed.add_field(name=field_name,
                                    value = '\n'.join(field_list), inline=True)
        else:
            # Esper info mode.
            rowfound, row = wotv_utils.find_row(df, arg)
            if rowfound == 0:
                if row == '':
                    embed.title = ' '.join(arg)
                    embed.description = ''.join((
                        'No match found. ',
                        'Or maybe did you mean to use `=esper r/c`?'))
                else:
                    embed.title = ' '.join(arg)
                    embed.description = '\n'.join((
                        'Too many results. Please try the following:', row))
            else:
                embed.colour = wotv_utils.dicts['colours'][row['Element']\
                    .lower()]
                embed.title = wotv_utils.name_str(row, alias=0)
                field_value_list = [str(row[col]) for col in \
                    wotv_utils.dicts['esper_stats']]
                if mobile_bool:
                    field_value_list = [f"**{col}:** {(row[col])}" for col in \
                        wotv_utils.dicts['esper_stats']]
                    embed.add_field(name='Stat',
                                    value='\n'.join(field_value_list),
                                    inline=False)
                else:
                    field_value_list = [str(row[col]) for col in \
                        wotv_utils.dicts['esper_stats']]
                    embed.add_field(name='Stat', value='\n'.join(wotv_utils \
                        .dicts['esper_stats']), inline=True)
                    embed.add_field(name='Value', value='\n'.join(
                        field_value_list), inline=True)
                field_value_list1 = [] # Effect names.
                field_value_list2 = [] # Effect values.
                for col, suffix in wotv_utils.dicts['esper_colsuffix'].items():
                    if row[col] != '':
                        eff_list = row[col].split(' / ')
                        for eff in eff_list:
                            re_match = wotv_utils.revalues.search(eff)
                            field_value_list1.append(''.join((
                                eff[:re_match.start()], suffix)))
                            field_value_list2.append(re_match.group())
                # Print based on display mode.
                if mobile_bool:
                    field_value_list = ['(including both board and innate)'] \
                        + [f"{a} {b}" for a, b in zip(field_value_list1, \
                        field_value_list2)]
                    embed.add_field(name='Max Effects',
                                    value='\n'.join(field_value_list),
                                    inline=False)
                else:
                    embed.add_field(name='Max Effects',
                                    value='(including both board and innate)',
                                    inline=False)
                    embed.add_field(name='Effect',
                                    value='\n'.join(field_value_list1),
                                    inline=True)
                    embed.add_field(name='Value',
                                    value='\n'.join(field_value_list2),
                                    inline=True)
                if row['Url'] != '':
                    embed.set_thumbnail(url=row['Url'])
                embed.add_field(name='WOTV-CALC',
                                value=wotv_utils.calc_url('esper', row.name),
                                inline=False)
        await self.log.send(ctx, embed=embed)
