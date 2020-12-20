import discord
import pandas as pd
from discord.ext import commands

bot_name = 'est'
bot = commands.Bot(command_prefix='=')

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")

@bot.command(aliases = commands_df.loc['eqlist', 'aliases'])
async def eqlist(ctx, *arg):
    eql_textlength = 0
    try:
        arg[0].encode('ascii')
        if arg[0] == 'jp':
            argi = 1
            lgstr = 'jp'
            inlgstr = 'en'
        else:
            argi = 0
            lgstr = 'en'
            inlgstr = 'en'
    except UnicodeEncodeError:
        argi = 0
        lgstr = 'jp'
        inlgstr = 'jp'
    if len(arg) == argi + 2:
        eql_ele = ele_match(arg[argi], inlgstr)
        eql_job = job_match(arg[argi + 1])
    elif len(arg) == argi + 1 and inlgstr == 'jp':
        eql_ele = ele_match(arg[argi][0], inlgstr)
        eql_job = job_match(arg[argi][1:])
    else:
        await ctx.send(eql_err_arg[lgstr])
        return
    eql_title = eqd.df_ele.loc[eql_ele, lgstr]
    if lgstr == 'en':
        eql_title += ' '
    eql_title += eqd.df_job.loc[eql_job, lgstr]
    eql_embed = discord.Embed(
        colour = eql_colour[eql_ele]
    )
    eql_embed.set_author(
        name = eql_title,
        icon_url = eql_jobicon[eql_job]
    )
    eql_df = eqd.df_eq[eql_job][eqd.df_eq[eql_job]['eleid'] == eql_ele]
    eql_textlength += len(eql_title)
    for df_index, df_row in eql_df.iterrows():
        df_name, df_text = read_eq(df_row, lgstr)
        eql_embed.add_field(name = df_name, value = df_text, inline = False)
        eql_textlength += len(df_name) + len(df_text)
    eql_textlength += len(eql_footer[lgstr])
    if bot_name == 'test':
        eql_embed.set_footer(text = str(eql_textlength))
    else:
        eql_embed.set_footer(text = eql_footer[lgstr])
    await ctx.send(embed = eql_embed)

@bot.command(aliases = commands_df.loc['eqfilter', 'aliases'])
async def eqfilter(ctx, *arg):
    try:
        arg[0].encode('ascii')
        if arg[0] == 'jp':
            argi = 1
            lgstr = 'jp'
            inlgstr = 'en'
        else:
            argi = 0
            lgstr = 'en'
            inlgstr = 'en'
    except UnicodeEncodeError:
        argi = 0
        lgstr = 'jp'
        inlgstr = 'jp'
    eql_job = -1
    if len(arg) >= argi + 2:
        eql_job = job_match(arg[argi])
        if eql_job != -1:
            argi += 1
    eff_dfid = eff_match(''.join(arg[argi:]), inlgstr)
    if len(eff_dfid) == 0:
        await ctx.send(eff_notfound[lgstr])
        return
    if eql_job == -1:
        if eff_dfid[0][1:5] == '0001':
            eql_job = 3
        elif eff_dfid[0][1:5] == '0002':
            eql_job = 5
        else:
            eql_job = int(eff_dfid[0][1])
    eql_textlength = 0
    eql_df_list = []
    eql_title_list = []
    for eff_id in eff_dfid:
        eql_title_list.append(read_eff(eff_id, lgstr))
        if len(eff_id) == 5:
            for eff_col in eff_cols:
                eql_df_list.append(eqd.df_eq[eql_job][eqd.df_eq[eql_job][eff_col].str.contains(eff_id, regex = False)])
        else:
            for eff_col in eff_cols:
                eql_df_temp = eqd.df_eq[eql_job][eqd.df_eq[eql_job][eff_col].str.contains(eff_id[0:5], regex = False)]
                param_cursor = 5
                while param_cursor < len(eff_id):
                    eql_df_temp = eql_df_temp[eql_df_temp[eff_col].str.contains(eff_id[param_cursor:param_cursor + 3], regex = False)]
                    param_cursor += 3
                eql_df_list.append(eql_df_temp)
            eql_df_temp = eqd.df_eq[eql_job][eqd.df_eq[eql_job]['aid'].str.contains('a2', regex = False)]
            param_cursor = 5
            while param_cursor < len(eff_id):
                eql_df_temp = eql_df_temp[eql_df_temp['aid'].str.contains(eff_id[param_cursor:param_cursor + 3], regex = False)]
                param_cursor += 3
            eql_df_list.append(eql_df_temp)
    eql_df = pd.concat(eql_df_list)
    eql_df = eql_df.sort_index()
    eql_df = eql_df.drop_duplicates()
    eql_embed = discord.Embed(
        colour = eql_colour[0]
    )
    eql_title = ' / '.join(eql_title_list)
    eql_embed.set_author(
        name = eql_title,
        icon_url = eql_jobicon[eql_job]
    )
    eql_textlength += len(eql_title)
    for df_index, df_row in eql_df.iterrows():
        df_name, df_text = read_eq(df_row, lgstr, ele_display=True)
        eql_embed.add_field(name = df_name, value = df_text, inline=False)
        eql_textlength += len(df_name) + len(df_text)
    eql_textlength += len(eql_footer[lgstr])
    if bot_name == 'test':
        eql_embed.set_footer(text = str(eql_textlength))
    else:
        eql_embed.set_footer(text = eql_footer[lgstr])
    try:
        await ctx.send(embed=eql_embed)
    except discord.HTTPException:
        await ctx.send(f"{eql_specify[lgstr]}\n{' / '.join(eql_title_list)}")

