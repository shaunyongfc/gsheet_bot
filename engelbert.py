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
            ('Raid', 'Raid'),
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
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        for jobid in dfjob.index:
            if jobid not in self.dfdict['User'].columns:
                self.dfdict['User'][jobid] = ''
    def sheetsync(self, logsync=0, raidsync=0):
        # sync local data into online sheet
        df = self.dfdict['User'].copy()
        df.index = df.index.astype(str)
        set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
        if logsync:
            set_with_dataframe(self.spreadsheet.worksheet('Log'), self.dfdict['Log'], include_index=False)
        if raidsync:
            set_with_dataframe(self.spreadsheet.worksheet('Raid'), self.dfdict['Raid'], include_index=True)
    def new_log(self, event, userid, timestamp):
        # write a new log
        new_log = {
            'Event': event,
            'User': userid,
            'Timestamp': timestamp
        }
        self.spreadsheet.worksheet('Log').append_row([str(v) for v in new_log.values()])
        self.dfdict['Log'] = self.dfdict['Log'].append(new_log, ignore_index=True)
    def find_index(self, query, dfname):
        df = self.dfdict[dfname]
        if dfname == 'Job':
            indices = df['Job']
            indexer = lambda x: x['Job']
        else:
            indices = df.index
            indexer = lambda x: x.name
        if query in indices:
            return query
        else:
            candidates = []
            for _, row in df.iterrows():
                if query.lower() == indexer(row).lower():
                    return indexer(row)
                elif query.lower() in indexer(row).lower():
                    candidates.append(indexer(row))
            if len(candidates) == 1:
                return candidates[0]
            else:
                return 'NOTFOUND'
    def jobjp_init(self):
        # initialize job level - JP table
        basejp = 10
        self.jobjp = dict()
        self.jobjpsum = dict()
        jpsum = 0
        for i in range(self.levelcap):
            self.jobjp[i] = basejp + (i * (i + 1)) // 2
            jpsum += basejp + (i * (i + 1)) // 2
            self.jobjpsum[i + 1] = jpsum
    def calchitrate(self, avoid):
        # calculate hit rate from agi difference
        if avoid < 1:
            return 1
        else:
            return max(1 - avoid * 0.05, 0)
    def calcstats(self, userid):
        # calculate stats given user id
        userdict = dict()
        level = 0
        for statname in self.statlist:
            userdict[statname] = self.dfdict['Base'].loc[self.dfdict['User'].loc[userid, 'Base'], statname]
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        for index, row in dfjob.iterrows():
            if index in self.dfdict['User'].columns:
                if self.dfdict['User'].loc[userid, index] != '':
                    for statname in self.statlist:
                        userdict[statname] += row[statname] * self.dfdict['User'].loc[userid, index]
                    level += self.dfdict['User'].loc[userid, index]
        userdict['Level'] = level
        return userdict
    def calcstatsraid(self, raid):
        # calculate raid stats given raid name
        raiddict = dict()
        base = self.dfdict['Raid'].loc[raid, 'Base']
        jobid = self.dfdict['Base'].loc[base, 'Starter']
        jobrow = self.dfdict['Job'].loc[jobid]
        for statname in self.statlist:
            raiddict[statname] = self.dfdict['Base'].loc[base, statname] + jobrow[statname] * self.dfdict['Raid'].loc[raid, 'Level']
        return raiddict
    def userattack(self, attacker, defender):
        # perform an attack between users
        if self.dfdict['User'].loc[attacker, 'HP'] == 0:
            return (0, 'You are dead!')
        elif self.dfdict['User'].loc[attacker, 'AP'] < self.attack_apcost:
            return (0, 'Not enough AP!')
        elif self.dfdict['User'].loc[defender, 'HP'] == 0:
            return (0, 'Target is dead!')
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
                hit = 0
                kill = 0
            else:
                hit = 1
                jp_gain += (damage + defenddict['Level']) // 5 # bonus JP for damage
                kill = self.userdamage(defender, damage)
                if kill:
                    jp_gain += defenddict['Level'] # bonus JP for killing
            defender_jp_gain = 1 + attackdict['Level'] // 10
            self.dfdict['User'].loc[defender, 'JP'] = self.dfdict['User'].loc[defender, 'JP'] + defender_jp_gain
            self.dfdict['User'].loc[attacker, 'JP'] = self.dfdict['User'].loc[attacker, 'JP'] + jp_gain # gains JP
            self.sheetsync()
            return (1, damage, hitrate, hit, kill, jp_gain, defender_jp_gain)
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
        userid = self.dfdict['Log'].loc[index, 'User']
        self.dfdict['User'].loc[userid, 'HP'] = self.calcstats(userid)['HP']
        self.dfdict['Log'].loc[index, 'Event'] = 'userrevived'
        self.dfdict['Log'].loc[index, 'Timestamp'] = datetime.strftime(datetime.now(), mydtformat)
        self.sheetsync(logsync=1)
    def userjoblevel(self, user, job, num_levels):
        # raises user job levels
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        jobid = dfjob[dfjob['Job'] == job].tail(1).index.tolist()[0]
        userrow = self.dfdict['User'].loc[user.id]
        available_jp = userrow['JP']
        job_level = userrow[jobid]
        if job_level == '':
            job_level = 0
        job_level_0 = job_level
        for i in range(num_levels):
            if job_level == self.levelcap:
                break
            if available_jp >= self.jobjp[job_level]:
                available_jp -= self.jobjp[job_level]
                job_level += 1
            else:
                break
        if job_level > job_level_0:
            self.dfdict['User'].loc[user.id, jobid] = job_level
            self.dfdict['User'].loc[user.id, 'JP'] = available_jp
            self.sheetsync()
        return f"{job_level - job_level_0} level(s) raised. Your current available JP is now {available_jp}."
    def userjobreset(self, user):
        # resets user job
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'userjobreset']
        df = df[df['User'] == user.id]
        if len(df) > 0:
            thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(days=1)
            now = datetime.now()
            if now < thres:
                remaining = thres - now
                return f"{remaining.seconds // 3600} hours {remaining.seconds % 3600 // 60} minutes left before you can reset jobs."
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        userrow = self.dfdict['User'].loc[user.id]
        jp_refunded = 0
        for jobid in dfjob.index:
            if userrow[jobid] != '':
                jp_refunded += self.jobjpsum[userrow[jobid]]
                self.dfdict['User'].loc[user.id, jobid] = ''
        if jp_refunded > 0:
            self.dfdict['User'].loc[user.id, 'JP'] = self.dfdict['User'].loc[user.id, 'JP'] + jp_refunded
            self.new_log('userjobreset', user.id, datetime.strftime(datetime.now(), mydtformat))
            self.sheetsync()
        return f"{jp_refunded} JP refunded!"
    def userbase(self, user, base):
        # changes user or starts a user
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'userbase']
        df = df[df['User'] == user.id]
        if len(df) > 0:
            thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(days=1)
            now = datetime.now()
            if now < thres:
                remaining = thres - now
                return f"{remaining.seconds // 3600} hours {remaining.seconds % 3600 // 60} minutes left before you can change base."
        baserow = self.dfdict['Base'].loc[base]
        if user.id in self.dfdict['User'].index:
            if self.dfdict['User'].loc[user.id, 'Base'] == base:
                return 'It is your current base!'
            else:
                self.dfdict['User'].loc[user.id, 'Base'] = base
                replystr = 'Base changed!'
        else:
            new_user = {
                'Base': base,
                'HP': baserow['HP'],
                'AP': baserow['AP'],
                'JP': 0,
                baserow['Starter']: 1
            }
            userrow = pd.Series(data=new_user.values(), index=new_user.keys(), name=user.id)
            self.dfdict['User'] = self.dfdict['User'].append(userrow).fillna('')
            replystr = 'User registered!'
        self.new_log('userbase', user.id, datetime.strftime(datetime.now(), mydtformat))
        self.sheetsync()
        return replystr
    def raiddamage(self, raid, damage):
        # function for a raid to take damage
        self.dfdict['Raid'].loc[raid, 'HP'] = int(max(self.dfdict['Raid'].loc[raid, 'HP'] - damage, 0))
        if self.dfdict['Raid'].loc[raid, 'HP'] == 0:
            # levels up the raid and fully recovers
            self.dfdict['Raid'].loc[raid, 'Level'] = self.dfdict['Raid'].loc[raid, 'Level'] + 1
            self.dfdict['Raid'].loc[raid, 'HP'] = self.calcstatsraid(raid)['HP']
            return 1
        else:
            return 0
    def raidattack(self, user, raid):
        # perform an attack between an user and a raid
        if self.dfdict['User'].loc[user, 'HP'] == 0:
            return (0, 'You are dead!')
        elif self.dfdict['User'].loc[user, 'AP'] < self.attack_apcost:
            return (0, 'Not enough AP!')
        else:
            # get their status sheets
            userdict = self.calcstats(user)
            raiddict = self.calcstatsraid(raid)
            jp_gain = 3 # base JP gain
            # consumes AP
            self.dfdict['User'].loc[user, 'AP'] = int(self.dfdict['User'].loc[user, 'AP'] - self.attack_apcost)
            # pick higher potential damage
            damage = max(userdict['ATK'] - raiddict['DEF'], userdict['MAG'] - raiddict['SPR'], 0)
            hitrate = self.calchitrate(raiddict['AGI'] - userdict['AGI'])
            if hitrate < random.random():
                hit = 0
                kill = 0
            else:
                hit = 1
                jp_gain += (damage + self.dfdict['Raid'].loc[raid, 'Level']) // 3 # bonus JP for damage
                kill = self.raiddamage(raid, damage)
                if kill:
                    jp_gain += self.dfdict['Raid'].loc[raid, 'Level'] # bonus JP for killing
            raid_damage = max(raiddict['ATK'] - userdict['DEF'], raiddict['MAG'] - userdict['SPR'], 0)
            raid_hitrate = self.calchitrate(userdict['AGI'] - raiddict['AGI'])
            if raid_hitrate < random.random():
                raid_hit = 0
                raid_kill = 0
            else:
                raid_hit = 1
                raid_kill = self.userdamage(user, raid_damage)
            self.dfdict['User'].loc[user, 'JP'] = self.dfdict['User'].loc[user, 'JP'] + jp_gain # gains JP
            self.sheetsync(raidsync=1)
            return (1, damage, hitrate, hit, kill, jp_gain,
                    raid_damage, raid_hitrate, raid_hit, raid_kill)
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
            desc_list = []
            for stat in self.statlist2:
                desc_list.append(f"{stat} `{row[stat]}`")
            desc_list.append(f"Starter: {self.dfdict['Job'].loc[row['Starter'], 'Job']}")
            base_list.append(f"**{index}**\n - {' | '.join(desc_list)}")
            base_count += 1
            if base_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(base_list))
                base_list = []
        if len(base_list) > 0:
            embed.add_field(name='-', value='\n'.join(base_list))
        return embed
    def listraid(self):
        # generate embed of list of available bases
        embed = discord.Embed()
        embed.title = 'List of Bases'
        desc = (
            'A raid is a boss to fight.',
            'Raids will counter attack when you attack them unlike other users.'
        )
        embed.description = '\n'.join(desc)
        df = self.dfdict['Raid']
        raid_list = []
        raid_count = 0
        for index, row in df.iterrows():
            raid_list.append(f"**{index}** - Level `{row['Level']}`")
            raid_count += 1
            if raid_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(raid_list))
                raid_list = []
        if len(raid_list) > 0:
            embed.add_field(name='-', value='\n'.join(raid_list))
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
        df = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        job_list = []
        job_count = 0
        for index, row in df.iterrows():
            desc_list = []
            for stat in self.statlist2:
                desc_list.append(f"{stat} `{self.statrating[row[stat]]}`")
            job_list.append(f"**{row['Job']}**\n - {' | '.join(desc_list)}")
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
        userrow = self.dfdict['User'].loc[user.id]
        embed.title = f"{user.name} Jobs"
        embed.description = f"JP: {userrow['JP']}"
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
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
        row = self.dfdict['User'].loc[user.id]
        embed.title = user.name
        desc_list = []
        userdict = self.calcstats(row.name)
        desc_list.append(f"Base: {row['Base']} (+{userdict['Level']})")
        desc_list.append(f"HP: {row['HP']}/{userdict['HP']}")
        desc_list.append(f"AP: {row['AP']}/{userdict['AP']}")
        desc_list.append(f"JP: {row['JP']}")
        embed.description = '\n'.join(desc_list)
        desc_list = []
        for stat in self.statlist2:
            desc_list.append(f"{stat}: {userdict[stat]}")
        embed.add_field(name='Stats', value='\n'.join(desc_list))
        thumbnail_url = self.dfdict['Base'].loc[row['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        return embed
    def inforaid(self, raid):
        # generate info embed of specific raid
        embed = discord.Embed()
        row = self.dfdict['Raid'].loc[raid]
        embed.title = raid
        desc_list = []
        raiddict = self.calcstatsraid(row.name)
        desc_list.append(f"Raid Level: {row['Level']}")
        desc_list.append(f"HP: {row['HP']}/{raiddict['HP']}")
        embed.description = '\n'.join(desc_list)
        desc_list = []
        for stat in self.statlist2:
            desc_list.append(f"{stat}: {raiddict[stat]}")
        embed.add_field(name='Stats', value='\n'.join(desc_list))
        thumbnail_url = self.dfdict['Base'].loc[row['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        return embed
    def infoattack(self, attacker, defender):
        # generate result embed of an attack
        result_tup = self.userattack(attacker.id, defender.id)
        embed = discord.Embed()
        if result_tup[0] == 0:
            embed.title = 'Attack Failed'
            embed.description = result_tup[1]
        else:
            embed.title = f"{attacker.name} VS {defender.name}"
            _, damage, hitrate, hit, kill, jp_gain, defender_jp_gain = result_tup
            desc_list = []
            desc_list.append(f"*Info: You have {hitrate * 100:.0f}% of doing {damage} damage.*")
            if hit:
                desc_list.append(f"You successfully attacked.")
            else:
                desc_list.append(f"You missed.")
            if kill:
                desc_list.append(f"{defender.name} is KO-ed.")
            desc_list.append(f"You gained {jp_gain} JP. {defender.name} gained {defender_jp_gain} JP.")
            embed.description = '\n'.join(desc_list)
            for user in (attacker, defender):
                desc_list = []
                desc_list.append(f"HP: {self.dfdict['User'].loc[user.id, 'HP']}")
                desc_list.append(f"AP: {self.dfdict['User'].loc[user.id, 'AP']}")
                desc_list.append(f"JP: {self.dfdict['User'].loc[user.id, 'JP']}")
                embed.add_field(name = user.name, value = '\n'.join(desc_list))
        return embed
    def infoattackraid(self, user, raid):
        # generate result embed of an attack
        result_tup = self.raidattack(user.id, raid)
        embed = discord.Embed()
        if result_tup[0] == 0:
            embed.title = 'Attack Failed'
            embed.description = result_tup[1]
        else:
            embed.title = f"{attacker.name} VS {raid}"
            _, damage, hitrate, hit, kill, jp_gain, raid_damage, raid_hitrate, raid_hit, raid_kill = result_tup
            desc_list = []
            desc_list.append(f"*Info: You have {hitrate * 100:.0f}% of doing {damage} damage.*")
            if hit:
                desc_list.append(f"You successfully attacked.")
            else:
                desc_list.append(f"You missed.")
            if kill:
                desc_list.append(f"{raid} is KO-ed. A new level has now been spawned.")
            desc_list.append(f"\nYou gained {jp_gain} JP.")
            embed.description = '\n'.join(desc_list)
            desc_list = []
            desc_list.append(f"\n*Info: {raid} has {raid_hitrate * 100:.0f}% of doing {raid_damage} damage to you.*")
            if raid_hit:
                desc_list.append(f"{raid} successfully countered.")
            else:
                desc_list.append(f"{raid} missed.")
            if raid_kill:
                desc_list.append(f"You are KO-ed.")
            embed.add_field(name = f"{raid} Counter Attack", value = '\n'.join(desc_list), inline = False)
            desc_list = []
            desc_list.append(f"HP: {self.dfdict['User'].loc[user.id, 'HP']}")
            desc_list.append(f"AP: {self.dfdict['User'].loc[user.id, 'AP']}")
            desc_list.append(f"JP: {self.dfdict['User'].loc[user.id, 'JP']}")
            embed.add_field(name = user.name, value = '\n'.join(desc_list))
            desc_list = []
            desc_list.append(f"Level: {self.dfdict['Raid'].loc[raid, 'Level']}")
            desc_list.append(f"HP: {self.dfdict['Raid'].loc[raid, 'HP']}")
            embed.add_field(name = raid, value = '\n'.join(desc_list))
        return embed
    def executecommand(self, ctx, user, *arg):
        pass

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
        user = ctx.author
        if len(arg) == 0:
            await ctx.send('Nice try 1.') # to be implemented with proper help function
        else:
            if arg[0] == 'info':
                if len(arg) == 1:
                    # own info
                    await ctx.send(embed = engel.infouser(user))
                else:
                    try:
                        member = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if member.id in engel.dfdict['User'].index:
                            await ctx.send(embed = engel.infouser(member))
                        else:
                            await ctx.send('User not found.') # to be implemented with proper starter stuff
                    except commands.BadArgument:
                        await ctx.send('User not found.') # to be implemented with proper starter stuff
            elif arg[0] == 'base':
                if len(arg) == 1:
                    # list of bases
                    await ctx.send(embed = engel.listbase())
                else:
                    # various operations
                    if len(arg) > 2 and arg[1] in ('change', 'start'):
                        # change base or start of tamagotchi
                        base = engel.find_index(' '.join(arg[2:]), 'Base')
                        if base == 'NOTFOUND':
                            await ctx.send('Base not found.') # to be implemented with proper suggestion
                        else:
                            await ctx.send(engel.userbase(user, base))
                    else:
                        # find base and info (not needed atm)
                        await ctx.send('Base command not found.') # to be implemented with proper suggestion
            elif arg[0] == 'job':
                if len(arg) == 1:
                    # list of jobs
                    await ctx.send(embed = engel.listjob())
                else:
                    if arg[1] in ('level', 'levels'):
                        if len(arg) == 2:
                            await ctx.send(embed = engel.infojp(user))
                        else:
                            if arg[2].isnumeric() and len(arg) > 3:
                                num_levels = int(arg[2])
                                job = engel.find_index(' '.join(arg[3:]), 'Job')
                            else:
                                num_levels = 1
                                job = engel.find_index(' '.join(arg[2:]), 'Job')
                            if job == 'NOTFOUND':
                                await ctx.send('Job not found.') # to be implemented with proper suggestion
                            else:
                                await ctx.send(engel.userjoblevel(user, job, num_levels))
                    elif arg[1] in ('reset',):
                        await ctx.send(engel.userjobreset(user))
                    else:
                        # find job and info (not needed atm)
                        await ctx.send('Job command not found.') # to be implemented with proper suggestion
            elif arg[0] == 'attack':
                if len(arg) == 1:
                    # to be implemented with proper suggestion
                    await ctx.send(embed = engel.infouser(user))
                else:
                    # find member of said name to attack
                    defender = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                    if defender.id in engel.dfdict['User'].index:
                        await ctx.send(embed = engel.infoattack(user, defender))
                    else:
                        await ctx.send('User not found.') # to be implemented with proper suggestion
            elif arg[0] == 'raid':
                # to be implemented
                if len(arg) == 1:
                    # available raids
                    await ctx.send(embed = engel.listraid())
                else:
                    if arg[1] == 'info' and len(arg) > 2:
                        raid = engel.find_index(' '.join(arg[2:]), 'Raid')
                        if raid == 'NOTFOUND':
                            await ctx.send('Raid not found.') # to be implemented with proper suggestion
                        else:
                            await ctx.send(embed = engel.inforaid(raid))
                    elif arg[1] == 'attack' and len(arg) > 2:
                        raid = engel.find_index(' '.join(arg[2:]), 'Raid')
                        if raid == 'NOTFOUND':
                            await ctx.send('Raid not found.') # to be implemented with proper suggestion
                        else:
                            await ctx.send(embed = engel.infoattackraid(user, raid))
                    else:
                        await ctx.send('Raid command not found.') # to be implemented with proper suggestion
            else:
                await ctx.send('Command not found.') # to be implemented with proper help function
