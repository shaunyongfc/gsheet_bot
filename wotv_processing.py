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
    ('gil', '799228097185579028'),
    ('visiore', '799228097169457163')
)
wotv_aemotes_raw = (
    ('elements', '796963642418790451'),
)

class WotvUtils:
    def __init__(self):
        self.reb = re.compile(r'\[[\w\/]+\]') # regex for bracketed conditions
        self.ren = re.compile(r'-?\d+$') # regex for numbers
        self.dicts = {
            'mat_sets': self.mat_sets(dfwotv['eq']),
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
            'esper_sets': self.esper_sets(dfwotv['esper']),
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
            'fortunes': ( # unfinished
                'I see the stars of the Hallowed Father shining with might. A miracle could be happening!',
                'I see the stars of the Dragon King smiling with grace. I foresee a delightful outcome.'
            ),
            'embed': {
                'default_colour': 0x999999,
                'author_name': 'FFBE幻影戦争',
                'gl_author_name': 'FFBE: War of the Visions',
                'author_icon_url': 'https://caelum.s-ul.eu/1OLnhC15.png',
                'footer': 'Data Source: WOTV-CALC (Bismark)'
            },
            'changelog': (
                ('13th January 2021', (
                    'Equipment function - expansion to check via English names.',
                    'Return list of suggestions when result not found for some commands.'
                )),
                ('12th January 2021', (
                    'Equipment function - mainly to check recipes and please refer to WOTV-CALC for in-depth info. (`=help eq` for more info)',
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
            )
        }
        self.dicts['help'] = (
            ('General info', (
                'Bot prefix is `=`.',
                'Made by `Caelum#3319`, please contact me for any bug report / data correction / suggestion (depends on viability).',
                'Feel free to contact me to request adding aliases to vc/esper/equipment.',
                'JP data only for now. Would need collaborator(s) to implement GL data. Please contact me if interested.',
                'For programming reason, element name lightning is all replaced by thunder (because the text contains another element light).'
            )),
            ('Standard commands', ('`=ping`', '`=help`', '`=changelog/version`')),
            ('Weekly', ('Enter `=weekly` for dungeon bonus of days of the week.',)),
            ('News', ('Enter `=news` for link to news.',)),
            ('Equipment', ('Enter `help eq` for more info.',)),
            ('VC', ('Enter `=help vc` for more info.',)),
            ('Esper', ('Enter `=help esper` for more info.',))
        )
        self.dicts['help_eq'] = (
            ('General info', (
                'The function is mainly for recipes checking, for in-depth equipment info please refer to WOTV-CALC.',
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
                'e.g. `=eq t accessory`, `=eq a raid`'
            )),
            ('Equipment by material', ('**= eq**',
                'Argument is one of the materials that can be checked by the first command.',
                'e.g. `=eq heart`, `=eq fire`'
            )),
            ('Equipment by name', ('**= eq**',
                'Argument is by equipment name (subject to name availability).',
                'e.g. `=eq ribbon`'
            ))
        )
        self.dicts['help_vc'] = (
            ('General info', (
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
        self.dicts['help_esper'] = (
            ('General info', (
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
        self.weekly_init()
    def weekly_init(self):
        msg_list = []
        weekly_tuples = [
            ('Sunday', ('gil',)),
            ('Monday', ('kame',)),
            ('Tuesday', ('fire', 'wind')),
            ('Wednesday', ('water', 'ice')),
            ('Thursday', ('earth', 'dark')),
            ('Friday', ('thunder', 'light'))
        ]
        for day, daylist in weekly_tuples:
            msg_line = day + ': '
            for ele in daylist:
                msg_line += self.dicts['emotes'][ele]
            msg_list.append(msg_line)
        msg_list.append('Saturday: :dango:')
        self.weekly = '\n'.join(msg_list)
    def mat_sets(self, df):
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
                        re_match = self.ren.search(eff)
                        v.add(eff[:re_match.start()].strip().lower())
        return dict_sets
    def emotes_init(self):
        wotv_emotes = dict()
        for k, v in wotv_emotes_raw:
            wotv_emotes[k] = f"<:wotv_{k}:{v}>"
        for k, v in wotv_aemotes_raw:
            wotv_emotes[k] = f"<a:wotv_{k}:{v}>"
        return wotv_emotes
    def bracket_init(self):
        bracket_dict = dict()
        for ele in ['fire', 'ice', 'wind', 'earth', 'thunder', 'water', 'light', 'dark']:
            bracket_dict[f"[{ele.capitalize()}]"] = ele
            bracket_dict[ele] = f"[{ele.capitalize()}]"
        return bracket_dict
    def eqt_convert(self, type_str):
        if type_str == 'Accessory':
            return 'accessory'
        elif 'Armor' in type_str:
            return 'armor'
        else:
            return 'weapon'
    def shortcut_convert(self, argstr, col='VC'):
        try:
            args = dfwotv['shortcut'].loc[argstr.lower()][col]
            if args != '':
                return args
            else:
                return argstr
        except:
            return argstr
    def esper_findcol(self, argstr):
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
    def name_str(self, row, name='NAME', alias=1, elestr=''):
        namestr = ''
        if elestr != '':
            namestr += self.dicts['emotes'][elestr]
        elif 'Element' in row.index:
            namestr += self.dicts['emotes'][row['Element'].lower()]
        if 'Rarity' in row.index:
            namestr += self.dicts['emotes'][row['Rarity'].lower()]
        if 'Type' in row.index:
            namestr += self.dicts['emotes'][self.eqt_convert(row['Type'])]
        if 'Limited' in row.index:
            if row['Limited'] != '':
                namestr += self.dicts['emotes']['limited']
        if 'Awaken' in row.index:
            if row['Awaken'] != '':
                namestr += self.dicts['emotes']['esper']
        if name == 'NAME':
            namestr += f" {row.name}"
        else:
            namestr += f" {name}"
        if 'Aliases' in row.index and alias:
            engstr = row['Aliases'].split(' / ')[0]
            if engstr != '':
                namestr += f" ({engstr})"
        return namestr
    def find_row(self, df, arg):
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

wotv_utils = WotvUtils()
