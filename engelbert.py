import re, random, discord, math
import pandas as pd
import numpy as np
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
        # status booleans
        self.syncpend = 0
        self.raidsync = 0
        self.logsync = 0
        self.maint = 0
        # gameplay constants
        self.attack_apcost = 3
        self.hpregen = 0.2
        self.apregen = 6
        self.levelcap = 99
        self.raidcap = 120
        self.raidcap2 = 79
        self.revivehours = 3
        self.cdjob = 12
        self.cdbase = 24
        self.skill_apcost = 5
        self.skill_hpcost = 0.2 # % HP cost
        self.skillduration = 5
        self.attackcap = 20 # number of attacks
        self.gachacost  = 10
        # GACHA RATE
        self.gacha_rate = {
            'i1': 50,
            'i2': 20,
            'i3': 20,
            'i4': 6,
            'i5': 2,
            'i6': 1,
            'i7': 1
        }
        self.drop_rate = {
            0: {
                'i1': 58,
                'i2': 20,
                'i3': 20,
                'i4': 2
            },
            50: {
                'i1': 56,
                'i2': 20,
                'i3': 20,
                'i4': 2,
                'i6': 1,
                'i7': 1
            },
            80: {
                'i2': 50,
                'i3': 35,
                'i4': 4,
                'i5': 1,
                'i6': 5,
                'i7': 5
            },
            '80': {
                'i1': 100
            },
            100: {
                'i2': 38,
                'i3': 25,
                'i4': 15,
                'i5': 2,
                'i6': 10,
                'i7': 10
            },
            '100': {
                'i1': 80,
                'i2': 20
            }
        }
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
        self.usernotfound = 'Choose a base first with `=char base start (base name)`. Try `=charhelp base`.'
        self.targetnotfound = 'User not found or did not start a character.'
        self.defaultfooter = 'Now in beta v2. Check changelog for changes. Prone to adjustment/bugs...'
        self.manual = dict()
        self.manual['character'] = ((
            'Description', (
                'Each Discord ID can only have one character.',
                'To start a character, you need to pick a base (check out `=charhelp base`).',
            )),(
            'Information', (
                '- Type `=char info` to check your character if you already started one.',
                '- Type `=char info (user ping)` (e.g. `=char info @Caelum`) to check character of another user.',
                '- Your stats are calculated from your Level and your current main/sub jobs.',
                '- Level raises by earning EXP.',
                f"- If your HP reaches zero, you cannot battle and will be revived after {self.revivehours} hours.",
                f"- AP is action points, spent for various actions.",
                '- LB is filled every time you battle or are attacked.',
                '- When fully filled, LB can be consumed to cast a skill (`=charhelp skill`).'
                '- For other stats please refer to battle mechanics. (`=charhelp battle`)',
            )),(
            'Train', (
                '- Mainly gained from raids. (`=charhelp raid`)',
                '- Type `=char train` or `=char train (number of AP)` (e.g. `=char train 10`) to quickly spend AP for EXP.',
                '- You can use items that restore LB to gain EXP.',
                '- Type `=char train (number) (item name)` (e.g. `=char train 3 hero`).',
            )),(
            'Hourly Regen', (
                f"- Your HP and AP regen {self.hpregen * 100}% and {self.apregen} respectively every hour.",
                '- If your AP is full, HP regen is doubled instead.',
                '- You also gain a small amount of EXP.',
            ))
        )
        self.manual['battle'] = ((
            'Description', (
                'Currently there are two types of battles: PVP and raids (`=charhelp raid`).',
                'As in any other RPG, the objective is to bring down the target HP to 0 while keeping yourself alive.',
            )),(
            'Mechanics', (
                '- When you attack a target, attacker ATK, MAG, DEX, defender DEF, SPR, AGI are used in calculation.',
                '- Damage is calculated by `ATK - DEF` or `MAG - SPR` (whichever larger).',
                '- You can only land critical if your DEX is higher than the opponent',
                '- You can only evade attacks if your AGI is higher than the opponent.',
                '- Critical rate is scaled by `(Attacker DEX - Defender AGI)`',
                '- Evasion rate is scaled by `(Defender AGI - Attacker DEX)`.',
                '- They use the same formula: 1~25 = 2% per point, 26~75 = 1% per point.',
                '- Critical damage is 2x regular damage.',
            )),(
            'PVP', (
                '- Two types of PVP: attacks and duels.',
                f"- Attacks cost {self.attack_apcost}.",
                '- Both attacker and target gain EXP scaled to damage and opponent level.',
                '- Type `=char attack (user ping)` (e.g. `=char attack @Caelum`) to another player.',
                f"- Type `=char attack (number) (user ping)` (e.g. `=char attack 6 @Caelum`) to attack multiple times  (up to {self.attackcap}).",
                '- Duels are basically battle simulation just for fun.',
                '- Duels do not cost AP nor result in any gain or loss.',
                '- Skill effects and auto settings do not take effect in duels.',
                '- Type `=char duel (user ping)` to duel with character of another user.',
            )),
        )
        self.manual['base'] = ((
            'Description', (
                'A base determines your base stats and your info picture where available.',
                'Every base has a default set of jobs but you can change afterwards.',
                f"Your base can be changed every {self.cdbase} hours. Changing a base does not change your jobs.",
            )),(
            'Commands', (
                '- Type `=char base` to find list of available bases.',
                '- Type `=char base (base name)` (e.g. `=char base lasswell`) to read info of the base.',
                '- Type `=char base start (base name)` (e.g. `=char base start jake`) to start your character.',
                '- Type `=char base change (base name)` (e.g. `=char base change rain`) to change the base of your character.',
            ))
        )
        self.manual['job'] = ((
            'Description', (
                'Your jobs determine most of your stats.'
                'You have 100% growth rate of main job and 50% of each sub job.'
                f"Main job can be changed every {self.cdjob} hours, but changing sub jobs has no limit."
                'Changing main job also resets your sub jobs. They can be changed anytime however.'
            )),(
            'Commands', (
                '- Type `=char job` to find list of jobs and their growth rate.',
                '- Type `=char job main (job name)` (e.g. `=char job main red mage`) to change main job.',
                '- Type `=char job sub1 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 1.',
                '- Type `=char job sub2 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 2.',
                '- Type `=char job subs (job name) | (job name)` (e.g. `=char job subs green mage | mechanic`) to change both sub jobs at once.'
            ))
        )
        self.manual['skill'] = ((
            'Description', (
                'You can use all skills available, but the skill of your main job will have higher potency.',
                'There are three types of skills - healing, buff, debuff.',
            )),(
            'Information', (
                '- Healing and buff skills can be cast on other users.',
                '- Skills do not apply on duels.',
                '- Only 1 buff or debuff skill can be active at one time.',
                f"- By default, skills cost {self.skill_apcost} AP to cast.",
                f"- You can opt to consume {self.skill_hpcost*100:.0f}% HP, 100% LB or 1 Hero Drink (item).",
                '- Skills gain you EXP proportional to user and target levels (0 EXP when consuming HP).',
                f"- Buff and debuff skills last for {self.skillduration} battles.",
                '- Duration is not consumed when you are attacked by other players.',
            )),(
            'Commands', (
                '- Type `=char skill` to find list of available skills.',
                '- Type `=char skill (skill name)` (e.g. `=char skill ruin`) to cast on yourself.',
                '- Type `=char hpskill (skill name)` (e.g. `=char hpskill faith`) to consume hp.',
                '- Type `=char lbskill (skill name)` (e.g. `=char lbskill cure`) to consume lb.',
                '- Type `=char heroskill (skill name)` (e.g. `=char lbskill cure`) to consume item Hero Drink.',
                '- Type `=char skill (skill name) | (user ping)` (e.g. `=char heroskill protect | @Caelum`) to cast on others.',
            )),(
            'Healing Skills', (
                '- Healing amount is scaled with your max HP.',
                '- You cannot use healing skills with HP.',
                '- You can revive a target only if you can fully heal the target.',
                '- To revive with AP: Type `=char revive (healing skill name) | (user ping)` (e.g. `=char revive cure | @Caelum`).',
                '- Otherwise the commands remain the same.',
            )),(
            'Auto LB Skill', (
                '- You can automatically consume LB gauge when full to cast a skill on yourself during battle.',
                '- It is activated when your LB gauge is full and (unless healing) no active buff or debuff',
                '- Note that auto item will activate before auto lb.',
                '- Type `=char autolbskill (skill name)` (e.g. `=char autolbskill brave`).',
                '- Type `=char autolbskill off` to turn off.',
            ))
        )
        self.manual['item'] = ((
            'Description', (
                'Items are consumables you obtain from raid drops or gacha.',
                'Check your inventory by `=char inv` or `=char inventory`.',
                'Please remember to claim your daily free gacha by `=char daily`.',
                'Note: AP% recovery caps at Max AP of 100.',
            )),(
            'Commands', (
                '- Type `=char inv` to check your inventory.'
                '- Type `=char item` to find list of available items.',
                '- Type `=char item (item name)` (e.g. `=char item elixir`) to use item.',
                '- Type `=char item (item name) | (user name)` (e.g. `=char item ether | @Caelum`) to use item on another user.',
                '- Type `=char item (number) (item name)` (e.g. `=char item 10 ether`) to use a number of items at once.',
            )),(
            'Auto Item', (
                '- You can set item to be automatically consumed before each battle when your HP is low.'
                '- Type `=char autoitem (item name)` (e.g. `=char autoitem potion`) to set item.',
                '- Type `=char autoitem (number)` (e.g. `=char autoitem 70`) to adjust HP% threshold.',
                '- Type `=char autoitem off` to turn off.',
            )),(
            'Gacha', (
                f"- Each gacha costs {self.gachacost} Gil.",
                '- Type `=char daily` for free 10 gachas daily (+ bonus 10 Ethers and 1 Elixir).',
                '- Type `=char gacha` to gacha 10 times.',
                '- Type `=char gacha (number)` (e.g. `=char gacha 7`) to gacha a number of times.',
                '- Type `=char rate` to check gacha rate.',
            ))
        )
        self.manual['raid'] = ((
            'Description', (
                'Raids are bosses shared across all users.',
                'Raids will counter you every time you attack.',
                'Check out `=charhelp battle` for battle mechanics.'
            )),(
            'Commands', (
                '- Type `=char raid` to find list of available raids and their levels.',
                '- Type `=char raid (raid name)` (e.g. `=char raid ifrit`) to check information of the raid.',
                '- Type `=char raid attack (raid name)` (e.g. `=char raid attack siren`) to attack the raid.',
                f"- Type `=char raid attack (number) (raid name)` (e.g. `=char raid attack 10 siren`) to attack multiple times (up to {self.attackcap}).",
                '- Type `=char rate` to check drop rates.',
            )),(
            'Rewards', (
                '- You gain EXP proportional to raid level and damage dealt.',
                '- If you deal the killing blow, you gain extra EXP and pick up item drops.',
                '- Type `=char rate` to check drop rate.',
            )),(
            'Levels', (
                '- Raids level up and revive with full HP when you defeat them.',
                '- Raids will loop back to initial levels when they hit certain levels.',
                f"- Group 1 levels will loop between {self.raidcap2 + 1} and {self.raidcap}.",
                f"- Group 2 levels will loop between 0 and {self.raidcap2}.",
            )
            )
        )
        manual_commands = '\n'.join([f"`=charhelp {k}`" for k in self.manual.keys()])
        self.helpintro = (
            'Engelbert (beta v2) is an experimental project of Discord bot tamagotchi '
            '(digital pet / avatar / character). It is under constant development so things '
            'may be subject to change. Have to see if free hosting service can '
            'handle the frequency of data update too... Feel free to drop some feedback!\n'
            '- Type `=char changelog` for recent changes.\n'
            '- Type `=char futureplan` for tentative future plans.\n'
            '- For more in-depth info of the following, try:\n' +
            manual_commands
        )
        self.futureplan = (
            'Subject to change and feasibility. Cannot say when they will be done... In order of priority:',
            '- EX Base: trade Dark Matters for EX Base and spend Dark Matters to upgrade.',
            '- Esper: trade Auracites for an esper for passive stat bonus. Not sure whether to make them upgradeable yet.',
            '- Trial: spend AP to spawn individual trial, beat them for rewards. Planning to have more complicated battle mechanics than raid.'
        )
        self.changelog = (
            ('18th February 2021', (
                '- Tried again to make help commands more readable...',
                '- Buffs now take effect when you are attacked by other players, but duration is not consumed.',
                '- Attacking other players now gets you EXP regardless of missing.',
                '- Type `=char heroskill` to cast skills with Hero Drinks directly.',
                '- Healing skills are no longer possible with HP cost.',
                '- In duels if both parties survive, now the one that dealt more damage is the winner.',
                '- Note: fixed some bugs and optimized a bit of battle coding, please let me know if anything unusual.',
                '- `=char futureplan` to check what is coming up.'
            )),
            ('17th February 2021', (
                'Raids now auto loop between certain levels. (`=charhelp raid`)',
                'Compared to previous adjustment, raids of level over 80 have their starting HP increased, HP growth and drop rate nerfed.',
                'You can now consume multiple items at once and consume Hero Drinks for EXP directly (`=charhelp item`)',
                'You can now check gacha or raid drop rate with `=char rate`.'
            )),
            ('15th February 2021', (
                'Items. Type `=charhelp item` for details.',
                'Past raid kills are rewarded with raid drops retroactively.',
                'Update: Due to critical balance error, some hours are rolled back with lower AP recovery potential.',
                'Beginners now get 10 Ethers to start.',
                'Free daily now gives 10 Ethers and 1 Elixir.',
                'Ramuh and Aigaion DEX buffed.',
                'Raids of level over 80 have their HP increased.'
            )),
            ('14th February 2021', (
                'Auto LB skill. Type `=char autolbskill (skill name)` to auto cast LB.',
                'Optimization. Should be faster in overall but might have sync issues. (Please report if anything wrong.)',
                'Main job change cooldown shortened to 12 hours but base change cooldown still remains 24 hours',
                'All ongoing base and job cooldowns are reset for the change.'
            )),
            ('13th February 2021', (
                'New bases. Find the list at `=char base`.',
                'Base default jobs redistributed (do not affect existing users).',
                'Base stats redistributed. Check with `=char base (base name)`.',
                'Sylph DEX and AGI reduced but DEF and SPR increased slightly.'
                'New jobs. Overall growth rate slightly adjusted. `=char job`',
                'Shortened skill commands. Check `=charhelp skill`.',
            )),
            ('12th February 2021', (
                'Overall stats increased slightly (including raids).',
                'Help and base commands overhauled.',
                'LB gauge - attack to charge, can be consumed for a free skill.',
                'Gil - consume AP to accumulate gil, in preparation of new function in future.',
                'You can now use HP to cast skills on yourself, except healing.',
                'All skills cast with HP no longer get you EXP.',
                'New skills. `=char skill`',
                'Potency of Protect and Shell increased. Skills now last for 5 battles.',
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
    def sheetsync(self):
        # sync local data into online sheet
        df = self.dfdict['User'].copy()
        df.index = pd.Index([self.indextransform(a) for a in df.index.tolist()], name='User')
        set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
        if self.logsync:
            set_with_dataframe(self.spreadsheet.worksheet('Log'), self.dfdict['Log'], include_index=False)
            self.logsync = 0
        if self.raidsync:
            set_with_dataframe(self.spreadsheet.worksheet('Raid'), self.dfdict['Raid'], include_index=True)
            self.raidsync = 0
        self.syncpend = 0
    def new_log(self, event,timestamp):
        # write a new log
        new_log = {
            'Event': event,
            'Timestamp': timestamp
        }
        new_row = (event, timestamp)
        self.spreadsheet.worksheet('Log').append_row(new_row)
        self.dfdict['Log'] = self.dfdict['Log'].append(new_log, ignore_index=True)
    def find_index(self, query, dfname):
        # auxiliary function to find index of a certain name
        if dfname == 'Item':
            df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item']
            indices = df['Skill']
            indexer = lambda x: x['Skill']
        else:
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
    def calcstats(self, userid, usertype='User', moddict=None, stat=None):
        if usertype == 'User':
            # calculate stats given user id
            userdict = dict()
            userdict['Level'] = self.calclevel(self.dfdict['User'].loc[userid, 'EXP'])
            if stat == 'ALL':
                statlist = self.statlist
            elif stat == None:
                statlist = self.statlist2
            else:
                statlist = [stat]
            for statname in statlist:
                userdict[statname] = self.dfdict['Base'].loc[self.dfdict['User'].loc[userid, 'Base'], statname]
            level_tup = (
                ('Main', userdict['Level'] + 1),
                ('Sub1', userdict['Level'] // 2 + 1),
                ('Sub2', (userdict['Level'] + 1) // 2)
            )
            for job_col, job_level in level_tup:
                job_id = self.dfdict['User'].loc[userid, job_col]
                for statname in statlist:
                    userdict[statname] += self.dfdict['Job'].loc[job_id, statname] * job_level
            if moddict != None:
                for k, v in moddict.items():
                    userdict[k] = int(round(userdict[k] * v))
            return userdict
        elif usertype == 'Raid':
            # calculate raid stats given raid name
            raid = userid
            raiddict = dict()
            base = self.dfdict['Raid'].loc[raid, 'Base']
            jobid = self.dfdict['Base'].loc[base, 'Main']
            jobrow = self.dfdict['Job'].loc[jobid]
            if stat == None or stat == 'ALL':
                for statname in self.statlist2:
                    raiddict[statname] = self.dfdict['Base'].loc[base, statname] + jobrow[statname] * (self.dfdict['Raid'].loc[raid, 'Level'] + 1)
            if stat == 'HP' or stat == 'ALL':
                raiddict['HP'] = self.dfdict['Base'].loc[base, 'HP'] + jobrow['HP'] * (self.dfdict['Raid'].loc[raid, 'Level'] + 1)
                if self.dfdict['Raid'].loc[raid, 'Level'] > self.raidcap2:
                    raiddict['HP'] = raiddict['HP'] * 2
                    raiddict['HP'] += jobrow['HP'] * (self.dfdict['Raid'].loc[raid, 'Level'] - self.raidcap2)
            if moddict != None:
                for k, v in moddict.items():
                    raiddict[statname] = int(round(raiddict[statname] * v))
            return raiddict
    def calcdamage(self, attacker, defender, a_skilltup=None, d_skilltup=None, counter=0, raid=0):
        # calculate damage given attacker and defender
        # skill check
        skilltuplist = []
        if a_skilltup != None:
            if self.dfdict['Skill'].loc[a_skilltup[0], 'Stat'] == 'COMBO':
                skilltuplist += [
                    (a, 'Main', 0) for a in self.dfdict['Skill'].loc[a_skilltup[0], 'Main'].split('/')
                ] + [
                    (a, 'Sub', 0) for a in self.dfdict['Skill'].loc[a_skilltup[0], 'Sub'].split('/')
                ]
            else:
                skilltuplist += [(*a_skilltup, 0)]
        if d_skilltup != None:
            if self.dfdict['Skill'].loc[d_skilltup[0], 'Stat'] == 'COMBO':
                skilltuplist += [
                    (a, 'Main', 1) for a in self.dfdict['Skill'].loc[d_skilltup[0], 'Main'].split('/')
                ] + [
                    (a, 'Sub', 1) for a in self.dfdict['Skill'].loc[d_skilltup[0], 'Sub'].split('/')
                ]
            else:
                skilltuplist += [(*d_skilltup, 1)]
        # stat modifier dict
        a_moddict = {stat: 1 for stat in self.statlist2}
        d_moddict = {stat: 1 for stat in self.statlist2}
        for skillid, skillpotency, skillside in skilltuplist:
            skillrow = self.dfdict['Skill'].loc[skillid]
            if skillside + skillrow['Ally'] == 1:
                a_moddict[skillrow['Stat']] = a_moddict[skillrow['Stat']] * skillrow[skillpotency]
            else:
                d_moddict[skillrow['Stat']] = d_moddict[skillrow['Stat']] * skillrow[skillpotency]
        # get their status sheets
        attackdict = self.calcstats(attacker, moddict=a_moddict)
        if raid == 1:
            defenddict = self.calcstats(defender, usertype='Raid', moddict=d_moddict)
        else:
            defenddict = self.calcstats(defender, moddict=d_moddict)
        # pick higher potential damage
        damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
        hitrate = self.calchitrate(attackdict['DEX'] - defenddict['AGI'])
        if counter:
            counter_damage = max(defenddict['ATK'] - attackdict['DEF'], defenddict['MAG'] - attackdict['SPR'], 0)
            counter_hitrate = self.calchitrate(defenddict['DEX'] - attackdict['AGI'])
            return damage, hitrate, counter_damage, counter_hitrate
        else:
            return damage, hitrate
    def userconsumeduration(self, user):
        # consume skill duration
        if self.dfdict['User'].loc[user, 'A_Skill'] != '':
            new_duration = self.dfdict['User'].loc[user, 'A_Duration'] - 1
            if new_duration == 0:
                self.dfdict['User'].loc[user, 'A_Skill'] = ''
                self.dfdict['User'].loc[user, 'A_Potency'] = ''
                self.dfdict['User'].loc[user, 'A_Duration'] = ''
            else:
                self.dfdict['User'].loc[user, 'A_Duration'] = new_duration
    def userattack(self, attacker, defender, zero_attack=0):
        # perform an attack between users
        if self.dfdict['User'].loc[attacker, 'A_Skill'] != '':
            a_skilltup = (self.dfdict['User'].loc[attacker, 'A_Skill'], self.dfdict['User'].loc[attacker, 'A_Potency'])
        else:
            a_skilltup = None
        if self.dfdict['User'].loc[defender, 'A_Skill'] != '':
            d_skilltup = (self.dfdict['User'].loc[defender, 'A_Skill'], self.dfdict['User'].loc[defender, 'A_Potency'])
        else:
            d_skilltup = None
        damage, hitrate = self.calcdamage(attacker, defender, a_skilltup, d_skilltup)
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
            # use lb
            lb_use = 0
            if self.dfdict['User'].loc[attacker, 'LB_Auto'] != 'off' and self.dfdict['User'].loc[attacker, 'LB'] == 100:
                skillrow = self.dfdict['Skill'].loc[self.dfdict['User'].loc[attacker, 'LB_Auto']]
                if self.dfdict['User'].loc[attacker, 'A_Skill'] == '' or self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                    lb_use = self.infoskill(attacker, skillrow.name, consumelb=1)
                    if not self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                        # recalculate damage and hit rate
                        a_skilltup = (self.dfdict['User'].loc[attacker, 'A_Skill'], self.dfdict['User'].loc[attacker, 'A_Potency'])
                        damage, hitrate = self.calcdamage(attacker, defender, a_skilltup, d_skilltup)
            self.userconsumeduration(attacker)
            # consume AP
            self.dfdict['User'].loc[attacker, 'AP'] = int(self.dfdict['User'].loc[attacker, 'AP'] - self.attack_apcost)
            # calculate critical or hit rate
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            # EXP gain
            a_level = self.calclevel(self.dfdict['User'].loc[attacker, 'EXP'])
            d_level = self.calclevel(self.dfdict['User'].loc[defender, 'EXP'])
            exp_gain = 15 + damage * hit // 30 + d_level * 2
            # bonus EXP for killing
            kill = self.userdamage(defender, damage * hit)
            if kill:
                exp_gain += d_level * 2
            self.dfdict['User'].loc[attacker, 'EXP'] = self.dfdict['User'].loc[attacker, 'EXP'] + exp_gain
            # defender EXP regardless of hit
            defender_exp_gain = 10 + damage * hit // 45 + a_level * 2
            self.dfdict['User'].loc[defender, 'EXP'] = self.dfdict['User'].loc[defender, 'EXP'] + defender_exp_gain
            # LB gain
            lb_gain = ((d_level - 1) // a_level + 1) * 10
            lb_gain = min(100 - self.dfdict['User'].loc[attacker, 'LB'], lb_gain)
            self.dfdict['User'].loc[attacker, 'LB'] = self.dfdict['User'].loc[attacker, 'LB'] + lb_gain
            # defender LB gain
            defender_lb_gain = ((a_level - 1) // d_level + 1) * 10
            defender_lb_gain = min(100 - self.dfdict['User'].loc[defender, 'LB'], defender_lb_gain)
            self.dfdict['User'].loc[defender, 'LB'] = self.dfdict['User'].loc[defender, 'LB'] + defender_lb_gain
            # Gil gain
            self.dfdict['User'].loc[attacker, 'Gil'] = self.dfdict['User'].loc[attacker, 'Gil'] + self.attack_apcost
            return (1, damage, hitrate, hit, kill, exp_gain, defender_exp_gain, lb_use)
    def userdamage(self, defender, damage):
        # function for a user to take damage
        self.dfdict['User'].loc[defender, 'HP'] = int(max(self.dfdict['User'].loc[defender, 'HP'] - damage, 0))
        if self.dfdict['User'].loc[defender, 'HP'] == 0:
            self.dfdict['User'].loc[defender, 'TS_Dead'] = datetime.strftime(datetime.now(), mydtformat)
            return 1
        else:
            return 0
    def userregenall(self, now=None):
        # hourly automatic regen for all
        if now != None:
            self.new_log('hourlyregen', datetime.strftime(now, mydtformat))
        for index, row in self.dfdict['User'].iterrows():
            u_level = self.calclevel(row['EXP'])
            u_hp = self.calcstats(index, stat='HP')['HP']
            u_ap = self.calcstats(index, stat='AP')['AP']
            if row['AP'] < u_ap: # if AP is not full
                new_ap = min(row['AP'] + self.apregen, u_ap)
                self.dfdict['User'].loc[index, 'AP'] = new_ap
                hp_recovery = int(u_hp * self.hpregen)
            else: # doubles HP regen if AP is full
                hp_recovery = int(u_hp * self.hpregen * 2)
            if 0 < row['HP'] < u_hp:
                new_hp = min(row['HP'] + hp_recovery, u_hp)
                self.dfdict['User'].loc[index, 'HP'] = new_hp
            # gains EXP passively too
            self.dfdict['User'].loc[index, 'EXP'] = self.dfdict['User'].loc[index, 'EXP'] + 20 + u_level
        self.syncpend = 1
    def userrevive(self, userid):
        # revive dead user and log it
        self.dfdict['User'].loc[userid, 'HP'] = self.calcstats(userid, stat='HP')['HP']
        self.dfdict['User'].loc[userid, 'TS_Dead'] = ''
        self.syncpend = 1
    def userjobchange(self, user, job, job_col='Main'):
        # change user main or sub job
        dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
        jobid = dfjob[dfjob['Job'] == job].tail(1).index.tolist()[0]
        if job_col == 'Main':
            if self.dfdict['User'].loc[user.id, 'TS_Job'] != '':
                thres = datetime.strptime(self.dfdict['User'].loc[user.id, 'TS_Job'], mydtformat) + timedelta(hours=self.cdjob)
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
            self.dfdict['User'].loc[user.id, 'TS_Job'] = datetime.strftime(datetime.now(), mydtformat)
            return (1, self.dfdict['Job'].loc[sub1jobid, 'Job'], self.dfdict['Job'].loc[sub2jobid, 'Job'])
        else:
            for jcol in ('Main', 'Sub1', 'Sub2'):
                if self.dfdict['User'].loc[user.id, jcol] == jobid:
                    return (0, jcol)
            self.dfdict['User'].loc[user.id, job_col] = jobid
            return (1,)
    def userbase(self, user, base):
        # change base or start a user
        baserow = self.dfdict['Base'].loc[base]
        if user.id in self.dfdict['User'].index:
            thres = datetime.strptime(self.dfdict['User'].loc[user.id, 'TS_Base'], mydtformat) + timedelta(hours=self.cdbase)
            now = datetime.now()
            if now < thres:
                remaining = thres - now
                return f"{remaining.seconds // 3600} hours {remaining.seconds % 3600 // 60} minutes left before {user.name} can change base."
            if self.dfdict['User'].loc[user.id, 'Base'] == base:
                return f"{user.name}, it is your current base."
            else:
                self.dfdict['User'].loc[user.id, 'Base'] = base
                self.dfdict['User'].loc[user.id, 'TS_Base'] = datetime.strftime(datetime.now(), mydtformat)
                replystr = f"{user.name} base now changed to {base}."
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
                'Gil': 0,
                'TS_Base': datetime.strftime(datetime.now(), mydtformat),
                'I_Thres': 50,
                'I_Auto': 'off',
                'LB_Auto': 'off',
                'i1': 0,
                'i2': 0,
                'i3': 0,
                'i4': 10,
                'i5': 0,
                'i6': 0,
                'i7': 0
            }
            userrow = pd.Series(data=new_user.values(), index=new_user.keys(), name=user.id)
            self.dfdict['User'] = self.dfdict['User'].append(userrow).fillna('')
            replystr = f"{user.name} registered with {base}!"
        self.syncpend = 1
        return replystr
    def raiddamage(self, raid, damage):
        # function for a raid to take damage
        self.dfdict['Raid'].loc[raid, 'HP'] = int(max(self.dfdict['Raid'].loc[raid, 'HP'] - damage, 0))
        # if kill
        if self.dfdict['Raid'].loc[raid, 'HP'] == 0:
            # item drop
            drop_level = 0
            for k in self.drop_rate.keys():
                if isinstance(k, str):
                    continue
                if k > self.dfdict['Raid'].loc[raid, 'Level']:
                    break
                else:
                    drop_level = k
            drop_dict = self.drop_rate[drop_level]
            item1 = random.choices(list(drop_dict.keys()), weights=list(drop_dict.values()))[0]
            if str(drop_level) in self.drop_rate.keys():
                drop_dict = self.drop_rate[str(drop_level)]
                item_drop = (random.choices(list(drop_dict.keys()), weights=list(drop_dict.values()))[0], item1)
            else:
                item_drop = (item1,)
            # level up the raid and fully recovers
            if raid == self.dfdict['Raid'].loc[raid, 'Base']:
                if self.dfdict['Raid'].loc[raid, 'Level'] < self.raidcap:
                    self.dfdict['Raid'].loc[raid, 'Level'] = self.dfdict['Raid'].loc[raid, 'Level'] + 1
                else:
                    self.dfdict['Raid'].loc[raid, 'Level'] = self.raidcap2 + 1
            else:
                if self.dfdict['Raid'].loc[raid, 'Level'] < self.raidcap2:
                    self.dfdict['Raid'].loc[raid, 'Level'] = self.dfdict['Raid'].loc[raid, 'Level'] + 1
                else:
                    self.dfdict['Raid'].loc[raid, 'Level'] = 0
            self.dfdict['Raid'].loc[raid, 'HP'] = self.calcstats(raid, usertype='Raid', stat='HP')['HP']
            return item_drop
        else:
            return 0
    def raidattack(self, user, raid, zero_attack=0):
        # perform an attack between an user and a raid
        if self.dfdict['User'].loc[user, 'A_Skill'] != '':
            a_skilltup = (self.dfdict['User'].loc[user, 'A_Skill'], self.dfdict['User'].loc[user, 'A_Potency'])
        else:
            a_skilltup = None
        damage, hitrate, raid_damage, raid_hitrate = self.calcdamage(user, raid, a_skilltup=a_skilltup, counter=1, raid=1)
        # check attack criteria
        if self.dfdict['User'].loc[user, 'HP'] == 0:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'You are dead!')
        elif self.dfdict['User'].loc[user, 'AP'] < self.attack_apcost:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'Not enough AP!')
        elif zero_attack:
            return (0, damage, hitrate, raid_damage, raid_hitrate)
        else:
            # use item
            item_use = 0
            u_hp = self.calcstats(user, stat='HP')['HP']
            hp_perc = self.dfdict['User'].loc[user, 'HP'] / u_hp
            if self.dfdict['User'].loc[user, 'I_Auto'] != 'off' and hp_perc < self.dfdict['User'].loc[user, 'I_Thres'] / 100:
                skillrow = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user, 'I_Auto']]
                while self.dfdict['User'].loc[user, self.dfdict['User'].loc[user, 'I_Auto']] > 0:
                    item_use += self.infoitem(user, skillrow.name)
                    if self.dfdict['User'].loc[user, 'HP'] / u_hp >= self.dfdict['User'].loc[user, 'I_Thres'] / 100:
                        break
            # use lb
            lb_use = 0
            if self.dfdict['User'].loc[user, 'LB_Auto'] != 'off' and self.dfdict['User'].loc[user, 'LB'] == 100:
                skillrow = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user, 'LB_Auto']]
                if self.dfdict['User'].loc[user, 'A_Skill'] == '' or self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                    lb_use = self.infoskill(user, skillrow.name, consumelb=1)
                    if not self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                        # recalculate damage and hit rate
                        a_skilltup = (self.dfdict['User'].loc[user, 'A_Skill'], self.dfdict['User'].loc[user, 'A_Potency'])
                        damage, hitrate, raid_damage, raid_hitrate = self.calcdamage(user, raid, a_skilltup=a_skilltup, counter=1, raid=1)
            self.userconsumeduration(user)
            # consume AP
            self.dfdict['User'].loc[user, 'AP'] = int(self.dfdict['User'].loc[user, 'AP'] - self.attack_apcost)
            # LB gain
            u_level = self.calclevel(self.dfdict['User'].loc[user, 'EXP'])
            r_level = self.dfdict['Raid'].loc[raid, 'Level']
            if r_level > u_level:
                lb_gain = 20
            else:
                lb_gain = 10
            lb_gain = min(100 - self.dfdict['User'].loc[user, 'LB'], lb_gain)
            self.dfdict['User'].loc[user, 'LB'] = self.dfdict['User'].loc[user, 'LB'] + lb_gain
            # check critical or hit
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            # EXP gain
            exp_gain = 30 + (damage * hit) // 30 + r_level * 3
            # Bonus EXP for killing
            kill = self.raiddamage(raid, damage * hit)
            if kill != 0:
                exp_gain += r_level * 3
                # Item drop
                for itemid in kill:
                    self.dfdict['User'].loc[user, itemid] = self.dfdict['User'].loc[user, itemid] + 1
            self.dfdict['User'].loc[user, 'EXP'] = self.dfdict['User'].loc[user, 'EXP'] + exp_gain
            # Gil gain
            self.dfdict['User'].loc[user, 'Gil'] = self.dfdict['User'].loc[user, 'Gil'] + self.attack_apcost
            # raid counter attack
            if raid_hitrate > 1:
                raid_hit = 1 + ((raid_hitrate - 1) > random.random())
            else:
                raid_hit = raid_hitrate > random.random()
            raid_kill = self.userdamage(user, raid_damage * raid_hit)
            return (1, damage, hitrate, raid_damage, raid_hitrate, hit, kill, raid_hit, raid_kill, exp_gain, lb_use, item_use)
    ############################
    # discord embed generators #
    ############################
    def helpmanual(self, kw=''):
        # generate help manual
        embed = discord.Embed()
        kw = kw.lower().rstrip('s').replace('char', 'character')
        if kw in self.manual.keys():
            embed.title = f"{kw.title()} Help"
            for field_name, field_value in self.manual[kw]:
                if field_name == 'Description':
                    embed.description = '\n'.join(field_value)
                else:
                    embed.add_field(name=field_name, value='\n'.join(field_value), inline=False)
        elif kw in ('changelog', 'version'):
            return self.infochangelog(1)
        elif kw in ('rate', 'drop', 'gacha'):
            return self.ratemanual()
        else:
            embed.title = 'Engelbert Help'
            embed.description = self.helpintro
        embed.set_thumbnail(url = 'https://caelum.s-ul.eu/peon3odf.png')
        return embed
    def ratemanual(self):
        embed = discord.Embed()
        # gacha
        field_list = []
        embed.description = 'Bracketed rates in raid drop rates are on separate slot. `=charhelp item` or `=charhelp raid` for other info.'
        df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item']
        for index, row in df.iterrows():
            field_list.append(f"**{row['Skill']}**: {self.gacha_rate[index]}%")
        embed.add_field(name='Gacha', value = '\n'.join(field_list))
        # raid drop
        previous_level = -1
        drop_list = dict()
        for k, v in self.drop_rate.items():
            if isinstance(k, str):
                continue
            if previous_level != -1:
                field_name = f"Raid Level {previous_level}-{k - 1}"
                field_list = [f"**{df.loc[itemid, 'Skill']}**: {ratestr}" for itemid, ratestr in drop_list.items()]
                embed.add_field(name = field_name, value = '\n'.join(field_list))
                drop_list = dict()
            for itemid in df.index:
                if itemid in v.keys():
                    drop_list[itemid] = f"{v[itemid]}%"
                if str(k) in self.drop_rate.keys():
                    if itemid in self.drop_rate[str(k)].keys():
                        if itemid in drop_list.keys():
                            drop_list[itemid] = drop_list[itemid] + f" ({self.drop_rate[str(k)][itemid]}%)"
                        else:
                            drop_list[itemid] = f"({self.drop_rate[str(k)][itemid]}%)"
            previous_level = k
        field_name = f"Raid Level {previous_level}+"
        field_list = [f"**{df.loc[itemid, 'Skill']}**: {ratestr}" for itemid, ratestr in drop_list.items()]
        embed.add_field(name = field_name, value = '\n'.join(field_list))
        embed.set_thumbnail(url = 'https://caelum.s-ul.eu/peon3odf.png')
        return embed
    def infofutureplan(self):
        # generate future plan
        embed = discord.Embed()
        embed.title = 'Engelbert Future Plans'
        embed.description = '\n'.join(self.futureplan)
        embed.set_thumbnail(url = 'https://caelum.s-ul.eu/peon3odf.png')
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
        embed.description = '`=charhelp base` for more info.'
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
        embed.description = '`=charhelp raid` for more info.'
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
        embed.description = '`=charhelp job` for more info.'
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
        embed.description = '`=charhelp skill` for more info.'
        df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == '']
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
    def listitem(self):
        # generate embed of list of available items
        embed = discord.Embed()
        embed.title = 'List of Items'
        embed.description = '`=charhelp item` for more info. Note: AP% recovery caps at Max AP of 100.'
        df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item']
        skill_list = []
        skill_count = 0
        for _, row in df.iterrows():
            if row['Stat'] == 'EXP':
                skill_list.append(f"**{row['Skill']}**\n - Valuable rare item for future use.")
            else:
                skill_list.append(f"**{row['Skill']}**\n - Restores {row['Main'] * 100:.0f}% {row['Stat']}.")
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
            self.syncpend = 1
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
        userdict = self.calcstats(row.name, stat='ALL')
        desc_list.append(f"Base: {row['Base']}")
        if userdict['Level'] == self.levelcap:
            desc_list.append(f"Level: {userdict['Level']} (MAX)")
        else:
            desc_list.append(f"Level: {userdict['Level']}")
            desc_list.append(f"*Next Level: {self.levelexp[userdict['Level'] + 1] - row['EXP']} EXP*")
        desc_list.append(f"HP: {row['HP']}/{userdict['HP']}")
        desc_list.append(f"AP: {row['AP']}/{userdict['AP']}")
        if row['LB'] == 100:
            desc_list.append(f"LB: **MAX**")
        else:
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
        # auto setting
        field_list = []
        if row['LB_Auto'] != 'off':
            field_list.append(f"LB Skill: {self.dfdict['Skill'].loc[row['LB_Auto'], 'Skill']}")
        else:
            field_list.append(f"LB Skill: *off*")
        if row['I_Auto'] != 'off':
            field_list.append(f"Item: {self.dfdict['Skill'].loc[row['I_Auto'], 'Skill']} ({row[row['I_Auto']]})")
        else:
            field_list.append(f"Item: *off*")
        field_list.append(f"HP Threshold: {row['I_Thres']}%")
        embed.add_field(name='Auto Setting', value='\n'.join(field_list))
        # show revival timer if dead
        if row['HP'] == 0:
            thres = datetime.strptime(row['TS_Dead'], mydtformat) + timedelta(hours=engel.revivehours)
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
    def infoinventory(self, user):
        # generate inventory embed of specific user
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user.id]
        embed.title = user.name + ' Inventory'
        embed.description = f"Gil: {userrow['Gil']}"
        df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item']
        skill_list = []
        skill_count = 0
        for index, row in df.iterrows():
            skill_list.append(f"{row['Skill']} - {userrow[index]}")
            skill_count += 1
            if skill_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
                skill_list = []
        if len(skill_list) > 0:
            embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
        # decoration
        thumbnail_url = self.dfdict['Base'].loc[userrow['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed_colour = self.dfdict['Base'].loc[userrow['Base'], 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    def inforaid(self, raid):
        # generate info embed of specific raid
        embed = discord.Embed()
        row = self.dfdict['Raid'].loc[raid]
        embed.title = raid
        desc_list = []
        raiddict = self.calcstats(row.name, usertype='Raid', stat='ALL')
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
        attackhp = self.calcstats(attacker.id, stat='HP')['HP']
        attackhp_init = attackhp
        defendhp = self.calcstats(defender.id, stat='HP')['HP']
        defendhp_init = defendhp
        # pick higher potential damage
        damage, hitrate, counter_damage, counter_hitrate = self.calcdamage(attacker.id, defender.id, counter=1)
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
        if attackhp == 0 and defendhp > 0:
            field_list.append(f"{defender.name} won!")
        elif defendhp == 0 and attackhp > 0:
            field_list.append(f"{attacker.name} won!")
        elif attackhp == defendhp == 0:
            field_list.append('It is a draw!')
        else:
            attackdmg = defendhp_init - defendhp
            defenddmg = attackhp_init - attackhp
            if attackdmg > defenddmg:
                field_list.append(f"{attacker.name} won!")
            elif defenddmg > attackdmg:
                field_list.append(f"{defender.name} won!")
            else:
                field_list.append('It is a draw!')
        embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        defender_base = self.dfdict['User'].loc[defender.id, 'Base']
        embed_colour = self.dfdict['Base'].loc[defender_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        return embed
    def infogacha(self, user, num_times=10, free=0):
        # generate result embed of a gacha session
        embed = discord.Embed()
        result_sum = {k: 0 for k in self.gacha_rate.keys()}
        desc_list = []
        if free: # daily free gacha
            embed.title = f"{user.name} Free Daily Gacha"
            if self.dfdict['User'].loc[user.id, 'TS_Gacha'] != '':
                thres = datetime.strptime(self.dfdict['User'].loc[user.id, 'TS_Gacha'], mydtformat)
                now = datetime.now()
                nowstr = datetime.strftime(now, mydtformat)
                todaystr = nowstr.split()[0] + ' 0:00'
                today = datetime.strptime(todaystr, mydtformat)
                if today < thres:
                    remaining = today + timedelta(days=1) - now
                    embed.description = f"{remaining.seconds // 3600} hours {remaining.seconds % 3600 // 60} minutes left before you can do free daily gacha."
                    return embed
            num_times = 10
            gil_cost = 0
            result_sum['i4'] += 10
            result_sum['i5'] += 1
            desc_list.append('You claimed your free Ethers and Elixir.')
            self.dfdict['User'].loc[user.id, 'TS_Gacha'] = datetime.strftime(datetime.now(), mydtformat)
        else:
            embed.title = f"{user.name} Gacha"
            num_times = min(self.dfdict['User'].loc[user.id, 'Gil'] // self.gachacost, num_times)
            gil_cost = num_times * self.gachacost
            self.dfdict['User'].loc[user.id, 'Gil'] = self.dfdict['User'].loc[user.id, 'Gil'] - gil_cost
        for _ in range(num_times):
            choice = random.choices(list(self.gacha_rate.keys()), weights=list(self.gacha_rate.values()))[0]
            result_sum[choice] += 1
        desc_list.append(f"You spent {gil_cost} Gil to gacha {num_times} time(s).")
        for k, v in result_sum.items():
            if v > 0:
                self.dfdict['User'].loc[user.id, k] = self.dfdict['User'].loc[user.id, k] + v
                desc_list.append(f"You got {v} {self.dfdict['Skill'].loc[k, 'Skill']}(s).")
        desc_list.append(f"You have {self.dfdict['User'].loc[user.id, 'Gil']} Gil left.")
        self.syncpend = 1
        embed.description = '\n'.join(desc_list)
        return embed
    def infotrain(self, user, ap_consume=3, skill=None):
        # generate result embed of a training session
        embed = discord.Embed()
        embed.title = f"{user.name} Training"
        total_exp_gain = 0
        if skill == None:
            ap_consume = min(self.dfdict['User'].loc[user.id, 'AP'], ap_consume)
            self.dfdict['User'].loc[user.id, 'AP'] = self.dfdict['User'].loc[user.id, 'AP'] - ap_consume
            self.dfdict['User'].loc[user.id, 'Gil'] = self.dfdict['User'].loc[user.id, 'Gil'] + ap_consume
            for _ in range(ap_consume):
                exp_gain = 20 + self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) * 2
                total_exp_gain += exp_gain
                self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] + exp_gain # gains EXP
            if total_exp_gain > 0:
                self.syncpend = 1
            embed.description = f"You spent {ap_consume} AP and gained {total_exp_gain} EXP."
        else:
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            if 'LB' not in self.dfdict['Skill'].loc[skillid, 'Stat'].split('/'):
                embed.description = f"You can only train with items that restore LB."
                return embed
            ap_consume = min(self.dfdict['User'].loc[user.id, skillid], ap_consume)
            self.dfdict['User'].loc[user.id, skillid] = self.dfdict['User'].loc[user.id, skillid] - ap_consume
            for _ in range(ap_consume):
                exp_gain = 50 + self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) * 2
                total_exp_gain += exp_gain
                self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] + exp_gain # gains EXP
            if total_exp_gain > 0:
                self.syncpend = 1
            embed.description = f"You consumed {ap_consume} {skill}(s) and gained {total_exp_gain} EXP."
        return embed
    def infoautolb(self, user, skill):
        # generate result embed of setting auto lb
        userid = user.id
        if skill == 'off' and self.dfdict['User'].loc[user.id, 'LB_Auto'] != 'off':
            self.dfdict['User'].loc[user.id, 'LB_Auto'] = 'off'
            self.syncpend = 1
            return f"{user.name} auto LB is now turned off."
        else:
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            if self.dfdict['User'].loc[user.id, 'LB_Auto'] != skillid:
                self.dfdict['User'].loc[user.id, 'LB_Auto'] = skillid
                self.syncpend = 1
                return f"{user.name} auto LB is now set to {skill}."
        return f"This is {user.name} current setting."
    def infoautoitem(self, user, skill):
        # generate result embed of setting auto item
        userid = user.id
        if isinstance(skill, int):
            if self.dfdict['User'].loc[user.id, 'I_Thres'] != skill:
                if skill < 1 or skill > 99:
                    return f"Please set a number between 1-99."
                self.dfdict['User'].loc[user.id, 'I_Thres'] = skill
                self.syncpend = 1
                return f"{user.name} auto item HP threshold now set to {skill}%."
        elif skill == 'off' and self.dfdict['User'].loc[user.id, 'I_Auto'] != 'off':
            self.dfdict['User'].loc[user.id, 'I_Auto'] = 'off'
            self.syncpend = 1
            return f"{user.name} auto item is now turned off."
        else:
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            if 'HP' not in self.dfdict['Skill'].loc[skillid, 'Stat'].split('/'):
                return f"You must set an item that restores HP."
            if self.dfdict['User'].loc[user.id, 'I_Auto'] != skillid:
                self.dfdict['User'].loc[user.id, 'I_Auto'] = skillid
                self.syncpend = 1
                return f"{user.name} auto item is now set to {skill}."
        return f"This is {user.name} current setting."
    def infoitem(self, user, skill, num_times=1, target=None):
        # generate result embed of a item
        embed = discord.Embed()
        if isinstance(user, int):
            userid = user
            skillid = skill
        else:
            userid = user.id
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            embed.title = f"{user.name} - {skill}"
        userrow = self.dfdict['User'].loc[userid]
        skillrow = self.dfdict['Skill'].loc[skillid]
        desc_list = []
        if userrow[skillid] == 0:
            embed.description = f"You ran out of {skillrow['Skill']}."
            return embed
        num_times = min(userrow[skillid], num_times)
        # check target
        if target == None:
            if isinstance(user, int):
                targetid = userid
            else:
                target = user
                targetid = target.id
        else:
            targetid = target.id
        t_hp = self.calcstats(targetid, stat='HP')['HP']
        t_ap = self.calcstats(targetid, stat='AP')['AP']
        hp_recovery = 0
        hp_num_times = 0
        ap_recovery = 0
        ap_num_times = 0
        lb_recovery = 0
        lb_num_times = 0
        # num of times to be coded
        if 'HP' in skillrow['Stat'].split('/'):
            if self.dfdict['User'].loc[targetid, 'HP'] == 0:
                if skillrow['Main'] < 1:
                    embed.description = f"{skillrow['Skill']} is not potent enough to revive."
                    return embed
                hp_recovery = -1
            else:
                hp_recovery = int(t_hp * skillrow['Main'])
                hp_diff = t_hp - self.dfdict['User'].loc[targetid, 'HP']
                hp_num_times = min(math.ceil(hp_diff / hp_recovery), num_times)
                hp_recovery = min(hp_diff, hp_recovery * hp_num_times)
        if 'AP' in skillrow['Stat'].split('/'):
            ap_recovery = int(min(t_ap, 100) * skillrow['Main'])
            ap_diff = t_ap - self.dfdict['User'].loc[targetid, 'AP']
            ap_num_times = min(math.ceil(ap_diff / ap_recovery), num_times)
            ap_recovery = min(ap_diff, ap_recovery * ap_num_times)
        if 'LB' in skillrow['Stat'].split('/'):
            lb_recovery = int(100 * skillrow['Main'])
            lb_diff = 100 - self.dfdict['User'].loc[targetid, 'LB']
            lb_num_times = min(math.ceil(lb_diff / lb_recovery), num_times)
            lb_recovery = min(lb_diff, lb_recovery * lb_num_times)
        if hp_recovery == 0 and ap_recovery == 0 and lb_recovery == 0:
            embed.description = f"It will have no effect."
            return embed
        # carry out the effects
        num_times = max(hp_num_times, ap_num_times, lb_num_times)
        self.dfdict['User'].loc[userid, skillid] = self.dfdict['User'].loc[userid, skillid] - num_times
        if num_times > 1:
            desc_list.append(f"You used {num_times} {skill}s.")
        if hp_recovery == -1:
            self.userrevive(targetid)
            if isinstance(user, int):
                return 1
            else:
                desc_list.append(f"{target.name} revived.")
        elif hp_recovery > 0:
            self.dfdict['User'].loc[targetid, 'HP'] = self.dfdict['User'].loc[targetid, 'HP'] + hp_recovery
            if not isinstance(user, int):
                desc_list.append(f"{target.name} restored {hp_recovery} HP.")
        if ap_recovery > 0:
            self.dfdict['User'].loc[targetid, 'AP'] = self.dfdict['User'].loc[targetid, 'AP'] + ap_recovery
            if not isinstance(user, int):
                desc_list.append(f"{target.name} restored {ap_recovery} AP.")
        if lb_recovery > 0:
            self.dfdict['User'].loc[targetid, 'LB'] = self.dfdict['User'].loc[targetid, 'LB'] + lb_recovery
            if not isinstance(user, int):
                desc_list.append(f"{target.name} restored {lb_recovery}% LB.")
        if isinstance(user, int):
            return 1
        embed.description = '\n'.join(desc_list)
        field_list = []
        # end summary
        for statname in ('HP', 'AP'):
            field_list.append(f"{statname}: {self.dfdict['User'].loc[targetid, statname]}")
        if self.dfdict['User'].loc[targetid, 'LB'] == 100:
            field_list.append(f"LB: **MAX**")
        else:
            field_list.append(f"LB: {self.dfdict['User'].loc[targetid, 'LB']}%")
        embed.add_field(name = target.name, value = '\n'.join(field_list))
        embed.add_field(name = 'Quantity Left', value = str(self.dfdict['User'].loc[userid, skillid]))
        self.syncpend = 1
        return embed
    def infoskill(self, user, skill, target=None, consumehp=0, consumelb=0):
        # generate result embed of a skill
        embed = discord.Embed()
        if isinstance(user, int):
            userid = user
            skillid = skill
        else:
            userid = user.id
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            embed.title = f"{user.name} - {skill}"
        userrow = self.dfdict['User'].loc[userid]
        skillrow = self.dfdict['Skill'].loc[skillid]
        desc_list = []
        # healing with HP
        if consumehp == 1 and skillrow['Healing']:
            embed.description = 'You cannot consume HP for healing skills.'
            return embed
        # check if skill available and what potency
        if consumelb == 1 and userrow['LB'] < 100:
            embed.description = f'Your LB gauge is not full yet.'
            return embed
        elif consumelb == 2 and userrow['i3'] < 1:
            embed.description = f'Your ran out of Hero Drinks.'
            return embed
        if skillid == self.dfdict['Job'].loc[userrow['Main'], 'Skill']:
            potency = 'Main'
        else:
            potency = 'Sub'
        # check target
        if target == None:
            if isinstance(user, int):
                targetid = userid
            else:
                target = user
                targetid = target.id
        else:
            targetid = target.id
        if targetid != userid and not skillrow['Ally']:
            embed.description = f"{skill} cannot be casted on others."
            return embed
        u_hp = self.calcstats(userid, stat='HP')['HP']
        t_hp = self.calcstats(targetid, stat='HP')['HP']
        hpcost = math.ceil(u_hp * self.skill_hpcost)
        apcost = self.skill_apcost
        hprecovery = math.floor(u_hp * skillrow[potency])
        # no EXP gain if HP consume
        if consumehp == 1:
            exp_gain = 0
        else:
            exp_gain = self.calclevel(self.dfdict['User'].loc[userid, 'EXP']) + self.calclevel(self.dfdict['User'].loc[targetid, 'EXP'])
        revive = 0
        # check if is to revive
        if skillrow['Healing'] and self.dfdict['User'].loc[targetid, 'HP'] == 0:
            num_times = math.ceil(t_hp / hprecovery)
            if num_times > 1 and consumelb > 0:
                if isinstance(user, int):
                    return 0
                else:
                    embed.description = f"You are not strong enough to revive {target.name} with one cast."
                    return embed
            hprecovery = hprecovery * num_times
            hpcost = hpcost * num_times
            apcost = apcost * num_times
            exp_gain = exp_gain * num_times
            revive = 1
            desc_list = ['Target is dead!',
                f"If you do not mind paying {apcost} AP, type `=char skill {skillrow['Skill']} | target | revive`."
            ]
            embed.description = '\n'.join(desc_list)
            return embed
        # check if target HP is full
        if skillrow['Healing'] and self.dfdict['User'].loc[targetid, 'HP'] == t_hp:
            if isinstance(user, int):
                return 0
            else:
                embed.description = f"{target.name} HP is full."
                return embed
        # check HP or AP amount or criteria to consume
        if consumehp == 1:
            if userrow['HP'] <= hpcost:
                embed.description = f"You need at least {hpcost + 1} HP."
                return embed
            else:
                desc_list.append(f"You consumed {hpcost} HP.")
                self.dfdict['User'].loc[userid, 'HP'] = self.dfdict['User'].loc[userid, 'HP'] - hpcost
        elif consumelb == 1:
            self.dfdict['User'].loc[userid, 'LB'] = 0
            desc_list.append(f"You consumed LB gauge.")
        elif consumelb == 2:
            self.dfdict['User'].loc[userid, 'i3'] = self.dfdict['User'].loc[userid, 'i3'] - 1
            desc_list.append(f"You consumed a Hero Drink.")
        elif userrow['AP'] < apcost:
            embed.description = f"You need to have at least {apcost} AP."
            return embed
        else:
            self.dfdict['User'].loc[userid, 'AP'] = self.dfdict['User'].loc[userid, 'AP'] - apcost
            self.dfdict['User'].loc[userid, 'Gil'] = self.dfdict['User'].loc[userid, 'Gil'] + apcost
            desc_list.append(f"You consumed {apcost} AP.")
        # Actual skill execution
        self.dfdict['User'].loc[userid, 'EXP'] = self.dfdict['User'].loc[userid, 'EXP'] + exp_gain
        if skillrow['Healing']:
            if revive:
                self.userrevive(targetid)
                if not isinstance(user, int):
                    desc_list.append(f"You casted {skillrow['Skill']} {num_times} time(s) to revive {target.name}.")
            else:
                self.dfdict['User'].loc[targetid, 'HP'] = min(self.dfdict['User'].loc[targetid, 'HP'] + hprecovery, t_hp)
                if not isinstance(user, int):
                    desc_list.append(f"You casted {skillrow['Skill']} on {target.name}, healing {hprecovery} HP.")
        else:
            self.dfdict['User'].loc[targetid, 'A_Skill'] = skillid
            self.dfdict['User'].loc[targetid, 'A_Potency'] = potency
            self.dfdict['User'].loc[targetid, 'A_Duration'] = self.skillduration
            if userid != targetid and not isinstance(user, int):
                desc_list.append(f"You casted {skillrow['Skill']} on {target.name}.")
            else:
                desc_list.append(f"You casted {skillrow['Skill']}.")
        if exp_gain > 0:
            desc_list.append(f"You gained {exp_gain} EXP.")
        self.syncpend = 1
        if isinstance(user, int):
            return exp_gain
        else:
            embed.description = '\n'.join(desc_list)
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
        # basic attack info (simulation)
        desc_list = []
        desc_list.append(f"*You have {min(result_tup[2], 1) * 100:.0f}% of doing {result_tup[1]} damage.*")
        desc_list.append(f"*You have {max(result_tup[2] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        exp_gain_total = 0
        defender_exp_gain_total = 0
        attack_count = 0
        # actual battle log
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
                _, damage, hitrate, hit, kill, exp_gain, defender_exp_gain, lb_use = result_tup
                if lb_use > 0:
                    skill = self.dfdict['Skill'].loc[self.dfdict['User'].loc[attacker.id, 'LB_Auto'], 'Skill']
                    field_list.append(f"You consumed LB gauge to cast {skill}.")
                    exp_gain_total += lb_use
                if hit == 2:
                    field_list.append(f"You landed a critical hit with {damage * hit} damage.")
                elif hit == 1:
                    field_list.append(f"You attacked with {damage} damage.")
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
        # user info
        for user in (attacker, defender):
            field_list = []
            field_list.append(f"Level: {self.calclevel(self.dfdict['User'].loc[user.id, 'EXP'])}")
            for statname in ('HP', 'AP'):
                field_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
            if self.dfdict['User'].loc[user.id, 'LB'] == 100:
                field_list.append(f"LB: **MAX**")
            else:
                field_list.append(f"LB: {self.dfdict['User'].loc[user.id, 'LB']}%")
            embed.add_field(name = user.name, value = '\n'.join(field_list))
        defender_base = self.dfdict['User'].loc[defender.id, 'Base']
        embed_colour = self.dfdict['Base'].loc[defender_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        if exp_gain_total + defender_exp_gain_total > 0:
            self.syncpend = 1
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
        # basic attack info (simulation)
        desc_list = []
        desc_list.append(f"*You have {min(result_tup[2], 1) * 100:.0f}% of doing {result_tup[1]} damage.*")
        desc_list.append(f"*You have {max(result_tup[2] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        desc_list.append(f"*{raid} has {min(result_tup[4], 1) * 100:.0f}% of doing {result_tup[3]} damage to you.*")
        desc_list.append(f"*{raid} has {max(result_tup[4] - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        exp_gain_total = 0
        attack_count = 0
        # actual log
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
                _, damage, hitrate, raid_damage, raid_hitrate, hit, kill, raid_hit, raid_kill, exp_gain, lb_use, item_use = result_tup
                if item_use > 0:
                    skill = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user.id, 'I_Auto'], 'Skill']
                    if item_use == 1:
                        field_list.append(f"You consumed {skill}.")
                    else:
                        field_list.append(f"You consumed {item_use} {skill}s.")
                if lb_use > 0:
                    skill = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user.id, 'LB_Auto'], 'Skill']
                    field_list.append(f"You consumed LB gauge to cast {skill}.")
                    exp_gain_total += lb_use
                if hit == 2:
                    field_list.append(f"You landed a critical hit with {damage * hit} damage.")
                elif hit == 1:
                    field_list.append(f"You attacked with {damage} damage.")
                else:
                    field_list.append(f"You missed.")
                if kill != 0:
                    item1 = self.dfdict['Skill'].loc[kill[0], 'Skill']
                    if len(kill) == 2:
                        item2 = self.dfdict['Skill'].loc[kill[1], 'Skill']
                        field_list.append(f"{raid} is KO-ed. You picked up {item1} and {item2}.")
                    else:
                        field_list.append(f"{raid} is KO-ed. You picked up {item1}.")
                exp_gain_total += exp_gain
                if raid_hit == 2:
                    field_list.append(f"{raid} landed a critical hit with {raid_damage * raid_hit} damage.")
                elif raid_hit == 1:
                    field_list.append(f"{raid} countered with {raid_damage} damage.")
                else:
                    field_list.append(f"{raid} missed.")
                if raid_kill:
                    field_list.append(f"You are KO-ed.")
                    break
            attack_count += 1
        field_list.append(f"You gained {exp_gain_total} EXP.")
        embed.add_field(name = 'Battle Log', value = '\n'.join(field_list), inline=False)
        # user info
        field_list = []
        field_list.append(f"Level: {self.calclevel(self.dfdict['User'].loc[user.id, 'EXP'])}")
        for statname in ('HP', 'AP'):
            field_list.append(f"{statname}: {self.dfdict['User'].loc[user.id, statname]}")
        if self.dfdict['User'].loc[user.id, 'LB'] == 100:
            field_list.append(f"LB: **MAX**")
        else:
            field_list.append(f"LB: {self.dfdict['User'].loc[user.id, 'LB']}%")
        embed.add_field(name = user.name, value = '\n'.join(field_list))
        # raid info
        field_list = []
        field_list.append(f"Level: {self.dfdict['Raid'].loc[raid, 'Level']}")
        field_list.append(f"HP: {self.dfdict['Raid'].loc[raid, 'HP']}")
        embed.add_field(name = raid, value = '\n'.join(field_list))
        raid_base = self.dfdict['Raid'].loc[raid, 'Base']
        embed_colour = self.dfdict['Base'].loc[raid_base, 'Colour']
        if embed_colour != '':
            embed.colour = int(embed_colour, 16)
        if exp_gain_total > 0:
            self.syncpend = 1
            self.raidsync = 1
        return embed
    async def executecommand(self, user, ctx, *arg):
        # main command execution
        if self.maint:
            return discord.Embed(description = 'Currently under maintenance. Will be back up shortly.')
        elif len(arg) == 0:
            return self.helpmanual()
        else:
            if arg[0] == 'info':
                if len(arg) == 1:
                    if user.id in self.dfdict['User'].index:
                        # own info
                        return self.infouser(user)
                    else:
                        return discord.Embed(description = self.usernotfound)
                else:
                    try:
                        member = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if member.id in self.dfdict['User'].index:
                            return self.infouser(member)
                        else:
                            return discord.Embed(description = self.targetnotfound)
                    except commands.BadArgument:
                        return discord.Embed(description = self.targetnotfound)
            elif arg[0] == 'base':
                if len(arg) == 1:
                    # list of bases
                    return self.listbase()
                else:
                    # various operations
                    if len(arg) > 2 and arg[1] in ('change', 'start'):
                        # change base or start of tamagotchi
                        if user.id in self.dfdict['User'].index.tolist() and arg[1] == 'start':
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
                elif user.id in self.dfdict['User'].index:
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
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] in ('autolbskill', 'autolb'):
                if len(arg) == 1:
                    # list of skills
                    return self.listskill()
                elif user.id in self.dfdict['User'].index:
                    if arg[1].lower() == 'off':
                        skill = 'off'
                    else:
                        skill = self.find_index(' '.join(arg[1:]), 'Skill')
                        if skill == 'NOTFOUND':
                            return discord.Embed(description = 'Skill not found. Try checking `=char skill`.')
                    return discord.Embed(description = self.infoautolb(user, skill))
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] in ('skill', 'revive', 'heroskill', 'lb', 'hpskill', 'skillhero', 'lbskill', 'skillhp', 'skilllb'):
                if len(arg) == 1:
                    # list of skills
                    return self.listskill()
                elif user.id in self.dfdict['User'].index:
                    consumehp = 0
                    consumelb = 0
                    if arg[0] in ('hero', 'heroskill'):
                        consumelb = 2
                    elif arg[0] in ('lb', 'lbskill', 'skilllb'):
                        consumelb = 1
                    elif arg[0] in ('hpskill', 'skillhp'):
                        consumehp = 1
                    elif arg[0] == 'revive':
                        consumehp = -1
                    elif arg[1].lower() == 'lb':
                        consumelb = 1
                        arg = arg[1:]
                    elif arg[1].lower() == 'hp':
                        consumehp = 1
                        arg = arg[1:]
                    elif arg[1].lower() == 'revive':
                        consumehp = -1
                        arg = arg[1:]
                    skillargs = [a.strip() for a in ' '.join(arg[1:]).split('|')]
                    skill = self.find_index(skillargs[0], 'Skill')
                    if skill == 'NOTFOUND':
                        return discord.Embed(description = 'Skill not found. Try checking `=char skill`.')
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
                                return discord.Embed(description = self.targetnotfound)
                        except commands.BadArgument:
                            return discord.Embed(description = self.targetnotfound)
                    else:
                        return self.infoskill(user, skill, user, consumehp, consumelb)
                    return discord.Embed(description = 'Try `=charhelp skill`.')
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] == 'item':
                if len(arg) == 1:
                    # list of items
                    return self.listitem()
                elif user.id in self.dfdict['User'].index:
                    if arg[1].isnumeric() and len(arg) > 2:
                        num_times = min(int(arg[1]), 20)
                        skillargs = [a.strip() for a in ' '.join(arg[2:]).split('|')]
                    else:
                        num_times = 1
                        skillargs = [a.strip() for a in ' '.join(arg[1:]).split('|')]
                    skill = self.find_index(skillargs[0], 'Item')
                    if skill == 'NOTFOUND':
                        return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    if len(skillargs) > 1:
                        try:
                            target = await commands.MemberConverter().convert(ctx, skillargs[1])
                            if target.id in self.dfdict['User'].index:
                                return self.infoitem(user, skill, target=target, num_times=num_times)
                            else:
                                return discord.Embed(description = self.targetnotfound)
                        except commands.BadArgument:
                            return discord.Embed(description = self.targetnotfound)
                    else:
                        return self.infoitem(user, skill, num_times=num_times)
                    return discord.Embed(description = 'Try `=charhelp item`.')
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] == 'autoitem':
                if len(arg) == 1:
                    # list of skills
                    return self.listitem()
                elif user.id in self.dfdict['User'].index:
                    if arg[1].lower() == 'off':
                        skill = 'off'
                    elif arg[1].isnumeric():
                        return discord.Embed(description = self.infoautoitem(user, int(arg[1])))
                    else:
                        skill = self.find_index(' '.join(arg[1:]), 'Item')
                        if skill == 'NOTFOUND':
                            return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    return discord.Embed(description = self.infoautoitem(user, skill))
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] in ('inventory', 'inv') and user.id in self.dfdict['User'].index:
                return self.infoinventory(user)
            elif arg[0] in 'daily' and user.id in self.dfdict['User'].index:
                return self.infogacha(user, free=1)
            elif arg[0] in 'gacha' and user.id in self.dfdict['User'].index:
                if len(arg) > 1:
                    if arg[1].isnumeric():
                        return self.infogacha(user, int(arg[1]))
                return self.infogacha(user)
            elif arg[0] == 'train' and user.id in self.dfdict['User'].index:
                ap_consume = 1
                skill = None
                if len(arg) > 1:
                    if arg[1].isnumeric():
                        ap_consume = int(arg[1])
                        if len(arg) > 2:
                            skill = self.find_index(' '.join(arg[2:]), 'Item')
                            if skill == 'NOTFOUND':
                                return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    else:
                        skill = self.find_index(' '.join(arg[1:]), 'Item')
                        if skill == 'NOTFOUND':
                            return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    return self.infotrain(user, ap_consume, skill)
                return self.infotrain(user)
            elif arg[0] == 'attack':
                if len(arg) == 1:
                    return discord.Embed(description = 'Try `=charhelp char`.')
                elif user.id in self.dfdict['User'].index:
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
                            return discord.Embed(description = self.targetnotfound)
                    except commands.BadArgument:
                        return discord.Embed(description = self.targetnotfound)
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] == 'duel':
                if len(arg) == 1:
                    return discord.Embed(description = 'Try `=charhelp char`.')
                elif user.id in self.dfdict['User'].index:
                    try:
                        # find member of said name to attack
                        defender = await commands.MemberConverter().convert(ctx, ' '.join(arg[1:]))
                        if defender.id in self.dfdict['User'].index:
                            return self.infoduel(user, defender)
                        else:
                            return discord.Embed(description = self.targetnotfound)
                    except commands.BadArgument:
                        return discord.Embed(description = self.targetnotfound)
                else:
                    return discord.Embed(description = self.usernotfound)
            elif arg[0] == 'raid':
                # to be implemented
                if len(arg) == 1:
                    # available raids
                    return self.listraid()
                elif user.id in self.dfdict['User'].index:
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
                else:
                    return discord.Embed(description = self.usernotfound)
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
            elif arg[0] in ('futureplans', 'futureplan', 'future'):
                return self.infofutureplan()
            elif arg[0] in ('rate', 'gacha'):
                return self.ratemanual()
            else:
                return discord.Embed(description = 'Try `=charhelp`.')

