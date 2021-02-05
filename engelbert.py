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
        self.levelcap = 10
        self.sheettuples = (
            ('Base', 'Base'),
            ('Job', 'JobID'),
            ('User', 'User'),
            ('Log', '')
        )
        self.statlist = ('HP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'AGI')
        self.statlist2 = ('ATK', 'MAG', 'DEF', 'SPR', 'AGI')
        self.statrating = {
            5: 'A',
            4: 'B',
            3: 'C',
            2: 'D',
            1: 'E'
        }
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
        df = self.dfdict['User'].copy()
        df.index = df.index.astype(str)
        set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
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
        self.jobjp = dict()
        self.jobjpsum = dict()
        jpsum = 0
        for i in range(self.levelcap):
            self.jobjp[i] = basejp + (i * (i + 1)) // 2
            jpsum += basejp + (i * (i + 1)) // 2
            self.jobjpsum[i] = jpsum
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
            jp_gain = 2 # base JP gain
            # consumes AP
            self.dfdict['User'].loc[attacker, 'AP'] = int(self.dfdict['User'].loc[attacker, 'AP'] - self.attack_apcost)
            # pick higher potential damage
            damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
            hitrate = self.calchitrate(defenddict['AGI'] - attackdict['AGI'])
            if hitrate < random.random():
                replystr = 'Attack missed!'
            else:
                replystr = f"{damage} damage!"
                jp_gain += (damage + defenddict['Level']) // 5 # bonus JP for damage
                kill = self.userdamage(defender, damage)
                if kill:
                    jp_gain += defenddict['Level'] # bonus JP for killing
            self.dfdict['User'].loc[defender, 'JP'] = self.dfdict['User'].loc[defender, 'JP'] + 1 + attackdict['Level'] // 10
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
    def userjoblevel(self, user, job, level=1):
        # raises user job levels
        jobid = self.dfdict['Job'][self.dfdict['Job']['Job'] == job].tail(1).index.tolist()[0]
        userrow = self.dfdict['User'].loc[user]
        available_jp = userrow['JP']
        job_level = userrow[jobid]
        if job_level == '':
            job_level = 0
        job_level_0 = job_level
        for i in range(level):
            if job_level == self.levelcap:
                break
            if available_jp >= self.jobjp[job_level]:
                available_jp -= self.jobjp[job_level]
                job_level += 1
            else:
                break
        if job_level > job_level_0:
            self.dfdict['User'].loc[user, jobid] = job_level
            self.dfdict['User'].loc[user, 'JP'] = available_jp
            self.sheetsync()
        return f"{job_level - job_level_0} level(s) raised. Your current available JP is now {available_jp}."
    def userjobreset(self, user):
        # resets user job
        userrow = self.dfdict['User'].loc[user]
        jp_refunded = 0
        for jobid in self.dfdict['Job'].index:
            if userrow[jobid] != '':
                jp_refunded += self.jobjpsum[userrow[jobid]]
                self.dfdict['User'].loc[user, jobid] = ''
        if jp_refunded > 0:
            self.dfdict['User'].loc[user, 'JP'] = self.dfdict['User'].loc[user, 'JP'] + jp_refunded
            self.new_log('userjobreset', user, datetime.strftime(datetime.now(), mydtformat))
            self.sheetsync()
        return f"{jp_refunded} JP refunded!"
    def userbase(self, user, base):
        # changes user or starts a user
        baserow = self.dfdict['Base'].loc[base]
        if user in self.dfdict['User'].index:
            if self.dfdict['User'].loc[user, 'Base'] == base:
                return 'It is your current base!'
            else:
                self.dfdict['User'].loc[user, 'Base'] = base
                replystr = 'Base changed!'
        else:
            new_user = {
                'Base': base,
                'HP': baserow['HP'],
                'AP': baserow['AP'],
                'JP': 0,
                baserow['Starter']: 1
            }
            userrow = pd.Series(data=new_user.values(), index=new_user.keys(), name=user)
            self.dfdict['User'] = self.dfdict['User'].append(userrow).fillna('')
            replystr = 'User registered!'
        self.new_log('userbase', user, datetime.strftime(datetime.now(), mydtformat))    
        self.sheetsync()
        return replystr
    ############################
    # discord embed generators #
    ############################
    def listbase(self):
        # generate embed of list of available bases
        embed = discord.Embed()
        embed.title = 'List of Bases'
        desc = (
            'A base determines your base stats and can be changed every 24 hours.',
            'It also determines your tamagotchi picture where available.',
            'Element or other features may be implemented in future.'
        )
        embed.description = '\n'.join(desc)
        df = self.dfdict['Base'][self.dfdict['Base']['Hidden'] == '']
        base_list = []
        base_count = 0
        for index, row in df.iterrows():
            disc_list = []
            for stat in self.statlist2:
                disc_list.append(f"{stat} `{row[stat]}`")
            disc_list.append(f"Starter: {self.dfdict['Job'].loc[row['Starter'], 'Job']}")
            base_list.append(f"**{index}**\n - {' | '.join(disc_list)}")
            base_count += 1
            if base_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(job_list))
                base_list = []
        if len(base_list) > 0:
            embed.add_field(name='-', value='\n'.join(base_list))
        return embed
    def listjob(self):
        # generate embed of list of available jobs
        embed = discord.Embed()
        embed.title = 'List of Jobs'
        desc = (
            'Leveling a job costs JP and raises your stats according to the job.',
            'Higher job levels require more JP.',
            'Job levels can be reset into JP every 24 hours.',
            'Skills or other features may be implemented in future.'
        )
        embed.description = '\n'.join(desc)
        df = self.dfdict['Job']
        job_list = []
        job_count = 0
        for index, row in df.iterrows():
            disc_list = []
            for stat in self.statlist2:
                disc_list.append(f"{stat} `{self.statrating[row[stat]]}`")
            job_list.append(f"**{row['Job']}**\n - {' | '.join(disc_list)}")
            job_count += 1
            if job_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(job_list))
                job_list = []
        if len(job_list) > 0:
            embed.add_field(name='-', value='\n'.join(job_list))
        return embed
    def infojp(self, user):
        # generate info embed of specific user jobs and jp
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user]
        embed.title = f"{userrow.name} Jobs" # convert ID into actual name...
        embed.description = f"JP: {userrow['JP']}"
        dfjob = self.dfdict['Job']
        job_list = []
        job_count = 0
        for index, row in dfjob.iterrows():
            job_level = userrow[index]
            if job_level == '':
                job_level = 0
            if job_level < self.levelcap:
                next_jp = self.jobjp[job_level]
                jobstr = f"**{row['Job']}**\n - Level `{job_level}` (Next: `{next_jp}` JP)"
                if userrow['JP'] >= next_jp:
                    jobstr += ' **OK**'
                job_list.append(jobstr)
            else:
                job_list.append(f"**{row['Job']}**\n - Level `{job_level}` (MAX)")
            job_count += 1
            if job_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(job_list))
                job_list = []
        if len(job_list) > 0:
            embed.add_field(name='-', value='\n'.join(job_list))
        return embed
    def infouser(self, user):
        # generate info embed of specific user
        embed = discord.Embed()
        row = self.dfdict['User'].loc[user]
        embed.title = row.name # convert ID into actual name...
        disc_list = []
        userdict = self.calcstats(row.name)
        disc_list.append(f"Base: {row['Base']} (+{userdict['Level']})")
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
                    user = ctx.author.id
                else:
                    member = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                    user = member.id
                if user in engel.dfdict['User'].index:
                    await ctx.send(embed = engel.infouser(user))
                else:
                    await ctx.send('Nice try 2.') # to be implemented with proper starter stuff
            elif arg[0] == 'base':
                if len(arg) == 1:
                    # list of bases
                    await ctx.send(embed = engel.listbase())
                else:
                    # various operations
                    if len(arg) > 2 and arg[1] in ('change', 'start'):
                        # change base or start of tamagotchi
                        user = ctx.author.id
                        base = ' '.join(arg[2:])
                        if base in engel.dfdict['Base'].index:
                            await ctx.send(engel.userbase(user, base))
                        else:
                            await ctx.send('Nice try 3.') # to be implemented with proper suggestion
                    else:
                        # find base and info (not needed atm)
                        await ctx.send('Nice try 4.') # to be implemented with proper suggestion
            elif arg[0] == 'job':
                if len(arg) == 1:
                    # list of jobs
                    await ctx.send(embed = engel.listjob())
                else:
                    user = ctx.author.id
                    if arg[1] in ('level',):
                        if len(arg) == 2:
                            await ctx.send(embed = engel.infojp(user))
                        else:
                            job = ' '.join(arg[2:])
                            await ctx.send(engel.userjoblevel(user, job))
                    elif arg[1] in ('levels',):
                        if len(arg) > 3:
                            num_levels = int(arg[2])
                            job = ' '.join(arg[3:])
                            await ctx.send(engel.userjoblevel(user, job, num_levels))
                    elif arg[1] in ('reset',):
                        await ctx.send(engel.userjobreset(user))
                    else:
                        # find job and info (not needed atm)
                        await ctx.send('Nice try 5.') # to be implemented with proper suggestion
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
