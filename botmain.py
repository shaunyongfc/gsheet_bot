import discord
import pandas as pd
from discord.ext import commands
from gsheet_handler import df_wotvmats, df_cotc, df_wotvvc
from wotv_processing import wotv_dicts, wotv_type_convert
from cotc_processing import cotc_dicts, get_cotc_label, get_sorted_df, get_support_df

bot = commands.Bot(command_prefix='=')

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")

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
        elif len(arg) == 2:
            embed.title = arg[1]
            for name, row in df_wotvmats.iterrows():
                if row['Type'] == arg[1]:
                    type_str = wotv_type_convert(row['Type'])
                    field_name = f"{wotv_dicts['emotes'][row['Rarity'].lower()]}{wotv_dicts['emotes'][type_str]} {name}"
                    field_value = f"- {row['Special']}"
                    embed.add_field(name=field_name, value=field_value, inline=True)
        else:
            await ctx.send('Error! Please try again!')
            return
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
        'Party Effect': [],
        'Party Effect Max': [],
        'Unit Effect': []
    }
    embed.title = ' '.join(arg)
    args = ' '.join(arg).lower()
    for k, v in wotv_dicts['colours'].items():
        if k in args:
            embed.colour = v
            break
    for index, row in df_wotvvc.iterrows():
        for col in effects_dict.keys():
            eff_list = row[col].split(' / ')
            eff_prefix = wotv_dicts['emotes']['neutral']
            for eff in eff_list:
                if eff[0] == '[':
                    for k, v in wotv_dicts['brackets'].items():
                        if k in eff:
                            eff_prefix = f"{wotv_dicts['emotes'][v]}"
                            break
                    else:
                        eff_prefix = eff[:(eff.index(']') + 1)]
                if args in eff.lower():
                    effects_dict[col].append(f"{eff_prefix}{wotv_dicts['emotes'][row['Rarity'].lower()]} {row.name} ({row['Nickname']})")
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
        df_row = df_wotvvc[df_wotvvc['Nickname'].str.contains(' '.join(arg).lower())]
        if len(df_row) == 1 or df_row.iloc[0]['Nickname'] == ' '.join(arg).lower():
            row = df_row.iloc[0]
        else:
            embed_text_list = df_row['Nickname'].tolist()
            embed.title = 'Too many results. Try the followings:'
            embed.description = ' / '.join(embed_text_list)
            await ctx.send(embed = embed)
            return
    embed.title = f"{wotv_dicts['emotes'][row['Rarity'].lower()]} {row.name}"
    for col in ['Unit Effect', 'Unit Skill', 'Party Effect', 'Party Effect Max']:
        if row[col] == '':
            continue
        field_name = col
        eff_list = row[col].split(' / ')
        eff_list_processed = []
        embed_colour = ''
        eff_prefix = ''
        for eff in eff_list:
            eff_text = eff
            if eff[0] == '[':
                for k, v in wotv_dicts['brackets'].items():
                    if k in eff:
                        embed_colour = v
                        eff_prefix = f"{wotv_dicts['emotes'][v]} "
                        eff_text = eff.replace(f"{k} ", '')
                        break
                else:
                    cond_end = eff.index(']')
                    eff_prefix = eff[:(cond_end + 2)]
                    eff_text = eff[(cond_end + 2):]
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
