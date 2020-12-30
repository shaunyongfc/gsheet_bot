import re
from gsheet_handler import df_wotvmats, df_wotvesper

re_numbers = re.compile(r'-?\d+$')
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
    'limited': '792712310178840596'
}

def get_wotv_sets(df_wotvmats):
    type_set = set()
    mat_common_set = set()
    mat_rare_set = set()
    mat_crystal_set = set()
    for index, row in df_wotvmats.iterrows():
        type_set.add(row['Type'])
        mat_common_set.add(row['Common'])
        if row['Rare'] != '':
            mat_rare_set.add(row['Rare'])
        for a in list(row['Crystal']):
            mat_crystal_set.add(a)
    wotv_sets = {
        'Type': type_set,
        'Common': mat_common_set,
        'Rare': mat_rare_set,
        'Crystal': mat_crystal_set
    }
    return wotv_sets

def get_wotv_sets_esper(df_wotvesper):
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
                    re_match = re_numbers.search(eff)
                    v.add(eff[:re_match.start()].strip().lower())
    return dict_sets

def get_wotv_emotes():
    wotv_emotes = dict()
    for k, v in wotv_emotes_raw.items():
        wotv_emotes[k] = f"<:wotv_{k}:{v}>"
    return wotv_emotes

def wotv_type_convert(type_str):
    if type_str == 'Accessory':
        return 'accessory'
    elif 'Armor' in type_str:
        return 'armor'
    else:
        return 'weapon'

def get_wotv_bracket():
    bracket_dict = dict()
    for ele in ['fire', 'ice', 'wind', 'earth', 'thunder', 'water', 'light', 'dark']:
        bracket_dict[f"[{ele.capitalize()}]"] = ele
        bracket_dict[ele] = f"[{ele.capitalize()}]"
    return bracket_dict

def wotv_find_col(argstr):
    args = argstr.split()
    if args[-1] in wotv_dicts['esper_suffix'].keys():
        col = wotv_dicts['esper_suffix'][args[-1]]
        argstr = ' '.join(args[:-1])
    else:
        for k, v in wotv_dicts['esper_sets'].items():
            if argstr in v:
                col = k
                break
    return col, argstr

wotv_dicts = {
    'mats_sets': get_wotv_sets(df_wotvmats),
    'esper_sets': get_wotv_sets_esper(df_wotvesper),
    'esper_suffix': {
        'atk': 'ATK Up',
        'killer': 'Killer',
        'res': 'RES Up'
    },
    'brackets': get_wotv_bracket(),
    'emotes': get_wotv_emotes(),
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
wotv_dicts['help'] =  {
    'General info': [
        'Bot prefix is =',
        'Elemental icons indicate unit-element-locked effects',
        wotv_dicts['emotes']['neutral'] + ' neutral icon indicates unconditional effects',
        wotv_dicts['emotes']['limited'] + ' xmas moogle icon indicates limited VC'],
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
