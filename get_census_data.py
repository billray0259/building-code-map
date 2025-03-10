# Total Population: B01003
# Median household income: B19013
# Median monthly housing costs: B25105

import pandas as pd
import geopandas as gpd
import json
from census_lib import fetch_census_data, variables
import os
import traceback  # Added import for stack trace functionality

def main():
    """
    Main function to collect census data for Colorado municipalities and save it to a spreadsheet.
    Uses data from the American Community Survey (ACS) 5-year estimates.
    - Total Population: B01003
    - Median household income: B19013
    - Median monthly housing costs: B25105
    """
    print("Loading municipality data...")
    # Load the municipalities data from the GeoJSON file
    municipalities_file = "/home/bill/dev/school/holt-research/building-code-map/data/gracy_3-9.geojson"
    municipalities_gdf = gpd.read_file(municipalities_file)
    
    print(f"Loaded {len(municipalities_gdf)} municipalities")
    
    # Load the TIGER/Line Places data which contains the GEOID needed for census API
    places_file = "/home/bill/dev/school/holt-research/building-code-map/data/tl_2024_08_place/tl_2024_08_place.geojson"
    places_gdf = gpd.read_file(places_file)
    
    print(f"Loaded {len(places_gdf)} places from TIGER/Line data")
    
    # Create a dataframe to store our results
    results = []
    
    # Census tables we want to fetch
    tables = {
        "B01003": "Total Population",
        "B19013": "Median Household Income",
        "B25105": "Median Monthly Housing Costs"
    }
    
    # Loop through each municipality
    for idx, municipality in municipalities_gdf.iterrows():
        name = municipality['name']
        print(f"Processing {name}...")
        
        # Try to find the matching place in the TIGER/Line data
        # Remove any special characters that might be in the name
        clean_name = name.split('?')[0].split('[')[0].strip()
        
        # Find matching place in TIGER/Line data
        match = places_gdf[places_gdf['NAME'].str.upper() == clean_name.upper()]
        
        if len(match) == 0:
            print(f"  ⚠️ Could not find {clean_name} in TIGER/Line data")
            # Add row with just municipality data but no census data
            municipality_data = {
                'Name': name,
                'Government': municipality['government'],
                'County': municipality['county'],
                'IRC': municipality['irc'],
                'IECC': municipality['iecc'],
                'Population': None,
                'Median Household Income': None,
                'Median Monthly Housing Costs': None
            }
            results.append(municipality_data)
            continue
        
        # Get the GEOID (used to fetch census data)
        geoid = match.iloc[0]['GEOID']
        
        # Create a dictionary to store municipality data
        municipality_data = {
            'Name': name,
            'Government': municipality['government'],
            'County': municipality['county'],
            'IRC': municipality['irc'],
            'IECC': municipality['iecc']
        }
        
        # Fetch census data for each table
        for table_id, table_name in tables.items():
            try:
                print(f"  Fetching {table_name}...")
                # Construct the UCGID from the GEOID
                ucgid = f"16000US{geoid}"
                data = fetch_census_data(table_id, [ucgid])
                
                # Get the variable name for the main estimate
                var_info = variables(table_id)
                main_var = [var for var in var_info if var.endswith('001E')][0]
                
                # Add the value to our municipality data
                if not data.empty and main_var in data.columns:
                    value = data[main_var].iloc[0]
                    municipality_data[table_name] = value
                else:
                    municipality_data[table_name] = None
                    print(f"  ⚠️ No data for {table_name}")
            except Exception as e:
                print(f"  ❌ Error fetching {table_name}: {e}")
                print("  📋 Stack trace:")
                print(traceback.format_exc())  # Print detailed stack trace
                municipality_data[table_name] = None
        
        # Add the municipality data to our results
        results.append(municipality_data)
    
    # Convert results to a DataFrame
    results_df = pd.DataFrame(results)
    
    # Clean up and format the data
    for col in ['Population', 'Median Household Income', 'Median Monthly Housing Costs']:
        if col in results_df:
            results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
    
    # Save to CSV
    output_file = "/home/bill/dev/school/holt-research/building-code-map/municipality_census_data.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\nData saved to {output_file}")
    
    # Also save to Excel for easier viewing
    excel_file = "/home/bill/dev/school/holt-research/building-code-map/municipality_census_data.xlsx"
    results_df.to_excel(excel_file, index=False)
    print(f"Data saved to {excel_file}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        print("📋 Full stack trace:")
        print(traceback.format_exc())  # Print detailed stack trace for any uncaught exceptions