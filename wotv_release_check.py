import pandas as pd
from gsheet_handler import DfHandlerWotv


dfwotv = DfHandlerWotv()
release_dict = dict()


def add_release(release_dict, release_date, release_str):
    if release_date in release_dict.keys():
        release_dict[release_date].append(release_str)
    else:
        release_dict[release_date] = [release_str]


# Populate dict
for index, row in dfwotv.tm.iterrows():
    add_release(release_dict, row['Release'], index)
    if row['EX']:
        add_release(release_dict, row['EX'], f"{index} EX")
    if row['Rein']:
        add_release(release_dict, row['TR'], f"{index} TR")
    if row['MA2']:
        add_release(release_dict, row['MA2'], f"{index} MA2")

for index, row in dfwotv.vc.iterrows():
    add_release(release_dict, row['Release'], index)

for index, row in dfwotv.eq.iterrows():
    add_release(release_dict, row['Release'], index)
    if row['Release+']:
        add_release(release_dict, row['Release+'], f"{index} +1")

# Print
for release_date in sorted(list(release_dict.keys())):
    print(release_date)
    print(release_dict[release_date])
