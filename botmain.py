import discord
import pandas as pd
from discord.ext import commands
from gsheet_handler import get_dfwotv, dfwotv
from wotv_processing import wotv_utils

from gsheet_handler import get_df_cotc, df_cotc
from cotc_processing import cotc_dicts, get_cotc_label, get_sorted_df, get_support_df

bot = commands.Bot(command_prefix='+')

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

################################
### FFBE: War of the Visions ###
################################
# Able to copy directly from this point

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")

bot.remove_command('help')
@bot.command(aliases=['help'])
async def wotvhelp(ctx, *arg):
    # Customised bot help function
    embed = discord.Embed(
        colour = wotv_utils.dicts['embed']['default_colour']
    )
    embed.set_author(
        name = wotv_utils.dicts['embed']['author_name'],
        icon_url = wotv_utils.dicts['embed']['author_icon_url']
    )
    embed.title = 'Ildyra Bot Help'
    help_tuples = wotv_utils.dicts['help']
    if len(arg) > 0:
        if arg[0].lower() == 'vc':
            help_tuples = wotv_utils.dicts['help_vc']
        elif arg[0].lower() == 'esper':
            help_tuples = wotv_utils.dicts['help_esper']
    for a, b in help_tuples:
        embed.add_field(name=a, value='\n'.join(b), inline=False)
    await ctx.send(embed = embed)

@bot.command()
async def sync(ctx, *arg):
    if ctx.message.author.id == 294834393569296385:
        if len(arg) == 0:
            # Synchronise sheets
            global dfwotv
            dfwotv = get_dfwotv()
            await ctx.send('Google sheet synced.')
        elif arg[0] == 'esper':
            # Update the set of effects per column in Esper
            wotv_utils.dicts['esper_sets'] = wotv_utils.esper_sets(dfwotv['esper'])
            await ctx.send('Esper keyword sets updated.')

@bot.command()
async def checkservers(ctx, *arg):
    if ctx.message.author.id == 294834393569296385:
        # Check what servers bot is in
        guilds = list(bot.guilds)
        guild_names = '\n'.join(f"- {a.name}" for a in guilds)
        await ctx.send(f"Connected on {len(guilds)} servers:\n{guild_names}")

@bot.command(aliases=['weekly', 'week', 'day', 'weekday'])
async def wotvweekly(ctx, *arg):
    # Reply pre-set message of day of the week bonuses
    await ctx.send(wotv_utils.weekly)

@bot.command(aliases=['we', 'eq'])
async def wotveq(ctx, *arg):
    embed = discord.Embed(
        colour = wotv_utils.dicts['embed']['default_colour']
    )
    embed.set_author(
        name = wotv_utils.dicts['embed']['author_name'],
        icon_url = wotv_utils.dicts['embed']['author_icon_url']
    )
    # Check if material search
    argstr = ''
    if arg[0].lower() in ['common', 'c']:
        argstr = 'Common'
    elif arg[0].lower() in ['rare', 'r']:
        argstr = 'Rare'
    elif arg[0].lower() in ['crystal', 'element', 'e']:
        argstr = 'Crystal'
    if argstr != '':
        # For material search
        if len(arg) == 1:
            # Print list of materials in the category
            embed.title = f"List of {argstr.lower()}s"
            embed.description = '\n'.join(wotv_utils.dicts['mat_sets'][argstr])
        elif len(arg) == 2:
            # Print all eq that use said materials
            embed.title = arg[1]
            embed_text_list = []
            for name, row in dfwotv['mats'].iterrows():
                if row[argstr] == arg[1] or (argstr == 'Crystal' and arg[1] in row[argstr]):
                    embed_text_list.append(f"{wotv_utils.emote_prefix(row)} {name}")
            embed.description = '\n'.join(embed_text_list)
    else:
        # Check if type search
        if arg[0].lower() in ['type', 't']:
            if len(arg) == 1:
                # Print list of types
                embed.title = f"List of types"
                embed.description = '\n'.join(wotv_utils.dicts['mat_sets']['Type'])
            else:
                # Process query
                query = ' '.join(arg[1:])
                embed.title = query
                query = query.lower()
                for a, b in wotv_utils.dicts['eq_replace']:
                    query = query.replace(a, b)
                # Find eq that match and add to the embed
                for index, row in dfwotv['mats'].iterrows():
                    if query in row['Type'].lower():
                        field_name = f"{wotv_utils.emote_prefix(row)} {index}"
                        field_value = f"- {row['Special']}"
                        embed.add_field(name=field_name, value=field_value, inline=True)
        elif len(arg) == 1:
            # Find the specific eq
            embed.title = arg[0]
            row = dfwotv['mats'].loc[arg[0]]
            embed.description = f"{wotv_utils.emote_prefix(row)} {row['Special']}\nAcquisition: {row['Acquisition']}"
            embed_text_list = []
            for col in ['Common', 'Rare', 'Crystal']:
                embed_text_list.append(f"- {row[col]}")
            embed.add_field(name='List of materials', value='\n'.join(embed_text_list), inline=True)
    await ctx.send(embed = embed)

