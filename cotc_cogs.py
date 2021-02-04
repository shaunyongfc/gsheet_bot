import discord
import pandas as pd
from discord.ext import commands
from cotc_processing import dfcotc, cotc_dicts, get_cotc_label, get_sorted_df, get_support_df

class CotcGeneral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['cr'])
    async def cotcrank(self, ctx, *arg):
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
        df = dfcotc.cotc[dfcotc.cotc[argstr_col] == argstr_jp]
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

    @commands.command(aliases=['cs'])
    async def cotcsupport(self, ctx, *arg):
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
        df = dfcotc.cotc[dfcotc.cotc[argstr_jp] != '']
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

    @commands.command(aliases=['ct'])
    async def cotctraveler(self, ctx, *arg):
        embed = discord.Embed()
        embed.set_author(
            name = 'オクトパストラベラー 大陸の覇者',
            icon_url = 'https://caelum.s-ul.eu/iNkqSeQ7.png'
        )
        row = dfcotc.cotc.loc[arg[0]]
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
