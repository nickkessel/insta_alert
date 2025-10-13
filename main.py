from colorama import Fore, Back, Style
import time, datetime
load_time = time.time()
print(Back.LIGHTWHITE_EX + Fore.BLACK + 'Load 1' + Fore.RESET + Back.RESET)
from shapely.geometry import shape
import requests
import json
import requests
print(Back.LIGHTWHITE_EX + Fore.BLACK + 'Load 2' + Fore.RESET + Back.RESET)
import re
from polygonmaker import plot_alert_polygon
import os
from dotenv import load_dotenv
print(Back.LIGHTWHITE_EX + Fore.BLACK + 'Load 3' + Fore.RESET + Back.RESET)
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading #slideshow
import queue #slideshow
import config
from post_to_ig import  make_instagram_post, instagram_login
from error_handler import report_error
import ijson
import gzip
load_dotenv()
load_done_time = time.time() - load_time
print(Back.GREEN + Fore.BLACK + f'imports imported succesfully {load_done_time:.2f}s' + Fore.RESET + Back.RESET)

#CHANGES: Added Discord Webhook sending support; Added toggles to enable/disable sending to Facebook/Discord; Added toggle to enable/disable use of test bbox; Moved the DAMN colorbar;
#(cont.) Added preliminary support for SPS/SMW; Wording changes; PDS box changes for readability; Added more hazards to hazard box; Added more pop-ups utilizing PDS box system; -DK
#TODO: test for dust storm warning/snow squall warning, will take a while as 1; it's not winter, and 2; dust storm warnings dont get issued too often. DSW not implimented. SQW needs work. -DK
#DONE: figure out why it is so slow when you first start running the script
#TODO: rename project at some point
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
IS_TESTING = False # Set to True to use local files, False to run normally

warning_types = config.ALERT_TYPES_TO_MONITOR
# Store already posted alerts to prevent duplicates
posted_alerts = set()
start_time = time.time()

required_folders = ['graphics']

def get_nws_alerts():
    print(Fore.CYAN + f'Beginning monitoring of {NWS_ALERTS_URL} at {datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%Sz %m/%d")}' + Fore.RESET)
    try:
        response = requests.get(NWS_ALERTS_URL, headers={"User-Agent": "weather-alert-bot"}, stream = True)
        response.raise_for_status()
        #alerts = response.json().get("features", [])
        #handle alerts 1 by 1 in a stream, decompressing each file as you go
        decompressed_stream = gzip.GzipFile(fileobj=response.raw)
        alerts = ijson.items(decompressed_stream, 'features.item')
        print( Back.GREEN + Fore.BLACK + "Connected to alerts stream, start processing" + Style.RESET_ALL)

        filtered_alerts = []
        total_alerts_processed = 0
        for alert in alerts:
            total_alerts_processed += 1
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
            
            def county_in_selected(zones, target, skip = config.EVERYWHERE):
                if skip :
                    return True
                else:
                    if not target.isdisjoint(zones): 
                        #print('alert in target zones')
                        return True
                    else:
                        #print('alert not in target zones')
                        return False
                
            target_zones_set = set(config.ACTIVE_ZONES)
            if event_type in warning_types and county_in_selected(affected_zones, target_zones_set): # and any_point_in_bbox(geometry, config.ACTIVE_BBOX) :
                print(f"Matching alert found: {event_type}, Zones: {affected_zones}")
                filtered_alerts.append(alert)
            #else:
                #print(f'{event_type} not in zone')

        print(Back.GREEN + f"Returning {len(filtered_alerts)} filtered alerts. Total processed: {total_alerts_processed}" + Back.RESET)
        return filtered_alerts
    except requests.RequestException as e:
        print(f"Error fetching NWS alerts (request exception): {e}")
        return []
    except Exception as e:
        print(f'An error occurred during JSON stream processing: {e}')
        return []

def log_to_discord(message, img_path):
    webhook = DiscordWebhook(url=config.WEBHOOKS[0], content=message)
    with open(img_path, 'rb') as f:
        webhook.add_file(file=f.read(), filename='Alert.png')
    try:
        print(Fore.GREEN + "Sent to Discord webhook successfully!" + Fore.RESET)
        response = webhook.execute()
    except Exception as e:
        print(Fore.RED + f"Error sending to webhook! {e}" + Fore.RESET)

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

def clean_filename(name):
    return re.sub(r'[<>:"/\\|?*.]', '', name)


