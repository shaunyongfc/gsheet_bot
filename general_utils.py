import discord
import re
import os
from dotenv import load_dotenv


class GeneralUtils():
    """An object that contains utility functions for general use."""
    def __init__(self, dfgen):
        """Object initialisation with a special dataframe handler object
        and a dictionary of ids as inputs.
        """
        load_dotenv()
        self.owner = int(os.getenv('OWNER'))
        self.logs = int(os.getenv('LOGS'))
        self.token = os.getenv('TOKEN')
        self.dfgen = dfgen
        self.res = re.compile(r'&\w+') # Regex for shortcuts.
        self.opdict = { # For mathematical calculations.
            '+': (lambda a, b: a + b),
            '-': (lambda a, b: a - b),
            '*': (lambda a, b: a * b),
            '/': (lambda a, b: a / b),
            '^': (lambda a, b: a ** b),
            '%': (lambda a, b: a % b),
        }
        self.math_errors = ('Zero Division Error', 'Overflow Error',
                            '... Excuse me?')
        self.tag_help = '\n'.join((
            'Since this function is only available privately, there are not many limitations.',
            'However be discreet while using them and do not abuse. I keep logs of my bot calls.',
            'Do NOT add mentions/pings to tags.',
            '`=tag keyword` to call contents of a keyword.',
            '`=tag keyword contents` to add contents to a keyword.',
            '`=tagrecent` to view list of recently-added keywords.',
            '`=tagedit serial contents` to change the contents of a tag with  aserial number.',
            '`=tagremove serial` to remove a tag with a serial number.',
            '`=tagserial serial` to view content of a serial number.',
        ))
        self.tag_disabled = False # Boolean to disable tags temporarily when needed

    def add_shortcut(self, *arg):
        """Parse command inputs to add message shortcuts and
        return result message.
        """
        if len(arg) == 3:
            try:
                int(arg[2])
                self.dfgen.add_shortcut(*arg)
                return 'Added.'
            except ValueError:
                return 'Non-integer id.'
        else:
            return 'Incorrect arguments.'

    def get_shortcut(self, name):
        """Get message shortcut contents from shortcut name."""
        row_index = self.dfgen.shortcuts[self.dfgen.shortcuts['Name']
                                         == name].index.tolist()[0]
        row = self.dfgen.shortcuts.iloc[row_index]
        if row['Type'] == 'channel':
            return row['id']
        elif row['Type'] == 'user':
            return f"<@{row['id']}>"
        elif row['Type'] == 'emote':
            return f"<:{row['Name']}:{row['id']}>"
        elif row['Type'] == 'aemote':
            return f"<a:{row['Name']}:{row['id']}>"
        elif row['Type'] == 'role':
            return f"<@&{row['id']}>"

    def message_process(self, argstr):
        """Process a message to replace all shortcut names with their
        respective contents.
        """
        re_matches = self.res.findall(argstr)
        for re_match in re_matches:
            try:
                argstr = argstr.replace(re_match,
                                        self.get_shortcut(re_match[1:]))
            except IndexError:
                pass
        return argstr

    def get_group(self, ctx):
        """Given message context get tag group."""
        group = 0
        channel_ids = self.dfgen.ids[
                            self.dfgen.ids['Type'].str.contains('TagC')]['ID']
        server_ids = self.dfgen.ids[
                            self.dfgen.ids['Type'].str.contains('TagS')]['ID']
        if ctx.channel.id in list(channel_ids):
            df = self.dfgen.ids[self.dfgen.ids['Type'].str.contains('TagC')]
            group = int(list(df[df['ID'] == ctx.channel.id]['Type'])[0][4:])
        elif ctx.guild.id in list(server_ids):
            df = self.dfgen.ids[self.dfgen.ids['Type'].str.contains('TagS')]
            group = int(list(df[df['ID'] == ctx.guild.id]['Type'])[0][4:])
        elif ctx.message.author.id == self.owner:
            group = list(self.dfgen.ids[self.dfgen.ids['Type'] \
                                                    == 'TagDefault']['ID'])[0]
        return group

    def math(self, mathstr):
        """Custom recursive math command."""
        mathstr = mathstr.strip()
        while True:
            # Handle brackets
            lbrackets = []
            for i, mathchar in enumerate(mathstr):
                if mathchar == '(':
                    lbrackets.append(i)
                elif mathchar == ')':
                    if len(lbrackets) == 1:
                        b_start = lbrackets.pop()
                        b_end = i
                        break
                    elif len(lbrackets) > 0:
                        lbrackets.pop()
            else:
                break
            # Call recursion for outermost bracket.
            mathstr = (mathstr[0:b_start].strip()
                       + self.math(mathstr[b_start+1:b_end].strip())
                       + mathstr[b_end+1:].strip())
        operation_found = 0
        for opstr, opfunc in self.opdict.items():
            # Check which operation to execute. Lowest priority first.
            op_index_list = [i for i, a in enumerate(mathstr) if a == opstr]
            if len(op_index_list) > 0:
                op_index = op_index_list[-1]
                # Call recursion for left and right side of the operator.
                leftstr = self.math(mathstr[:op_index])
                rightstr = self.math(mathstr[op_index+1:])
                if opstr == "%" and len(rightstr) == 0:
                    continue
                operation_found = 1
                try:
                    # Update mathstr with left and right results.
                    mathstr = str(opfunc(float(leftstr), float(rightstr)))
                except ValueError:
                    # Check if left or right already returned errors.
                    if self.math_errors[0] in [leftstr, rightstr]:
                        mathstr = self.math_errors[0]
                    elif self.math_errors[1] in [leftstr, rightstr]:
                        mathstr = self.math_errors[1]
                    else:
                        mathstr = self.math_errors[2]
                except ZeroDivisionError:
                    mathstr = self.math_errors[0]
                except OverflowError:
                    mathstr = self.math_errors[1]
        # Handle % sign
        if not operation_found and len(mathstr) > 1:
            if mathstr[-1] == "%":
                mathstr = mathstr.rstrip("%")
                try:
                    mathstr = str(float(mathstr) / 100)
                except ValueError:
                    mathstr = self.math_errors[2]
        return mathstr
