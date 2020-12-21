import discord
import pandas as pd
from discord.ext import commands
from gsheet_handler import df_wotv
from wotv_processing import wotv_sets, wotv_emotes, wotv_type_convert

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
    else:
        await ctx.send('Error! Please try again!')
        return
    if len(arg) == 1:
        embed.title = f"List of {argstr.lower()}s"
        embed.description = '\n'.join(wotv_sets[argstr])
    elif len(arg) == 2:
        embed.title = arg[1]
        embed_text_list = []
        for name, row in df_wotv.iterrows():
            if row[argstr] == arg[1]:
                type_str = wotv_type_convert(row['Type'])
                embed_text_list.append(f"{wotv_emotes[row['Rarity'].lower()]}{wotv_emotes[type_str]} {name}")
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
            embed.description = '\n'.join(wotv_sets['Type'])
        elif len(arg) == 2:
            embed.title = arg[1]
            for name, row in df_wotv.iterrows():
                if row['Type'] == arg[1]:
                    type_str = wotv_type_convert(row['Type'])
                    field_name = f"{wotv_emotes[row['Rarity'].lower()]}{wotv_emotes[type_str]} {name}"
                    field_value = f"- {row['Special']}"
                    embed.add_field(name=field_name, value=field_value, inline=False)
        else:
            await ctx.send('Error! Please try again!')
            return
    elif len(arg) == 1:
        embed.title = arg[0]
        row = df_wotv.loc[arg[0]]
        type_str = wotv_type_convert(row['Type'])
        embed.description = f"{wotv_emotes[row['Rarity'].lower()]}{wotv_emotes[type_str]} {row['Special']}"
        embed_text_list = []
        for col in ['Common', 'Rare', 'Crystal']:
            embed_text_list.append(f"- {row[col]}")
        embed.add_field(name='List of materials', value='\n'.join(embed_text_list), inline=False)
    else:
        await ctx.send('Error! Please try again!')
        return
    await ctx.send(embed = embed)

fp = open(f"token.txt")
token = fp.read().rstrip('\n')
fp.close()
bot.run(token)
