import re, random
import pandas as pd

class WotvUtils:
    def __init__(self, dfwotv, id_dict):
        self.dfwotv = dfwotv
        self.reconditions = re.compile(r'\[[\w\/]+\]') # regex for bracketed conditions
        self.revalues = re.compile(r'-?\d+$') # regex for numbers
        self.resymbols = re.compile(r'[^\w ]') # regex for symbols to be omitted for url
        self.dicts = {
            'mat_sets': self.mat_sets(self.dfwotv.eq),
            'eq_lists': {
                'Type': ('t',),
                'Acquisition': ('a',),
                'Regular': ('n', 'common'),
                'Rare': ('r',),
                'Cryst': ('c', 'e', 'element'),
                'Ore': ('o',)
            },
            'eq_replace': (
                ('staff', 'rod'),
                ('gs', 'great sword'),
                ('greatsword', 'great sword'),
                ('nb', 'ninja blade'),
                ('ninjablade', 'ninja blade'),
                ('armour', 'armor')
            ),
            'esper_sets': self.esper_sets(self.dfwotv.esper),
            'esper_suffix': {
                'atk': 'ATK Up',
                'killer': 'Killer',
                'res': 'RES Up'
            },
            'esper_stats': ['HP', 'TP', 'AP', 'ATK', 'MAG', 'DEX', 'AGI', 'LUCK'],
            'esper_colsuffix': {
                'ATK Up': 'ATK',
                'Killer': 'Killer',
                'Stat Up': '',
                'RES Up': 'RES'
            },
            'magicites': {
                'S': 400,
                'M': 800,
                'L': 1600,
                'XL': 32000
            },
            'esper_exp': {
                1: 1699380,
                2: 6727933,
                3: 16821904
            },
            'brackets': self.bracket_init(),
            'emotes': self.emotes_init(),
            'colours': {
                'fire': 0xE47051,
                'ice': 0xA4B3F0,
                'wind': 0xA3E053,
                'earth': 0xF6D993,
                'thunder': 0xF5F464,
                'water': 0xAAFAFC,
                'light': 0xFCFCFC,
                'dark': 0xE083F4,
                'neutral': 0x7F8486
            },
            'embed': { # default embed settings
                'default_colour': 0x999999,
                'author_name': 'FFBE幻影戦争',
                'gl_author_name': 'FFBE: War of the Visions',
                'author_icon_url': 'https://caelum.s-ul.eu/1OLnhC15.png'
            },
            'paramcalc': {
                'agi': (70, ('agi', 'speed', 'spd', 'agility')),
                'dex': (250, ('dex', 'dexterity')),
                'luck': (250, ('luck', 'luc', 'luk')),
                'acc': (0, ('acc', 'accuracy', 'hit')),
                'eva': (0, ('eva', 'evasion', 'evade', 'avoid')),
                'crit': (0, ('crit', 'critical', 'crit rate', 'critical rate')),
                'c.avo': (0, ('crit avoid', 'crit avo', 'critical avoidance', 'ca', 'cavo', 'c. avo', 'c.avo'))
            },
            'calcurl': (
                ('é', 'e'),
                (' ', '-')
            ),
            'changelog': (
                ('25th April 2021', (
                    'Ramada Star Reading - added Moore (`=help stars`).',
                )),
                ('16th March 2021', (
                    'Esper Filter - bug fix and able to search espers without 3-star awakening.',
                )),
                ('7th March 2021', (
                    'VC Elements - now an extra section that includes universal VC effects that come with an elemental max effect.',
                )),
                ('20th February 2021', (
                    'Magicite Calculator - calculate EXP required from certain star and magicites you have (`=help esper`).',
                )),
                ('6th February 2021', (
                    '(beta) Engelbert Tamagotchi - fluff tamagotchi function `=char help` or `=tamagotchi help` or `=engel help`',
                )),
                ('31st January 2021', (
                    'Events - `=events` to check on-going or up-coming events. (`=help events` for more info)',
                )),
                ('27th January 2021', (
                    'Parameter calculation - `=param` to input screen parameters to calculate accuracy, evasion, critical rate and critical avoidance. (`=help param` for more info)',
                )),
                ('21st January 2021', (
                    'Random function - `=rand` or `=choice` to have bot pick a random number within given range or a random choice.',
                )),
                ('19th January 2021', (
                    'Warning: Bot command calls will be logged for improvement purpose. Please do not include sensitive info while using the bot.',
                    'Math function - `=math` or `=calc` for simple math calculations.',
                )),
                ('16th January 2021', (
                    'Changed display picture because of clash with another bot.',
                    'Equipment search function - search equipment by effect. (`=help eq` for more info)'
                )),
                ('14th January 2021', (
                    'Updated icons into in-game-assets.',
                    'Ramada Star Reading - `=stars` or `=ramada` (fluff command).'
                )),
                ('13th January 2021', (
                    'Equipment function - mainly to check recipes and please refer to WOTV-CALC for in-depth info. (`=help eq` for more info)',
                    'Return list of suggestions when result not found for some commands.'
                )),
                ('8th January 2021', (
                    'Changelog implemented (this function).',
                    'Esper filter - able to filter 3-star or limited espers. (`=help esper` for more info)',
                    'Slight changes in general info.'
                )),
                ('7th January 2021', (
                    'Esper compare - able to compare all or a group of effects at once. (`=help esper` for more info)',
                    'News link - get link to news with `=news` or `=news gl`.'
                ))
            ),
            'ramada_rarity': ('R', 'SR', 'SSR', 'UR'),
            'ramada_implication': ('up', 'neutral', 'down'),
            'event_tuples': (
                (('gacha', 'banner', 'step', 'summon', 'pull', 'sale'), 'visiore'),
                (('recipe', 'weapon', 'armor', 'armour', 'accessory', 'farm'), 'recipe'),
                (('pvp', 'arena', 'class', 'guild'), 'party'),
                (('event', 'raid', 'tower', 'box'), 'event'),
                (('shop', 'whimsy'), 'shop'),
                (('update', 'change', 'patch', 'upgrade', 'fix'), 'update')
            )
        }
        self.help_general = (
            ('General Info', (
                'Bot prefix is `=`. Only JP data is available at the moment.',
                'Bot commands are case sensitive. Please do NOT capitalize the commands.',
                'For programming reason, element name lightning is replaced by thunder because the text contains another element light.',
                'WARNING: Bot command calls will be logged for improvement purpose. Please do not include sensitive info while using the bot.'
            )),
            ('About', (
                f"Made by <@{id_dict['Owner']}>, please contact me for any bug report / data correction / adding aliases / suggestion (depends on viability).",
                'I only play JP and do not wish to maintain GL data. To implement GL data, I would need collaborator(s). Please contact me if interested.'
            )),
            ('Standard Commands', ('`=ping`, `=help`, `=changelog/version`, `=rand/choice`',)),
            ('WOTV Commands', (
                'Enter their respective specific help commands for more info.',
                '- **Events** `=help events`',
                '- **Parameter Calculation** `=help param`',
                '- **Equipment** `=help eq`',
                '- **Vision Card** `=help vc`',
                '- **Esper** `=help esper`'
            )),
            ('Simple Calculation', ('Enter `=math/calc` with a mathematical expression to calculate. e.g. `=calc 1+1`',)),
            ('Weekly', ('Enter `=weekly` for dungeon bonus of days of the week.',)),
            ('News', ('Enter `=news` for link to JP news or `=news gl` for link to GL news.',)),
            ('Ramada Star Reading', ('Fluff command. Enter `=stars` or `=ramada` or `=moore` to have Ramada or Moore read your fortune. Enter `=help stars` for current rate.',
            'Disclaimer: This has nothing to do with in-game mechanics or lore, just pre-written lines and RNG.')),
            ('Engelbert Tamagotchi', ('Fluff command. A tamagotchi (digital pet / avatar / character) raising function.',
            'Note that it is a group of functions entirely separated from the rest of the bot so all related commands start with `=char`, `=tamagotchi` or `=engel`.',
            'Enter `=char help` or `=tamagotchi help` or `=engel help` for more info.'))
        )
        self.help_events = (
            ('Events', (
                '** =events**',
                'Returns list of up-coming / on-going events (subject to having been keyed...).'
            )),
            ('Countdown', (
                '`=events` (the default)',
                'Returns a list of on-going events with their remaining time and a list of up-coming events counting down to their starting times.'
            )),
            ('Date and Time', (
                '`=events date` or `=events time`',
                'Same as above but instead of countdowns, returns the starting and ending times (in JST) of on-going events and up-coming events.'
            )),
            ('Date and Time Embedded', (
                '`=events embed` or `=events format`',
                'Returns the same result as `=events date` but in embedded format. May not format correctly if there are lengthy events.',
                'Not intended to use while in mobile (you can try).'
            ))
        )
        self.help_param = (
            ('Parameter Calculation', (
                '**= param / acc / eva / crit** (will return the same result regardless of which you use)',
                'Input AGI, DEX, LUCK and/or flat sources of ACC, EVA, CRIT, CRIT AVOID to calculate actual accuracy, evasion, crit, crit avoid in battle.',
                'Arguments separated by `|` for each stat followed by their values.',
                'e.g. `=param dex 300 | luck 400 | eva 80`',
                'Note: Not to be confused with `=calc` which is simple math calculation command.'
            )),
            ('Default Values',
                ('Parameters not input (or negative agi/dex/luck) will have their default values used.',
                f"Current default values: {', '.join([k + ' ' + str(v[0]) for k, v in self.dicts['paramcalc'].items()])}."
            )),
            ('Disclaimer and Sources',
                ('Formulae used: Meow and Shalzuth.',
                '[Article regarding Accuracy and Evasion](https://wotv.info/accuracy-and-evasion-debunked-datamine-diary-2/)',
                '[Article regarding Crit and Crit Avoidance](https://wotv.info/crit-crit-avoidance-formula/)'
            ))
        )
        self.help_eq = (
            ('Equipment Help', (
                'The function is mainly for recipes checking, for in-depth equipment info please refer to WOTV-CALC.',
                'Note that only craftable/star-able SSR/UR equipment is listed (i.e. no TM).',
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.'
            )),
            ('Equipment by name', ('**= eq**',
                'Argument is by equipment name (subject to name availability).',
                'e.g. `=eq ribbon`',
                'Note that the link to WOTV-CALC may not necessarily work...'
            )),
            ('Equipment by effect', ('**= es / eqs**',
                'Argument is specific effect names.',
                'e.g. `=es slash res`'
            )),
            ('List of keywords', ('**= eq l**',
                'Argument is one of `type, acquisition, regular, rare, cryst, ore` to check their respective keywords.',
                'Put no argument to return the above list.'
                'e.g. `=eq l rare`'
            )),
            ('Equipment by type', ('**= eq t**',
                'Argument is one of the equipment types that can be checked by command above.',
                'e.g. `=eq t accessory`, `=eq t sword`'
            )),
            ('Equipment by acquisition method', ('**= eq a**',
                'Argument is one of the acquisition methods that can be checked by command above.',
                'e.g. `=eq a key`, `=eq a raid`'
            )),
            ('Equipment by material', ('**= eq**',
                'Argument is one of the materials that can be checked by the first command.',
                'It shares the same command as equipment by name, so needs to be exact match (among the aliases).',
                'e.g. `=eq heart`, `=eq fire`'
            )),
            ('Disclaimer and Sources',
                ('SQEX and Gumi (obviously).',
                'Data source: [WOTV-CALC](https://wotv-calc.com/JP/equipments) (Bismark). Special thanks to Shalzuth for assets etc.',
                'Some recent releases are taken directly from in-game info and news.'
            ))
        )
        self.help_vc = (
            ('Vision Card Help', (
                self.dicts['emotes']['elements'] + ' elemental icons indicate unit-element-locked effects.',
                self.dicts['emotes']['allele'] + ' ALL icon indicates unconditional effects.',
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.'
            )),
            ('VC Info', ('**= vc / wvc / wotvvc**',
                'Argument either in Japanese name, English name or short nicknames (aliases) bracketed in other commands.',
                'e.g. `=vc omega`'
            )),
            ('VC Search', ('**= vs / vcs / wvs /wotvvcsearch**',
                'Argument in specific effect names with following conventions:',
                '- slash/pierce/strike/missile/magic atk/res/pen',
                '- fire/ice/(etc) atk/res'
                '- def/spr up/pen',
                '- atk%/mag%/agi%/dex%/luck%/hp%/accuracy/evasion',
                '- single/area res',
                '- crit rate/evade/damage',
                '- ap gain, max damage, etc',
                'e.g. `=vs pierce atk`'
            )),
            ('VC Element', ('**= ve / vce / wve / wotvvcelement**',
                'Argument in element (e.g. fire).',
                'e.g. `=ve light`'
            )),
            ('Disclaimer and Sources',
                ('SQEX and Gumi (obviously).',
                'Data source: [WOTV-CALC](https://wotv-calc.com/JP/vc) (Bismark). Special thanks to Shalzuth for assets etc.',
                'Some recent releases are taken directly from in-game info and news.'
            ))
        )
        self.help_esper = (
            ('Esper Help', (
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.',
                self.dicts['emotes']['esper'] + ' icon indicates 3-star awakened data.',
                'Adding `m` right after `=esper` or modifiers mentioned below will make them more readable in mobile.'
            )),
            ('Esper Info', ('**= esper**',
                'Argument in standard English name or Japanese name.',
                'e.g. `=esper omega`',
                'Note that the link to WOTV-CALC may not necessarily work...'
            )),
            ('Esper Rank', ('**= esper r / esper rank**',
                'Actually search/filter and sort functions in one. Also callable with `=esper f` or `=esper s`',
                'Arguments separated by `|` for each stat / effect.',
                'Will filter and rank by the first argument, while also display values of other arguments for comparison.',
                'Filter 3-star espers by `=esper r awaken` (/ `3-star`) but will not be sorted.',
                'Filter espers without 3-star by `=esper r 2` but will not be sorted.',
                'Filter limited espers by `=esper r limited` (/ `collab`) but will not be sorted.',
                '3 or more arguments will force it into mobile display mode.',
                'e.g. `=esper r magic | human`, `=esper r m magic | mag% | agi`'
            )),
            ('Esper Compare', ('**= esper c / esper compare**',
                'Arguments separated by `|` for each esper / effect.',
                'Will only compare all flat stats by default, add effect comparisons by `+ effect` as arguments.',
                'Alternatively, `+all` to add all effects; `+atk` `+killer` `+stat` `+res` for their respective categories.',
                '3 or more espers will force it into mobile display mode.',
                'e.g. `=esper c baha | odin | +human`, `=esper c m baha | cact | mindflayer | +magic | +mag% | +human`'
            )),
            ('Note on effect convention', ('Arguments of effects in rank or compare have the following conventions:',
                '- hp/tp/ap/atk/mag/agi/dex/luck (base)',
                '- slash/pierce/strike/missile/magic atk/res',
                '- fire/ice/(etc) atk/res',
                '- def/spr/hp%/tp%/ap%/atk%/mag% (node)',
                '- accuracy/evasion',
                '- crit rate/evade/damage',
                '- poison/stop/(etc) res'
            )),
            ('Magicite Calculator', ('**= magicite / esperexp**',
                'Input the number of S, M, L, XL magicites, star of esper you are raising from and bonus to calculate if you have enough magicites.',
                'Starting from 1-star esper, 100% bonus, non-neutral by default.',
                'Arguments separated by `|` for each value followed by their values.',
                'e.g. `=magicite s 300 | m 400 | xl 80 | star 3 | bonus 90`',
                'e.g. `=magicite xl 100 | star 2 | bonus 100 | neutral` for neutral espers like Odin or Bahamut.'
                'Note: Not to be confused with `=calc` which is simple math calculation command.'
            )),
            ('Disclaimer and Sources',
                ('SQEX and Gumi (obviously).',
                'Data source: [WOTV-CALC](https://wotv-calc.com/JP/espers) (Bismark). Special thanks to Shalzuth for assets etc.',
                'Some recent releases are taken directly from in-game info and news.'
            ))
        )
        self.update_ramada()
        self.weekly_init()
    def weekly_init(self):
        # only runs once to generate the end string
        msg_list = []
        weekly_tuples = [
            ('`Sunday   `', ('gil',)),
            ('`Monday   `', ('kame', 'pot')),
            ('`Tuesday  `', ('fire', 'wind')),
            ('`Wednesday`', ('water', 'ice')),
            ('`Thursday `', ('earth', 'dark')),
            ('`Friday   `', ('thunder', 'light')),
            ('`Saturday `', ('pink', 'gil'))
        ]
        for day, daylist in weekly_tuples:
            msg_line = day + ': '
            for ele in daylist:
                msg_line += self.dicts['emotes'][ele]
            msg_list.append(msg_line)
        self.weekly = '\n'.join(msg_list)
    def mat_sets(self, df):
        # only runs once to generate the dictonary entry
        dict_sets = {
            'Type': set(),
            'Acquisition': set(),
            'Regular': set(),
            'Rare': set(),
            'Cryst': set(),
            'Ore': set()
        }
        for _, row in df.iterrows():
            for k, v in dict_sets.items():
                if row[k] != '':
                    if k == 'Cryst' and len(row[k]) > 1:
                        v = v.union(set(row[k]))
                    else:
                        v.add(row[k])
        return dict_sets
    def esper_sets(self, df):
        # only runs once to generate the dictonary entry
        dict_sets = {
            'ATK Up': set(),
            'Killer': set(),
            'Stat Up': set(),
            'RES Up': set(),
        }
        for index, row in df.iterrows():
            for k, v in dict_sets.items():
                if row[k] != '':
                    for eff in row[k].split(' / '):
                        re_match = self.revalues.search(eff)
                        v.add(eff[:re_match.start()].strip().lower())
        return dict_sets
    def emotes_init(self):
        # only runs once to generate the dictonary entry
        # raw code of emotes uploaded into Discord
        wotv_emotes_raw = (
            ('weapon', '799182037348909077'),
            ('armor', '799182037696905276'),
            ('accessory', '799182037248114689'),
            ('ur', '799226625631322152'),
            ('ssr', '799226625199570965'),
            ('sr', '799226625715208212'),
            ('r', '799226625371537449'),
            ('n', '805571101786374215'),
            ('mr', '799226833635508224'),
            ('fire', '791969566023745547'),
            ('ice', '791969566308958219'),
            ('wind', '791969566409752576'),
            ('earth', '791969566477385738'),
            ('thunder', '791969566245781535'),
            ('water', '791969566254825523'),
            ('light', '791969565826613259'),
            ('dark', '791969566246436884'),
            ('neutral', '791969566233853952'),
            ('allele', '799186663229227038'),
            ('limited', '799155023249408001'),
            ('esper', '799155023086878740'),
            ('kame', '799186663041531907'),
            ('pink', '799230682470678559'),
            ('pot', '799231267651584010'),
            ('gil', '799228097185579028'),
            ('visiore', '799228097169457163'),
            ('up', '800158793983852584'),
            ('down', '800158794007969892'),
            ('update', '805305947740176425'),
            ('event', '805305947722743830'),
            ('recipe', '805305947898642473'),
            ('shop', '805305948003368970'),
            ('party', '809924634903838810')
        )
        wotv_aemotes_raw = (
            ('elements', '796963642418790451'),
        )
        wotv_emotes = dict()
        for k, v in wotv_emotes_raw:
            wotv_emotes[k] = f"<:wotv_{k}:{v}>"
        for k, v in wotv_aemotes_raw:
            wotv_emotes[k] = f"<a:wotv_{k}:{v}>"
        return wotv_emotes
    def bracket_init(self):
        # only runs once to generate the dictonary entry
        bracket_dict = dict()
        for ele in ['fire', 'ice', 'wind', 'earth', 'thunder', 'water', 'light', 'dark']:
            bracket_dict[f"[{ele.capitalize()}]"] = ele
            bracket_dict[ele] = f"[{ele.capitalize()}]"
        return bracket_dict
    def eqt_convert(self, type_str):
        # only used so correct type emote is generated when printed
        if type_str == 'Accessory':
            return 'accessory'
        elif 'Armor' in type_str:
            return 'armor'
        else:
            return 'weapon'
    def shortcut_convert(self, argstr, col='VC'):
        # convert shortcut if in the sheet
        try:
            args = self.dfwotv.shortcut.loc[argstr.lower()][col]
            if args != '':
                return args
            else:
                return argstr
        except KeyError:
            return argstr
    def esper_findcol(self, argstr):
        # find the correct column to search for an effect from an argument string
        if argstr[:3] == 'ALL':
            return argstr[4:], 'ALL'
        if argstr.rstrip('s') in ['awakened', 'awaken', '3-star', '3star', '3']:
            return 'Awaken', 'y'
        if argstr.rstrip('s') in ['2-star', '2star', '2']:
            return 'Awaken', 'n'
        if argstr in ['collab', 'limited']:
            return 'Limited', 'y'
        if argstr.upper() in self.dicts['esper_stats']:
            return argstr.upper(), 'STAT'
        col = 'NOTFOUND'
        args = argstr.split()
        if args[-1] in self.dicts['esper_suffix'].keys():
            col = self.dicts['esper_suffix'][args[-1]]
            argstr = ' '.join(args[:-1])
        else:
            for k, v in self.dicts['esper_sets'].items():
                if argstr in v:
                    col = k
                    break
            else:
                col_list = []
                for k, v in self.dicts['esper_sets'].items():
                    for v_item in v:
                        if argstr in v_item:
                            col_list.append(k)
                if len(col_list) == 1:
                    col = col_list[0]
        return col, argstr
    def name_str(self, row, name='NAME', element=1, rarity=1, type=1, limited=1, awaken=1, alias=1, elestr=''):
        # process an entry to print the name string decorated with emotes
        namestr = ''
        if elestr != '':
            namestr += self.dicts['emotes'][elestr]
        elif 'Element' in row.index and element:
            namestr += self.dicts['emotes'][row['Element'].lower()]
        if 'Rarity' in row.index and rarity:
            namestr += self.dicts['emotes'][row['Rarity'].lower()]
        if 'Type' in row.index and type:
            namestr += self.dicts['emotes'][self.eqt_convert(row['Type'])]
        if 'Limited' in row.index and limited:
            if row['Limited'] != '':
                namestr += self.dicts['emotes']['limited']
        if 'Awaken' in row.index and awaken:
            if row['Awaken'] == 'y':
                namestr += self.dicts['emotes']['esper']
        if name == 'NAME':
            namestr += f" {row.name}"
        else:
            namestr += f" {name}"
        if 'Aliases' in row.index and alias:
            engstr = row['Aliases'].split(' / ')[0]
            if engstr != '':
                if name == '':
                    namestr += engstr
                else:
                    namestr += f" ({engstr})"
        return namestr
    def calc_url(self, category, namestr):
        # generate urls for Bismark's WOTC-CALC
        calc_url = f"https://wotv-calc.com/JP/{category}/"
        urlstr = namestr.lower().replace('-', ' ')
        urlstr = self.resymbols.sub('', urlstr)
        for a, b in self.dicts['calcurl']:
            urlstr = urlstr.replace(a, b)
        return f"[{namestr}]({calc_url + urlstr})"
    def find_row(self, df, arg):
        # tolerance processing for query to find the correct entry
        if isinstance(arg, str):
            argstr = arg.lower()
        else:
            try:
                arg[0].encode('ascii')
                argstr = ' '.join(arg).lower()
            except UnicodeEncodeError: # Check if arguments are in Japanese
                argstr = '　'.join(arg)
        try:
            row = df.loc[argstr]
            return 1, row
        except KeyError:
            df_name = df[df.index.str.lower().str.contains(argstr)]
            if len(df_name) > 0:
                for index, row in df_name.iterrows():
                    if argstr == index.lower():
                        return 1, row
            if 'Aliases' in df.columns:
                df_aliases = df[df['Aliases'].str.lower().str.contains(argstr)]
                if len(df_aliases) > 0:
                    for _, row in df_aliases.iterrows():
                        if argstr in [a.lower() for a in row['Aliases'].split(' / ')]:
                            return 1, row
            else:
                df_aliases = pd.DataFrame()
            if 'English' in df.columns: # VC only
                df_english = df[df['English'].str.lower().str.contains(argstr)]
                if len(df_english) > 0:
                    for _, row in df_english.iterrows():
                        if argstr == row['English'].lower():
                            return 1, row
            else:
                df_english = pd.DataFrame()
            if len(df_name) == 1:
                return 1, df_name.iloc[0]
            elif len(df_english) == 1:
                return 1, df_english.iloc[0]
            elif len(df_aliases) == 1:
                return 1, df_aliases.iloc[0]
            else:
                suggestion_list = df_name.index.tolist()
                if len(df_english) > 0:
                    suggestion_list = suggestion_list + df_english['English'].tolist()
                for alias_list in df_aliases['Aliases'].tolist():
                    for suggestion in alias_list.split(' / '):
                        if suggestion != '':
                            suggestion_list.append(suggestion)
                return 0, ' / '.join(suggestion_list)
    def rand(self, ffbe, *arg):
        randstr = ''
        incorrect = 0
        # check if 1 or 2 numbers are input
        if len(arg) == 1:
            if arg[0].isnumeric():
                randstr = str(random.randint(0, int(arg[0])))
        elif len(arg) == 2:
            if arg[0].isnumeric() and arg[1].isnumeric():
                randstr = str(random.randint(int(arg[0]), int(arg[1])))
        # if not numbers
        if randstr == '':
            if len(arg) > 1:
                if '|' in arg:
                    arg = [a.strip() for a in ' '.join(arg).split('|')]
                # random choice of strings
                randstr = random.choice(arg)
            else:
                # insufficient input
                incorrect = 1
        if ffbe: # return only non-WOTV characters if server is FFBE
            df = self.dfwotv.rand[self.dfwotv.rand['FFBE'] == 1]
        else:
            df = self.dfwotv.rand
        df_index = df[df['Incorrect'] == incorrect].sample().index[0]
        df_row = df.loc[df_index]
        return (incorrect, df_row['Name'], df_row['Element'], df_row['Url'], df_row['String'].replace('CHOICE', randstr))
    def ramada(self, reader):
        # random fortune generator for star reading
        choice = random.choices(self.dfwotv.stars.index.tolist(), weights=self.dfwotv.stars['Weight'].tolist())[0]
        row = self.dfwotv.stars.iloc[choice]
        if reader not in ('moore', 'ramada'):
            if row['Emote'] == 'neutral':
                reader = 'ramada'
            elif row['Rarity'] == 'SSR':
                reader = 'moore'
            else:
                reader = random.choice(('ramada', 'moore'))
        if reader == 'moore':
            row_url = row['MUrl']
            row_title = f"Moore Star Reading {self.dicts['emotes'][row['Rarity'].lower()]}{self.dicts['emotes'][row['Emote']]}"
        elif reader == 'ramada':
            row_url = row['Url']
            row_title = f"Ramada Star Reading {self.dicts['emotes'][row['Rarity'].lower()]}{self.dicts['emotes'][row['Emote']]}"
        return row['Fortune'], row_title, row_url,
    def update_ramada(self):
        # Generate current rate dynamically directly from data
        rate_lists = []
        for rarity in self.dicts['ramada_rarity']:
            df_row1 = self.dfwotv.stars[self.dfwotv.stars['Rarity'] == rarity]
            rarity_str = f"{self.dicts['emotes'][rarity.lower()]}: {df_row1['Weight'].sum()}%"
            implication_lists = []
            for implication in self.dicts['ramada_implication']:
                df_row2 = df_row1[df_row1['Emote'] == implication]
                if len(df_row2) > 0:
                    implication_lists.append(f"{self.dicts['emotes'][implication]} {df_row2['Weight'].sum()}%")
            rarity_str += f" ({' '.join(implication_lists)})"
            rate_lists.append(rarity_str)
        self.help_ramada = (
            ('Ramada Star Reading Help',
                ('A fluff command. Enter `=ramada` to have Ramada read your fortune.',
                'Enter `=moore` to have Moore read your fortune.',
                'Enter `=stars` to have either of them read your fortune.',
                'Disclaimer: This has nothing to do with in-game mechanics or lore, just pre-written lines and RNG.',
                'Note that the rate may change from time to time. Any feedback is welcome.'
            )),
            ('Current rate:', rate_lists)
        )
