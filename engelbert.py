import re, random, discord
import pandas as pd
from discord.ext import commands, tasks
from gsheet_handler import client
from gspread_dataframe import set_with_dataframe
from id_dict import id_dict
from datetime import datetime, timedelta

# experimental project on Discord bot tamagotchi, codenamed Engelbert

class Engel:
    # utility class that contains the utility functions and parameters
    def __init__(self):
        # gameplay constants
        self.attack_apcost = 3
        self.hpregen = 0.05
        self.apregen = 0.1
        self.sheettuples = (
            ('Base', 'Base'),
            ('Job', 'JobID'),
            ('User', 'User'),
            ('Log', '')
        )
        self.statlist = ('HP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'AGI')
        self.spreadsheet = client.open("Engelbert Bot")
        self.dfdict = dict()
        self.dfsync()
        self.jobjp_init()
    def dfsync(self):
        # sync online sheet into local data
        for sheetname, indexname in self.sheettuples:
             df = pd.DataFrame(self.spreadsheet.worksheet(sheetname).get_all_records())
             df['row'] = df.index + 2
             if indexname != '':
                 df = df.set_index(indexname)
             self.dfdict[sheetname] = df
    def sheetsync(self):
        # sync local data into online sheet
        set_with_dataframe(self.spreadsheet.worksheet('User'), self.dfdict['User'].drop('row', axis=1), include_index=True)
    def jobjp_init(self):
        # initialize job level - JP table
        basejp = 10
        levelcap = 10
        self.jobjp = dict()
        for i in range(levelcap):
            self.jobjp[i] = basejp + (i * (i + 1)) // 2
    def calchitrate(self, avoid):
        # calculate hit rate from agi difference
        if avoid < 1:
            return 1
        else:
            return max(1 - avoid * 0.05, 0)
    def calcstats(self, user):
        # calculate stats given user id
        userdict = dict()
        level = 0
        for statname in self.statlist:
            userdict[statname] = self.dfdict['Base'].loc[self.dfdict['User'].loc[user, 'Base'], statname]
        for index, row in self.dfdict['Job'].iterrows():
            if index in self.dfdict['User'].columns:
                if self.dfdict['User'].loc[user, index] != '':
                    for statname in self.statlist:
                        userdict[statname] += row[statname] * self.dfdict['User'].loc[user, index]
                    level += self.dfdict['User'].loc[user, index]
        userdict['Level'] = level
        return userdict
    def userattack(self, attacker, defender):
        # perform an attack between users
        replystr = ''
        if self.dfdict['User'].loc[attacker, 'AP'] < self.attack_apcost:
            replystr = 'Not enough AP!'
        elif self.dfdict['User'].loc[defender, 'HP'] == 0:
            replystr = 'Target is dead!'
        else:
            # get their status sheets
            attackdict = self.calcstats(attacker)
            defenddict = self.calcstats(defender)
            jp_gain = 1 # base JP gain
            # consumes AP
            self.dfdict['User'].loc[attacker, 'AP'] = int(self.dfdict['User'].loc[attacker, 'AP'] - self.attack_apcost)
            # pick higher potential damage
            damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
            hitrate = self.calchitrate(defenddict['AGI'] - attackdict['AGI'])
            if hitrate < random.random():
                replystr = 'Attack missed!'
            else:
                replystr = f"{damage} damage!"
                jp_gain += (damage + defenddict['Level']) // 10 # bonus JP for damage
                self.dfdict['User'].loc[defender, 'HP'] = int(max(self.dfdict['User'].loc[defender, 'HP'] - damage, 0))
                if self.dfdict['User'].loc[defender, 'HP'] == 0:
                    jp_gain += defenddict['Level'] # bonus JP for killing
            if self.dfdict['User'].loc[defender, 'AP'] < defenddict['AP']:
                self.dfdict['User'].loc[defender, 'AP'] = self.dfdict['User'].loc[defender, 'AP'] + 1
            replystr += (f"\nGained {jp_gain} JP!")
            self.dfdict['User'].loc[attacker, 'JP'] = self.dfdict['User'].loc[attacker, 'JP'] + jp_gain # gains JP
            self.sheetsync()
        return replystr
    def regenall(self):
        # hourly automatic regen for all
        for index, row in self.dfdict['User'].iterrows():
            userdict = self.calcstats(index)
            if row['AP'] < userdict['AP']: # if AP is not full
                new_ap = min(row['AP'] + int(userdict['AP'] * self.apregen), userdict['AP'])
                self.dfdict['User'].loc[index, 'AP'] = new_ap
                hp_recovery = int(userdict['HP'] * self.hpregen)
            else: # doubles HP regen if AP is full
                hp_recovery = int(userdict['HP'] * self.hpregen * 2)
            if 0 < row['HP'] < userdict['HP']:
                new_hp = min(row['HP'] + hp_recovery, userdict['HP'])
                self.dfdict['User'].loc[index, 'HP'] = new_hp
            # gains JP passively too
            self.dfdict['User'].loc[index, 'JP'] = self.dfdict['User'].loc[index, 'JP'] + 1 + userdict['Level'] // 10
        self.sheetsync()
    def hourlyregen(self, now):
        self.regenall()
        self.spreadsheet.worksheet('Log').append_row('hourlyregen', [datetime.strftime(now)])
        self.dfdict['Log'] = pd.DataFrame(self.spreadsheet.worksheet('Log').get_all_records())

engel = Engel()
mydtformat = '%Y/%m/%d %H:%M'

class Engelbert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #self.hourlyregen.start()

    @tasks.loop(minutes=1.0)
    async def hourlyregen(self):
        now = datetime.now()
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'hourlyregen']
        thres = datetime.strptime(df[-1]['Timestamp'], mydtformat) + timedelta(hours=1)
        if now.minute == 0 or now > thres:
            engel.hourlyregen()

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama'])
    async def engelbert(self, ctx, *arg):
        if len(arg) == 0:
            pass
