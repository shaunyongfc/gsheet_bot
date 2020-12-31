import re
from gsheet_handler import df_wotvmats, df_wotvesper

wotv_emotes_raw = {
    'weapon': '790521500788064306',
    'armor': '790521500548857867',
    'accessory': '790521500658171925',
    'ur': '790521500821749808',
    'ssr': '790521500829876244',
    'sr': '793618254529822730',
    'fire': '791969566023745547',
    'ice': '791969566308958219',
    'wind': '791969566409752576',
    'earth': '791969566477385738',
    'thunder': '791969566245781535',
    'water': '791969566254825523',
    'light': '791969565826613259',
    'dark': '791969566246436884',
    'neutral': '791969566233853952',
    'limited': '794002206642143232'
}

class WotvUtils:
    def __init__(self):
        self.reb = re.compile(r'\[[\w\/]+\]')
        self.ren = re.compile(r'-?\d+$')
        self.dicts = {
            'mats_sets': self.mat_sets(df_wotvmats),
            'eq_replace': {
                'staff': 'rod',
                'gs': 'great sword',
                'greatsword': 'great sword',
                'nb': 'ninja blade',
                'ninjablade': 'ninja blade',
                'armour': 'armor'
            },
            'esper_sets': self.esper_sets(df_wotvesper),
            'esper_suffix': {
                'atk': 'ATK Up',
                'killer': 'Killer',
                'res': 'RES Up'
            },
            'esper_stats': ['HP', 'TP', 'AP', 'ATK', 'MAG', 'DEX', 'AGI', 'LUCK'],
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
            }
        }
        self.dicts['help'] =  {
            'General info': [
                'Bot prefix is =',
                'Elemental icons indicate unit-element-locked effects',
                self.dicts['emotes']['neutral'] + ' neutral icon indicates unconditional effects',
                self.dicts['emotes']['limited'] + ' halloween pumpkin icon indicates time limited'],
            'Standard commands': ['= ping', '= help'],
            'VC Info': ['**= vc / wvc / wotvvc**',
                'Argument either in full Japanese name or short English nickname bracketed in other commands.',
                'e.g. `=vc omega`'],
            'VC Search': ['**= vs / vcs / wvs /wotvvcsearch**',
                'Argument in specific effect names with following conventions:',
                ' > - slash/pierce/strike/missile/magic atk/res/pen',
                ' > - fire/ice/(etc) atk/res'
                ' > - def/spr up/pen',
                ' > - atk%/mag%/agi%/dex%/luck%/hp%/accuracy/evasion',
                ' > - single/area res',
                ' > - crit rate/evade/damage',
                ' > - ap gain, max damage, etc',
                'e.g. `=vs pierce atk`'
                ],
            'VC Element': ['**= ve / vce / wve / wotvvcelement**',
                'Argument in element (e.g. fire)',
                'e.g. `=ve light`']
        }
    def mat_sets(self, df_wotvmats):
        dict_sets = {
            'Type': set(),
            'Common': set(),
            'Rare': set(),
            'Crystal': set()
        }
        for index, row in df_wotvmats.iterrows():
            for k, v in dict_sets.items():
                if row[k] != '':
                    v.add(row[k])
        return dict_sets
    def esper_sets(self, df_wotvesper):
        dict_sets = {
            'ATK Up': set(),
            'Killer': set(),
            'Stat Up': set(),
            'RES Up': set(),
        }
        for index, row in df_wotvesper.iterrows():
            for k, v in dict_sets.items():
                if row[k] != '':
                    for eff in row[k].split(' / '):
                        re_match = self.ren.search(eff)
                        v.add(eff[:re_match.start()].strip().lower())
        return dict_sets
    def emotes_init(self):
        wotv_emotes = dict()
        for k, v in wotv_emotes_raw.items():
            wotv_emotes[k] = f"<:wotv_{k}:{v}>"
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
    def esper_findcol(self, argstr):
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
    def emote_prefix(self, row, elestr=''):
        prefix = ''
        if elestr != '':
            prefix += self.dicts['emotes'][elestr]
        elif 'Element' in row.index:
            prefix += self.dicts['emotes'][row['Element'].lower()]
        if 'Rarity' in row.index:
            prefix += self.dicts['emotes'][row['Rarity'].lower()]
        if 'Type' in row.index:
            prefix += self.dicts['emotes'][self.eqt_convert(row['Type'])]
        if 'Limited' in row.index:
            if row['Limited'] != '':
                prefix += self.dicts['emotes']['limited']
        return prefix

wotv_utils = WotvUtils()
