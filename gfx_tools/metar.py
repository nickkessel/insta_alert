import pandas as pd
import geopandas as gpd
from scipy.spatial import KDTree
from shapely.geometry import Point
from metpy.io import station_info
from colorama import Fore, Back
import requests, json
from datetime import datetime, timezone, timedelta

METAR_URL = 'https://api.weather.gov/stations/'

def build_kdtree():
    """
    Runs on startup and creates a pandas df of US METAR stations
    Creates a scipy KDTree for use later to search for the nearest station
    Returns:
        KDTree: a KDTree for all the METAR stations Pandas DF: dataframe of station ids and coords
    """    
    station_rows = []
    for sid, info in station_info.items():
        try: 
            lat = getattr(info, 'latitude', None)
            lon = getattr(info, 'longitude', None)
            if lat is not None and lon is not None:
                station_rows.append({
                    'station_id': sid,
                    'lat': lat,
                    'lon': lon
                })
        except Exception as e:
            continue

    df = pd.DataFrame(station_rows)
    #print(df)

    coords = df[['lat', 'lon']].values
    tree = KDTree(coords) #create the kdtree
    print(Back.GREEN + 'METAR: KDTree and df created successfully' + Back.RESET)
    return tree, df

def get_nearest_station(tree, df, lat, lon):
    """_summary_

    Args:
        tree (Scipy KDTree): A KDTree object (created on start-up)
        df (pandas DataFrame): A DataFrame of station IDs and lat/lons
        lat (float): latitude of the center of the alert polygon
        lon (float): longitude of the center of the alert polygon

    Returns:
        str: Station ID
        float: distance to nearest station (km)
    """    
    target_latlon = (lat, lon)
    distance_deg, idx = tree.query(target_latlon)
    nearest_station = df.iloc[idx]
    #print(nearest_station)
    station_coords = (nearest_station['lat'], nearest_station['lon'])
    target_geom = gpd.GeoSeries([Point(target_latlon[1], target_latlon[0])], crs= 'EPSG:4326')
    station_geom = gpd.GeoSeries([Point(station_coords[1], station_coords[0])], crs= 'EPSG:4326')

    target_proj = target_geom.to_crs(epsg=3857)
    station_proj = station_geom.to_crs(epsg=3857)

    distance_km = target_proj.distance(station_proj).values[0] / 1000
    print(Fore.LIGHTBLUE_EX + f'METAR: {round(distance_km,3)}km to {nearest_station['station_id']}' + Fore.RESET)
    return nearest_station['station_id'], distance_km

def get_station_temp(sid):
    """Gets station temp from a code

    Args:
        sid (string): METAR code for the target station

    Returns:
        float: temperature in Celsius
    """    
    STATION_URL = METAR_URL + f'{sid}/observations/latest'
    print(STATION_URL)
    station_temp = 0.0
    try:
        response = requests.get(STATION_URL, headers={"User-Agent": "weather-alert-bot"})
        #print(response.status_code)
    except Exception as e:
        print(Back.RED + f'METAR: Error {e} occurred while getting url {STATION_URL}.' + Back.RESET)
        return 0.0 #really normal winter temp so it just counts this part of the check as true
    data = response.json().get("properties", [])
    
    report_time = data.get('timestamp', [])
    report_time = datetime.fromisoformat(report_time)
    #print(report_time)
    current_time_utc = datetime.now(timezone.utc)
    threshold = timedelta(minutes=90) #can adjust to permit older or newer reports
    time_difference = current_time_utc - report_time
    is_older = time_difference > threshold #bool
    if not is_older:
        station_temp = data.get('temperature', 0.0).get('value', 0.0)
        #print(station_temp)
        return station_temp
    else:
        print(f'METAR: data for station {sid} was older than the threshold {threshold}. Returning dummy value.')
        return 0.0
    
#get_station_temp('KMOP')
