import re, random, discord, math
import pandas as pd
from discord.ext import commands, tasks
from gsheet_handler import client
from gspread_dataframe import set_with_dataframe
from general_utils import logs_embed
from id_dict import id_dict
from datetime import datetime, timedelta

# experimental project on Discord bot tamagotchi, codenamed Engelbert
mydtformat = '%Y/%m/%d %H:%M'

class Engel:
    # utility class that contains the utility functions and parameters
    def __init__(self):
        # gameplay constants
        self.attack_apcost = 3
        self.hpregen = 0.1
        self.apregen = 6
        self.levelcap = 20
        self.revivehours = 4
        self.sheettuples = (
            ('Base', 'Base'),
            ('Job', 'JobID'),
            ('User', 'User'),
            ('Raid', 'Raid'),
            ('Log', '')
        )
        self.statlist = ('HP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.statlist2 = ('ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.statrating = {
            7: 'S-',
            6: 'A+',
            5: 'A-',
            4: 'B+',
            3: 'B-',
            2: 'C+',
            1: 'C-'
        }
        self.manual = dict()
        self.indepth = dict()
        self.helptup = {
            'char': 'Character',
            'character': 'Character',
            'base': 'Base',
            'job': 'Job',
            'raid': 'Raid'
        }
        self.helpintro = (
            'Engelbert (beta) is an experimental project of Discord bot tamagotchi '
            '(digital pet / avatar / character). It is still under beta so things '
            'may be subject to change. Have to see if free hosting service can '
            'handle the frequency of data update too... Feel free to drop some feedback!\n'
            'For more in-depth info of the following, try `=charhelp char`, `=charhelp base`, '
            '`=charhelp job`, `=charhelp raid`'
        )
        self.manual['Character'] = (
            'Each Discord ID can only have one character. To start a character, '
            'you need to pick a base (check out `=charhelp base`). '
            'Your stats are calculated from you base and your job levels. '
        )
        self.indepth['Character'] = (
            '- Type `=char info` to check your character if you already started one.',
            '- Type `=char info (user ping)` (e.g. `=char info @Caelum`) to check character of another user.',
            '- HP is your health (over your max health)',
            f"- AP is action points. You need to spend {self.attack_apcost} to battle.",
            '- JP is used to raise your job levels, automatically gained slowly or from battles.',
            '- ATK and MAG are your offensive stats and DEF and SPR are your defensive stats.',
            '- DEX determines your accuracy and critical rate.'
            '- AGI determines your evasion and critical avoid.',
            f"- Your HP and AP regen {self.hpregen * 100}% and {self.apregen} respectively every hour.",
            '- If your AP is full, HP regen is doubled instead.',
            f"- If your HP reaches zero, you will be revived with full HP after {self.revivehours} hours."
        )
        self.indepthbattle = (
            '- To battle, you attack another player or a raid.',
            '- You can battle another player by `=char attack (user ping)`.',
            '- Check out `=charhelp raid` for info about raid.'
            '- Damage is calculated by `ATK - DEF` or `MAG - SPR` (whichever larger) with ATK/MAG of attacker and DEF/SPR of defender.',
            '- You can only land critical if your DEX is higher than the opponent; you can only evade attacks if your AGI is higher than the opponent.',
            '- Critical rate is scaled by `(Attacker DEX - Defender AGI)`; evasion rate is scaled by `(Defender AGI - Attacker DEX)`.',
            '- They use the same formula: 1~10 = 3% per point, 11~40 = 2% per point, 41~50 = 1% per point.',
            '- Critical damage is double of regular damage.'
        )
        self.manual['Base'] = (
            'A base determines your base stats and your info picture where available. '
            'Your first base also gives you a free job level. '
            'Your base can be reset every 24 hours. '
            'Element and/or other features may be implemented in future. '
        )
        self.indepth['Base'] = (
            'Type `=char base` to find list of bases and their bases stats.',
            'Type `=char base start (base name)` (e.g. `=char base start jake`) to start your character.',
            'Type `=char base change (base name)` (e.g. `=char base change rain`) to change the base of your character.'
        )
        self.manual['Job'] = (
            'Leveling a job costs JP and raises your stats according to the job. '
            'Higher levels require more JP to level. '
            'Job levels can be reset into JP every 24 hours. '
            'Skills or other features may be implemented in future. '
        )
        self.indepth['Job'] = (
            'Type `=char job` to find list of jobs and their growth rate.',
            'Type `=char job level` to see your current job levels and required JP.',
            'Type `=char job level (job name)` (e.g. `=char job level red mage`) to level a job.',
            'Type `=char job level (number) (job name)` (e.g. `=char job level 10 red mage`) to raise multiple levels of a job at once.',
            'Type `=char job reset` to reset all your job levels into JP.'
        )
        self.manual['Raid'] = (
            'You can battle a raid by to gain extra JP. '
            'Note that unlike attacking another player, a raid will counter you every time you attack. '
            'After a raid dies the killer gains extra JP and the raid will level up with full HP. '
            'Check out `=charhelp char` for battle mechanics. '
        )
        self.indepth['Raid'] = (
            'Type `=char raid` to find list of available raids and their levels.',
            'Type `=char raid info (raid name)` (e.g. `=char raid info ifrit`) to see the stats etc of the raid.',
            'Type `=char raid attack (raid name)` (e.g. `=char raid attack siren`) to attack the raid.'
        )
        self.changelog = (
            ('8th February 2021', (
                'Level cap increased from 10 to 20.',
                'JP gain now scales more with level and less with damage.',
                f"Base AP increased but AP regen is now fixed at 6.",
                'HP regen % is doubled and revival time is shortened to 4 hours.',
                'Overall ATK/MAG have been increased across the board.',
                'AGI stat split into DEX and AGI: AGI > DEX chance to miss; DEX > AGI chance to critical.',
                'New job added - Assassin (becomes Vinera default)'
            )),
            ('7th February 2021', (
                'Raid HP significantly reduced but growth rate increased.',
                'Evasion rate nerfed.',
                'JP required per level decreased.'
            )),
            ('6th February 2021', (
                '(beta) Launch!',
            ))
        )
        self.spreadsheet = client.open(id_dict['Engel Sheet'])
        self.dfdict = dict()
        self.dfsync()
        self.jobjp_init()
    def indextransform(self, index):
        # to counter google sheet eating user ids
        if isinstance(index, (int, float)):
            return f"u{index}"
        else:
            if index[0] == 'u':
                return int(index[1:])
            else:
                return index
    def dfsync(self):
        # sync online sheet into local data
        for sheetname, indexname in self.sheettuples:
             df = pd.DataFrame(self.spreadsheet.worksheet(sheetname).get_all_records())
             if indexname != '':
                 df[indexname] = df[indexname].apply(self.indextransform)
                 df = df.set_index(indexname)
             self.dfdict[sheetname] = df
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        for jobid in dfjob.index:
            if jobid not in self.dfdict['User'].columns:
                self.dfdict['User'][jobid] = ''
    def sheetsync(self, logsync=0, raidsync=0):
        # sync local data into online sheet
        df = self.dfdict['User'].copy()
        df.index = pd.Index([self.indextransform(a) for a in df.index.tolist()], name='User')
        set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
        if logsync:
            df = self.dfdict['Log'].copy()
            df['User'] = df['User'].astype(str)
            set_with_dataframe(self.spreadsheet.worksheet('Log'), df, include_index=False)
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
            self.jobjp[i] = basejp + math.floor(i ** 1.5)
            jpsum += self.jobjp[i]
            self.jobjpsum[i + 1] = jpsum
    def calchitrate(self, accuracy):
        # calculate critical or hit rate from dex - agi
        if accuracy == 0:
            return 1
        elif accuracy >= 50:
            return 2
        elif accuracy <= -50:
            return 0
        else:
            if abs(accuracy) >= 40:
                modifier = 0.9 - 0.4 + abs(accuracy) * 0.01
            elif abs(accuracy) >= 10:
                modifier = 0.3 - 0.2 + abs(accuracy) * 0.02
            else:
                modifier = abs(accuracy) * 0.03
            if accuracy > 0:
                return 1 + modifier
            else:
                return 1 - modifier
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
            hitrate = self.calchitrate(attackdict['DEX'] - defenddict['AGI'])
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            jp_gain += (damage * hit // 6 + defenddict['Level'] * min(hit, 1)) // 5 # bonus JP for damage
            kill = self.userdamage(defender, damage * hit)
            if kill:
                jp_gain += defenddict['Level'] # bonus JP for killing
            defender_jp_gain = 1 + (damage * hit // 12 + attackdict['Level']) // 5
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
                new_ap = min(row['AP'] + self.apregen, userdict['AP'])
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
            jp_gain = 5 # base JP gain
            # consumes AP
            self.dfdict['User'].loc[user, 'AP'] = int(self.dfdict['User'].loc[user, 'AP'] - self.attack_apcost)
            # pick higher potential damage
            damage = max(userdict['ATK'] - raiddict['DEF'], userdict['MAG'] - raiddict['SPR'], 0)
            hitrate = self.calchitrate(userdict['DEX'] - raiddict['AGI'])
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            jp_gain += (damage * hit) // 30 + self.dfdict['Raid'].loc[raid, 'Level'] * 10 # bonus JP for damage
            kill = self.raiddamage(raid, damage * hit)
            if kill:
                jp_gain += self.dfdict['Raid'].loc[raid, 'Level'] * 10 # bonus JP for killing
            raid_damage = max(raiddict['ATK'] - userdict['DEF'], raiddict['MAG'] - userdict['SPR'], 0)
            raid_hitrate = self.calchitrate(raiddict['DEX'] - userdict['AGI'])
            if raid_hitrate > 1:
                raid_hit = 1 + ((raid_hitrate - 1) > random.random())
            else:
                raid_hit = raid_hitrate > random.random()
            raid_kill = self.userdamage(user, raid_damage * raid_hit)
            self.dfdict['User'].loc[user, 'JP'] = self.dfdict['User'].loc[user, 'JP'] + jp_gain # gains JP
            self.sheetsync(raidsync=1)
            return (1, damage, hitrate, hit, kill, jp_gain,
                    raid_damage, raid_hitrate, raid_hit, raid_kill)
    ############################
    # discord embed generators #
    ############################
    def helpmanual(self, kw=''):
        # generate help manual
        embed = discord.Embed()
        kw = kw.lower()
        if kw in self.helptup.keys():
            kw = self.helptup[kw]
            embed.title = f"{kw} Help"
            embed.description = self.manual[kw]
            embed.add_field(name = 'In Depth', value = '\n'.join(self.indepth[kw]), inline = False)
            if kw == 'Character':
                embed.add_field(name = 'Battle', value = '\n'.join(self.indepthbattle), inline = False)
        else:
            embed.title = 'Engelbert Help'
            embed.description = self.helpintro
            for k, v in self.manual.items():
                embed.add_field(name = k, value = v, inline = False)
        embed.set_thumbnail(url = 'https://caelum.s-ul.eu/3MgPuHkX.png')
        return embed
    def infochangelog(self, num=3):
        # generate changelog
        embed = discord.Embed()
        embed.title = 'Engelbert Changelog'
        try:
            entry_num = int(num)
        except IndexError:
            entry_num = 3
        for i, tup in enumerate(self.changelog):
            if i == entry_num:
                break
            embed.add_field(name=tup[0], value = '\n'.join(tup[1]), inline=False)
        embed.set_thumbnail(url = 'https://caelum.s-ul.eu/peon3odf.png')
        return embed
    def listbase(self):
        # generate embed of list of available bases
        embed = discord.Embed()
        embed.title = 'List of Bases'
        embed.description = self.manual['Base'] + '\n`=charhelp base` for more info.'
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
        embed.title = 'List of Raids'
        embed.description = self.manual['Raid'] + '\n`=charhelp raid` for more info.'
        df = self.dfdict['Raid']
        raid_list = []
        raid_count = 0
        for index, row in df.iterrows():
            raid_list.append(f"**{index}** - Level `{row['Level']}` | HP `{row['HP']}`")
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
        embed.description = self.manual['Job'] + '\n`=charhelp job` for more info.'
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
        embed_colour = self.dfdict['Base'].loc[userrow['Base'], 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
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
        if row['HP'] == 0:
            dflog = self.dfdict['Log'][self.dfdict['Log']['Event'] == 'userdead']
            deadtime = dflog[dflog['User'] == user.id].tail(1)['Timestamp'].tolist()[0]
            thres = datetime.strptime(deadtime, mydtformat) + timedelta(hours=engel.revivehours)
            revivaltd = thres - datetime.now()
            revivalstr = f"{revivaltd.seconds // 60 + 1} minutes remaining."
            embed.add_field(name='Revival Time', value=revivalstr, inline=False)
        thumbnail_url = self.dfdict['Base'].loc[row['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed_colour = self.dfdict['Base'].loc[row['Base'], 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
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
        embed_colour = self.dfdict['Base'].loc[row['Base'], 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
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
            desc_list.append(f"*Info: You have {min(hitrate, 1) * 100:.0f}% of doing {damage} damage.*")
            desc_list.append(f"*Info: You have {max(hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
            if hit == 2:
                desc_list.append(f"You landed a critical hit.")
            elif hit == 1:
                desc_list.append(f"You successfully attacked.")
            else:
                desc_list.append(f"You missed.")
            if kill:
                desc_list.append(f"{defender.name} is KO-ed.")
            desc_list.append(f"You gained {jp_gain} JP. {defender.name} gained {defender_jp_gain} JP.")
            embed.description = '\n'.join(desc_list)
            for user in (attacker, defender):
                desc_list = []
                for statname in ('HP', 'AP', 'JP'):
                    desc_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
                embed.add_field(name = user.name, value = '\n'.join(desc_list))
        defender_base = self.dfdict['User'].loc[defender.id, 'Base']
        embed_colour = self.dfdict['Base'].loc[defender_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    def infoattackraid(self, user, raid):
        # generate result embed of an attack
        result_tup = self.raidattack(user.id, raid)
        embed = discord.Embed()
        if result_tup[0] == 0:
            embed.title = 'Attack Failed'
            embed.description = result_tup[1]
        else:
            embed.title = f"{user.name} VS {raid}"
            _, damage, hitrate, hit, kill, jp_gain, raid_damage, raid_hitrate, raid_hit, raid_kill = result_tup
            desc_list = []
            desc_list.append(f"*Info: You have {min(hitrate, 1) * 100:.0f}% of doing {damage} damage.*")
            desc_list.append(f"*Info: You have {max(hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
            if hit == 2:
                desc_list.append(f"You landed a critical hit.")
            elif hit == 1:
                desc_list.append(f"You successfully attacked.")
            else:
                desc_list.append(f"You missed.")
            if kill:
                self.new_log(f"{raid} kill", user.id, datetime.strftime(datetime.now(), mydtformat))
                desc_list.append(f"{raid} is KO-ed. A new level has now been spawned.")
            desc_list.append(f"\nYou gained {jp_gain} JP.")
            embed.description = '\n'.join(desc_list)
            desc_list = []
            desc_list.append(f"\n*Info: {raid} has {min(raid_hitrate, 1) * 100:.0f}% of doing {raid_damage} damage to you.*")
            desc_list.append(f"*Info: {raid} has {max(raid_hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
            if raid_hit == 2:
                desc_list.append(f"{raid} landed a critical hit.")
            elif raid_hit == 1:
                desc_list.append(f"{raid} successfully countered.")
            else:
                desc_list.append(f"{raid} missed.")
            if raid_kill:
                desc_list.append(f"You are KO-ed.")
            embed.add_field(name = f"{raid} Counter Attack", value = '\n'.join(desc_list), inline = False)
            desc_list = []
            for statname in ('HP', 'AP', 'JP'):
                desc_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
            embed.add_field(name = user.name, value = '\n'.join(desc_list))
            desc_list = []
            desc_list.append(f"Level: {self.dfdict['Raid'].loc[raid, 'Level']}")
            desc_list.append(f"HP: {self.dfdict['Raid'].loc[raid, 'HP']}")
            embed.add_field(name = raid, value = '\n'.join(desc_list))
        raid_base = self.dfdict['Raid'].loc[raid, 'Base']
        embed_colour = self.dfdict['Base'].loc[raid_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    async def executecommand(self, user, ctx, *arg):
        # main command execution
        if len(arg) == 0:
            return self.helpmanual()
        else:
            if arg[0] == 'info':
                if len(arg) == 1:
                    if user.id in self.dfdict['User'].index:
                        # own info
                        return self.infouser(user)
                    else:
                        return discord.Embed(description = 'Choose a base first with `=char base start (base name)`. Try `=charhelp base`.')
                else:
                    try:
                        member = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if member.id in self.dfdict['User'].index:
                            return self.infouser(member)
                        else:
                            return discord.Embed(description = 'User not found or did not start a character.')
                    except commands.BadArgument:
                        return discord.Embed(description = 'User not found or did not start a character.')
            elif arg[0] == 'base':
                if len(arg) == 1:
                    # list of bases
                    return self.listbase()
                else:
                    # various operations
                    if len(arg) > 2 and arg[1] in ('change', 'start'):
                        # change base or start of tamagotchi
                        base = self.find_index(' '.join(arg[2:]), 'Base')
                        if base == 'NOTFOUND':
                            return discord.Embed(description = 'Base not found. Try checking `=char base`.')
                        return discord.Embed(description = self.userbase(user, base))
                    else:
                        # find base and info (not needed atm)
                        return discord.Embed(description = 'Try `=charhelp base`.')
            elif arg[0] == 'job':
                if len(arg) == 1:
                    # list of jobs
                    return self.listjob()
                else:
                    if arg[1] in ('level', 'levels'):
                        if len(arg) == 2:
                            return self.infojp(user)
                        else:
                            if arg[2].isnumeric() and len(arg) > 3:
                                num_levels = int(arg[2])
                                job = self.find_index(' '.join(arg[3:]), 'Job')
                            else:
                                num_levels = 1
                                job = self.find_index(' '.join(arg[2:]), 'Job')
                            if job == 'NOTFOUND':
                                return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                            else:
                                return discord.Embed(description = self.userjoblevel(user, job, num_levels))
                    elif arg[1] in ('reset',):
                        return discord.Embed(description = self.userjobreset(user))
                    else:
                        # find job and info (not needed atm)
                        return discord.Embed(description = 'Try `=charhelp job`.')
            elif arg[0] == 'attack':
                if len(arg) == 1:
                    return discord.Embed(description = 'Try `=charhelp char`.')
                else:
                    try:
                        # find member of said name to attack
                        defender = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if defender.id in self.dfdict['User'].index:
                            return self.infoattack(user, defender)
                        else:
                            return discord.Embed(description = 'User not found or did not start a character.')
                    except commands.BadArgument:
                        return discord.Embed(description = 'User not found or did not start a character.')
            elif arg[0] == 'raid':
                # to be implemented
                if len(arg) == 1:
                    # available raids
                    return self.listraid()
                else:
                    if arg[1] == 'attack' and len(arg) > 2:
                        raid = self.find_index(' '.join(arg[2:]), 'Raid')
                        if raid == 'NOTFOUND':
                            return discord.Embed(description = 'Raid not found. Try checking `=char raid`.')
                        else:
                            return self.infoattackraid(user, raid)
                    elif arg[1] == 'info' and len(arg) > 2:
                        raid = self.find_index(' '.join(arg[2:]), 'Raid')
                        if raid == 'NOTFOUND':
                            return discord.Embed(description = 'Raid not found. Try checking `=char raid`.')
                        else:
                            return self.inforaid(raid)
                    else:
                        raid = self.find_index(' '.join(arg[1:]), 'Raid')
                        if raid == 'NOTFOUND':
                            return discord.Embed(description = 'Try `=charhelp raid`.')
                        else:
                            return self.inforaid(raid)
            elif arg[0] == 'help':
                if len(arg) > 1:
                    return self.helpmanual(arg[1])
                else:
                    return self.helpmanual()
            elif arg[0] in ('changelog', 'version'):
                if len(arg) > 1:
                    return self.infochangelog(arg[1])
                else:
                    return self.infochangelog()
            else:
                return self.helpmanual()

engel = Engel()

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
            thres = datetime.strptime(row['Timestamp'], mydtformat) + timedelta(hours=engel.revivehours)
            if now > thres:
                engel.userrevive(index)

    @commands.command(aliases=['engelsync'])
    async def engelbertsync(self, ctx, *arg):
        # Synchronise Engelbert sheets
        if ctx.message.author.id == id_dict['Owner']:
            engel.dfsync()
            await ctx.send('Google sheet synced for Engelbert.')

    @commands.command(aliases=['fred'])
    async def frederika(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # admin test command
        if ctx.message.author.id == id_dict['Owner']:
            user = await self.bot.fetch_user(int(arg[0]))
            embed = await engel.executecommand(user, ctx, *arg[1:])
            embed.set_footer(text='Still in beta phase. Prone to bugs...')
            await ctx.send(embed = embed)
            await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp'])
    async def engelberthelp(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, 'help', *arg)
        embed.set_footer(text='Still in beta phase. Prone to bugs...')
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama', 'char'])
    async def engelbert(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, *arg)
        embed.set_footer(text='Still in beta phase. Prone to bugs...')
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)