@bot.command(aliases = ['eqf2'])
async def eqfind(ctx, *arg):
    try:
        arg[0].encode('ascii')
        if arg[0] == 'jp':
            argi = 1
            lgstr = 'jp'
        else:
            argi = 0
            lgstr = 'en'
    except UnicodeEncodeError:
        argi = 0
        lgstr = 'jp'
    eql_job = job_match(arg[argi])
    eql_df = eqd.df_eq[eql_job]
    for find_i in arg[argi + 1:]:
        if find_i[0] == 'a':
            eql_df = eql_df[eql_df['aid'].str.contains(find_i, regex = False)]
        elif find_i[0] == 's':
            df_list = []
            for sp_col in sp_cols:
                df_list.append(eql_df[eql_df[sp_col].str.contains(find_i, regex = False)])
            eql_df = pd.concat(df_list)
            eql_df = eql_df.sort_index()
            eql_df = eql_df.drop_duplicates()
        elif find_i[0] == 'e':
            df_list = []
            for eff_col in eff_cols:
                df_list.append(eql_df[eql_df[eff_col].str.contains(find_i, regex = False)])
            eql_df = pd.concat(df_list)
            eql_df = eql_df.sort_index()
            eql_df = eql_df.drop_duplicates()
    eql_embed = discord.Embed(
        colour = eql_colour[0]
    )
    eql_title = ' / '.join(arg[argi + 1:])
    eql_embed.set_author(
        name = eql_title,
        icon_url = eql_jobicon[eql_job]
    )
    for df_index, df_row in eql_df.iterrows():
        df_name, df_text = read_eq(df_row, lgstr, ele_display=True)
        eql_embed.add_field(name = df_name, value = df_text, inline=False)
    eql_embed.set_footer(text = eql_footer[lgstr])
    try:
        await ctx.send(embed=eql_embed)
    except discord.HTTPException:
        await ctx.send(f"{eql_specify[lgstr]}\n{' / '.join(eql_title_list)}")

@bot.command(aliases = commands_df.loc['eqseries', 'aliases'])
async def eqseries(ctx, *arg):
    if len(arg) == 2 and arg[0].isnumeric():
        eql_id = int(arg[0])
        lgstr = arg[1]
    else:
        try:
            arg[0].encode('ascii')
            if arg[0] == 'jp':
                argi = 1
                lgstr = 'jp'
                inlgstr = 'en'
            else:
                argi = 0
                lgstr = 'en'
                inlgstr = 'en'
        except UnicodeEncodeError:
            argi = 0
            lgstr = 'jp'
            inlgstr = 'jp'
        df_eqs = eqd.df_eq0[dfstr_clean(eqd.df_eq0[inlgstr]) == str_clean(''.join(arg[argi:]))]
        if len(df_eqs) == 0:
            df_eq1 = eqd.df_eq0[dfstr_clean(eqd.df_eq0['alias']).str.contains(str_clean(''.join(arg[argi:])), regex=False)]
            df_eq2 = eqd.df_eq0[dfstr_clean(eqd.df_eq0[inlgstr]).str.contains(str_clean(''.join(arg[argi:])), regex=False)]
            df_eqs = pd.concat([df_eq1, df_eq2])
        if len(df_eqs) == 0:
            await ctx.send(ser_notfound[lgstr])
            return
        elif len(df_eqs) > 1:
            serieslist = []
            for df_index, df_row in df_eqs.iterrows():
                serieslist.append(f"{df_row[lgstr]}")
            await ctx.send(f"{eql_specify[lgstr]} {' / '.join(serieslist)}")
            return
        else:
            eql_id = df_eqs.index[0]
    eql_ele = eqd.df_eq0.loc[eql_id, 'eleid']
    eql_title = eqd.df_eq0.loc[eql_id, lgstr]
    if eqd.df_eq0.loc[eql_id, 'slid'] != 0:
        eql_title += f" [{eql_slid[eqd.df_eq0.loc[eql_id, 'slid']]}]"
    eql_embed = discord.Embed(
        colour = eql_colour[eql_ele]
    )
    eql_embed.set_author(
        name = eql_title,
        icon_url = eql_eleicon[eql_ele]
    )
    for i in range(1, 6):
        df_name, df_text = read_eq(eqd.df_eq[i].loc[eql_id, :], lgstr)
        df_name = f"{eql_jobemote[i]} **{eqd.df_job.loc[i, lgstr].rstrip('s')}**"
        eql_embed.add_field(name = df_name, value = df_text, inline = False)
    await ctx.send(embed = eql_embed)

