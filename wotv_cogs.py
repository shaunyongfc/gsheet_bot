import discord
import random
import itertools
import pandas as pd
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from gsheet_handler import DfHandlerWotv
from wotv_utils import WotvUtils

dfwotv = DfHandlerWotv()
wotv_utils = WotvUtils(dfwotv)
MYDTFORMAT = '%Y/%m/%d %H:%M' # For events sheet
PRINTDTFORMAT = '%b %d, %H:%M' # For events command
DFDTFORMAT = '%Y%m%d' # For other sheets
EMBEDDTFORMAT = '%d %B %Y' # For ohter commands
BLANK = '\u200b'


class EmbedWotv():
    """
    Support functions for discord commands to generate embeds for specific
    purposes. Separated from the cogs to facilitate redirection.
    """
    @classmethod
    def split_field(cls, f_name, entry_list, max_lines=0):
        """Given list of line entries (str), split into list of field tuples of
        field name (str) and value (str) with respect to character limits."""
        if not entry_list: # Empty list
            return entry_list
        tuple_list = []
        f_value = '\n'.join(entry_list)
        if len(f_value) < 1020 and not max_lines: # Short enough to fit into 1
            return [(f_name, f_value)]
        checkpoint = 0
        char_count = -2
        line_count = 0
        for i, entry in enumerate(entry_list):
            char_count += len(entry) + 2
            line_count += 1
            if char_count > 1000 or (max_lines and line_count > max_lines):
                # Add entries so far to the list (field) and add new field
                f_value = '\n'.join(entry_list[checkpoint:i])
                tuple_list.append((f_name, f_value))
                char_count = len(entry)
                line_count = 1
                if not checkpoint: # No need to repeat headings
                    f_name = BLANK
                checkpoint = i
        f_value = '\n'.join(entry_list[checkpoint:])
        tuple_list.append((f_name, f_value))
        return tuple_list

    @classmethod
    def split_embed(cls, embed, tuple_list, inline_num=0, embed_limit=10):
        """Given list of tuples of field name (str) and value (str),
        split into embeds with respect to discord limitations.
        Returns empty list if out of bounds.

        From website:
        Embed titles are limited to 256 characters
        Embed descriptions are limited to 2048 characters
        There can be up to 25 fields
        The name of a field is limited to 256 characters and its value to 1024 characters
        The footer text is limited to 2048 characters
        The author name is limited to 256 characters
        In addition, the sum of all characters in an embed structure must not exceed 6000 characters
        A webhook can have 10 embeds per message
        A webhook can only send 30 messages per minute
        """
        embed_colour = embed.colour
        char_count = 0
        field_count = 0
        embed_list = []
        if inline_num:
            inline = True
        else:
            inline = False
        for f_name, f_value in tuple_list:
            if inline_num == 2 and field_count % 3 == 2:
                # Add blank field to for 2 column embeds
                embed.add_field(name=BLANK, value=BLANK, inline=True)
                char_count += len(BLANK) * 2
                field_count += 1
            field_char = len(f_name) + len(f_value)
            if char_count + field_char > 5500 or field_count >= 24:
                # Add current embed to the list and reinitialise new embed
                embed_list.append(embed)
                if len(embed_list) >= embed_limit: # Exceeded embed limit
                    return []
                embed = discord.Embed(colour=embed_colour)
                char_count = 0
                field_count = 0
            embed.add_field(name=f_name, value=f_value, inline=inline)
            char_count += field_char
            field_count += 1
        if inline_num == 2 and field_count % 3 == 2:
            # To balance display so that the last row doesn't display awkwardly
            embed.add_field(name=BLANK, value=BLANK, inline=True)
        embed_list.append(embed)
        return embed_list

    @classmethod
    def unitinfo(cls, arg):
        """Generates unit information embed."""
        row_error, row = wotv_utils.find_row(dfwotv.tm, ' '.join(arg),
                                             col_list=('English', 'Aliases'))
        if row_error:
            return row_error, row
        # Basic information
        description = f"Cost: {row['Cost']}\nGroup: {row['Group']}"
        if row['Group'].lower() in wotv_utils.dict['weapon_dict'].keys():
            description += f" ({wotv_utils.dict['weapon_dict'][row['Group'].lower()]})"
        embed = discord.Embed(
            title=wotv_utils.name_str(row, type=0),
            description=description,
            colour=wotv_utils.dict['colours'][row['Element'].lower()]
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/units',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        # TM information
        embed.add_field(
            name='Trust Master',
            value=f"{wotv_utils.name_str(row, name='TM English', backup_name='TM Name', element=0, group=0)}\nRefer to `=tm {row['English']}`",
            inline=False
        )
        # Release information
        release_str = f"{datetime.strftime(datetime.strptime(str(row['Release']), DFDTFORMAT), EMBEDDTFORMAT)}\nAcquisition: {row['Acquisition']}"
        if row['Pool'] != 'Regular':
            release_str += f" ({row['Pool']})"
        if row['EX']:
            release_str += f"\n**EX Job**: {datetime.strftime(datetime.strptime(str(row['EX']), DFDTFORMAT), EMBEDDTFORMAT)}"
        if row['TR']:
            release_str += f"\n**Transcendence**: {datetime.strftime(datetime.strptime(str(row['TR']), DFDTFORMAT), EMBEDDTFORMAT)}"
        if row['MA2']:
            release_str += f"\n**MA2**: {datetime.strftime(datetime.strptime(str(row['MA2']), DFDTFORMAT), EMBEDDTFORMAT)}"
        embed.add_field(name='Release', value=release_str, inline=False)
        # Thumbnail and URL
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        embed.add_field(
            name='WOTV-CALC',
            value=wotv_utils.calc_url('units', row['English']),
            inline=False
        )
        return 0, [embed]

    @classmethod
    def unitlist(cls, arg):
        """Generates list of units of specific element or weapon group."""
        # Check if element or weapon type / job and initialise embed
        ele = arg[0].lower().replace('lightning', 'thunder')
        args = ' '.join(arg).lower()
        for index, row in dfwotv.w_type.iterrows():
            args = args.replace(index, row['VC'])
        if ele in wotv_utils.dict['colours'].keys() and ele != 'neutral':
            # Argument is an element and units are split by groups
            df = dfwotv.tm[dfwotv.tm['Element'].str.lower() == ele]
            split_col = 'Group'
            embed = discord.Embed(
                title=f"{wotv_utils.dict['emotes'][ele]} {arg[0].title()}",
                colour=wotv_utils.dict['colours'][ele]
            )
        elif args in wotv_utils.dict['weapons']:
            # Argument is a group and units are split by elements
            df = dfwotv.tm[dfwotv.tm['Group'].str.lower() == args]
            split_col = 'Element'
            embed_title = wotv_utils.dict['emotes'][f"w_{args}"] + \
                          f" {args.title()}"
            if args in wotv_utils.dict['weapon_dict'].keys():
                embed_title = embed_title[:-1] + embed_title[-1].upper() + \
                              f" ({wotv_utils.dict['weapon_dict'][args]})"
            embed = discord.Embed(
                title=embed_title,
                colour=wotv_utils.dict['colours']['neutral']
            )
        else:
            # Match fail
            return 1, []
        # Further initialisation
        embed.description = f"Refer to `=vl {args}` for list of relevant VCs."
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                         url='https://wotv-calc.com/JP/units',
                         icon_url=wotv_utils.dict['embed']['author_icon_url'])
        list_dict = dict()
        if split_col == 'Group':# For element argument
            for group in wotv_utils.dict['Weapons']:
                list_dict[group] = dict()
        else: # For weapon group argument
            for element in wotv_utils.dict['colours'].keys():
                list_dict[element.title()] = dict()
        for unit_dict in list_dict.values():
            for rarity in wotv_utils.dict['rarity']:
                unit_dict[rarity] = []
        # Add unit entry with respect to element/group and rarity
        for _, row in df.iterrows():
            list_dict[row[split_col]][row['Rarity']].append(row['English'])
        # Generate embed fields
        if split_col == 'Group':
            line_list = []
            for group, unit_dict in list_dict.items():
                rarity_list = []
                for rarity, unit_list in unit_dict.items():
                    if not unit_list:
                        continue
                    rarity_list.append(f"{wotv_utils.dict['emotes'][rarity.lower()]} {' / '.join(unit_list)}")
                if rarity_list:
                    line_list.append(wotv_utils.dict['emotes'][f"w_{group.lower()}"] + f" {' '.join(rarity_list)}")
            tuple_list = cls.split_field(BLANK, line_list)
            for _, field_value in tuple_list:
                embed.add_field(name=BLANK, value=field_value, inline=False)
        else:
            for element, unit_dict in list_dict.items():
                rarity_list = []
                for rarity, unit_list in unit_dict.items():
                    if not unit_list:
                        continue
                    rarity_list.append(f"{wotv_utils.dict['emotes'][rarity.lower()]} {' / '.join(unit_list)}")
                if rarity_list:
                    embed.add_field(
                        name=f"{wotv_utils.dict['emotes'][element.lower()]} {element}",
                        value='\n'.join(rarity_list),
                        inline=False
                    )
        return 0, [embed]

    @classmethod
    def vcinfo(cls, arg):
        """Generates vision card information embed."""
        row_error, row = wotv_utils.find_row(dfwotv.vc, ' '.join(arg))
        if row_error:
            return row_error, row
        # Initialise
        embed = discord.Embed(
            title=wotv_utils.name_str(row, name='NAME'),
            description=f"`=vu {row['Aliases'].split(' / ')[0]}` for relevant UR units.",
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                         icon_url=wotv_utils.dict['embed']['author_icon_url'])
        embed_colours = set() # Set to prevent duplicates
        condition_flag = 0
        # Generate field per column
        for col in ('Unit', 'Party', 'Party Max', 'Skill'):
            if not row[col]: # Empty column
                continue
            effstr_list = []
            eff_prefixes = [] # Condition prefixes
            for eff in row[col].split(' / '):
                re_match = wotv_utils.reconditions.search(eff)
                if re_match:
                    conditions = re_match.group() \
                                 .strip('[]').lower().split('/')
                    eff_prefixes = []
                    eff_text = eff.replace(re_match.group(), '').strip()
                    condition_flag = 1
                else:
                    conditions = []
                    eff_text = eff
                for condition in conditions: # Skipped if no new condition
                    if condition in wotv_utils.dict['colours'].keys():
                        eff_prefixes.append(
                            wotv_utils.dict['emotes'][condition]
                        )
                        embed_colours.add(
                            wotv_utils.dict['colours'][condition]
                        )
                    if condition in wotv_utils.dict['weapons']:
                        eff_prefixes.append(
                            wotv_utils.dict['emotes'][f"w_{condition}"]
                        )
                    if not eff_prefixes: # Special condition
                        eff_prefixes = [re_match[0]] # Whole bracket
                        break
                effstr_list.append(f"{' '.join(eff_prefixes)} {eff_text}")
            f_value = '\n'.join(effstr_list)
            embed.add_field(name=col, value=f_value)
        # Suggest command for conditional VC
        if condition_flag:
            embed.description = f"`=vu {row['Aliases'].split(' / ')[0]}` for relevant UR units.",
        # Release information
        release_str = f"{datetime.strftime(datetime.strptime(str(row['Release']), DFDTFORMAT), EMBEDDTFORMAT)}\nAcquisition: {row['Acquisition']}"
        if row['Pool'] != 'Regular':
            release_str += f" ({row['Pool']})"
        embed.add_field(name='Release', value=release_str)
        # Final decorations and URL
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        if embed_colours:
            embed.colour = random.choice(list(embed_colours))
        if row['English']:
            embed.add_field(name='WOTV-CALC',
                            value=wotv_utils.calc_url('card', row['English']),
                            inline=False)
        return 0, [embed]

    @classmethod
    def vcunits(cls, arg):
        """Generates list of units applicable to the vc."""
        row_error, row = wotv_utils.find_row(dfwotv.vc, ' '.join(arg))
        if row_error:
            return row_error, row
        re_match = wotv_utils.reconditions.search(row['Party Max'].split(' / ')[0])
        if not re_match: # No condition, like job crystal
            return 1, []
        conditions = re_match.group().strip('[]').split('/')
        if conditions[0].lower() in wotv_utils.dict['colours'].keys():
            # Conditions are elements and units are split by groups
            condition_col = 'Element'
            split_col = 'Group'
        elif conditions[0] in wotv_utils.dict['Weapons']:
            # Conditions are groups and units are split by elements
            condition_col = 'Group'
            split_col = 'Element'
        else:
            return 1, [] # Not general condition, in case of future release
        # Initialise
        embed = discord.Embed(
            title=wotv_utils.name_str(row, name='NAME'),
            description=f"`=vc {row['Aliases'].split(' / ')[0]}` for VC info.",
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/cards',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        list_dict = dict()
        if split_col == 'Group': # Splitting by weapon group
            for group in wotv_utils.dict['Weapons']:
                list_dict[group.lower()] = []
            embed_colours = []
            for condition in conditions:
                embed_colours.append(
                    wotv_utils.dict['colours'][condition.lower()]
                )
            embed.colour = random.choice(embed_colours)
        else: # Splitting by element
            for element in wotv_utils.dict['colours'].keys():
                list_dict[element] = []
        df = dfwotv.tm[dfwotv.tm['Rarity'] == 'UR']
        for _, u_row in df.iterrows():
            if u_row[condition_col] in conditions:
                list_dict[u_row[split_col].lower()].append(u_row['English'])
        if split_col == 'Group':
            line_list = []
            for group, unit_list in list_dict.items():
                if not unit_list:
                    continue
                line_list.append(
                    wotv_utils.dict['emotes'][f"w_{group}"] + ' ' + ' / '.join(unit_list),
                )
            tuple_list = cls.split_field(BLANK, line_list)
            for _, field_value in tuple_list:
                embed.add_field(name=BLANK, value=field_value, inline=False)
        else:
            for element, unit_list in list_dict.items():
                if not unit_list:
                    continue
                embed.add_field(
                    name=f"{wotv_utils.dict['emotes'][element]} {element.title()}",
                    value=' / '.join(unit_list),
                    inline=False
                )
        # Add thumbnail and URL
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        if row['English']:
            embed.add_field(name='WOTV-CALC',
                            value=wotv_utils.calc_url('card', row['English']),
                            inline=False)
        return 0, [embed]

    @classmethod
    def vcsearch(cls, arg):
        """Generates vision card search embeds."""
        # Process keywords
        if len(arg) == 1: # Check if shortcut keyword.
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        args = args.lower()
        # Initialise
        vc_dicts = dict() # vc_dicts[p/u + UR/-][element] = list of vcstr
        for key in ('pUR', 'p', 'uUR', 'u'):
            vc_dicts[key] = {k: [] for k in wotv_utils.dict['colours'].keys()}
        col_tuples = (
           ('Party Max', 'p', f"{wotv_utils.dict['emotes']['vcmax']} "),
           ('Party', 'p', ''),
           ('Unit', 'u', '')
        )
        # Search df
        for _, row in dfwotv.vc.sort_values(
                ['Rarity', 'Release'], ascending=[False, False]).iterrows():
            vc_ele = '' # Determined by max effect for universal vc
            vcdict = {'p': [], 'u': []} # List of party and unit effects
            suffix_icons = []
            if row['Rarity'] == 'UR':
                key_suffix = 'UR'
            else:
                key_suffix = ''
            for col, key_prefix, max_icon in col_tuples:
                eff_prefixes = []
                for eff in row[col].split(' / '):
                    # Process the brackets first in case conditional effect is matched
                    effstr = eff
                    re_match = wotv_utils.reconditions.search(eff)
                    if re_match:
                        effstr = effstr[re_match.end():].strip()
                        conditions = re_match.group() \
                                     .strip('[]').lower().split('/')
                        eff_prefixes = []
                    else:
                        conditions = []
                    for condition in conditions:
                         # Remove previous conditions if new effect with conditions
                        if condition in wotv_utils.dict['colours'].keys():
                            eff_prefixes.append(
                                wotv_utils.dict['emotes'][condition]
                            )
                            if vc_ele == '':
                                vc_ele = condition
                            elif vc_ele != condition: # Multi-elemental VC
                                vc_ele = 'neutral' # For sorting only
                        if condition in wotv_utils.dict['weapons']:
                            eff_prefixes.append(
                                wotv_utils.dict['emotes'][f"w_{condition}"]
                            )
                        if not eff_prefixes: # Special condition
                            eff_prefixes = [re_match.group()]
                            break
                    # Add to unit effects for related stat ups
                    if args not in effstr.lower():
                        if args == 'agi%':
                            if 'agi+' not in eff.lower():
                                continue
                        elif args == 'def up':
                            if 'def+' not in eff.lower():
                                continue
                        elif args == 'spr up':
                            if 'spr+' not in eff.lower():
                                continue
                        else:
                            continue
                    if args in effstr.lower(): # Match Found
                        additional_icon = ''
                        if not eff_prefixes: # Add max effect element icon if universal
                            additional_icon = f" {''.join(suffix_icons)}"
                            eff_prefixes = [wotv_utils.dict['emotes']['allele']]
                        vcdict[key_prefix].append(
                            f"{''.join(eff_prefixes)}{wotv_utils.name_str(row, name='Aliases')} - {max_icon}{effstr}{additional_icon}"
                        )
                if eff_prefixes:
                    suffix_icons = eff_prefixes
            # Add entries to corresponding element and rarity
            if not vc_ele:
                vc_ele = 'neutral'
            for key_prefix, effstr_list in vcdict.items():
                vc_dicts[f"{key_prefix}{key_suffix}"][vc_ele].extend(effstr_list)
        # Combine lists of each element and rarity in their respective orders
        tuple_list = cls.split_field('Party',
            list(itertools.chain.from_iterable(vc_dicts['pUR'].values())) +
            list(itertools.chain.from_iterable(vc_dicts['p'].values()))
        ) + cls.split_field('Unit',
            list(itertools.chain.from_iterable(vc_dicts['uUR'].values())) +
            list(itertools.chain.from_iterable(vc_dicts['u'].values()))
        )
        if not tuple_list:
            return 1, tuple_list
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dict['embed']['default_colour'],
        )
        if arg[0].lower() in wotv_utils.dict['colours'].keys():
            embed.description = f"`=ve {arg[0]}` for list of elemental vcs"
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                         icon_url=wotv_utils.dict['embed']['author_icon_url'])
        # Change embed colour if requested effect is elemental
        for colour, colour_code in wotv_utils.dict['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed_list = cls.split_embed(
            embed, tuple_list, inline_num=2, embed_limit=3
        )
        if not embed_list:
            return 1, embed_list
        else:
            return 0, embed_list

    @classmethod
    def vclist(cls, arg):
        """Generates vision card list embeds by element or weapon type / job."""
        # Parse for argument to sort by effect rather than vc
        effect_sort = 0
        if len(arg) > 1:
            if arg[0].lower() in {'s', 'sort'}:
                effect_sort = 1
                arg = arg[1:]
        # Check if element or weapon type / job and initialise embed
        ele = arg[0].lower().replace('lightning', 'thunder')
        args = ' '.join(arg).lower()
        for index, row in dfwotv.w_type.iterrows():
            args = args.replace(index, row['VC'])
        if ele in wotv_utils.dict['colours'].keys() and ele != 'neutral':
            args = ele
            embed = discord.Embed(
                title=f"{wotv_utils.dict['emotes'][ele]} {arg[0].title()}",
                description=f"Refer to `=ul {args}` for list of relevant units.",
                colour=wotv_utils.dict['colours'][ele]
            )
        elif args in wotv_utils.dict['weapons']:
            embed_title = wotv_utils.dict['emotes'][f"w_{args}"] + \
                          f" {args.title()}"
            if args in wotv_utils.dict['weapon_dict'].keys():
                embed_title = embed_title[:-1] + embed_title[-1].upper() + \
                              f" ({wotv_utils.dict['weapon_dict'][args]})"
            embed = discord.Embed(
                title=embed_title,
                description=f"Refer to `=ul {args}` for list of relevant units.",
                colour=wotv_utils.dict['colours']['neutral']
            )
        else: # Return empty list if match fail, otherwise there has to be some results
            return 1, []
        # Initialise
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                         icon_url=wotv_utils.dict['embed']['author_icon_url'])
        col_tuples = (
            ('Party Max', wotv_utils.dict['emotes']['vcmax']),
            ('Party', '')
        )
        vctuples_list = []
        # Search df
        for index, row in dfwotv.vc.sort_values(
                ['Rarity', 'Release'], ascending=[False, False]).iterrows():
            vc_match = 0 # Flag to indicate vc matching criterion
            vctuples = [] # List of (vc name + effect prefixes, effect) to facilitate sorting
            for col, col_prefix in col_tuples:
                conditional = 0 # Flag for universal prefix
                vccoltuples = []
                eff_prefixes = [] # Prefix for other conditions sharing effect
                for eff in row[col].split(' / '):
                    re_match = wotv_utils.reconditions.search(eff)
                    if re_match:
                        conditional = 1
                        conditions = re_match.group() \
                                     .strip('[]').lower().split('/')
                        eff_text = eff[re_match.end():].strip()
                        eff_prefixes = [] # Reset prefix
                    else:
                        conditions = []
                        eff_text = eff
                    for condition in conditions:
                         # Remove previous conditions if new effect with different conditions
                        if condition == args: # Condition match found
                            vc_match = 1
                        elif condition in wotv_utils.dict['colours'].keys():
                            eff_prefixes.append(
                                wotv_utils.dict['emotes'][condition]
                            )
                        elif condition in wotv_utils.dict['weapons']:
                            eff_prefixes.append(
                                wotv_utils.dict['emotes'][f"w_{condition}"]
                            )
                        else:
                            eff_prefixes.append(
                                f"[{condition.title()}]"
                            )
                    if eff_prefixes:
                        final_prefix = f"{''.join(eff_prefixes)} "
                    elif not conditional:
                        final_prefix = f"{wotv_utils.dict['emotes']['allele']} "
                    else:
                        final_prefix = ''
                    vccoltuples.append((
                        f"{wotv_utils.name_str(row, name='Aliases')} - {col_prefix}{final_prefix}",
                        eff_text
                    ))
                vccoltuples.extend(vctuples) # To make max effect last
                vctuples = vccoltuples
            if vc_match:
                vctuples_list.extend(vctuples)
        # Generate embeds
        if effect_sort:
            vctuples_list = sorted(vc_tuples, key=lambda tup: tup[1])
        vcstr_list = [f"{vcprefix}{vceffstr}"
                      for vcprefix, vceffstr in vctuples_list]
        tuple_list = cls.split_field(BLANK, vcstr_list)
        embed_list = cls.split_embed(embed, tuple_list, inline_num=2)
        return 0, embed_list

    @classmethod
    def esperinfo(cls, arg):
        """Generates esper information embed."""
        row_error, row = wotv_utils.find_row(dfwotv.esper, ' '.join(arg))
        if row_error:
            return row_error, row
        # Initialise embed
        embed = discord.Embed(
            title=wotv_utils.name_str(row),
            colour=wotv_utils.dict['colours'][row['Element'].lower()]
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/espers',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        # Basic stats
        esstr_list = []
        for col in wotv_utils.dict['esper_stats']:
            esstr_list.append(f"`{col}{' ' * (4 - len(col))}` `{row[col]}`")
        embed.add_field(name='Stat',
                        value='\n'.join(esstr_list),
                        inline=False)
        esstr_list = []
        # Effect columns
        for col, suffix in wotv_utils.dict['esper_colsuffix'].items():
            if row[col]:
                eff_list = row[col].split(' / ')
                for eff in eff_list:
                    re_match = wotv_utils.revalues.search(eff)
                    if not re_match:
                        continue
                    effstr = eff[:re_match.start()]
                    if suffix:
                        effstr = f"{effstr}{suffix}"
                    esstr_list.append(f"{effstr} - `{re_match.group()}`")
        embed.add_field(name='Max Effects',
                        value='\n'.join(esstr_list),
                        inline=False)
        evoke_str = row['Evoke']
        # Evoke effect
        if row['Evoke Field']:
            evoke_str += f"\n**Field**: {row['Evoke Field']}"
        embed.add_field(name='Evoke', value=evoke_str, inline=False)
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        embed.add_field(name='WOTV-CALC',
                        value=wotv_utils.calc_url('esper', row['English']),
                        inline=False)
        return 0, [embed]

    @classmethod
    def espersearch(cls, arg):
        """Generates esper search embeds."""
        # Convert arg list to split with | instead and process keywords
        args = ' '.join(arg)
        arg = [a.lower().strip() for a in args.split('|')]
        for i, argstr in enumerate(arg):
            if len(argstr.split()) == 1:
                arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
            for index, row in dfwotv.replace.iterrows():
                arg[i] = arg[i].replace(index, row['VC'])
        # Parse first argument for filter and rank
        while arg:
            first_col, first_arg = wotv_utils.esper_findcol(arg[0]) # Function to find which column the said effect should be
            if first_col == 'NOTFOUND': # Skip invalid keywords
                arg = arg[1:]
            else:
                break
        df = dfwotv.esper
        if first_col == 'NOTFOUND':
            return 1, []
        if first_arg == 'STAT': # If stat, find 20 largest values
            df_ranked = df.nlargest(20, first_col)
        else:
            df_ranked = df[df[first_col].str.lower().str.contains(first_arg)]
        # Parse arguments for display
        if first_arg in ('y', 'n'): # If first filter is just yes/no, leave it out of display feature
            arg = arg[1:]
        heading_list = []
        arg_tuples = []
        for argstr in arg: # Skip if arg is empty
            if argstr.upper() in wotv_utils.dict['esper_stats']:
                arg_tuples.append((argstr.upper(), 'STAT'))
                heading_list.append(argstr.upper())
            else:
                col, esper_arg = wotv_utils.esper_findcol(argstr)
                if col != 'NOTFOUND':
                    arg_tuples.append((col, esper_arg))
                    heading = esper_arg.title()
                    suffix = wotv_utils.dict['esper_colsuffix'][col]
                    if suffix:
                        heading = f"{heading} {suffix}"
                    heading_list.append(heading)
        # Initialise
        esstr_list = []
        eslist_list = []
        # Search df
        for index, row in df_ranked.iterrows():
            filter_state = 0 # Flag of 0: First argument, 1: Effect matched, 2: Matched but below threshold
            eslist = [index] # [Name, value from arg1, value from arg2 ...]
            for tupcol, tuparg in arg_tuples:
                # Find value and add to eslist
                if tuparg == 'STAT':
                    eslist.append(str(row[tupcol]))
                    filter_state = 1
                elif tuparg in row[tupcol].lower():
                    for eff in row[tupcol].split(' / '):
                        if tuparg in eff.lower():
                            re_match = wotv_utils.revalues.search(eff)
                            if not re_match:
                                continue
                            eslist.append(re_match.group())
                            break
                    # To filter accuracy/evasion 7
                    if tuparg in 'accuracy' or tuparg in 'evasion':
                        if filter_state == 0:
                            if int(re_match[0]) < 8:
                                filter_state = 2
                                break
                    filter_state = 1
                else: # Esper does not have the effect
                    eslist.append('-')
            if filter_state == 1:
                eslist_list.append(eslist)
        if not eslist_list:
            return 1, eslist_list
        # Sort list
        if first_arg not in {'y', 'n'}:
            eslist_list.sort(key=lambda a: int(a[1]), reverse=True)
        for eslist in eslist_list:
            esstr = wotv_utils.name_str(df_ranked.loc[eslist[0]])
            if eslist:
                esstr += f" - `{' | '.join(eslist[1:])}`"
            esstr_list.append(esstr)
        tuple_list = cls.split_field(
            'Esper - ' + ' | '.join(heading_list), esstr_list
        )
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                         url='https://wotv-calc.com/JP/espers',
                         icon_url=wotv_utils.dict['embed']['author_icon_url'])
        # Change embed colour if requested effect is elemental.
        for colour, colour_code in wotv_utils.dict['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed_list = cls.split_embed(embed, tuple_list, embed_limit=2)
        if not embed_list:
            return 1, embed_list
        return 0, embed_list

    @classmethod
    def espercompare(cls, arg):
        """Generates esper comparison embed."""
        # Convert arg list to split with | instead and process keywords
        args = ' '.join(arg)
        arg = [a.lower().strip() for a in args.split('|')]
        for i, argstr in enumerate(arg):
            if len(argstr.split()) == 1:
                arg[i] = wotv_utils.shortcut_convert(argstr, 'Esper')
        row_list = []
        esper_list = []
        for argstr in arg:
            # Find the espers
            row_error, row = wotv_utils.find_row(dfwotv.esper, argstr)
            if not row_error:
                row_list.append(row)
                esper_list.append(wotv_utils.name_str(row))
        if len(esper_list) < 2: # Need 2 or more espers to compare
            return 1, esper_list
        # Initialise
        stat_dict = {stat: [] for stat in wotv_utils.dict['esper_stats']}
        effdict_dict = {col: dict() for col in #effs_dict[col][effstr][esper id]
            wotv_utils.dict['esper_colsuffix'].keys()}
        # Process each esper
        for i, row in enumerate(row_list):
            for stat in stat_dict.keys():
                stat_dict[stat].append(str(row[stat]))
            for col, suffix in wotv_utils.dict['esper_colsuffix'].items():
                eff_list = row[col].split(' / ')
                for eff in eff_list:
                    re_match = wotv_utils.revalues.search(eff)
                    if not re_match:
                        continue
                    effstr = eff[:re_match.start()]
                    if suffix:
                        effstr += suffix
                    if effstr in effdict_dict[col].keys():
                        effdict_dict[col][effstr][i] = re_match.group()
                    else:
                        effdict_dict[col][effstr] =  {i: re_match.group()}
        # Combine data from different columns
        effdict_dict = {
            effstr: effvalue
            for effdict in effdict_dict.values()
            for effstr, effvalue in effdict.items()
        }
        # Fill absent data and convert into list of values
        eff_dict = dict()
        for effstr, effdict in effdict_dict.items():
            eff_dict[effstr] = []
            for i, _ in enumerate(esper_list):
                if i in effdict.keys():
                    eff_dict[effstr].append(effdict[i])
                else:
                    eff_dict[effstr].append('-')
        # Combine lists and generate fields
        tuple_list = cls.split_field('Stat - ' + ' | '.join(esper_list), [
            f"{stat} - `{'` | `'.join(stat_values)}`" for stat, stat_values in stat_dict.items()
        ]) + cls.split_field('Max Effects - ' + ' | '.join(esper_list), [
            f"{effstr} - `{'` | `'.join(eff_values)}`" for effstr, eff_values in eff_dict.items()
        ])
        # Final decorations and split embed in case length issue
        embed = discord.Embed(
            colour=wotv_utils.dict['embed']['default_colour'],
            title=args.title()
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/espers',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list)
        if not embed_list:
            return 1, embed_list
        return 0, embed_list

    @classmethod
    def eqinfo(cls, arg):
        """Generates equipment information embed."""
        row_error, row = wotv_utils.find_row(dfwotv.eq, ' '.join(arg))
        if row_error:
            return row_error, row
        # Initialise
        description_list = [wotv_utils.name_str(row)]
        effstr_list = []
        embed_colours = set()
        if row['Restriction']:
            description_list.append(f"*Restriction: {row['Restriction']}*")
            if row['Restriction'].lower() in wotv_utils.dict['colours'].keys():
                # Colour for elemental rings
                embed_colours.add(
                    wotv_utils.dict['colours'][row['Restriction'].lower()]
                )
        conditions = ''
        # Passive effects
        for eff in row['Passive'].split(' / '):
            re_match = wotv_utils.reconditions.search(eff)
            if re_match:
                conditions = re_match.group()
                for condition in conditions.strip('[]').split('/'):
                    if condition.lower() in wotv_utils.dict['colours'].keys():
                        embed_colours.add(
                            wotv_utils.dict['colours'][condition.lower()]
                        )
                effstr_list.append(eff)
            elif conditions == '':
                effstr_list.append(eff)
            else: # From previous conditions
                effstr_list.append(f"{conditions} {eff}")
        description_list.extend(effstr_list)
        # Heartquartz effects
        if row['Extra'] != '':
            for eff in row['Extra'].split(' / '):
                description_list.append(f"{wotv_utils.dict['emotes']['heartquartzs']} {eff}")
        # Change embed colour if there are elemental ATK passives
        for colour, colour_code in wotv_utils.dict['colours'].items():
            if f"{colour.title()} ATK" in row['Passive']:
                embed_colours.add(colour_code)
        if not embed_colours:
            embed_colours={wotv_utils.dict['embed']['default_colour']}
        # Embed creation and input info so far
        embed = discord.Embed(
            title=row.name,
            description = '\n'.join(description_list),
            colour=random.choice(list(embed_colours))
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        # Acquisition and release information
        acq_str = f"{row['Acquisition']}\nRelease: {datetime.strftime(datetime.strptime(str(row['Release']), DFDTFORMAT), EMBEDDTFORMAT)}"
        if row['Release+']:
            acq_str += f"\n{wotv_utils.dict['emotes']['heartquartzs']} Release: {datetime.strftime(datetime.strptime(str(row['Release+']), DFDTFORMAT), EMBEDDTFORMAT)}"
        embed.add_field(name='Acquisition', value=acq_str, inline=False)
        # Craft materials (legacy)
        material_list = []
        for col in ['Regular', 'Rare', 'Cryst', 'Ore']:
            if row[col] != '':
                if col == 'Cryst':
                    material_list.append(wotv_utils.get_cryst(row))
                else:
                    engstr = dfwotv.mat.loc[row[col]]['Aliases'].split(' / ')[0]
                    material_list.append(f"{row[col]} ({engstr})")
        if material_list:
            embed.add_field(
                name='List of materials',
                value='\n'.join(material_list),
                inline=False
            )
        # Thumbnail and URL
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        if row['English']:
            embed.add_field(
                name='WOTV-CALC',
                value=wotv_utils.calc_url('equipment', row['English']),
                inline=False)
        return 0, [embed]

    @classmethod
    def eqsearch(cls, arg):
        """Generates equipment search embeds."""
        # Process keywords
        if len(arg) == 1:
            args = wotv_utils.shortcut_convert(arg[0])
        else:
            args = ' '.join(arg)
        args = args.lower()
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        # Initialise
        eqstr_list = []
        # Search df
        for _, row in dfwotv.eq.sort_values(
                ['Rarity', 'Release'], ascending=[False, False]).iterrows():
            if args in row['Passive'].lower() or args in row['Extra'].lower():
                eqstr_list.append(wotv_utils.eq_str(row))
        if not eqstr_list: # No match
            return 1, eqstr_list
        # Process into embeds
        tuple_list = cls.split_field(BLANK, eqstr_list)
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dict['embed']['default_colour']
        )
        for colour, colour_code in wotv_utils.dict['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed.set_author(
            name = wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url = wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list, embed_limit=3)
        if not embed_list:
            return 1, embed_list
        else:
            return 0, embed_list

    @classmethod
    def eqlist(cls, arg):
        """Generates equipment list embeds."""
        # Process keywords
        args = ' '.join(arg).lower()
        col = ''
        match_str = ''
        for dict_col, dict_set in wotv_utils.dict['eq_sets'].items():
            col_args = args
            if dict_col == 'Type':
                for index, row in dfwotv.eq_type.iterrows():
                    col_args = col_args.replace(index, row['VC'])
            col_candidates = []
            for set_item in dict_set:
                set_str = set_item.split(' - ')[-1]
                if col_args in set_str.lower():
                    col_candidates.append(set_item)
            if len(col_candidates) == 1:
                col = dict_col
                match_str = col_candidates[0]
                break
        if not col: # No match
            return 1, []
        eqstr_list = []
        # Search df
        for _, row in dfwotv.eq.sort_values(
                ['Rarity', 'Release'], ascending=[False, False]).iterrows():
            if match_str in row[col]:
                eqstr_list.append(wotv_utils.eq_str(row))
        tuple_list = cls.split_field(BLANK, eqstr_list)
        embed = discord.Embed(
            title=f"List of {col} - {match_str}",
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list)
        return 0, embed_list

    @classmethod
    def tminfo(cls, arg):
        """Generates trust master information embed."""
        row_error, row = wotv_utils.find_row(dfwotv.tm, ' '.join(arg))
        if row_error:
            return row_error, row
        # Process basic info and initialise embed
        description_list = [wotv_utils.name_str(row, type=0)]
        if row['Restriction']:
            description_list.append(f"*Restriction: {row['Restriction']}*")
        embed = discord.Embed(
            title=wotv_utils.name_str(row, name='TM Name', element=0, group=0),
            description='\n'.join(description_list),
            colour=wotv_utils.dict['colours'][row['Element'].lower()]
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/units',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        # Main stats
        stat_list = []
        for stat_name in wotv_utils.dict['tm_stats']:
            if row[stat_name]:
                stat_list.append(f"**{stat_name}** {row[stat_name]}")
        embed.add_field(
            name='Stats', value='\n'.join(stat_list), inline=False
        )
        # Passive effects if the TM has them (mostly non-UR)
        eff_list = []
        if row['Passive']:
            embed.add_field(
                name='Passive',
                value='\n'.join(row['Passive'].split(' / ')),
                inline=False
            )
        # Skill effects if the TM has them (mostly UR)
        if row['Skill']:
            if row['S Uses'] == 1:
                skill_name = f"TM Skill (1 Use)"
            else:
                skill_name = f"TM Skill ({row['S Uses']} Uses)"
            if row['S Area'] == 'Self':
                skill_range = '__Self__'
            elif not row['S Range']:
                skill_range = f"__{row['S Area']} Area__"
            else:
                skill_range = f"__Range: {row['S Range']} ({row['S Area']})__"
            embed.add_field(
                name=skill_name,
                value='\n'.join([skill_range] + row['Skill'].split(' / '))
            )
        # Thumbnail and URLs
        if row['TM Url']:
            embed.set_thumbnail(url=row['TM Url'])
        if row['TM English']:
            embed.add_field(
                name='WOTV-CALC',
                value='\n'.join((
                    wotv_utils.calc_url('equipment', row['TM English']),
                    wotv_utils.calc_url('units', row['English'])
                )),
                inline=False)
        return 0, [embed]

    @classmethod
    def tmsearch(cls, arg):
        """Generates trust master search embeds."""
        df = dfwotv.tm
        # EQ Type filter
        type_args = []
        if len(arg) > 1: # In case first two words are used for eq type
            type_args.append(' '.join(arg[:2]).lower())
        type_args.append(arg[0].lower())
        eqtype_filter = ''
        eqtype_candidates = []
        for i, type_arg in enumerate(type_args):
            for index, row in dfwotv.eq_type.iterrows():
                type_arg = type_arg.replace(index, row['VC'])
            for eqtype in wotv_utils.dict['eq_sets']['Type']:
                eqtype_str = eqtype.split(' - ')[-1].lower()
                if type_arg in eqtype_str:
                    eqtype_candidates.append((i, eqtype))

        if len(eqtype_candidates) == 1:
            arg = arg[2-eqtype_candidates[0][0]:]
            eqtype_filter = eqtype_candidates[0][1]
        # Target filter
        target = ''
        if arg:
            for skill_range in (
                    'Self', 'Ranged', 'Single', 'Plus', 'Diamond', 'none'):
                if arg[0].lower() == skill_range.lower():
                    target = skill_range
                    arg = arg[1:]
                    break
                elif arg[-1].lower() == skill_range.lower():
                    target = skill_range
                    arg = arg[:-1]
                    break
        args = ' '.join(arg).lower()
        if not target:
            target = 'NONE'
        elif target == 'none':
            target = '' # For search purpose
        # Filter appropriately
        if eqtype_filter:
            df = df[df['Type'] == eqtype_filter]
        if target == 'NONE':
            pass
        elif target == 'Ranged':
            df = df[df['S Range'].replace('', 0).astype('int') > 0]
        else:
            df = df[df['S Area'] == target]
        # STAT AND PASSIVES
        statstr_list = []
        if args.upper() in wotv_utils.dict['tm_stats']: # STAT
            df_filtered = df[df[args.upper()].replace('', 0).astype('int') > 0]\
                .copy(deep=True)
            df_filtered[args.upper()] = pd.to_numeric(df_filtered[args.upper()])
            if len(df_filtered):
                df_ranked = df_filtered.nlargest(50, args.upper())
            for _, row in df_ranked.iterrows():
                statstr_list.append(wotv_utils.tm_str(row, 'stat'))
        elif args or target == 'NONE': # PASSIVE
            # Search each tm
            for _, row in df.iterrows():
                if args in row['Passive'].lower():
                    statstr_list.append(wotv_utils.tm_str(row, 'stat'))
        # SKILL
        skillstr_list = []
        if len(args.split()) == 1:
            args = wotv_utils.shortcut_convert(args)
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        if args or target != 'NONE':
            for _, row in df.iterrows():
                if args in row['Skill'].lower():
                    skillstr_list.append(wotv_utils.tm_str(row, 'skill'))
        tuple_list = cls.split_field('TM by Stats', statstr_list) + \
                     cls.split_field('TM by Skills', skillstr_list)
        if not tuple_list:
            return 1, tuple_list
        # Embed creation and decorations
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dict['embed']['default_colour']
        )
        if target != 'NONE':
            embed.description = f"Target Filter: {target}"
        for colour, colour_code in wotv_utils.dict['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            url='https://wotv-calc.com/JP/units',
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list, embed_limit=3)
        if not embed_list:
            return 1, embed_list
        else:
            return 0, embed_list

    @classmethod
    def passivelist(cls, arg):
        """Generates list of passives embed."""
        # Generate passive list
        if arg[0].lower() == 'esper':
            # Separate processing for espers due to column separations
            args = 'esper'
            passivestr_list = []
            for col, suffix in wotv_utils.dict['esper_colsuffix'].items():
                if not suffix:
                    passivestr_list.extend(
                        list(sorted(wotv_utils.dict['esper_sets'][col]))
                    )
                    continue
                for eff in sorted(wotv_utils.dict['esper_sets'][col]):
                    passivestr_list.append(f"{eff} {suffix}")
        else:
            if arg[0].lower() == 'vc':
                args = 'vc'
            elif arg[0].lower() in ('eq', 'equip', 'equipment'):
                args = 'eq'
            elif arg[0].lower() in ('tm', 'trust'):
                args = 'tm'
            else:
                return 1, []
            passivestr_list = list(sorted(wotv_utils.dict[f"{args}_set"]))
        # Process into embeds
        tuple_list = cls.split_field(BLANK, passivestr_list, max_lines=15)
        embed = discord.Embed(
            title=f"List of Passives - {args}",
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(
            embed, tuple_list, inline_num=1, embed_limit=3
        )
        return 0, embed_list

    @classmethod
    def history(cls, arg):
        """Generates embeds of release history."""
        # Default duration
        end = datetime.now(tz=timezone(timedelta(hours=9)))\
                          .replace(tzinfo=None)
        period = 3
        start = end - timedelta(days=period * 30)
        # Initialise eq, vc, unit columns
        cols = (['Release'], ['Release'], ['Release'])
        # Process args
        for args in arg:
            for args_match, args_cols, args_period in \
                    wotv_utils.dict['history_tuples']:
                if args.lower() in args_match:
                    cols = args_cols
                    pediod = args_period
            for history_format in wotv_utils.dict['history_formats']:
                try:
                    args_start = datetime.strptime(args, history_format)
                    if args_start < end + timedelta(days=30):
                        start = args_start
                    break
                except ValueError:
                    args_start = None
        end = start + timedelta(days=period * 30)
        date_dict = dict()
        history_replace = wotv_utils.dict['history_replace'] # Default
        # Search each df
        for i, (df_name, df) in enumerate(
            [('EQ', dfwotv.eq), ('VC', dfwotv.vc), ('Unit', dfwotv.tm)]
                ):
            if not cols[i]:
                continue # No need to process the df if not asked for
            history_replace['Release'] = df_name
            for _, row in df.iterrows():
                for col in cols[i]:
                    if not row[col]:
                        continue
                    history_date = datetime.strptime(str(row[col]), DFDTFORMAT)
                    if start <= history_date <= end:
                        if col == 'TR':
                            heading = f"TR {row['Rarity']}"
                            name_str = wotv_utils.name_str(row, rarity=0, type=0)
                        elif df_name == 'Unit':
                            heading = col
                            name_str = wotv_utils.name_str(row, type=0)
                        else:
                            heading = col
                            name_str = wotv_utils.name_str(row)
                        if col in history_replace.keys():
                            heading = history_replace[col]
                        if row[col] not in date_dict.keys():
                            date_dict[row[col]] = dict()
                        if heading not in date_dict[row[col]].keys():
                            date_dict[row[col]][heading] = [name_str]
                        else:
                            date_dict[row[col]][heading].append(name_str)
        # Process into embeds
        tuple_list = []
        for release_date in sorted(list(date_dict.keys())):
            date_list = []
            for heading in wotv_utils.dict['history_headings']:
                if heading not in date_dict[release_date].keys():
                    continue
                if heading.split()[0] == 'TR':
                    rarity = wotv_utils.dict['emotes'][heading.split()[1].lower()]
                    heading_str = f"**Transcendence** {rarity}"
                else:
                    heading_str = f"**{heading}**"
                date_list.append(f"{heading_str} {' '.join(date_dict[release_date][heading])}")
            tuple_list.extend(cls.split_field(
                datetime.strftime(datetime.strptime(
                    str(release_date), DFDTFORMAT), EMBEDDTFORMAT),
                date_list
            ))
        embed = discord.Embed(
            title='WOTV History',
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list, inline_num=0)
        return 0, embed_list

    @classmethod
    def guildraid(cls, arg):
        """(Prototype) Generates guild raid embed from unit data for useful units.
        """
        # Check if element or weapon type / job and initialise embed
        if not arg: # Basic latest guild raid info
            df = dfwotv.text[dfwotv.text['Key'] == 'guild_raid']
            embed = discord.Embed(
                title='Guild Raid',
                description=df[df['Title'] == 'Embed']['Body'].tolist()[0],
                colour=wotv_utils.dict['embed']['default_colour']
            )
            embed.set_author(
                name=wotv_utils.dict['embed']['author_name'],
                icon_url=wotv_utils.dict['embed']['author_icon_url']
            )
            df = df[df['Title'] != 'Embed']
            for _, row in df.iterrows():
                embed.add_field(
                    name=row['Title'],
                    value=row['Body'],
                    inline=False
                )
            return 0, [embed]
        ele = arg[0].lower().replace('lightning', 'thunder')
        element = ele.title()
        if ele in wotv_utils.dict['colours'].keys() and ele != 'neutral':
            embed = discord.Embed(
                title=f"{wotv_utils.dict['emotes'][ele]} {element}",
                colour=wotv_utils.dict['colours'][ele]
            )
        else:
            return cls.guildraid([]) # Return basic info if not found
        # Boss info if designated at latest GR
        df = dfwotv.text[dfwotv.text['Key'] == 'gr_ele']
        df = df[df['Title'] == ele.title()]
        if len(df):
            embed.description = df['Body'].tolist()[0]
        else:
            embed.description = 'No designated boss for this element.'
        # Get multihit VCs into dict
        vc_dict = dict()
        df = dfwotv.text[dfwotv.text['Key'] == 'gr_vc']
        for _, row in df.iterrows():
            vc_dict[row['Title']] = row['Body']
        # Initialise
        embed.set_author(name=wotv_utils.dict['embed']['author_name'],
                     url='https://wotv-calc.com/JP/cards',
                     icon_url=wotv_utils.dict['embed']['author_icon_url'])
        df = dfwotv.tm[dfwotv.tm['Element'] == element]
        debuff_main = {key: [] for key in wotv_utils.dict['gr_debuffs']} # Proper order
        debuff_sub = {key: [] for key in wotv_utils.dict['gr_debuffs']} # Proper order
        list_dps = [] # DPS without debuffs
        # Loop all eligible units
        for _, row in df.iterrows():
            unit_name = wotv_utils.name_str(row, type=0, element=0)
            multihit_strs = []
            multihit_innate = 0
            unit_dict = defaultdict(list)
            # Process each column and add to respective lists
            # TBD: only either Slow or AGI depending on boss?
            if row['DB Slow']:
                for eff in row['DB Slow'].split(' / '):
                    unit_dict['Slow'].append(wotv_utils.gr_parse(eff))
            if row['DB AGI']:
                for eff in row['DB AGI'].split(' / '):
                    unit_dict['AGI'].append(wotv_utils.gr_parse(eff))
            if row['DB Target']:
                for eff in row['DB Target'].split(' / '):
                    if eff[0] == 'S':
                        unit_dict['Single RES'].append(wotv_utils.gr_parse(eff[2:]))
                    else:
                        unit_dict['Area RES'].append(wotv_utils.gr_parse(eff[2:]))
            if row['DB Element']:
                for eff in row['DB Element'].split(' / '):
                    if eff[:3] == 'All':
                        unit_dict['All Elemental RES'].append(wotv_utils.gr_parse(eff[4:]))
                    else:
                        unit_dict['ELE RES'].append(wotv_utils.gr_parse(eff))
            if row['DB Type']:
                for eff in row['DB Type'].split(' / '):
                    if eff[:3] == 'All':
                        unit_dict['All Type RES'].append(wotv_utils.gr_parse(eff[4:]))
                    else:
                        unit_dict[f"{wotv_utils.dict['gr_types'][eff[:2]]} RES"]\
                            .append(wotv_utils.gr_parse(eff[3:]))
            if row['DB DEF']:
                for eff in row['DB DEF'].split(' / '):
                    unit_dict['DEF'].append(wotv_utils.gr_parse(eff))
            if row['DB SPR']:
                for eff in row['DB SPR'].split(' / '):
                    unit_dict['SPR'].append(wotv_utils.gr_parse(eff))
            if row['DB Special']:
                for eff in row['DB Special'].split(' / '):
                    prefix, suffix = eff.split(' ', 1)
                    special_str = prefix.replace('_', ' ')
                    special_suffix = wotv_utils.gr_parse(suffix)
                    if special_suffix:
                        special_str += f" {special_suffix}"
                    unit_dict['Special'].append(special_str)
            # Check for DPS capabilities
            if row['Multihit']:
                for eff in row['Multihit'].split(' / '):
                    multihit_strs.append(wotv_utils.gr_parse(eff, include_type=True))
                    multihit_innate = 1
                    # TBD: to check whether > 3 hits at least for list_dps?
            weapons = row['Sub Weapon'].split(' / ')
            weapons.insert(0, row['Group'].rstrip('ABC'))
            for weapon in weapons:
                if weapon in vc_dict.keys():
                    pmh, vc_str = vc_dict[weapon].split()
                    if row['PMH'] == 'H' or row['PMH'] == pmh:
                        multihit_strs.append(vc_str)
            # Add to result dicts
            if multihit_strs:
                row_dict = debuff_main
                suffix_str = f" ({', '.join(multihit_strs)})"
            else:
                row_dict = debuff_sub
                suffix_str = ''
            for key, value_list in unit_dict.items():
                unit_str = unit_name
                value_str = ' or '.join(value_list)
                if value_str:
                    unit_str += f" [{value_str}]"
                unit_str += suffix_str
                row_dict[key].append(unit_str)
            if multihit_innate and not unit_dict:
                list_dps.append(f"{unit_name}{suffix_str}")
        # Evoke espers
        esper_lists = [[], [], []]
        df = dfwotv.esper[dfwotv.esper['Evoke Field'].str.contains(element)]
        for _, row in df.iterrows():
            if f"{element} Imperil / {element} ATK&MAG" in row['Evoke Field']:
                if element in row['Evoke']:
                    esper_tier = 0
                else:
                    esper_tier = 1
            elif element in row['Evoke'] and ('ATK' in row['Evoke Field'] or 'MAG' in row['Evoke Field']):
                esper_tier = 1
            else:
                esper_tier = 2
            esper_lists[esper_tier].append(wotv_utils.name_str(row, element=0))
        list_espers = []
        for i, tier_name in enumerate(['Recommended', 'Alternative', 'Last Resort']):
            if not esper_lists[i]:
                continue
            list_espers.append(f"{tier_name}: {' '.join(esper_lists[i])}")
        # Rearrange dict of lists into lists of strs
        tuple_list = []
        # Main debuffers
        for key, value_list in debuff_main.items():
            if not value_list:
                continue
            if key == 'ELE RES':
                heading = f"{element} RES"
            else:
                heading = key
            tuple_list.extend(cls.split_field(heading, value_list))
        # DPS and evokes
        tuple_list.extend(cls.split_field('Other DPS', list_dps) +
                          cls.split_field('Recommended Evoke', list_espers))
        # Debuffer alternatives
        debuff_sub_strs = []
        for key, value_list in debuff_sub.items():
            if not value_list:
                continue
            if key == 'ELE RES':
                heading = f"{element} RES"
            else:
                heading = key
            debuff_sub_strs.append(f"**{heading}**: {', '.join(value_list)}")
        tuple_list.extend(
            cls.split_field('Debuffer Alternatives', debuff_sub_strs)
        )
        embed_list = cls.split_embed(
            embed, tuple_list, inline_num=0, embed_limit=3
        )
        return 0, embed_list

    @classmethod
    def help(cls, arg):
        """Generates help embed."""
        help_tuples = wotv_utils.help_general # Default help
        if arg:
            if arg[0].lower() in ('engel', 'char', 'tamagotchi'):
                return 0, discord.Embed(
                    title='The function is discontinued.',
                    description='Thank you for your support.'
                )
            for key, value in (
                (('vc',), wotv_utils.help_vc),
                (('unit',), wotv_utils.help_unit),
                (('esper',), wotv_utils.help_esper),
                (('eq', 'tm', 'equip', 'trust'), wotv_utils.help_eq),
                (('param',), wotv_utils.help_param),
                (('stars', 'ramada', 'moore'), wotv_utils.help_ramada),
                (('events',), wotv_utils.help_events),
                (('materia', 'rune'), wotv_utils.help_materia),
            ):
                if arg[0].lower() in key:
                    help_tuples = value
                    break
        embed = discord.Embed(
            title='Ildyra Bot Help',
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        for f_name, f_value in help_tuples:
            embed.add_field(name=f_name, value=f_value, inline=False)
        return 0, [embed]

    @classmethod
    def redirect(cls, arg, main_func, help_str='', redirect_tuples=tuple()):
        """Redirects commands given the intended function and the redirect
        priorities. Returns (presence of error, content, list of embeds).
        arg: arg from commands as is
        main_func: intended function for the command
        help_str: help embed redirection
        redirect_tuples: list of tuples of (redirect_func, redirect_str)
        """
        if not arg: # No argument, redirect to help
            _, embed_list = cls.help([help_str])
            return (
                1,
                f"Redirected to `=help {help_str}`",
                embed_list
            )
        elif arg[0].lower() == 'help':
            _, embed_list = cls.help([help_str])
            return (
                1,
                f"Redirected to `=help {help_str}`",
                embed_list
            )
        embed_error, embed_list = main_func(arg)
        if not embed_error: # Command is carried out as intended
            return 0, None, embed_list
        for redirect_func, redirect_str in redirect_tuples:
            redirect_error, redirect_embeds = redirect_func(arg)
            if not redirect_error:
                redirect_content = f"Redirected to {redirect_str}. `=help {help_str}` for more info."
                if embed_list:
                    redirect_content += f" Otherwise, try: {' / '.join(embed_list)}"
                return (
                    1,
                    redirect_content,
                    redirect_embeds
                )
        if embed_list:
            return (
                1,
                f"Sorry, no match found. Try: {' / '.join(embed_list)}",
                None
            )
        return (
            1,
            f"Sorry, no match found or exceeded limit. Try `=help {help_str}`.",
            None
        )


class WotvGeneral(commands.Cog):
    """Discord cog with WOTV general commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log
        self.bot.remove_command('help')
        self.newscheck.start()

    @tasks.loop(minutes=1.0)
    async def newscheck(self):
        """Checks for news every minute and post to designated channels."""
        soup = wotv_utils.get_news()
        articles = soup.find_all("article")
        id_list = set()
        news_list = [] # Tuples of article id, article date, article title
        for article in articles:
            if article['data-id'] not in wotv_utils.news_entries.union(id_list):
                id_list.add(article['data-id'])
                news_list.append((
                    article['data-id'],
                    article.find('time').text.strip(' \n\t'),
                    article.find('h2').text
                ))
        if news_list:
            wotv_utils.news_entries = set([
                article['data-id'] for article in articles])
            for channel_id in dfwotv.ids['WOTV Newsfeed']:
                await self.bot.get_channel(channel_id).send('\n'.join([
                    f":newspaper: {news[1]} - {news[2]} - <https://players.wotvffbe.com/{news[0]}/>" for news in news_list
                ]))

    @commands.command()
    async def wotvsync(self, ctx, *arg):
        """(Owner only) Synchronise WOTV sheets."""
        if ctx.message.author.id == self.log.owner or \
                ctx.message.author.id in dfwotv.ids['WOTV Sync']:
            if not arg:
                # Synchronise WOTV sheets
                dfwotv.sync()
                wotv_utils.dict_sets_init()
                wotv_utils.update_text()
                await ctx.send('Google sheet synced for WOTV data.')
            elif arg[0] == 'events':
                dfwotv.sync_events()
                await ctx.send('Google sheet synced for WOTV events.')

    @commands.command(aliases=['passive', 'passives'])
    async def wotvpassive(self, ctx, *arg):
        """Check list of passives to look for ways to search."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.passivelist, '', tuple()
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['help', 'about', 'info', 'aboutme', 'readme', 'Help'])
    async def wotvhelp(self, ctx, *arg):
        """Customised help command."""
        await self.log.log(ctx.message)
        _, embed_list = EmbedWotv.help(arg)
        await self.log.send(ctx, embeds=embed_list)

    @commands.command(aliases=['history', 'release'])
    async def wotvhistory(self, ctx, *arg):
        """Generate embeds of WOTV release history."""
        await self.log.log(ctx.message)
        _, embed_list = EmbedWotv.history(arg)
        await self.log.send(ctx, embeds=embed_list)

    @commands.command(aliases=['gr', 'guildraid'])
    async def wotvgr(self, ctx, *arg):
        """(Prototype) Generate guild raid related embeds."""
        await self.log.log(ctx.message)
        _, embed_list = EmbedWotv.guildraid(arg)
        await self.log.send(ctx, embeds=embed_list)

    @commands.command(aliases=['materia', 'materias', 'Materia', 'Materias',
                               'rune', 'runes', 'truststone', 'Truststone',
                               'truststones', 'Truststones'])
    async def wotvmaterias(self, ctx, *arg):
        """Command to call info regarding materias."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            title='Materia Main Stats',
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        materia_tuples = wotv_utils.materia_set
        if arg:
            if arg[0].lower() in ('substat', 'sub', 'substats', 's'):
                embed.title = 'Materia Substats'
                materia_tuples = wotv_utils.materia_substat
                for f_name, f_value in materia_tuples:
                    embed.add_field(name=f_name, value=f_value, inline=True)
                await self.log.send(ctx, embed=embed)
                return
            elif arg[0].lower() in ('passive', 'passives', 'recraft', 'p'):
                embed.title = 'Materia Passives'
                materia_tuples = wotv_utils.materia_passive
        for f_name, f_value in materia_tuples:
            embed.add_field(name=f_name, value=f_value, inline=False)
        embed.add_field(name=BLANK, value='\n'.join((
                '`=materia set` for main stat types and set effects',
                '`=materia substat` for substats',
                '`=materia passive` for passives',
                '`=help materia` for more info')))
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['addevent'])
    async def wotvaddevent(self, ctx, *arg): # Legacy
        """Add event to calendar for authorized people."""
        await self.log.log(ctx.message)
        if ctx.message.author.id in dfwotv.ids['WOTV Events']:
            try:
                # Parse arguments.
                arg = [a.strip() for a in ' '.join(arg).split('|')]
                eventstr = arg[0]
                eventstart = datetime.strptime(arg[1], MYDTFORMAT)
                if len(arg) == 2:
                    eventend = eventstart
                    arg = (*arg, arg[1])
                else:
                    eventend = datetime.strptime(arg[2], MYDTFORMAT)
                # Check end time is later than start time.
                if eventstart <= eventend:
                    dfwotv.add_event(arg)
                    await self.log.send(ctx, 'Event added.')
                else:
                    await self.log.send(ctx,
                        'Ending time must be later than starting time.')
            except (IndexError, ValueError):
                await self.log.send(ctx, 'Incorrect format.')
        else:
            await self.log.send(ctx, 'Permission denied.')

    @commands.command(aliases=['events', 'calendar'])
    async def wotvevents(self, ctx, *arg): # Legacy
        """Check ongoing or upcoming events."""
        await self.log.log(ctx.message)
        dt_bool = 0
        sp_bool = 0
        if arg:
            if arg[0] in ('date', 'time', 'upcoming',
                'up-coming', 'ongoing', 'on-going'):
                dt_bool = 1
            elif arg[0] in ('embed', 'format'):
                dt_bool = 2
        events = {
            'on-going': [],
            'up-coming': []
        }
        # Goes through the dataframe
        now_jst = datetime.now(tz=timezone(timedelta(hours=9)))\
                          .replace(tzinfo=None)
        for _, row in dfwotv.events.iterrows():
            if now_jst <= datetime.strptime(row['End'], MYDTFORMAT):
                # Search keyword to decide on the emote prefix.
                eventprefix = ':calendar:'
                for event_keywords, event_emote in \
                        wotv_utils.dict['event_tuples']:
                    for event_keyword in event_keywords:
                        if event_keyword in row['Event'].lower():
                            eventprefix = \
                                wotv_utils.dict['emotes'][event_emote]
                            break
                    if eventprefix != ':calendar:':
                        break
                eventname = f"{eventprefix} {row['Event']}"
                # Check if it is up-coming or on-going.
                if now_jst < \
                        datetime.strptime(row['Start'], MYDTFORMAT):
                    events['up-coming'].append((
                        eventname,
                        datetime.strptime(row['Start'], MYDTFORMAT),
                        datetime.strptime(row['End'], MYDTFORMAT),
                    ))
                elif now_jst <= \
                        datetime.strptime(row['End'], MYDTFORMAT):
                    events['on-going'].append((
                        eventname,
                        datetime.strptime(row['Start'], MYDTFORMAT),
                        datetime.strptime(row['End'], MYDTFORMAT),
                    ))
        events['on-going'].sort(key=lambda a: a[2])
        events['up-coming'].sort(key=lambda a: a[1])
        if dt_bool == 2:
            # Generate reply embed.
            embed = discord.Embed(
                colour = wotv_utils.dict['embed']['default_colour']
            )
            embed.title = 'WOTV JP Calendar'
            for k, v in events.items():
                if not v:
                    continue
                namelist = []
                startlist = []
                endlist = []
                event_count = 0
                for eventname, eventstart, eventend in v:
                    event_count += 1
                    namelist.append(eventname)
                    startlist.append(datetime.strftime(
                        eventstart, PRINTDTFORMAT))
                    endlist.append(datetime.strftime(
                        eventend, PRINTDTFORMAT))
                    # Add new field every 10 counts for character limit.
                    if event_count == 10:
                        embed.add_field(name=k.capitalize(),
                                        value='\n'.join(namelist))
                        embed.add_field(name='Start',
                                        value='\n'.join(startlist))
                        embed.add_field(name='End', value='\n'.join(endlist))
                        namelist = []
                        startlist = []
                        endlist = []
                        event_count = 0
                if event_count:
                    embed.add_field(name=k.capitalize(),
                                    value='\n'.join(namelist))
                    embed.add_field(name='Start', value='\n'.join(startlist))
                    embed.add_field(name='End', value='\n'.join(endlist))
            await self.log.send(ctx, embed=embed)
        else:
            # Generate reply string.
            replystr_list = ['']
            for k, v in events.items():
                if len(replystr_list) > 1:
                    replystr_list.append('\n\n')
                if not v:
                    replystr_list.append(f"*No {k} events.*")
                else:
                    replystr_list.append(f"**{k.capitalize()} Events**")
                    for event in v:
                        if dt_bool == 1:
                            eventstart = datetime.strftime(
                                event[1], PRINTDTFORMAT)
                            eventend = datetime.strftime(
                                event[2], PRINTDTFORMAT)
                            replystr_list.append(''.join((
                                f"\n{event[0]} - ",
                                f"`{eventstart}` to `{eventend}`")))
                        else:
                            replystr_list.append(f"\n{event[0]} -")
                            if k == 'on-going':
                                eventdd = event[2] - now_jst
                            else:
                                eventdd = event[1] - now_jst
                            eventddsplit = (
                                ('day', eventdd.days),
                                ('hour', eventdd.seconds // 3600),
                                ('minute', eventdd.seconds % 3600 // 60)
                            )
                            for eventddstr, eventddnum in eventddsplit:
                                if eventddnum > 1:
                                    replystr_list.append(
                                        f" `{eventddnum} {eventddstr}s`")
                                elif eventddnum == 1:
                                    replystr_list.append(
                                        f" `{eventddnum} {eventddstr}`")
                        replystr = ''.join(replystr_list)
                        if len(replystr) > 1800:
                            await self.log.send(ctx, replystr)
                            replystr_list = ['(Cont.)']
            if len(replystr_list) > 1:
                await self.log.send(ctx, ''.join(replystr_list))

    @commands.command(aliases=['rand', 'random', 'choice'])
    async def wotvrand(self, ctx, *arg):
        """Fluff command to pick a number or string from users."""
        await self.log.log(ctx.message)
        embed = discord.Embed()
        # Check command is called in a FFBE server.
        if ctx.guild.id in dfwotv.ids['FFBE Server']:
            ffbe = 1
        else:
            ffbe = 0
        npctup = wotv_utils.rand(ffbe, *arg)
        embed.title = f"Random {npctup[1]}"
        embed.colour = wotv_utils.dict['colours'][npctup[2]]
        embed.set_thumbnail(url=npctup[3])
        if npctup[0]:
            embed.description = '\n'.join((
                f"{npctup[4]} Give us either:",
                "- one or two numbers",
                "- two or more choices"))
        else:
            embed.description = npctup[4]
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['fortune', 'stars', 'ramada', 'moore'])
    async def wotvramada(self, ctx, *arg):
        """Fluff command to read fortune."""
        await self.log.log(ctx.message)
        # Check if Moore or Ramada is specified.
        reader = ctx.message.content.lstrip('=+').split()[0]
        embed = discord.Embed(
            colour = wotv_utils.dict['embed']['default_colour']
        )
        fortunestr, fortunetitle, fortuneurl = wotv_utils.ramada(reader)
        embed.title = fortunetitle
        embed.description = fortunestr
        embed.set_thumbnail(url=fortuneurl)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['changelog', 'version', 'Changelog'])
    async def wotvchangelog(self, ctx, *arg):
        """Return recent changelogs."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            colour=wotv_utils.dict['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dict['embed']['author_name'],
            icon_url=wotv_utils.dict['embed']['author_icon_url']
        )
        embed.title = 'Ildyra Bot Changelog'
        try:
            entry_num = int(arg[0])
        except IndexError:
            entry_num = 3 # Default: show 3 most recent changes
        num = 0
        for _, row in dfwotv.text[dfwotv.text['Key'] == 'changelog'].iterrows():
            if num == entry_num:
                break
            embed.add_field(name=row['Title'], value=row['Body'], inline=False)
            num += 1
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['weekly', 'weekday', 'daily', 'Weekly'])
    async def wotvweekly(self, ctx, *arg):
        """Reply pre-set message of day of the week bonuses."""
        await self.log.log(ctx.message)
        await self.log.send(ctx, wotv_utils.weekly)

    @commands.command(aliases=['news'])
    async def wotvnews(self, ctx, *arg):
        """Reply pre-set link to news."""
        await self.log.log(ctx.message)
        if arg:
            if arg[0].lower() == 'gl':
                news_str = 'https://site.na.wotvffbe.com//whatsnew'
            else:
                news_str = '\n'.join(('https://site.wotvffbe.com//whatsnew',
                                      '<https://players.wotvffbe.com/>'))
        else:
            news_str = '\n'.join(('https://site.wotvffbe.com//whatsnew',
                                '<https://players.wotvffbe.com/>'))
        await self.log.send(ctx, news_str)

    @commands.command(aliases=['param', 'acc', 'eva', 'crit', 'params', 'Param'])
    async def wotvparam(self, ctx, *arg):
        """Calculate acc, eva, crit and crit avoid from
        dex, agi, luck and equipment stats.
        """
        await self.log.log(ctx.message)
        if not arg:
            _, embeds = EmbedWotv.help(['param'])
            await self.log.send(
                ctx,
                'Redirected to `=help param`',
                embeds=embeds
            )
            return
        params = {k: v[0] for k, v in wotv_utils.dict['paramcalc'].items()}
        args = ' '.join(arg)
        embed = discord.Embed(
            title = args,
            colour = wotv_utils.dict['embed']['default_colour']
        )
        # Convert arg list to split with | instead.
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number
            re_match = wotv_utils.revalues.search(argstr)
            if not re_match:
                continue
            paramval = int(re_match.group())
            paramstr = argstr[0:re_match.start()].strip()
            for k, v in wotv_utils.dict['paramcalc'].items():
                if paramstr in v[1]:
                    if k not in ('agi', 'dex', 'luck') or paramval >= 0:
                        # Disallow negative values for the three stats.
                        params[k] = paramval
                    break
        # Actual calculations
        results = (
            ('ACC', (11*params['dex']**0.2/20 + params['luck']**0.96/200
                - 1)*100 + params['acc']),
            ('EVA', (11*params['agi']**0.9/1000 + params['luck']**0.96/200
                - 1)*100 + params['eva']),
            ('CRIT', (params['dex']**0.35/4 - 1) * 100 + params['crit']),
            ('C.AVO', (params['luck']**0.37/5 - 1) * 100 + params['c.avo'])
        )
        # Present results.
        embed.add_field(name='Inputs', value='\n'.join([
            f"`{k.upper(): <5}` {v}" for k, v in params.items()]), inline=True)
        embed.add_field(name='Results', value='\n'.join([
            f"`{k: <5}` {v: .1f}%" for k, v in results]), inline=True)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=[
        'engelhelp', 'pethelp', 'tamagotchihelp', 'tamahelp', 'charhelp',
        'engelrep', 'petrep', 'tamagotchirep', 'tamarep', 'charrep',
        'engel', 'pet', 'tamagotchi', 'tama', 'char',
        'engelberthelp', 'engelbertrepeat', 'engelbert',
        ])
    async def wotv_discontinued(self, ctx, *arg):
        """Function to respond that the corresponding functionality has
        already been discontinued.
        """
        await self.log.log(ctx.message)
        await self.log.send(ctx, 'The tamagotchi function has been discontinued. Thank you for your support.')


