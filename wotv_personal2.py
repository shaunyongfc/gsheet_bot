import pandas as pd
import gspread
from gsheet_handler import myspreadsheet
SHARDS_REQ = {
    'UR+': [40, 80, 120, 160, 200, 80, 120, 200],
    'UR': [40, 80, 120, 160, 200, 80, 120, 200],
    'SSR': [20, 40, 80, 160, 200, 80, 120, 200]
    }
SHARDS_DAILY = {'UR+': 1, 'UR': 2, 'SSR': 3}
STAGE_NAME = ['LB +0', 'LB +1', 'LB +2', 'LB +3', 'LB +4', 'LB +5', 'J 19', 'J 22', 'J 25']
LB_SUPPRESS = 3

# process personal sheets of unit data into progress prediction

class Roster:
    def __init__(self, spreadsheet):
        self.unitlb = pd.DataFrame(spreadsheet.worksheet('WOTV_unitlb').get_all_records()).set_index('Unit')
        unithq = pd.DataFrame(spreadsheet.worksheet('WOTV_unithq').get_all_records())
        self.unitbr = unithq[unithq['Type'] != 1]
        self.unithq = unithq[unithq['Type'] != 0]
        self.brqueue = -1
        self.hqqueue = -1
        self.day_count = 0
    def unit_gain(self, name, gain):
        self.unitlb.loc[name, 'Shards'] += gain
        if self.unitlb.loc[name, 'Shards'] >= SHARDS_REQ[self.unitlb.loc[name, 'Rarity']][self.unitlb.loc[name, 'Stage']]:
            self.unitlb.loc[name, 'Shards'] -= SHARDS_REQ[self.unitlb.loc[name, 'Rarity']][self.unitlb.loc[name, 'Stage']]
            self.unitlb.loc[name, 'Stage'] += 1
            return 1
        else:
            return 0
    def daily(self):
        self.day_count += 1
        brcount = 0
        for index, row in self.unitbr.iterrows():
            if self.unitlb.loc[row['Unit'], 'Stage'] < row['Target']:
                brcount += 1
                if index > self.brqueue:
                    self.brqueue = index
                    print(f" - Barracks Update: {row['Unit']}")
                if self.unit_gain(row['Unit'], SHARDS_DAILY[self.unitlb.loc[row['Unit'], 'Rarity']]):
                    if self.unitlb.loc[row['Unit'], 'Stage'] >= LB_SUPPRESS:
                        print(f"Day {self.day_count}: {row['Unit']} -> {STAGE_NAME[self.unitlb.loc[row['Unit'], 'Stage']]}")
                if brcount == 5:
                    break
        hqcount = 0
        for index, row in self.unithq.iterrows():
            if self.unitlb.loc[row['Unit'], 'Stage'] < row['Target']:
                hq_gain = min(SHARDS_DAILY[self.unitlb.loc[row['Unit'], 'Rarity']], 10 - hqcount)
                hqcount += hq_gain
                if index > self.hqqueue:
                    self.hqqueue = index
                    print(f" - HQ Update: {row['Unit']}")
                if self.unit_gain(row['Unit'], hq_gain):
                    if self.unitlb['Stage'][row['Unit']] >= LB_SUPPRESS:
                        print(f"Day {self.day_count}: {row['Unit']} -> {STAGE_NAME[self.unitlb.loc[row['Unit'], 'Stage']]}")
                if hqcount == 10:
                    break
    def progress(self, days=360):
        for _ in range(days):
            self.daily()

if __name__ == '__main__':
    my_roster = Roster(myspreadsheet)
    my_roster.progress()
