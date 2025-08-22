import matplotlib.pyplot as plt #imports :-)
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from metpy.plots import USCOUNTIES
from shapely.geometry import shape
import requests
import json
import pandas as pd
import time
import requests
from datetime import datetime
import pytz
from math import hypot
from matplotlib.offsetbox import AnchoredText, OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import geopandas as gpd
from shapely.geometry import box
from colorama import Fore
import re
from polygonmaker import plot_alert_polygon
import os
from dotenv import load_dotenv
load_dotenv()

#TODO: these are roughly (ish) in order of do first/last. simpler stuff is kinda to the top
#DONE different color warnings tor = red, svr = yellow, flashflood = green, tor-r = wideborder red, pds-tor = magenta, svr-destructive/considerable = wideborder yellow
#DONE add to header text expiration time for warning
#DONE make bigger cities have bigger labels. could probably do a few "bins" e.g. >40000 biggest font, 10000-40000 medium font, <10000 small font? trial and error, should not be too hard.
#DONEchange city label font; thinking monospace all-caps for legibility. 
#DONE change city markers; thinking "plus" signs? 
#DONE make county borders thinner, help with legibility
#DONE fix it so that it only tries to plot cities in the map region, not plot everything in the dataset then only show a small subset
# check through list of params (hailsize, windspeed, torpossible, etc) and for the ones that are present, draw in box on map in corner of view
#DONE declutter map with place names: either:
    #1) manually change csv to have only chosen places names (easier, lots of trial and error to get it good. not scalable/applicable to different locales, would have to redo it for that)
    #2) write loop that checks lat/lon of each place being plotted and if it's too close to another lat/lon, don't plot. also account for zoom level, e.g. if we're more zoomed in, the lat/lon
        #between place names can be less, and if more zoomed out, then adjust the other way, have lat/lon tolerance be larger, to plot less names. 
        #also make sure bigger cities are plotted first, so they're not accidently left out. this method is probably a lot more work up front, but once it's working should be able to be
        #applied to multiple regions wihtout much difficulty
#DONE fix error with plotting cities where some are labeled like on the edge of the map. not sure how to do this.  
                                                              
#add support for pds tor warnings and considerable/destructive svr. could be a little box below the issued time ("this is a destructive storm! this is a paticularly dangerous situation! need to see how these come across in the json")
#fix weird scaling issue with different sized warnings        
#make cities out of the polygon paler                         
#maybe declutter the map some by either keeping zoom closer to the box or having lower density of ciites
# DONE figure out why adding warning to the posted_alerts[] list still plots again 
#make it so that updates to existing warnings don't post unless there is a different geometry or parameters. 
    #use the "references" field in the json to check, maybe?  
    #for svr warnings expiring, if there is no wind/hail value, then it is a cancellation
#optimisations!! once everything is working, make it fast. cache as much as possible, especially the city names csv, only have my region cities
                                                              
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")                 
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"      
                                                              
# Define your area by zone or county                          
target_bbox = { #this is the area that is being scanned for alerts as well
        "lon_min": -85.124817,                                
        "lon_max": -83.364258,                                
        "lat_min": 38.736946,
        "lat_max": 39.664914
    } 
test_bbox = {
        "lon_min": -98,
        "lon_max": -93,
        "lat_min": 40,
        "lat_max": 50
}

warning_types = ["Tornado Warning", "Severe Thunderstorm Warning", "Flash Flood Warning"]

# Store already posted alerts to prevent duplicates
posted_alerts = set()
start_time = time.time()

#FIX TO JUST TRISTATE AREA!!!! will be faster 

df_large = pd.read_csv('filtered_cities_all.csv')
logo_path= 'cincyweathernobg.png'
logo = mpimg.imread(logo_path)

roads = gpd.read_file("ne_10m_roads/ne_10m_roads.shp")

interstates_all = roads[roads['level'] == 'Interstate']
federal_roads_all = roads[roads['level'] == 'Federal']
#interstates.to_csv('interstates_filtered.csv')

def get_nws_alerts():
    
    try:
        response = requests.get(NWS_ALERTS_URL, headers={"User-Agent": "weather-alert-bot"})
        response.raise_for_status()
        alerts = response.json().get("features", [])
        print(f"Fetched {len(alerts)} total alerts from NWS")

        filtered_alerts = []
        for alert in alerts:
            properties = alert["properties"]
            event_type = properties.get("event")
            affected_zones = properties.get("geocode", {}).get("UGC", [])
            geometry = alert.get("geometry")
            
            def any_point_in_bbox(geo, bbox):
                #check if any vertex of a polygon is inside the target box
                if not geo or not geo.get('coordinates') or not geo['coordinates'][0]: #check for and skip empty geometries
                    return False
                points = geo["coordinates"][0]
                
                is_inside = any(
                    bbox['lon_min'] <= lon <= bbox['lon_max'] and \
                        bbox['lat_min'] <= lat <= bbox['lat_max']
                    for lon, lat in points
                )
                return is_inside #true/false

            if event_type in warning_types and any_point_in_bbox(geometry, test_bbox):
                print(f"Matching alert found: {event_type}, Zones: {affected_zones}")
                filtered_alerts.append(alert)

        print(f"Returning {len(filtered_alerts)} filtered alerts")
        return filtered_alerts
    except requests.RequestException as e:
        print(f"Error fetching NWS alerts: {e}")
        return []
    
