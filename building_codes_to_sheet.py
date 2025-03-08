import pandas as pd
import json


with open('data/building_codes.json') as f:
    building_codes = json.load(f)
    

df = pd.DataFrame.from_dict(building_codes, orient='index')

# save to xlsx

# df.to_excel('data/building_codes.xlsx')

for county, data in building_codes.items():
    if not data['Adopted IRC'] or not data['Adopted IECC']:
        print(county)