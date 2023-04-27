import discord
from discord.ext import commands

from general_cogs import GeneralCommands, TestCommands, BotLog
from wotv_cogs import WotvGeneral, WotvUnit, WotvEquipment, WotvVc, WotvEsper


def main():
    bot = commands.Bot(command_prefix='+')

    @bot.event
    async def on_ready():
        """Bot login function."""
        print(f"We have logged in as {bot.user}")
        await bot.change_presence(activity = discord.Game(name = '幻影の覇者'))

    bot_log = BotLog(bot)
    # bot load cogs.
    bot.add_cog(TestCommands(bot))
    bot.add_cog(GeneralCommands(bot, bot_log))
    bot.add_cog(WotvGeneral(bot, bot_log))
    bot.add_cog(WotvEquipment(bot, bot_log))
    bot.add_cog(WotvUnit(bot, bot_log))
    bot.add_cog(WotvVc(bot, bot_log))
    bot.add_cog(WotvEsper(bot, bot_log))

    bot.run(bot_log.token)


if __name__ == "__main__":
    main()
