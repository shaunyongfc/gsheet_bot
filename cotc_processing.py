from gsheet_handler import df_cotc

def get_cotc_emotes():
    cotc_emotes_raw = {
        'wealth': '790521500825288714',
        'power': '790521500821356554',
        'fame': '790521500905898014',
        'warrior': '790521500553576480',
        'merchant': '790521500889120768',
        'apothecary': '790521500759228416',
        'thief': '790521500859236352',
        'hunter': '790521500444131349',
        'cleric': '790521500791865394',
        'scholar': '790521500578218016',
        'dancer': '790521500754640896',
        'fire': '790521500641918987',
        'ice': '790521500884926466',
        'lightning': '790521500788457502',
        'wind': '790521500590800898',
        'light': '790521500759359529',
        'dark': '790521500960686080',
        'heal': '790521500901441587',
        'buff': '790521500770893864',
        'debuff': '790521500846915594',
        'passive': '791087444975943721',
        'universal': '791087444895203389'
    }
    cotc_emotes = dict()
    for k, v in cotc_emotes_raw.items():
        cotc_emotes[k] = f"<:cotc_{k}:{v}>"
    return cotc_emotes

cotc_dicts = {
    'ジョブ': {
        '剣士': ['warrior', 'sword', '剣', 'swordsman'],
        '商人': ['merchant', 'spear', '槍'],
        '薬師': ['apothecary', 'axe', '斧'],
        '盗賊': ['thief', 'dagger', '短剣'],
        '狩人': ['hunter', 'bow', '弓', 'ranger'],
        '神官': ['cleric', 'staff', '杖', 'priest'],
        '学者': ['scholar', 'book', '本'],
        '踊子': ['dancer', 'fan', '扇']
    },
    '属性': {
        '火': ['fire'],
        '氷': ['ice'],
        '雷': ['lightning', 'thunder'],
        '風': ['wind'],
        '光': ['light'],
        '闇': ['dark']
    },
    '影響力': {
        '富': ['wealth'],
        '権力': ['power'],
        '名声': ['fame']
    },
    'colours': {
        'fire': 0xAD3E35,
        'ice': 0X87ACE7,
        'lightning': 0xE0D774,
        'wind': 0x9ED86E,
        'light': 0xF7FCD2,
        'dark': 0x974FD1,
        'heal': 0x71CCD5,
        'buff': 0x77DADC,
        'debuff': 0xc6B3DF
    },
    'cols': {
        'ジョブ': ['物', '物威', '物全', '物全威'],
        '属性': ['属', '属威', '属全', '属全威'],
        '影響力': ['影響力']
    },
    'support': {
        '弱点以外': ['universal'],
        '回復': ['heal'],
        'バフ': ['buff'],
        'デバフ': ['debuff']
    },
    'hits': {
        '4': 4,
        '乱４': 3.5,
        '3': 3,
        '乱３': 2.5,
        '2': 2,
        '乱２': 1.5,
        '1': 1
    },
    'traveler': {
        'Passive Abilities': {
            'サポートアビ１': '-',
            'サポートアビ２': '-'
        },
        'Physical Attacks': {
            '物': 'Max ST hits',
            '物威': 'Max ST mod',
            '物全': 'Max AoE hits',
            '物全威': 'Max AoE mod'
        },
        'Elemental Attacks': {
            '属': 'Max ST hits',
            '属威': 'Max ST mod',
            '属全': 'Max AoE hits',
            '属全威': 'Max AoE mod'
        }
    },
    'Supportive Abilities': {
        '弱点以外': ('Universal breaking', 'universal'),
        '回復': ('Heals', 'heal'),
        '解除': ('Effect removal', 'heal'),
        'バフ': ('Buffs', 'buff'),
        'デバフ': ('Debuffs', 'debuff')
    },
    'emotes': get_cotc_emotes()
}

def get_cotc_label(row):
    label = ''
    for k in cotc_dicts['cols'].keys():
        label += cotc_dicts['emotes'][cotc_dicts[k][row[k]][0]]
    label += f" {row.name}"
    return label

def int_hits(hits):
    if hits == '':
        return 0
    else:
        return cotc_dicts['hits'][str(hits)]

def int_power(power):
    if power == '':
        return 0
    else:
        return int(str(power).replace('会心', ''))

def get_sorted_df(df, col, aoe=0):
    hits_ranked = []
    power_ranked = []
    for index, row in df.iterrows():
        label = get_cotc_label(row)
        if aoe:
            hits = row[cotc_dicts['cols'][col][2]]
            if hits != '':
                power = row[cotc_dicts['cols'][col][3]]
                hits_ranked.append((label, hits))
                power_ranked.append((label, power))
        else:
            # WIP need to account for difference in mod boosting
            hits = max(row[cotc_dicts['cols'][col][0]], row[cotc_dicts['cols'][col][2]], key=int_hits)
            power = max(row[cotc_dicts['cols'][col][1]], row[cotc_dicts['cols'][col][3]], key=int_power)
            hits_ranked.append((label, hits))
            power_ranked.append((label, power))
    hits_ranked.sort(key=lambda k: int_hits(k[1]), reverse=True)
    power_ranked.sort(key=lambda k: int_power(k[1]), reverse=True)
    return hits_ranked, power_ranked

def get_support_df(df, col, aoe=0, kw=''):
    char_list = []
    for index, row in df.iterrows():
        if aoe:
            eff_separated = row[col].split('、')
            for eff in eff_separated:
                if kw in eff and '全体' in eff:
                    char_list.append(f"{get_cotc_label(row)} - {eff}")
        elif kw in row[col]:
            char_list.append(f"{get_cotc_label(row)} - {row[col]}")
    return '\n'.join(char_list)
