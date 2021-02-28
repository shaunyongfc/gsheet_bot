import discord, re
from datetime import datetime

def logs_embed(msg):
    # Generate embed for command logging
    if msg.guild == None:
        embed = discord.Embed(title= f"{msg.channel}")
    else:
        embed = discord.Embed(title= f"{msg.guild} | {msg.channel}")
    embed.add_field(name='Content', value=msg.content)
    embed.add_field(name='Author', value=msg.author)
    embed.add_field(name='Time', value=datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M'))
    return embed

class GeneralUtils():
    def __init__(self, dfgen, id_dict):
        self.dfgen = dfgen
        self.res = re.compile(r'&\w+') # regex for shortcuts
        self.opdicts = {
            '+': (lambda a, b: a + b),
            '-': (lambda a, b: a - b),
            '*': (lambda a, b: a * b),
            '/': (lambda a, b: a / b),
            '%': (lambda a, b: a % b),
            '^': (lambda a, b: a ** b)
        }
        self.math_errors = ('Zero Division Error', 'Overflow Error', '... Excuse me?')
    def add_shortcut(self, *arg):
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
        row_index = self.dfgen.shortcuts[self.dfgen.shortcuts['Name'] == name].index.tolist()[0]
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
    def msg_process(self, argstr):
        re_matches = self.res.findall(argstr)
        for re_match in re_matches:
            try:
                argstr = argstr.replace(re_match, self.get_shortcut(re_match[1:]))
            except IndexError:
                pass
        return argstr
    def math(self, mathstr):
        # Custom math command (recursive)
        while True:
            # Handle brackets
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
            # recursion for outer brackets
            mathstr = mathstr[0:bstart] + self.math(mathstr[bstart+1:bend]) + mathstr[bend+1:]
        for opstr, opfunc in self.opdicts.items():
            # check which operation
            op_index_list = [i for i, a in enumerate(mathstr) if a == opstr]
            if len(op_index_list) > 0:
                op_index = op_index_list[-1]
                try:
                    leftstr = self.math(mathstr[:op_index]).strip()
                    rightstr = self.math(mathstr[op_index+1:]).strip()
                    mathstr = str(opfunc(float(leftstr), float(rightstr)))
                except ValueError:
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
        return mathstr
