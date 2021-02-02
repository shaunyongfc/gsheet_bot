import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from gsheet_handler import  myspreadsheet
ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth', 'Thunder', 'Water', 'Light', 'Dark']
ROLES = ['Slash', 'Pierce', 'Strike', 'Missile', 'Magic', 'Heal', 'Tank']

# process a personal sheet of unit data into unit summary by category

def wotvsummary_process(spreadsheet):
    df_wotvunitcat = pd.DataFrame(spreadsheet.worksheet('WOTV_unitcat').get_all_records())
    df_wotvunitcat = df_wotvunitcat.set_index('Unit')
    list_elements = []
    for element in ELEMENTS:
        df_element = df_wotvunitcat[df_wotvunitcat['Element'] == element]
        list_roles = []
        for role in ROLES:
            df_role = df_element[df_element[role] != '']
            list_units = []
            for index, row in df_role.iterrows():
                if row[role] == 'Y':
                    list_units.append(index)
                else:
                    list_units.append(f"{index} ({row[role]})")
            if len(list_units) > 0:
                list_roles.append(', '.join(list_units))
            else:
                list_roles.append('')
        list_roles.append(len(df_element))
        list_elements.append(list_roles)
    df = pd.DataFrame.from_records(data=list_elements, index=ELEMENTS, columns=ROLES + ['Sum'])
    return df

def wotvsummary_update(spreadsheet, summarydf):
    set_with_dataframe(spreadsheet.worksheet('WOTV_unitsum'), summarydf, include_index=True)

if __name__ == '__main__':
    wotvsummary_update(myspreadsheet, wotvsummary_process(myspreadsheet))
    print('Sheet updated!')
