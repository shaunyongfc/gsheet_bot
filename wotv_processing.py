from gsheet_handler import df_wotv

wotv_emotes_raw = {
    'wotv_weapon': '790388262254542868',
    'wotv_armor': '790388261976670228',
    'wotv_accessory': '790388261902221333',
    'wotv_ur': '790388261906022401',
    'wotv_ssr': '790388261830524960'
}

def get_wotv_sets():
    type_set = set()
    mat_common_set = set()
    mat_rare_set = set()
    mat_crystal_set = set()

    for index, row in df_wotv.iterrows():
        type_set.add(row['Type'])
        mat_common_set.add(row['Common'])
        if row['Rare'] != '':
            mat_rare_set.add(row['Rare'])
        for a in list(row['Crystal']):
            mat_crystal_set.add(a)

    return {
        'Type': type_set,
        'Common': mat_common_set,
        'Rare': mat_rare_set,
        'Crystal': mat_crystal_set
    }

def get_wotv_emotes():
    wotv_emotes = dict()
    for k, v in wotv_emotes_raw.items():
        wotv_emotes[k.replace('wotv_', '')] = f"<:{k}:{v}>"
    return wotv_emotes

def wotv_type_convert(type_str):
    if type_str == 'アクセ':
        return 'accessory'
    elif type_str in ['軽装', '重装']:
        return 'armor'
    else:
        return 'weapon'

wotv_sets = get_wotv_sets()
wotv_emotes = get_wotv_emotes()
