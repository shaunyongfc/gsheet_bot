import discord
import pandas as pd
from discord.ext import commands
from gsheet_handler import dfwotv
from wotv_processing import WotvUtils
from general_cogs import logs_embed
from id_dict import id_dict
from datetime import datetime

wotv_utils = WotvUtils(dfwotv, id_dict)
mydtformat = '%Y/%m/%d %H:%M'

class WotvGeneral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command('help')

    @commands.command()
    async def wotvsync(self, ctx, *arg):
        if ctx.message.author.id == id_dict['Owner']:
            if len(arg) == 0:
                # Synchronise WOTV sheets
                dfwotv.sync()
                await ctx.send('Google sheet synced for WOTV data.')
            elif arg[0] == 'ramada':
                wotv_utils.update_ramada()
                await ctx.send('Ramada rate updated.')
            elif arg[0] == 'esper':
                # Update the set of effects per column in Esper
                wotv_utils.dicts['esper_sets'] = wotv_utils.esper_sets(dfwotv.esper)
                await ctx.send('Esper keyword sets updated.')
            elif arg[0] == 'events':
                dfwotv.sync_events()
                await ctx.send('Google sheet synced for WOTV events.')

    @commands.command(aliases=['help', 'about', 'info', 'aboutme', 'readme'])
    async def wotvhelp(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Customised bot help function
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
            elif arg[0].lower() in ['stars', 'ramada']:
                help_tuples = wotv_utils.help_ramada
            elif arg[0].lower() == 'events':
                help_tuples = wotv_utils.help_events
        for a, b in help_tuples:
            embed.add_field(name=a, value='\n'.join(b), inline=False)
        await ctx.send(embed = embed)

    @commands.command(aliases=['addevent'])
    async def wotvaddevent(self, ctx, *arg):
        # Add event to calendar for authorized people
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        if ctx.message.author.id in dfwotv.ids['WOTV Events']:
            try:
                arg = [a.strip() for a in ' '.join(arg).split('|')]
                eventstr = arg[0]
                eventstart = datetime.strptime(arg[1], mydtformat)
                if len(arg) == 2:
                    eventend = eventstart
                else:
                    eventend = datetime.strptime(arg[2], mydtformat)
                if eventstart <= eventend:
                    dfwotv.add_event(arg)
                    await ctx.send('Event added.')
                else:
                    await ctx.send('Ending time must be later than starting time.')
            except (IndexError, ValueError):
                await ctx.send('Incorrect format.')
        else:
            await ctx.send('Permission denied.')

    @commands.command(aliases=['events', 'calendar', 'timer', 'countdown', 'date'])
    async def wotvevents(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Check ongoing or upcoming events
        dt_bool = 0
        sp_bool = 0
        if len(arg) > 0:
            if arg[0] in ('date', 'time', 'upcoming', 'up-coming', 'ongoing', 'on-going'):
                dt_bool = 1
            elif arg[0] in ('embed', 'format'):
                dt_bool = 2
        events = {
            'on-going': [],
            'up-coming': []
        }
        for _, row in dfwotv.events.iterrows(): # Goes through the dataframe
            if datetime.now() <= datetime.strptime(row['End'], mydtformat):
                eventprefix = ':calendar:'
                for event_keywords, event_emote in wotv_utils.dicts['event_tuples']:
                    for event_keyword in event_keywords:
                        if event_keyword in row['Event'].lower():
                            eventprefix = wotv_utils.dicts['emotes'][event_emote]
                            break
                    if eventprefix != ':calendar:':
                        break
                eventname = f"{eventprefix} {row['Event']}"
                if datetime.now() <= datetime.strptime(row['End'], mydtformat):
                    events['on-going'].append((eventname, row['Start'], row['End']))
                elif datetime.now() <= datetime.strptime(row['Start'], mydtformat):
                    events['up-coming'].append((eventname, row['Start'], row['End']))
        replystr = ''
        if dt_bool == 2:
            embed = discord.Embed(
                colour = wotv_utils.dicts['embed']['default_colour']
            )
            embed.title = 'WOTV JP Calendar'
            for k, v in events.items():
                if len(v) == 0:
                    continue
                transpose_list = list(map(list, zip(*v)))
                embed.add_field(name=k.capitalize(), value='\n'.join(transpose_list[0]))
                embed.add_field(name='Start', value='\n'.join(transpose_list[1]))
                embed.add_field(name='End', value='\n'.join(transpose_list[2]))
            await ctx.send(embed = embed)
        else:
            for k, v in events.items():
                if len(replystr) > 0:
                    replystr += '\n\n'
                if len(v) == 0:
                    replystr += f"*No {k} events.*"
                else:
                    replystr += f"**{k.capitalize()} Events**"
                    for event in v:
                        if dt_bool == 1:
                            replystr += f"\n{event[0]} - `{event[1]}` to `{event[2]}`"
                        else:
                            replystr += f"\n{event[0]} -"
                            if k == 'on-going':
                                eventdd = datetime.strptime(event[2], mydtformat) - datetime.now()
                            else:
                                eventdd = datetime.strptime(event[1], mydtformat) - datetime.now()
                            eventddsplit = (
                                ('day', eventdd.days),
                                ('hour', eventdd.seconds // 3600),
                                ('minute', eventdd.seconds % 3600 // 60)
                            )
                            for eventddstr, eventddnum in eventddsplit:
                                if eventddnum > 1:
                                    replystr += f" `{eventddnum} {eventddstr}s`"
                                elif eventddnum == 1:
                                    replystr += f" `{eventddnum} {eventddstr}`"
            await ctx.send(replystr)

    @commands.command(aliases=['rand', 'random', 'choice'])
    async def wotvrand(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Fluff command to pick a number or string from users
        embed = discord.Embed()
        if ctx.guild.id in dfwotv.ids['FFBE Server']:
            ffbe = 1
        else:
            ffbe = 0
        npctup = wotv_utils.rand(ffbe, *arg)
        embed.title = f"Random {npctup[1]}"
        embed.colour = wotv_utils.dicts['colours'][npctup[2]]
        embed.set_thumbnail(url=npctup[3])
        if npctup[0]:
            embed.description = f"{npctup[4]} Give us either:\n- one or two numbers\n- two or more choices"
        else:
            embed.description = npctup[4]
        await ctx.send(embed = embed)

    @commands.command(aliases=['fortune', 'stars', 'ramada'])
    async def wotvramada(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Fluff command to read fortune
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        fortunestr, fortunedeco, fortuneurl = wotv_utils.ramada()
        embed.title = f"Ramada Star Reading {fortunedeco}"
        embed.description = fortunestr
        embed.set_thumbnail(url=fortuneurl)
        await ctx.send(embed = embed)

    @commands.command(aliases=['changelog', 'version'])
    async def wotvchangelog(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Return recent changelogs
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
        for i, tup in enumerate(wotv_utils.dicts['changelog']):
            if i == entry_num:
                break
            embed.add_field(name=tup[0], value = '\n'.join(tup[1]), inline=False)
        await ctx.send(embed = embed)

    @commands.command(aliases=['weekly', 'week', 'day', 'weekday'])
    async def wotvweekly(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Reply pre-set message of day of the week bonuses
        await ctx.send(wotv_utils.weekly)

    @commands.command(aliases=['news'])
    async def wotvnews(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Reply pre-set link to news
        try:
            if arg[0].lower() == 'gl':
                await ctx.send('https://site.na.wotvffbe.com//whatsnew')
            else:
                await ctx.send('https://site.wotvffbe.com//whatsnew\n<https://players.wotvffbe.com/>')
        except IndexError:
            await ctx.send('https://site.wotvffbe.com//whatsnew\n<https://players.wotvffbe.com/>')

    @commands.command(aliases=['param', 'acc', 'eva', 'crit'])
    async def wotvparam(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help param`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        # Calculate acc, eva, crit and crit avoid from dex, agi, luck, eq stats
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        params = {k: v[0] for k, v in wotv_utils.dicts['paramcalc'].items()}
        args = ' '.join(arg)
        embed.title = args
        # convert arg list to split with | instead
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # find position and value of number
            re_match = wotv_utils.revalues.search(argstr)
            try:
                paramval = int(re_match.group())
                paramstr = argstr[0:re_match.start()].strip()
                for k, v in wotv_utils.dicts['paramcalc'].items():
                    if paramstr in v[1]:
                        if k not in ('agi', 'dex', 'luck') or paramval >= 0:
                            # disallowing negative values for the three stats
                            params[k] = paramval
                        break
            except AttributeError:
                pass
        # actual calculations
        results = (
            ('ACC', (11*params['dex']**0.2/20 + params['luck']**0.96/200 - 1) * 100 + params['acc']),
            ('EVA', (11*params['agi']**0.9/1000 + params['luck']**0.96/200 - 1) * 100 + params['eva']),
            ('CRIT', (params['dex']**0.35/4 - 1) * 100 + params['crit']),
            ('C.AVO', (params['luck']**0.37/5 - 1) * 100 + params['c.avo'])
        )
        # presenting results
        embed.add_field(name='Inputs', value='\n'.join([f"`{k.upper(): <5}` {v}" for k, v in params.items()]), inline=True)
        embed.add_field(name='Results', value='\n'.join([f"`{k: <5}` {v: .1f}%" for k, v in results]), inline=True)
        await ctx.send(embed = embed)

class WotvEquipment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['we', 'eq'])
    async def wotveq(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help eq`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        # Preliminary code for global implementation
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        if arg[0].lower() in ['list', 'l']:
            if len(arg) == 1:
                # Print list of lists
                embed.title = f"List of lists"
                embed.description = '\n'.join(wotv_utils.dicts['eq_lists'].keys())
            else:
                # Print list of searchable items in the column
                argstr = ' '.join(arg[1:]).lower()
                for k, v in wotv_utils.dicts['eq_lists'].items():
                    if argstr in v or argstr == k.lower():
                        argstr = k
                        break
                embed.title = f"List of {argstr}s"
                text_list = list(wotv_utils.dicts['mat_sets'][argstr])
                if argstr not in ['Type', 'Acquisition']:
                    text_list = [f"{a} ({dfwotv.mat.loc[a]['Aliases'].split(' / ')[0]})" for a in text_list]
                embed.description = '\n'.join(text_list)
        # Check if type search
        elif arg[0].lower() in ['type', 't', 'acquisition', 'a'] and len(arg) > 1:
            if arg[0].lower() in ['type', 't']:
                colstr = 'Type'
            else:
                colstr = 'Acquisition'
            # Process query
            argstr = ' '.join(arg[1:])
            embed.title = argstr
            argstr = argstr.lower()
            for a, b in wotv_utils.dicts['eq_replace']:
                argstr = argstr.replace(a, b)
            # Find eq that match and add to the embed
            for index, row in dfwotv.eq.iterrows():
                if argstr in row[colstr].lower():
                    field_name = wotv_utils.name_str(row)
                    field_value = f"- {row['Special']}"
                    embed.add_field(name=field_name, value=field_value, inline=True)
        else:
            # Check if material search
            argstr = ' '.join(arg)
            matstr = ('',)
            for index, row in dfwotv.mat.iterrows():
                if argstr in row['Aliases'].lower().split(' / '):
                    matstr = (index, row['Type'], row['Aliases'].split(' / ')[0])
                    break
            if matstr[0] != '':
                # Print all eq that use said materials
                embed.title = f"Recipes w/ {matstr[2]}"
                embed_text_list = {
                    'ur': [],
                    'ssr': []
                }
                for index, row in dfwotv.eq.iterrows():
                    if row[matstr[1]] == matstr[0] or (matstr[1] == 'Cryst' and matstr[0] in row[matstr[1]]):
                        embed_text_list[row['Rarity'].lower()].append(wotv_utils.name_str(row))
                for k, v in embed_text_list.items():
                    if len(v) > 0:
                        field_value = '\n'.join(v)
                        if len(field_value) < 1020:
                            embed.add_field(name=k.upper(), value=field_value, inline=True)
                        else:
                            # Split if too long
                            checkpoint = 0
                            field_value_length = -2
                            field_name = k.upper()
                            for i, v_entry in enumerate(v):
                                field_value_length += len(v_entry) + 2
                                if field_value_length > 1000:
                                    field_value = '\n'.join(v[checkpoint:i])
                                    embed.add_field(name=field_name, value=field_value, inline=True)
                                    field_value_length = len(v_entry)
                                    checkpoint = i
                                    field_name = f"{k.upper()} (cont.)"
                            field_value = '\n'.join(v[checkpoint:])
                            embed.add_field(name=field_name, value=field_value, inline=True)
            else:
                # Find the specific eq
                rowfound, row = wotv_utils.find_row(dfwotv.eq, arg)
                if rowfound == 0:
                    if row == '':
                        embed.title = ' '.join(arg)
                        embed.description = 'No match found. Or did you mean to use `=es` or `=eq l/t/a`?'
                    else:
                        embed.title = ' '.join(arg)
                        embed.description = 'Too many results. Please try the following:\n' + row
                else:
                    embed.title = row.name
                    embed.description = f"{wotv_utils.name_str(row, name='')}\n{row['Special']}\nAcquisition: {row['Acquisition']}"
                    embed_text_list = []
                    for col in ['Regular', 'Rare', 'Cryst', 'Ore']:
                        if row[col] != '':
                            if col == 'Cryst':
                                for cryst_ele in list(row[col]):
                                    if row['Rarity'] == 'UR':
                                        engstr = dfwotv.mat.loc[cryst_ele]['Aliases'].split(' / ')[0].replace('(Mega)C', 'Megac')
                                    else:
                                        engstr = dfwotv.mat.loc[cryst_ele]['Aliases'].split(' / ')[0].replace('(Mega)', '')
                                    embed_text_list.append(f"- {cryst_ele} ({engstr})")
                            else:
                                engstr = dfwotv.mat.loc[row[col]]['Aliases'].split(' / ')[0]
                                embed_text_list.append(f"- {row[col]} ({engstr})")
                    embed.add_field(name='List of materials', value='\n'.join(embed_text_list), inline=True)
                    embed.add_field(name='WOTV-CALC', value=wotv_utils.calc_url('equipment', row['Aliases'].split(' / ')[0]), inline=False)
        await ctx.send(embed = embed)

    @commands.command(aliases=['wes', 'eqs', 'es'])
    async def wotveqsearch(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help eq`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        if len(arg) == 1:
            # Check if it is a shortcut keyword
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        embed.title = args.title()
        args = args.lower()
        args = args.replace('lightning', 'thunder')
        for k, v in wotv_utils.dicts['colours'].items():
            if k in args:
                embed.colour = v
                break
        # Search each eq
        for _, row in dfwotv.eq.iterrows():
                eff_list = row['Special'].split(' / ')
                for eff in eff_list:
                    if args in eff.lower():
                        embed.add_field(name=wotv_utils.name_str(row), value=f"- {row['Special']}")
                        break
        try:
            await ctx.send(embed = embed)
        except discord.HTTPException:
            await ctx.send('Too many results. Please refine the search.')

class WotvVc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['wvs', 'vcs', 'vs'])
    async def wotvvcsearch(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help vc`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        # Preliminary code for global implementation
        df = dfwotv.vc
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/cards',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        # Initialise empty lists
        effects_dict = {
            'Party': [],
            'Party Max': [],
            'Unit': []
        }
        if len(arg) == 1:
            # Check if it is a shortcut keyword
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        embed.title = args.title()
        args = args.lower()
        args = args.replace('lightning', 'thunder')
        # Search each vc
        for _, row in df.iterrows():
            for col in effects_dict.keys():
                eff_list = row[col].split(' / ')
                eff_prefix = wotv_utils.dicts['emotes']['allele'] # Default icon unless condition found
                for eff in eff_list:
                    # Have to process the brackets first because might match 2nd conditional effect
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if len(match_brackets) == 1:
                        if match_brackets[0] in wotv_utils.dicts['brackets'].keys():
                            eff_prefix = wotv_utils.dicts['emotes'][wotv_utils.dicts['brackets'][match_brackets[0]]]
                        else:
                            eff_prefix = match_brackets[0]
                    if args in eff.lower():
                        eff_suffix = '' # Actually effect numbers
                        match_numbers = wotv_utils.revalues.findall(eff)
                        if len(match_numbers) == 1:
                            eff_suffix = ' ' + match_numbers[0]
                        effects_dict[col].append(f"{eff_prefix}{wotv_utils.name_str(row)}{eff_suffix}")
        # Print from each list if non-empty
        empty_list = 1
        for k, v in effects_dict.items():
            if len(v) > 0:
                empty_list = 0
                field_value = '\n'.join(v)
                if len(field_value) < 1020:
                    embed.add_field(name=k, value=field_value, inline=False)
                else:
                    # Split if too long
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
            embed.description = 'No match found. Try checking `=help vc`. Or did you mean to use `=vc`?'
        # Fluff to change embed colour if requested effect is elemental
        for k, v in wotv_utils.dicts['colours'].items():
            if k in args:
                embed.colour = v
                embed.add_field(name='Note:',
                    value=f"`=ve {k}` instead to list element-locked effects."
                )
                break
        try:
            await ctx.send(embed = embed)
        except discord.HTTPException:
            await ctx.send('Too many results. Please refine the search.')

    @commands.command(aliases=['wve', 'vce', 've'])
    async def wotvvcelement(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help vc`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed()
        # Preliminary code for global implementation
        df = dfwotv.vc
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/cards',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        # Initialise empty lists
        effects_dict = {
            'Party': [],
            'Party Max': []
        }
        ele = arg[0].lower().replace('lightning', 'thunder')
        embed.title = f"{wotv_utils.dicts['emotes'][ele]} {arg[0].title()}"
        embed.colour = wotv_utils.dicts['colours'][ele]
        # Search each vc
        for index, row in df.iterrows():
            for col in effects_dict.keys():
                eff_list = row[col].split(' / ')
                ele_found = 0
                for eff in eff_list:
                    if ele_found or wotv_utils.dicts['brackets'][ele] in eff:
                        ele_found = 1
                        effects_dict[col].append(f"{wotv_utils.name_str(row)} {eff.replace(wotv_utils.dicts['brackets'][ele] + ' ', '')}")
        # Print from each list if non-empty
        for k, v in effects_dict.items():
            if len(v) > 0:
                field_value = '\n'.join(v)
                if len(field_value) < 1020:
                    embed.add_field(name=k, value=field_value, inline=False)
                else:
                    # Split if too long
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
        await ctx.send(embed = embed)

    @commands.command(aliases=['wv', 'vc'])
    async def wotvvc(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help vc`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        # Preliminary code for global implementation
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
                embed.description = 'No match found. Or did you mean to use `=vs` or `=ve`?'
            else:
                embed.title = ' '.join(arg)
                embed.description = 'Too many results. Please try the following:\n' + row
        else:
            embed.title = wotv_utils.name_str(row, alias=0)
            embed_colour = ''
            for col in ('Unit', 'Party', 'Party Max', 'Skill'):
                if row[col] == '':
                    continue
                eff_list = row[col].split(' / ')
                eff_list_processed = []
                eff_prefix = ''
                for eff in eff_list:
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if len(match_brackets) == 1:
                        if match_brackets[0] in wotv_utils.dicts['brackets'].keys():
                            eff_prefix = wotv_utils.dicts['emotes'][wotv_utils.dicts['brackets'][match_brackets[0]]] + ' '
                            embed_colour = wotv_utils.dicts['brackets'][match_brackets[0]]
                        else:
                            eff_prefix = match_brackets[0] + ' '
                        eff_text = eff.replace(match_brackets[0] + ' ', '')
                    else:
                        eff_text = eff
                    eff_list_processed.append(f"{eff_prefix}{eff_text}")
                field_value = '\n'.join(eff_list_processed)
                embed.add_field(name=col, value=field_value)
            if row['Url'] != '':
                embed.set_thumbnail(url=row['Url'])
            if embed_colour != '':
                embed.colour = wotv_utils.dicts['colours'][embed_colour]
            if row['English'] != '':
                embed.add_field(name='WOTV-CALC', value=wotv_utils.calc_url('card', row['English']), inline=False)
        await ctx.send(embed = embed)

class WotvEsper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['esper'])
    async def wotvesper(self, ctx, *arg):
        if len(arg) == 0:
            await ctx.send('Try `=help esper`.')
            return
        await self.bot.get_channel(id_dict['Logs']).send(embed = logs_embed(ctx.message))
        embed = discord.Embed(
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        # Preliminary code for global implementation
        #if arg[0] in ['global', 'gl']:
            #global_bool = 1
            #embed.set_author(
            #    name = wotv_utils.dicts['embed']['gl_author_name'],
            #    url = 'https://wotv-calc.com/espers',
            #    icon_url = wotv_utils.dicts['embed']['author_icon_url']
            #)
            #df = dfwotv.glesper
            #arg = arg[1:]
        #else:
            #global_bool = 0
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/espers',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        df = dfwotv.esper
        # Check arguments
        if arg[0] in ['m', 'mobile']:
            mobile_bool = 1
            arg = arg[1:]
        else:
            mobile_bool = 0
        if arg[0] in ['sort', 's', 'rank', 'r', 'filter', 'f']:
            # Ranking mode
            if mobile_bool == 0 and arg[1] in ['m', 'mobile']:
                mobile_bool = 1
                args = ' '.join(arg[2:])
            else:
                args = ' '.join(arg[1:])
            embed.title = args
            # convert arg list to split with | instead
            arg = [a.lower().strip() for a in args.split('|')]
            # Check for shortcuts
            for i, argstr in enumerate(arg):
                if len(argstr.split()) == 1:
                    arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
            # Function to find which column the said effect should be
            while len(arg) > 0:
                col, first_arg = wotv_utils.esper_findcol(arg[0])
                if col == 'NOTFOUND':
                    arg = arg[1:]
                else:
                    break
            if first_arg == 'STAT':
                row_df = df.nlargest(20, col)
            else:
                row_df = df[df[col].str.lower().str.contains(first_arg)]
            if first_arg == 'y':
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
                row_list = [index] # Initialise for each row with only name
                for tupcol, tuparg in tuples_list:
                    # Find value and add to row list
                    if tuparg == 'STAT':
                        row_list.append(str(row[tupcol]))
                    elif tuparg in row[tupcol].lower():
                        eff_list = row[tupcol].split(' / ')
                        for eff in eff_list:
                            if tuparg in eff.lower():
                                re_match = wotv_utils.revalues.findall(eff)
                                row_list.append(re_match[0])
                    else:
                        row_list.append('-')
                list_lists.append(row_list)
            # Sort list
            if first_arg != 'y':
                list_lists.sort(key=lambda a: int(a[1]), reverse=True)
            # Print based on display mode
            if mobile_bool:
                for row_list in list_lists:
                    field_name = wotv_utils.name_str(row_df.loc[row_list[0]])
                    field_list = []
                    for argname, argvalue in zip(arg, row_list[1:]):
                        if argvalue != '-':
                            field_list.append(f"**{argname.title()}**: {argvalue}")
                    embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
            else:
                transpose_list = list(map(list, zip(*list_lists)))
                esper_list = [wotv_utils.name_str(row_df.loc[a], alias=0) for a in transpose_list[0]]
                field_value = '\n'.join(esper_list)
                checkpoint_list = [0]
                # Split if too long
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
                        embed.add_field(name='\u200B', value='\u200B', inline=False)
                        field_name = 'Esper (cont.)'
                    if i == len(checkpoint_list):
                        field_value = '\n'.join(esper_list[checkpoint:])
                    else:
                        field_value = '\n'.join(esper_list[checkpoint:checkpoint_list[i]])
                    embed.add_field(name=field_name, value=field_value, inline=True)
                    for field_name, field_list in zip(arg, transpose_list[1:]):
                        if i == len(checkpoint_list):
                            field_value = '\n'.join(field_list[checkpoint:])
                        else:
                            field_value = '\n'.join(field_list[checkpoint:checkpoint_list[i]])
                        embed.add_field(name=field_name.capitalize(), value=field_value, inline=True)
        elif arg[0] in ['compare', 'c']:
            # Comparison mode
            if mobile_bool == 0 and arg[1] in ['m', 'mobile']:
                mobile_bool = 1
                args = ' '.join(arg[2:])
            else:
                args = ' '.join(arg[1:])
            embed.title = args
            # convert arg list to split with | instead
            arg = [a.lower().strip() for a in args.split('|')]
            # Check for shortcuts
            for i, argstr in enumerate(arg):
                if len(argstr.split()) == 1:
                    arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
            row_list = []
            list_espers = []
            extra_stats = []
            # parse arguments
            for argstr in arg:
                if argstr[0] == '+':
                    # additional line
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
                        extra_stats = extra_stats + ['ALL ATK Up', 'ALL Killer', 'ALL Stat Up', 'ALL RES Up']
                    else:
                        extra_stats.append(extra_arg)
                else:
                    # find esper
                    row_df = df[df.index.str.lower() == argstr]
                    if len(row_df) == 0:
                        row_df = df[df.index.str.lower().str.contains(argstr)]
                    if len(row_df) == 0:
                        row_df = df[argstr in df['Aliases'].str.split(' / ')]
                    if len(row_df) == 0:
                        row_df = df[df['Aliases'].str.contains(argstr)]
                    if len(row_df) == 1:
                        row_list.append(row_df.iloc[0])
                        list_espers.append(wotv_utils.name_str(row_df.iloc[0], alias=0))
            if len(list_espers) > 2:
                # Force into mobile mode otherwise can't fit
                mobile_bool = 1
            tuples_list = []
            for colstat in extra_stats:
                tup = wotv_utils.esper_findcol(colstat)
                if tup[0] != 'NOTFOUND':
                    tuples_list.append(tup)
            list_stats = []
            list_effects = {a: dict() for a in wotv_utils.dicts['esper_colsuffix'].keys()}
            # Process each esper
            for i, row in enumerate(row_list):
                list_stats.append([str(row[col]) for col in wotv_utils.dicts['esper_stats']])
                for tupcol, tuparg in tuples_list:
                    eff_list = row[tupcol].split(' / ')
                    for eff in eff_list:
                        if tuparg == 'ALL' or tuparg in eff.lower():
                            re_match = wotv_utils.revalues.search(eff)
                            effstr = f"{eff[:re_match.start()]}{wotv_utils.dicts['esper_colsuffix'][tupcol]}"
                            if effstr in list_effects[tupcol].keys():
                                list_effects[tupcol][effstr][i] = re_match.group()
                            else:
                                list_effects[tupcol][effstr] = {i: re_match.group()}
            # Combining stats data and effects data
            list_effects_combined = {k: v for _, a in list_effects.items() for k, v in a.items()}
            stat_list = wotv_utils.dicts['esper_stats'] + list(list_effects_combined.keys())
            for _, effstr_dict in list_effects_combined.items():
                for i, row_stats in enumerate(list_stats):
                    if i in effstr_dict.keys():
                        row_stats.append(effstr_dict[i])
                    else:
                        row_stats.append('-')
            # Print based on display mode
            if mobile_bool:
                transpose_list = list(map(list, zip(*list_stats)))
                embed.add_field(name='Stat', value=' | '.join(list_espers), inline=False)
                for field_name, stat_list in zip(stat_list, transpose_list):
                    field_list = [str(a) for a in stat_list]
                    embed.add_field(name=field_name, value=' | '.join(field_list), inline=False)
            else:
                embed.add_field(name='Stat', value='\n'.join(stat_list), inline=True)
                for field_name, stat_list in zip(list_espers, list_stats):
                    field_list = [str(a) for a in stat_list]
                    embed.add_field(name=field_name, value = '\n'.join(field_list), inline=True)
        else:
            # Esper info mode
            rowfound, row = wotv_utils.find_row(df, arg)
            if rowfound == 0:
                if row == '':
                    embed.title = ' '.join(arg)
                    embed.description = 'No match found. Or maybe did you mean to use `=esper r/c`?'
                else:
                    embed.title = ' '.join(arg)
                    embed.description = 'Too many results. Please try the following:\n' + row
            else:
                embed.colour = wotv_utils.dicts['colours'][row['Element'].lower()]
                embed.title = wotv_utils.name_str(row, alias=0)
                field_value_list = [str(row[col]) for col in wotv_utils.dicts['esper_stats']]
                if mobile_bool:
                    field_value_list = [f"**{col}:** {(row[col])}" for col in wotv_utils.dicts['esper_stats']]
                    embed.add_field(name='Stat', value='\n'.join(field_value_list), inline=False)
                else:
                    field_value_list = [str(row[col]) for col in wotv_utils.dicts['esper_stats']]
                    embed.add_field(name='Stat', value='\n'.join(wotv_utils.dicts['esper_stats']), inline=True)
                    embed.add_field(name='Value', value='\n'.join(field_value_list), inline=True)
                field_value_list1 = [] # effect names
                field_value_list2 = [] # numbers
                for col, suffix in wotv_utils.dicts['esper_colsuffix'].items():
                    if row[col] != '':
                        eff_list = row[col].split(' / ')
                        for eff in eff_list:
                            re_match = wotv_utils.revalues.search(eff)
                            field_value_list1.append(f"{eff[:re_match.start()]}{suffix}")
                            field_value_list2.append(re_match.group())
                # Print based on display mode
                if mobile_bool:
                    field_value_list = ['(including both board and innate)'] + [f"{a} {b}" for a, b in zip(field_value_list1, field_value_list2)]
                    embed.add_field(name='Max Effects', value='\n'.join(field_value_list), inline=False)
                else:
                    embed.add_field(name='Max Effects', value='(including both board and innate)', inline=False)
                    embed.add_field(name='Effect', value='\n'.join(field_value_list1), inline=True)
                    embed.add_field(name='Value', value='\n'.join(field_value_list2), inline=True)
                if row['Url'] != '':
                    embed.set_thumbnail(url=row['Url'])
                embed.add_field(name='WOTV-CALC', value=wotv_utils.calc_url('esper', row.name), inline=False)
        await ctx.send(embed = embed)
