import re
from colorama import Fore, Back
if __name__ == '__main__':
    from metar import build_kdtree, get_nearest_station, get_station_temp
else: 
    from .metar import build_kdtree, get_nearest_station, get_station_temp

def is_alert_winter(alert, centerlat, centerlon):
    """Evaluates if a given alert deals with winter weather.
    Primarily WSW, SQW, some SPS

    Args:
        alert (NWS Alert Object): Alert to evaluate
        centerlat (float): Middle of the alert polygon latitude
        centerlon (float): Middle of the alert polygon longitude

    Returns:
        boolean: if it deals with winter weather
    """
    alert_type = alert['properties'].get("event")
    #print(centerlat, centerlon)
 
    if alert_type in ['Snow Squall Warning', 'Winter Storm Warning', 'Lake Effect Snow Warning']:
        print(Fore.LIGHTBLUE_EX + 'Winter Product identified, using snow cmap' + Fore.RESET)
        return True
    elif alert_type == 'Special Weather Statement':
        description_text = alert['properties'].get('description', '').lower()
        station_temp = 0.0 #default to this bit of the check being true unless the station is close enough
        station, dist = get_nearest_station(tree, df, centerlat, centerlon)
        
        if dist < 35: #anything within 35km
            station_temp = get_station_temp(station)
           
            snow_pattern = r'\bsnow'  #regex to check for winter stuff goes here. need more
            snow_match = re.search(snow_pattern, description_text)
            if snow_match and station_temp < 5.0: #colder than 5c and theres snow match? winter it...
                print(Fore.LIGHTBLUE_EX + 'Winter SPS identified by regex and METAR, using snow cmap' + Fore.RESET)
                return True
            else:
                return False
        else:
            station_temp = 0.0 #defaulting again if the station is too far away
           
            snow_pattern = r'\bsnow'  #regex to check for winter stuff goes here. need more
            snow_match = re.search(snow_pattern, description_text)
            if snow_match:
                print(Fore.LIGHTBLUE_EX + 'Winter SPS identified by regex only, using snow cmap' + Fore.RESET)
                return True
            else:
                return False
     
    return False

#want this to run when script startup
tree, df = build_kdtree()

#station, dist = get_nearest_station(tree, df, 45.678, -110.67)

#(get_station_temp(station))