def are_alerts_different(new_alert, ref_alert):
    """
    Only works with polygon based alerts 
    Compares a new alert with its reference to see if it's a significant update.
    Returns True if it's new/different and should be posted.
    Returns False if it's a non-critical duplicate update.
    Returns the "action", like upgraded or continued
    """
    new_geom = new_alert.get('geometry')
    ref_geom = ref_alert.get('geometry')
    new_params = new_alert['properties']['parameters']
    ref_params = ref_alert['properties']['parameters']
    alert_type = new_alert['properties'].get("event")


    # Case 1: Both are polygon-based (e.g., Warnings)
    if new_geom and ref_geom: #add another check where it only does the parameters stuff for tor and svr, and if/else for ffws, and have seperate logic for those
        if alert_type == 'Severe Thunderstorm Warning' or alert_type == 'Tornado Warning' or alert_type == 'Tornado Emergency': #not sure if that last one comes through as a seperate thing but worht a shot
            print("checking SVR/TOR attributes...")

            new_maxWindGust = new_params.get('maxWindGust', ["0"])[0]
            new_maxWindGust = re.sub('[^0-9]','', new_maxWindGust) #regex to remove all letters/spaces
            ref_maxWindGust = ref_params.get('maxWindGust', ["0"])[0]
            ref_maxWindGust = re.sub('[^0-9]','', ref_maxWindGust)
            new_maxHailSize = new_params.get('maxHailSize', ["0.0"])[0] 
            new_maxHailSize = re.sub('[^0-9.]','', new_maxHailSize) #regex to remove all letter/spaces while keeping in the decimals
            ref_maxHailSize = ref_params.get('maxHailSize', ["0.0"])[0]
            ref_maxHailSize = re.sub('[^0-9.]','', ref_maxHailSize)
            new_tornadoDetection = new_params.get('tornadoDetection', [None])[0]
            ref_tornadoDetection = ref_params.get('tornadoDetection', [None])[0]
            new_torSeverity = new_params.get('tornadoDamageThreat', [None])[0]
            ref_torSeverity = ref_params.get('tornadoDamageThreat', [None])[0]
            
            print(new_maxWindGust,ref_maxWindGust,new_maxHailSize,ref_maxHailSize,new_tornadoDetection,ref_tornadoDetection,new_torSeverity,ref_torSeverity)
            # Compare key attributes that would trigger a new post
            if (int(new_maxWindGust) > int(ref_maxWindGust) or float(new_maxHailSize) > float(ref_maxHailSize)):
                print("Wind/Hail has increased. UPGRADE")
                return True, 'upgraded'
            elif (new_tornadoDetection == 'POSSIBLE' and ref_tornadoDetection == None):
                print('tor possible, upgrade')
                return True, 'upgraded'
            elif (new_tornadoDetection == 'OBSERVED' and ref_tornadoDetection == 'RADAR INDICATED'):
                print('tor confirmed, upgrade')
                return True, 'upgraded'
            elif (new_torSeverity == 'CONSIDERABLE' and ref_torSeverity == None):
                print('tor severity upgraded, upgrade')
                return True, 'upgraded'
            elif (new_torSeverity == 'CATASTROPHIC' and ref_torSeverity == 'CONSIDERABLE'):
                print('tor severity upgraded, upgrade')
                return True, 'upgraded'
            elif (new_torSeverity == 'CATASTROPHIC' and ref_torSeverity == None):
                print('tor sevrity upgraded, upgrade')
                return True, 'upgraded'
            elif int(new_maxWindGust) == int(ref_maxWindGust) and float(new_maxHailSize) == float(ref_maxHailSize): #SHOULD check for downgrades tho#not checking for tor stuff atm as its kinda confusing with the tor detection
                print("attributes are the same, checking geometries")
                if shape(new_geom).equals(shape(ref_geom)):
                    print('geometries are equal, not plotting.')
                    return False, ''
                else:
                    print("Geometries are different.")
                    return True, 'continued'
            else:
                print(Back.YELLOW + "how did we get here?? (maybe downgrade?)" + Back.RESET)
                return True, 'continued' #really its more than likely a downgrade, but i dont want to say downgrade as that implies that its chill now (which it may not be)
        elif alert_type == 'Flash Flood Warning': #do ffw specific checks
            print("checking FFW attributes")
            new_ffwDetection = new_params.get('flashFloodDetection', [None])[0]
            ref_ffwDetection = ref_params.get('flashFloodDetection', [None])[0]
            new_ffwDamage = new_params.get('flashFloodDamageThreat', [None])[0]
            ref_ffwDamage = ref_params.get('flashFloodDamageThreat', [None])[0] #what is the default??? is there one???
            print(new_ffwDetection,ref_ffwDetection,new_ffwDamage,ref_ffwDamage)
            if (new_ffwDetection == 'OBSERVED' and ref_ffwDetection == 'RADAR INDICATED'):
                print('ffw confirmed, upgrade')
                return True, 'upgraded'
            elif (new_ffwDamage == 'CONSIDERABLE' and ref_ffwDamage == None):
                print('ffw severity upgraded, upgrade')
                return True, 'upgraded'
            elif (new_ffwDamage == 'CATASTROPHIC' and ref_ffwDamage == 'CONSIDERABLE'):
                print('ffw severity upgraded, upgrade')
                return True, 'upgraded'
            elif (new_ffwDamage == 'CATASTROPHIC' and ref_ffwDamage == None):
                print('ffw severity upgraded, upgrade')
                return True, 'upgraded'
            elif (new_ffwDetection == ref_ffwDetection and new_ffwDamage == ref_ffwDamage) or (new_ffwDetection == 'RADAR INDICATED' and ref_ffwDetection == 'OBSERVED') or (new_ffwDamage == None and (ref_ffwDamage == 'CONSIDERABLE' or ref_ffwDamage == 'CATASTROPHIC')): #if all attributes are the same, or a downgrade
                print("attributes are the same or downgraded, checking geometries")
                if shape(new_geom).equals(shape(ref_geom)):
                    print('geometries are equal, not plotting.')
                    return False, ''
                else:
                    print("Geometries are different.")
                    return True, 'continued'
            else:
                print(Back.YELLOW + "how did we get here?? (ffw, downgrades should be covered)" + Back.RESET)
                return True, 'continued'

        else:
            #print(f'{alert_type}, not sure how we got here?')#probably SPS or SMW or FLA, but i dont think they really do the whole references thing like other alerts do.
            if shape(new_geom).equals(shape(ref_geom)):
                print('geometries are equal, not plotting.')
                return False, ''
            else:
                print("Geometries are different.")
                return True, 'continued'
    # Case 2: Both are zone-based (e.g., Watches)
    elif not new_geom and not ref_geom:
        # Compare by checking if the set of affected zones (UGC codes) is identical
        new_ugc = set(new_alert['properties']['geocode'].get('UGC', []))
        ref_ugc = set(ref_alert['properties']['geocode'].get('UGC', []))
        
        if new_ugc == ref_ugc:
            print("Affected zones (UGC) are the same. This is a duplicate update.")
            return False, ''
        else:
            print("Affected zones (UGC) have changed.")
            return True, 'continued'

    # Case 3: Mixed types (one is polygon, one is zone). Treat as different.
    else:
        print("Alert type (polygon vs. zone) differs from reference.")
        return True, 'continued'

