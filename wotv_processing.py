import re
import random
from gsheet_handler import dfwotv

# raw code of emotes uploaded into Discord
wotv_emotes_raw = (
    ('weapon', '799182037348909077'),
    ('armor', '799182037696905276'),
    ('accessory', '799182037248114689'),
    ('ur', '799226625631322152'),
    ('ssr', '799226625199570965'),
    ('sr', '799226625715208212'),
    ('r', '799226625371537449'),
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
    ('down', '800158794007969892')
)
wotv_aemotes_raw = (
    ('elements', '796963642418790451'),
)

class WotvUtils:
    def __init__(self):
        self.reconditions = re.compile(r'\[[\w\/]+\]') # regex for bracketed conditions
        self.revalues = re.compile(r'-?\d+$') # regex for numbers
        self.opdicts = {
            '+': (lambda a, b: a + b),
            '-': (lambda a, b: a - b),
            '*': (lambda a, b: a * b),
            '/': (lambda a, b: a / b),
            '%': (lambda a, b: a % b),
            '^': (lambda a, b: a ** b),
            '**': (lambda a, b: a ** b),
        }
        self.dicts = {
            'mat_sets': self.mat_sets(dfwotv.eq),
            'eq_lists': {
                'Type': ['t'],
                'Acquisition': ['a'],
                'Regular': ['n', 'common'],
                'Rare': ['r'],
                'Cryst': ['c', 'e', 'element'],
                'Ore': ['o']
            },
            'eq_replace': (
                ('staff', 'rod'),
                ('gs', 'great sword'),
                ('greatsword', 'great sword'),
                ('nb', 'ninja blade'),
                ('ninjablade', 'ninja blade'),
                ('armour', 'armor')
            ),
            'esper_sets': self.esper_sets(dfwotv.esper),
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
                'author_icon_url': 'https://caelum.s-ul.eu/1OLnhC15.png',
                'footer': 'Data Source: WOTV-CALC (Bismark)'
            },
            'changelog': (
                ('21st January 2021', (
                    'Random function - `=rand` or `=choice` to have bot pick a random number within given range or a random choice.',
                )),
                ('19th January 2021', (
                    'Warning: Bot command calls will be logged for future improvement purpose. Please do not include sensitive info while using the bot.',
                    'Math function - `=math` or `=calc` for simple math calculations.',
                )),
                ('16th January 2021', (
                    'Changed display picture because of clash with another bot.',
                    'Equipment search function - search equipment by effect. (`=help eq` for more info)'
                )),
                ('14th January 2021', (
                    'Updated icons into in-game-assets.',
                    'Ramada Star Reading - `=stars` (fluff command).'
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
            'math_errors': ('Zero Division Error', 'Overflow Error', '... Excuse me?')
        }
        self.help_general = (
            ('General Info', (
                'Bot prefix is `=`.',
                'Made by `Caelum#3319`, please contact me for any bug report / data correction / suggestion (depends on viability).',
                'Feel free to contact me to request adding aliases to vc/esper/equipment.',
                'JP data only for now. Would need collaborator(s) to implement GL data. Please contact me if interested.',
                'For programming reason, element name lightning is all replaced by thunder (because the text contains another element light).',
                'Warning: Bot command calls will be logged for future improvement purpose. Please do not include sensitive info while using the bot.'
            )),
            ('Standard Commands', ('`=ping`', '`=help`', '`=changelog/version`', '`=math/calc`', '`=rand/choice`')),
            ('Equipment', ('Enter `help eq` for more info.',)),
            ('VC', ('Enter `=help vc` for more info.',)),
            ('Esper', ('Enter `=help esper` for more info.',)),
            ('Weekly', ('Enter `=weekly` for dungeon bonus of days of the week.',)),
            ('News', ('Enter `=news` for link to JP news, `=news gl` for link to GL news.',)),
            ('Ramada Star Reading', ('Fluff command. Enter `=stars` or `=ramada` to have Ramada read your fortune. Enter `=help stars` for current rate.',
            'Disclaimer: This has nothing to do with in-game mechanics or lore. Basically RNG.'))
        )
        self.help_eq = (
            ('General Info (Equipment)', (
                'The function is mainly for recipes checking, for in-depth equipment info please refer to WOTV-CALC.',
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.'
            )),
            ('Equipment by name', ('**= eq**',
                'Argument is by equipment name (subject to name availability).',
                'e.g. `=eq ribbon`'
            )),
            ('Equipment by effect', ('**= es / eqs**',
                'Argument is specific effect names.',
                'e.g. `=es slash res`')),
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
                'e.g. `=eq t accessory`, `=eq a raid`'
            )),
            ('Equipment by material', ('**= eq**',
                'Argument is one of the materials that can be checked by the first command.',
                'It shares the same command as equipment by name, so needs to be exact match (among the aliases).',
                'e.g. `=eq heart`, `=eq fire`'
            ))
        )
        self.help_vc = (
            ('General Info (Vision Cards)', (
                self.dicts['emotes']['elements'] + ' elemental icons indicate unit-element-locked effects.',
                self.dicts['emotes']['allele'] + ' ALL icon indicates unconditional effects.',
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.'
            )),
            ('VC Info', ('**= vc / wvc / wotvvc**',
                'Argument either in full Japanese name or short English nickname bracketed in other commands.',
                'e.g. `=vc omega`'
            )),
            ('VC Search', ('**= vs / vcs / wvs /wotvvcsearch**',
                'Argument in specific effect names with following conventions:',
                ' > - slash/pierce/strike/missile/magic atk/res/pen',
                ' > - fire/ice/(etc) atk/res'
                ' > - def/spr up/pen',
                ' > - atk%/mag%/agi%/dex%/luck%/hp%/accuracy/evasion',
                ' > - single/area res',
                ' > - crit rate/evade/damage',
                ' > - ap gain, max damage, etc',
                'e.g. `=vs pierce atk`'
            )),
            ('VC Element', ('**= ve / vce / wve / wotvvcelement**',
                'Argument in element (e.g. fire).',
                'e.g. `=ve light`'
            ))
        )
        self.help_esper = (
            ('General Info (Espers)', (
                self.dicts['emotes']['limited'] + ' Ramza coin indicates time limited.',
                self.dicts['emotes']['esper'] + ' icon indicates 3-star awakened data.',
                'Adding `m` right after `=esper` or modifiers mentioned below will make them more readable in mobile.'
            )),
            ('Esper Info', ('**= esper**',
                'Argument either in full Japanese name or short English nickname bracketed in other commands.',
                'e.g. `=esper omega`'
            )),
            ('Esper Rank', ('**= esper r / esper rank**',
                'Arguments separated by `|` for each stat / effect.',
                'Will filter and rank by the first argument, while also display values of other arguments for comparison.',
                'Filter 3-star espers by `=esper r awaken` (/ `3-star`) but will not be sorted.',
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
                ' > - slash/pierce/strike/missile/magic atk/res',
                ' > - fire/ice/(etc) atk/res'
                ' > - def/spr/tp%/ap%',
                ' > - atk%/mag%/agi%/dex%/luck%/hp%/accuracy/evasion',
                ' > - crit rate/evade/damage'))
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
            args = dfwotv.shortcut.loc[argstr.lower()][col]
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
        if argstr in ['collab', 'limited']:
            return 'Limited', 'y'
        if argstr.upper() in self.dicts['esper_stats']:
            return argstr.upper(), 'STAT'
        args = argstr.split()
        if args[-1] in self.dicts['esper_suffix'].keys():
            col = self.dicts['esper_suffix'][args[-1]]
            argstr = ' '.join(args[:-1])
        else:
            for k, v in self.dicts['esper_sets'].items():
                if argstr in v:
                    col = k
                    break
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
            if row['Awaken'] != '':
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
            if 'Aliases' in df.columns:
                df_aliases = df[df['Aliases'].str.lower().str.contains(' '.join(arg).lower())]
                if len(df_aliases) > 0:
                    for _, row in df_aliases.iterrows():
                        if argstr in [a.lower() for a in row['Aliases'].split(' / ')]:
                            return 1, row
            df_name = df[df.index.str.lower().str.contains(argstr.lower())]
            if len(df_name) == 1:
                return 1, df_name.iloc[0]
            elif len(df_aliases) == 1:
                return 1, df_aliases.iloc[0]
            else:
                suggestion_list = df_name.index.tolist()
                for alias_list in df_aliases['Aliases'].tolist():
                    for suggestion in alias_list.split(' / '):
                        if suggestion != '':
                            suggestion_list.append(suggestion)
                return 0, ' / '.join(suggestion_list)
    def rand(self, *arg):
        if len(arg) == 1:
            if arg[0].isnumeric():
                return random.randint(0, int(arg[0]))
        elif len(arg) == 2:
            if arg[0].isnumeric() and arg[1].isnumeric():
                return random.randint(int(arg[0]), int(arg[1]))
        if len(arg) > 1:
            return random.choice(arg)
        else:
            return ''
    def ramada(self):
        # random fortune generator for star reading
        choice = random.choices(dfwotv.stars.index.tolist(), weights=dfwotv.stars['Weight'].tolist())[0]
        row = dfwotv.stars.iloc[choice]
        row_deco = self.dicts['emotes'][row['Rarity'].lower()] + self.dicts['emotes'][row['Emote']]
        return row['Fortune'], row_deco, row['Url']
    def update_ramada(self):
        # Generate current rate dynamically directly from data
        rate_lists = []
        for rarity in self.dicts['ramada_rarity']:
            df_row1 = dfwotv.stars[dfwotv.stars['Rarity'] == rarity]
            rarity_str = f"{self.dicts['emotes'][rarity.lower()]}: {df_row1['Weight'].sum()}%"
            implication_lists = []
            for implication in self.dicts['ramada_implication']:
                df_row2 = df_row1[df_row1['Emote'] == implication]
                if len(df_row2) > 0:
                    implication_lists.append(f"{self.dicts['emotes'][implication]} {df_row2['Weight'].sum()}%")
            rarity_str += f" ({' '.join(implication_lists)})"
            rate_lists.append(rarity_str)
        self.help_ramada = (
            ('General Info (Ramada Star Reading)',
                ('A fluff command. Enter `=stars` or `=ramada` to have Ramada read your fortune.',
                'Disclaimer: This has nothing to do with in-game mechanics or lore. Basically RNG.',
                'Note that the rate may change from time to time. Any feedback is welcome.'
            )),
            ('Current rate:', rate_lists)
        )
    def math(self, mathstr):
        # Custom math command (recursive)
        while True:
            lbrackets = []
            for i, mathchar in enumerate(mathstr):
                if mathchar == '(':
                    lbrackets.append(i)
                elif mathchar == ')':
                    if len(lbrackets) == 1:
                        bstart = lbrackets.pop()
                        bend = i
                        break
                    elif len(lbrackets) > 0:
                        lbrackets.pop()
            else:
                break
            mathstr = mathstr[0:bstart] + self.math(mathstr[bstart+1:bend]) + mathstr[bend+1:]
        for opstr, opfunc in self.opdicts.items():
            op_index_list = [i for i, a in enumerate(mathstr) if a == opstr]
            if len(op_index_list) > 0:
                op_index = op_index_list[-1]
                try:
                    leftstr = self.math(mathstr[:op_index]).strip()
                    rightstr = self.math(mathstr[op_index+1:]).strip()
                    mathstr = str(opfunc(float(leftstr), float(rightstr)))
                except ValueError:
                    if self.dicts['math_errors'][0] in [leftstr, rightstr]:
                        mathstr = self.dicts['math_errors'][0]
                    elif self.dicts['math_errors'][1] in [leftstr, rightstr]:
                        mathstr = self.dicts['math_errors'][1]
                    else:
                        mathstr = self.dicts['math_errors'][2]
                except ZeroDivisionError:
                    mathstr = self.dicts['math_errors'][0]
                except OverflowError:
                    mathstr = self.dicts['math_errors'][1]
        return mathstr

wotv_utils = WotvUtils()