@bot.command(aliases=['wvs', 'vcs', 'vs'])
async def wotvvcsearch(ctx, *arg):
    embed = discord.Embed(
        colour = wotv_utils.dicts['embed']['default_colour']
    )
    # Preliminary code for global implementation
    df = dfwotv['vc']
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
        try:
            # Check if it is a shortcut keyword
            args = dfwotv['shortcut'].loc[arg[0].lower()]['Conversion']
        except:
            args = arg[0]
    else:
        args = ' '.join(arg)
    embed.title = args.capitalize()
    args = args.lower()
    args = args.replace('lightning', 'thunder')
    # Fluff to change embed colour if requested effect is elemental
    for k, v in wotv_utils.dicts['colours'].items():
        if k in args:
            embed.colour = v
            break
    # Search each vc
    for _, row in df.iterrows():
        for col in effects_dict.keys():
            eff_list = row[col].split(' / ')
            eff_prefix = wotv_utils.dicts['emotes']['neutral'] # Default icon unless condition found
            for eff in eff_list:
                # Have to process the brackets first because might match 2nd conditional effect
                match_brackets = wotv_utils.reb.findall(eff)
                if len(match_brackets) == 1:
                    if match_brackets[0] in wotv_utils.dicts['brackets'].keys():
                        eff_prefix = wotv_utils.dicts['emotes'][wotv_utils.dicts['brackets'][match_brackets[0]]]
                    else:
                        eff_prefix = match_brackets[0]
                if args in eff.lower():
                    eff_suffix = '' # Actually effect numbers
                    match_numbers = wotv_utils.ren.findall(eff)
                    if len(match_numbers) == 1:
                        eff_suffix = ' ' + match_numbers[0]
                    nickname = row['Nickname'].split(', ')[0]
                    effects_dict[col].append(f"{eff_prefix}{wotv_utils.emote_prefix(row)} {row.name} ({nickname}){eff_suffix}")
    # Print from each list if non-empty
    for k, v in effects_dict.items():
        if len(v) > 0:
            embed.add_field(name=k, value='\n'.join(v), inline=False)
    embed.set_footer(text=wotv_utils.dicts['embed']['footer'])
    try:
        await ctx.send(embed = embed)
    except discord.HTTPException:
        await ctx.send('Too many results. Please refine the search.')

@bot.command(aliases=['wve', 'vce', 've'])
async def wotvvcelement(ctx, *arg):
    embed = discord.Embed()
    # Preliminary code for global implementation
    df = dfwotv['vc']
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
    embed.title = f"{wotv_utils.dicts['emotes'][ele]} {arg[0].capitalize()}"
    embed.colour = wotv_utils.dicts['colours'][ele]
    # Search each vc
    for index, row in df.iterrows():
        for col in effects_dict.keys():
            eff_list = row[col].split(' / ')
            ele_found = 0
            for eff in eff_list:
                if ele_found or wotv_utils.dicts['brackets'][ele] in eff:
                    ele_found = 1
                    nickname = row['Nickname'].split(', ')[0]
                    effects_dict[col].append(f"{wotv_utils.emote_prefix(row)} {index} ({nickname}) {eff.replace(wotv_utils.dicts['brackets'][ele] + ' ', '')}")
    # Print from each list if non-empty
    for k, v in effects_dict.items():
        if len(v) > 0:
            embed.add_field(name=k, value='\n'.join(v), inline=False)
    embed.set_footer(text=wotv_utils.dicts['embed']['footer'])
    await ctx.send(embed = embed)

