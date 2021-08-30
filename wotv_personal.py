# Process a personal sheet of unit data into unit summary by category.
# Discontinued as no longer useful.

import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe

from gsheet_handler import wotvspreadsheet

ELEMENTS = ['Fire', 'Ice', 'Wind', 'Earth',
            'Thunder', 'Water', 'Light', 'Dark']
ROLES = ['Slash', 'Pierce', 'Strike', 'Missile', 'Magic', 'Heal', 'Tank']


def wotv_summary_process(spreadsheet):
    """Take a spreadsheet object as input and
    return processed table as pandas dataframe.
    """
    df_wotvunitcat = pd.DataFrame(
        spreadsheet.worksheet('WOTV_unitcat').get_all_records())
    df_wotvunitcat = df_wotvunitcat.set_index('Unit')
    list_elements = [] # Initialise list.
    for element in ELEMENTS:
        # Filter units by elements.
        df_element = df_wotvunitcat[df_wotvunitcat['Element'] == element]
        list_roles = [] #Initialise list.
        for role in ROLES:
            # Filter units with non-empty content in said role.
            df_role = df_element[df_element[role] != '']
            list_units = []
            for index, row in df_role.iterrows():
                if row[role] == 'Y':
                    # Add unit name if just Y.
                    list_units.append(index)
                else:
                    # Add unit name and special remark if cell content not Y.
                    list_units.append(f"{index} ({row[role]})")
            if len(list_units) > 0:
                # Join with commas if multiple entries for said role.
                list_roles.append(', '.join(list_units))
            else:
                list_roles.append('')
        # Add total members of that element at the end.
        list_roles.append(len(df_element))
        list_elements.append(list_roles)
    # Generate dataframe from list of lists.
    df = pd.DataFrame.from_records(data=list_elements,
                                   index=ELEMENTS,
                                   columns = ROLES + ['Sum'])
    return df


def wotv_summary_update(spreadsheet, summary_df):
    """Take a spreadsheet object as input and
    update it with a dataframe input.
    """
    set_with_dataframe(spreadsheet.worksheet('WOTV_unitsum'),
                       summary_df, include_index=True)


if __name__ == '__main__':
    wotv_summary_update(wotvspreadsheet, wotv_summary_process(wotvspreadsheet))
    print('Sheet updated!')
