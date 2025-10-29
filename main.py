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
import os
from dotenv import load_dotenv
print(Back.LIGHTWHITE_EX + Fore.BLACK + 'Load 3' + Fore.RESET + Back.RESET)
import threading #slideshow
import queue #slideshow
from integrations.instagram import  make_instagram_post, instagram_login
from integrations.discord import log_to_discord
from integrations.facebook import post_to_facebook
from gfx_tools.watch_attributes import get_watch_attributes, get_watch_number
from helper.logging import load_posted_alerts, save_posted_alert
from helper.error_handler import report_error
import ijson
import gzip
load_dotenv()
load_done_time = time.time() - load_time
print(Back.GREEN + Fore.BLACK + f'imports imported succesfully {load_done_time:.2f}s' + Fore.RESET + Back.RESET)

import argparse
import config_manager


#CHANGES: Added Discord Webhook sending support; Added toggles to enable/disable sending to Facebook/Discord; Added toggle to enable/disable use of test bbox; Moved the DAMN colorbar;
#(cont.) Added preliminary support for SPS/SMW; Wording changes; PDS box changes for readability; Added more hazards to hazard box; Added more pop-ups utilizing PDS box system; -DK
#TODO: test for dust storm warning/snow squall warning, will take a while as 1; it's not winter, and 2; dust storm warnings dont get issued too often. DSW not implimented. SQW needs work. -DK
#TODO: rename project at some point

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
IS_TESTING = False # Set to True to use local files, False to run normally

# Store already posted alerts to prevent duplicates

start_time = time.time()

#handle convective watches
delayed_watches = []
queued_watch_ids = set()
WATCH_DELAY_TIME = 800 #seconds, should not take this long for watchCanBePlotted to come true, so if this qualifier hits, its a fallback as we don't want to wait much longer to post the watch

required_folders = ['graphics', 'logs']

def get_nws_alerts(warning_types):
    """Gets NWS Alerts from the API
    Args:
        warning_types (list): warning types to monitor for
    Returns:
        list: active alerts that are of the chosen type and in the given area.
    """    
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
            issuing_office = properties.get('senderName')
            issuing_time_str = properties.get('sent')
            local_dt = datetime.datetime.fromisoformat(issuing_time_str)
            utc_dt = local_dt.astimezone(datetime.timezone.utc)
            issuing_time = utc_dt.strftime("%m-%d %H:%Mz") #zulu time format
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
                print("Matching alert found: " + Fore.YELLOW + f"{event_type} - " + Fore.MAGENTA + f"{issuing_office}" + Fore.RESET + f" at {issuing_time}")
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

def clean_filename(name):
    return re.sub(r'[<>:"/\\|?*.]', '', name)