@bot.command(aliases=['wv', 'vc'])
async def wotvvc(ctx, *arg):
    embed = discord.Embed(
        colour = wotv_utils.dicts['embed']['default_colour']
    )
    # Preliminary code for global implementation
    df = dfwotv['vc']
    embed.set_author(
        name = wotv_utils.dicts['embed']['author_name'],
        url = 'https://wotv-calc.com/JP/cards',
        icon_url = wotv_utils.dicts['embed']['author_icon_url']
    )
    row_found = False
    try:
        # Check if arguments are in Japanese
        arg[0].encode('ascii')
        row_df = df[df['Nickname'].str.contains(' '.join(arg).lower())]
    except UnicodeEncodeError:
        # If arguments are in English
        try:
            row = df.loc['　'.join(arg)]
            row_found = True
        except KeyError:
            row_df = df[df.index.str.contains('　'.join(arg))]
    if not row_found:
        if len(row_df) == 1:
            row = row_df.iloc[0]
        elif len(row_df) > 1:
            for _, df_row in row_df.iterrows():
                if ' '.join(arg).lower() in df_row['Nickname'].split(', '):
                    row = df_row
                    break
            else:
                embed_text_list = row_df['Nickname'].tolist()
                embed.title = 'Too many results. Try the followings:'
                embed.description = ' / '.join(embed_text_list)
                await ctx.send(embed = embed)
                return
    embed.title = f"{wotv_utils.emote_prefix(row)} {row.name}"
    embed_colour = ''
    for col in ('Unit', 'Party', 'Party Max', 'Skill'):
        if row[col] == '':
            continue
        eff_list = row[col].split(' / ')
        eff_list_processed = []
        eff_prefix = ''
        for eff in eff_list:
            match_brackets = wotv_utils.reb.findall(eff)
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
    embed.set_footer(text=wotv_utils.dicts['embed']['footer'])
    await ctx.send(embed = embed)

