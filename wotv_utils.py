import re
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs


class WotvUtils:
    """An object that contains multiple utility functions for WOTV."""
    def __init__(self, dfwotv):
        """Object initialisation with a special dataframe handler object
        and a dictionary of ids as inputs.
        """
        self.dfwotv = dfwotv
        # Regex for bracketed conditions.
        self.reconditions = re.compile(r'\[[\w\/]+\]')
        # Regex for numbers including negative.
        self.revalues = re.compile(r'-?\d+$')
        # Regex for symbols to be omitted for url generation.
        self.resymbols = re.compile(r'[^\w ]')
        # Dictionary to store various contents
        self.dict = {
            'eq_lists': {
                'Type': ('t',),
                'Acquisition': ('a',),
                'Regular': ('n', 'common'),
                'Rare': ('r',),
                'Cryst': ('c', 'e', 'element'),
                'Ore': ('o',)
            },
            'esper_suffix': {
                'atk': 'ATK Up',
                'killer': 'Killer',
                'res': 'RES Up'
            },
            'esper_stats': {
                'HP': (2500, 4500),
                'TP': (120, 200), # Unused as of 20230826
                'AP': (100, 200),  # Unused as of 20230826
                'ATK': (350, 430),
                'MAG': (350, 430),
                'DEX': (160, 260),  # Unused as of 20230826
                'AGI': (45, 65),  # Unused as of 20230826
                'LUCK': (160, 200),  # Unused as of 20230826
            },
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
            'tm_stats': (
                'HP', 'TP', 'AP', 'ATK', 'MAG', 'DEF', 'SPR', 'ACC', 'EVA',
                'AGI', 'DEX', 'CRIT', 'CEVA', 'LUCK'
            ),
            'colours': { # Embed colour hex codes.
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
            'embed': { # Default embed settings.
                'default_colour': 0x999999,
                'author_name': 'FFBE幻影戦争',
                'gl_author_name': 'FFBE: War of the Visions',
                'author_icon_url': 'https://caelum.s-ul.eu/1OLnhC15.png'
            },
            'paramcalc': { # Default parameter values and aliases.
                'agi': (100, ('agi', 'speed', 'spd', 'agility')),
                'dex': (350, ('dex', 'dexterity')),
                'luck': (350, ('luck', 'luc', 'luk')),
                'acc': (0, ('acc', 'accuracy', 'hit')),
                'eva': (0, ('eva', 'evasion', 'evade', 'avoid')),
                'crit': (0, ('crit', 'critical', 'crit rate',
                             'critical rate')),
                'c.avo': (0, ('crit avoid', 'crit avo', 'critical avoidance',
                              'ca', 'cavo', 'c. avo', 'c.avo'))
            },
            'calcurl': ( # replace str for url generation
                ('é', 'e'),
                (' ', '-')
            ),
            'ramada_rarity': ('R', 'SR', 'SSR', 'UR'),
            'ramada_implication': ('up', 'neutral', 'down'),
            'event_tuples': (
                (('banner', 'gacha', 'step', 'pull', 'sale', 'fest'), 'visiore'),
                (('recipe', 'currency', 'acquisition'),'recipe'),
                (('pvp', 'arena', 'match', 'guild'), 'party'),
                (('event', 'raid', 'tower', 'box', 'challenge'), 'event'),
                (('shop', 'whimsy', 'medal'), 'shop'),
                (('update', 'change', 'fix', 'new', 'ex', 'ma2', 'eq+'), 'update')
            ),
            'weapons': ('axe', 'book', 'bow', 'dagger', 'fist', 'glove', 'gs',
                        'gun', 'katana', 'mace', 'nb', 'spear', 'staffa',
                        'staffb', 'sworda', 'swordb', 'swordc',), # for vc job type
            'Weapons': ('SwordA', 'SwordB', 'SwordC', 'StaffA', 'StaffB', 'GS',
                        'Spear', 'Axe', 'Bow', 'Gun', 'Fist', 'Dagger', 'NB',
                        'Katana', 'Mace', 'Glove', 'Book'), # capitalized and ordered
            'weapon_dict': { # representative job
                'sworda': 'Red Mage',
                'swordb': 'Warrior',
                'swordc': 'Knight',
                'staffa': 'Black Mage',
                'staffb': 'Devout',
            },
            'rarity': ('UR', 'SSR', 'SR', 'R', 'N'),
            'history_tuples': ( # process args
                (('eq', 'equip'), (['Release', 'Release+'], [], [], []), 3),
                (('hq',), (['Release+'], [], [], []), 6),
                (('vc', 'vcs'), ([], ['Release'], [], ['Release', 'Release3']), 6),
                (('unit', 'units'), ([], [], ['Release', 'EX', 'TR', 'MA2'], []), 3),
                (('ex',), ([], [], ['EX'], []), 6),
                (('tr', 'rein', '140'), ([], [], ['TR'], []), 3),
                (('ma2',), ([], [], ['MA2'], []), 6)
            ),
            'history_replace': { # column name to heading
                'Release+': 'Heartquartz',
                'Release3': '3-Star',
            },
            'history_formats': ( # tolerance processing for date
                '%Y%m',
                '%y%m',
                '%B%Y',
                '%b%Y',
                '%B%y',
                '%b%y'
            ),
            'history_headings': ( # to order properly
                'Unit', 'EX', 'TR UR', 'TR SSR', 'TR SR', 'TR R', 'TR N',
                'MA2', 'VC', 'EQ', 'Heartquartz', 'Esper', '3-Star'
            ),
            'gr_debuffs': (
                'Slow', 'AGI', 'Single RES', 'Area RES', 'ELE RES', 'All Elemental RES',
                'Slash RES', 'Pierce RES', 'Strike RES', 'Missile RES', 'Magic RES', 'All Type RES',
                'DEF', 'SPR', 'Special'
            ),
            'gr_types': {
                'SL': 'Slash',
                'PI': 'Pierce',
                'ST': 'Strike',
                'MS': 'Missile',
                'MG': 'Magic',
                'TL': 'Typeless'
            }
        }
        self.emotes_init()
        self.update_text()
        # Generate the weekly command string.
        msg_list = []
        weekly_tuples = [
            ('`Monday   `', ('kame', 'pot', 'materias'), ('All',)),
            ('`Tuesday  `', ('fire', 'wind', 'materia_i'), ('Sword', 'Greatsword', 'Axe')),
            ('`Wednesday`', ('water', 'ice', 'materia_h'), ('Spear', 'Gun', 'Accessory')),
            ('`Thursday `', ('earth', 'dark', 'materia_f'), ('Mace', 'Bow', 'Armour')),
            ('`Friday   `', ('thunder', 'light', 'materia_o'), ('Staff', 'Katana', 'Dagger')),
            ('`Saturday `', ('pink', 'gil', 'materia_w'), ('Fist', 'Ninjablade', 'Accessory')),
            ('`Sunday   `', ('gil', 'materia_s'), ('Glove', 'Book', 'Armour')),
        ]
        for day, daylist, booklist in weekly_tuples:
            msg_line = day + ': '
            for ele in daylist:
                msg_line += self.dict['emotes'][ele]
            msg_line += f" (Books: {', '.join(booklist)})"
            msg_list.append(msg_line)
        self.weekly = '\n'.join(msg_list)
        # Initialise existing news entries.
        r = requests.get("https://players.wotvffbe.com/")
        soup = bs(r.content, features="lxml")
        articles = soup.find_all("article")
        self.news_entries = set([article['data-id'] for article in articles])

    def update_text(self):
        """
        Initialise or update various help text from sheet data.
        """
        # Help strings
        ## General help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_general']
        self.help_general = [
            (row['Title'], row['Body']) for _, row in df.iterrows()]
        ## Event help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_events']
        self.help_events = [
            (row['Title'], row['Body']) for _, row in df.iterrows()]
        ## Param help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_param']
        self.help_param = []
        for _, row in df.iterrows():
            if row['Title'] == 'Default Values':
                body = row['Body'].replace('[PLACEHOLDER]',
                    ', '.join([k + ' ' + str(v[0]) for k, v in \
                    self.dict['paramcalc'].items()]))
            else:
                body = row['Body']
            self.help_param.append((row['Title'], body))
        ## EQ Help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_eq']
        self.help_eq = []
        for _, row in df.iterrows():
            if row['Title'] == 'Equipment Help':
                body = row['Body'].replace('[PLACEHOLDER1]',
                    self.dict['emotes']['limited'])
                body = body.replace('[PLACEHOLDER2]',
                    self.dict['emotes']['heartquartzs'])
            else:
                body = row['Body']
            self.help_eq.append((row['Title'], body))
        ## Unit Help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_unit']
        self.help_unit = []
        for _, row in df.iterrows():
            self.help_unit.append((row['Title'], row['Body']))
        ## VC Help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_vc']
        self.help_vc = []
        for _, row in df.iterrows():
            if row['Title'] == 'Vision Card Help':
                body = row['Body'].replace('[PLACEHOLDER1]',
                    self.dict['emotes']['elements'])
                body = body.replace('[PLACEHOLDER2]',
                    self.dict['emotes']['allele'])
                body = body.replace('[PLACEHOLDER3]',
                    self.dict['emotes']['vcmax'])
                body = body.replace('[PLACEHOLDER4]',
                    self.dict['emotes']['limited'])
            else:
                body = row['Body']
            self.help_vc.append((row['Title'], body))
        ## Esper Help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_esper']
        self.help_esper = []
        for _, row in df.iterrows():
            if row['Title'] == 'Esper Help':
                body = row['Body'].replace('[PLACEHOLDER]',
                    self.dict['emotes']['limited'])
            else:
                body = row['Body']
            self.help_esper.append((row['Title'], body))
        ## Materia Help
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_materia']
        self.help_materia = []
        for _, row in df.iterrows():
            self.help_materia.append((row['Title'], row['Body']))
        ## Ramada Help
        row = self.dfwotv.text[self.dfwotv.text['Key'] == 'help_ramada'].iloc[0]
        rate_lists = []
        for rarity in self.dict['ramada_rarity']:
            df_row1 = self.dfwotv.stars[self.dfwotv.stars['Rarity'] == rarity]
            rarity_str = ''.join((f"{self.dict['emotes'][rarity.lower()]}: ",
                                  f"{df_row1['Weight'].sum()}%"))
            implication_lists = []
            for implication in self.dict['ramada_implication']:
                df_row2 = df_row1[df_row1['Emote'] == implication]
                if len(df_row2) > 0:
                    implication_str = ''.join((
                        f"{self.dict['emotes'][implication]} ",
                        f"{df_row2['Weight'].sum()}%"))
                    implication_lists.append(implication_str)
            rarity_str += f" ({' '.join(implication_lists)})"
            rate_lists.append(rarity_str)
        self.help_ramada = ((row['Title'], row['Body']),
                            ('Current rate:', '\n'.join(rate_lists)))
        # Materia information
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'materia_set']
        self.materia_set = [
            (row['Title'], row['Body']) for _, row in df.iterrows()]
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'materia_substat']
        self.materia_substat = [
            (row['Title'], row['Body']) for _, row in df.iterrows()]
        df = self.dfwotv.text[self.dfwotv.text['Key'] == 'materia_passive']
        self.materia_passive = [
            (row['Title'], row['Body']) for _, row in df.iterrows()]

        # Various sets
        ## EQ sets
        self.dict['eq_sets'] = {
            'Type': set(),
            'Acquisition': set(),
            'Regular': set(),
            'Rare': set(),
            'Cryst': set(),
            'Ore': set()
        }
        for _, row in self.dfwotv.eq.iterrows():
            for k, v in self.dict['eq_sets'].items():
                if row[k]:
                    if k == 'Cryst' and len(row[k]) > 1:
                        v = v.union(set(row[k]))
                    else:
                        v.add(row[k])

        ## Esper sets
        self.dict['esper_sets'] = {
            'ATK Up': set(),
            'Killer': set(),
            'Stat Up': set(),
            'RES Up': set(),
        }
        self.dict['esper_sets_lower'] = {
            'ATK Up': set(),
            'Killer': set(),
            'Stat Up': set(),
            'RES Up': set(),
        }
        for _, row in self.dfwotv.esper.iterrows():
            for k in self.dict['esper_sets'].keys():
                if row[k]:
                    for eff in row[k].split(' / '):
                        re_match = self.revalues.search(eff)
                        self.dict['esper_sets'][k]\
                            .add(eff[:re_match.start()].strip())
                        self.dict['esper_sets_lower'][k]\
                            .add(eff[:re_match.start()].strip().lower())

        ## VC and EQ/TM sets
        passive_tuples = (
            ('vc_set', ('Unit', 'Party', 'Party Max'), self.dfwotv.vc),
            ('eq_set', ('Passive', 'Extra'), self.dfwotv.eq),
            ('eq_set', ('Passive',), self.dfwotv.tm),
            ('tm_set', ('Skill',), self.dfwotv.tm),
        )
        for dict_entry, dict_cols, dict_df in passive_tuples:
            if dict_entry not in self.dict:
                self.dict[dict_entry] = set()
            for _, row in dict_df.iterrows():
                for col in dict_cols:
                    for eff in row[col].split(' / '):
                        effstr = eff
                        re_match = self.reconditions.search(eff)
                        if re_match:
                            effstr = effstr[re_match.end():].strip()
                        re_match = self.revalues.search(effstr)
                        if re_match:
                            effstr = effstr[:re_match.start()].strip()
                        self.dict[dict_entry].add(effstr)
            self.dict[dict_entry].remove('')

    def emotes_init(self):
        """Only run once to generate the dictonary entry."""
        # Raw numbers of emotes uploaded into Discord copied manually.
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
            ('limited', '881743510125043753'),
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
            ('party', '809924634903838810'),
            ('vcmax', '881743510145998848'),
            ('materia_i', '914818426114027530'),
            ('materia_f', '914818426072096798'),
            ('materia_h', '914818426072096788'),
            ('materia_o', '914818426126626837'),
            ('materia_w', '914818426147602442'),
            ('materia_s', '914818426097254440'),
        )
        wotv_aemotes_raw = (
            ('elements', '796963642418790451'),
            ('materias', '913749364810338315'),
            ('heartquartzs', '972379294682734602'),
            ('w_axe', '1060023590956838922'),
            ('w_book', '1060023595058872370'),
            ('w_bow', '1060024865425465444'),
            ('w_dagger', '1060024873595981924'),
            ('w_fist', '1060024878662684712'),
            ('w_glove', '1060025022871248936'),
            ('w_gs', '1060025025333301268'),
            ('w_gun', '1060025029364039711'),
            ('w_katana', '1060023459855470663'),
            ('w_mace', '1060023461780652102'),
            ('w_nb', '1060023465215803513'),
            ('w_spear', '1060023468680286299'),
            ('w_staffa', '1060023475189854238'),
            ('w_staffb', '1060023473197568000'),
            ('w_sworda', '1060023478843088976'),
            ('w_swordb', '1060023482236289164'),
            ('w_swordc', '1060023484689961007'),
        )
        wotv_emotes = dict()
        for k, v in wotv_emotes_raw:
            wotv_emotes[k] = f"<:wotv_{k}:{v}>"
        for k, v in wotv_aemotes_raw:
            wotv_emotes[k] = f"<a:wotv_{k}:{v}>"
        self.dict['emotes'] = wotv_emotes

    def get_news(self):
        """Called periodically to fetch news site."""
        r = requests.get("https://players.wotvffbe.com/")
        return bs(r.content, features="lxml")

    def shortcut_convert(self, args, col='VC'):
        """Convert shortcuts into corresponding contents."""
        try:
            argshort = self.dfwotv.shortcut.loc[args.lower()][col]
            if argshort != '':
                return argshort
            else:
                return args
        except KeyError:
            return args

    def name_str(self, row, element=1, group=1, rarity=1, type=0, limited=1,
                 name='English', backup_name='Aliases'):
        """Process an entry to return the name string decorated with
        emotes.
        row: DataFrame series
        element, group, rarity, type, limited: 1 or 0 to indicate whether to include
        name: 'NAME' to use the row name as name.
              If a column name is applicable, the column is used.
              Otherwise, use the name as name.
        backup_name: Same as name but as backup if name is not available.
        """
        # EQ: EQ Name (JP), English, Aliases
        # TM: Unit Name (JP), English, TM (JP), TM (EN), Aliases
        # VC: VC Name (JP), English, Aliases
        # Esper: Esper (JP), English, Aliases
        prefix_str = ''
        name_str = ''
        # Prefix icons
        if 'Element' in row.index and element:
            prefix_str += self.dict['emotes'][row['Element'].lower()]
        if 'Group' in row.index and group:
            if row['Group'] in self.dict['Weapons']: # In case of Hope
                prefix_str += self.dict['emotes'][f"w_{row['Group'].lower()}"]
        if 'Rarity' in row.index and rarity:
            prefix_str += self.dict['emotes'][row['Rarity'].lower()]
        if 'Type' in row.index and type: # EQ
            prefix_str += self.dict['emotes'][self.eqt_convert(row['Type'])]
        if 'Limited' in row.index and limited:
            if row['Limited'] != '':
                prefix_str += self.dict['emotes']['limited']
        # Entry name
        if name == 'NAME': # Used if available
            name_str = row.name
        elif name in row.index:
            name_str = row[name].split(' / ')[0]
        else:
            name_str = name
        if not name_str:
            if backup_name == 'NAME': # Backup
                name_str = row.name
            elif backup_name in row.index:
                name_str = row[backup_name].split(' / ')[0]
            else:
                name_str = backup_name
        return f"{prefix_str} {name_str}"

    def eq_str(self, row):
        """Return appropriate string for equipment search / list command."""
        row_str = self.name_str(row)
        if row['Restriction']:
            row_str += f" [*{row['Restriction']}*]"
        if row['Passive']:
            row_str += f" - {row['Passive']}"
        if row['Extra']:
            row_str += f" {self.dict['emotes']['heartquartzs']} {row['Extra']}"
        return row_str

    def tm_str(self, row, mode='stat'):
        """Return appropriate string for trust master search command."""
        if mode == 'en':
            # Proper TM name only, for use of titles
            return self.name_str(row, name='TM English', backup_name='TM Name',
                                 element=0, group=0, type=1)
        elif mode == 'jp':
            return self.name_str(row, name='TM Name',
                                 element=0, group=0, type=1)
        row_str = self.name_str(row, element=0, group=0, type=1)
        if row['Restriction']:
            row_str += f" [*{row['Restriction']}*]"
        stat_value = []
        if mode == 'stat':
            for stat_name in self.dict['tm_stats']:
                if row[stat_name] != '':
                    stat_value.append(f"**{stat_name}** {row[stat_name]}")
            row_str += f" - {' '.join(stat_value)}"
            if row['Passive']:
                row_str += f" - {row['Passive']}"
        elif mode == 'skill':
            row_str += f" - {row['Skill']}"
            if row['S Area'] == 'Self':
                row_str += ' (*Self x'
            elif row['S Range'] == 0:
                row_str += f" (*{row['S Area']} Area x"
            else:
                row_str += f" (*Range {row['S Range']} {row['S Area']} x"
            row_str += f"__{row['S Uses']}__*)"
        return row_str

    def calc_url(self, category, name_str):
        """Generate URLs for Bismark's WOTC-CALC given raw name string."""
        calc_url = f"https://wotv-calc.com/JP/{category}/"
        urlstr = name_str.lower().replace('-', ' ')
        urlstr = self.resymbols.sub('', urlstr)
        for a, b in self.dict['calcurl']:
            urlstr = urlstr.replace(a, b)
        return f"[{name_str}]({calc_url + urlstr})"

    def find_row(self, df, args, col_list='DEFAULT'):
        """Tolerance processing for query to find the correct entry.
        Return a tuple with a boolean indicating the correct entry is found.
        If false, return a list of suggestions."""
        try:
            args.encode('ascii')
            args = args.lower()
        except UnicodeEncodeError: # Check if arguments are in Japanese
            # Different space for Japanese
            args = '　'.join(args.split())
        # Exact match first
        if args in df.index: # Exact match + match case
            row = df.loc[args]
            return 0, row
        df_name = df[df.index.str.lower().str.contains(args)]
        if len(df_name):
            for index, row in df_name.iterrows():
                if args == index.lower():
                    return 0, row
        if col_list == 'DEFAULT':
            col_list = ('English', 'Aliases', 'TM Name', 'TM English')
        df_tuples = []
        for col in col_list:
            if col in df.columns:
                df_filtered = df[df[col].str.lower().str.contains(args)]
                if len(df_filtered):
                    for _, row in df_filtered.iterrows():
                        if args in row[col].lower().split(' / '):
                            return 0, row
                    df_tuples.append((col, df_filtered))
        # Subset match & generate list of suggestions
        if len(df_name) == 1:
            return 0, df_name.iloc[0]
        suggestion_list = df_name.index.tolist()
        for col, col_df in df_tuples:
            if len(col_df) == 1:
                return 0, col_df.iloc[0]
            suggestion_list.extend(col_df[col].tolist())
        return 1, suggestion_list

    def unit_list(self, filter_list):
        """Given a list of filter args, return units belonging to the filters
        separated by element/group and rarity.
        """
        list_dict = dict()
        filter_list.append('all')
        # For element argument
        if filter_list[0] in self.dict['colours'].keys():
            df = self.dfwotv.tm[self.dfwotv.tm['Element'].str.lower().isin(filter_list)]
            split_col = 'Group'
            for group in self.dict['Weapons']:
                list_dict[group] = dict()
        # For weapon group argument
        elif filter_list[0] in self.dict['weapons']:
            df = self.dfwotv.tm[self.dfwotv.tm['Group'].str.lower().isin(filter_list)]
            split_col = 'Element'
            for element in self.dict['colours'].keys():
                list_dict[element.title()] = dict()
        else:
            return 1, None
        list_dict['nope'] = dict()
        list_dict['ALL'] = dict()
        for unit_dict in list_dict.values():
            for rarity in self.dict['rarity']:
                unit_dict[rarity] = []
        # Add unit entry with respect to element/group and rarity
        for _, row in df.iterrows():
            if row[split_col] not in list_dict:
                list_dict['nope'][row['Rarity']].append(row['English'])
                continue
            list_dict[row[split_col]][row['Rarity']].append(row['English'])
        return 0, list_dict

    def get_cryst(self, row):
        """Given DataFrame row of equipment, return text string for the
        corresponding cryst.
        """
        text_list = []
        for cryst_ele in list(row['Cryst']):
            # Add Mega if UR crysts. Remove Mega if SSR.
            if row['Rarity'] == 'UR':
                engstr = self.dfwotv.mat.loc[cryst_ele]['Aliases']\
                    .split(' / ')[0].replace('(Mega)C', 'Megac')
            else:
                engstr = self.dfwotv.mat.loc[cryst_ele]['Aliases']\
                    .split(' / ')[0].replace('(Mega)', '')
            text_list.append(f"- {cryst_ele} ({engstr})")
        return '\n'.join(text_list)


    def eqt_convert(self, type_str):
        """Used to convert equipment type string into type emote shortcut."""
        if type_str == 'Accessory':
            return 'accessory'
        elif 'Armor' in type_str:
            return 'armor'
        else:
            return 'weapon'

    def esper_est(self, row, return_tuple=1):
        """
        Add board stats to esper base stats for total stat estimation.
        """
        row_est = dict()
        for stat in self.dict['esper_stats'].keys():
            row_est[stat] = [[], row[stat], row[stat]]
            # list of description strs, low estimate, high estimate
        for eff in row['Stat Up'].split(' / '):
            eff_str = ' '.join(eff.split()[:-1])
            eff_value = int(eff.split()[-1])
            for stat in row_est.keys():
                if eff_str == f"{stat}%":
                    row_est[stat][0].append(f"+{eff_value}%")
                    row_est[stat][1] += (self.dict['esper_stats'][stat][0] \
                                        * eff_value) // 100
                    row_est[stat][2] += (self.dict['esper_stats'][stat][1] \
                                        * eff_value) // 100
                elif eff_str == stat:
                    row_est[stat][0].append(f"+{eff_value}")
                    row_est[stat][1] += eff_value
                    row_est[stat][2] += eff_value
        if return_tuple:
            return row_est
        row_average = dict()
        for col, row_tuple in row_est.items():
            row_average[col] = (row_tuple[1] + row_tuple[2]) // 2
        return row_average

    def esper_findcol(self, args):
        """
        Find the correct column to search for an effect from an argument
        string.
        """
        if args[:3] == 'ALL':
            return args[4:], 'ALL'
        if args in ['collab', 'limited']:
            return 'Limited', 'y'
        if args.upper() in self.dict['esper_stats'].keys():
            return args.upper(), 'STAT'
        col = 'NOTFOUND'
        arg = args.split()
        if arg[-1] in self.dict['esper_suffix'].keys():
            col = self.dict['esper_suffix'][arg[-1]]
            args = ' '.join(arg[:-1])
        else:
            for k, v in self.dict['esper_sets_lower'].items():
                if args in v:
                    col = k
                    break
            else:
                col_list = []
                for k, v in self.dict['esper_sets_lower'].items():
                    for v_item in v:
                        if args in v_item:
                            col_list.append(k)
                if len(col_list) == 1:
                    col = col_list[0]
        return col, args

    def gr_parse(self, effstr, include_type=False, omit_1H=True, include_value=True):
        """Parse the contents in the tm (unit) google sheet regarding debuffs
        and multihits for guild raid functionality.
        """
        parsed_str = ''
        # Prefixes
        while effstr:
            try:
                prefix, suffix = effstr.split(' ', 1)
            except ValueError:
                break
            if prefix in ('LB', 'Slow', 'Crit'):
                parsed_str += f"{prefix} "
                effstr = suffix
            elif prefix == 'OE':
                parsed_str += 'Off-Element '
                effstr = suffix
            else:
                break
        if effstr[0] == 'A':
            parsed_str += 'AoE '
            effstr = effstr[1:]
        # Hits
        if effstr[0] == '0':
            parsed_str += 'Non-Attack'
            effstr = effstr[2:]
        else:
            if not omit_1H or effstr[0] != '1':
                parsed_str += f"{effstr[0]}-Hit"
            if include_type:
                parsed_str += f" {self.dict['gr_types'][effstr[2:4]]}"
            effstr = effstr[4:]
        # Values
        if effstr:
            parsed_str += f" `{effstr.strip()}`"
        return parsed_str.strip()

    def rand(self, ffbe, *arg):
        """Random command to return a random value depending on given inputs.
        FFBE indicates whether only non-WOTV avatars are used.
        Return a tuple of multiple message components.
        """
        randstr = ''
        incorrect = 0
        # Check if 1 or 2 numbers are input.
        if len(arg) == 1:
            if arg[0].isnumeric():
                randstr = str(random.randint(0, int(arg[0])))
        elif len(arg) == 2:
            if arg[0].isnumeric() and arg[1].isnumeric():
                randstr = str(random.randint(int(arg[0]), int(arg[1])))
        # If not numbers.
        if randstr == '':
            if len(arg) > 1:
                if '|' in arg:
                    arg = [a.strip() for a in ' '.join(arg).split('|')]
                # Random choice of strings.
                randstr = random.choice(arg)
            else:
                # Insufficient input.
                incorrect = 1
        if ffbe: # Return only non-WOTV characters if server is FFBE.
            df = self.dfwotv.rand[self.dfwotv.rand['FFBE'] == 1]
        else:
            df = self.dfwotv.rand
        df_index = df[df['Incorrect'] == incorrect].sample().index[0]
        df_row = df.loc[df_index]
        return (incorrect, df_row['Name'], df_row['Element'], df_row['Url'],
                df_row['String'].replace('CHOICE', randstr))

    def ramada(self, reader):
        """Random fortune generator for star reading.
        Return a tuple of multiple message components."""
        choice = random.choices(self.dfwotv.stars.index.tolist(),
                            weights=self.dfwotv.stars['Weight'].tolist())[0]
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
            row_title = ''.join((f"Moore Star Reading ",
                                 self.dict['emotes'][row['Rarity'].lower()],
                                 self.dict['emotes'][row['Emote']]))
        elif reader == 'ramada':
            row_url = row['Url']
            row_title = ''.join((f"Ramada Star Reading ",
                                 self.dict['emotes'][row['Rarity'].lower()],
                                 self.dict['emotes'][row['Emote']]))
        return row['Fortune'], row_title, row_url
