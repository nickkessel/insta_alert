#Use this to test things in real scenario with no local alerts - should work for anywhere in the country - will be SLOW - no posting to fb function
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
from colorama import Fore, Back, Style
import re

#TODO: these are roughly (ish) in order of do first/last. simpler stuff is kinda to the top
#DONE different color warnings tor = red, svr = yellow, flashflood = green, tor-r = wideborder red, pds-tor = magenta, svr-destructive/considerable = wideborder yellow
#DONE add to header text expiration time for warning
#DONE make bigger cities have bigger labels. could probably do a few "bins" e.g. >40000 biggest font, 10000-40000 medium font, <10000 small font? trial and error, should not be too hard.
#DONEchange city label font; thinking monospace all-caps for legibility. 
#DONE change city markers; thinking "plus" signs? 
#DONE make county borders thinner, help with legibility
#DONE fix it so that it only tries to plot cities in the map region, not plot everything in the dataset then only show a small subset
# check through list of params (hailsize, windspeed, torDetection, etc) and for the ones that are present, draw in box on map in corner of view
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
#figure out why adding warning to the posted_alerts[] list still plots again 
#optimisations!! once everything is working, make it fast. cache as much as possible, especially the city names csv, only have my region cities


NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"


# Store already posted alerts to prevent duplicates
posted_alerts = set()
start_time = time.time()

df_large = pd.read_csv('filtered_cities_all.csv')
logo_path= 'cincyweathernobg.png'
logo = mpimg.imread(logo_path)

roads = gpd.read_file("ne_10m_roads/ne_10m_roads.shp")

interstates_all = roads[roads['level'] == 'Interstate']
federal_roads_all = roads[roads['level'] == 'Federal']

#secondary_roads = regional_roads[regional_roads['name'].str.contains(r'\b(?:50|32|22|42|747|127|27|73)\b', na= False)]
#interstates_all.to_csv('interstates_all.csv')

def get_nws_alerts():
    try:
        response = requests.get(NWS_ALERTS_URL, headers={"User-Agent": "weather-alert-bot - kesse1ni@cmich.edu"})
        response.raise_for_status()
        alerts = response.json().get("features", [])
        print(f"Fetched {len(alerts)} total alerts from NWS")

        filtered_alerts = []
        for alert in alerts:
            properties = alert["properties"]
            event_type = properties.get("event")
            affected_zones = properties.get("geocode", {}).get("UGC", [])

            if event_type in ["Tornado Warning", "Severe Thunderstorm Warning", "Flash Flood Warning"]: #ffws excluded from testing just bc there were so many so it goes faster
                print(f"Matching alert found: {event_type}, Zones: {affected_zones}")
                filtered_alerts.append(alert)

        print(f"Returning {len(filtered_alerts)} filtered alerts")
        return filtered_alerts
    except requests.RequestException as e:
        print(f"Error fetching NWS alerts: {e}")
        return []
    