check_time = 60 #seconds of downtime between scans

def main():
    # --- Create a queue for communication between main thread and slideshow thread ---
    slideshow_queue = None
    if config.SEND_TO_SLIDESHOW:
        slideshow_queue = queue.Queue()
        from slideshow import run_slideshow
        # Start the slideshow in a daemon thread so it closes when the main script exits
        slideshow_thread = threading.Thread(
            target=run_slideshow, args=(slideshow_queue,), daemon=True
        )
        slideshow_thread.start()
        print(Fore.MAGENTA + "Slideshow thread started." + Fore.RESET)

   
    while True:
        print(Fore.LIGHTCYAN_EX + 'Start scan for alerts' + Fore.RESET)
        alerts_stack = []
        if IS_TESTING:
            print(Back.YELLOW + Fore.BLACK + "--- RUNNING IN TEST MODE ---" + Back.RESET + Fore.RESET)
            # in test mode, load the UPGRADED alert
            with open('test_alerts/svr-witharef.json', 'r') as f:
                loaded_alert = json.load(f)
                alerts_stack = [loaded_alert]
        else:
            # in normal mode, fetch live alerts
            alerts_stack = get_nws_alerts()
        #print(alerts_stack)
        for alert in alerts_stack:
            #get info about the alert
            properties = alert.get("properties", {})
            awips_id = alert['properties']['parameters'].get('AWIPSidentifier', ['ERROR'])[0] #ex. SVSILN or TORGRR
            event_type = properties.get("event")
            clickable_alert_id = properties.get("@id") #with https, etc so u can click in terminal
            alert_id = properties.get("id") #just the id
            expiry_time_iso = properties.get("expires") # <-- Added for slideshow
            clean_alert_id = clean_filename(alert_id) #id minus speciasl chars so it can be saved
            maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
            maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
            floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
            references = properties.get('references') #returns as list
            new_geom = alert['geometry']

            #this should stop cancelled warnings (which come through as svr/svs), but don't have a value for wind/hail from getting gfx made
            #also stops cancelled ffws (which don't have a source for the warning)
            #also will stop expired/cancelled flood watches
            null_check_passed = True
            if awips_id[:2] == "SV": #if alert is type svr or svs
                if (maxWind == "n/a" and maxHail == "n/a"): 
                    null_check_passed = False
                    print(Fore.RED + f"Null check failed, SVR/SVS expired {clickable_alert_id}")
                else:
                    null_check_passed = True
            if awips_id[:3] == "FFW" or awips_id[:3] == "FFS": #same but for ffws
                if (floodDetection == "n/a"): 
                    null_check_passed = False
                    print(Fore.RED + f"Null check failed, FFW expired {clickable_alert_id}")
                else:
                    null_check_passed = True
            if event_type == 'Flood Watch':
                if (properties.get('urgency') == "Past"):
                    null_check_passed = False
                    print(Fore.RED + f"Null check failed, Flood Watch expired {clickable_alert_id}")
                else:
                    null_check_passed = True

            ref_check_passed = True #default to true as not every alert has a ref check
            alert_verb = 'issued' #default to issued
            references = properties.get('references')
            if references:
                try:
                    ref_url = references[-1]['@id'] #always gets the last item in list, which is the most recent warning.
                    print(Fore.LIGHTMAGENTA_EX + f"Alert ({clickable_alert_id}) has reference: {ref_url}" + Fore.RESET)
                    if IS_TESTING: #testing for single local alert
                        with open (ref_url, 'r') as f:
                            ref_data = json.load(f)
                    else: #normal, get from the api
                        ref_response = requests.get(ref_url, headers={"User-Agent": "warnings_on_fb/kesse1ni@cmich.edu"})
                        ref_response.raise_for_status()
                        ref_data = ref_response.json()
                    
                    ref_check_passed, alert_verb = are_alerts_different(alert, ref_data) #check if the alert has a reference AND if its been upgraded
                    print(ref_check_passed, alert_verb)
                except Exception as e:
                    print(Fore.RED + f"Error processing reference alert: {e}" + Fore.RESET)

            if alert_id not in posted_alerts and null_check_passed == True and ref_check_passed == True:
                message = (
                    f"Alert to generate gfx: {clickable_alert_id}"
                )
                print(Fore.LIGHTBLUE_EX + message)
                print(Fore.RESET) #sets color back to white for plot_alert_polygon messages
                alert_path = f'graphics/alert_{awips_id}_{clean_alert_id}.jpg'
                try: #try/except as we were getting incomplete file errors!
                    plot_mrms = True #default, we want to plot radar
                    properties = alert["properties"]
                    no_mrms_list = ['Dense Fog Advisory', 'Freeze Warning', 'Frost Advisory']
                    if event_type in no_mrms_list:
                        plot_mrms = False
                    
                    try:
                        path, statement = plot_alert_polygon(alert, alert_path, plot_mrms, alert_verb)
                    except Exception as e:
                        report_error(e, context=f"Plotting {event_type} alert")
                        time.sleep(15)
                        continue

                    # --- If slideshow is enabled, send it the new alert info ---
                    if config.SEND_TO_SLIDESHOW and path and expiry_time_iso:
                        slideshow_queue.put((path, expiry_time_iso))
                    if config.POST_TO_FACEBOOK:
                        post_to_facebook(statement, alert_path)
                    if config.POST_TO_DISCORD:
                        log_to_discord(statement, alert_path)
                    if config.POST_TO_INSTAGRAM_STORY:
                        make_instagram_post(statement, alert_path, 'story', ig_client)
                    if config.POST_TO_INSTAGRAM_GRID:
                        make_instagram_post(statement, alert_path, 'grid', ig_client)
                    posted_alerts.add(alert_id)
                except Exception as e:
                    print(Back.RED + f'An error occurred. Waiting 15 seconds then restarting.' + Back.RESET)
                    time.sleep(15)
                    continue
            elif alert_id in posted_alerts:
                message = (
                    f"Alert already handled: {clickable_alert_id}"
                )
                print(Fore.LIGHTBLUE_EX + message)
        print(Fore.LIGHTCYAN_EX + f'End scan for alerts - all gfx generated or previously handled. Rescan in {check_time}s')
        time.sleep(check_time)  # Check every x seconds

for folder in required_folders:
    print(f"checking for required folder: {folder}")
    os.makedirs(folder, exist_ok= True)

if __name__ == "__main__":
    try:
        if config.POST_TO_INSTAGRAM_GRID or config.POST_TO_INSTAGRAM_STORY:
            ig_client = instagram_login(os.getenv("IG_USER"), os.getenv("IG_PASS"))
        main()
    except Exception as e:
        print(Back.RED + f"Fatal error: {e}" + Back.RESET)
        report_error(e, context="Top-level main()")
        raise  # optional — keeps the crash visible in logs
