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
        self.statlist2 = ('ATK', 'MAG', 'DEF', 'SPR', 'AGI')
        self.spreadsheet = client.open("Engelbert Bot")
        self.dfdict = dict()
        self.dfsync()
        self.jobjp_init()
    def dfsync(self):
        # sync online sheet into local data
        for sheetname, indexname in self.sheettuples:
             df = pd.DataFrame(self.spreadsheet.worksheet(sheetname).get_all_records())
             if indexname != '':
                 df = df.set_index(indexname)
             self.dfdict[sheetname] = df
    def sheetsync(self, logsync=0):
        # sync local data into online sheet
        set_with_dataframe(self.spreadsheet.worksheet('User'), self.dfdict['User'], include_index=True)
        if logsync:
            set_with_dataframe(self.spreadsheet.worksheet('Log'), self.dfdict['Log'], include_index=False)
    def new_log(self, event, user, timestamp):
        # write a new log
        new_log = {
            'Event': event,
            'User': user,
            'Timestamp': timestamp
        }
        self.spreadsheet.worksheet('Log').append_row(list(new_log.values()))
        self.dfdict['Log'] = self.dfdict['Log'].append(new_log, ignore_index=True)
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
                kill = self.userdamage(defender, damage)
                if kill:
                    jp_gain += defenddict['Level'] # bonus JP for killing
            if self.dfdict['User'].loc[defender, 'AP'] < defenddict['AP']:
                self.dfdict['User'].loc[defender, 'AP'] = self.dfdict['User'].loc[defender, 'AP'] + 1
            replystr += (f"\nGained {jp_gain} JP!")
            self.dfdict['User'].loc[attacker, 'JP'] = self.dfdict['User'].loc[attacker, 'JP'] + jp_gain # gains JP
            self.sheetsync()
        print(replystr)
    def userdamage(self, defender, damage):
        # function for a user to take damage
        self.dfdict['User'].loc[defender, 'HP'] = int(max(self.dfdict['User'].loc[defender, 'HP'] - damage, 0))
        if self.dfdict['User'].loc[defender, 'HP'] == 0:
            self.new_log('userdead', defender, datetime.strftime(datetime.now(), mydtformat))
            return 1
        else:
            return 0
    def userregenall(self, now=None):
        # hourly automatic regen for all
        if now != None:
            self.new_log('hourlyregen', '', datetime.strftime(now, mydtformat))
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
    def userrevive(self, index):
        # revives dead user and logs it
        user = self.dfdict['Log'].loc[index, 'User']
        self.dfdict['User'].loc[user, 'HP'] = self.calcstats(user)['HP']
        print(f"{user} revived!")
        self.dfdict['Log'].loc[index, 'Event'] = 'userrevived'
        self.dfdict['Log'].loc[index, 'Timestamp'] = datetime.strftime(datetime.now(), mydtformat)
        self.sheetsync(logsync=1)
    ############################
    # discord embed generators #
    ############################
    def listbase(self):
        # generate embed of list of available bases
        embed = discord.Embed()
        embed.title = 'List of Bases'
        df = self.dfdict['Base'][self.dfdict['Base']['Hidden'] == '']
        job_list = []
        job_count = 0
        for index, row in df.iterrows():
            disc_list = []
            for stat in self.statlist2:
                disc_list.append(f"{stat}: {row[stat]}")
            disc_list.append(f"Starting Job: {row['Job']}")
            job_list.append(f"**{index}**: {' | '.join(disc_list)}")
            job_count += 1
            if job_count % 10 == 0:
                if job_count // 10 > 0:
                    embed.add_field(name='Cont.', value='\n'.join(job_list))
                else:
                    embed.description = '\n'.join(job_list)
                job_list = []
        if len(job_list) > 0:
            if job_count // 10 > 0:
                embed.add_field(name='Cont.', value='\n'.join(job_list))
            else:
                embed.description = '\n'.join(job_list)
        return embed
    def infouser(self, row):
        # generate info embed of specific user
        embed = discord.Embed()
        embed.title = row.name
        disc_list = []
        disc_list.append(f"Base: {row['Base']} (+{userdict['Level']})")
        userdict = self.calcstats(row.name)
        disc_list.append(f"HP: {row['HP']}/{userdict['HP']}")
        disc_list.append(f"AP: {row['AP']}/{userdict['AP']}")
        disc_list.append(f"JP: {row['JP']}")
        embed.description = '\n'.join(disc_list)
        field_list = []
        for stat in self.statlist2:
            field_list.append(f"{stat}: {userdict[stat]}")
        embed.add_field(name='Stats', value='\n'.join(field_list))
        thumbnail_url = self.dfdict['Base'].loc[row['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        return embed


engel = Engel()
mydtformat = '%Y/%m/%d %H:%M'

class Engelbert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timercheck.start()

    @tasks.loop(minutes=1.0)
    async def timercheck(self):
        # check timer every minute
        now = datetime.now()
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'hourlyregen']
        thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(hours=1)
        if now.minute == 0 or now > thres:
            engel.userregenall(now)
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'userdead']
        thres = now  - timedelta(hours=5)
        for index, row in df.iterrows():
            thres = datetime.strptime(row['Timestamp'], mydtformat) + timedelta(hours=6)
            if now > thres:
                engel.userrevive(index)

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama'])
    async def engelbert(self, ctx, *arg):
        # main function
        if len(arg) == 0:
            await ctx.send('Nice try 1.') # to be implemented with proper help function
        else:
            if arg[0] == 'info':
                if len(arg) == 1:
                    # own info
                    try:
                        row = engel.dfdict['User'].loc[ctx.author.id]
                        await ctx.send(engel.infouser(row))
                    except KeyError:
                        await ctx.send('Nice try 2.') # to be implemented with proper starter stuff
                else:
                    try:
                        # to be implemented with finding member
                        row = engel.dfdict['User'].loc[arg[1]]
                        await ctx.send(embed = engel.infouser(row))
                    except KeyError:
                        await ctx.send('Nice try 3.') # to be implemented with proper suggestion
            elif arg[0] == 'base':
                if len(arg) == 1:
                    # list of bases
                    await ctx.send(embed = engel.listbase())
                else:
                    # various operations
                    # find base and info
                    # change base
                    # start of tamagotchi
                    pass
            elif arg[0] == 'job':
                if len(arg) == 1:
                    # list of jobs
                    pass
                else:
                    # various operations
                    # find job and info
                    # level job
                    # reset job
                    pass
            elif arg[0] == 'attack':
                if len(arg) == 1:
                    # ???
                    pass
                else:
                    # find member of said name to attack
                    pass
            elif arg[0] == 'raid':
                # to be implemented
                if len(arg) == 1:
                    # available raids
                    pass
                else:
                    # find raid and info
                    # attack raid
                    pass
            else:
                await ctx.send('Nice try.') # to be implemented with proper help function
