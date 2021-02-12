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
        self.hpregen = 0.2
        self.apregen = 6
        self.levelcap = 99
        self.revivehours = 3
        self.skill_apcost = 5
        self.skill_hpcost = 0.2
        self.skillduration = 5
        self.attackcap = 20
        self.sheettuples = (
            ('Base', 'Base'),
            ('Job', 'JobID'),
            ('Skill', 'SkillID'),
            ('User', 'User'),
            ('Raid', 'Raid'),
            ('Log', ''),
        )
        self.statlist = ('HP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.statlist2 = ('ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.intro = dict()
        self.indepth = dict()
        self.helptup = {
            'char': 'Character',
            'character': 'Character',
            'base': 'Base',
            'job': 'Job',
            'skill': 'Skill',
            'raid': 'Raid',
            'battle': 'Battle'
        }
        self.helpintro = (
            'Engelbert (beta v2) is an experimental project of Discord bot tamagotchi '
            '(digital pet / avatar / character). It is still under beta so things '
            'may be subject to change. Have to see if free hosting service can '
            'handle the frequency of data update too... Feel free to drop some feedback!\n'
            '- Type `=char changelog` for recent changes.\n'
            '- For more in-depth info of the following, try `=charhelp char`, `=charhelp battle`, '
            '`=charhelp base`, `=charhelp job`, `=charhelp raid`, `=charhelp skill`.'
        )
        self.intro['Character'] = (
            'Each Discord ID can only have one character. To start a character, '
            'you need to pick a base (check out `=charhelp base`).'
        )
        self.indepth['Character'] = (
            '- Type `=char info` to check your character if you already started one.',
            '- Type `=char info (user ping)` (e.g. `=char info @Caelum`) to check character of another user.',
            '- Type `=char duel (user ping)` to duel with character of another user (no gain/loss whatsoever).',
            '- Your stats are calculated from your Level and your current main/sub jobs.',
            '- Level raises by earning EXP, mainly from battles (`=charhelp battle`, `=charhelp raid`).',
            '- Type `=char train` or `=char train (number of AP)` (e.g. `=char train 10`) to quickly spend AP for EXP.',
            f"- If your HP reaches zero, you cannot battle and will be revived after {self.revivehours} hours.",
            f"- AP is action points, spent for various actions.",
            f"- Your HP and AP regen {self.hpregen * 100}% and {self.apregen} respectively every hour.",
            '- If your AP is full, HP regen is doubled instead.',
            '- LB is filled every time you battle or are attacked.',
            '- When fully filled, LB can be consumed to cast a skill (`=charhelp skill`).',
            '- Gil is earned every time you consume AP. No use for now, to be implemented in a future update.'
        )
        self.intro['Battle'] = (
            f"There are two types of battle: player and raid. Each battle consumes {self.attack_apcost}. "
            'Check out `=charhelp raid` for info about raid. '
            'Note: Duel does not consume AP. '
        )
        self.indepth['Battle'] = (
            '- Type `=char attack (user ping)` to another player.',
            f"- Attack multiple times in a row by inserting a number like `=char attack 6 @Caelum` (up to {self.attackcap}).",
            '- When you attack a target, attacker ATK, MAG, DEX, defender DEF, SPR, AGI are used in calculation.'
            '- Damage is calculated by `ATK - DEF` or `MAG - SPR` (whichever larger).',
            '- You can only land critical if your DEX is higher than the opponent',
            '- You can only evade attacks if your AGI is higher than the opponent.',
            '- Critical rate is scaled by `(Attacker DEX - Defender AGI)`',
            '- Evasion rate is scaled by `(Defender AGI - Attacker DEX)`.',
            '- They use the same formula: 1~25 = 2% per point, 26~75 = 1% per point.',
            '- Critical damage is 2x regular damage.',
        )
        self.intro['Base'] = (
            'A base determines your base stats and your info picture where available. '
            'Every base has a default set of jobs but you can change afterwards. '
            'Your base can be changed every 24 hours. Changing a base does not change your jobs. '
        )
        self.indepth['Base'] = (
            '- Type `=char base` to find list of available bases.',
            '- Type `=char base (base name)` (e.g. `=char base lasswell`) to read info of the base.'
            '- Type `=char base start (base name)` (e.g. `=char base start jake`) to start your character.',
            '- Type `=char base change (base name)` (e.g. `=char base change rain`) to change the base of your character.'
        )
        self.intro['Job'] = (
            'Your jobs determine your stats. '
            'You have 100% growth rate of main job and 50% of each sub job. '
            'Main job can be changed every 24 hours, but changing sub jobs has no limit. '
            'Changing main job also resets your sub jobs. They can be changed anytime however. '
        )
        self.indepth['Job'] = (
            '- Type `=char job` to find list of jobs and their growth rate.',
            '- Type `=char job main (job name)` (e.g. `=char job main red mage`) to change main job.',
            '- Type `=char job sub1 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 1.',
            '- Type `=char job sub2 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 2.',
            '- Type `=char job subs (job name) | (job name)` (e.g. `=char job subs green mage | mechanic`) to change both sub jobs at once.'
        )
        self.intro['Skill'] = (
            'Skills can cost either HP, AP or LB. '
            'You can use all skills available. However, the skill of your main job will have higher potency. '
            'There are three types of skills - healing, buff, debuff. '
            'Healing is scaled with your max HP, i.e. level. '
        )
        self.indepth['Skill'] = (
            '- Type `=char skill` to find list of available skills.',
            '- Skills do not apply on duels nor when you are being attacked.',
            '- Using skills with AP or LB get you EXP proportional to user and target levels.',
            '- Only 1 buff or debuff skill can be active at one time.',
            f"- Buff and debuff skills last for {self.skillduration} battles.",
            f"- By default, skills cost {self.skill_apcost} AP to cast.",
            '- Type `=char skill (skill name)` (e.g. `=char skill ruin`) to cast on yourself..',
            '- Healing and buff skills can be cast on other users.',
            '- Type `=char skill (skill name) | (user ping)` (e.g. `=char skill protect | @Caelum`).',
            f"- You can opt to consume {self.skill_hpcost*100:.0f}% HP or LB instead of AP.",
            '- Type `=char skill (skill name) | (user ping) | hp` (e.g. `=char skill cure | @Caelum | hp`).',
            '- Type `=char skill (skill name) | (user ping) | lb` (e.g. `=char skill luck | @Caelum | lb`).'
        )
        self.indepth['Healing'] = (
            '- You cannot heal yourself with HP.',
            '- You can revive a target by healing only if you spend enough HP or AP to fully heal the target.',
            '- You can only revive a target by healing using LB if you can fully heal the target in one cast.',
            '- The command remains the same if you revive by HP, but to revive with AP:',
            '- Type `=char skill (healing skill name) | (user ping) | revive` (e.g. `=char skill cure | @Caelum | revive`).',
        )
        self.intro['Raid'] = (
            'You can battle a raid to gain EXP. '
            'Unlike attacking another player, a raid will counter you every time you attack. '
            'After a raid dies the killer gains extra EXP and the raid will level up with full HP. '
            'Check out `=charhelp battle` for battle mechanics. '
        )
        self.indepth['Raid'] = (
            '- Type `=char raid` to find list of available raids and their levels.',
            '- Type `=char raid (raid name)` (e.g. `=char raid ifrit`) to see the stats etc of the raid.',
            '- Type `=char raid attack (raid name)` (e.g. `=char raid attack siren`) to attack the raid.'
            f"- Attack multiple times in a row by inserting a number like `=char raid attack 7 siren` (up to {self.attackcap}).",
        )
        self.changelog = (
            ('12th February 2021', (
                'Overall stats increased slightly (including raids).',
                'Help and base commands overhauled.',
                'LB gauge - attack to charge, can be consumed for a free skill.',
                'Gil - consume AP to accumulate gil, in preparation of new function in future.',
                'You can now use HP to cast skills on yourself, except healing.',
                'All skills cast with HP no longer get you EXP.',
                'New skills. `=char skill`',
                'Potency of Protect and Shell increased. Skills now last for 5 turns.',
            )),
            ('11th February 2021', (
                'Healing with HP no longer gets EXP to prevent abuse.',
                'Raid overall DEX decreased with slight increase in ATK/MAG.',
                'New raids.'
            )),
            ('10th February 2021', (
                'You can use all skills at sub job potency. Main job skill still has higher potency.',
                'Using skills now get you EXP.',
                'Available number of bases doubled.',
                'Train and user attack EXP increased.',
                'Level - curve adjusted so earlier levels need fewer EXP.',
                'Critical rate and evasion rate nerfed for the third time.',
                'It is now possible to buff a dead target.',
                'It is now possible to revive (with a higher cost of healing). `=charhelp skill`'
            )),
            ('9th February 2021', (
                'Data reboot with the entire system rebalanced (please check various lists and helps).',
                'Please check your new stats and reset raid list.',
                'Level - EXP system to replace Job Levels - JP system (simpler).',
                'Stats are now raised with main / sub jobs. (`=charhelp job`)',
                'Skills. (`=charhelp skill`)'
                'Train function (mainly for newbies) to convert AP into EXP. (`=char train`)',
                'Able to attack player or raid conescutively by adding a number.',
                'Again, HP regen % is doubled and revival time is shortened to 3 hours.'
            )),
            ('8th February 2021', (
                'Duel function.',
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
        self.levelexp_init()
    def indextransform(self, index):
        # to counter google sheet eating user ids
        if isinstance(index, (int, float)):
            return f"u{index}"
        elif index == '':
            return index
        else:
            if index[0] == 'u':
                return int(index[1:])
            else:
                return index
    def dfsync(self):
        # sync online sheet into local data
        for sheetname, indexname in self.sheettuples:
             df = pd.DataFrame(self.spreadsheet.worksheet(sheetname).get_all_records())
             if 'User' in df.columns:
                 df['User'] = df['User'].apply(self.indextransform)
             if indexname != '':
                 df = df.set_index(indexname)
             self.dfdict[sheetname] = df
    def sheetsync(self, logsync=0, raidsync=0):
        # sync local data into online sheet
        df = self.dfdict['User'].copy()
        df.index = pd.Index([self.indextransform(a) for a in df.index.tolist()], name='User')
        set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
        if logsync:
            df = self.dfdict['Log'].copy()
            df['User'] = df['User'].apply(self.indextransform)
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
        new_row = (event, self.indextransform(userid), timestamp)
        self.spreadsheet.worksheet('Log').append_row(new_row)
        self.dfdict['Log'] = self.dfdict['Log'].append(new_log, ignore_index=True)
    def find_index(self, query, dfname):
        # auxiliary function to find index of a certain name
        df = self.dfdict[dfname]
        if 'Hidden' in df.columns:
            df = df[df['Hidden'] == '']
        if dfname == 'Job':
            indices = df['Job']
            indexer = lambda x: x['Job']
        elif dfname == 'Skill':
            indices = df['Skill']
            indexer = lambda x: x['Skill']
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
    def levelexp_init(self):
        # initialize level - EXP table
        basejp = 50
        self.nextlevelexp = []
        self.levelexp = [0]
        expsum = 0
        for i in range(self.levelcap):
            self.nextlevelexp.append(basejp + math.floor(i ** 1.7 * 4))
            expsum += self.nextlevelexp[i]
            self.levelexp.append(expsum)
    def calclevel(self, exp):
        # calculate level from total EXP
        level = 0
        for i in range(0, self.levelcap, 10):
            if exp < self.levelexp[i]:
                level = i - 10
                break
        else:
            level = i
        for i in range(level, self.levelcap + 1, 1):
            if exp < self.levelexp[i]:
                level = i - 1
                break
        else:
            return self.levelcap
        return level
    def calchitrate(self, accuracy):
        # calculate critical or hit rate from dex - agi
        if accuracy == 0:
            return 1
        elif accuracy >= 75:
            return 2
        elif accuracy <= -75:
            return 0
        else:
            if abs(accuracy) >= 25:
                modifier = 0.5 - 0.25 + abs(accuracy) * 0.01
            else:
                modifier = abs(accuracy) * 0.02
            if accuracy > 0:
                return 1 + modifier
            else:
                return 1 - modifier
    def calcstats(self, userid):
        # calculate stats given user id
        userdict = dict()
        userdict['Level'] = self.calclevel(self.dfdict['User'].loc[userid, 'EXP'])
        for statname in self.statlist:
            userdict[statname] = self.dfdict['Base'].loc[self.dfdict['User'].loc[userid, 'Base'], statname]
        level_tup = (
            ('Main', userdict['Level'] + 1),
            ('Sub1', (userdict['Level'] + 1) // 2),
            ('Sub2', userdict['Level'] // 2)
        )
        for job_col, job_level in level_tup:
            job_id = self.dfdict['User'].loc[userid, job_col]
            for statname in self.statlist:
                userdict[statname] += self.dfdict['Job'].loc[job_id, statname] * job_level
        return userdict
    def calcstatsraid(self, raid):
        # calculate raid stats given raid name
        raiddict = dict()
        base = self.dfdict['Raid'].loc[raid, 'Base']
        jobid = self.dfdict['Base'].loc[base, 'Main']
        jobrow = self.dfdict['Job'].loc[jobid]
        for statname in self.statlist:
            raiddict[statname] = self.dfdict['Base'].loc[base, statname] + jobrow[statname] * (self.dfdict['Raid'].loc[raid, 'Level'] + 1)
        return raiddict
    def userattack(self, attacker, defender, zero_attack=0):
        # perform an attack between users
        # get their status sheets
        attackdict = self.calcstats(attacker)
        defenddict = self.calcstats(defender)
        # skill check
        if self.dfdict['User'].loc[attacker, 'A_Skill'] != '':
            skillrow = self.dfdict['Skill'].loc[self.dfdict['User'].loc[attacker, 'A_Skill']]
            modifier = skillrow[self.dfdict['User'].loc[attacker, 'A_Potency']]
            if skillrow['Ally']:
                attackdict[skillrow['Stat']] = int(round(attackdict[skillrow['Stat']] * modifier))
            else:
                defenddict[skillrow['Stat']] = int(round(defenddict[skillrow['Stat']] * modifier))
        # pick higher potential damage
        damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
        hitrate = self.calchitrate(attackdict['DEX'] - defenddict['AGI'])
        # check attack criteria
        if self.dfdict['User'].loc[attacker, 'HP'] == 0:
            return (0, damage, hitrate, 'You are dead!')
        elif self.dfdict['User'].loc[attacker, 'AP'] < self.attack_apcost:
            return (0, damage, hitrate, 'Not enough AP!')
        elif self.dfdict['User'].loc[defender, 'HP'] == 0:
            return (0, damage, hitrate, 'Target is dead!')
        elif zero_attack:
            return (0, damage, hitrate)
        else:
            # consume skill duration
            if self.dfdict['User'].loc[attacker, 'A_Skill'] != '':
                new_duration = self.dfdict['User'].loc[attacker, 'A_Duration'] - 1
                if new_duration == 0:
                    self.dfdict['User'].loc[attacker, 'A_Skill'] = ''
                    self.dfdict['User'].loc[attacker, 'A_Potency'] = ''
                    self.dfdict['User'].loc[attacker, 'A_Duration'] = ''
                else:
                    self.dfdict['User'].loc[attacker, 'A_Duration'] = new_duration
            # consume AP
            self.dfdict['User'].loc[attacker, 'AP'] = int(self.dfdict['User'].loc[attacker, 'AP'] - self.attack_apcost)
            # calculate critical or hit rate
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            # EXP gain
            exp_gain = 15 + damage * hit // 30 + defenddict['Level'] * min(hit, 1) * 2
            # bonus EXP for killing
            kill = self.userdamage(defender, damage * hit)
            if kill:
                exp_gain += defenddict['Level']
            self.dfdict['User'].loc[attacker, 'EXP'] = self.dfdict['User'].loc[attacker, 'EXP'] + exp_gain
            # defender EXP regardless of hit
            defender_exp_gain = 10 + damage * hit // 45 + attackdict['Level'] * 2
            self.dfdict['User'].loc[defender, 'EXP'] = self.dfdict['User'].loc[defender, 'EXP'] + defender_exp_gain
            # LB gain
            lb_gain = ((defenddict['Level'] - 1) // attackdict['Level'] + 1) * 10
            lb_gain = min(100 - self.dfdict['User'].loc[attacker, 'LB'], lb_gain)
            self.dfdict['User'].loc[attacker, 'LB'] = self.dfdict['User'].loc[attacker, 'LB'] + lb_gain
            # defender LB gain
            defender_lb_gain = ((attackdict['Level'] - 1) // defenddict['Level'] + 1) * 10
            defender_lb_gain = min(100 - self.dfdict['User'].loc[defender, 'LB'], defender_lb_gain)
            self.dfdict['User'].loc[defender, 'LB'] = self.dfdict['User'].loc[defender, 'LB'] + defender_lb_gain
            # Gil gain
            self.dfdict['User'].loc[attacker, 'Gil'] = self.dfdict['User'].loc[attacker, 'Gil'] + self.attack_apcost
            return (1, damage, hitrate, hit, kill, exp_gain, defender_exp_gain)
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
            # gains EXP passively too
            self.dfdict['User'].loc[index, 'EXP'] = self.dfdict['User'].loc[index, 'EXP'] + 10 + userdict['Level']
        self.sheetsync()
    def userrevive(self, index):
        # revive dead user and log it
        userid = self.dfdict['Log'].loc[index, 'User']
        self.dfdict['User'].loc[userid, 'HP'] = self.calcstats(userid)['HP']
        self.dfdict['Log'].loc[index, 'Event'] = 'userrevived'
        self.dfdict['Log'].loc[index, 'Timestamp'] = datetime.strftime(datetime.now(), mydtformat)
        self.sheetsync(logsync=1)
    def userjobchange(self, user, job, job_col='Main'):
        # change user main or sub job
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        jobid = dfjob[dfjob['Job'] == job].tail(1).index.tolist()[0]
        if job_col == 'Main':
            df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'userjob']
            df = df[df['User'] == user.id]
            if len(df) > 0:
                thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(days=1)
                now = datetime.now()
                if now < thres:
                    remaining = thres - now
                    return (0, 0, remaining.seconds)
            if self.dfdict['User'].loc[user.id, 'Main'] == jobid:
                return (0, 1)
            self.dfdict['User'].loc[user.id, 'Main'] = jobid
            # reset sub jobs
            sub1jobid = self.dfdict['Job'].loc[jobid, 'Sub1']
            self.dfdict['User'].loc[user.id, 'Sub1'] = sub1jobid
            sub2jobid = self.dfdict['Job'].loc[jobid, 'Sub2']
            self.dfdict['User'].loc[user.id, 'Sub2'] = sub2jobid
            self.new_log('userjob', user.id, datetime.strftime(datetime.now(), mydtformat))
            return (1, self.dfdict['Job'].loc[sub1jobid, 'Job'], self.dfdict['Job'].loc[sub2jobid, 'Job'])
        else:
            for jcol in ('Main', 'Sub1', 'Sub2'):
                if self.dfdict['User'].loc[user.id, jcol] == jobid:
                    return (0, jcol)
            self.dfdict['User'].loc[user.id, job_col] = jobid
            return (1,)
    def userbase(self, user, base):
        # change base or start a user
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
            # initialize user
            new_user = {
                'Base': base,
                'HP': baserow['HP'],
                'AP': baserow['AP'],
                'EXP': 0,
                'Main': baserow['Main'],
                'Sub1': self.dfdict['Job'].loc[baserow['Main'], 'Sub1'],
                'Sub2': self.dfdict['Job'].loc[baserow['Main'], 'Sub2'],
                'LB': 0,
                'Gil': 0
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
            # level up the raid and fully recovers
            self.dfdict['Raid'].loc[raid, 'Level'] = self.dfdict['Raid'].loc[raid, 'Level'] + 1
            self.dfdict['Raid'].loc[raid, 'HP'] = self.calcstatsraid(raid)['HP']
            return 1
        else:
            return 0
    def raidattack(self, user, raid, zero_attack=0):
        # perform an attack between an user and a raid
        # get their status sheets
        userdict = self.calcstats(user)
        raiddict = self.calcstatsraid(raid)
        # skill check
        if self.dfdict['User'].loc[user, 'A_Skill'] != '':
            skillrow = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user, 'A_Skill']]
            modifier = skillrow[self.dfdict['User'].loc[user, 'A_Potency']]
            if skillrow['Ally']:
                userdict[skillrow['Stat']] = int(round(userdict[skillrow['Stat']] * modifier))
            else:
                raiddict[skillrow['Stat']] = int(round(raiddict[skillrow['Stat']] * modifier))
        # pick higher potential damage
        damage = max(userdict['ATK'] - raiddict['DEF'], userdict['MAG'] - raiddict['SPR'], 0)
        hitrate = self.calchitrate(userdict['DEX'] - raiddict['AGI'])
        raid_damage = max(raiddict['ATK'] - userdict['DEF'], raiddict['MAG'] - userdict['SPR'], 0)
        raid_hitrate = self.calchitrate(raiddict['DEX'] - userdict['AGI'])
        # check attack criteria
        if self.dfdict['User'].loc[user, 'HP'] == 0:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'You are dead!')
        elif self.dfdict['User'].loc[user, 'AP'] < self.attack_apcost:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'Not enough AP!')
        elif zero_attack:
            return (0, damage, hitrate, raid_damage, raid_hitrate)
        else:
            # consume skill duration
            if self.dfdict['User'].loc[user, 'A_Skill'] != '':
                new_duration = self.dfdict['User'].loc[user, 'A_Duration'] - 1
                if new_duration == 0:
                    self.dfdict['User'].loc[user, 'A_Skill'] = ''
                    self.dfdict['User'].loc[user, 'A_Potency'] = ''
                    self.dfdict['User'].loc[user, 'A_Duration'] = ''
                else:
                    self.dfdict['User'].loc[user, 'A_Duration'] = new_duration
            # consume AP
            self.dfdict['User'].loc[user, 'AP'] = int(self.dfdict['User'].loc[user, 'AP'] - self.attack_apcost)
            # check critical or hit
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            # EXP gain
            exp_gain = 30 + (damage * hit) // 30 + self.dfdict['Raid'].loc[raid, 'Level'] * 3
            # Bonus EXP for killing
            kill = self.raiddamage(raid, damage * hit)
            if kill:
                exp_gain += self.dfdict['Raid'].loc[raid, 'Level'] * 3
            self.dfdict['User'].loc[user, 'EXP'] = self.dfdict['User'].loc[user, 'EXP'] + exp_gain
            # LB gain
            lb_gain = (self.dfdict['Raid'].loc[raid, 'Level'] // userdict['Level'] + 1) * 10
            lb_gain = min(100 - self.dfdict['User'].loc[user, 'LB'], lb_gain)
            self.dfdict['User'].loc[user, 'LB'] = self.dfdict['User'].loc[user, 'LB'] + lb_gain
            # Gil gain
            self.dfdict['User'].loc[user, 'Gil'] = self.dfdict['User'].loc[user, 'Gil'] + self.attack_apcost
            # raid counter attack
            if raid_hitrate > 1:
                raid_hit = 1 + ((raid_hitrate - 1) > random.random())
            else:
                raid_hit = raid_hitrate > random.random()
            raid_kill = self.userdamage(user, raid_damage * raid_hit)
            return (1, damage, hitrate, raid_damage, raid_hitrate, hit, kill, raid_hit, raid_kill, exp_gain)
    ############################
    # discord embed generators #
    ############################
    def helpmanual(self, kw=''):
        # generate help manual
        embed = discord.Embed()
        kw = kw.lower().rstrip('s')
        if kw in self.helptup.keys():
            kw = self.helptup[kw]
            embed.title = f"{kw} Help"
            embed.description = self.intro[kw]
            embed.add_field(name = 'In Depth', value = '\n'.join(self.indepth[kw]), inline = False)
            if kw == 'Skill':
                embed.add_field(name = 'Healing', value = '\n'.join(self.indepth['Healing']), inline = False)
        else:
            embed.title = 'Engelbert Help'
            embed.description = self.helpintro
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
        embed.description = self.intro['Base'] + '\n`=charhelp base` for more info.'
        base_list = self.dfdict['Base'][self.dfdict['Base']['Hidden'] == ''].index.tolist()
        base_count = 0
        field_list = []
        for base in base_list:
            field_list.append(base)
            base_count += 1
            if base_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(field_list))
                field_list = []
        if len(field_list) > 0:
            embed.add_field(name='-', value='\n'.join(field_list))
        return embed
    def listraid(self):
        # generate embed of list of available bases
        embed = discord.Embed()
        embed.title = 'List of Raids'
        embed.description = self.intro['Raid'] + '\n`=charhelp raid` for more info.'
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
        embed.description = self.intro['Job'] + '\n`=charhelp job` for more info.'
        df = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        job_list = []
        job_count = 0
        for _, row in df.iterrows():
            desc_list = []
            for stat in self.statlist2:
                desc_list.append(f"{stat} `{row[stat]}`")
            desc_list.append(f"{self.dfdict['Skill'].loc[row['Skill'], 'Skill']}")
            job_list.append(f"**{row['Job']}**\n - {' | '.join(desc_list)}")
            job_count += 1
            if job_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(job_list), inline=False)
                job_list = []
        if len(job_list) > 0:
            embed.add_field(name='-', value='\n'.join(job_list), inline=False)
        return embed
    def listskill(self):
        # generate embed of list of available skills
        embed = discord.Embed()
        embed.title = 'List of Skills'
        embed.description = self.intro['Skill'] + '\n`=charhelp skill` for more info.'
        df = self.dfdict['Skill']
        skill_list = []
        skill_count = 0
        for _, row in df.iterrows():
            desc_list = []
            if row['Ally']:
                target = 'ally'
            else:
                target = 'enemy'
            if row['Healing']:
                desc_list.append('Healing')
            elif row['Ally'] > 0:
                desc_list.append('Buff')
                desc_list.append(f"Increases {target} {row['Stat']} during battle.")
            else:
                desc_list.append('Debuff')
                desc_list.append(f"Partially ignores {target} {row['Stat']} during battle.")
            skill_list.append(f"**{row['Skill']}**\n - {' | '.join(desc_list)}")
            skill_count += 1
            if skill_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
                skill_list = []
        if len(skill_list) > 0:
            embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
        return embed
    def infojobchange(self, user, jobchange_dict):
        # generate info embed of job change
        embed = discord.Embed()
        embed.title = f"{user.name} Job Change"
        change = 0
        desc_list = []
        for k, v in jobchange_dict.items():
            if k == 'Main':
                result_tup = self.userjobchange(user, v)
                if result_tup[0]:
                    desc_list = (
                        'Success! Your jobs are now the following:',
                        f"Main: {v}",
                        f"Sub1: {result_tup[1]}",
                        f"Sub2: {result_tup[2]}")
                    change = 1
                elif result_tup[1]:
                    desc_list.append('It is already your current main job!')
                else:
                    desc_list.append(f"{result_tup[2] // 3600} hours {result_tup[2] % 3600 // 60} minutes left before you can change your main job.")
            else:
                result_tup = self.userjobchange(user, v, k)
                if result_tup[0]:
                    desc_list.append(f"Success! Your {k} is now {v}.")
                    change = 1
                else:
                    desc_list.append(f"{v} is already your {result_tup[1]} job!")
        if change:
            self.sheetsync()
        embed.description = '\n'.join(desc_list)
        return embed
    def infobase(self, base):
        # generate info embed of specific base
        embed = discord.Embed()
        row = self.dfdict['Base'].loc[base]
        embed.title = base
        desc_list = []
        for stat in self.statlist2:
            desc_list.append(f"{stat}: `{row[stat]}`")
        desc_list.append(f"Default Main: {self.dfdict['Job'].loc[row['Main'], 'Job']}")
        embed.description = '\n'.join(desc_list)
        thumbnail_url = row['Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed_colour = row['Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    def infouser(self, user):
        # generate info embed of specific user
        embed = discord.Embed()
        row = self.dfdict['User'].loc[user.id]
        embed.title = user.name
        # basic info
        desc_list = []
        userdict = self.calcstats(row.name)
        desc_list.append(f"Base: {row['Base']}")
        if userdict['Level'] == self.levelcap:
            desc_list.append(f"Level: {userdict['Level']} (MAX)")
        else:
            desc_list.append(f"Level: {userdict['Level']}")
            desc_list.append(f"*Next Level: {self.levelexp[userdict['Level'] + 1] - row['EXP']} EXP*")
        desc_list.append(f"HP: {row['HP']}/{userdict['HP']}")
        desc_list.append(f"AP: {row['AP']}/{userdict['AP']}")
        desc_list.append(f"LB: {row['LB']}%")
        desc_list.append(f"Gil: {row['Gil']}")
        if row['A_Skill'] != '':
            desc_list.append(f"Status: {self.dfdict['Skill'].loc[row['A_Skill'], 'Skill']} ({row['A_Duration']})")
        embed.description = '\n'.join(desc_list)
        # field of stats
        field_list = []
        for stat in self.statlist2:
            field_list.append(f"{stat}: {userdict[stat]}")
        embed.add_field(name='Stats', value='\n'.join(field_list))
        # field of current jobs
        field_list = []
        for job_col in ('Main', 'Sub1', 'Sub2'):
            job_line = f"{job_col}: {self.dfdict['Job'].loc[row[job_col], 'Job']}"
            field_list.append(job_line)
        skillid = self.dfdict['Job'].loc[row['Main'], 'Skill']
        field_list.append(f"Main Skill: {self.dfdict['Skill'].loc[skillid, 'Skill']}")
        embed.add_field(name='Jobs', value='\n'.join(field_list))
        # show revival timer if dead
        if row['HP'] == 0:
            dflog = self.dfdict['Log'][self.dfdict['Log']['Event'] == 'userdead']
            deadtime = dflog[dflog['User'] == user.id].tail(1)['Timestamp'].tolist()[0]
            thres = datetime.strptime(deadtime, mydtformat) + timedelta(hours=engel.revivehours)
            revivaltd = thres - datetime.now()
            revivalstr = f"{revivaltd.seconds // 60 + 1} minutes remaining."
            embed.add_field(name='Revival Time', value=revivalstr, inline=False)
        # decoration
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
        desc_list.append(f"Level: {row['Level']}")
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
    def infoduel(self, attacker, defender):
        # generate result embed of a duel
        embed = discord.Embed()
        embed.title = f"{attacker.name} VS {defender.name}"
        # get their status sheets
        attackdict = self.calcstats(attacker.id)
        attackhp = attackdict['HP']
        defenddict = self.calcstats(defender.id)
        defendhp = defenddict['HP']
        # pick higher potential damage
        damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
        hitrate = self.calchitrate(attackdict['DEX'] - defenddict['AGI'])
        counter_damage = max(defenddict['ATK'] - attackdict['DEF'], defenddict['MAG'] - attackdict['SPR'], 0)
        counter_hitrate = self.calchitrate(defenddict['DEX'] - attackdict['AGI'])
        desc_list = []
        desc_list.append(f"*{attacker.name} has {min(hitrate, 1) * 100:.0f}% of doing {damage} damage.*")
        desc_list.append(f"*{attacker.name} has {max(hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
        desc_list.append(f"*{defender.name} has {min(counter_hitrate, 1) * 100:.0f}% of doing {counter_damage} damage.*")
        desc_list.append(f"*{defender.name} has {max(counter_hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        for i in range(5):
            field_name = f"Round {i+1}"
            field_list = [f"{attacker.name} HP `{attackhp}` | {defender.name} HP `{defendhp}`"]
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            if hit == 2:
                field_list.append(f"{attacker.name} landed a critical hit with {damage * hit} damage.")
            elif hit == 1:
                field_list.append(f"{attacker.name} successfully attacked with {damage * hit} damage.")
            else:
                field_list.append(f"{attacker.name} missed.")
            if counter_hitrate > 1:
                counter_hit = 1 + ((counter_hitrate - 1) > random.random())
            else:
                counter_hit = counter_hitrate > random.random()
            if counter_hit == 2:
                field_list.append(f"{defender.name} landed a critical hit with {counter_damage * counter_hit} damage.")
            elif counter_hit == 1:
                field_list.append(f"{defender.name} successfully attacked with {counter_damage * counter_hit} damage.")
            else:
                field_list.append(f"{defender.name} missed.")
            attackhp = max(attackhp - counter_damage * counter_hit, 0)
            defendhp = max(defendhp - damage * hit, 0)
            embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
            if attackhp == 0 or defendhp == 0:
                break
        field_name = 'Result'
        field_list = [f"{attacker.name} HP `{attackhp}` | {defender.name} HP `{defendhp}`"]
        if attackhp == defendhp:
            field_list.append('It is a draw!')
        elif attackhp > defendhp:
            field_list.append(f"{attacker.name} won!")
        else:
            field_list.append(f"{defender.name} won!")
        embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        defender_base = self.dfdict['User'].loc[defender.id, 'Base']
        embed_colour = self.dfdict['Base'].loc[defender_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    def infotrain(self, user, ap_consume=3):
        # generate result embed of a training session
        embed = discord.Embed()
        embed.title = f"{user.name} Training"
        total_exp_gain = 0
        ap_consume = min(self.dfdict['User'].loc[user.id, 'AP'], ap_consume)
        self.dfdict['User'].loc[user.id, 'AP'] = self.dfdict['User'].loc[user.id, 'AP'] - ap_consume
        self.dfdict['User'].loc[user.id, 'Gil'] = self.dfdict['User'].loc[user.id, 'Gil'] + ap_consume
        for _ in range(ap_consume):
            exp_gain = 10 + int(self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) * 0.9)
            total_exp_gain += exp_gain
            self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] +  exp_gain # gains EXP
        if total_exp_gain > 0:
            self.sheetsync()
        embed.description = f"You spent {ap_consume} AP and gained {total_exp_gain} EXP."
        return embed
    def infoskill(self, user, skill, target=None, consumehp=0, consumelb=0):
        # generate result embed of a skill
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user.id]
        skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
        skillrow = self.dfdict['Skill'].loc[skillid]
        embed.title = f"{user.name} - {skillrow['Skill']}"
        # check if skill available and what potency
        if consumelb and userrow['LB'] < 100:
            embed.description = f'Your LB gauge is not full yet.'
            return embed
        if skillid == self.dfdict['Job'].loc[userrow['Main'], 'Skill']:
            potency = 'Main'
        else:
            potency = 'Sub'
        # check target
        if target == None:
            target = user
        if target.id != user.id and not skillrow['Ally']:
            embed.description = f"{skill} cannot be casted on others."
            return embed
        hpcost = math.ceil(self.calcstats(user.id)['HP'] * self.skill_hpcost)
        apcost = self.skill_apcost
        hprecovery = math.floor(self.calcstats(user.id)['HP'] * skillrow[potency])
        # no EXP gain if HP consume
        if consumehp:
            exp_gain = 0
        else:
            exp_gain = self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) + self.calclevel(self.dfdict['User'].loc[target.id, 'EXP'])
        revive = 0
        # check if is to revive
        if skillrow['Healing'] and self.dfdict['User'].loc[target.id, 'HP'] == 0:
            num_times = math.ceil(self.calcstats(target.id)['HP'] / hprecovery)
            if num_times > 1 and consumelb:
                embed.description = f"You are not strong enough to revive {target.name} with one cast."
                return embed
            hprecovery = hprecovery * num_times
            hpcost = hpcost * num_times
            apcost = apcost * num_times
            exp_gain = exp_gain * num_times
            revive = 1
            if consumehp == 0:
                desc_list = ['Target is dead!',
                    f"If you do not mind paying {apcost} AP, type `=char skill {skillrow['Skill']} | target | revive`."
                ]
                if target.id != user.id:
                    desc_list.append(f"If you do not mind paying {hpcost} HP, type `=char skill {skill} | target | hp`.")
                embed.description = '\n'.join(desc_list)
                return embed
        # check HP or AP amount or criteria to consume
        if consumehp == 1:
            if target.id == user.id and skillrow['Healing']:
                embed.description = 'You cannot consume HP to heal yourself.'
                return embed
            if userrow['HP'] <= hpcost:
                embed.description = f"You need at least {hpcost + 1} HP."
                return embed
            else:
                self.dfdict['User'].loc[user.id, 'HP'] = self.dfdict['User'].loc[user.id, 'HP'] - hpcost
        elif consumelb == 1:
            self.dfdict['User'].loc[user.id, 'LB'] = 0
        elif userrow['AP'] < apcost:
            embed.description = f"You need to have at least {apcost} AP."
            return embed
        else:
            self.dfdict['User'].loc[user.id, 'AP'] = self.dfdict['User'].loc[user.id, 'AP'] - apcost
            self.dfdict['User'].loc[user.id, 'Gil'] = self.dfdict['User'].loc[user.id, 'Gil'] + apcost
        # Actual skill execution
        self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] + exp_gain
        if skillrow['Healing']:
            if revive:
                df = self.dfdict['Log'][self.dfdict['Log']['Event'] == 'userdead']
                logindex = df[df['User'] == target.id].tail(1).index.tolist()[0]
                self.userrevive(logindex)
                embed.description = f"You casted {skillrow['Skill']} {num_times} time(s) to revive {target.name}. You gained {exp_gain} EXP."
                return embed
            else:
                self.dfdict['User'].loc[target.id, 'HP'] = min(self.dfdict['User'].loc[target.id, 'HP'] + hprecovery, self.calcstats(target.id)['HP'])
                embed.description = f"You casted {skillrow['Skill']} on {target.name}, healing {hprecovery} HP. You gained {exp_gain} EXP."
        else:
            self.dfdict['User'].loc[target.id, 'A_Skill'] = skillid
            self.dfdict['User'].loc[target.id, 'A_Potency'] = potency
            self.dfdict['User'].loc[target.id, 'A_Duration'] = self.skillduration
            if user.id != target.id:
                embed.description = f"You casted {skillrow['Skill']} on {target.name}. You gained {exp_gain} EXP."
            else:
                embed.description = f"You casted {skillrow['Skill']}, gaining {exp_gain} EXP."
        self.sheetsync()
        return embed
    def infoattack(self, attacker, defender, num_times=1):
        # generate result embed of an attack
        embed = discord.Embed()
        embed.title = f"{attacker.name} VS {defender.name}"
        if num_times == 0:
            zero_attack = 1
        else:
            zero_attack = 0
        result_tup = self.userattack(attacker.id, defender.id, zero_attack)
        desc_list = []
        desc_list.append(f"*You have {min(result_tup[2], 1) * 100:.0f}% of doing {result_tup[1]} damage.*")
        desc_list.append(f"*You have {max(result_tup[2] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        exp_gain_total = 0
        defender_exp_gain_total = 0
        attack_count = 0
        field_list = []
        for i in range(num_times):
            if attack_count == 10:
                embed.add_field(name = 'Battle Log', value = '\n'.join(field_list), inline=False)
                field_list = []
                attack_count = 0
            if i != 0:
                result_tup = self.userattack(attacker.id, defender.id)
            if result_tup[0] == 0:
                embed.add_field(name=f"Only attacked {i} time(s).", value=result_tup[3], inline=False)
                break
            else:
                _, damage, hitrate, hit, kill, exp_gain, defender_exp_gain = result_tup
                if hit == 2:
                    field_list.append(f"You landed a critical hit with {damage * hit} damage.")
                elif hit == 1:
                    field_list.append(f"You successfully attacked with {damage} damage.")
                else:
                    field_list.append(f"You missed.")
                exp_gain_total += exp_gain
                defender_exp_gain_total += defender_exp_gain
                if kill:
                    field_list.append(f"{defender.name} is KO-ed.")
                    break
            attack_count += 1
        field_list.append(f"You gained {exp_gain_total} EXP. {defender.name} gained {defender_exp_gain_total} EXP.")
        embed.add_field(name = 'Battle Log', value = '\n'.join(field_list), inline=False)
        for user in (attacker, defender):
            field_list = []
            field_list.append(f"Level: {self.calclevel(self.dfdict['User'].loc[user.id, 'EXP'])}")
            for statname in ('HP', 'AP'):
                field_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
            embed.add_field(name = user.name, value = '\n'.join(field_list))
        defender_base = self.dfdict['User'].loc[defender.id, 'Base']
        embed_colour = self.dfdict['Base'].loc[defender_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        if exp_gain_total + defender_exp_gain_total > 0:
            self.sheetsync()
        return embed
    def infoattackraid(self, user, raid, num_times=1):
        # generate result embed of an attack
        embed = discord.Embed()
        embed.title = f"{user.name} VS {raid}"
        if num_times == 0:
            zero_attack = 1
        else:
            zero_attack = 0
        result_tup = self.raidattack(user.id, raid, zero_attack)
        desc_list = []
        desc_list.append(f"*You have {min(result_tup[2], 1) * 100:.0f}% of doing {result_tup[1]} damage.*")
        desc_list.append(f"*You have {max(result_tup[2] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        desc_list.append(f"*{raid} has {min(result_tup[4], 1) * 100:.0f}% of doing {result_tup[3]} damage to you.*")
        desc_list.append(f"*{raid} has {max(result_tup[4] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        exp_gain_total = 0
        attack_count = 0
        field_list = []
        for i in range(num_times):
            if attack_count == 5:
                embed.add_field(name = 'Battle Log', value = '\n'.join(field_list), inline=False)
                field_list = []
                attack_count = 0
            if i != 0:
                result_tup = self.raidattack(user.id, raid)
            if result_tup[0] == 0:
                embed.add_field(name=f"Only attacked {i} time(s).", value=result_tup[5], inline=False)
                break
            else:
                _, damage, hitrate, raid_damage, raid_hitrate, hit, kill, raid_hit, raid_kill, exp_gain = result_tup
                if hit == 2:
                    field_list.append(f"You landed a critical hit with {damage * hit} damage.")
                elif hit == 1:
                    field_list.append(f"You successfully attacked with {damage} damage.")
                else:
                    field_list.append(f"You missed.")
                if kill:
                    self.new_log(f"{raid} kill", user.id, datetime.strftime(datetime.now(), mydtformat))
                    field_list.append(f"{raid} is KO-ed. A new level has now been spawned.")
                exp_gain_total += exp_gain
                if raid_hit == 2:
                    field_list.append(f"{raid} landed a critical hit with {raid_damage * raid_hit} damage.")
                elif raid_hit == 1:
                    field_list.append(f"{raid} successfully countered with {raid_damage} damage.")
                else:
                    field_list.append(f"{raid} missed.")
                if raid_kill:
                    field_list.append(f"You are KO-ed.")
                    break
            attack_count += 1
        field_list.append(f"You gained {exp_gain_total} EXP.")
        embed.add_field(name = 'Battle Log', value = '\n'.join(field_list), inline=False)
        field_list = []
        field_list.append(f"Level: {self.calclevel(self.dfdict['User'].loc[user.id, 'EXP'])}")
        for statname in ('HP', 'AP'):
            field_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
        embed.add_field(name = user.name, value = '\n'.join(field_list))
        field_list = []
        field_list.append(f"Level: {self.dfdict['Raid'].loc[raid, 'Level']}")
        field_list.append(f"HP: {self.dfdict['Raid'].loc[raid, 'HP']}")
        embed.add_field(name = raid, value = '\n'.join(field_list))
        raid_base = self.dfdict['Raid'].loc[raid, 'Base']
        embed_colour = self.dfdict['Base'].loc[raid_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        if exp_gain_total > 0:
            self.sheetsync(raidsync=1)
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
                        if user.id in self.dfdict['User'].index.tolist():
                            return discord.Embed(description = 'You already started. See your base by `=char info` or change your base with `=char base change` instead.')
                        base = self.find_index(' '.join(arg[2:]), 'Base')
                        if base == 'NOTFOUND':
                            return discord.Embed(description = 'Base not found. Try checking `=char base`.')
                        return discord.Embed(description = self.userbase(user, base))
                    else:
                        base = self.find_index(' '.join(arg[1:]), 'Base')
                        if base == 'NOTFOUND':
                            return discord.Embed(description = 'Base not found. Try checking `=char base`.')
                        return self.infobase(base)
            elif arg[0] == 'job':
                if len(arg) == 1:
                    # list of jobs
                    return self.listjob()
                else:
                    if arg[1].lower() in ('main', 'change') and len(arg) > 2:
                        job = self.find_index(' '.join(arg[2:]), 'Job')
                        if job == 'NOTFOUND':
                            return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                        else:
                            return self.infojobchange(user, {'Main': job})
                    elif arg[1].lower() == 'sub1' and len(arg) > 2:
                        job = self.find_index(' '.join(arg[2:]), 'Job')
                        if job == 'NOTFOUND':
                            return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                        else:
                            return self.infojobchange(user, {'Sub1': job})
                    elif arg[1].lower() == 'sub2' and len(arg) > 2:
                        job = self.find_index(' '.join(arg[2:]), 'Job')
                        if job == 'NOTFOUND':
                            return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                        else:
                            return self.infojobchange(user, {'Sub2': job})
                    elif arg[1].lower() in ('sub', 'subs') and len(arg) > 2:
                        jobargs = [a.strip() for a in ' '.join(arg[2:]).split('|')]
                        if len(jobargs) == 1:
                            job = self.find_index(jobargs[0], 'Job')
                            if job == 'NOTFOUND':
                                return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                            else:
                                return self.infojobchange(user, {'Sub1': job})
                        else:
                            job1 = self.find_index(jobargs[0], 'Job')
                            job2 = self.find_index(jobargs[1], 'Job')
                            if 'NOTFOUND' in (job1, job2):
                                return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                            else:
                                return self.infojobchange(user, {'Sub1': job1, 'Sub2': job2})
                    else:
                        # find job and info (not needed atm)
                        return discord.Embed(description = 'Try `=charhelp job`.')
            elif arg[0] == 'skill':
                if len(arg) == 1:
                    # list of jobs
                    return self.listskill()
                else:
                    skillargs = [a.strip() for a in ' '.join(arg[1:]).split('|')]
                    skill = self.find_index(skillargs[0], 'Skill')
                    if skill == 'NOTFOUND':
                        return discord.Embed(description = 'Skill not found. Try checking `=char skill`.')
                    consumehp = 0
                    consumelb = 0
                    if len(skillargs) == 3:
                        if skillargs[2].lower() == 'hp':
                            consumehp = 1
                        elif skillargs[2].lower() == 'revive':
                            consumehp = -1
                        elif skillargs[2].lower() == 'lb':
                            consumelb = 1
                    if len(skillargs) > 1:
                        try:
                            target = await commands.MemberConverter().convert(ctx, skillargs[1])
                            if target.id in self.dfdict['User'].index:
                                return self.infoskill(user, skill, target, consumehp, consumelb)
                            else:
                                return discord.Embed(description = 'User not found or did not start a character.')
                        except commands.BadArgument:
                            return discord.Embed(description = 'User not found or did not start a character.')
                    else:
                        return self.infoskill(user, skill)
                    return discord.Embed(description = 'Try `=charhelp skill`.')
            elif arg[0] == 'train':
                if len(arg) > 1:
                    if arg[1].isnumeric():
                        return self.infotrain(user, int(arg[1]))
                return self.infotrain(user)
            elif arg[0] == 'attack':
                if len(arg) == 1:
                    return discord.Embed(description = 'Try `=charhelp char`.')
                else:
                    if arg[1].isnumeric() and len(arg) > 2:
                        num_times = min(int(arg[1]), 20)
                        defender_name = ' '.join(arg[2:])
                    else:
                        num_times = 1
                        defender_name = ' '.join(arg[1:])
                    try:
                        # find member of said name to attack
                        defender = await commands.MemberConverter().convert(ctx, defender_name)
                        if defender.id in self.dfdict['User'].index:
                            return self.infoattack(user, defender, num_times)
                        else:
                            return discord.Embed(description = 'User not found or did not start a character.')
                    except commands.BadArgument:
                        return discord.Embed(description = 'User not found or did not start a character.')
            elif arg[0] == 'duel':
                if len(arg) == 1:
                    return discord.Embed(description = 'Try `=charhelp char`.')
                else:
                    try:
                        # find member of said name to attack
                        defender = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if defender.id in self.dfdict['User'].index:
                            return self.infoduel(user, defender)
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
                        if arg[2].isnumeric() and len(arg) > 3:
                            num_times = min(int(arg[2]), 20)
                            raid_name = ' '.join(arg[3:])
                        else:
                            num_times = 1
                            raid_name = ' '.join(arg[2:])
                        raid = self.find_index(raid_name, 'Raid')
                        if raid == 'NOTFOUND':
                            return discord.Embed(description = 'Raid not found. Try checking `=char raid`.')
                        else:
                            return self.infoattackraid(user, raid, num_times)
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
                return discord.Embed(description = 'Try `=charhelp`.')

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
            embed.set_footer(text='Now in beta v2. Check changelog for changes. Prone to adjustment/bugs...')
            await ctx.send(embed = embed)
            await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp'])
    async def engelberthelp(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, 'help', *arg)
        embed.set_footer(text='Now in beta v2. Check changelog for changes. Prone to adjustment/bugs...')
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama', 'char'])
    async def engelbert(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, *arg)
        embed.set_footer(text='Now in beta v2. Check changelog for changes. Prone to adjustment/bugs...')
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)