def post_to_facebook(message, img_path): #message is string & img is https url reference to .jpg or .png
    if not img_path:
        print('no image path provided')
        return
    photo_upload_url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/photos"
    photo_payload = {
        "published": "false",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    
    try:
        with open(img_path, 'rb') as image_file:
            files = {'source': image_file}
            photo_response = requests.post(photo_upload_url, data = photo_payload, files = files)
        
        photo_response.raise_for_status()
        photo_id = photo_response.json()['id']
        print(Fore.GREEN + "Uploaded Image successfully" + Fore.RESET)
    
    except requests.RequestException as e:
        print(Fore.RED + f"Error uploading image: {e}" + Fore.RESET)
        print(Fore.RED + f"Response: {e.response.text}" + Fore.RESET) # More detailed error
        return
    except FileNotFoundError:
        print(Fore.RED + f"Error: Could not find image file at {img_path}" + Fore.RESET)
        return
    
        # create the post using the uploaded photo ID
    post_url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/feed"
    post_payload = {
        "message": message,
        "attached_media[0]": json.dumps({"media_fbid": photo_id}),
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    
    try:
        post_response = requests.post(post_url, data=post_payload)
        post_response.raise_for_status()
        print(Fore.GREEN + "Posted to Facebook successfully" + Fore.RESET)
    except requests.RequestException as e:
        print(Fore.RED + f"Error creating post: {e}" + Fore.RESET)
        print(Fore.RED + f"Response: {e.response.text}" + Fore.RESET)


#post_to_facebook("testing, testing", "https://plsn.com/site/wp-content/uploads/fig-2.-1920px-SMPTE_Color_Bars_16x9.png")

def clean_filename(name):
    return re.sub(r'[<>:"/\\|?*.]', '', name)

check_time = 60 #seconds of downtime between scans

def main():
    print(Fore.CYAN + 'Beginning monitoring of api.weather.gov/alerts/active')
    while True:
        print(Fore.LIGHTCYAN_EX + 'Start scan for alerts')
        print(Fore.RESET)
        alerts_stack = get_nws_alerts() #returns list of alerts that fit criteria
        
        for alert in alerts_stack:
            #get info about the alert
            properties = alert.get("properties", {})
            awips_id = alert['properties']['parameters'].get('AWIPSidentifier', ['ERROR'])[0] #ex. SVSILN or TORGRR
            clickable_alert_id = properties.get("@id") #with https, etc so u can click in terminal
            alert_id = properties.get("id") #just the id
            clean_alert_id = clean_filename(alert_id) #id minus speciasl chars so it can be saved
            maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
            maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
            floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
            references = properties.get('references') #returns as list
            new_geom = alert['geometry']
            #print(references)
            
            #this should stop cancelled warnings (which come through as svr/svs), but don't have a value for wind/hail from getting gfx made
            #also stops cancelled ffws (which don't have a source for the warning)
            null_check_passed = True
            if awips_id[:2] == "SV": #if alert is type svr or svs 
                if (maxWind == "n/a" and maxHail == "n/a"): #fix so it seperates svr and ffw so they dont always null out
                    null_check_passed = False
                    print(Fore.RED + f"Null check failed, SVR/SVS expired {clickable_alert_id}")
                else:
                    null_check_passed = True
            if awips_id[:2] == "FF": #same but for ffws
                if (floodDetection == "n/a"): #fix so it seperates svr and ffw so they dont always null out
                    null_check_passed = False
                    print(Fore.RED + f"Null check failed, FFW expired {clickable_alert_id}")
                else:
                    null_check_passed = True
                    
            ref_check_passed = True #default to true as not every alert has a ref check        
            if len(references) != 0: #check if alert refs older ones, and if they have the same lat/lon, then check if they have the same attributes
                ref_url = references[0]['@id']
                
                ref_response = requests.get(ref_url, headers={"User-Agent": "weather-alert-bot - kesse1ni@cmich.edu"}) #SHOULD just return a single alert
                ref_response.raise_for_status()
                ref_data = ref_response.json()
                ref_geom = ref_data['geometry']
                #print(new_geom)
                #print(ref_geom)
                new_shape = shape(new_geom) #shapely object to check for equals
                ref_shape = shape(ref_geom)
                ref_maxWind = ref_data['properties']['parameters'].get('maxWindGust', ["n/a"])[0]
                ref_maxHail = ref_data['properties']['parameters'].get('maxHailSize', ["n/a"])[0]
                print(Fore.LIGHTMAGENTA_EX + f"alert ({clickable_alert_id}) has ref: {ref_url}")
                print(Fore.RESET)
                if new_shape.equals(ref_shape):
                    print("equal geometry, checking attributes")
                    
                    if ref_maxWind == maxWind and ref_maxHail == maxHail:
                        print("new attributes = ref attributes, not posting")
                        ref_check_passed = False
                    elif (ref_maxWind != maxWind) or (ref_maxHail != maxHail):
                        print("new attributes differ from old ones, posting")
                        ref_check_passed = True
                else:
                    print("new alert has new geometry")
                    ref_check_passed = True
                        
            if alert_id not in posted_alerts and null_check_passed == True and ref_check_passed == True:
                message = (
                    f"Alert to generate gfx: {clickable_alert_id}"
                )
                print(Fore.LIGHTBLUE_EX + message)
                print(Fore.RESET) #sets color back to white for plot_alert_polygon messages
                alert_path = f'graphics/alert_{awips_id}_{clean_alert_id}.png'
                path, statement = plot_alert_polygon(alert, alert_path)
                print(statement)
                #post_to_facebook(statement, alert_path)
                posted_alerts.add(alert_id)
            elif alert_id in posted_alerts:
                message = (
                    f"Alert already handled: {clickable_alert_id}"
                )
                print(Fore.LIGHTBLUE_EX + message)
        print(Fore.LIGHTCYAN_EX + f'End scan for alerts - all gfx generated or previously handled. Rescan in {check_time}s')
        time.sleep(check_time)  # Check every x seconds

main()

'''
if __name__ == "__main__":
    main()
'''