def are_alerts_different(new_alert, ref_alert):
    """
    Only works with polygon based alerts 
    Compares a new alert with its reference to see if it's a significant update.
    Returns True if it's new/different and should be posted.
    Returns False if it's a non-critical duplicate update, or a cancellation
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
        #print(f'New alert UGC: {new_ugc} \nRef aler UGC: {ref_ugc}')
        if new_ugc == ref_ugc:
            print("Affected zones (UGC) are the same. This is a duplicate update.")
            return False, ''
        else:
            if alert_type in ['Freeze Warning', 'Frost Advisory']: #have been having issues with these posting too much, not super important, so just won't post continuations
                #print('Different UGC, but not posting due to issues with Freeze/Frost zones and posting too much.')
                return False, ''
            else:
                print("Affected zones (UGC) have changed.")
                return True, 'continued'

    # Case 3: Mixed types (one is polygon, one is zone). Treat as different.
    else:
        print("Alert type (polygon vs. zone) differs from reference.")
        return True, 'continued'

def check_if_alert_is_valid(alert):
    """
    Checks if an alert is a cancellation or has expired.
    
    Returns True if the alert is valid for posting, False otherwise.
    """
    properties = alert.get("properties", {})
    raw_desc = properties.get('description') or ''
    awips_id = properties['parameters'].get('AWIPSidentifier', ['ERROR'])[0]
    event_type = properties.get("event")
    clickable_alert_id = properties.get("@id")
    
    # SVR/SVS cancellation check (if wind and hail are both n/a, it's a cancellation)
    if awips_id.startswith("SV"):
        max_wind = properties['parameters'].get('maxWindGust', ["n/a"])[0]
        max_hail = properties['parameters'].get('maxHailSize', ["n/a"])[0]
        if max_wind == "n/a" and max_hail == "n/a":
            print(Fore.RED + f"Check failed, SVR/SVS expired or cancelled: {clickable_alert_id}" + Fore.RESET)
            return False
            
    # FFW/FFS cancellation check (if detection source is n/a, it's a cancellation)
    if awips_id.startswith("FF"):
        flood_detection = properties['parameters'].get('flashFloodDetection', ['n/a'])[0]
        if flood_detection == "n/a":
            print(Fore.RED + f"Check failed, FFW expired or cancelled: {clickable_alert_id}" + Fore.RESET)
            return False
    
    #any other case, if desc text has something along the line of "will allow the Frost Advisory to expire" or "Flood watch will be allowed to expire"
    if event_type not in ['Severe Thunderstorm Warning', 'Flash Flood Warning'] and raw_desc is not None and len(raw_desc) > 2:
        description_text = ' '.join(raw_desc.split()).lower()
        expired_pattern = r"(?i)\b(?:allow(?:ed|s)?(?: the [a-z ]+?)?|the [a-z ]+?(?: will(?: be)?(?: allowed to)?)?|the threat(?: for [a-z ]+?)?)\s+(?:expire(?: at \d{1,2}(?::\d{2})?\s?(?:am|pm))?|has ended)\b"        
        expired_match = re.search(expired_pattern, description_text)
        if expired_match:
            print(Fore.RED + f'Check failed, {event_type} expired (Regex fail)! {clickable_alert_id}' + Fore.RESET)
            return False
        elif properties.get('urgency') == 'Past': #not sure how many of these come through, but def don't want to post them
            print(Fore.RED + f'Check failed, {event_type} expired (urgency = Past)! {clickable_alert_id}' + Fore.RESET)
            return False
    
    # If none of the cancellation conditions are met, the alert is valid.
    return True

check_time = 60 #seconds of downtime between scans

def main():
    """
    Main loop to fetch, process, and post weather alerts.
    This version uses a more robust, multi-stage logic to handle watch delays correctly.
    """
    global posted_alerts
    posted_alerts = load_posted_alerts(config.LOG_FILE)
    slideshow_queue = None
    if config.SEND_TO_SLIDESHOW:
        slideshow_queue = queue.Queue()
        from integrations.slideshow import run_slideshow
        slideshow_thread = threading.Thread(
            target=run_slideshow, args=(slideshow_queue,), daemon=True
        )
        slideshow_thread.start()
        print(Fore.MAGENTA + "Slideshow thread started." + Fore.RESET)

    while True:
        warning_types = config.ALERT_TYPES_TO_MONITOR
        #print(Fore.LIGHTCYAN_EX + 'Start scan for alerts' + Fore.RESET)
        
        # --- Stage 1: Prepare lists for the current scan cycle ---
        alerts_ready_to_process = []
        watches_for_next_cycle = []
        newly_delayed_watches = []

        # --- Stage 2: Evaluate watches delayed from the PREVIOUS cycle ---
        current_time = time.time()
        for add_time, watch_alert in delayed_watches:
            alert_id = watch_alert['properties']['id']

            # If a watch was already posted (e.g., via timeout), discard it.
            if alert_id in posted_alerts:
                queued_watch_ids.discard(alert_id)
                continue

            watch_desc = watch_alert['properties'].get('description', '').lower()
            watch_id_num = get_watch_number(watch_desc)
            
            has_attribs = False
            if watch_id_num:
                has_attribs, _, _ = get_watch_attributes(watch_id_num)

            # Promote the watch if it's ready OR has timed out
            if has_attribs or (current_time - add_time >= WATCH_DELAY_TIME):
                print(Fore.GREEN + f'Promoting watch {alert_id} from delay queue to be processed.' + Fore.RESET)
                alerts_ready_to_process.append(watch_alert)
            else:
                # Otherwise, keep it in the delay queue for the next cycle
                watches_for_next_cycle.append((add_time, watch_alert))
        
        # --- Stage 3: Fetch and triage NEW alerts from the API ---
        alerts_stack = []
        if IS_TESTING:
            print(Back.YELLOW + Fore.BLACK + "--- RUNNING IN TEST MODE ---" + Back.RESET)
            with open('test_alerts/spstesttext.json', 'r') as f:
                alerts_stack = [json.load(f)]
        else:
            alerts_stack = get_nws_alerts(warning_types)

        for alert in alerts_stack:
            alert_id = alert['properties']['id']
            event_type = alert['properties']['event']

            # Skip any alert that has already been posted or is already waiting in our queue
            if alert_id in posted_alerts or alert_id in queued_watch_ids:
                continue

            # If it's a NEW watch, add it to a temporary "newly delayed" list
            if event_type in ['Tornado Watch', 'Severe Thunderstorm Watch']:
                print(f'New watch detected ({alert_id}). Adding to delay queue for next cycle.')
                newly_delayed_watches.append((time.time(), alert))
                queued_watch_ids.add(alert_id)
            else:
                # If it's any other type of new, valid alert, add it to be processed now
                alerts_ready_to_process.append(alert)

        # --- Stage 4: Update the master delay list for the NEXT cycle ---
        delayed_watches[:] = watches_for_next_cycle + newly_delayed_watches

        # --- Stage 5: Process all alerts that are ready for this cycle ---
        for alert in alerts_ready_to_process:
            properties = alert.get("properties", {})
            alert_id = properties.get("id")

            # Final safeguard check
            if alert_id in posted_alerts:
                continue

            # Check for cancellations (SVR, FFW, etc.)
            if not check_if_alert_is_valid(alert):
                save_posted_alert(alert_id, config.LOG_FILE)
                posted_alerts.add(alert_id) # Mark cancelled alert as "handled"
                continue

            awips_id = properties['parameters'].get('AWIPSidentifier', ['ERROR'])[0]
            clickable_alert_id = properties.get("@id")
            expiry_time_iso = properties.get("expires")
            clean_alert_id = clean_filename(alert_id)
            
            # Check for upgrades or significant changes
            ref_check_passed, alert_verb = True, 'issued'
            references = properties.get('references')
            if references:
                try:
                    ref_url = references[-1]['@id']
                    if IS_TESTING: #testing for single local alert
                        with open (ref_url, 'r') as f:
                            ref_data = json.load(f)
                    else:
                        ref_response = requests.get(ref_url, headers={"User-Agent": "warnings_on_fb/kesse1ni@cmich.edu"})
                        ref_response.raise_for_status()
                        ref_data = ref_response.json()
                        
                    ref_check_passed, alert_verb = are_alerts_different(alert, ref_data)
                except Exception as e:
                    print(Fore.RED + f"Error processing reference for {clickable_alert_id}: {e}" + Fore.RESET)
            
            if ref_check_passed:
                print(Fore.LIGHTBLUE_EX + f"Processing graphics for {alert_verb} alert: {clickable_alert_id}" + Fore.RESET)
                alert_path = f'{config.OUTPUT_DIR}/alert_{awips_id}_{clean_alert_id}.png'
                properties = alert.get("properties", {})
                event_type = properties.get("event")
                try:
                    plot_mrms = True #default to plotting radar
                    no_mrms_list = ['Dense Fog Advisory', 'Freeze Warning', 'Frost Advisory', 'Red Flag Warning']

                    if event_type in no_mrms_list:
                        print(f'{event_type}, skipping mrms plotting')
                        plot_mrms = False
                    else: 
                        plot_mrms = True
                        
                    path, statement = plot_alert_polygon(alert, alert_path, plot_mrms, alert_verb)
                    if path and statement:  # Ensure plotting was successful
                        if config.SEND_TO_SLIDESHOW and expiry_time_iso:
                            slideshow_queue.put((path, expiry_time_iso))
                        if config.POST_TO_FACEBOOK:
                            post_to_facebook(statement, alert_path)
                        if config.POST_TO_DISCORD:
                            log_to_discord(statement, alert_path, config.WEBHOOKS)
                        if config.POST_TO_INSTAGRAM_GRID:
                            make_instagram_post(statement, alert_path, 'grid', ig_client)
                        if config.POST_TO_INSTAGRAM_STORY:
                            make_instagram_post(statement, alert_path, 'story', ig_client)
                        #add to both the local set() and the persistent set() for use across sessions
                        posted_alerts.add(alert_id)
                        save_posted_alert(alert_id, config.LOG_FILE)
                    else:
                        print(Back.YELLOW + f'Plotting failed for {alert_id}, will retry on next scan.' + Back.RESET)
                except Exception as e:
                    print(Back.RED + f'CRITICAL ERROR during plotting of {alert_id}: {e}' + Back.RESET)
            else: 
                print(Fore.YELLOW + f'Ref check failed, {clickable_alert_id} is a duplicate/downgrade. No plot.' + Fore.RESET)

        print(Fore.LIGHTCYAN_EX + f'End scan. {len(delayed_watches)} watches in queue. Rescan in {check_time}s' + Fore.RESET)
        time.sleep(check_time)

for folder in required_folders:
    print(f"checking for required folder: {folder}")
    os.makedirs(folder, exist_ok= True)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description= 'Insta-Alert CLI')
    available_configs = config_manager.get_available_configs()
    parser.add_argument(
        "--config",
        required=True,
        type=str,
        choices=available_configs, # This ensures only valid configs can be passed
        help=f"The name of the configuration to use. Available: {', '.join(available_configs)}"
    )
    
    args = parser.parse_args()
    config_manager.load(args.config)
    config = config_manager.config
    #import things down here that need a populated config file
    from polygonmaker import plot_alert_polygon
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    try:
        if config.POST_TO_INSTAGRAM_GRID or config.POST_TO_INSTAGRAM_STORY:
            ig_client = instagram_login(os.getenv("IG_USER"), os.getenv("IG_PASS"))
        main()
    except Exception as e:
        print(Back.RED + f"Fatal error: {e}" + Back.RESET)
        report_error(e, context="Top-level main()")
        raise  # optional — keeps the crash visible in logs
