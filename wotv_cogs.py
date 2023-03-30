import discord
import random
import itertools
import pandas as pd
import warnings
from pandas.core.common import SettingWithCopyWarning
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta

from gsheet_handler import DfHandlerWotv
from wotv_utils import WotvUtils

dfwotv = DfHandlerWotv()
wotv_utils = WotvUtils(dfwotv)
MYDTFORMAT = '%Y/%m/%d %H:%M'
PRINTDTFORMAT = '%b %d, %H:%M'
BLANK = '\u200b'


class EmbedWotv():
    """
    Support functions for discord commands to generate embeds for specific
    purposes. Separated from the cogs to facilitate redirection.
    """
    @classmethod
    def split_field(cls, f_name, entry_list):
        """Given list of line entries (str), split into list of field tuples of
        field name (str) and value (str) with respect to character limits."""
        if not entry_list: # Empty list
            return entry_list
        tuple_list = []
        f_value = '\n'.join(entry_list)
        if len(f_value) < 1020: # Short enough to fit into 1
            return [(f_name, f_value)]
        checkpoint = 0
        char_count = -2
        for i, entry in enumerate(entry_list):
            char_count += len(entry) + 2
            if char_count > 1000:
                f_value = '\n'.join(entry_list[checkpoint:i])
                tuple_list.append((f_name, f_value))
                char_count = len(entry)
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
                embed.add_field(name=BLANK, value=BLANK, inline=True)
                char_count += len(BLANK) * 2
                field_count += 1
            field_char = len(f_name) + len(f_value)
            if char_count + field_char > 5500 or field_count >= 24:
                if inline_num == 2 and field_count % 3 == 2: # To balance display
                    embed.add_field(name=BLANK, value=BLANK, inline=True)
                embed_list.append(embed)
                if len(embed_list) >= embed_limit: # Exceeded limit
                    return []
                embed = discord.Embed(colour=embed_colour)
                char_count = 0
                field_count = 0
            embed.add_field(name=f_name, value=f_value, inline=inline)
            char_count += field_char
            field_count += 1
        if inline_num == 2 and field_count % 3 == 2: # To balance display
            embed.add_field(name=BLANK, value=BLANK, inline=True)
        embed_list.append(embed)
        return embed_list

    @classmethod
    def vcinfo(cls, arg):
        """Generates vision card information embed."""
        df = dfwotv.vc
        row_error, row = wotv_utils.find_row(df, ' '.join(arg))
        if row_error:
            return row_error, row
        embed = discord.Embed(
            title=wotv_utils.name_str(row, alias=0),
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(name=wotv_utils.dicts['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                         icon_url=wotv_utils.dicts['embed']['author_icon_url'])
        embed_colours = set() # Set to prevent duplicates
        for col in ('Unit', 'Party', 'Party Max', 'Skill'):
            if not row[col]: # Empty column
                continue
            effstr_list = []
            eff_prefixes = [] # Condition prefixes
            for eff in row[col].split(' / '):
                match_brackets = wotv_utils.reconditions.findall(eff)
                if match_brackets:
                    conditions = match_brackets[0] \
                                 .strip('[]').lower().split('/')
                    eff_prefixes = []
                    eff_text = eff.replace(match_brackets[0], '').strip()
                else:
                    conditions = []
                    eff_text = eff
                for condition in conditions: # Skipped if no new condition
                    if condition in wotv_utils.dicts['colours'].keys():
                        eff_prefixes.append(
                            wotv_utils.dicts['emotes'][condition]
                        )
                        embed_colours.add(
                            wotv_utils.dicts['colours'][condition]
                        )
                    if condition in wotv_utils.dicts['weapons']:
                        eff_prefixes.append(
                            wotv_utils.dicts['emotes'][f"w_{condition}"]
                        )
                    if not eff_prefixes: # Special condition
                        eff_prefixes = [match_brackets[0]] # Whole bracket
                        break
                effstr_list.append(f"{' '.join(eff_prefixes)} {eff_text}")
            f_value = '\n'.join(effstr_list)
            embed.add_field(name=col, value=f_value)
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
    def vcsearch(cls, arg):
        """Generates vision card search embeds."""
        df = dfwotv.vc
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
            vc_dicts[key] = {k: [] for k in wotv_utils.dicts['colours'].keys()}
        # Search df
        for _, row in df.iterrows():
            vc_ele = '' # Determined by max effect for universal vc
            vcdict = {'p': [], 'u': []} # List of party and unit effects
            suffix_icons = []
            if row['Rarity'] == 'UR':
                key_suffix = 'UR'
            else:
                key_suffix = ''
            for col, key_prefix, max_icon in (
               ('Party Max', 'p', f"{wotv_utils.dicts['emotes']['vcmax']} "),
               ('Party', 'p', ''),
               ('Unit', 'u', '')
            ):
                eff_prefixes = []
                for eff in row[col].split(' / '):
                    # Process the brackets first in case conditional effect is matched
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if match_brackets:
                        conditions = match_brackets[0] \
                                     .strip('[]').lower().split('/')
                        eff_prefixes = []
                    else:
                        conditions = []
                    for condition in conditions:
                         # Remove previous conditions if new effect with conditions
                        if condition in wotv_utils.dicts['colours'].keys():
                            eff_prefixes.append(
                                wotv_utils.dicts['emotes'][condition]
                            )
                            if vc_ele == '':
                                vc_ele = condition
                            elif vc_ele != condition: # Multi-elemental VC
                                vc_ele = 'neutral' # For sorting only
                        if condition in wotv_utils.dicts['weapons']:
                            eff_prefixes.append(
                                wotv_utils.dicts['emotes'][f"w_{condition}"]
                            )
                        if not eff_prefixes: # Special condition
                            eff_prefixes = [match_brackets[0]]
                            break
                    if args in eff.lower(): # Match Found
                        eff_suffix = '' # Actual effect numbers.
                        match_numbers = wotv_utils.revalues.findall(eff)
                        additional_icon = ''
                        if not eff_prefixes: # Add max effect element icon if universal
                            additional_icon = f" {''.join(suffix_icons)}"
                            eff_prefixes = [wotv_utils.dicts['emotes']['allele']]
                        if match_numbers:
                            eff_suffix = match_numbers[0]
                        vcdict[key_prefix].append(
                            f"{''.join(eff_prefixes)}{wotv_utils.name_str(row, name='')} - {max_icon}{eff_suffix}{additional_icon}"
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
            colour=wotv_utils.dicts['embed']['default_colour'],
        )
        embed.set_author(name=wotv_utils.dicts['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                         icon_url=wotv_utils.dicts['embed']['author_icon_url'])
        # Change embed colour if requested effect is elemental
        for colour, colour_code in wotv_utils.dicts['colours'].items():
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
        df = dfwotv.vc
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
        if ele in wotv_utils.dicts['colours'].keys() and ele != 'neutral':
            args = ele
            embed = discord.Embed(
                title=f"{wotv_utils.dicts['emotes'][ele]} {arg[0].title()}",
                colour=wotv_utils.dicts['colours'][ele]
            )
        elif args in wotv_utils.dicts['weapons']:
            w_emote = wotv_utils.dicts['emotes'][f"w_{args}"]
            embed = discord.Embed(
                title=f"{w_emote} {args.title()}",
                colour=wotv_utils.dicts['colours']['neutral']
            )
            df_job = dfwotv.text[dfwotv.text['Key'] == 'vc_job']
            if args in df_job['Title'].tolist():
                embed.description = df_job[df_job['Title'] == args]['Body'].tolist()[0]
        else: # Return empty list if match fail, otherwise there has to be some results
            return 1, []
        # Initialise
        embed.set_author(name=wotv_utils.dicts['embed']['author_name'],
                         url='https://wotv-calc.com/JP/cards',
                        icon_url=wotv_utils.dicts['embed']['author_icon_url'])
        col_tuples = (
            ('Party Max', wotv_utils.dicts['emotes']['vcmax']),
            ('Party', '')
        )
        vctuples_list = []
        # Search df
        for index, row in df.iterrows():
            vc_match = 0 # Flag to indicate vc matching criterion
            vctuples = [] # List of (vc name + effect prefixes, effect) to facilitate sorting
            for col, col_prefix in col_tuples:
                conditional = 0 # Flag for universal prefix
                eff_prefixes = [] # Prefix for other conditions sharing effect
                for eff in row[col].split(' / '):
                    match_brackets = wotv_utils.reconditions.findall(eff)
                    if match_brackets:
                        conditional = 1
                        conditions = match_brackets[0] \
                                     .strip('[]').lower().split('/')
                        eff_text = eff.replace(match_brackets[0], '').strip()
                        eff_prefixes = [] # Reset prefix
                    else:
                        conditions = []
                        eff_text = eff
                    for condition in conditions:
                         # Remove previous conditions if new effect with different conditions
                        if condition == args: # Condition match found
                            vc_match = 1
                        elif condition in wotv_utils.dicts['colours'].keys():
                            eff_prefixes.append(
                                wotv_utils.dicts['emotes'][condition]
                            )
                        elif condition in wotv_utils.dicts['weapons']:
                            eff_prefixes.append(
                                wotv_utils.dicts['emotes'][f"w_{condition}"]
                            )
                        else:
                            eff_prefixes.append(
                                f"[{condition.title()}]"
                            )
                    if eff_prefixes:
                        final_prefix = f"{''.join(eff_prefixes)} "
                    elif not conditional:
                        final_prefix = f"{wotv_utils.dicts['emotes']['allele']} "
                    else:
                        final_prefix = ''
                    vctuples.append((
                        f"{wotv_utils.name_str(row, name='')} - {col_prefix}{final_prefix}",
                        eff_text
                    ))
            if vc_match:
                vctuples_list.extend(vctuples)
        # Print while keeping track of characters.
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
        df = dfwotv.esper
        row_error, row = wotv_utils.find_row(df, ' '.join(arg))
        if row_error:
            return row_error, row
        embed = discord.Embed(
            title=wotv_utils.name_str(row, alias=0),
            colour=wotv_utils.dicts['colours'][row['Element'].lower()]
        )
        embed.set_author(
            name=wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/espers',
            icon_url=wotv_utils.dicts['embed']['author_icon_url']
        )
        esstr_list = []
        for col in wotv_utils.dicts['esper_stats']:
            esstr_list.append(f"`{col}{' ' * (4 - len(col))}` `{row[col]}`")
        embed.add_field(name='Stat',
                        value='\n'.join(esstr_list),
                        inline=False)
        esstr_list = []
        # Effect columns
        for col, suffix in wotv_utils.dicts['esper_colsuffix'].items():
            if row[col]:
                eff_list = row[col].split(' / ')
                for eff in eff_list:
                    re_match = wotv_utils.revalues.search(eff)
                    effstr = eff
                    if suffix:
                        effstr = f"{eff[:re_match.start()]}{suffix}"
                    esstr_list.append(f"{effstr} - `{re_match.group()}`")
        embed.add_field(name='Max Effects',
                        value='\n'.join(esstr_list),
                        inline=False)
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        embed.add_field(name='WOTV-CALC',
                        value=wotv_utils.calc_url('esper', row.name),
                        inline=False)
        return 0, [embed]

    @classmethod
    def espersearch(cls, arg):
        """Generates esper search embeds."""
        df = dfwotv.esper
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
        if first_col == 'NOTFOUND':
            return 1, []
        if first_arg == 'STAT': # If stat, find 20 largest values
            row_df = df.nlargest(20, first_col)
        else:
            row_df = df[df[first_col].str.lower().str.contains(first_arg)]
        # Parse arguments for display
        if first_arg in ('y', 'n'): # If first filter is just yes/no, leave it out of display feature
            arg = arg[1:]
        heading_list = []
        arg_tuples = []
        for argstr in arg: # Skip if arg is empty
            if argstr.upper() in wotv_utils.dicts['esper_stats']:
                arg_tuples.append((argstr.upper(), 'STAT'))
                heading_list.append(argstr.upper())
            else:
                col, esper_arg = wotv_utils.esper_findcol(argstr)
                if col != 'NOTFOUND':
                    arg_tuples.append((col, esper_arg))
                    heading = esper_arg.title()
                    suffix = wotv_utils.dicts['esper_colsuffix'][col]
                    if suffix:
                        heading = f"{heading} {suffix}"
                    heading_list.append(heading)
        # Initialise
        esstr_list = []
        eslist_list = []
        # Search df
        for index, row in row_df.iterrows():
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
                            re_match = wotv_utils.revalues.findall(eff)
                            eslist.append(re_match[0])
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
            esstr = wotv_utils.name_str(row_df.loc[eslist[0]], alias=0)
            if eslist:
                esstr += f" - `{' | '.join(eslist[1:])}`"
            esstr_list.append(esstr)
        tuple_list = cls.split_field(
            'Esper - ' + ' | '.join(heading_list), esstr_list
        )
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(name=wotv_utils.dicts['embed']['author_name'],
                         url='https://wotv-calc.com/JP/espers',
                         icon_url=wotv_utils.dicts['embed']['author_icon_url'])
        # Change embed colour if requested effect is elemental.
        for colour, colour_code in wotv_utils.dicts['colours'].items():
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
        df = dfwotv.esper
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
            row_error, row = wotv_utils.find_row(df, argstr)
            if not row_error:
                row_list.append(row)
                esper_list.append(wotv_utils.name_str(row, alias=0))
        if len(esper_list) < 2: # Need 2 or more espers to compare
            return 1, esper_list
        # Initialise
        stat_dict = {stat: [] for stat in wotv_utils.dicts['esper_stats']}
        effdict_dict = {col: dict() for col in #effs_dict[col][effstr][esper id]
            wotv_utils.dicts['esper_colsuffix'].keys()}
        # Process each esper
        for i, row in enumerate(row_list):
            for stat in stat_dict.keys():
                stat_dict[stat].append(str(row[stat]))
            for col, suffix in wotv_utils.dicts['esper_colsuffix'].items():
                eff_list = row[col].split(' / ')
                for eff in eff_list:
                    re_match = wotv_utils.revalues.search(eff)
                    if re_match == None:
                        continue
                    effstr = eff
                    if suffix:
                        effstr = f"{eff[:re_match.start()]}{suffix}"
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
            f"{stat} - `{' | '.join(stat_values)}`" for stat, stat_values in stat_dict.items()
        ]) + cls.split_field('Max Effects - ' + ' | '.join(esper_list), [
            f"{effstr} - `{' | '.join(eff_values)}`" for effstr, eff_values in eff_dict.items()
        ])
        embed = discord.Embed(
            colour=wotv_utils.dicts['embed']['default_colour'],
            title=args.title()
        )
        embed.set_author(
            name=wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/espers',
            icon_url=wotv_utils.dicts['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list)
        if not embed_list:
            return 1, embed_list
        return 0, embed_list

    @classmethod
    def eqinfo(cls, arg):
        """Generates equipment information embed."""
        df = dfwotv.eq
        row_error, row = wotv_utils.find_row(df, ' '.join(arg))
        if row_error:
            return row_error, row
        description_list = [wotv_utils.name_str(row, name='', alias=2)]
        effstr_list = []
        embed_colours = []
        if row['Restriction']:
            description_list.append(f"*Restriction: {row['Restriction']}*")
            if row['Restriction'].lower() in wotv.utils.dicts['colours'].keys():
                embed_colours = [ # Mostly for elemental rings
                    wotv.utils.dicts['colours'][row['Restriction']]
                ]
        condition = ''
        for eff in row['Passive'].split(' / '):
            match_brackets = wotv_utils.reconditions.findall(eff)
            if match_brackets:
                condition = match_brackets[0]
                effstr_list.append(eff)
            elif condition == '':
                effstr_list.append(eff)
            else:
                effstr_list.append(f"{condition} {eff}")
        description_list.extend(effstr_list)
        if row['Extra'] != '':
            description_list.append(
                f"{wotv_utils.dicts['emotes']['heartquartzs']} {row['Extra']}"
            )
        # Change embed colour if there are elemental passives
        if not embed_colours:
            for colour, colour_code in wotv_utils.dicts['colours'].items():
                if colour in row['Passive']:
                    embed_colours.append(colour_code)
        if not embed_colours:
            embed_colours=[wotv_utils.dicts['embed']['default_colour']]
        embed = discord.Embed(
            title=row.name,
            description = '\n'.join(description_list),
            colour=random.choice(embed_colours)
        )
        embed.set_author(
            name=wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url=wotv_utils.dicts['embed']['author_icon_url']
        )
        embed.add_field(name='Acquisition', value=row['Acquisition'],
                        inline=True)
        # Craft materials (legacy)
        material_list = []
        for col in ['Regular', 'Rare', 'Cryst', 'Ore']:
            if row[col] != '':
                if col == 'Cryst':
                    material_list.append(wotv_utils.get_cryst(row))
                else:
                    engstr = dfwotv.mat.loc[row[col]]['Aliases'].split(' / ')[0]
                    material_list.append(f"- {row[col]} ({engstr})")
        if material_list:
            embed.add_field(
                name='List of materials',
                value='\n'.join(material_list),
                inline=True
            )
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
        df = dfwotv.eq
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
        for _, row in df.iterrows():
            if args in row['Passive'].lower() or args in row['Extra'].lower():
                eqstr_list.append(wotv_utils.eq_str(row))
        if not eqstr_list: # No match
            return 1, eqstr_list
        tuple_list = cls.split_field(BLANK, eqstr_list)
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        for colour, colour_code in wotv_utils.dicts['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list, embed_limit=3)
        if not embed_list:
            return 1, embed_list
        else:
            return 0, embed_list

    @classmethod
    def eqlist(cls, arg):
        """Generates equipment list embeds."""
        df = dfwotv.eq
        # Process keywords
        args = ' '.join(arg).lower()
        col = ''
        match_str = ''
        for dict_col, dict_set in wotv_utils.dicts['eq_sets'].items():
            col_args = args
            if dict_col == 'Type':
                for index, row in dfwotv.eq_type.iterrows():
                    col_args = col_args.replace(index, row['VC'])
            for set_item in dict_set:
                if col_args in set_item.lower():
                    col = dict_col
                    match_str = set_item
                    break
        if not col: # No match
            return 1, []
        eqstr_list = []
        # Search df
        for _, row in dfwotv.eq.iterrows():
            if match_str in row[col]:
                eqstr_list.append(wotv_utils.eq_str(row))
        tuple_list = cls.split_field(BLANK, eqstr_list)
        embed = discord.Embed(
            title=f"List of {col} - {match_str}",
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/equipment',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list)
        return 0, embed_list

    @classmethod
    def tminfo(cls, arg):
        """Generates trust master information embed."""
        df = dfwotv.tm
        row_error, row = wotv_utils.find_row(df, ' '.join(arg))
        if row_error:
            return row_error, row
        # Process equipment info
        description_list = [wotv_utils.name_str(row, name='', alias=3)]
        if row['Restriction']:
            description_list.append(f"*Restriction: {row['Restriction']}*")
        embed = discord.Embed(
            title = row.name,
            description = '\n'.join(description_list),
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/units',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        stat_list = []
        for stat_name in wotv_utils.dicts['tm_stats']:
            if row[stat_name]:
                stat_list.append(f"**{stat_name}** {row[stat_name]}")
        embed.add_field(
            name='Stats', value='\n'.join(stat_list), inline=False
        )
        eff_list = []
        if row['Passive']: # If the TM has a passive
            embed.add_field(
                name='Passive',
                value='\n'.join(row['Passive'].split(' / ')),
                inline=False
            )
        if row['Skill']: # If the TM has a skill
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
        if row['Url']:
            embed.set_thumbnail(url=row['Url'])
        if row['English']:
            embed.add_field(
                name='WOTV-CALC',
                value='\n'.join((
                    wotv_utils.calc_url('equipment', row['English']),
                    wotv_utils.calc_url('units', row.name)
                )),
                inline=False)
        return 0, [embed]

    @classmethod
    def tmsearch(cls, arg):
        """Generates trust master search embeds."""
        df = dfwotv.tm
        # Process keywords
        target = ''
        range_list = ('Self', 'Ranged', 'Single', 'Plus', 'Diamond', 'none')
        for skill_range in range_list:
            if arg[0].lower() == skill_range.lower():
                target = skill_range
                args = ' '.join(arg[1:])
                break
            elif arg[-1].lower() == skill_range.lower():
                target = skill_range
                args = ' '.join(arg[:-1])
                break
        else:
            args = ' '.join(arg)
        args = args.lower()
        if not target:
            target = 'NONE'
        elif target == 'none':
            target = '' # For search purpose
        # Filter appropriately
        if target == 'NONE':
            pass
        elif target == 'Ranged':
            df = df[df['S Range'].replace('', 0).astype('int') > 0]
        else:
            df = df[df['S Area'] == target]
        # STAT AND PASSIVES
        statstr_list = []
        if args.upper() in wotv_utils.dicts['tm_stats']: # STAT
            df_filtered = df[df[args.uppper()].replace('', 0),astype('int') > 0]
            if len(df_filtered):
                row_df = df_filtered.nlargest(20, args.upper())
            for _, row in row_df.iterrows():
                statstr_list.append(wotv_utils.tm_str(row, 'stat'))
        elif not args: # PASSIVE
            # Search each tm
            for _, row in df.iterrows():
                in_list = 0
                if args in row['Passive'].lower():
                    statstr_list.append(wotv_utils.tm_str(row, 'stat'))
        # SKILL
        skillstr_list = []
        if len(args.split()) == 1:
            args = wotv_utils.shortcut_convert(args)
        for index, row in dfwotv.replace.iterrows():
            args = args.replace(index, row['VC'])
        for _, row in df.iterrows():
            in_list = 0
            if args in row['Skill'].lower():
                skillstr_list.append(wotv_utils.tm_str(row, 'skill'))
        tuple_list = cls.split_field('TM by Stats', statstr_list) + \
                     cls.split_field('TM by Skills', skillstr_list)
        if not tuple_list:
            return 1, tuple_list
        embed = discord.Embed(
            title=args.title(),
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        if target != 'NONE':
            embed.description = f"Target Filter: {target}"
        for colour, colour_code in wotv_utils.dicts['colours'].items():
            if colour in args:
                embed.colour = colour_code
                break
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            url='https://wotv-calc.com/JP/units',
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
        )
        embed_list = cls.split_embed(embed, tuple_list, embed_limit=2)
        if not embed_list:
            return 1, embed_list
        else:
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
                (('esper',), wotv_utils.help_esper),
                (('eq', 'tm', 'equip', 'trust'), wotv_utils.help_eq),
                (('param',), wotv_utils.help_param),
                (('stars', 'ramada', 'moore'), wotv_utils.help_ramada),
                (('events'), wotv_utils.help_events),
                (('materia', 'rune'), wotv_utils.help_materia),
            ):
                if arg[0].lower() in key:
                    help_tuples = value
                    break
        embed = discord.Embed(
            title='Ildyra Bot Help',
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
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
            _, embed_list = cls.help(help_str)
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
                f"Sorry, too many results. Try: {' / '.join(embed_list)}",
                None
            )
        return (
            1,
            f"Sorry, no result found. Try `=help {help_str}`.",
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
                await ctx.send('Google sheet synced for WOTV data.')
            elif arg[0] == 'text':
                wotv_utils.update_text()
                await ctx.send('Text updated. (If Google sheet is updated.)')
            elif arg[0] == 'esper':
                # Update the set of effects per column in Esper
                wotv_utils.dicts['esper_sets'] = \
                    wotv_utils.esper_sets(dfwotv.esper)
                await ctx.send('Esper keyword sets updated.')
            elif arg[0] == 'events':
                dfwotv.sync_events()
                await ctx.send('Google sheet synced for WOTV events.')

    @commands.command(aliases=['help', 'about', 'info', 'aboutme', 'readme', 'Help'])
    async def wotvhelp(self, ctx, *arg):
        """Customised help command."""
        await self.log.log(ctx.message)
        _, embed_list = EmbedWotv.help(arg)
        await self.log.send(ctx, embeds=embed_list)

    @commands.command(aliases=['materia', 'materias', 'Materia', 'Materias',
                               'rune', 'runes', 'truststone', 'Truststone',
                               'truststones', 'Truststones'])
    async def wotvmaterias(self, ctx, *arg):
        """Command to call info regarding materias."""
        await self.log.log(ctx.message)
        embed = discord.Embed(
            title='Ildyra Bot Help',
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name=wotv_utils.dicts['embed']['author_name'],
            icon_url=wotv_utils.dicts['embed']['author_icon_url']
        )
        materia_tuples = wotv_utils.materia_set
        if arg:
            if arg[0].lower() in ('substat', 'sub', 'substats', 's'):
                materia_tuples = wotv_utils.materia_substat
                for f_name, f_value in materia_tuples:
                    embed.add_field(name=f_name, value=f_value, inline=True)
                await self.log.send(ctx, embed=embed)
                return
            elif arg[0].lower() in ('passive', 'passives', 'recraft', 'p'):
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
                        wotv_utils.dicts['event_tuples']:
                    for event_keyword in event_keywords:
                        if event_keyword in row['Event'].lower():
                            eventprefix = \
                                wotv_utils.dicts['emotes'][event_emote]
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
                colour = wotv_utils.dicts['embed']['default_colour']
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
        embed.colour = wotv_utils.dicts['colours'][npctup[2]]
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
            colour = wotv_utils.dicts['embed']['default_colour']
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
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        embed.set_author(
            name = wotv_utils.dicts['embed']['author_name'],
            icon_url = wotv_utils.dicts['embed']['author_icon_url']
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
            _, embeds = EmbedWotv.help('param')
            await self.log.send(
                ctx,
                'Redirected to `=help param`',
                embeds=embeds
            )
            return
        params = {k: v[0] for k, v in wotv_utils.dicts['paramcalc'].items()}
        args = ' '.join(arg)
        embed = discord.Embed(
            title = args,
            colour = wotv_utils.dicts['embed']['default_colour']
        )
        # Convert arg list to split with | instead.
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number
            re_match = wotv_utils.revalues.search(argstr)
            try:
                paramval = int(re_match.group())
                paramstr = argstr[0:re_match.start()].strip()
                for k, v in wotv_utils.dicts['paramcalc'].items():
                    if paramstr in v[1]:
                        if k not in ('agi', 'dex', 'luck') or paramval >= 0:
                            # Disallow negative values for the three stats.
                            params[k] = paramval
                        break
            except AttributeError:
                pass
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
                (EmbedWotv.tmsearch, 'Trust Master Search (`=tms`)'),
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
                    name = wotv_utils.dicts['embed']['author_name'],
                    url='https://wotv-calc.com/JP/equipment',
                    icon_url = wotv_utils.dicts['embed']['author_icon_url']
                )
                for col, eq_set in wotv_utils.dicts['eq_sets'].items():
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
            _, embeds = EmbedWotv.help('esper')
            await self.log.send(
                ctx,
                'Apparently you need some assistance. Redirected to `=help esper`',
                embeds=embeds
            )
            return
        magicites = {k: 0 for k in wotv_utils.dicts['magicites'].keys()}
        esper_start = 1
        bonus = 100
        neutral = 0
        args = ' '.join(arg)
        embed = discord.Embed(
            title=args,
            colour=wotv_utils.dicts['embed']['default_colour']
        )
        # Convert arg list to split with | instead
        arg = [a.lower().strip() for a in args.split('|')]
        for argstr in arg:
            # Find position and value of number
            if argstr == 'neutral':
                neutral = 1
                continue
            re_match = wotv_utils.revalues.search(argstr.rstrip('%'))
            try:
                paramval = int(re_match.group())
                paramstr = argstr[0:re_match.start()].strip()
                if paramstr in ('star', 'stars') and paramval in (1, 2, 3):
                    esper_start = paramval
                elif paramstr in ('bonus',) and 0 <= paramval <= 100:
                    bonus = paramval
                else:
                    for k in wotv_utils.dicts['magicites'].keys():
                        if paramstr == k.lower():
                            magicites[k] = max(paramval, 0)
                            break
            except AttributeError:
                pass
        # Actual calculations
        req_exp = sum([wotv_utils.dicts['esper_exp'][a] for a in \
            range(esper_start, 4, 1)])
        total_exp = 0
        for k, v in magicites.items():
            if neutral:
                total_exp += int(v * wotv_utils.dicts['magicites'][k]
                                 * (100+bonus) / 100 * 0.75)
            else:
                total_exp += (v * wotv_utils.dicts['magicites'][k]
                              * int((100+bonus) / 100))
        if neutral:
            xl_exp = (wotv_utils.dicts['magicites']['XL'] * (100+bonus) / 100
                      * 0.75)
        else:
            xl_exp = wotv_utils.dicts['magicites']['XL'] * (100+bonus) / 100
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
