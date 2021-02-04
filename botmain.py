import discord
from discord.ext import commands
from general_cogs import GeneralCommands, TestCommands
from wotv_cogs import WotvGeneral, WotvEquipment, WotvVc, WotvEsper
#from cotc_cogs import CotcGeneral
from engelbert import Engelbert

bot = commands.Bot(command_prefix='+')

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

bot.add_cog(TestCommands(bot))
bot.add_cog(GeneralCommands(bot))
bot.add_cog(WotvGeneral(bot))
bot.add_cog(WotvEquipment(bot))
bot.add_cog(WotvVc(bot))
bot.add_cog(WotvEsper(bot))
#bot.add_cog(CotcGeneral(bot))
bot.add_cog(Engelbert(bot))

with open(f"token.txt") as fp:
    token = fp.read().rstrip('\n')
bot.run(token)
