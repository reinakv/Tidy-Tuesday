import pandas as pd
import time
from geopy.geocoders import Nominatim

# Load the dataset
df = pd.read_csv("MTA_Permanent_Art_Catalog.csv")

# Prepare unique station list for geocoding
stations_unique = df['station_name'].dropna().drop_duplicates()

# Set up geocoder
geolocator = Nominatim(user_agent="mta_geocoder", timeout=10)

# Function to geocode a station
def geocode_station(station):
    try:
        location = geolocator.geocode(f"{station} Station, New York, NY")
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding {station}: {e}")
        return None, None

# Geocode unique stations
results = []
for i, station in enumerate(stations_unique, start=1):
    print(f"Geocoding {i}/{len(stations_unique)}: {station}")
    lat, lon = geocode_station(station)
    results.append({"station_name": station, "lat": lat, "lon": lon})
    time.sleep(1)  # polite pause for API

coords_df = pd.DataFrame(results)

# Merge coordinates back to ALL artworks
df_with_coords = df.merge(coords_df, on="station_name", how="left")

# Save
df_with_coords.to_csv("station_coords.csv", index=False)

print(f"✅ Done! Saved station_coords.csv with {len(df_with_coords)} rows.")