engel = Engel()

class Engelbert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timercheck.start()
        self.synccheck.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.get_channel(id_dict['Engel Logs']).send('I restarted.')

    @tasks.loop(minutes=1.0)
    async def timercheck(self):
        # check timer every minute
        now = datetime.now()
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'hourlyregen']
        thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(hours=1)
        if now.minute == 0 or now > thres:
            engel.userregenall(now)
        df = engel.dfdict['User'][engel.dfdict['User']['TS_Dead'] != '']
        for userid, row in df.iterrows():
            thres = datetime.strptime(row['TS_Dead'], mydtformat) + timedelta(hours=engel.revivehours)
            if now > thres:
                engel.userrevive(userid)

    @tasks.loop(seconds=5.0)
    async def synccheck(self):
        # check if sync is pending
        if engel.syncpend:
            engel.sheetsync()

    @commands.command(aliases=['engelmaint'])
    async def engelbertmaint(self, ctx, *arg):
        # Maintenance mode to pause updating of sheets
        if ctx.message.author.id == id_dict['Owner']:
            if engel.maint:
                engel.maint = 0
                await ctx.send('Maintenance mode shifted.')
            else:
                engel.maint = 1
                await ctx.send('Maintenance mode entered.')

    @commands.command(aliases=['engelsync'])
    async def engelbertsync(self, ctx, *arg):
        # Synchronise Engelbert sheets
        if ctx.message.author.id == id_dict['Owner']:
            engel.maint = 1
            engel.dfsync()
            engel.maint = 0
            await ctx.send('Google sheet synced for Engelbert.')

    @commands.command(aliases=['fred'])
    async def frederika(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # admin test command
        if ctx.message.author.id == id_dict['Owner']:
            user = await self.bot.fetch_user(int(arg[0]))
            embed = await engel.executecommand(user, ctx, *arg[1:])
            embed.set_footer(text = engel.defaultfooter)
            await ctx.send(embed = embed)
            await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp'])
    async def engelberthelp(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, 'help', *arg)
        embed.set_footer(text = engel.defaultfooter)
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama', 'char'])
    async def engelbert(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, *arg)
        embed.set_footer(text = engel.defaultfooter)
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)
