from shapely.geometry import shape
from colorama import Fore, Back
import requests
import time
from shapely import unary_union, buffer


zone_geometry_cache = {}
MAX_ZONES_IN_CACHE = 200

def get_alert_geometry(alert):
    """
    Determines the geometry for an alert. 
    If the alert has a direct (polygon) geometry, it uses that.
    If not, it fetches and combines geometries from the affected zones.
    """
    # Check for a direct polygon geometry first
    geometry_data = alert.get("geometry")
    if geometry_data:
        print("Processing polygon-based alert.")
        #print(shape(geometry_data))
        return shape(geometry_data), 'polygon'

    # If no direct geometry, process as a zone-based alert (e.g., a Watch)
    print("Processing zone-based alert (geometry is null).")
    affected_zones = alert['properties'].get('affectedZones', [])
    if not affected_zones:
        print(Fore.YELLOW + "Alert has no geometry and no affected zones." + Fore.RESET)
        return None, None
    
    alert_type = alert['properties'].get("event")
    '''
    if issuing_state == 'AK' and alert_type == 'Special Weather Statement':
        print('not plotting due to known errors with Alaska zone-based SPS.')
        return None, None
    '''
    geometries = []
    print(f"Fetching geometries for {len(affected_zones)} zones...")
    max_retries = 5
    for attempt in range(max_retries):
        for zone_url in affected_zones:
            if zone_url in zone_geometry_cache: # Check cache first to reduce API calls
                geometries.append(zone_geometry_cache[zone_url])
                continue
            
            try:
                # Fetch zone data from the NWS API
                response = requests.get(zone_url, headers={"User-Agent": "warnings_on_fb/kesse1ni@cmich.edu"}, timeout=10)
                response.raise_for_status()
                zone_geom_data = response.json().get('geometry')
                
                if zone_geom_data:
                    zone_shape = shape(zone_geom_data)
                    geometries.append(zone_shape)
                    if len(zone_geometry_cache) >= MAX_ZONES_IN_CACHE:
                        # remove a random item (simple approach) or the first item
                        zone_geometry_cache.pop(next(iter(zone_geometry_cache)))
                    zone_geometry_cache[zone_url] = zone_shape
            except requests.RequestException as e:
                print(Fore.RED + f"Failed to fetch geometry for zone {zone_url}: {e}. Attempt {attempt}, retrying." + Fore.RESET)
                if attempt + 1 >= max_retries:
                    print(Back.RED + f"All download attempts ({max_retries}) failed" + Back.RESET)
                    attempt += 1
                    continue
                else:
                    time.sleep(2)
    if not geometries:
        print(Fore.RED + "Could not retrieve any geometries for the affected zones." + Fore.RESET)
        return None

    # Combine all individual zone polygons into one single shape
    combined_geometry = unary_union(geometries)
    clean_geometry = buffer(combined_geometry, 0.001) #should remove tiny/weird overlaps.
    print("Successfully combined zone geometries.")
    return clean_geometry, 'zone'