def plot_alert_polygon(alert, output_path):
    plot_start_time = time.time()
    geometry = alert.get("geometry")
    
    if not geometry:
        print("No geometry found for alert.")
        return None

    try:
        geom = shape(geometry)
        #print(geom)
        alert_type = alert['properties'].get("event") #tor, svr, ffw, etc
        expiry_time = alert['properties'].get("expires") #raw eastern time thing need to format to time
        issued_time = alert['properties'].get("sent")
        issuing_office = alert['properties'].get("senderName")
        dt = datetime.fromisoformat(expiry_time)
        eastern = pytz.timezone("US/Eastern")
        dt_eastern = dt.astimezone(eastern)
        formatted_expiry_time = dt_eastern.strftime("%B %d, %I:%M %p %Z")
        
        dt1 = datetime.fromisoformat(issued_time)
        dt1_eastern = dt1.astimezone(eastern)
        formatted_issued_time = dt1_eastern.strftime("%I:%M %p %Z")
        print(alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )

        fig, ax = plt.subplots(figsize=(9, 6), subplot_kw={'projection': ccrs.PlateCarree()})
        ax.set_title(f"{alert_type.upper()}\nexpires {formatted_expiry_time}", fontsize=14, fontweight='bold', loc='left')
        ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth = 1.5)
        ax.add_feature(USCOUNTIES.with_scale('5m'), linewidth = 0.5, edgecolor = "#9e9e9e")
        interstates_all.plot(ax=ax, linewidth = 1, edgecolor='blue', transform = ccrs.PlateCarree())
        federal_roads_all.plot(ax=ax, linewidth= 0.5, edgecolor= 'red', transform = ccrs.PlateCarree())
        
        if alert_type == "Severe Thunderstorm Warning":
            fig.set_facecolor('yellow')
        elif alert_type == 'Tornado Warning':
            fig.set_facecolor('red') 
        elif alert_type == 'Flash Flood Warning':
            fig.set_facecolor('green')
        else:
            fig.set_facecolor("#b7b7b7")
                   
        # Fit view to geometry
        minx, miny, maxx, maxy = geom.bounds
        width = maxx - minx
        height = maxy - miny
        target_aspect = 3/2
        
        current_aspect = width / height
        
        if current_aspect > target_aspect:
            #too wide, pad height
            new_height = width / target_aspect
            padding = (new_height - height) / 2
            miny -= padding
            maxy += padding
        else:
            #too tall pad height
            new_width = height * target_aspect
            padding = (new_width - width) /2
            minx -= padding
            maxx += padding
            
        #optional extra padding (like zooming out)
        padding_factor = 0.3 #0.2-0.4 is alright
        pad_x = (maxx - minx) *padding_factor
        pad_y = (maxy - miny) * padding_factor
        
        minx -= pad_x
        maxx += pad_x
        miny -= pad_y
        maxy += pad_y
        #scale = 0.2 #more is more zoomed out, less is more zoomed in #0.2-0.3 is probably ideal
        map_region = [minx, maxx, miny, maxy]
        #print(map_region)
        ax.set_extent(map_region)
        clip_box = ax.get_window_extent() #for the text on screen

        #filter for only cities in map view
        visible_cities_df = df_large[
            (df_large['lng'] >= minx) & (df_large['lng'] <= maxx) &
            (df_large['lat'] >= miny) & (df_large['lat'] <= maxy)
        ].copy()
        
        #print(f'total cities available: {len(df_large)}')
        print(f'cities in view: {len(visible_cities_df)}')

        #plot cities
        fig.canvas.draw()
        text_candidates = []
        plotted_points = []
        min_distance_deg = 0.04 #0.065 is good for 0.2-0.3 scale
        for _, city in visible_cities_df.iterrows():
            city_x = city['lng']
            city_y = city['lat']
            city_pop = city['population']
            
            #skip if too close to already plotted city
            too_close = any(hypot(city_x - px, city_y - py) < min_distance_deg for px, py in plotted_points)
            if too_close:
                continue
            #actually plot city
            
            scatter = ax.scatter(city_x, city_y, transform = ccrs.PlateCarree(), color='black', s = 1.5, marker = ".")
            if city_pop > 60000:
                name = city['city_ascii'].upper()
                fontsize = 12
                weight = 'book'
                color = "#222222"
                bgcolor = '#ffffff00'
            elif city_pop > 10000:
                name = city['city_ascii']
                fontsize = 10
                weight = 'light'
                color = "#313131"
                bgcolor = "#ffffff00"
            else:
                name = city['city_ascii']
                fontsize = 8
                weight = 'light'
                color = "#313131"
                bgcolor = '#ffffff00'

            text_artist = ax.text(
                city_x, city_y, name,
                fontfamily='monospace', fontsize=fontsize, weight=weight,
                fontstretch='ultra-condensed', ha='center', va='bottom',
                c=color, transform=ccrs.PlateCarree(), clip_on=True,
                backgroundcolor=bgcolor
            )
            text_artist.set_clip_box(clip_box)
            text_artist.set_path_effects([PathEffects.withStroke(linewidth=3, foreground='white'), PathEffects.Normal()])
            text_candidates.append((text_artist, scatter, city_x, city_y, city['city_ascii'], city_pop))
            plotted_points.append((city_x, city_y))
        
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        
        accepted_bboxes = []
        final_texts = []
        
        for text_artist, scatter, x, y, city_name, city_pop1 in text_candidates:
            bbox = text_artist.get_window_extent(renderer=renderer)
            
            if any(bbox.overlaps(existing) for existing in accepted_bboxes):
                text_artist.remove()
                scatter.remove()
                #print(f'removed {city_name}, population: {city_pop1}')
            else:
                accepted_bboxes.append(bbox)
                final_texts.append(text_artist)
                #print(f'plotted {city_name}, population: {city_pop1}')

        ax.text(0.01, 0.95, f"Issued {formatted_issued_time} by {issuing_office}", 
                transform=ax.transAxes, ha='left', va='bottom', 
                fontsize=10, backgroundcolor="#eeeeeecc") #plotting this down here so it goes on top of city names

        # Draw the polygon
        if geom.geom_type == 'Polygon':
            if alert_type == "Severe Thunderstorm Warning":
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=2, transform=ccrs.PlateCarree())
                ax.fill(x, y, facecolor='#ffff0050')
            elif alert_type == 'Tornado Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree())
                ax.fill(x, y, facecolor="#ff000050")
            elif alert_type == 'Flash Flood Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='green', linewidth=2, transform=ccrs.PlateCarree())
                ax.fill(x, y, facecolor = "#00ff2f50")
            else:
                x, y = geom.exterior.xy
                ax.plot(x, y, color="#414141", linewidth=2, transform=ccrs.PlateCarree())
                ax.fill(x, y, facecolor = "#8e8e8e49")  
                  
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree())
        
        #box to show info about hazards like hail/wind if applicable
        maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
        maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
        torDetection = alert['properties']['parameters'].get('tornadoDetection', ['n/a'])[0] #string, possible for svr; radar-indicated, radar-confirmed, need to see others for tor warning
        floodSeverity = alert['properties']['parameters'].get('flashFloodDamageThreat', ['n/a'])[0] #string, default level (unsure what this returns), considerable, catastophic
        tStormSeverity = alert['properties']['parameters'].get('thunderstormDamageThreat', ['n/a'])[0] 
        torSeverity = alert['properties']['parameters'].get('tornadoDamageThreat', ['n/a'])[0] #considerable for pds, not sure for tor-e. 
        floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
        
        
        hazard_details = [
            (maxWind, 'Max. Wind Gusts', ""),
            (maxHail, 'Max. Hail Size', "in"),
            (torDetection, 'Tornado', ""),
            (floodSeverity, 'Flood Threat', ""),
            (tStormSeverity, 'Severe Threat', ""),
            (torSeverity, 'Tornado Threat', ""),
            (floodDetection, 'Source', "")
        ]
        details_text_lines = []
        for value, label, suffix in hazard_details:
            if value != "n/a":
                val_str = str(value).replace(" ", r"\ ") + suffix
                details_text_lines.append(f"{label}: $\\bf{{{val_str}}}$")

        details_text = "\n".join(details_text_lines)
        info_box = AnchoredText(details_text, loc=3, prop={'size': 12}, frameon=True)
        ax.add_artist(info_box)
        
        if tStormSeverity == 'DESTRUCTIVE': #need to check this is what pds/tor-e have as their tags
            pdsBox = ax.text(0.5, 0.85, "This is a DESTRUCTIVE THUNDERSTORM!! \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#ffffff',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        elif torSeverity == 'CONSIDERABLE':
            pdsBox = ax.text(0.5, 0.85, "This is a PATICULARLY DANGEROUS SITUATION!! \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#ffffff',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        elif torSeverity == 'CATASTROPHIC':
            pdsBox = ax.text(0.5, 0.85, "This is a TORNADO EMERGENCY!! \n A large and extremely dangerous tornado is ongoing \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#ffffff',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        elif floodSeverity == 'CATASTROPHIC':
            pdsBox = ax.text(0.5, 0.85, "This is a FLASH FLOOD EMERGENCY!! \n Get to higher ground NOW!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#ffffff',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        
        
        #add watermark
        imagebox = OffsetImage(logo, zoom = 0.09, alpha = 0.75)
        ab = AnnotationBbox(
            imagebox,
            xy=(0.98, 0.02),
            xycoords= 'axes fraction',
            frameon=False,
            box_alignment=(1,0)
        )
        ax.add_artist(ab)
        
        # Save the image
        
        ax.set_aspect('equal')  # or 'equal' if you want uniform scaling
        plt.savefig(output_path, bbox_inches='tight', dpi= 200)
        plt.close()
        
        area_desc = alert['properties'].get('areaDesc', ['n/a']) #area impacted
        desc = alert['properties'].get('description', ['n/a']) #long text
        statement = (alert_type + " including " + area_desc + " until " 
                     + formatted_expiry_time + "!!\n" + desc + '\n#cincywx #cincinnati #weather #ohwx #ohiowx #cincy #cincinnatiwx')
        
        elapsed_plot_time = time.time() - plot_start_time
        elapsed_total_time = time.time() - start_time
        print(Fore.LIGHTGREEN_EX + f"Map saved to {output_path} in {elapsed_plot_time:.2f}s. Total script time: {elapsed_total_time:.2f}s")
        #print(statement)
        return output_path, statement
    except Exception as e:
        print(Fore.RED + f"Error plotting alert geometry: {e}")
        return None
    
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
            print(references)
            
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
                print(new_geom)
                print(ref_geom)
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
                plot_alert_polygon(alert, f'big_domain_test/alert_{awips_id}_{clean_alert_id}.png')
                #post_to_facebook(message)
                posted_alerts.add(alert_id)
            elif alert_id in posted_alerts:
                message = (
                    f"Alert already handled: {clickable_alert_id}"
                )
                print(Fore.LIGHTBLUE_EX + message)
        print(Fore.LIGHTCYAN_EX + f'End scan for alerts - all gfx generated or previously handled. Rescan in {check_time}s')
        time.sleep(check_time)  # Check every x seconds
        
main()