class WotvUnit(commands.Cog):
    """Discord cog with WOTV units commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['unit'])
    async def wotvunit(self, ctx, *arg):
        """Unit information command."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.unitinfo, 'unit',
            (
                (EmbedWotv.unitlist, 'Unit List (`=ul`)'),
                (EmbedWotv.tminfo, 'Trust Master Information (`=tm`)')
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['ul'])
    async def wotvunitlist(self, ctx, *arg):
        """Unit list command."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.unitlist, 'unit',
            (
                (EmbedWotv.unitinfo, 'Unit Information (`=unit`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

class WotvEquipment(commands.Cog):
    """Discord cog with WOTV equipment commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['tm', 'Tm', 'trust', 'Trust', 'tmr', 'Tmr', 'TM'])
    async def wotvtm(self, ctx, *arg):
        """Trust master information command."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.tminfo, 'eq',
            (
                (EmbedWotv.eqlist, 'Equipment List (`=eql`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['tms', 'ts', 'Tms', 'Ts'])
    async def wotvtmsearch(self, ctx, *arg):
        """Trust master search command."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.tmsearch, 'eq',
            (
                (EmbedWotv.tminfo, 'Trust Master Information (`=tm`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['eq', 'equip', 'Eq', 'Equip'])
    async def wotveq(self, ctx, *arg):
        """Equipment information command."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.eqinfo, 'eq',
            (
                (EmbedWotv.tminfo, 'Trust Master Information (`=tm`)'),
                (EmbedWotv.eqsearch, 'Equipment Search (`=eqs`)'),
                (EmbedWotv.eqlist, 'Equipment List (`=eql`)'),
                (EmbedWotv.tmsearch, 'Trust Master Search (`=tms`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['eql', 'el', 'Eql', 'El'])
    async def wotveqlist(self, ctx, *arg):
        """List equipment by type, acquisition, material."""
        await self.log.log(ctx.message)
        if arg:
            if arg[0] in ('t', 'a', 'm'):
                arg = arg[1:]
            if arg[0] in ('l', 'list'):
                embed = discord.Embed(
                    title='Equipment List',
                    description='List of arguments for equipment list command `=eql`'
                )
                embed.set_author(
                    name=wotv_utils.dict['embed']['author_name'],
                    url='https://wotv-calc.com/JP/equipment',
                    icon_url=wotv_utils.dict['embed']['author_icon_url']
                )
                for col, eq_set in wotv_utils.dict['eq_sets'].items():
                    embed.add_field(
                        name=f"List by {col}",
                        value=' / '.join(eq_set),
                        inline=False
                    )
                await self.log.send(ctx, embed=embed)
                return
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.eqlist, 'eq',
            (
                (EmbedWotv.eqsearch, 'Equipment Search (`=eqs`)'),
                (EmbedWotv.tmsearch, 'Trust Master Search (`=tms`)'),
                (EmbedWotv.eqinfo, 'Equipment Information (`=eq`)'),
                (EmbedWotv.tminfo, 'Trust Master Information (`=tm`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['eqs', 'es', 'Eqs', 'Es'])
    async def wotveqsearch(self, ctx, *arg):
        """Search equipment by effect."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.eqsearch, 'eq',
            (
                (EmbedWotv.eqlist, 'Equipment List (`=eql`)'),
                (EmbedWotv.tmsearch, 'Trust Master Search (`=tms`)'),
                (EmbedWotv.eqinfo, 'Equipment Information (`=eq`)'),
                (EmbedWotv.tminfo, 'Trust Master Information (`=tm`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)


class WotvVc(commands.Cog):
    """Discord cog with WOTV vision card commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['vc', 'VC', 'Vc'])
    async def wotvvc(self, ctx, *arg):
        """Search vision card by name."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.vcinfo, 'vc',
            (
                (EmbedWotv.vclist, 'Vision Card List (`=vcl`)'),
                (EmbedWotv.vcsearch, 'Vision Card Search (`=vcs`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['vcs', 'vs', 'Vcs', 'Vs'])
    async def wotvvcsearch(self, ctx, *arg):
        """Search vision cards by effect."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.vcsearch, 'vc',
            (
                (EmbedWotv.vclist, 'Vision Card List (`=vcl`)'),
                (EmbedWotv.vcinfo, 'Vision Card Information (`=vc`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['vcu', 'vu', 'Vcu', 'Vu'])
    async def wotvvcunits(self, ctx, *arg):
        """Search relevant units by vc."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.vcunits, 'vc',
            (
                (EmbedWotv.vcinfo, 'Vision Card Information (`=vc`)'),
                (EmbedWotv.vclist, 'Vision Card List (`=vcl`)'),
                (EmbedWotv.vcsearch, 'Vision Card Search (`=vcs`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['vce', 've', 'Vce', 'Ve',
                               'vcj', 'vj', 'Vcj', 'Vj',
                               'vcw', 'vw', 'Vcw', 'Vw',
                               'vcl', 'vl', 'Vcl', 'Vl'])
    async def wotvvclist(self, ctx, *arg):
        """Search vision cards by element or weapon type / job."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.vclist, 'vc',
            (
                (EmbedWotv.vcsearch, 'Vision Card Search (`=vcs`)'),
                (EmbedWotv.vcinfo, 'Vision Card Information (`=vc`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)


class WotvEsper(commands.Cog):
    """Discord cog with WOTV esper commands."""
    def __init__(self, bot, bot_log):
        """Registers associated bot."""
        self.bot = bot
        self.log = bot_log

    @commands.command(aliases=['magicite', 'magicites', 'Magicite', 'Magicites'])
    async def wotvmagicite(self, ctx, *arg):
        """Calculate required amount of magicites from inputs."""
        await self.log.log(ctx.message)
        if not arg:
            _, embeds = EmbedWotv.help(['esper'])
            await self.log.send(
                ctx,
                'Apparently you need some assistance. Redirected to `=help esper`',
                embeds=embeds
            )
            return
        magicites = {k: 0 for k in wotv_utils.dict['magicites'].keys()}
        esper_start = 1
        bonus = 100
        neutral = 0
        args = ' '.join(arg)
        embed = discord.Embed(
            title=args,
            colour=wotv_utils.dict['embed']['default_colour']
        )
        # Convert arg list to split with | instead
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number
            if argstr == 'neutral':
                neutral = 1
                continue
            re_match = wotv_utils.revalues.search(argstr.rstrip('%'))
            if not re_match:
                continue
            paramval = int(re_match.group())
            paramstr = argstr[0:re_match.start()].strip()
            if paramstr in ('star', 'stars') and paramval in (1, 2, 3):
                esper_start = paramval
            elif paramstr in ('bonus',) and 0 <= paramval <= 100:
                bonus = paramval
            else:
                for k in wotv_utils.dict['magicites'].keys():
                    if paramstr == k.lower():
                        magicites[k] = max(paramval, 0)
                        break
        # Actual calculations
        req_exp = sum([wotv_utils.dict['esper_exp'][a] for a in \
            range(esper_start, 4, 1)])
        total_exp = 0
        for k, v in magicites.items():
            if neutral:
                total_exp += int(v * wotv_utils.dict['magicites'][k]
                                 * (100+bonus) / 100 * 0.75)
            else:
                total_exp += (v * wotv_utils.dict['magicites'][k]
                              * int((100+bonus) / 100))
        if neutral:
            xl_exp = (wotv_utils.dict['magicites']['XL'] * (100+bonus) / 100
                      * 0.75)
        else:
            xl_exp = wotv_utils.dict['magicites']['XL'] * (100+bonus) / 100
        # Present results
        field_list = [
            f"Starting from `{esper_start}-star`",
            f"Bonus: `{bonus}%`",
        ] + [f"{k} Magicites: `{v}`" for k, v in magicites.items()]
        if neutral:
            field_list.append('Neutral Esper')
        embed.add_field(name='Inputs', value='\n'.join(field_list),
                        inline=True)
        field_list = [
            f"Required EXP: `{req_exp}` (`{req_exp / xl_exp:.1f}` XL)",
            f"Total EXP: `{total_exp}` (`{total_exp / xl_exp:.1f}` XL)",
        ]
        if total_exp > req_exp:
            field_list.append(''.join(('Enough with leftovers of ',
                f"`{(total_exp - req_exp) / xl_exp:.1f}` XL.")))
        elif req_exp > total_exp:
            field_list.append(''.join(('Insufficient of ',
                f"`{(req_exp - total_exp) / xl_exp:.1f}` XL.")))
        embed.add_field(name='Results', value='\n'.join(field_list),
                        inline=True)
        await self.log.send(ctx, embed=embed)

    @commands.command(aliases=['esperchart', 'Esperchart'])
    async def wotvesperchart(self, ctx, *arg):
        """Return a chart image of espers."""
        await self.log.log(ctx.message)
        df = dfwotv.text[dfwotv.text['Key'] == 'chart']
        await self.log.send(ctx, df[df['Title'] == 'esper']['Body'].tolist()[0])

    @commands.command(aliases=['esper', 'Esper', 'esp', 'Esp'])
    async def wotvesper(self, ctx, *arg):
        """Search esper by name."""
        await self.log.log(ctx.message)
        if arg:
            # Parse m, chart, s, r, f, c for legacy
            if arg[0] == 'chart':
                df = dfwotv.text[dfwotv.text['Key'] == 'chart']
                await self.log.send(
                    ctx, df[df['Title'] == 'esper']['Body'].tolist()[0]
                )
                return
            if arg[0] == 'm':
                arg = arg[1:]
            if arg[0] in ('r', 'f', 's'):
                arg = arg[1:]
                if arg:
                    if arg[0] == 'm':
                        arg = arg[1:]
                _, msg_content, msg_embeds = EmbedWotv.redirect(
                    arg, EmbedWotv.espersearch, 'esper',
                    (
                        (EmbedWotv.esperinfo, 'Esper Information (`=esp`)'),
                        (EmbedWotv.espercompare, 'Esper Comparison (`=esc`)'),
                    )
                )
                await self.log.send(ctx, msg_content, embeds=msg_embeds)
                return
            if arg[0] == 'c':
                arg = arg[1:]
                if arg[0] == 'm':
                    arg = arg[1:]
                _, msg_content, msg_embeds = EmbedWotv.redirect(
                    arg, EmbedWotv.espercompare, 'esper',
                    (
                        (EmbedWotv.esperinfo, 'Esper Information (`=esp`)'),
                        (EmbedWotv.espersearch, 'Esper Rank (`=esr`)'),
                    )
                )
                await self.log.send(ctx, msg_content, embeds=msg_embeds)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.esperinfo, 'esper',
            (
                (EmbedWotv.espercompare, 'Esper Comparison (`=esc`)'),
                (EmbedWotv.espersearch, 'Esper Rank (`=esr`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['esr', 'esperr', 'er', 'Esr', 'Er', 'ess', 'Ess'])
    async def wotvespersearch(self, ctx, *arg):
        """Search esper by effect or stat."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.espersearch, 'esper',
            (
                (EmbedWotv.esperinfo, 'Esper Information (`=esp`)'),
                (EmbedWotv.espercompare, 'Esper Comparison (`=esc`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)

    @commands.command(aliases=['esc', 'esperc', 'ec', 'Esc', 'Ec'])
    async def wotvespercompare(self, ctx, *arg):
        """Search esper by effect or stat."""
        await self.log.log(ctx.message)
        _, msg_content, msg_embeds = EmbedWotv.redirect(
            arg, EmbedWotv.espercompare, 'esper',
            (
                (EmbedWotv.esperinfo, 'Esper Information (`=esp`)'),
                (EmbedWotv.espersearch, 'Esper Rank (`=esr`)'),
            )
        )
        await self.log.send(ctx, msg_content, embeds=msg_embeds)