@bot.command(aliases = commands_df.loc['eqindex', 'aliases'])
async def eqindex(ctx, *arg):
    if len(arg) > 0:
        try:
            arg[0].encode('ascii')
            if arg[0] == 'jp':
                argi = 1
                lgstr = 'jp'
            else:
                argi = 0
                lgstr = 'en'
        except UnicodeEncodeError:
            argi = 0
            lgstr = 'jp'
        if len(arg) > argi:
            if arg[argi] in df_index_dict.keys():
                await ctx.send(df_listid(df_index_dict[arg[argi]], lgstr))
                return
            if arg[argi][0] == 'e' and arg[argi][1].isnumeric():
                await ctx.send(df_listeff(arg[argi], lgstr))
                return
    else:
        lgstr = 'en'
    for i in [1, 2, 3, 4]:
        fd_list = []
        df = eqd.df_eq0[eqd.df_eq0['eleid'] == i]
        for df_index, df_row in df.iterrows():
            fd_text = f"{df_index}: {df_row[lgstr]}"
            if df_row['slid'] != 0:
                fd_text += f" [{eql_slid[df_row['slid']]}]"
            fd_list.append(fd_text)
        eqi_embed = discord.Embed(
            description = '\n'.join(fd_list),
            colour = eql_colour[i]
        )
        eqi_embed.set_author(
            name = eqd.df_ele.loc[i, lgstr],
            icon_url = eql_eleicon[i]
        )
        await ctx.author.send(embed = eqi_embed)
    fd_list = []
    df = eqd.df_eq0[eqd.df_eq0['eleid'] == 0]
    for df_index, df_row in df.iterrows():
        fd_text = f"{df_index}: {df_row[lgstr]}"
        if df_row['slid'] != 0:
            fd_text += f" [{eql_slid[df_row['slid']]}]"
        fd_list.append(fd_text)
    eqi_embed = discord.Embed(
        colour = eql_colour[0],
    )
    eqi_embed.set_author(
        name = eqi_name_others[lgstr],
        icon_url = bot.user.avatar_url
    )
    eqi_embed.add_field(
        name = f"**{eql_elemote[0]} {eqd.df_ele.loc[0, lgstr]}**",
        value = '\n'.join(fd_list)
    )
    eqi_embed.add_field(
        name = f"**{eqi_no_index[lgstr]}**",
        value = eqi_no_index_desc[lgstr],
        inline = False
    )
    fd_text = ''
    for i in [1, 2, 3, 4, 5]:
        fd_text = f"{eql_jobemote[i]} **{eqd.df_job.loc[i, lgstr].rstrip('s')}**"
        fd_list = []
        for j in [1, 2, 3, 4, 5]:
            fd_list_text = f"{eql_elemote[eqd.df_eq[i].loc[j, 'eleid']]} {eqd.df_eq[i].loc[j, lgstr]}"
            if eqd.df_eq[i].loc[j, 'slid'] != 0:
                fd_list_text += f" [{eql_slid[eqd.df_eq[i].loc[j, 'slid']]}]"
            fd_list.append(f"{eql_elemote[eqd.df_eq[i].loc[j, 'eleid']]} {eqd.df_eq[i].loc[j, lgstr]}")
        eqi_embed.add_field(
            name = fd_text,
            value = '\n'.join(fd_list)
        )
    await ctx.author.send(embed = eqi_embed)

fp = open(f"{bot_name}oken.txt")
token = fp.read().rstrip('\n')
fp.close()
bot.run(token)
