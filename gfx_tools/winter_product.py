import re
from colorama import Fore, Back

def is_alert_winter(alert):
    """Evaluates if a given alert deals with winter weather.
    Primarily WSW, SQW, some SPS

    Args:
        alert (NWS Alert Object): Alert to evaluate

    Returns:
        boolean: if it deals with winter weather
    """
    alert_type = alert['properties'].get("event")
 
    if alert_type in ['Snow Squall Warning', 'Winter Storm Warning']:
        return True
    elif alert_type == 'Special Weather Statement':
        description_text = alert['properties'].get('description', '').lower()
        #regex to check for winter stuff goes here
        snow_pattern = r'\bSnow'
        snow_match = re.search(snow_pattern, description_text)
        if snow_match:
            return True
        else:
            return False
        
    return False
