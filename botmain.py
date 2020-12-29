import discord, re
import pandas as pd
from discord.ext import commands
from gsheet_handler import get_df
from wotv_processing import wotv_dicts, wotv_type_convert
from cotc_processing import cotc_dicts, get_cotc_label, get_sorted_df, get_support_df

bot = commands.Bot(command_prefix='+')
re_brackets = re.compile(r'\[[\w\/]+\]')
re_numbers = re.compile(r'-?\d+$')
df_cotc, df_wotvmats, df_wotvvc, df_wotvshortcut, df_wotvesper = get_df()

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")

bot.remove_command('help')
@bot.command(aliases=['help'])
async def wotvhelp(ctx, *arg):
    embed = discord.Embed(
        colour = 0x999999
    )
    embed.set_author(
        name = 'FFBE幻影戦争',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    embed.title = 'Ildyra Bot Help'
    for k, v in wotv_dicts['help'].items():
        embed.add_field(name=k, value='\n'.join(v), inline=False)
    await ctx.send(embed = embed)

@bot.command()
async def sync(ctx, *arg):
    if ctx.channel.permissions_for(ctx.message.author).manage_guild:
        global df_cotc, df_wotvmats, df_wotvvc, df_wotvshortcut, df_wotvesper
        df_cotc, df_wotvmats, df_wotvvc, df_wotvshortcut, df_wotvesper = get_df()
        await ctx.send('Google sheet synced.')
    else:
        await ctx.send('Error. Permission denied.')

@bot.command(aliases=['wm'])
async def wotvmat(ctx, *arg):
    embed = discord.Embed(
        colour = 0x999999
    )
    embed.set_author(
        name = 'FFBE幻影戦争',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    if arg[0].lower() in ['common', 'c']:
        argstr = 'Common'
    elif arg[0].lower() in ['rare', 'r']:
        argstr = 'Rare'
    elif arg[0].lower() in ['crystal', 'element', 'e']:
        argstr = 'Crystal'
    if len(arg) == 1:
        embed.title = f"List of {argstr.lower()}s"
        embed.description = '\n'.join(wotv_dicts['sets'][argstr])
    elif len(arg) == 2:
        embed.title = arg[1]
        embed_text_list = []
        for name, row in df_wotvmats.iterrows():
            if row[argstr] == arg[1]:
                type_str = wotv_type_convert(row['Type'])
                embed_text_list.append(f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{wotv_dicts['emotes'][type_str]} {name}")
        embed.description = '\n'.join(embed_text_list)
    await ctx.send(embed = embed)

@bot.command(aliases=['we'])
async def wotveq(ctx, *arg):
    embed = discord.Embed(
        colour = 0x999999
    )
    embed.set_author(
        name = 'FFBE幻影戦争',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    if arg[0].lower() in ['type', 't']:
        if len(arg) == 1:
            embed.title = f"List of types"
            embed.description = '\n'.join(wotv_dicts['sets']['Type'])
        else:
            query = ' '.join(arg[1:])
            embed.title = query
            query = query.lower()
            query = query.replace('gs', 'great sword')
            query = query.replace('nb', 'ninja blade')
            query = query.replace('armour', 'armor')
            for name, row in df_wotvmats.iterrows():
                if query in row['Type'].lower():
                    type_str = wotv_type_convert(row['Type'])
                    field_name = f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{wotv_dicts['emotes'][type_str]} {name}"
                    field_value = f"- {row['Special']}"
                    embed.add_field(name=field_name, value=field_value, inline=True)
    elif len(arg) == 1:
        embed.title = arg[0]
        row = df_wotvmats.loc[arg[0]]
        type_str = wotv_type_convert(row['Type'])
        embed.description = f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{wotv_dicts['emotes'][type_str]} {row['Special']}\nAcquisition: {row['Acquisition']}"
        embed_text_list = []
        for col in ['Common', 'Rare', 'Crystal']:
            embed_text_list.append(f"- {row[col]}")
        embed.add_field(name='List of materials', value='\n'.join(embed_text_list), inline=True)
    else:
        await ctx.send('Error! Please try again!')
        return
    await ctx.send(embed = embed)

@bot.command(aliases=['wvs', 'vcs', 'vs'])
async def wotvvcsearch(ctx, *arg):
    embed = discord.Embed(
        colour = 0x999999
    )
    embed.set_author(
        name = 'FFBE幻影戦争',
        url = 'https://wotv-calc.com/JP/cards',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    effects_dict = {
        'Party': [],
        'Party Max': [],
        'Unit': []
    }
    if len(arg) == 1:
        try:
            args = df_wotvshortcut.loc[arg[0].lower()]['Conversion']
        except:
            args = arg[0]
    else:
        args = ' '.join(arg)
    embed.title = args.capitalize()
    args = args.lower()
    args = args.replace('lightning', 'thunder')
    for k, v in wotv_dicts['colours'].items():
        if k in args:
            embed.colour = v
            break
    for index, row in df_wotvvc.iterrows():
        for col in effects_dict.keys():
            eff_list = row[col].split(' / ')
            eff_prefix = wotv_dicts['emotes']['neutral']
            for eff in eff_list:
                eff_suffix = ''
                match_brackets = re_brackets.findall(eff)
                if len(match_brackets) == 1:
                    if match_brackets[0] in wotv_dicts['brackets'].keys():
                        eff_prefix = wotv_dicts['emotes'][wotv_dicts['brackets'][match_brackets[0]]]
                    else:
                        eff_prefix = match_brackets[0]
                match_numbers = re_numbers.findall(eff)
                if len(match_numbers) == 1:
                    eff_suffix = ' ' + match_numbers[0]
                if args in eff.lower():
                    if row['Limited'] != '':
                        eff_prefix2 = wotv_dicts['emotes']['limited']
                    else:
                        eff_prefix2 = ''
                    effects_dict[col].append(f"{eff_prefix}{wotv_dicts['emotes'][row['Rarity'].lower()]}{eff_prefix2} {row.name} ({row['Nickname']}){eff_suffix}")
    for k, v in effects_dict.items():
        if len(v) > 0:
            field_name = k
            field_value = '\n'.join(v)
            embed.add_field(name=field_name, value=field_value, inline=False)
    embed.set_footer(text='Data Source: WOTV-CALC (Bismark)')
    try:
        await ctx.send(embed = embed)
    except discord.HTTPException:
        await ctx.send('Too many results. Please refine the search.')

@bot.command(aliases=['wve', 'vce', 've'])
async def wotvvcelement(ctx, *arg):
    embed = discord.Embed()
    embed.set_author(
        name = 'FFBE幻影戦争',
        url = 'https://wotv-calc.com/JP/cards',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    effects_dict = {
        'Party': [],
        'Party Max': []
    }
    ele = arg[0].lower().replace('lightning', 'thunder')
    embed.title = f"{wotv_dicts['emotes'][ele]} {arg[0].capitalize()}"
    embed.colour = wotv_dicts['colours'][ele]
    for index, row in df_wotvvc.iterrows():
        for col in effects_dict.keys():
            eff_list = row[col].split(' / ')
            ele_found = 0
            for eff in eff_list:
                if ele_found or wotv_dicts['brackets'][ele] in eff:
                    ele_found = 1
                    if row['Limited'] != '':
                        eff_prefix2 = wotv_dicts['emotes']['limited']
                    else:
                        eff_prefix2 = ''
                    effects_dict[col].append(f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{eff_prefix2} {row.name} ({row['Nickname']}) {eff.replace(wotv_dicts['brackets'][ele] + ' ', '')}")
    for k, v in effects_dict.items():
        if len(v) > 0:
            field_name = k
            field_value = '\n'.join(v)
            embed.add_field(name=field_name, value=field_value, inline=False)
    embed.set_footer(text='Data Source: WOTV-CALC (Bismark)')
    await ctx.send(embed = embed)

@bot.command(aliases=['wv', 'vc'])
async def wotvvc(ctx, *arg):
    embed = discord.Embed(
        colour = 0x999999
    )
    embed.set_author(
        name = 'FFBE幻影戦争',
        url = 'https://wotv-calc.com/JP/cards',
        icon_url = 'https://caelum.s-ul.eu/1OLnhC15.png'
    )
    try:
        row = df_wotvvc.loc['　'.join(arg)]
    except KeyError:
        row_df = df_wotvvc[df_wotvvc['Nickname'].str.contains(' '.join(arg).lower())]
        if len(row_df) == 1:
            row = row_df.iloc[0]
        elif len(row_df) > 1:
            for index, df_row in row_df.iterrows():
                if df_row['Nickname'] == ' '.join(arg).lower():
                    row = df_row
                    break
            else:
                embed_text_list = row_df['Nickname'].tolist()
                embed.title = 'Too many results. Try the followings:'
                embed.description = ' / '.join(embed_text_list)
                await ctx.send(embed = embed)
                return
    if row['Limited'] != '':
        embed.title = f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{wotv_dicts['emotes']['limited']} {row.name}"
    else:
        embed.title = f"{wotv_dicts['emotes'][row['Rarity'].lower()]} {row.name}"
    for col in ['Unit', 'Party', 'Party Max', 'Skill']:
        if row[col] == '':
            continue
        field_name = col
        eff_list = row[col].split(' / ')
        eff_list_processed = []
        embed_colour = ''
        eff_prefix = ''
        for eff in eff_list:
            match_brackets = re_brackets.findall(eff)
            if len(match_brackets) == 1:
                if match_brackets[0] in wotv_dicts['brackets'].keys():
                    eff_prefix = wotv_dicts['emotes'][wotv_dicts['brackets'][match_brackets[0]]] + ' '
                    embed_colour = wotv_dicts['brackets'][match_brackets[0]]
                else:
                    eff_prefix = match_brackets[0] + ' '
                eff_text = eff.replace(match_brackets[0] + ' ', '')
            else:
                eff_text = eff
            eff_list_processed.append(f"{eff_prefix}{eff_text}")
        field_value = '\n'.join(eff_list_processed)
        embed.add_field(name=field_name, value=field_value)
    if row['Url'] != '':
        embed.set_thumbnail(url=row['Url'])
    if embed_colour != '':
        embed.colour = wotv_dicts['colours'][embed_colour]
    embed.set_footer(text='Data Source: WOTV-CALC (Bismark)')
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
        for index, row in df.iterrows():
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
            embed.colour = 0x999999
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
        embed.colour = 0x999999
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
