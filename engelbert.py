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
        self.upgradecap = 10
        self.unlockcost = 5
        self.raidcap = 179
        self.raidcap2 = 119
        self.raidcap3 = 79
        self.revivehours = 3
        self.cdjob = 1
        self.cdbase = 4
        self.cdduel = 5 # minutes
        self.skill_apcost = 5
        self.skill_hpcost = 0.2 # % HP cost
        self.skillduration = 5
        self.attackcap = 20 # number of attacks
        self.gachacost  = 10
        self.refinecost = 5
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
                'i2': 40,
                'i3': 25,
                'i4': 12,
                'i5': 3,
                'i6': 10,
                'i7': 10
            },
            '80': {
                'i1': 80,
                'i2': 20
            },
            120: {
                'i2': 20,
                'i3': 20,
                'i4': 17,
                'i5': 3,
                'i6': 20,
                'i7': 20
            },
            '120': {
                'i1': 65,
                'i2': 35
            },
            150: {
                'i3': 20,
                'i4': 16,
                'i5': 4,
                'i6': 30,
                'i7': 30
            },
            '150': {
                'i1': 50,
                'i2': 50
            },
        }
        self.refine_rate = {
            'i1': (100, 'i2', 50),
            'i2': (30, 'i7', 1),
            'i3': (30, 'i6', 1),
            'i4': (4, 'i5', 1),
            'i5': (2, 'i7', 1),
            'i6': (2, 'i7', 1),
            'i7': (2, 'i6', 1)
        }
        self.tower_tuples = {
            25: (180, 50, 'Tonberry Kai', ('i6', 10), ('i8', 6),
                ((15, 'i7', 4), (11, 'i7', 5), (8, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((15000, 'i7', 4), (10000, 'i7', 5), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Enhanced Tonberry that is even stronger than the one in floor 8.',
                'https://caelum.s-ul.eu/BnE0Q30D.png'),
            24: (180, 50, 'Mindflayer', ('i6', 10), ('i8', 6),
                ((15, 'i6', 4), (11, 'i6', 5), (8, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((15000, 'i6', 4), (10000, 'i6', 5), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Mindflayer will attempt to paralyse you. You can resist it if your total defenses are over 3000.',
                'https://caelum.s-ul.eu/esper/ou4fUjQX.png'),
            23: (180, 50, 'Ochu', ('i6', 10), ('i8', 6),
                ((15, 'i6', 4), (11, 'i6', 5), (8, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((15000, 'i6', 4), (10000, 'i6', 5), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Ochu will inflict an ailment on you to halve your highest stat.',
                'https://caelum.s-ul.eu/esper/h4BFr1Tq.png'),
            22: (180, 50, 'Shinryu', ('e20', 0), ('i8', 6),
                ((15, 'i7', 4), (11, 'i7', 5), (8, 'i7', 5), (5, 'i7', 5), (5, 'i7', 6)),
                ((15000, 'i7', 4), (10000, 'i7', 5), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Endure magical attacks for 5 turns.',
                'https://caelum.s-ul.eu/Uc5laJhf.png'),
            21: (180, 50, 'Omega', ('e19', 0), ('i8', 6),
                ((15, 'i7', 4), (11, 'i7', 5), (8, 'i7', 5), (5, 'i7', 5), (5, 'i7', 6)),
                ((15000, 'i7', 4), (10000, 'i7', 5), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Endure physical attacks for 5 turns.',
                'https://caelum.s-ul.eu/esper/BflBUAtn.png'),
            20: (150, 50, 'Cactuar', ('i6', 10), ('i8', 5),
                ((5, 'i6', 4), (5, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((10000, 'i6', 4), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Cactuar will not attack you in phase 1 but only takes 1 damage.',
                'https://caelum.s-ul.eu/esper/CtQEnlKj.png'),
            19: (150, 50, 'Demon Wall', ('i6', 10), ('i8', 5),
                ((5, 'i6', 4), (5, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((10000, 'i6', 4), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Demon Wall attacks you while drawing closer. You lose if you cannot defeat it by phase 1.',
                'https://caelum.s-ul.eu/esper/E6Nk0f9N.png'),
            18: (150, 50, 'Leviathan', ('e18', 0), ('i8', 5),
                ((15, 'i7', 4), (10, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Leviathan is immune to non-critical damage.',
                'https://caelum.s-ul.eu/esper/pRPeCusl.png'),
            17: (150, 50, 'Anima', ('e17', 0), ('i8', 5),
                ((5, 'i7', 4), (5, 'i7', 5), (5, 'i7', 5), (5, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Anima shares her pain with you. If you can endure her pain in phase 1, you win.',
                'https://caelum.s-ul.eu/DCsfqtff.png'),
            16: (150, 50, 'Aigaion', ('i8', 80), ('i8', 5),
                ((15, 'i6', 4), (10, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((10000, 'i6', 4), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Aigaion has no special gimmicks but mainly deals physical damage (same damage calculation as raid).',
                'https://caelum.s-ul.eu/esper/MMEqzj4e.png'),
            15: (150, 50, 'Glacial', ('i8', 80), ('i8', 5),
                ((15, 'i6', 4), (10, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((10000, 'i6', 4), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Glacial has no special gimmicks but mainly deals magical damage (same damage calculation as raid).',
                'https://caelum.s-ul.eu/esper/gufdaaew.png'),
            14: (150, 50, 'Carbuncle', ('i8', 70), ('i8', 4),
                ((15, 'i7', 4), (10, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Carbuncle reflects magical damage.',
                'https://caelum.s-ul.eu/esper/XWy0PpzJ.png'),
            13: (150, 50, 'Golem', ('i8', 70), ('i8', 4),
                ((15, 'i7', 4), (10, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Golem has very high DEF but low SPR.',
                'https://caelum.s-ul.eu/esper/oQ7SdelP.png'),
            12: (150, 50, 'Chocobo Eater', ('e16', 0), ('i8', 4),
                ((15, 'i7', 4), (10, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Chocobo Eater dispels your buffs. Try debuffing it.',
                'https://caelum.s-ul.eu/74v8pJU8.png'),
            11: (150, 50, 'Typhon', ('e15', 0), ('i8', 4),
                ((15, 'i7', 4), (10, 'i7', 5), (5, 'i7', 5), (3, 'i7', 6)),
                ((10000, 'i7', 4), (5000, 'i7', 5), (2000, 'i7', 5), (100, 'i7', 6)),
                'Typhon messes with your stats so that your DEX replaces your ATK/MAG.',
                'https://caelum.s-ul.eu/esper/qALvt1Nq.png'),
            10: (150, 50, 'Gilgamesh', ('i8', 50), ('i8', 4),
                ((5, 'i6', 4), (5, 'i6', 5), (5, 'i6', 5), (3, 'i6', 6)),
                ((10000, 'i6', 4), (5000, 'i6', 5), (2000, 'i6', 5), (100, 'i6', 6)),
                'Gilgamesh reduces your DEF to 0 and you win if you survive phase 1.',
                'https://caelum.s-ul.eu/iN6qLrjp.png'),
            9: (120, 50, 'Magic Pot', ('i6', 5), ('i8', 3),
                ((5, 'i6', 5), (5, 'i6', 5), (5, 'i6', 5)),
                ((5000, 'i6', 5), (3000, 'i6', 5), (500, 'i6', 10)),
                'Endure bombardment of Magic Pot and it will flee after Phase 1.',
                'https://caelum.s-ul.eu/AIarVqAN.png'),
            8: (120, 50, 'Tonberry', ('e14', 0), ('i8', 3),
                ((10, 'i7', 4), (5, 'i7', 5), (3, 'i7', 6)),
                ((5000, 'i7', 4), (3000, 'i7', 5), (100, 'i7', 6)),
                'Tonberry reduces your DEF and AGI to 0 but will not attack in Phase 1. Kill quickly.',
                'https://caelum.s-ul.eu/esper/id37FPgn.png'),
            7: (120, 50, 'Fenrir', ('e11', 0), ('i8', 3),
                ((10, 'i7', 4), (5, 'i7', 5), (3, 'i7', 6)),
                ((5000, 'i7', 4), (3000, 'i7', 5), (1000, 'i7', 6)),
                'Fenrir is immune to debuffs. Try buffing your own stats.',
                'https://caelum.s-ul.eu/esper/g3Os0zDz.png'),
            6: (120, 50, 'Alexander', ('e13', 0), ('i8', 3),
                ((10, 'i7', 4), (5, 'i7', 5), (3, 'i7', 6)),
                ((2000, 'i7', 4), (1000, 'i7', 5), (100, 'i7', 6)),
                'Alexander has high DEF/SPR. Maybe you can lower them?',
                'https://caelum.s-ul.eu/mR0vPG2a.png'),
            5: (120, 50, 'Diabolos', ('e12', 0), ('i8', 3),
                ((10, 'i7', 4), (5, 'i7', 5), (3, 'i7', 6)),
                ((5000, 'i7', 4), (3000, 'i7', 5), (1000, 'i7', 6)),
                'Diabolos reduces your SPR to 0. Try to raise AGI to dodge it.',
                'https://caelum.s-ul.eu/esper/kn082MLW.png'),
            4: (100, 50, 'Marilith', ('i7', 5), ('i8', 2),
                ((10, 'i7', 3), (5, 'i7', 5), (3, 'i7', 5)),
                ((3000, 'i7', 3), (1000, 'i7', 5), (100, 'i7', 5)),
                'Enemy has high DEX. Note your DEF/SPR.',
                'https://caelum.s-ul.eu/esper/p5XM03y3.png'),
            3: (80, 50, 'Ahriman', ('i6', 3), ('i8', 2),
                ((10, 'i6', 3), (5, 'i6', 4), (3, 'i6', 4)),
                ((2000, 'i6', 3), (1000, 'i6', 4), (100, 'i6', 4)),
                'Enemy has high AGI. Note your DEX.',
                'https://caelum.s-ul.eu/esper/dZ3BeAWU.png'),
            2: (60, 50, 'Behemoth', ('i7', 2), ('i8', 1),
                ((10, 'i7', 2), (5, 'i7', 3), (3, 'i7', 3)),
                ((1500, 'i7', 2), (800, 'i7', 3), (100, 'i7', 3)),
                'Enemy has high DEX/ATK/MAG. Survive and defeat it.',
                'https://caelum.s-ul.eu/esper/S4EL3aLY.png'),
            1: (40, 50, 'Iron Giant', ('i6', 2), ('i8', 1),
                ((10, 'i6', 2), (5, 'i6', 3), (3, 'i6', 3)),
                ((1000, 'i6', 2), (500, 'i6', 3), (100, 'i6', 3)),
                'Enemy has high HP/DEF/SPR. Have enough DPS to clear within turn limit.',
                'https://caelum.s-ul.eu/esper/39QkFDA8.png'),
        }
        self.tower_stats = {
            25: (15000, (9999, 9999, 1600, 1600, 9999, 800)),
            24: (9999, (2500, 2500, 1800, 1800, 1000, 700)),
            23: (9999, (2200, 2200, 1500, 1500, 1000, 600)),
            22: (99999, (0, 3500, 9999, 9999, 9999, 0)),
            21: (99999, (3500, 0, 9999, 9999, 9999, 0)),
            20: (5, (9999, 9999, 9999, 9999, 9999, 1300)),
            19: (9999, (2200, 2200, 2000, 2000, 1100, 400)),
            18: (9999, (2200, 2200, 1800, 1800, 1100, 900)),
            17: (9999, (3000, 3000, 2000, 2000, 1200, 0)),
            16: (12000, (2500, 1000, 900, 900, 1200, 900)),
            15: (12000, (1000, 2500, 800, 800, 1200, 1000)),
            14: (15000, (1500, 1500, 500, 500, 1100, 850)),
            13: (20000, (1500, 1500, 5000, 0, 1100, 750)),
            12: (12000, (2200, 2200, 800, 800, 1000, 850)),
            11: (9000, (2000, 2000, 400, 400, 1100, 850)),
            10: (9999, (2550, 0, 1500, 1500, 1100, 700)),
            9: (1, (3000, 3000, 9999, 9999, 9999, 0)),
            8: (9999, (3000, 0, 1200, 1200, 200, 700)),
            7: (9000, (2000, 2000, 800, 800, 800, 700)),
            6: (6000, (1200, 1200, 2000, 2000, 1000, 500)),
            5: (9000, (0, 1600, 600, 600, 900, 700)),
            4: (9000, (1800, 1800, 600, 600, 3000, 800)),
            3: (7000, (1400, 1400, 500, 500, 700, 1000)),
            2: (5000, (1400, 1400, 500, 500, 700, 500)),
            1: (3000, (700, 700, 700, 700, 300, 300))
        }
        self.sheettuples = (
            ('Base', 'Base'),
            ('Job', 'JobID'),
            ('Skill', 'SkillID'),
            ('User', 'User'),
            ('Raid', 'Raid'),
            ('Esper', 'EsperID'),
            ('Log', ''),
        )
        self.statlist = ('HP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.statlist2 = ('ATK', 'MAG', 'DEF', 'SPR', 'DEX', 'AGI')
        self.usernotfound = 'Choose a base first with `=char start (base name)`. Check `=char base` for available bases.'
        self.targeterror = 'User not found or did not start a character.'
        self.defaultfooter = 'Note that this is separated from usual WOTV functions. Check `=char changelog` for updates. Prone to adjustment/bugs.'
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
                '- Type `=char train` or `=char train (number of AP)` (e.g. `=char train 10`) to quickly spend AP for EXP.',
                '- You can use Hero Drinks to gain EXP.',
                '- Type `=char train (number) hero` (e.g. `=char train 3 hero`).',
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
                '- The scale has a diminishing effect as lower end of DEX or AGI gets higher.',
                '- For example, you need 100 AGI to 100% dodge a 0 DEX opponent.',
                '- But you need 1350 AGI to 100% dodge a 1000 DEX opponent.',
                '- Critical damage is 2x regular damage.',
            )),(
            'PVP', (
                '- Two types of PVP: attacks and duels.',
                f"- Attacks cost {self.attack_apcost}.",
                '- Both attacker and target gain EXP scaled to damage and opponent level.',
                '- Type `=char attack (user ping)` (e.g. `=char attack @Caelum`) to another player.',
                f"- Type `=char attack (number) (user ping)` (e.g. `=char attack 6 @Caelum`) to attack multiple times  (up to {self.attackcap}).",
                '- Duels are basically battle simulation just for fun.',
                '- Duels do not cost AP nor result in any item/gil gain or loss.',
                '- Winner will take some trophies from loser, scaled with trophy count difference.',
                f"- There is a cooldown of {self.cdduel} minutes to duel for trophies.",
                f'- If trophy count difference is over 50, there is no trophy change.',
                '- Trophy is also passively gained by 1 every hour.',
                '- If both auto skills are turned on, they are casted in duel and both HP become doubled.',
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
                '- Type `=char start (base name)` (e.g. `=char base start jake`) to start your character.',
                '- Type `=char base change (base name)` (e.g. `=char base change rain`) to change the base of your character.',
            )),(
            'EX Base', (
                'EX bases are premium bases traded using Dark Matters.',
                'They come with unique jobs that have low starting stats',
                'After upgrading the EX bases with Dark Matters, the unique jobs will have higher stats than other bases.',
                'Unique jobs also come with powerful Limit Break that are special skills that can only consume LB gauge or Hero Drink.',
                'Limit Break is usually a combination of two skills at main job potencies, or three skills at sub job potencies, or one effect with even higher potency.',
                f"Max upgrade is {self.upgradecap}."
            )),(
            'EX Base Commands', (
                '- Type `=char exbase` to find list of available EX bases and their unlock / upgrade status.',
                '- Type `=char exbase (base name)` (e.g. `=char exbase hyoh`) to read info of the EX base.',
                '- Type `=char exbase change (base name)` (e.g. `=char exbase change ildyra`) to change the base of your character.',
                '- Type `=char exbase unlock (base name)` (e.g. `=char exbase unlock tifa`) to unlock the EX base.',
                '- Type `=char exbase up (base name)` (e.g. `=char exbase up ace`) to upgrade the EX base.',
                '- Type `=char main ex` to change main job into the unique job.'
            ))
        )
        self.manual['esper'] = ((
            'Description', (
                'Espers are stat boosts traded using Auracites.',
                'The boosts all scale on one stat different to each esper.',
                'After upgrading the espers with Auracites, the boosts will become more powerful.',
                'The scaled stat might be decreased at first but may become boosts with enough upgrades.',
                f"Max upgrade is {self.upgradecap}."
            )),(
            'Commands', (
                '- Type `=char esper` to find list of espers and their unlock / upgrade status.',
                '- Type `=char esper (esper name)` (e.g. `=char esper shiva`) to read info of the esper.',
                '- Type `=char esper change (esper name)` (e.g. `=char esper change ifrit`) to change the esper of your character.',
                '- Type `=char esper unlock (esper name)` (e.g. `=char esper unlock titan`) to unlock the esper.',
                '- Type `=char esper up (esper name)` (e.g. `=char esper up siren`) to upgrade the esper.',
                '- Type `=char esper off` to unequip the esper of your character.',
            ))
        )
        self.manual['job'] = ((
            'Description', (
                'Your jobs determine most of your stats.',
                'You have 100% growth rate of main job and 50% of each sub job.',
                f"Main job can be changed every {self.cdjob} hours, but changing sub jobs has no limit.",
                'Changing main job also resets your sub jobs. They can be changed anytime however.',
            )),(
            'Commands', (
                '- Type `=char job` to find list of jobs and their growth rate.',
                '- Type `=char main (job name)` (e.g. `=char job main red mage`) to change main job.',
                '- Type `=char sub1 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 1.',
                '- Type `=char sub2 (job name)` (e.g. `=char job sub1 assassin`) to change sub job 2.',
                '- Type `=char subs (job name) | (job name)` (e.g. `=char job subs green mage | mechanic`) to change both sub jobs at once.',
                '- Type `=char main ex` to change main job into unique job (EX base only).'
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
                '- Type `=char lbskill` to cast Limit Break (EX base unique job only).',
                '- Type `=char heroskill ex` to cast Limit Break with Hero Drink (EX base unique job only).'
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
                '- Type `=char autolbskill`(e.g. `=char autolbskill brave`) to set Limit Break (EX base unique job only).',
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
                '- Type `=char autoitem (number) (item name)` (e.g. `=char autoitem 30 phoenix`) to change both.'
                '- Type `=char autoitem off` to turn off.',
            )),(
            'Gacha', (
                f"- Each gacha costs {self.gachacost} Gil.",
                '- Type `=char daily` for free 10 gachas daily (+ bonus 10 Ethers and 1 Elixir).',
                '- Type `=char gacha` to gacha 10 times.',
                '- Type `=char gacha (number)` (e.g. `=char gacha 7`) to gacha a number of times.',
                '- Type `=char rate` to check gacha rate.',
            )),(
            'Refine', (
                f"- Spend {self.refinecost} Arcanas to convert a quantity of items into another item type.",
                '- Note that Arcanas themselves cannot be refined.',
                '- Type `=char refine` to find list of available options.',
                '- Type `=char refine (item name)` (e.g. `=char refine potion`) to refine Potions into Phoenix Downs.',
                '- Type `=char refine (number) (item name)` (e.g. `=char refine 10 potion`) to refine a number of items at once.',
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
                '- Raids higher than level 80 will have more drops but higher HP.'
                f"- Group 1 levels will loop between {self.raidcap2 + 1} and {self.raidcap}.",
                f"- Group 2 levels will loop between {self.raidcap3 + 1} and {self.raidcap2}.",
                f"- Group 3 levels will loop between 0 and {self.raidcap3}.",
            ))
        )
        self.manual['tower'] = ((
            'Description', (
                'Tower is a series of floors that you can challenge for rewards.',
                'You need to clear in sequence, i.e. cannot challenge 3 if you have not cleared 2 yet.'
                f"Currently up to floor {max(self.tower_tuples.keys())}.",
                'Rewards are separated into first clear, repeat clear and achievement missions.',
                'There are two types of achievement missions - clear within a number of turns and clear taking less than a number of damage.',
            )),(
            'Battle', (
                '- Your current conditions (HP, LB gauge, status) are ignored for your tower fight.',
                '- i.e. you start from max HP for each fight and your auto skill will apply for the entire fight.',
                '- Items cannot be used in tower.',
                '- Unless stated otherwise, floor bosses use ATK if your DEF is higher than SPR or MAG if your SPR is higher than DEF (opposite of usual).',
                '- Unless stated otherwise, you are attacked first in tower (opposite of raids).',
                '- You can battle up to 4 phases with 5 turns each, in a total of 20 turns.',
                '- Your HP is fully recovered in the beginning of each phase.',
                '- You fail if your HP reaches 0 or cannot kill the floor boss within 20 turns.',
                '- If you fail the tower battle stays active. You can challenge again without spending AP.',
                '- However, you cannot start another floor until you give up.'
            )),(
            'Commands', (
                '- Type `=char tower` to find list of available tower floor bosses (top 10 available).',
                '- Type `=char tower mission` to find list of available tower floor bosses with unfinished missions.',
                '- Type `=char tower (floor number)` (e.g. `=char tower 1`) to view the info of specific floor.',
                '- Type `=char tower fight (floor number)` (e.g. `=char tower fight 1`) to fight the specific floor boss.',
                '- Type `=char tower giveup` to give up an active tower battle.'
            ))
        )
        manual_commands = '\n'.join([f"`=charhelp {k}`" for k in self.manual.keys()])
        self.helpintro = (
            'Engelbert is an experimental project of Discord bot tamagotchi '
            '(digital pet / avatar / character). It is still under constant development so things '
            'may be subject to change and adjustment. Feel free to drop some feedback!\n'
            '- Type `=char changelog` for recent changes.\n'
            '- Type `=char futureplan` for tentative future plans.\n'
            '- Type `=charrep (number) (command)` (e.g. `=charrep 10 exbase up hyoh`) for repeated commands (up to 10).\n'
            '- WARNING: Multiple replies will occur so please do not overuse to flood the channel...\n'
            '- For more in-depth info of the following, try:\n' +
            manual_commands
        )
        self.futureplan = (
            'Subject to change and feasibility. Cannot say when they will be done... In order of priority:',
            '- Equipment: Make use of overflow EXP into flat stat boosts. Initial release will be modest and see how the balance goes...',
            '- (if people are still playing) Esper Expansion: esper gauge and in-battle-buffs',
        )
        self.changelog = (
            ('12th March 2021', (
                '- New floors (up to 25) with 2 new espers.',
                '- Anima and Leviathan stats buffed.',
                '- Noctis, Bartz, Montblanc, Golbez limit breaks now come with small secondary effects',
                '- Duel now uses skills if both self and opponent autoskills are turned on and both HP doubled.',
                '- Trophy system (beta) for duel, check `=charhelp battle`.',
            )),
            ('7th March 2021', (
                '- New floors (up to 20) with 2 new espers.',
                '- Chocobo and Typhon stats buffed.',
            )),
            ('5th March 2021', (
                '- Now DEX and AGI have diminishing effect as the values become higher.',
                '- DEX and AGI buffs nerfed to be the same as debuffs.',
                '- New tower floors (up to 16) with 2 new espers.',
                '- Note that missions may not be all feasible at this point...',
                '- New EX Bases. Note that triple effects have lower potencies.',
                '- Under-performing EX Base Physalis LB changed into triple debuffs.',
                '- Under-performing EX Bases Mont has similar change but replaced with Daisy.',
                '- Mont will be re-released in a future date.',
                '- Base stats (including AP) are increased across the board, mostly to scale with the new DEX/AGI distribution.',
                '- Old (cost 5) espers have their final boosts slightly increased.',
                '- You can now refine several items at once.',
                '- Type `=charrep (number) (command)` (e.g. `=charrep 10 exbase up hyoh`) for repeated commands (up to 10).',
                '- WARNING: Multiple replies will occur so please do not overuse to flood the channel.'
            )),
            ('5th March 2021 (Raid Adjustments)', (
                '- Some raids are abolished, with group 2 and group 3 only having the basic ones left.',
                '- Abolished raids will reappear in tower if you miss them.',
                '- Raid stats redistributed (major for Sylph and Ramuh, minor for others).',
                '- Raid level separators are now 80 and 120, drop rates for 100+ now apply to 80+.',
                '- Max raid level is now level 179, with drop rate separator adjusted from 140 to 150.',
                '- Dark Matter / Auracite rates - 120+: 15/15; 140+: 20/20 -> 120+: 20/20, 150+: 30/30.'
            )),
            ('1st March 2021', (
                '- Base change cooldown changed to 4 hours. Main job change cooldown reduced to 1 hour.',
                '- Raid level cap raised to 159. Level separators will be adjusted in a future date.',
            )),
            ('28th February 2021', (
                '- Base change cooldown halved to 12 hours. Main job change cooldown halved to 6 hours.',
                '- Tower expansion with new espers unlocked with tower.',
                '- Tower battle turns were bugged to be 24 instead of 20... Fixed.'
            )),
            ('27th February 2021', (
                '- Tower (`=charhelp tower`) - only basic floors for now. To add more in future...',
                '- Refine (`=charhelp item`)'
            )),
            ('26th February 2021', (
                '- New EX bases.',
                '- You can now set your autoitem item and threshold in one line.'
            )),
            ('24th February 2021', (
                '- Stats adjustment across the board (including raids), mainly increasing DEX / AGI values so they hold similar values as other stats.',
                '- Now 1% critical / evasion rate per 2 points of DEX / AGI difference. (i.e. 200 to hit 100%)',
                '- Esper boosts are adjusted accordingly, now their boosts are more spread out and even.',
                '- Further finetuning might happen if balance is wonky...',
                '- New jobs',
                '- Lightning and Terra main skills changed to Mirror of Equity and Ruin respectively.',
            )),
            ('23rd February 2021', (
                '- Changed how commands are parsed, please let me know if any commands are not working properly.',
                '- A few commands slightly shortened.',
                '- Some older and longer commands are depreciated.',
                '- You can no longer use Elixirs to train, only Hero Drinks (if anyone is even using...).'
            )),
            ('21st February 2021', (
                '- EX Base (`=charhelp base`).',
                '- Esper (`=charhelp esper`).',
                '- Raids now separated into 3 groups (`=charhelp raid`) with raised level cap that also come with higher drop rate (`=char rate`).'
            )),
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
        self.colours = {
            'fire': 0xE47051,
            'ice': 0xA4B3F0,
            'wind': 0xA3E053,
            'earth': 0xF6D993,
            'thunder': 0xF5F464,
            'water': 0xAAFAFC,
            'light': 0xFCFCFC,
            'dark': 0xE083F4,
            'neutral': 0x7F8486
        }
        self.spreadsheet = client.open(id_dict['Engel Sheet'])
        self.dfdict = dict()
        self.dfsync()
        self.levelexp_init()
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
        try:
            set_with_dataframe(self.spreadsheet.worksheet('User'), df, include_index=True)
            if self.logsync:
                set_with_dataframe(self.spreadsheet.worksheet('Log'), self.dfdict['Log'], include_index=False)
                self.logsync = 0
            if self.raidsync:
                set_with_dataframe(self.spreadsheet.worksheet('Raid'), self.dfdict['Raid'], include_index=True)
                self.raidsync = 0
            self.syncpend = 0
            return 1
        except gspread.exceptions.APIError as e:
            return e
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
        elif dfname == 'EX Base':
            df = self.dfdict['Base'][self.dfdict['Base']['Hidden'] == 'ex']
            indices = df.index
            indexer = lambda x: x.name
        else:
            df = self.dfdict[dfname]
            if 'Hidden' in df.columns:
                df = df[df['Hidden'] == '']
            if dfname == 'Job':
                indices = df['Job']
                indexer = lambda x: x['Job']
            elif dfname == 'Esper':
                indices = df['Esper']
                indexer = lambda x: x['Esper']
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
    def unlock_parse(self, input, reverse=0):
        # parse EX_Unlock and Esper_Unlock into dict
        if reverse == 0:
            if input == '':
                return dict()
            parsed_unlock = input.split('/')
            unlock_dict = dict()
            # key = unlocked, value = upgrade level
            for unlock in parsed_unlock:
                unlock_list = unlock.split(',')
                unlock_dict[unlock_list[0]] = int(unlock_list[1])
            return unlock_dict
        else:
            unlock_list = []
            for k, v in input.items():
                unlock_list.append(f"{k},{v}")
            return '/'.join(unlock_list)
    def tower_parse(self, input, reverse=0):
        # parse T_Record into dict
        if reverse == 0:
            if input == '':
                return dict()
            parsed_unlock = input.split('/')
            unlock_dict = dict()
            # key = cleared, value = [min turns, min damage]
            for unlock in parsed_unlock:
                unlock_list = unlock.split(',')
                unlock_dict[int(unlock_list[0])] = [int(a) for a in unlock_list[1:]]
            return unlock_dict
        else:
            unlock_list = []
            for k, v in input.items():
                unlock_list.append(f"{k},{v[0]},{v[1]}")
            return '/'.join(unlock_list)
    def calcupcost(self, up, unlockcost=None):
        # return dark matter / auracite upgradecost
        if unlockcost == None:
            return up
        elif unlockcost == 5:
            return up
        elif unlockcost == 10:
            return 1 + int(up * 1.5)
        elif unlockcost == 15:
            return 2 + int(up * 2.45)
        elif unlockcost == 20:
            return 2 + up * 4
        else:
            return self.levelcap
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
    def calchitrate(self, dex, agi):
        # calculate critical or hit rate from dex - agi
        accuracy = dex - agi
        divisor = 100 + min(dex, agi) // 4
        if accuracy == 0:
            return 1
        elif accuracy >= divisor:
            return 2
        elif accuracy <= -divisor:
            return 0
        else:
            return 1 + round(accuracy / divisor, 2)
    def calcstats(self, userid, usertype='U', moddict=None, stat=None):
        # returns dict of stats
        if usertype == 'U':
            # calculate stats given user id
            userrow = self.dfdict['User'].loc[userid]
            userdict = dict()
            userdict['Level'] = self.calclevel(self.dfdict['User'].loc[userid, 'EXP'])
            baserow = self.dfdict['Base'].loc[userrow['Base']]
            if stat == 'ALL':
                statlist = self.statlist
            elif stat == None:
                statlist = self.statlist2
            else:
                statlist = [stat]
            for statname in statlist:
                userdict[statname] = baserow[statname]
            level_tup = (
                ('Main', userdict['Level'] + 1),
                ('Sub1', userdict['Level'] // 2 + 1),
                ('Sub2', (userdict['Level'] + 1) // 2)
            )
            for job_col, job_level in level_tup:
                jobrow = self.dfdict['Job'].loc[userrow[job_col]]
                # EX job upgrade changes
                if jobrow['Hidden'] == 'ex':
                    stat_perc = (self.upgradecap + userrow['EX_Up']) / (self.upgradecap * 2)
                    for statname in statlist:
                        if statname in ('HP', 'AP'):
                            userdict[statname] += jobrow[statname] * job_level
                        else:
                            userdict[statname] += int(jobrow[statname] * job_level * stat_perc)
                else:
                    for statname in statlist:
                        userdict[statname] += jobrow[statname] * job_level
            # Esper stat changes
            if userrow['Esper'] != '' and stat in ('ALL', None):
                esperrow = self.dfdict['Esper'].loc[userrow['Esper']]
                scaledstat = userdict[esperrow['S_Stat']]
                for prefix in ('S', 'B1', 'B2'):
                    if esperrow[f"{prefix}_Stat"] == '':
                        continue
                    statmod = (esperrow[f"{prefix}_MIN"] + (esperrow[f"{prefix}_MAX"] - esperrow[f"{prefix}_MIN"]) * userrow['E_Up'] / self.upgradecap) / 100
                    for statname in esperrow[f"{prefix}_Stat"].split('/'):
                        userdict[statname] += int(scaledstat * statmod)
            if moddict != None:
                for k, v in moddict.items():
                    userdict[k] = int(round(userdict[k] * v))
            return userdict
        elif usertype == 'R':
            # calculate raid stats given raid name
            raidrow = self.dfdict['Raid'].loc[userid]
            raiddict = dict()
            baserow = self.dfdict['Base'].loc[raidrow['Base']]
            jobrow = self.dfdict['Job'].loc[baserow['Main']]
            if stat == None or stat == 'ALL':
                for statname in self.statlist2:
                    raiddict[statname] = baserow[statname] + jobrow[statname] * (raidrow['Level'] + 1)
            if stat == 'HP' or stat == 'ALL':
                raiddict['HP'] = baserow['HP'] + jobrow['HP'] * (raidrow['Level'] + 1)
                if raidrow['Level'] > 79:
                    raiddict['HP'] = raiddict['HP'] * 2
                    raiddict['HP'] += jobrow['HP'] * (raidrow['Level'] - 79)
            if moddict != None:
                for k, v in moddict.items():
                    raiddict[k] = int(round(raiddict[k] * v))
            return raiddict
        elif usertype == 'T':
            # calculate tower stats given tower floor
            towerdict = {k: v for k, v in zip(self.statlist2, self.tower_stats[userid][1])}
            if moddict != None:
                for k, v in moddict.items():
                    towerdict[k] = int(round(towerdict[k] * v))
            return towerdict
    def calcdamage(self, attacker, defender, a_skilltup=None, d_skilltup=None, counter=0, raid=0):
        # calculate damage given attacker and defender
        # returns tuples to be parsed by other functions
        # skill check
        skilltuplist = []
        if a_skilltup != None:
            skillrow = self.dfdict['Skill'].loc[a_skilltup[0]]
            if skillrow['Stat'] == 'COMBO':
                for subpotency in ('Main', 'Sub'):
                    if skillrow[subpotency] == '':
                        continue
                    for subskillid in skillrow[subpotency].split('/'):
                        subskillrow = self.dfdict['Skill'].loc[subskillid]
                        if subskillrow['Healing'] == 0:
                            skilltuplist.append((subskillid, subpotency, 0))
            else:
                skilltuplist += [(*a_skilltup, 0)]
        if d_skilltup != None:
            skillrow = self.dfdict['Skill'].loc[d_skilltup[0]]
            if skillrow['Stat'] == 'COMBO':
                for subpotency in ('Main', 'Sub'):
                    if skillrow[subpotency] == '':
                        continue
                    for subskillid in skillrow[subpotency].split('/'):
                        subskillrow = self.dfdict['Skill'].loc[subskillid]
                        if subskillrow['Healing'] == 0:
                            skilltuplist.append((subskillid, subpotency, 1))
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
        # Tower that reads sheet stats
        if raid == 2 and defender in (23,):
            attackdict = self.calcstats(attacker, moddict=None)
            if defender == 23: # Ochu
                maxstat = max([(v, k) for k, v in attackdict.items()])[1]
                a_moddict[maxstat] = a_moddict[maxstat] * 0.5
        # get their status sheets
        if raid == 2 and defender == 12: # Tower Chocobo Eater
            attackdict = self.calcstats(attacker, moddict=None)
        else:
            attackdict = self.calcstats(attacker, moddict=a_moddict)
        if raid == 1:
            defenddict = self.calcstats(defender, usertype='R', moddict=d_moddict)
        elif raid == 2:
            # tower
            if defender == 7: # Fenrir
                defenddict = self.calcstats(defender, usertype='T')
            else:
                defenddict = self.calcstats(defender, usertype='T', moddict=d_moddict)
            if defender not in (5, 8, 10, 15, 16, 21, 22):
                if attackdict['DEF'] > attackdict['SPR']:
                    defenddict['MAG'] = 0
                else:
                    defenddict['ATK'] = 0
        else:
            defenddict = self.calcstats(defender, moddict=d_moddict)
        # pick higher potential damage
        if raid == 2 and defender == 11: # Tower Typhon
            damage = max(attackdict['DEX'] - defenddict['DEF'], attackdict['DEX'] - defenddict['SPR'], 0)
        elif raid == 2 and defender == 20: # Tower Cactuar
            damage = 1
        else:
            damage = max(attackdict['ATK'] - defenddict['DEF'], attackdict['MAG'] - defenddict['SPR'], 0)
        hitrate = self.calchitrate(attackdict['DEX'], defenddict['AGI'])
        if raid == 2 and defender == 14: # Tower Carbuncle
            if attackdict['ATK'] - defenddict['DEF'] < attackdict['MAG'] - defenddict['SPR']:
                hitrate = -1
        if counter:
            counter_damage = max(defenddict['ATK'] - attackdict['DEF'], defenddict['MAG'] - attackdict['SPR'], 0)
            counter_hitrate = self.calchitrate(defenddict['DEX'], attackdict['AGI'])
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
        # returns tuples to be parsed in other functions
        attackrow = self.dfdict['User'].loc[attacker]
        defendrow = self.dfdict['User'].loc[defender]
        if attackrow['A_Skill'] != '':
            a_skilltup = (attackrow['A_Skill'], attackrow['A_Potency'])
        else:
            a_skilltup = None
        if defendrow['A_Skill'] != '':
            d_skilltup = (defendrow['A_Skill'], defendrow['A_Potency'])
        else:
            d_skilltup = None
        damage, hitrate = self.calcdamage(attacker, defender, a_skilltup, d_skilltup)
        # check attack criteria
        if attackrow['HP'] == 0:
            return (0, damage, hitrate, 'You are dead!')
        elif attackrow['AP'] < self.attack_apcost:
            return (0, damage, hitrate, 'Not enough AP!')
        elif defendrow['HP'] == 0:
            return (0, damage, hitrate, 'Target is dead!')
        elif zero_attack:
            return (0, damage, hitrate)
        else:
            # use lb
            lb_use = 0
            if attackrow['LB_Auto'] != 'off' and attackrow['LB'] == 100:
                if attackrow['LB_Auto'] == 'ex':
                    skillrow = self.dfdict['Skill'].loc[attackrow['Main']]
                else:
                    skillrow = self.dfdict['Skill'].loc[attackrow['LB_Auto']]
                if attackrow['A_Skill'] == '' or self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                    lb_use = self.infoskill(attacker, skillrow.name, argop=2)
                    attackrow = self.dfdict['User'].loc[attacker]
                    if not self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                        # recalculate damage and hit rate
                        a_skilltup = (attackrow['A_Skill'], attackrow['A_Potency'])
                        damage, hitrate = self.calcdamage(attacker, defender, a_skilltup, d_skilltup)
            self.userconsumeduration(attacker)
            # consume AP
            self.dfdict['User'].loc[attacker, 'AP'] = int(attackrow['AP'] - self.attack_apcost)
            # calculate critical or hit rate
            if hitrate > 1:
                hit = 1 + ((hitrate - 1) > random.random())
            else:
                hit = hitrate > random.random()
            # EXP gain
            a_level = self.calclevel(attackrow['EXP'])
            d_level = self.calclevel(defendrow['EXP'])
            exp_gain = 15 + damage * hit // 30 + d_level * 2
            # bonus EXP for killing
            kill = self.userdamage(defender, damage * hit)
            if kill:
                exp_gain += d_level * 2
            self.dfdict['User'].loc[attacker, 'EXP'] = attackrow['EXP'] + exp_gain
            # defender EXP regardless of hit
            defender_exp_gain = 10 + damage * hit // 45 + a_level * 2
            self.dfdict['User'].loc[defender, 'EXP'] = defendrow['EXP'] + defender_exp_gain
            # LB gain
            lb_gain = ((d_level - 1) // a_level + 1) * 10
            lb_gain = min(100 - attackrow['LB'], lb_gain)
            self.dfdict['User'].loc[attacker, 'LB'] = attackrow['LB'] + lb_gain
            # defender LB gain
            defender_lb_gain = ((a_level - 1) // d_level + 1) * 10
            defender_lb_gain = min(100 - defendrow['LB'], defender_lb_gain)
            self.dfdict['User'].loc[defender, 'LB'] = defendrow['LB'] + defender_lb_gain
            # Gil gain
            self.dfdict['User'].loc[attacker, 'Gil'] = attackrow['Gil'] + self.attack_apcost
            return (1, damage, hitrate, hit, kill, exp_gain, defender_exp_gain, lb_use)
    def userdamage(self, defender, damage):
        # function for a user to take damage
        # returns boolean whether user is killed
        new_hp = int(max(self.dfdict['User'].loc[defender, 'HP'] - damage, 0))
        self.dfdict['User'].loc[defender, 'HP'] = new_hp
        if new_hp == 0:
            self.dfdict['User'].loc[defender, 'TS_Dead'] = datetime.strftime(datetime.now(), mydtformat)
            return 1
        else:
            return 0
    def userregenall(self):
        # hourly automatic regen for all
        # no return values
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
            self.dfdict['User'].loc[index, 'EXP'] = row['EXP'] + 20 + u_level
            # gains trophy passively
            self.dfdict['User'].loc[index, 'Trophy'] = row['Trophy'] + 1
        self.syncpend = 1
    def userrevive(self, userid):
        # revive dead user and log it
        # no return values
        self.dfdict['User'].loc[userid, 'HP'] = self.calcstats(userid, stat='HP')['HP']
        self.dfdict['User'].loc[userid, 'TS_Dead'] = ''
        self.syncpend = 1
    def userjobchange(self, user, job, job_col='Main', ignore_ts=0, is_id=0):
        # change user main or sub job
        # returns tuples to be parsed by embed function
        userrow = self.dfdict['User'].loc[user.id]
        if is_id:
            jobid = job
        elif job == 'ex':
            baserow = self.dfdict['Base'].loc[userrow['Base']]
            if baserow['Hidden'] != 'ex':
                return (0, 2)
            else:
                jobid = baserow['Main']
        else:
            dfjob = self.dfdict['Job'][self.dfdict['Job']['Hidden'] == '']
            jobid = dfjob[dfjob['Job'] == job].tail(1).index.tolist()[0]
        if job_col == 'Main':
            if ignore_ts == 0:
                if userrow['TS_Job'] != '':
                    thres = datetime.strptime(userrow['TS_Job'], mydtformat) + timedelta(hours=self.cdjob)
                    now = datetime.now()
                    if now < thres:
                        remaining = thres - now
                        return (0, 0, remaining.seconds)
            if self.dfdict['User'].loc[user.id, 'Main'] == jobid:
                return (0, 1)
            self.dfdict['User'].loc[user.id, 'Main'] = jobid
            # check if auto skill is LB
            if 'ex' in userrow['Main'] and 'ex' not in jobid:
                self.dfdict['User'].loc[user.id, 'LB_Auto'] = 'off'
            # reset sub jobs
            sub1jobid = self.dfdict['Job'].loc[jobid, 'Sub1']
            self.dfdict['User'].loc[user.id, 'Sub1'] = sub1jobid
            sub2jobid = self.dfdict['Job'].loc[jobid, 'Sub2']
            self.dfdict['User'].loc[user.id, 'Sub2'] = sub2jobid
            if ignore_ts == 0:
                self.dfdict['User'].loc[user.id, 'TS_Job'] = datetime.strftime(datetime.now(), mydtformat)
            return (1, self.dfdict['Job'].loc[sub1jobid, 'Job'], self.dfdict['Job'].loc[sub2jobid, 'Job'])
        else:
            for jcol in ('Main', 'Sub1', 'Sub2'):
                if userrow[jcol] == jobid:
                    return (0, jcol)
            self.dfdict['User'].loc[user.id, job_col] = jobid
            return (1,)
    def userbasechange(self, user, base):
        # change base
        # returns string directly to be encased in excecution
        desc_list = []
        baserow = self.dfdict['Base'].loc[base]
        userrow = self.dfdict['User'].loc[user.id]
        thres = datetime.strptime(userrow['TS_Base'], mydtformat) + timedelta(hours=self.cdbase)
        now = datetime.now()
        if now < thres:
            remaining = thres - now
            return f"{remaining.seconds // 3600} hours {remaining.seconds % 3600 // 60} minutes left before {user.name} can change base."
        if userrow['Base'] == base:
            return f"{user.name}, it is your current base."
        else:
            # check if EX
            if baserow['Hidden'] == 'ex':
                exdict = self.unlock_parse(userrow['EX_Unlock'])
                if baserow['Main'] not in exdict.keys():
                    return f"Unlock the EX base first with `=char exbase unlock {base}`."
                self.dfdict['User'].loc[user.id, 'EX_Up'] = exdict[baserow['Main']]
                if exdict[baserow['Main']] == self.upgradecap:
                    desc_list.append(f"{user.name} base now changed to {base} (MAX).")
                else:
                    desc_list.append(f"{user.name} base now changed to {base} (+{exdict[baserow['Main']]}).")
                if 'ex' not in userrow['Main']:
                    desc_list.append(f"Change into unique job with `=char main ex`.")
            else:
                self.dfdict['User'].loc[user.id, 'EX_Up'] = 0
                desc_list.append(f"{user.name} base now changed to {base}.")
            # check if previous job is unique
            if 'ex' in userrow['Main']:
                result_tup = self.userjobchange(user, baserow['Main'], ignore_ts=1, is_id=1)
                desc_list.append(f"Main job now changed to {self.dfdict['Job'].loc[baserow['Main'], 'Job']}.")
                desc_list.append(f"Sub jobs now changed to {result_tup[1]} and {result_tup[2]}.")
            self.dfdict['User'].loc[user.id, 'Base'] = base
            self.dfdict['User'].loc[user.id, 'TS_Base'] = datetime.strftime(datetime.now(), mydtformat)
        self.syncpend = 1
        return '\n'.join(desc_list)
    def userstart(self, user, base):
        # start a user
        # returns string directly to be encased in excecution
        desc_list = []
        baserow = self.dfdict['Base'].loc[base]
        new_user = {
            'Base': base,
            'HP': baserow['HP'],
            'AP': baserow['AP'],
            'EXP': 0,
            'Trophy': 100,
            'Main': baserow['Main'],
            'Sub1': self.dfdict['Job'].loc[baserow['Main'], 'Sub1'],
            'Sub2': self.dfdict['Job'].loc[baserow['Main'], 'Sub2'],
            'LB': 0,
            'Gil': 0,
            'TS_Base': datetime.strftime(datetime.now(), mydtformat),
            'I_Thres': 50,
            'I_Auto': 'off',
            'LB_Auto': 'off',
            'i4': 10,
            'EX_Up': 0,
            'E_Up': 0,
        }
        for index in self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item'].index:
            if index not in new_user.keys():
                new_user[index] = 0
        userrow = pd.Series(data=new_user.values(), index=new_user.keys(), name=user.id)
        self.dfdict['User'] = self.dfdict['User'].append(userrow).fillna('')
        desc_list.append(f"{user.name} registered with {base}.")
        desc_list.append(f"Default job is {self.dfdict['Job'].loc[baserow['Main'], 'Job']} (check `=char job`).")
        self.syncpend = 1
        return '\n'.join(desc_list)
    def raiddamage(self, raid, damage):
        # function for a raid to take damage
        # returns tuple of item drops if dead, otherwise returns 0
        raidrow = self.dfdict['Raid'].loc[raid]
        self.dfdict['Raid'].loc[raid, 'HP'] = int(max(raidrow['HP'] - damage, 0))
        # if kill
        if self.dfdict['Raid'].loc[raid, 'HP'] == 0:
            # item drop
            drop_level = 0
            for k in self.drop_rate.keys():
                if isinstance(k, str):
                    continue
                if k > raidrow['Level']:
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
            if raid == raidrow['Base']:
                if raidrow['Level'] < self.raidcap:
                    self.dfdict['Raid'].loc[raid, 'Level'] = raidrow['Level'] + 1
                else:
                    self.dfdict['Raid'].loc[raid, 'Level'] = self.raidcap2 + 1
            elif '2' in raid:
                if raidrow['Level'] < self.raidcap2:
                    self.dfdict['Raid'].loc[raid, 'Level'] = raidrow['Level'] + 1
                else:
                    self.dfdict['Raid'].loc[raid, 'Level'] = self.raidcap3 + 1
            else:
                if raidrow['Level'] < self.raidcap3:
                    self.dfdict['Raid'].loc[raid, 'Level'] = raidrow['Level'] + 1
                else:
                    self.dfdict['Raid'].loc[raid, 'Level'] = 0
            self.dfdict['Raid'].loc[raid, 'HP'] = self.calcstats(raid, usertype='R', stat='HP')['HP']
            return item_drop
        else:
            return 0
    def raidattack(self, user, raid, zero_attack=0):
        # perform an attack between an user and a raid
        # returns tuples to be parsed by other functions
        userrow = self.dfdict['User'].loc[user]
        if userrow['A_Skill'] != '':
            a_skilltup = (userrow['A_Skill'], userrow['A_Potency'])
        else:
            a_skilltup = None
        damage, hitrate, raid_damage, raid_hitrate = self.calcdamage(user, raid, a_skilltup=a_skilltup, counter=1, raid=1)
        # check attack criteria
        if userrow['HP'] == 0:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'You are dead!')
        elif userrow['AP'] < self.attack_apcost:
            return (0, damage, hitrate, raid_damage, raid_hitrate, 'Not enough AP!')
        elif zero_attack:
            return (0, damage, hitrate, raid_damage, raid_hitrate)
        else:
            # use item
            item_use = 0
            u_hp = self.calcstats(user, stat='HP')['HP']
            hp_perc = userrow['HP'] / u_hp
            if userrow['I_Auto'] != 'off' and hp_perc < userrow['I_Thres'] / 100:
                skillrow = self.dfdict['Skill'].loc[userrow['I_Auto']]
                while self.dfdict['User'].loc[user, userrow['I_Auto']] > 0:
                    item_use += self.infoitem(user, skillrow.name)
                    if self.dfdict['User'].loc[user, 'HP'] / u_hp >= userrow['I_Thres'] / 100:
                        break
                userrow = self.dfdict['User'].loc[user]
            # use lb
            lb_use = 0
            if userrow['LB_Auto'] != 'off' and userrow['LB'] == 100:
                if userrow['LB_Auto'] == 'ex':
                    skillrow = self.dfdict['Skill'].loc[userrow['Main']]
                else:
                    skillrow = self.dfdict['Skill'].loc[userrow['LB_Auto']]
                if userrow['A_Skill'] == '' or self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                    lb_use = self.infoskill(user, skillrow.name, argop=2)
                    userrow = self.dfdict['User'].loc[user]
                    if not self.dfdict['Skill'].loc[skillrow.name, 'Healing']:
                        # recalculate damage and hit rate
                        a_skilltup = (userrow['A_Skill'], userrow['A_Potency'])
                        damage, hitrate, raid_damage, raid_hitrate = self.calcdamage(user, raid, a_skilltup=a_skilltup, counter=1, raid=1)
            self.userconsumeduration(user)
            # consume AP
            self.dfdict['User'].loc[user, 'AP'] = int(userrow['AP'] - self.attack_apcost)
            # LB gain
            u_level = self.calclevel(userrow['EXP'])
            r_level = self.dfdict['Raid'].loc[raid, 'Level']
            if r_level > u_level:
                lb_gain = 20
            else:
                lb_gain = 10
            lb_gain = min(100 - userrow['LB'], lb_gain)
            self.dfdict['User'].loc[user, 'LB'] = userrow['LB'] + lb_gain
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
            self.dfdict['User'].loc[user, 'EXP'] = userrow['EXP'] + exp_gain
            # Gil gain
            self.dfdict['User'].loc[user, 'Gil'] = userrow['Gil'] + self.attack_apcost
            # raid counter attack
            if raid_hitrate > 1:
                raid_hit = 1 + ((raid_hitrate - 1) > random.random())
            else:
                raid_hit = raid_hitrate > random.random()
            raid_kill = self.userdamage(user, raid_damage * raid_hit)
            return (1, damage, hitrate, raid_damage, raid_hitrate, hit, kill, raid_hit, raid_kill, exp_gain, lb_use, item_use)
    def towergiveup(self, user):
        userrow = self.dfdict['User'].loc[user.id]
        if userrow['Tower'] == '':
            return f"{user.name} does not have an active tower challenge."
        else:
            self.dfdict['User'].loc[user.id, 'Tower'] = ''
            self.syncpend = 1
            return f"{user.name} gave up the active tower challenge."
    ############################
    # discord embed generators #
    ############################
    def helpmanual(self, kw=''):
        # generate help manual
        embed = discord.Embed()
        kw = kw.lower().rstrip('s').replace('char', 'character').replace('exbase', 'base').replace('refine', 'item')
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
            if index in self.gacha_rate.keys():
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
    def listexbase(self, user=None):
        # generate embed of list of available ex bases
        embed = discord.Embed()
        if user == None:
            embed.title = 'List of EX Bases'
        else:
            embed.title = f"List of EX Bases ({user.name})"
        embed.description = '`=charhelp base` for more info.'
        base_count = 0
        base_list = []
        if user != None:
            exdict = self.unlock_parse(self.dfdict['User'].loc[user.id, 'EX_Unlock'])
        else:
            exdict = dict()
        for index, row in self.dfdict['Base'][self.dfdict['Base']['Hidden'] == 'ex'].iterrows():
            base_str = ''
            base_str += f"{index}"
            if row['Main'] in exdict.keys():
                if exdict[row['Main']] == self.upgradecap:
                    base_str += f":star: (MAX) "
                else:
                    base_str += f":star: (+{exdict[row['Main']]}) "
            base_list.append(base_str)
            base_count += 1
            if base_count % 8 == 0:
                embed.add_field(name='-', value='\n'.join(base_list))
                base_list = []
        if len(base_list) > 0:
            embed.add_field(name='-', value='\n'.join(base_list))
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
            if raid_count % 8 == 0:
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
            if job_count % 12 == 0:
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
        buff_list = []
        debuff_list = []
        healing_list = []
        for _, row in df.iterrows():
            if row['Healing']:
                healing_list.append(f"**{row['Skill']}**\n - Recovers `{row['Sub']*100:.0f}%` or `{row['Main']*100:.0f}%` of Max HP.")
            elif row['Ally'] == 1:
                buff_list.append(f"**{row['Skill']}**\n - Target {row['Stat']} `x{row['Sub']}` or `x{row['Main']}` during battle.")
            else:
                debuff_list.append(f"**{row['Skill']}**\n - Enemy {row['Stat']} `x{row['Sub']}` or `x{row['Main']}` during battle.")
        embed.add_field(name='Buffs', value='\n'.join(buff_list), inline=False)
        embed.add_field(name='Debuffs', value='\n'.join(debuff_list), inline=False)
        embed.add_field(name='Healing', value='\n'.join(healing_list), inline=False)
        return embed
    def listrefine(self):
        # generate embed of list of available items
        embed = discord.Embed()
        embed.title = 'List of Refine Options'
        embed.description = f"`=charhelp item` for more info. Note that refining costs {self.refinecost} Arcanas."
        for refine_mat, refine_tup in self.refine_rate.items():
            matname = self.dfdict['Skill'].loc[refine_mat, 'Skill']
            refinename = self.dfdict['Skill'].loc[refine_tup[1], 'Skill']
            embed.add_field(name=matname, value=f"Convert {refine_tup[0]} into {refine_tup[2]} {refinename}(s).", inline=False)
        return embed
    def listitem(self):
        # generate embed of list of available items
        embed = discord.Embed()
        embed.title = 'List of Items'
        embed.description = '`=charhelp item` for more info. Note: AP% recovery caps at Max AP of 100.'
        df = self.dfdict['Skill'][self.dfdict['Skill']['Hidden'] == 'item']
        skill_list = []
        skill_count = 0
        for index, row in df.iterrows():
            if index == 'i6':
                skill_list.append(f"**{row['Skill']}**\n - Valuable rare item related to EX bases.")
            elif index == 'i7':
                skill_list.append(f"**{row['Skill']}**\n - Valuable rare item related to espers.")
            elif index == 'i8':
                skill_list.append(f"**{row['Skill']}**\n - Material required for refining items.")
            else:
                skill_list.append(f"**{row['Skill']}**\n - Restores {row['Main'] * 100:.0f}% {row['Stat']}.")
            skill_count += 1
            if skill_count % 10 == 0:
                embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
                skill_list = []
        if len(skill_list) > 0:
            embed.add_field(name='-', value='\n'.join(skill_list), inline=False)
        return embed
    def listesper(self, user=None):
        # generate embed of list of available espers
        embed = discord.Embed()
        if user == None:
            embed.title = 'List of Espers'
        else:
            embed.title = f"List of Espers ({user.name})"
        embed.description = '`=charhelp esper` for more info.'
        esper_list = []
        if user != None:
            esperdict = self.unlock_parse(self.dfdict['User'].loc[user.id, 'E_Unlock'])
        else:
            esperdict = dict()
        cur_cost = self.unlockcost
        for index, row in self.dfdict['Esper'].iterrows():
            if row['Cost'] != cur_cost:
                embed.add_field(name=f"Cost: {cur_cost}", value='\n'.join(esper_list))
                esper_list = []
                cur_cost = row['Cost']
            esper_str = ''
            esper_str += f"**{row['Esper']}**"
            if index in esperdict.keys():
                if esperdict[index] == self.upgradecap:
                    esper_str += f":star: (MAX)"
                else:
                    esper_str += f":star: (+{esperdict[index]})"
            esper_str += '\n - '
            esper_str += f" Converts {row['S_Stat']} into {row['B1_Stat']}"
            if row['B2_Stat'] != '':
                esper_str += f" and {row['B2_Stat']}"
            esper_list.append(esper_str)
        embed.add_field(name=f"Cost: {cur_cost}", value='\n'.join(esper_list))
        return embed
    def listtower(self, user, unfinished=0):
        # generate embed of list of available tower floors
        embed = discord.Embed()
        embed.title = f"Tower ({user.name})"
        embed.description = f"`=charhelp tower` for more info. Current up to floor {max(self.tower_tuples.keys())}."
        userrow = self.dfdict['User'].loc[user.id]
        recorddict = self.tower_parse(userrow['T_Record'])
        if len(recorddict) == 0:
            next = 1
        else:
            next = max(recorddict.keys()) + 1
        tower_count = 0
        for floor, tower_tup in self.tower_tuples.items():
            if floor > next:
                continue
            stars_count = 0
            field_name = f"{floor} - {tower_tup[2]}"
            if floor < next:
                field_name += ' :star:'
                stars_count += 1
                if recorddict[floor][0] <= tower_tup[5][-1][0]:
                    field_name += ':star:'
                    stars_count += 1
                if recorddict[floor][1] <= tower_tup[6][-1][0]:
                    field_name += ':star:'
                    stars_count += 1
            if floor == userrow['Tower']:
                field_name = ':crossed_swords: ' + field_name
            if unfinished == 1 and stars_count == 3:
                continue
            else:
                tower_count += 1
                embed.add_field(name=field_name, value=f"Level: {tower_tup[0]} | AP: {tower_tup[1]}", inline=False)
            if unfinished == 0 and tower_count == 10:
                break
        if unfinished == 1 and tower_count == 0:
            embed.add_field(name='Congratulations!', value='You have completed all available tower missions.')
        return embed
    def infotower(self, user, floor):
        # generate info embed of a tower floor
        embed = discord.Embed()
        tower_tup = self.tower_tuples[floor]
        embed.title = f"{floor} - {tower_tup[2]} ({user.name})"
        desc_list = []
        userrow = self.dfdict['User'].loc[user.id]
        recorddict = self.tower_parse(userrow['T_Record'])
        if len(recorddict) == 0:
            next = 1
        else:
            next = max(recorddict.keys()) + 1
        if floor > next:
            desc_list.append(f"You cannot challenge this floor yet.")
        elif floor == next:
            desc_list.append(f"This is your next floor.")
        else:
            desc_list.append(f"You cleared this floor.")
        desc_list.append(f"Level: {tower_tup[0]} | AP: {tower_tup[1]}")
        if tower_tup[3][1] == 0:
            esper = self.dfdict['Esper'].loc[tower_tup[3][0], 'Esper']
            desc_list.append(f"First Clear: {esper} Esper Unlock")
        else:
            item = self.dfdict['Skill'].loc[tower_tup[3][0], 'Skill']
            desc_list.append(f"First Clear: {tower_tup[3][1]} {item}(s)")
        item = self.dfdict['Skill'].loc[tower_tup[4][0], 'Skill']
        desc_list.append(f"Repeat Clear: {tower_tup[4][1]} {item}(s)")
        desc_list.append(f"Hint: {tower_tup[7]}")
        embed.description = '\n'.join(desc_list)
        # stats where available
        if floor in self.tower_stats.keys():
            towerdict = self.calcstats(floor, usertype='T')
            field_list = [f"HP: {self.tower_stats[floor][0]}"]
            for statname, statvalue in towerdict.items():
                field_list.append(f"{statname}: {statvalue}")
            embed.add_field(name='Stats', value='\n'.join(field_list))
        field_list = []
        # turn taken missions
        for field_tup in tower_tup[5]:
            item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
            field_str = f"{field_tup[0]} T: {field_tup[2]} {item}(s)"
            if floor in recorddict.keys():
                if recorddict[floor][0] <= field_tup[0]:
                    field_str += ' :star:'
            field_list.append(field_str)
        embed.add_field(name='Turn Rewards', value='\n'.join(field_list))
        field_list = []
        # damage taken missions
        for field_tup in tower_tup[6]:
            item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
            field_str = f"{field_tup[0]} HP: {field_tup[2]} {item}(s)"
            if floor in recorddict.keys():
                if recorddict[floor][1] <= field_tup[0]:
                    field_str += ' :star:'
            field_list.append(field_str)
        embed.add_field(name='Damage Rewards', value='\n'.join(field_list))
        embed.set_thumbnail(url=tower_tup[8])
        return embed
    def infochallengetower(self, user, start=None):
        # generate info embed of tower challenge
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user.id]
        recorddict = self.tower_parse(userrow['T_Record'])
        desc_list = []
        if len(recorddict) == 0:
            next = 1
        else:
            next = max(recorddict.keys()) + 1
        if start == None and userrow['Tower'] == '':
            embed.description = 'Choose a floor to start first. (`=char tower`)'
            return embed
        elif (start == None or start == userrow['Tower']) and  userrow['Tower'] != '':
            floor = userrow['Tower']
            tower_tup = self.tower_tuples[floor]
        elif userrow['Tower'] != '':
            embed.description = 'You already started another floor.'
            return embed
        else:
            floor = start
            tower_tup = self.tower_tuples[floor]
            if floor > next:
                embed.description = f"You cannot challenge this floor yet."
                return embed
            elif userrow['AP'] < tower_tup[1]:
                embed.description = f"You need {tower_tup[1]} AP to challenge this floor. Your current AP is {userrow['AP']}."
                return embed
            self.dfdict['User'].loc[user.id, 'AP'] = userrow['AP'] - tower_tup[1]
            self.dfdict['User'].loc[user.id, 'Gil'] = userrow['Gil'] + tower_tup[1]
            self.dfdict['User'].loc[user.id, 'Tower'] = floor
            desc_list.append(f"You spent {tower_tup[1]} AP to challenge this floor. Your current AP is {userrow['AP'] - tower_tup[1]}")
            self.syncpend = 1
        embed.title = f"{user.name} VS {tower_tup[2]}"
        if floor in (5, 8, 10):
            if floor == 5:
                d_skilltup = ('t01', 'Main')
            elif floor in (8, 25):
                d_skilltup = ('t04', 'Main')
            elif floor == 10:
                d_skilltup = ('t02', 'Main')
            desc_list.append(f"{tower_tup[2]} casted {self.dfdict['Skill'].loc[d_skilltup[0], 'Skill']}.")
        elif floor == 7:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Invincible Moon.")
        elif floor == 11:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Disintegration.")
        elif floor == 14:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Ruby Light.")
        elif floor == 17:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Pain.")
        elif floor == 18:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Tidal Wave.")
        elif floor == 20:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted 9999 Needles.")
        elif floor == 23:
            d_skilltup = None
            desc_list.append(f"{tower_tup[2]} casted Ochu Dance.")
        elif floor == 24:
            desc_list.append(f"{tower_tup[2]} casted Mindblast.")
            userdict = self.calcstats(user.id)
            if userdict['DEF'] + userdict['SPR'] < 3000:
                d_skilltup = ('t05', 'Main')
            else:
                desc_list.append(f"But it failed.")
                d_skilltup = None
        else:
            d_skilltup = None
        # calculate damage and hit rate
        if userrow['LB_Auto'] != 'off':
            if userrow['LB_Auto'] == 'ex':
                skillrow = self.dfdict['Skill'].loc[userrow['Main']]
            else:
                skillrow = self.dfdict['Skill'].loc[userrow['LB_Auto']]
            if skillrow.name == self.dfdict['Job'].loc[userrow['Main'], 'Skill'] or 'ex' in skillrow.name:
                potency = 'Main'
            else:
                potency = 'Sub'
            desc_list.append(f"{user.name} casted {skillrow['Skill']}.")
            a_skilltup = (skillrow.name, potency)
        else:
            a_skilltup = None
        if floor == 12:
            desc_list.append(f"{tower_tup[2]} casted Dispel.")
        damage, hitrate, counter_damage, counter_hitrate = self.calcdamage(user.id, floor, a_skilltup=a_skilltup, d_skilltup=d_skilltup, raid=2, counter=1)
        desc_list.append(f"*{tower_tup[2]} has {min(counter_hitrate, 1) * 100:.0f}% of doing {counter_damage} damage.*")
        desc_list.append(f"*{tower_tup[2]} has {max(counter_hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
        desc_list.append(f"*{user.name} has {min(max(hitrate, 0), 1) * 100:.0f}% of doing {damage} damage.*")
        desc_list.append(f"*{user.name} has {max(hitrate - 1, 0) * 100:.0f}% of landing a critical hit.*")
        embed.description = '\n'.join(desc_list)
        # get their HP
        userhp = self.calcstats(user.id, stat='HP')['HP']
        towerhp = self.tower_stats[floor][0]
        turn_taken = 0
        damage_taken = 0
        # 4 phases with 5 battles each
        for phase in range(1, 5, 1):
            userhp_current = userhp
            field_name = f"Phase {phase}"
            field_list = [f"{tower_tup[2]} HP `{towerhp}`"]
            for _ in range(5):
                turn_taken += 1
                # tower boss attacks first
                if floor in (8, 25) and phase == 1:
                    field_list.append(f"{tower_tup[2]} is moving closer...") # Tonberry phase 1
                elif floor == 20 and phase == 1:
                    field_list.append(f"{tower_tup[2]} is watching you intently...") # Cactuar phase 1
                else:
                    if counter_hitrate > 1:
                        counter_hit = 1 + ((counter_hitrate - 1) > random.random())
                    else:
                        counter_hit = counter_hitrate > random.random()
                    tower_damage = counter_damage * counter_hit
                    if counter_hit == 2:
                        field_list.append(f"{tower_tup[2]} landed a critical hit with {tower_damage} damage.")
                    elif counter_hit == 1:
                        field_list.append(f"{tower_tup[2]} successfully attacked with {tower_damage} damage.")
                    else:
                        field_list.append(f"{tower_tup[2]} missed.")
                    userhp_current = max(userhp_current - tower_damage, 0)
                    damage_taken += tower_damage
                    if userhp_current == 0:
                        break
                # user's turn
                if floor == 14 and hitrate == -1:
                    userhp_current = max(userhp_current - damage, 0)
                    damage_taken += damage
                    field_list.append(f"Your magic bounced off {tower_tup[2]}, hitting yourself with {damage} damage.")
                else:
                    if hitrate > 1:
                        hit = 1 + ((hitrate - 1) > random.random())
                    else:
                        hit = hitrate > random.random()
                    if floor == 18 and hit == 1: # Leviathan
                        user_damage = 0
                    else:
                        user_damage = damage * hit
                    if hit == 2:
                        field_list.append(f"You landed a critical hit with {user_damage} damage.")
                    elif hit == 1:
                        field_list.append(f"You successfully attacked with {user_damage} damage.")
                    else:
                        field_list.append(f"You missed.")
                    towerhp = max(towerhp - user_damage, 0)
                if towerhp == 0:
                    break
                if floor == 17: # Anima pain
                    pain_damage = self.tower_stats[floor][0] - towerhp
                    field_list.append(f"{tower_tup[2]} inflicted you with her pain, dealing {pain_damage} damage.")
                    userhp_current = max(userhp_current - pain_damage, 0)
                    if userhp_current == 0:
                        break
                elif floor == 19: # Demon Wall
                    field_list.append(f"{tower_tup[2]} is drawing closer...")
            if userhp_current == 0 or towerhp == 0:
                break
            elif floor == 9:
                towerhp = 0
                field_list.append(f"{tower_tup[2]} fled.")
                break
            elif floor == 10:
                towerhp = 0
                field_list.append(f"{tower_tup[2]} stomped away in rage.")
                break
            elif floor == 17:
                towerhp = 0
                field_list.append(f"{tower_tup[2]} seemed pleased and faded back into the abyss.")
                break
            elif floor == 19:
                userhp_current = 0
                field_list.append(f"{tower_tup[2]} crushed you! Game Over!")
                break
            elif floor == 21:
                towerhp = 0
                field_list.append(f"{tower_tup[2]} recognised you as a friend and became dormant.")
                break
            elif floor == 22:
                towerhp = 0
                field_list.append(f"{tower_tup[2]} was pleased at your endurance and declared you winner.")
                break
            embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        if turn_taken < 20:
            embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        field_name = 'Result'
        field_list = []
        # Check results
        if towerhp > 0:
            field_list.append(f"You failed.")
            if userhp_current == 0:
                field_list.append(f"You are KO-ed.")
            else:
                field_list.append(f"Turn limit is up.")
        else:
            field_list.append('You won.')
            self.dfdict['User'].loc[user.id, 'Tower'] = ''
            if floor == next:
                recorddict[floor] = (turn_taken, damage_taken)
                if tower_tup[3][1] == 0:
                    esper = self.dfdict['Esper'].loc[tower_tup[3][0], 'Esper']
                    esperdict = self.unlock_parse(userrow['E_Unlock'])
                    esperdict[tower_tup[3][0]] = 0
                    self.dfdict['User'].loc[user.id, 'E_Unlock'] = self.unlock_parse(esperdict, reverse=1)
                    field_list.append(f"You unlocked esper {esper}. :star:")
                else:
                    self.dfdict['User'].loc[user.id, tower_tup[3][0]] = userrow[tower_tup[3][0]] + tower_tup[3][1]
                    item = self.dfdict['Skill'].loc[tower_tup[3][0], 'Skill']
                    field_list.append(f"You obtained {tower_tup[3][1]} {item}(s).")
                # new clear
                for field_tup in tower_tup[5]:
                    if turn_taken <= field_tup[0]:
                        item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
                        self.dfdict['User'].loc[user.id, field_tup[1]] = self.dfdict['User'].loc[user.id, field_tup[1]] + field_tup[2]
                        field_list.append(f"You cleared within {field_tup[0]} turns. You obtained {field_tup[2]} {item}(s).")
                for field_tup in tower_tup[6]:
                    if damage_taken <= field_tup[0]:
                        item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
                        self.dfdict['User'].loc[user.id, field_tup[1]] = self.dfdict['User'].loc[user.id, field_tup[1]] + field_tup[2]
                        field_list.append(f"You took less than {field_tup[0]} damage. You obtained {field_tup[2]} {item}(s).")
            else:
                best_turn_taken, best_damage_taken = recorddict[floor]
                self.dfdict['User'].loc[user.id, tower_tup[4][0]] = userrow[tower_tup[4][0]] + tower_tup[4][1]
                item = self.dfdict['Skill'].loc[tower_tup[4][0], 'Skill']
                field_list.append(f"You obtained {tower_tup[4][1]} {item}(s).")
                # old clear, check if best results
                if turn_taken < best_turn_taken:
                    for field_tup in tower_tup[5]:
                        if turn_taken <= field_tup[0] < best_turn_taken:
                            item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
                            self.dfdict['User'].loc[user.id, field_tup[1]] = self.dfdict['User'].loc[user.id, field_tup[1]] + field_tup[2]
                            field_list.append(f"You cleared within {field_tup[0]} turns. You obtained {field_tup[2]} {item}(s).")
                    best_turn_taken = turn_taken
                if damage_taken < best_damage_taken:
                    for field_tup in tower_tup[6]:
                        if damage_taken <= field_tup[0] < best_damage_taken:
                            item = self.dfdict['Skill'].loc[field_tup[1], 'Skill']
                            self.dfdict['User'].loc[user.id, field_tup[1]] = self.dfdict['User'].loc[user.id, field_tup[1]] + field_tup[2]
                            field_list.append(f"You took less than {field_tup[0]} damage. You obtained {field_tup[2]} {item}(s).")
                    best_damage_taken = damage_taken
                recorddict[floor] = (best_turn_taken, best_damage_taken)
            self.dfdict['User'].loc[user.id, 'T_Record'] = self.tower_parse(recorddict, reverse=1)
            self.syncpend = 1
        embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        embed.colour = self.colours[self.dfdict['Base'].loc[userrow['Base'], 'Element'].lower()]
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
                    desc_list = ['Success! Your jobs are now the following:']
                    if v == 'ex':
                        userrow = self.dfdict['User'].loc[user.id]
                        jobid = self.dfdict['Base'].loc[userrow['Base'], 'Main']
                        if userrow['EX_Up'] == self.upgradecap:
                            desc_list.append(f"Main: {self.dfdict['Job'].loc[jobid, 'Job']} (MAX)")
                        else:
                            desc_list.append(f"Main: {self.dfdict['Job'].loc[jobid, 'Job']} (+{userrow['EX_Up']})")
                    else:
                        desc_list.append(f"Main: {v}")
                    desc_list.append(f"Sub1: {result_tup[1]}")
                    desc_list.append(f"Sub2: {result_tup[2]}")
                    self.syncpend = 1
                elif result_tup[1] == 1:
                    desc_list.append('It is already your current main job.')
                elif result_tup[1] == 2:
                    desc_list.append('Your current base does not have unique job.')
                else:
                    desc_list.append(f"{result_tup[2] // 60} minutes left before you can change your main job.")
            else:
                result_tup = self.userjobchange(user, v, k)
                if result_tup[0]:
                    desc_list.append(f"Success! Your {k} is now {v}.")
                    self.syncpend = 1
                else:
                    desc_list.append(f"{v} is already your {result_tup[1]} job!")
        embed.description = '\n'.join(desc_list)
        return embed
    def infoesperchange(self, user, esper):
        # generate info embed of esper change
        embed = discord.Embed()
        embed.title = f"{user.name} Esper Change"
        userrow = self.dfdict['User'].loc[user.id]
        if esper == userrow['Esper']:
            embed.description = 'It is already your current esper.'
            return embed
        desc_list = []
        if esper == 'off':
            self.dfdict['User'].loc[user.id, 'Esper'] = ''
            self.dfdict['User'].loc[user.id, 'E_Up'] = 0
            desc_list.append(f"You now unequipped your esper.")
        else:
            esperid = self.dfdict['Esper'][self.dfdict['Esper']['Esper'] == esper].tail(1).index.tolist()[0]
            esperrow = self.dfdict['Esper'].loc[esperid]
            thumbnail_url = esperrow['Url']
            if thumbnail_url != '':
                embed.set_thumbnail(url=thumbnail_url)
            embed.colour = self.colours[esperrow['Element'].lower()]
            esperdict = self.unlock_parse(userrow['E_Unlock'])
            if esperid not in esperdict.keys():
                if esperrow['Cost'] > self.unlockcost:
                    desc_list.append(f"You need to unlock it by clearing its corresponding tower floor first.")
                else:
                    desc_list.append(f"You need to unlock it first using {esperrow['Cost']} Auracites.")
                    desc_list.append(f"Type `=char esper unlock {esper}` to unlock.")
            else:
                self.dfdict['User'].loc[user.id, 'Esper'] = esperid
                self.dfdict['User'].loc[user.id, 'E_Up'] = esperdict[esperid]
                if esperdict[esperid] == self.upgradecap:
                    desc_list.append(f"Your esper is now changed to {esper} (MAX).")
                else:
                    desc_list.append(f"Your esper is now changed to {esper} (+{esperdict[esperid]}).")
        embed.description = '\n'.join(desc_list)
        self.syncpend = 1
        return embed
    def infoupesper(self, user, esper, unlock=0):
        # generate info embed of unlocking or upgrading ex base
        embed = discord.Embed()
        embed.title = f"{user.name} - {esper}"
        userrow = self.dfdict['User'].loc[user.id]
        esperid = self.dfdict['Esper'][self.dfdict['Esper']['Esper'] == esper].tail(1).index.tolist()[0]
        esperrow = self.dfdict['Esper'].loc[esperid]
        thumbnail_url = esperrow['Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed.colour = self.colours[esperrow['Element'].lower()]
        esperdict = self.unlock_parse(userrow['E_Unlock'])
        desc_list = []
        if esperid in esperdict.keys():
            if unlock:
                embed.description = f"You already unlocked {esper}."
                return embed
            elif esperdict[esperid] == self.upgradecap:
                embed.description = f"Your {esper} cannot be upgraded any further."
                return embed
            else:
                upcost = self.calcupcost(esperdict[esperid] + 1, unlockcost=esperrow['Cost'])
                if userrow['i7'] < upcost:
                    desc_list.append(f"You need {upcost} Auracites to upgrade.")
                    desc_list.append(f"You do not have enough Auracites.")
                else:
                    esperdict[esperid] = esperdict[esperid] + 1
                    if userrow['Esper'] == esperid: # check if currently equipped
                        self.dfdict['User'].loc[user.id, 'E_Up'] = esperdict[esperid]
                    self.dfdict['User'].loc[user.id, 'i7'] = userrow['i7'] - upcost
                    self.dfdict['User'].loc[user.id, 'E_Unlock'] = self.unlock_parse(esperdict, reverse=1)
                    self.syncpend = 1
                    desc_list.append(f"You spent {upcost} Auracites.")
                    if esperdict[esperid] == self.upgradecap:
                        desc_list.append(f"Your {esper} is now MAX.")
                        desc_list.append(f"Your {esper} now cannot be upgraded any further.")
                    else:
                        upcost = self.calcupcost(esperdict[esperid] + 1, unlockcost=esperrow['Cost'])
                        desc_list.append(f"Your {esper} is now +{esperdict[esperid]} (Next: {upcost} Auracites).")
        else:
            if esperrow['Cost'] > self.unlockcost:
                embed.description = f"You need to unlock it by clearing its corresponding tower floor first."
                return embed
            elif unlock == 0:
                embed.description = f"Type `=char esper unlock {esper}` to unlock first."
                return embed
            elif userrow['i7'] < esperrow['Cost']:
                desc_list.append(f"You need {esperrow['Cost']} Auracites to unlock.")
                desc_list.append(f"You do not have enough Auracites.")
            else:
                esperdict[esperid] = 0
                self.dfdict['User'].loc[user.id, 'i7'] = userrow['i7'] - esperrow['Cost']
                self.dfdict['User'].loc[user.id, 'E_Unlock'] = self.unlock_parse(esperdict, reverse=1)
                self.syncpend = 1
                upcost = self.calcupcost(esperdict[esperid] + 1, unlockcost=esperrow['Cost'])
                desc_list.append(f"You spent {esperrow['Cost']} Auracites to unlock {esper} (Next: {upcost} Auracites).")
                desc_list.append(f"Note: type `=char esper change {esper}` to change esper.")
        embed.description = '\n'.join(desc_list)
        embed.add_field(name='Auracites left', value=str(self.dfdict['User'].loc[user.id, 'i7']))
        return embed
    def infoupexbase(self, user, base, unlock=0):
        # generate info embed of unlocking or upgrading ex base
        embed = discord.Embed()
        embed.title = f"{user.name} - {base}"
        userrow = self.dfdict['User'].loc[user.id]
        baserow = self.dfdict['Base'].loc[base]
        thumbnail_url = baserow['Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed.colour = self.colours[baserow['Element'].lower()]
        exdict = self.unlock_parse(userrow['EX_Unlock'])
        desc_list = []
        if baserow['Main'] in exdict.keys():
            if unlock:
                embed.description = f"You already unlocked {base}."
                return embed
            elif exdict[baserow['Main']] == self.upgradecap:
                embed.description = f"Your {base} cannot be upgraded any further."
                return embed
            else:
                upcost = self.calcupcost(exdict[baserow['Main']] + 1)
                if userrow['i6'] < upcost:
                    desc_list.append(f"You need {upcost} Dark Matters to upgrade.")
                    desc_list.append(f"You do not have enough Dark Matters.")
                else:
                    exdict[baserow['Main']] = exdict[baserow['Main']] + 1
                    if userrow['Base'] == base: # check if currently equipped
                        self.dfdict['User'].loc[user.id, 'EX_Up'] = exdict[baserow['Main']]
                    self.dfdict['User'].loc[user.id, 'i6'] = userrow['i6'] - upcost
                    self.dfdict['User'].loc[user.id, 'EX_Unlock'] = self.unlock_parse(exdict, reverse=1)
                    self.syncpend = 1
                    desc_list.append(f"You spent {upcost} Dark Matters.")
                    if exdict[baserow['Main']] == self.upgradecap:
                        desc_list.append(f"Your {base} is now MAX.")
                        desc_list.append(f"Your {base} now cannot be upgraded any further.")
                    else:
                        upcost = self.calcupcost(exdict[baserow['Main']] + 1)
                        desc_list.append(f"Your {base} is now +{exdict[baserow['Main']]} (Next: {upcost} Dark Matters).")
        else:
            if unlock == 0:
                embed.description = f"Type `=char exbase unlock {base}` to unlock first."
                return embed
            elif userrow['i6'] < self.unlockcost:
                desc_list.append(f"You need {self.unlockcost} Dark Matters to unlock.")
                desc_list.append(f"You do not have enough Dark Matters.")
            else:
                exdict[baserow['Main']] = 0
                self.dfdict['User'].loc[user.id, 'i6'] = userrow['i6'] - self.unlockcost
                self.dfdict['User'].loc[user.id, 'EX_Unlock'] = self.unlock_parse(exdict, reverse=1)
                self.syncpend = 1
                upcost = self.calcupcost(exdict[baserow['Main']] + 1)
                desc_list.append(f"You spent {self.unlockcost} Dark Matters to unlock {base} (Next: {upcost} Dark Matters).")
                desc_list.append(f"Note: type `=char exbase change {base}` to change base.")
        embed.description = '\n'.join(desc_list)
        embed.add_field(name='Dark Matters left', value=str(self.dfdict['User'].loc[user.id, 'i6']))
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
        embed.colour = self.colours[row['Element'].lower()]
        return embed
    def infoesper(self, esper, user=None):
        # generate embed of list of available espers
        embed = discord.Embed()
        esperid = self.dfdict['Esper'][self.dfdict['Esper']['Esper'] == esper].tail(1).index.tolist()[0]
        row = self.dfdict['Esper'].loc[esperid]
        embed.title = esper
        # if existing user, display upgrade condition and cost
        if user != None:
            desc_str = user.name
            esperdict = self.unlock_parse(self.dfdict['User'].loc[user.id, 'E_Unlock'])
            if row.name in esperdict.keys():
                desc_str += ' unlocked'
                if esperdict[row.name] == self.upgradecap:
                    desc_str += ' (MAX).'
                else:
                    up_cost = self.calcupcost(esperdict[row.name] + 1, row['Cost'])
                    desc_str += f" (+{esperdict[row.name]}). `{up_cost}` Auracites to upgrade."
            else:
                if row['Cost'] > self.unlockcost:
                    desc_str += f" did not unlock. Clear the corresponding tower floor to unlock."
                else:
                    desc_str += f" did not unlock. {row['Cost']} Auracites to unlock."
            embed.description = desc_str
        field_list = []
        field_list.append(f"{row['S_Stat']}: `{row['S_MIN']}` to `{row['S_MAX']}`% of {row['S_Stat']}")
        field_list.append(f"{row['B1_Stat']}: `{row['B1_MIN']}` to `{row['B1_MAX']}`% of {row['S_Stat']}")
        if row['B2_Stat'] != '':
            field_list.append(f"{row['B2_Stat']}: `{row['B2_MIN']}` to `{row['B2_MAX']}`% of {row['S_Stat']}")
        embed.add_field(name='Stat Bonuses', value='\n'.join(field_list))
        embed.add_field(name='Cost', value=row['Cost'])
        thumbnail_url = row['Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed.colour = self.colours[row['Element'].lower()]
        return embed
    def infoexbase(self, base, user=None):
        # generate info embed of specific EX base
        embed = discord.Embed()
        row = self.dfdict['Base'].loc[base]
        embed.title = base
        # if existing user, display upgrade condition and cost
        if user != None:
            desc_str = user.name
            exdict = self.unlock_parse(self.dfdict['User'].loc[user.id, 'EX_Unlock'])
            if row['Main'] in exdict.keys():
                desc_str += ' unlocked'
                if exdict[row['Main']] == self.upgradecap:
                    desc_str += ' (MAX).'
                else:
                    up_cost = self.calcupcost(exdict[row['Main']] + 1)
                    desc_str += f" (+{exdict[row['Main']]}). `{up_cost}` Dark Matters to upgrade."
            else:
                desc_str += f" did not unlock. {self.unlockcost} Dark Matters to unlock."
            embed.description = desc_str
        # base stats field
        field_list = []
        for stat in self.statlist2:
            field_list.append(f"{stat}: `{row[stat]}`")
        jobrow = self.dfdict['Job'].loc[row['Main']]
        embed.add_field(name='Base Stats', value='\n'.join(field_list))
        # unique main job
        field_list = []
        for stat in self.statlist2:
            field_list.append(f"{stat}: `{int(jobrow[stat] / 2)}` to `{jobrow[stat]}`")
        skillrow = self.dfdict['Skill'].loc[row['Main']]
        field_list.append(f"Limit Break: {skillrow['Skill']}")
        # limit break description
        skill_desc = ''
        during_battle = 0
        if skillrow['Stat'] == 'COMBO':
            effect_list = []
            for subpotency in ('Main', 'Sub'):
                if skillrow[subpotency] == '':
                    continue
                for subskillid in skillrow[subpotency].split('/'):
                    subskillrow = self.dfdict['Skill'].loc[subskillid]
                    if subskillrow['Healing']:
                        effect_list.append('heals')
                    elif subskillrow['Ally'] > 0:
                        effect_list.append(f"self {subskillrow['Stat']} `x{subskillrow[subpotency]}`")
                        during_battle = 1
                    else:
                        effect_list.append(f"enemy {subskillrow['Stat']} `x{subskillrow[subpotency]}`")
                        during_battle = 1
            effect_str = ' and '.join(effect_list)
            if during_battle:
                effect_str += ' during battle'
        else:
            if skillrow['Healing']:
                effect_str = 'Heals.'
            elif skillrow['Ally'] > 0:
                effect_str = f"self {skillrow['Stat']} `x{skillrow['Main']}` during battle"
            else:
                effect_str = f"enemy {skillrow['Stat']} `x{skillrow['Main']}` during battle"
        field_list.append(f"({effect_str})")
        # main skill
        field_list.append(f"Main Skill: {self.dfdict['Skill'].loc[jobrow['Skill'], 'Skill']}")
        embed.add_field(name=f"Unique Main - {jobrow['Job']}", value='\n'.join(field_list))
        thumbnail_url = row['Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed.colour = self.colours[row['Element'].lower()]
        return embed
    def infouser(self, user):
        # generate info embed of specific user
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user.id]
        embed.title = user.name
        # basic info
        desc_list = []
        userdict = self.calcstats(userrow.name, stat='ALL')
        baserow = self.dfdict['Base'].loc[userrow['Base']]
        if baserow['Hidden'] == 'ex':
            desc_list.append(f"EX Base: {baserow.name}")
        else:
            desc_list.append(f"Base: {userrow['Base']}")
        if userdict['Level'] == self.levelcap:
            desc_list.append(f"Level: {userdict['Level']} (MAX)")
        else:
            desc_list.append(f"Level: {userdict['Level']}")
            desc_list.append(f"*Next Level: {self.levelexp[userdict['Level'] + 1] - userrow['EXP']} EXP*")
        desc_list.append(f"HP: {userrow['HP']}/{userdict['HP']}")
        desc_list.append(f"AP: {userrow['AP']}/{userdict['AP']}")
        if userrow['LB'] == 100:
            desc_list.append(f"LB: **MAX**")
        else:
            desc_list.append(f"LB: {userrow['LB']}%")
        if userrow['A_Skill'] != '':
            desc_list.append(f"Status: {self.dfdict['Skill'].loc[userrow['A_Skill'], 'Skill']} ({userrow['A_Duration']})")
        desc_list.append(f"Trophy: {userrow['Trophy']}")
        embed.description = '\n'.join(desc_list)
        # field of stats
        field_list = []
        for stat in self.statlist2:
            field_list.append(f"{stat}: {userdict[stat]}")
        embed.add_field(name='Stats', value='\n'.join(field_list))
        # field of current jobs
        field_list = []
        jobrow = self.dfdict['Job'].loc[userrow['Main']]
        if jobrow['Hidden'] == 'ex':
            if userrow['EX_Up'] == self.upgradecap:
                plus_str = 'MAX'
            else:
                plus_str = f"+{userrow['EX_Up']}"
            field_list.append(f"Main: {jobrow['Job']} ({plus_str})")
        else:
            field_list.append(f"Main: {jobrow['Job']}")
        for job_col in ('Sub1', 'Sub2'):
            field_list.append(f"{job_col}: {self.dfdict['Job'].loc[userrow[job_col], 'Job']}")
        if userrow['Esper'] == '':
            field_list.append(f"Esper: *off*")
        else:
            if userrow['E_Up'] == self.upgradecap:
                plus_str = 'MAX'
            else:
                plus_str = f"+{userrow['E_Up']}"
            field_list.append(f"Esper: {self.dfdict['Esper'].loc[userrow['Esper'], 'Esper']} ({plus_str})")
        if jobrow['Hidden'] == 'ex':
            field_list.append(f"Limit Break: {self.dfdict['Skill'].loc[userrow['Main'], 'Skill']}")
        skillid = self.dfdict['Job'].loc[userrow['Main'], 'Skill']
        field_list.append(f"Main Skill: {self.dfdict['Skill'].loc[skillid, 'Skill']}")
        embed.add_field(name='Setup', value='\n'.join(field_list))
        # auto setting
        field_list = []
        if userrow['LB_Auto'] != 'off':
            if userrow['LB_Auto'] == 'ex':
                field_list.append(f"LB: {self.dfdict['Skill'].loc[userrow['Main'], 'Skill']}")
            else:
                field_list.append(f"LB Skill: {self.dfdict['Skill'].loc[userrow['LB_Auto'], 'Skill']}")
        else:
            field_list.append(f"LB Skill: *off*")
        if userrow['I_Auto'] != 'off':
            field_list.append(f"Item: {self.dfdict['Skill'].loc[userrow['I_Auto'], 'Skill']} ({userrow[userrow['I_Auto']]})")
        else:
            field_list.append(f"Item: *off*")
        field_list.append(f"HP Threshold: {userrow['I_Thres']}%")
        embed.add_field(name='Auto Setting', value='\n'.join(field_list))
        # show revival timer if dead
        if userrow['HP'] == 0:
            thres = datetime.strptime(userrow['TS_Dead'], mydtformat) + timedelta(hours=engel.revivehours)
            revivaltd = thres - datetime.now()
            revivalstr = f"{revivaltd.seconds // 60 + 1} minutes remaining."
            embed.add_field(name='Revival Time', value=revivalstr, inline=False)
        # decoration
        thumbnail_url = self.dfdict['Base'].loc[userrow['Base'], 'Url']
        if thumbnail_url != '':
            embed.set_thumbnail(url=thumbnail_url)
        embed.colour = self.colours[baserow['Element'].lower()]
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
        embed.colour = self.colours[self.dfdict['Base'].loc[userrow['Base'], 'Element'].lower()]
        return embed
    def inforaid(self, raid):
        # generate info embed of specific raid
        embed = discord.Embed()
        row = self.dfdict['Raid'].loc[raid]
        embed.title = raid
        desc_list = []
        raiddict = self.calcstats(row.name, usertype='R', stat='ALL')
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
        embed.colour = self.colours[self.dfdict['Base'].loc[row['Base'], 'Element'].lower()]
        return embed
    def infoduel(self, attacker, defender):
        # generate result embed of a duel
        embed = discord.Embed()
        embed.title = f"{attacker.name} VS {defender.name}"
        # get their status sheets
        attackhp = self.calcstats(attacker.id, stat='HP')['HP']
        attackrow = self.dfdict['User'].loc[attacker.id]
        defendhp = self.calcstats(defender.id, stat='HP')['HP']
        defendrow = self.dfdict['User'].loc[defender.id]
        # calculate damage and hit rate
        desc_list = []
        if attackrow['LB_Auto'] != 'off' and defendrow['LB_Auto'] != 'off':
            if attackrow['LB_Auto'] == 'ex':
                skillrow = self.dfdict['Skill'].loc[attackrow['Main']]
            else:
                skillrow = self.dfdict['Skill'].loc[attackrow['LB_Auto']]
            if skillrow.name == self.dfdict['Job'].loc[attackrow['Main'], 'Skill'] or 'ex' in skillrow.name:
                potency = 'Main'
            else:
                potency = 'Sub'
            desc_list.append(f"{attacker.name} casted {skillrow['Skill']}.")
            a_skilltup = (skillrow.name, potency)
            if defendrow['LB_Auto'] == 'ex':
                skillrow = self.dfdict['Skill'].loc[defendrow['Main']]
            else:
                skillrow = self.dfdict['Skill'].loc[defendrow['LB_Auto']]
            if skillrow.name == self.dfdict['Job'].loc[defendrow['Main'], 'Skill'] or 'ex' in skillrow.name:
                potency = 'Main'
            else:
                potency = 'Sub'
            desc_list.append(f"{defender.name} casted {skillrow['Skill']}.")
            d_skilltup = (skillrow.name, potency)
            attackhp = attackhp * 2
            defendhp = defendhp * 2
            damage, hitrate, counter_damage, counter_hitrate = self.calcdamage(attacker.id, defender.id, a_skilltup=a_skilltup, d_skilltup=d_skilltup, counter=1)
        else:
            damage, hitrate, counter_damage, counter_hitrate = self.calcdamage(attacker.id, defender.id, counter=1)
        attackhp_init = attackhp
        defendhp_init = defendhp
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
            attacker_win = -1
        elif defendhp == 0 and attackhp > 0:
            attacker_win = 1
        elif attackhp == defendhp == 0:
            attacker_win = 0
        else:
            attackdmg = defendhp_init - defendhp
            defenddmg = attackhp_init - attackhp
            if attackdmg > defenddmg:
                attacker_win = 1
            elif defenddmg > attackdmg:
                attacker_win = -1
            else:
                attacker_win = 0
        if attacker_win == 0:
            field_list.append('It is a draw!')
        elif attacker_win == 1:
            field_list.append(f"{attacker.name} won!")
            # cooldown
            if attackrow['TS_Duel'] != '':
                thres = datetime.strptime(attackrow['TS_Duel'], mydtformat) + timedelta(minutes=self.cdduel)
                now = datetime.now()
                if now < thres:
                    remaining = thres - now
                    field_list.append(f"{remaining.seconds} seconds before you can duel for trophies.")
            elif attackrow['Trophy'] - defendrow['Trophy'] <= 50:
                trophy_xfer = max((defendrow['Trophy'] - attackrow['Trophy']) // 3, 5)
                self.dfdict['User'].loc[attacker.id, 'Trophy'] = attackrow['Trophy'] + trophy_xfer
                self.dfdict['User'].loc[defender.id, 'Trophy'] = defendrow['Trophy'] - trophy_xfer
                field_list.append(f"{attacker.name} won {trophy_xfer} trophies from {defender.name}!")
                self.dfdict['User'].loc[attacker.id, 'TS_Duel'] = datetime.strftime(datetime.now(), mydtformat)
                self.syncpend = 1
            else:
                field_list.append(f"There is no trophy to be won!")
        elif attacker_win == -1:
            field_list.append(f"{defender.name} won!")
            if attackrow['TS_Duel'] != '':
                thres = datetime.strptime(attackrow['TS_Duel'], mydtformat) + timedelta(minutes=self.cdduel)
                now = datetime.now()
                if now < thres:
                    remaining = thres - now
                    field_list.append(f"{remaining.seconds} seconds before you can duel for trophies.")
            elif defendrow['Trophy'] - attackrow['Trophy'] <= 50:
                trophy_xfer = max((attackrow['Trophy'] - defendrow['Trophy']) // 3, 5)
                self.dfdict['User'].loc[attacker.id, 'Trophy'] = attackrow['Trophy'] - trophy_xfer
                self.dfdict['User'].loc[defender.id, 'Trophy'] = defendrow['Trophy'] + trophy_xfer
                field_list.append(f"{defender.name} won {trophy_xfer} trophies from {attacker.name}!")
                self.dfdict['User'].loc[attacker.id, 'TS_Duel'] = datetime.strftime(datetime.now(), mydtformat)
                self.syncpend = 1
            else:
                field_list.append(f"There is no trophy to be won!")
        embed.add_field(name=field_name, value='\n'.join(field_list), inline=False)
        embed.colour = self.colours[self.dfdict['Base'].loc[defendrow['Base'], 'Element'].lower()]
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
    def infotrain(self, user, num_times=3, argop=0):
        # generate result embed of a training session
        embed = discord.Embed()
        embed.title = f"{user.name} Training"
        total_exp_gain = 0
        if argop == 0:
            num_times = min(self.dfdict['User'].loc[user.id, 'AP'], num_times)
            self.dfdict['User'].loc[user.id, 'AP'] = self.dfdict['User'].loc[user.id, 'AP'] - num_times
            self.dfdict['User'].loc[user.id, 'Gil'] = self.dfdict['User'].loc[user.id, 'Gil'] + num_times
            for _ in range(num_times):
                exp_gain = 20 + self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) * 2
                total_exp_gain += exp_gain
                self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] + exp_gain # gains EXP
            if total_exp_gain > 0:
                self.syncpend = 1
            embed.description = f"You spent {num_times} AP and gained {total_exp_gain} EXP."
        else:
            num_times = min(self.dfdict['User'].loc[user.id, 'i3'], num_times)
            self.dfdict['User'].loc[user.id, 'i3'] = self.dfdict['User'].loc[user.id, 'i3'] - num_times
            for _ in range(num_times):
                exp_gain = 50 + self.calclevel(self.dfdict['User'].loc[user.id, 'EXP']) * 2
                total_exp_gain += exp_gain
                self.dfdict['User'].loc[user.id, 'EXP'] = self.dfdict['User'].loc[user.id, 'EXP'] + exp_gain # gains EXP
            if total_exp_gain > 0:
                self.syncpend = 1
            embed.description = f"You consumed {num_times} Hero Drink(s) and gained {total_exp_gain} EXP."
        return embed
    def infoautolb(self, user, skill):
        # generate result embed of setting auto lb
        userid = user.id
        userrow = self.dfdict['User'].loc[user.id]
        if skill == 'off' and userrow['LB_Auto'] != 'off':
            self.dfdict['User'].loc[user.id, 'LB_Auto'] = 'off'
            self.syncpend = 1
            return f"{user.name} auto LB is now turned off."
        else:
            if skill == 'ex':
                skillid = 'ex'
                if 'ex' not in userrow['Main']:
                    return f"{user.name} current main job does not have limit break."
            else:
                skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            if userrow['LB_Auto'] != skillid:
                self.dfdict['User'].loc[user.id, 'LB_Auto'] = skillid
                self.syncpend = 1
                if skill == 'ex':
                    return f"{user.name} auto LB is now set to limit break."
                else:
                    return f"{user.name} auto LB is now set to {skill}."
        return f"This is {user.name} current setting."
    def infoautoitem(self, user, skill=None, thres=None):
        # generate result embed of setting auto item
        userid = user.id
        replystr_list = []
        if thres != None:
            if self.dfdict['User'].loc[user.id, 'I_Thres'] != thres:
                if thres < 1 or thres > 99:
                    return f"Please set a number between 1-99."
                self.dfdict['User'].loc[user.id, 'I_Thres'] = thres
                self.syncpend = 1
                replystr_list.append(f"{user.name} auto item HP threshold now set to {thres}%.")
        elif skill == 'off' and self.dfdict['User'].loc[user.id, 'I_Auto'] != 'off':
            self.dfdict['User'].loc[user.id, 'I_Auto'] = 'off'
            self.syncpend = 1
            return f"{user.name} auto item is now turned off."
        if skill != None:
            skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            if 'HP' not in self.dfdict['Skill'].loc[skillid, 'Stat'].split('/'):
                return f"You must set an item that restores HP."
            if self.dfdict['User'].loc[user.id, 'I_Auto'] != skillid:
                self.dfdict['User'].loc[user.id, 'I_Auto'] = skillid
                self.syncpend = 1
                replystr_list.append(f"{user.name} auto item is now set to {skill}.")
        if len(replystr_list) == 0:
            return f"This is {user.name} current setting."
        else:
            return '\n'.join(replystr_list)
    def inforefine(self, user, skill, num_times=1):
        # generate result embed of refining an item
        embed = discord.Embed()
        userrow = self.dfdict['User'].loc[user.id]
        skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
        if skillid == 'i8':
            embed.description = f"Arcana cannot be refined."
            return embed
        skillrow = self.dfdict['Skill'].loc[skillid]
        refine_tup = self.refine_rate[skillid]
        refinerow = self.dfdict['Skill'].loc[refine_tup[1]]
        embed.title = f"{user.name} - Refining {skill} into {refinerow['Skill']}"
        # detect amount
        if userrow['i8'] < self.refinecost:
            embed.description = f"You do not have enough Arcanas. You need {self.refinecost} Arcanas to refine items."
            return embed
        elif userrow[skillid] < refine_tup[0]:
            embed.description = f"You do not have enough {skill}s. You need {refine_tup[0]} {skill}s to refine."
            return embed
        # perform the action
        desc_list = []
        material_cur = userrow[skillid]
        arcana_cur = userrow['i8']
        gained_cur = userrow[refine_tup[1]]
        for _ in range(num_times):
            if material_cur < refine_tup[0] or arcana_cur < self.refinecost:
                break
            material_cur = material_cur - refine_tup[0]
            arcana_cur = arcana_cur - self.refinecost
            gained_cur = gained_cur + refine_tup[2]
        self.dfdict['User'].loc[user.id, skillid] = material_cur
        self.dfdict['User'].loc[user.id, 'i8'] = arcana_cur
        desc_list.append(f"You consumed {userrow[skillid] - material_cur} {skill}s and {userrow['i8'] - arcana_cur} Arcanas.")
        self.dfdict['User'].loc[user.id, refine_tup[1]] = gained_cur
        desc_list.append(f"You gained {gained_cur - userrow[refine_tup[1]]} {refinerow['Skill']}(s).")
        embed.description = '\n'.join(desc_list)
        field_list = (
            f"{skill} - {material_cur}",
            f"{refinerow['Skill']} - {gained_cur}",
            f"Arcana - {arcana_cur}"
        )
        embed.add_field(name='Result', value='\n'.join(field_list))
        self.syncpend = 1
        return embed
    def infoitem(self, user, skill, num_times=1, target=None):
        # generate result embed of using a item
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
        if userrow[skillid] == 0:
            embed.description = f"You ran out of {skillrow['Skill']}."
            return embed
        desc_list = []
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
    def infoskill(self, user, skill, target=None, argop=0):
        # generate result embed of a skill
        embed = discord.Embed()
        if isinstance(user, int):
            userid = user
            userrow = self.dfdict['User'].loc[userid]
            skillid = skill
        else:
            userid = user.id
            userrow = self.dfdict['User'].loc[userid]
            if 'ex' in skill:
                skillid = userrow['Main']
                if 'ex' not in skillid:
                    embed.description = 'Your current main job does not have limit break.'
                    return embed
                # check consumption type
                if argop not in (2, 3):
                    argop = 2
                target = user
            else:
                skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
            embed.title = f"{user.name} - {skill}"
        skillrow = self.dfdict['Skill'].loc[skillid]
        desc_list = []
        # check criteria
        if argop == 1 and skillrow['Healing']:
            embed.description = 'You cannot consume HP for healing skills.'
            return embed
        if argop == 2 and userrow['LB'] < 100:
            embed.description = f'Your LB gauge is not full yet.'
            return embed
        # check skill potency
        if skillid == self.dfdict['Job'].loc[userrow['Main'], 'Skill'] or 'ex' in skillid:
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
        targetrow = self.dfdict['User'].loc[targetid]
        if targetid != userid and not skillrow['Ally']:
            embed.description = f"{skill} cannot be casted on others."
            return embed
        u_hp = self.calcstats(userid, stat='HP')['HP']
        t_hp = self.calcstats(targetid, stat='HP')['HP']
        # check if lb combo involves healing
        hprecovery = 0
        if skillrow['Healing']:
            hprecovery = math.floor(u_hp * skillrow[potency])
        elif skillrow['Stat'] == 'COMBO':
            for subpotency in ('Main', 'Sub'):
                if skillrow[subpotency] == '':
                    continue
                for subskillid in skillrow[subpotency].split('/'):
                    subskillrow = self.dfdict['Skill'].loc[subskillid]
                    if subskillrow['Healing']:
                        hprecovery += math.floor(u_hp * subskillrow[subpotency])
        # no EXP gain if HP consume
        if argop == 1:
            exp_gain = 0
        else:
            exp_gain = self.calclevel(userrow['EXP']) + self.calclevel(targetrow['EXP'])
        revive = 0
        num_times = 1
        # check if is to revive
        if skillrow['Healing'] and targetrow['HP'] == 0:
            num_times = math.ceil(t_hp / hprecovery)
            if num_times > 1 and argop == 2:
                if isinstance(user, int):
                    return 0
                else:
                    embed.description = f"You are not strong enough to revive {target.name} with one cast."
                    return embed
            hprecovery = hprecovery * num_times
            exp_gain = exp_gain * num_times
            revive = 1
            if argop == 0:
                if isinstance(user, int):
                    return 0
                else:
                    desc_list = ['Target is dead!',
                        f"If you do not mind paying {self.apcost * num_times} AP, type `=char revive {skillrow['Skill']} | target`."
                    ]
                    embed.description = '\n'.join(desc_list)
                    return embed
        # check if target HP is full
        if skillrow['Healing'] and targetrow['HP'] == t_hp:
            if isinstance(user, int):
                return 0
            else:
                embed.description = f"{target.name} HP is full."
                return embed
        # check HP or AP amount or criteria to consume
        if argop == 1:
            hpcost = math.ceil(u_hp * self.skill_hpcost) * num_times
            if userrow['HP'] <= hpcost:
                embed.description = f"You need at least {hpcost + 1} HP."
                return embed
            else:
                desc_list.append(f"You consumed {hpcost} HP.")
                self.dfdict['User'].loc[userid, 'HP'] = userrow['HP'] - hpcost
        elif argop == 2:
            self.dfdict['User'].loc[userid, 'LB'] = 0
            desc_list.append(f"You consumed LB gauge.")
        elif argop == 3:
            if userrow['i3'] < num_times:
                embed.description = f'Your ran out of Hero Drinks.'
                return embed
            else:
                self.dfdict['User'].loc[userid, 'i3'] = self.dfdict['User'].loc[userid, 'i3'] - num_times
                if num_times == 1:
                    desc_list.append(f"You consumed a Hero Drink.")
                else:
                    desc_list.append(f"You consumed {num_times} Hero Drinks.")
        else:
            apcost = self.skill_apcost * num_times
            if userrow['AP'] < apcost:
                embed.description = f"You need to have at least {apcost} AP."
                return embed
            else:
                self.dfdict['User'].loc[userid, 'AP'] = self.dfdict['User'].loc[userid, 'AP'] - apcost
                self.dfdict['User'].loc[userid, 'Gil'] = self.dfdict['User'].loc[userid, 'Gil'] + apcost
                desc_list.append(f"You consumed {apcost} AP.")
        # Actual skill execution
        self.dfdict['User'].loc[userid, 'EXP'] = userrow['EXP'] + exp_gain
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
                    skillid = self.dfdict['User'].loc[attacker.id, 'LB_Auto']
                    if skillid == 'ex':
                        skill = self.dfdict['Skill'].loc[self.dfdict['User'].loc[attacker.id, 'Main'], 'Skill']
                    else:
                        skill = self.dfdict['Skill'].loc[skillid, 'Skill']
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
        embed.colour = self.colours[self.dfdict['Base'].loc[defender_base, 'Element'].lower()]
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
                    skillid = self.dfdict['User'].loc[user.id, 'LB_Auto']
                    if skillid == 'ex':
                        skill = self.dfdict['Skill'].loc[self.dfdict['User'].loc[user.id, 'Main'], 'Skill']
                    else:
                        skill = self.dfdict['Skill'].loc[skillid, 'Skill']
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
        embed.colour = self.colours[self.dfdict['Base'].loc[raid_base, 'Element'].lower()]
        if exp_gain_total > 0:
            self.syncpend = 1
            self.raidsync = 1
        return embed
    # admin commands
    def fredtest(self):
        # command to remove job and base change cooldowns (irreversible until restarted)
        self.cdjob = 0
        self.cdbase = 0
    def fredgift(self, *arg):
        # command to send gifts
        if arg[0] == 'all':
            sendall = 1
        elif arg[0].isnumeric():
            sendall = 0
            targetid = int(arg[0])
        else:
            return 'Target Error'
        try:
            num_times = int(arg[1])
        except ValueError:
            return 'ValueError'
        skill = self.find_index(' '.join(arg[2:]), 'Item')
        if skill == 'NOTFOUND':
            return 'Item Not Found'
        skillid = self.dfdict['Skill'][self.dfdict['Skill']['Skill'] == skill].tail(1).index.tolist()[0]
        if sendall:
            self.dfdict['User'][skillid] = self.dfdict['User'][skillid] + num_times
            self.syncpend = 1
            return f"Sent {num_times} {skill}(s) to all users."
        else:
            self.dfdict['User'].loc[targetid, skillid] = self.dfdict['User'].loc[targetid, skillid] + num_times
            return f"Sent u{targetid} {num_times} {skill}(s)."
    async def executecommand(self, user, ctx, *arg):
        # main command execution
        if self.maint:
            return discord.Embed(description = 'Currently under maintenance. Will be back up shortly.')
        elif len(arg) == 0:
            return self.helpmanual()
        else:
            # initialise error parameters
            if user.id in self.dfdict['User'].index:
                userfound = 1
            else:
                userfound = 0
            targeterror = 0
            # process arguments
            argkw = arg[0].lower()
            argstart = 0
            arglen = len(arg)
            if argkw in ('subs', 'sub1', 'sub2', 'main'):
                argkw = 'job'
            elif argkw in ('start',):
                argkw = 'base'
            elif argkw in ('hpskill', 'skillhp', 'lb', 'lbskill', 'skilllb', 'heroskill', 'skillhero', 'revive', 'reviveskill', 'skillrevive'):
                argkw = 'skill'
            else:
                argkw = argkw.rstrip('s')
                argstart += 1
                arglen -= 1
            # find and process operations
            ## commands with lists
            if argkw == 'info':
                if arglen == 0:
                    if userfound:
                        # own info
                        return self.infouser(user)
                else:
                    targeterror = 1
                    try:
                        target = await commands.MemberConverter().convert(ctx, ' '.join(arg[argstart:]))
                        if target.id in self.dfdict['User'].index:
                            targeterror = 0
                            return self.infouser(target)
                    except commands.BadArgument:
                        pass
            elif argkw == 'base':
                if arglen == 0:
                    # list of bases
                    return self.listbase()
                else:
                    # find operation
                    if arglen > 1 and arg[argstart].lower() == 'change' and userfound:
                        # change base
                        argop = 1
                        argstart += 1
                    elif arglen > 1 and arg[argstart].lower() in ('start', 'change'):
                        # start of tamagotchi
                        argop = 2
                        argstart += 1
                        if userfound:
                            return discord.Embed(description = 'You already started. See your base by `=char info` or change your base with `=char base change` instead.')
                    else:
                        # check info
                        argop = 0
                    # find base
                    base = self.find_index(' '.join(arg[argstart:]), 'Base')
                    if base == 'NOTFOUND':
                        return discord.Embed(description = 'Base not found. Try checking `=char base`.')
                    # carry out operation
                    if argop == 1:
                        return discord.Embed(description = self.userbasechange(user, base))
                    elif argop == 2:
                        return discord.Embed(description = self.userstart(user, base))
                    else:
                        return self.infobase(base)
            elif argkw in ('exbase', 'ex'):
                if arglen == 0:
                    # list of ex bases
                    if userfound:
                        return self.listexbase(user)
                    else:
                        return self.listexbase()
                else:
                    # find operation
                    if arglen > 1 and arg[argstart].lower() == 'unlock' and userfound:
                        # unlock ex base
                        argop = 1
                        argstart += 1
                    elif arglen > 1 and arg[argstart].lower() in ('upgrade', 'up') and userfound:
                        # upgrade ex base
                        argop = 2
                        argstart += 1
                    elif arglen > 1 and arg[argstart].lower() == 'change' and userfound:
                        # change ex base
                        argop = 3
                        argstart += 1
                    else:
                        # check info
                        argop = 0
                    # find ex base
                    base = self.find_index(' '.join(arg[argstart:]), 'EX Base')
                    if base == 'NOTFOUND':
                        return discord.Embed(description = 'EX Base not found. Try checking `=char exbase`.')
                    # carry out operation
                    if argop == 1:
                        return self.infoupexbase(user, base, unlock=1)
                    elif argop == 2:
                        return self.infoupexbase(user, base)
                    elif argop == 3:
                        return discord.Embed(description = self.userbasechange(user, base))
                    else:
                        if userfound:
                            return self.infoexbase(base, user)
                        else:
                            return self.infoexbase(base)
            elif argkw == 'job':
                if arglen == 0:
                    # list of jobs
                    return self.listjob()
                elif userfound and arglen > 1:
                    # find operation
                    if arg[argstart].lower() in ('main', 'change'):
                        # change main job
                        argop = 1
                        argstart += 1
                    elif arg[argstart].lower() in ('sub', 'subs'):
                        # change both sub jobs
                        argop = 2
                        argstart += 1
                    elif arg[argstart].lower() == 'sub1':
                        # change sub job 1
                        argop = 3
                        argstart += 1
                    elif arg[argstart].lower() == 'sub2':
                        # change sub job 2
                        argop = 4
                        argstart += 1
                    else:
                        # check info (not needed atm)
                        return discord.Embed(description = 'Try `=charhelp job`.')
                    # find job and match their destination
                    if arg[argstart].lower() == 'ex' and argop == 1:
                        jobchangedict = {'Main': 'ex'}
                    else:
                        jobargs = [a.strip() for a in ' '.join(arg[argstart:]).split('|')]
                        jobchangedict = dict()
                        if argop == 2 and len(jobargs) == 2:
                            jobchangedict_keys = ('Sub1', 'Sub2')
                        elif argop == 4:
                            jobchangedict_keys = ('Sub2',)
                        elif argop == 1:
                            jobchangedict_keys = ('Main',)
                        else:
                            jobchangedict_keys = ('Sub1',)
                        for i, jobchangedict_key in enumerate(jobchangedict_keys):
                            job = self.find_index(jobargs[i], 'Job')
                            if job == 'NOTFOUND':
                                return discord.Embed(description = 'Job not found. Try checking `=char job`.')
                            else:
                                jobchangedict[jobchangedict_key] = job
                    # carry out operation
                    return self.infojobchange(user, jobchangedict)
            elif argkw == 'skill':
                if arglen == 0:
                    # list of skills
                    return self.listskill()
                elif userfound:
                    # find operation
                    consumehp = 0
                    consumelb = 0
                    if arglen > 1 and arg[argstart] in ('hp', 'hpskill', 'skillhp'):
                        # consume hp
                        argop = 1
                        argstart += 1
                    elif arg[argstart] in ('lb', 'lbskill', 'skilllb'):
                        # consume lb
                        argop = 2
                        argstart += 1
                    elif arg[argstart] in ('hero', 'heroskill', 'skillhero'):
                        # consume hero drink
                        argop = 3
                        argstart += 1
                    elif arglen > 1 and arg[argstart] in ('revive', 'reviveskill', 'skillrevive'):
                        # consume AP to revive
                        argop = 4
                        argstart += 1
                    else:
                        argop = 0
                    # find skill
                    if arglen == 1 and argop in (2, 3):
                        skill = 'ex'
                        target = None
                    elif arg[argstart] == 'ex':
                        skill = 'ex'
                        target = None
                    else:
                        skillargs = [a.strip() for a in ' '.join(arg[argstart:]).split('|')]
                        skill = self.find_index(skillargs[0], 'Skill')
                        if skill == 'NOTFOUND':
                            return discord.Embed(description = 'Skill not found. Try checking `=char skill`.')
                        target = None
                        if len(skillargs) > 1:
                            # find target
                            try:
                                target = await commands.MemberConverter().convert(ctx, skillargs[1])
                                if target.id not in self.dfdict['User'].index:
                                    targeterror = 1
                            except commands.BadArgument:
                                targeterror = 1
                    # carry out operation
                    if not targeterror:
                        return self.infoskill(user, skill, target=target, argop=argop)
            elif argkw == 'item':
                if arglen == 0:
                    # list of items
                    return self.listitem()
                elif userfound:
                    # check number of times
                    num_times = 1
                    if arglen > 1 and arg[argstart].isnumeric():
                        num_times = min(int(arg[argstart]), 20)
                        argstart += 1
                    # find item
                    skillargs = [a.strip() for a in ' '.join(arg[argstart:]).split('|')]
                    skill = self.find_index(skillargs[0], 'Item')
                    if skill == 'NOTFOUND':
                        return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    target = None
                    if len(skillargs) > 1:
                        # find target
                        try:
                            target = await commands.MemberConverter().convert(ctx, skillargs[1])
                            if target.id not in self.dfdict['User'].index:
                                targeterror = 1
                        except commands.BadArgument:
                            targeterror = 1
                    # carry out operation
                    if not targeterror:
                        return self.infoitem(user, skill, target=target, num_times=num_times)
            elif argkw == 'refine':
                if arglen == 0:
                    # list of refine options
                    return self.listrefine()
                elif userfound:
                    # check number of times
                    num_times = 1
                    if arglen > 1 and arg[argstart].isnumeric():
                        num_times = min(int(arg[argstart]), 20)
                        argstart += 1
                    # find item
                    skill = self.find_index(' '.join(arg[argstart:]), 'Item')
                    if skill == 'NOTFOUND':
                        return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                    # carry out operation
                    return self.inforefine(user, skill, num_times=num_times)
            elif argkw == 'esper':
                if arglen == 0:
                    # list of espers
                    if userfound:
                        return self.listesper(user)
                    else:
                        return self.listesper()
                else:
                    # find operation
                    if arglen > 1 and arg[argstart].lower() == 'unlock' and userfound:
                        # unlock esper
                        argop = 1
                        argstart += 1
                    elif arglen > 1 and arg[argstart].lower() in ('upgrade', 'up') and userfound:
                        # upgrade esper
                        argop = 2
                        argstart += 1
                    elif arglen > 1 and arg[argstart].lower() == 'change' and userfound:
                        # change esper
                        argop = 3
                        argstart += 1
                    elif arg[argstart].lower() == 'off' and userfound:
                        return self.infoesperchange(user, 'off')
                    else:
                        # check info
                        argop = 0
                    # find esper
                    esper = self.find_index(' '.join(arg[argstart:]), 'Esper')
                    if esper == 'NOTFOUND':
                        return discord.Embed(description = 'Esper not found. Try checking `=char esper`.')
                    # carry out operation
                    if argop == 1:
                        return self.infoupesper(user, esper, unlock=1)
                    elif argop == 2:
                        return self.infoupesper(user, esper)
                    elif argop == 3:
                        return self.infoesperchange(user, esper)
                    else:
                        if userfound:
                            return self.infoesper(esper, user)
                        else:
                            return self.infoesper(esper)
            elif argkw == 'raid':
                if arglen == 0:
                    # list of raids
                    return self.listraid()
                elif userfound:
                    # find operation
                    if arglen > 1 and arg[argstart] == 'attack':
                        argop = 1
                        argstart += 1
                        arglen -= 1
                        num_times = 1
                    elif arglen > 1 and arg[argstart] == 'info':
                        argop = 0
                        argstart += 1
                    else:
                        argop = 0
                    if arglen > 1 and arg[argstart].isnumeric():
                        argop = 1
                        num_times = min(int(arg[argstart]), 20)
                        argstart += 1
                    # find raid
                    raid = self.find_index(' '.join(arg[argstart:]), 'Raid')
                    if raid == 'NOTFOUND':
                        return discord.Embed(description = 'Raid not found. Try checking `=char raid`.')
                    # carry out operation
                    if argop == 1:
                        return self.infoattackraid(user, raid, num_times)
                    else:
                        return self.inforaid(raid)
            elif argkw == 'help':
                if arglen > 0:
                    return self.helpmanual(arg[argstart])
                else:
                    return self.helpmanual()
            elif argkw in ('changelog', 'version'):
                if arglen > 0:
                    return self.infochangelog(arg[argstart])
                else:
                    return self.infochangelog()
            elif argkw in ('futureplan', 'future', 'plan'):
                return self.infofutureplan()
            elif argkw in ('rate', 'gacharate'):
                return self.ratemanual()
            ## commands all need userid
            elif userfound:
                if argkw == 'tower':
                    if arglen == 0:
                        # list of tower floors
                        return self.listtower(user)
                    else:
                        if arg[argstart].lower() in ('mission', 'unfinished'):
                            return self.listtower(user, unfinished=1)
                        if arg[argstart].lower() in ('giveup', 'give', 'surrender'):
                            return discord.Embed(description = self.towergiveup(user))
                        elif arg[argstart].lower() in ('start', 'challenge', 'fight', 'attack'):
                            argop = 1
                            argstart += 1
                            arglen -= 1
                        else:
                            argop = 0
                        if arglen == 0 and argop == 1:
                            floor = None
                        else:
                            if not arg[argstart].isnumeric():
                                return discord.Embed(description = 'Please give a floor number.')
                            floor = int(arg[argstart])
                            if floor not in self.tower_tuples.keys():
                                return discord.Embed(description = 'Tower floor not found. Try `=char tower`')
                        if argop == 1:
                            return self.infochallengetower(user, start=floor)
                        else:
                            return self.infotower(user, floor)
                elif argkw in ('autolbskill', 'autolb'):
                    # autolb setting
                    if arglen == 0:
                        skill = 'ex'
                    else:
                        if arg[argstart].lower() == 'off':
                            skill = 'off'
                        elif arg[argstart].lower() == 'ex':
                            skill = 'ex'
                        else:
                            skill = self.find_index(' '.join(arg[1:]), 'Skill')
                            if skill == 'NOTFOUND':
                                return discord.Embed(description = 'Skill not found. Try checking `=char skill`.')
                    return discord.Embed(description = self.infoautolb(user, skill))
                elif argkw == 'autoitem':
                    if arglen == 0:
                        # list of items
                        return self.listitem()
                    else:
                        skill = None
                        thres = None
                        if arg[argstart].lower() == 'off':
                            skill = 'off'
                        else:
                            if arg[argstart].isnumeric():
                                thres = int(arg[argstart])
                                argstart += 1
                                arglen -= 1
                            if arglen > 0:
                                skill = self.find_index(' '.join(arg[argstart:]), 'Item')
                                if skill == 'NOTFOUND':
                                    return discord.Embed(description = 'Item not found. Try checking `=char item`.')
                        return discord.Embed(description = self.infoautoitem(user, skill, thres))
                elif argkw in ('inventory', 'inv'):
                    return self.infoinventory(user)
                elif argkw == 'daily':
                    return self.infogacha(user, free=1)
                elif argkw == 'gacha':
                    if arglen > 0:
                        if arg[argstart].isnumeric():
                            return self.infogacha(user, int(arg[argstart]))
                    return self.infogacha(user)
                elif argkw == 'train':
                    argop = 0
                    num_times = 1
                    if arglen > 0:
                        if arg[argstart].lower() == 'hero':
                            argop = 1
                            argstart += 1
                            arglen -= 1
                    if arglen > 0:
                        if arg[argstart].isnumeric():
                            num_times = int(arg[argstart])
                            argstart += 1
                            arglen -= 1
                    if arglen > 0:
                        if arg[argstart].lower() == 'hero':
                            argop = 1
                    return self.infotrain(user, num_times=num_times, argop=argop)
                elif argkw == 'attack':
                    if arglen == 0:
                        return discord.Embed(description = 'Try `=charhelp battle`.')
                    else:
                        num_times = 1
                        if arglen > 1 and arg[argstart].isnumeric():
                            num_times = min(int(arg[argstart]), 20)
                            argstart += 1
                        try:
                            # find member of said name to attack
                            target = await commands.MemberConverter().convert(ctx, ' '.join(arg[argstart:]))
                            if target.id in self.dfdict['User'].index:
                                return self.infoattack(user, target, num_times)
                            else:
                                targeterror = 1
                        except commands.BadArgument:
                            targeterror = 1
                elif argkw == 'duel':
                    if arglen == 0:
                        return discord.Embed(description = 'Try `=charhelp battle`.')
                    else:
                        try:
                            # find member of said name to attack
                            target = await commands.MemberConverter().convert(ctx, ' '.join(arg[argstart:]))
                            if target.id in self.dfdict['User'].index:
                                return self.infoduel(user, target)
                            else:
                                targeterror = 1
                        except commands.BadArgument:
                            targeterror = 1
            if userfound == 0:
                # user not found
                return discord.Embed(description = self.usernotfound)
            elif targeterror:
                return discord.Embed(description = self.targeterror)
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
        await self.bot.get_channel(id_dict['Engel Synclogs']).send(f"Restarted ({datetime.strftime(datetime.now(), mydtformat)}).")

    @tasks.loop(minutes=1.0)
    async def timercheck(self):
        # check timer every minute
        now = datetime.now()
        df = engel.dfdict['Log'][engel.dfdict['Log']['Event'] == 'hourlyregen']
        thres = datetime.strptime(df.tail(1)['Timestamp'].tolist()[0], mydtformat) + timedelta(hours=1)
        if now.minute == 0 or now > thres:
            engel.userregenall()
            try:
                engel.new_log('hourlyregen', datetime.strftime(now, mydtformat))
            except gspread.exceptions.APIError as e:
                await self.bot.get_channel(id_dict['Engel Synclogs']).send(f"Hourly Regen Error: {e} ({datetime.strftime(datetime.now(), mydtformat)}).")
        df = engel.dfdict['User'][engel.dfdict['User']['TS_Dead'] != '']
        for userid, row in df.iterrows():
            thres = datetime.strptime(row['TS_Dead'], mydtformat) + timedelta(hours=engel.revivehours)
            if now > thres:
                engel.userrevive(userid)

    @tasks.loop(seconds=10.0)
    async def synccheck(self):
        # check if sync is pending
        if engel.syncpend:
            return_val = engel.sheetsync()
            try:
                channel = self.bot.get_channel(id_dict['Engel Synclogs'])
                if channel == None:
                    print('Channel error. Trying again 10s later.')
                if return_val == 1:
                    await channel.send(f"Synced success ({datetime.strftime(datetime.now(), mydtformat)}).")
                else:
                    await channel.send(f"Sync Error: {return_val} ({datetime.strftime(datetime.now(), mydtformat)}).")
            except AttributeError:
                print(f"Channel Error. Synced success ({datetime.strftime(datetime.now(), mydtformat)}).")

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
            if len(arg) > 0:
                if arg[0] in ('s', 'sheetsync'):
                    return_val = engel.sheetsync()
                    if return_val == 1:
                        await ctx.send(f"Synced success ({datetime.strftime(datetime.now(), mydtformat)}).")
                    else:
                        await ctx.send(f"Error: {return_val} ({datetime.strftime(datetime.now(), mydtformat)}).")
            else:
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

    @commands.command(aliases=['fredgift'])
    async def frederikagift(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # admin gift command
        if ctx.message.author.id == id_dict['Owner']:
            await ctx.send(engel.fredgift(*arg))

    @commands.command(aliases=['fredtest'])
    async def frederikatest(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # admin gift command
        if ctx.message.author.id == id_dict['Owner']:
            engel.fredtest()
            await ctx.send('Cooldowns removed for testing.')

    @commands.command(aliases=['engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp'])
    async def engelberthelp(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, 'help', *arg)
        embed.set_footer(text = engel.defaultfooter)
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)

    @commands.command(aliases=['engelrep', 'petrep', 'tamagotchirep', 'tamarep', 'charrep'])
    async def engelbertrepeat(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # repeat main command
        user = ctx.author
        if len(arg) > 1:
            if arg[0].isnumeric():
                num_times = max(int(arg[0]), 1)
                num_times = min(num_times, 10)
                for _ in range(num_times):
                    embed = await engel.executecommand(user, ctx, *arg[1:])
                    embed.set_footer(text = engel.defaultfooter)
                    await ctx.send(embed = embed)
                    await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)
                return
        await ctx.send(f"The usage is `=charrep (number) (command)` (e.g. `=charrep 10 exbase up hyoh`).")

    @commands.command(aliases=['engel', 'pet', 'tamagotchi', 'tama', 'char'])
    async def engelbert(self, ctx, *arg):
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = logs_embed(ctx.message))
        # main command
        user = ctx.author
        embed = await engel.executecommand(user, ctx, *arg)
        embed.set_footer(text = engel.defaultfooter)
        await ctx.send(embed = embed)
        await self.bot.get_channel(id_dict['Engel Logs']).send(embed = embed)
