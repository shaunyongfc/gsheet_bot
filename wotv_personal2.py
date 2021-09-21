# Process personal sheets of unit data into progress prediction.

import pandas as pd
import gspread

from gsheet_handler import wotvspreadsheet

SHARDS_REQ = {
    'UR': [40, 80, 120, 160, 200, 80, 120, 200],
    'SSR': [20, 40, 80, 160, 200, 80, 120, 200],
    }
SHARDS_DAILY = {'UR': 2, 'SSR': 3}
STAGE_NAME = ['LB +0', 'LB +1', 'LB +2', 'LB +3', 'LB +4', 'LB +5',
              'J 19', 'J 22', 'J 25']
LB_SUPPRESS = 4 # Omitted from printing of progress below this stage.


class Roster:
    """Object to store various roster growth parameters and unit data."""
    def __init__(self, spreadsheet):
        """Initialise with a spreadsheet object."""
        self.unitlb = pd.DataFrame(spreadsheet.worksheet('WOTV_unitlb')
                                   .get_all_records()).set_index('Unit')
        unithq = pd.DataFrame(spreadsheet.worksheet('WOTV_unithq')
                              .get_all_records())
        self.unitbr = unithq[unithq['Type'] != 1] # Includes 0 and 2.
        self.unithq = unithq[unithq['Type'] != 0] # Includes 1 and 2.
        self.brqueue = -1 # To track barracks lineup.
        self.hqqueue = -1 # To track HQ lineup.
        self.day_count = 0

    def unit_gain(self, name: 'Unit name index', gain: 'Integer shard gain.'):
        """Function to increase shard count for individual unit.
        Return a boolean indicating whether next stage is reached.
        """
        self.unitlb.loc[name, 'Shards'] += gain
        # Check if enough shards to reach next stage.
        rarity = self.unitlb.loc[name, 'Rarity']
        stage = self.unitlb.loc[name, 'Stage']
        if self.unitlb.loc[name, 'Shards'] >= SHARDS_REQ[rarity][stage]:
            self.unitlb.loc[name, 'Shards'] -= SHARDS_REQ[rarity][stage]
            self.unitlb.loc[name, 'Stage'] += 1
            return 1
        else:
            return 0

    def daily(self):
        """Function to process a day's worth of growth in the roster."""
        self.day_count += 1
        # Barracks gain.
        brcount = 0
        for index, row in self.unitbr.iterrows():
            # Check if unit already fulfills target.
            if self.unitlb.loc[row['Unit'], 'Stage'] < row['Target']:
                brcount += 1 # Barrack counts by number of units.
                if index > self.brqueue:
                    # Barracks lineup change.
                    self.brqueue = index
                    print(f" - Barracks Update: {row['Unit']}")
                if self.unit_gain(row['Unit'],
                        SHARDS_DAILY[self.unitlb.loc[row['Unit'], 'Rarity']]):
                    # Report that new stage is reached.
                    if self.unitlb.loc[row['Unit'], 'Stage'] >= LB_SUPPRESS:
                        print(''.join((f"Day {self.day_count}: {row['Unit']}",
                        ' -> ', STAGE_NAME[self.unitlb.loc[row['Unit'], \
                        'Stage']])))
                if brcount == 5:
                    # Barracks are full.
                    break
        # HQ gain.
        hqcount = 0
        for index, row in self.unithq.iterrows():
            # Check if unit already fulfills target.
            if self.unitlb.loc[row['Unit'], 'Stage'] < row['Target']:
                # Check the number of remaining entries.
                hq_gain = min(SHARDS_DAILY[self.unitlb.loc[row['Unit'],
                              'Rarity']], 10 - hqcount)
                hqcount += hq_gain # HQ counts by number of shards.
                if index > self.hqqueue:
                    # HQ lineup change.
                    self.hqqueue = index
                    print(f" - HQ Update: {row['Unit']}")
                if self.unit_gain(row['Unit'], hq_gain):
                    # Report that new stage is reached.
                    if self.unitlb['Stage'][row['Unit']] >= LB_SUPPRESS:
                        print(''.join((f"Day {self.day_count}: {row['Unit']}",
                        ' -> ', STAGE_NAME[self.unitlb.loc[row['Unit'], \
                        'Stage']])))
                if hqcount == 10:
                    # HQ entries are finished.
                    break

    def progress(self, days=180):
        """Function to progress growth in the roster for specified number of
        days.
        """
        for _ in range(days):
            self.daily()


if __name__ == '__main__':
    my_roster = Roster(wotvspreadsheet)
    my_roster.progress()