@bot.command(aliases=['esper'])
async def wotvesper(ctx, *arg):
    embed = discord.Embed(
        colour = wotv_utils.dicts['embed']['default_colour']
    )
    # Preliminary code for global implementation
    if arg[0] in ['global', 'gl']:
        embed.set_author(
            name = wotv_utils.dicts['embed']['gl_author_name'],
            url = 'https://wotv-calc.com/espers',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        global_bool = 1
        df = dfwotv['gl_esper']
        arg = arg[1:]
    else:
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url = 'https://wotv-calc.com/JP/espers',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        global_bool = 0
        df = dfwotv['esper']
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
        embed.title = args.capitalize()
        # convert arg list to split with | instead
        arg = [a.lower().strip() for a in args.split('|')]
        if len(arg) > 2:
            # Force into mobile mode otherwise can't fit
            mobile_bool = 1
        # Function to find which column the said effect should be
        col, first_arg = wotv_utils.esper_findcol(arg[0])
        if first_arg == 'STAT':
            row_df = df.nlargest(10, col)
        else:
            row_df = df[df[col].str.lower().str.contains(first_arg)]
        tuples_list = [(col, first_arg)]
        if len(arg) > 1:
            for argstr in arg[1:]:
                if argstr.upper() in wotv_utils.dicts['esper_stats']:
                    tuples_list.append((argstr.upper(), 'STAT'))
                else:
                    tuples_list.append(wotv_utils.esper_findcol(argstr))
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
                            re_match = wotv_utils.ren.findall(eff)
                            row_list.append(re_match[0])
                else:
                    row_list.append('-')
            list_lists.append(row_list)
        # Sort list
        list_lists.sort(key=lambda a: int(a[1]), reverse=True)
        # Print based on display mode
        if mobile_bool:
            for row_list in list_lists:
                field_name = f"{wotv_utils.emote_prefix(row_df.loc[row_list[0]])} {row_list[0]}"
                field_list = []
                for argname, argvalue in zip(arg, row_list[1:]):
                    if argvalue != '-':
                        field_list.append(f"**{argname.capitalize()}**: {argvalue}")
                embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        else:
            transpose_list = list(map(list, zip(*list_lists)))
            field_list = [f"{wotv_utils.emote_prefix(row_df.loc[a])} {a}" for a in transpose_list[0]]
            embed.add_field(name='Esper', value='\n'.join(field_list), inline=True)
            for field_name, field_list in zip(arg, transpose_list[1:]):
                embed.add_field(name=field_name, value='\n'.join(field_list), inline=True)
    elif arg[0] in ['compare', 'c']:
        # Comparison mode
        if mobile_bool == 0 and arg[1] in ['m', 'mobile']:
            mobile_bool = 1
            args = ' '.join(arg[2:])
        else:
            args = ' '.join(arg[1:])
        embed.title = args.capitalize()
        # convert arg list to split with | instead
        arg = [a.lower().strip() for a in args.split('|')]
        row_list = []
        list_espers = []
        extra_stats = []
        # parse arguments
        for argstr in arg:
            if argstr[0] == '+':
                # additional line
                extra_stats.append(argstr.lstrip('+').lstrip())
            else:
                # find esper
                row_df = df[df.index.str.lower() == argstr]
                if len(row_df) == 0:
                    row_df = df[df.index.str.lower().str.contains(argstr)]
                if len(row_df) == 0:
                    row_df = df[argstr in df['Nickname'].str.split(', ')]
                if len(row_df) == 0:
                    row_df = df[df['Nickname'].str.contains(argstr)]
                if len(row_df) == 1:
                    row_list.append(row_df.iloc[0])
                    list_espers.append(f"{wotv_utils.emote_prefix(row_df.iloc[0])} {row_df.iloc[0].name}")
        if len(list_espers) > 2:
            # Force into mobile mode otherwise can't fit
            mobile_bool = 1
        tuples_list = [wotv_utils.esper_findcol(a) for a in extra_stats]
        list_stats = []
        # Process each esper
        for row in row_list:
            row_stats = [str(row[col]) for col in wotv_utils.dicts['esper_stats']]
            for tupcol, tuparg in tuples_list:
                if tuparg in row[tupcol].lower():
                    eff_list = row[tupcol].split(' / ')
                    for eff in eff_list:
                        if tuparg in eff.lower():
                            re_match = wotv_utils.ren.findall(eff)
                            row_stats.append(re_match[0])
                else:
                    row_stats.append('-')
            list_stats.append(row_stats)
        # Print based on display mode
        if mobile_bool:
            transpose_list = list(map(list, zip(*list_stats)))
            embed.add_field(name='Stat', value=' | '.join(list_espers), inline=False)
            for field_name, stat_list in zip(wotv_utils.dicts['esper_stats'] + extra_stats, transpose_list):
                field_list = [str(a) for a in stat_list]
                embed.add_field(name=field_name, value=' | '.join(field_list), inline=False)
        else:
            embed.add_field(name='Stat', value='\n'.join(wotv_utils.dicts['esper_stats'] + extra_stats), inline=True)
            for field_name, stat_list in zip(list_espers, list_stats):
                field_list = [str(a) for a in stat_list]
                embed.add_field(name=field_name, value = '\n'.join(field_list), inline=True)
    else:
        # Esper info mode
        row_df = df[df.index.str.lower() == ' '.join(arg).lower()]
        if len(row_df) == 0:
            row_df = df[df.index.str.lower().str.contains(' '.join(arg).lower())]
        if len(row_df) == 0:
            row_df = df[[' '.join(arg).lower() in row['Nickname'].split(', ') for _, row in df.iterrows()]]
        if len(row_df) == 0:
            row_df = df[df['Nickname'].str.contains(' '.join(arg).lower())]
        row = row_df.iloc[0]
        embed.colour = wotv_utils.dicts['colours'][row['Element'].lower()]
        embed.title = f"{wotv_utils.emote_prefix(row)} {row.name}"
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
        for col, suffix in [('ATK Up', 'ATK'), ('Killer', 'Killer'), ('Stat Up', ''), ('RES Up', 'RES')]:
            if row[col] != '':
                eff_list = row[col].split(' / ')
                for eff in eff_list:
                    re_match = wotv_utils.ren.search(eff)
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
        if global_bool:
            calc_url = f"https://wotv-calc.com/esper/{row.name.lower().replace(' ', '-')}"
        else:
            calc_url = f"https://wotv-calc.com/JP/esper/{row.name.lower().replace(' ', '-')}"
        embed.add_field(name='WOTV CALC', value=calc_url, inline=False)
    embed.set_footer(text=wotv_utils.dicts['embed']['footer'])
    await ctx.send(embed = embed)

#####################################################
### OCTOPATH TRAVELER: CHAMPIONS OF THE CONTINENT ###
#####################################################
# Work paused because lack of data / interest in practical use

@bot.command(aliases=['cr'])
async def cotcrank(ctx, *arg):
    embed = discord.Embed()
    embed.set_author(
        name = 'オクトパストラベラー 大陸の覇者',
        icon_url = 'https://caelum.s-ul.eu/iNkqSeQ7.png'
    )
    argstr_col = ''
    argstr_jp = ''
    argstr_en = ''
    for col in cotc_dicts['cols'].keys():
        for k, v in cotc_dicts[col].items():
            if arg[0].lower() in v or arg[0] == k:
                argstr_jp = k
                argstr_en = v[0]
                argstr_col = col
                break
        else:
            continue
        break
    df = df_cotc[df_cotc[argstr_col] == argstr_jp]
    if argstr_col == '影響力':
        embed.title = f"List of {argstr_en} travelers:"
        desc_text = []
        for _, row in df.iterrows():
            desc_text.append(get_cotc_label(row))
        embed.description = '\n'.join(desc_text)
    else:
        aoe = 0
        aoestr = ''
        if len(arg) > 1:
            if arg[1].lower() in ['aoe', '全体', '全']:
                aoe = 1
                aoestr = 'AoE '
        if argstr_col == '属性':
            embed.title = f"Ranking of {aoestr}{argstr_en} attacks:"
            embed.colour = cotc_dicts['colours'][argstr_en]
        else:
            embed.title = f"Ranking of {aoestr}{cotc_dicts[argstr_col][argstr_jp][1]} attacks:"
            embed.colour = wotv_utils.dicts['embed']['default_colour']
        hits_ranked, power_ranked = get_sorted_df(df, argstr_col, aoe=aoe)
        field_name = "Shield breaking:"
        field_value = '\n'.join([f"{a} - {b}" for a, b in hits_ranked])
        embed.add_field(name=field_name, value=field_value, inline=True)
        field_name = "Damage mod:"
        field_value = '\n'.join([f"{a} - {b}" for a, b in power_ranked])
        embed.add_field(name=field_name, value=field_value, inline=True)
    await ctx.send(embed = embed)

@bot.command(aliases=['cs'])
async def cotcsupport(ctx, *arg):
    embed = discord.Embed()
    embed.set_author(
        name = 'オクトパストラベラー 大陸の覇者',
        icon_url = 'https://caelum.s-ul.eu/iNkqSeQ7.png'
    )
    argstr_jp = ''
    argstr_en = ''
    for k, v in cotc_dicts['support'].items():
        if arg[0].lower() in v or arg[0] == k:
            argstr_jp = k
            argstr_en = v[0]
            break
    df = df_cotc[df_cotc[argstr_jp] != '']
    aoe = 0
    aoestr = ''
    kw = ''
    kwstr = ''
    if len(arg) > 1:
        if arg[1].lower() in ['aoe', '全体', '全']:
            aoe = 1
            aoestr = 'AoE '
            if len(arg) > 2:
                kw = arg[2] # Japanese only for now
                kwstr = kw + ' '
        else:
            kw = arg[1] # Japanese only for now
            kwstr = kw + ' '
            if len(arg) > 2:
                if arg[2].lower() in ['aoe', '全体', '全']:
                    aoe = 1
                    aoestr = 'AoE '
    embed.title = f"List of {aoestr}{kw}{argstr_en}s:"
    if argstr_en == 'universal':
        embed.colour = wotv_utils.dicts['embed']['default_colour']
    else:
        embed.colour = cotc_dicts['colours'][argstr_en]
    embed.description = get_support_df(df, argstr_jp, aoe=aoe, kw=kw)
    await ctx.send(embed = embed)

@bot.command(aliases=['ct'])
async def cotctraveler(ctx, *arg):
    embed = discord.Embed()
    embed.set_author(
        name = 'オクトパストラベラー 大陸の覇者',
        icon_url = 'https://caelum.s-ul.eu/iNkqSeQ7.png'
    )
    row = df_cotc.loc[arg[0]]
    embed.title = get_cotc_label(row)
    embed.colour = cotc_dicts['colours'][cotc_dicts['属性'][row['属性']][0]]
    field_name_icons = {
        'Passive Abilities': cotc_dicts['emotes']['passive'],
        'Physical Attacks': cotc_dicts['emotes'][cotc_dicts['ジョブ'][row['ジョブ']][0]],
        'Elemental Attacks': cotc_dicts['emotes'][cotc_dicts['属性'][row['属性']][0]]
    }
    for k, v in cotc_dicts['traveler'].items():
        field_name = f"{field_name_icons[k]} {k}"
        field_list = []
        for v_k, v_v in v.items():
            if row[v_k] != '':
                field_list.append(f"{v_v}: {row[v_k]}")
        field_value = '\n'.join(field_list)
        embed.add_field(name=field_name, value=field_value, inline=True)
    field_name = 'Supportive Abilities'
    field_list = []
    for k, v in cotc_dicts['Supportive Abilities'].items():
        if row[k] != '':
            field_list.append(f"{cotc_dicts['emotes'][v[1]]} {v[0]}: {row[k]}")
    field_value = '\n'.join(field_list)
    embed.add_field(name=field_name, value=field_value, inline=True)
    await ctx.send(embed = embed)

fp = open(f"token.txt")
token = fp.read().rstrip('\n')
fp.close()
bot.run(token)
