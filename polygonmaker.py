#using this as like a test thing
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from shapely.geometry import shape, Point
import pandas as pd
from datetime import datetime
import pytz
from math import hypot
from matplotlib.offsetbox import AnchoredText, OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import geopandas as gpd
import time
from shapely import unary_union, buffer
from colorama import Back, Fore, Style
from plot_mrms2 import get_mrms_data_async
import re
import requests
from timezonefinderL import TimezoneFinder
import gc
import json
import config
from bs4 import BeautifulSoup


#DONE: set color "library" of sorts for the colors associated with each warning type, to unify between the gfx bg and the polygons
#DONE: figure out way to seperate the colorbar from the imagery in the plot stack, so the colorbar plots on top of
    #everything, but the imagery still plots towards the bottom. 
#TODO: wider polygon borders for more intense (destructive/tor-e) warnings
#DONE: consider shrinking hazards box when theres more than x (3?4?) things in there
#DONE: adjust city name boldness for readability (done-ish)
#DONE: space out city names slightly more
#DONE: have a greater min_deg_distance when the lat/lon is bigger than a certain area, so that for big warnings
    #there aren't like big boxes with super dense city names with them
#DONE: figure out/fix highway/road plotting so that they are better, basically, but also continuous (e.g no random gaps in the highway)
#DONE: use regex to pull hazard params from SMW alert text so they show in hazardbox (done? need to test w/ hail)
#DONE: use ak_cities dataset for alaska alerts, and also filter it so it's just AK. 
#TODO: make sure that the little dots for city locations are actually in a good spot
#TODO: maybe: add some sort of filter or something to show cities w/ less population when its a super sparse area (like ND)
''' 
ZORDER STACK
0 - polygon fill
1 - radar imagery
2 - county/state borders
3 - roads
4 - polygon border
5 - city/town names
7 - UI elements (issued time, logo, colorbar, radar time, hazards box, pdsbox)
'''
VERSION_NUMBER = "0.6.6" #Major version (dk criteria for this) Minor version (pushes to stable branch) Feature version (each push to dev branch)
ALERT_COLORS = {
    "Severe Thunderstorm Warning": {
        "facecolor": "#ffff00", # yellow
        "edgecolor": "#efef00", # darker yellow for border
        "fillalpha": "50"
    },
    "Tornado Warning": {
        "facecolor": "#ff0000", # red
        "edgecolor": "#cc0000", # darker red
        "fillalpha": "50"
    },
    "Flash Flood Warning": {
        "facecolor": "#02de02", # green
        "edgecolor": "#00dc00", # darker green
        "fillalpha": "50"
    },
    "Special Weather Statement": {
        "facecolor": "#ff943d", # orange
        "edgecolor": "#e07b24", # darker orange
        "fillalpha": "50"
    },
    "Special Marine Warning": {
        "facecolor": "#00E4DD", # teal
        "edgecolor": "#00cdc6", # darker teal
        "fillalpha": "50"
    },
    "Dust Storm Warning": {
        "facecolor": "#FFE4C4",
        "edgecolor": "#968672",
        "fillalpha": "50"
    },
    'Flood Advisory': {
        'facecolor': '#00ff7f',
        'edgecolor': "#00d168",
        'fillalpha': '50'
    },
    'Severe Thunderstorm Watch': {
        'facecolor': "#DB7093", #pink because i hate nick
        'edgecolor': "#8f4a61",
        'fillalpha': '50'
    },
    'Tornado Watch': {
        'facecolor': "#FFFF00", #also yellow because i hate nick
        'edgecolor': "#b8b800",
        'fillalpha': '50'
    },
    'Flood Watch': {
        'facecolor': "#2E8B57",
        'edgecolor': "#168445",
        'fillalpha': '50'
    },
    'Flash Flood Watch': {
        'facecolor': "#2E8B57",
        'edgecolor': "#168445",
        'fillalpha': '50'
    },
    "default": {
        "facecolor": "#b7b7b7", # grey
        "edgecolor": "#414141", # dark grey
        "fillalpha": "50"
    }
}

start_time = time.time()
zone_geometry_cache = {}
MAX_ZONES_IN_CACHE = 200
tf = TimezoneFinder()

print(Fore.BLACK + Back.LIGHTWHITE_EX + 'Loading cities' + Back.RESET)
#cities w/pop >250
conus_cities_ds = pd.read_csv('gis/cities_100_lite.csv')
ak_cities_ds = pd.read_csv('gis/ak_cities.csv')

print(Back.LIGHTWHITE_EX + 'Cities loaded. Loading logo.' + Back.RESET)
logo_path= 'testlogo1.png'
logo = mpimg.imread(logo_path)

print(Back.LIGHTWHITE_EX + 'Logo loaded. Loading pre-processed 500k borders.' + Back.RESET)
# Load the two layers from the single, pre-processed gpkg file.
counties_gdf = gpd.read_file("gis/processed_borders_500k.gpkg", layer='counties')
states_gdf = gpd.read_file("gis/processed_borders_500k.gpkg", layer='states')

lakes = gpd.read_file("gis/lakes/ne_10m_lakes_north_america.shp")

print(Back.LIGHTWHITE_EX + 'Borders loaded. Loading roads.' + Back.RESET)
interstates = gpd.read_file("gis/processed_interstates_500k_5prec_10tol.fgb") #3  decimals on the coords
us_highways = gpd.read_file('gis/all_us_highways_10tol.fgb') #us highways for conus and state highways for ak/hi. dataset does not have us/state highways equivalents for PR...

print(Back.LIGHTWHITE_EX + 'All data loaded successfully.' + Back.RESET + Fore.RESET)
#interstates.to_csv('interstates_filtered.csv')


def get_alert_geometry(alert):
    """
    Determines the geometry for an alert. 
    If the alert has a direct geometry, it uses that.
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
            print(Fore.RED + f"Failed to fetch geometry for zone {zone_url}: {e}" + Fore.RESET)
            continue
    if not geometries:
        print(Fore.RED + "Could not retrieve any geometries for the affected zones." + Fore.RESET)
        return None

    # Combine all individual zone polygons into one single shape
    combined_geometry = unary_union(geometries)
    clean_geometry = buffer(combined_geometry, 0.001) #should remove tiny/weird overlaps.
    print("Successfully combined zone geometries.")
    return clean_geometry, 'zone'


def draw_alert_shape(ax, shp, colors):
    """Helper function to draw single or multi-polygons on the map."""
    polygons_to_draw = []
    if shp.geom_type == 'Polygon':
        polygons_to_draw = [shp]
    elif shp.geom_type == 'MultiPolygon':
        polygons_to_draw = shp.geoms

    for poly in polygons_to_draw:
        x, y = poly.exterior.xy
        # Plot fill and borders
        ax.fill(x, y, facecolor=colors['facecolor'] + colors['fillalpha'], zorder=0)
        ax.plot(x, y, color='#000000', linewidth=4, transform=ccrs.PlateCarree(), zorder=4)
        ax.plot(x, y, color=colors['edgecolor'], linewidth=2, transform=ccrs.PlateCarree(), zorder=4)

blank_watch_url = 'https://www.spc.noaa.gov/products/watch/ww' #+ XXXX.html
def get_watch_attributes(id):
    id = str(id).zfill(4) #pads the left side w/ 0s until its 4 wide (proper format for the spc website)
    target_watch_url = f'{blank_watch_url}{id}.html'
    print(target_watch_url)
    
    try:
        response = requests.get(target_watch_url)
        html_content = response.content
        soup = BeautifulSoup(html_content, 'lxml') #want to get the first 6 things with class="wblack"
        attribs = soup.find_all(class_='wblack')
        attribs = attribs[:6] #first 6, gets repeitive after that for the like different views
        watch_attribs = [tag.text for tag in attribs] #get only the text content
        percents = [tag['title'].replace('% probability', '\%') for tag in attribs] 
        print(watch_attribs, percents)
        return watch_attribs, percents
    except Exception as e:
        print(f'error getting watch attributes: [{e}]')
        return ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']



def plot_alert_polygon(alert, output_path, mrms_plot, alert_verb):
    plot_start_time = time.time()
    geom, geom_type = get_alert_geometry(alert) #returns geometry shape and if it is polygon or zone/county
    issuing_state = alert['properties'].get("senderName")[-2:] #last 2 of it
    if issuing_state == 'AK':
        cities_ds = ak_cities_ds  #different pop cutoff to show more places on map 
    else: 
        cities_ds = conus_cities_ds 
    
    if not geom:
        print("No geometry found for alert.")
        return None, "Failed to generate graphic: No geometry found"

    try:
        #print(geom)
        alert_type = alert['properties'].get("event") #tor, svr, ffw, etc
        expiry_time = alert['properties'].get("expires") #raw time thing need to format to time
        issued_time = alert['properties'].get("sent")
        issuing_office = alert['properties'].get("senderName")
        
        #new time stuff
        try:
            centerlon, centerlat = geom.centroid.x, geom.centroid.y
            #print(centerlon, centerlat)
            timezone_str = tf.timezone_at(lng=centerlon, lat= centerlat)
            alert_tz = pytz.timezone(timezone_str)
            
            dt_sent = datetime.fromisoformat(issued_time).astimezone(alert_tz)
            dt_expires = datetime.fromisoformat(expiry_time).astimezone(alert_tz)
        
            formatted_issued_time = dt_sent.strftime("%I:%M %p %Z")
            formatted_expiry_time = dt_expires.strftime("%B %d, %I:%M %p %Z")
            print(alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
        except Exception as e:
            print(Back.YELLOW + f'error getting timezone: [{e}] defaulting to UTC' + Back.RESET)
        
            #time formatting (old)
            dt = datetime.fromisoformat(expiry_time)
            eastern = pytz.timezone("GMT")
            dt_eastern = dt.astimezone(eastern)
            formatted_expiry_time = dt_eastern.strftime("%B %d, %I:%M %p %Z")
            dt1 = datetime.fromisoformat(issued_time)
            dt1_eastern = dt1.astimezone(eastern)
            formatted_issued_time = dt1_eastern.strftime("%I:%M %p %Z")
            print(alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
        
        #plot setup
        minx, _, maxx, _ = geom.bounds #ignore the lat, as its not relevant here
        #print(minx, maxx)
        fig, ax = plt.subplots(figsize=(9, 6), subplot_kw={'projection': ccrs.PlateCarree()})
        colors = ALERT_COLORS.get(alert_type, ALERT_COLORS['default'])
        if alert_verb == 'upgraded':
            ax.set_title(fr"$\mathbf{{{alert_type.upper().replace(' ', r'\ ')}}}$" + " -" + fr" $\mathit{{{alert_verb.capitalize()}!}}$" + "\n" + f"expires {formatted_expiry_time}", fontsize=14, loc='left')  #latex/math formatting is also beyond me. ALSO the exclamation point wont be italicized because the default MPL font just straight up doesnt have a glyph for it and the workaround seems way worse than what its at now
        else:
            ax.set_title(fr"$\mathbf{{{alert_type.upper().replace(' ', r'\ ')}}}$" + "\n" + f"expires {formatted_expiry_time}", fontsize=14, loc='left')  #dont really need a verb if it is not upgraded i dont think
        counties_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='#9e9e9e', facecolor='none', linewidth=0.75, zorder=2) 
        states_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=1.5, zorder=2)
        #ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth = 1.5, zorder = 2)
        #ax.add_feature(USCOUNTIES.with_scale('5m'), linewidth = 0.5, edgecolor = "#9e9e9e", zorder = 2)
        us_highways.plot(ax=ax, linewidth= 0.5, edgecolor= 'red', transform = ccrs.PlateCarree(), zorder = 4)
        interstates.plot(ax=ax, linewidth = 1, edgecolor='blue', transform = ccrs.PlateCarree(), zorder = 4)
        lakes.plot(ax=ax, linewidth = 2, edgecolor='blue', facecolor="#7685d7", transform = ccrs.PlateCarree(), zorder = 2)
        
        #simplified
        colors = ALERT_COLORS.get(alert_type, ALERT_COLORS['default'])
        fig.set_facecolor(colors['facecolor'])
                   
        # Fit view to geometry
         # Fit view to geometry's initial bounds
        minx, miny, maxx, maxy = geom.bounds
        
        # Add initial padding
        padding_factor = 0.3
        width = maxx - minx
        height = maxy - miny
        pad_x = width * padding_factor
        pad_y = height * padding_factor
        
        minx -= pad_x
        maxx += pad_x
        miny -= pad_y
        maxy += pad_y

        # Clamp padded extent to valid lat/lon ranges
        clamped_minx = max(minx, -180.0)
        clamped_maxx = min(maxx, 180.0)
        clamped_miny = max(miny, -90.0)
        clamped_maxy = min(maxy, 90.0)

        # Recalculate dimensions after clamping
        width = clamped_maxx - clamped_minx
        height = clamped_maxy - clamped_miny
        
        # Enforce the target aspect ratio (3:2) on the clamped box
        target_aspect = 3.0 / 2.0
        current_aspect = width / height

        if current_aspect > target_aspect:
            # Box is too wide, it needs to be taller
            new_height = width / target_aspect
            delta_y = (new_height - height) / 2
            clamped_miny -= delta_y
            clamped_maxy += delta_y
        else:
            # Box is too tall, it needs to be wider
            new_width = height * target_aspect
            delta_x = (new_width - width) / 2
            clamped_minx -= delta_x
            clamped_maxx += delta_x

        # Final check to ensure the aspect ratio adjustment didn't push us back out of bounds
        final_minx = max(clamped_minx, -180.0)
        final_maxx = min(clamped_maxx, 180.0)
        final_miny = max(clamped_miny, -90.0)
        final_maxy = min(clamped_maxy, 90.0)
        
        map_region = [final_minx, final_maxx, final_miny, final_maxy]
        #print(map_region)
        #print(map_region)
        map_region2 = { # For the MRMS stuff, pad it a little bit to not have blank space at the edges
            "lon_min": final_minx - 0.01,
            "lon_max": final_maxx + 0.01,
            "lat_min": final_miny - 0.01,
            "lat_max": final_maxy + 0.01
        }
        
        ax.set_extent(map_region, crs=ccrs.PlateCarree())

        clip_box = ax.get_window_extent() #for the text on screen
        #NEW: plotting MRMS data here
        #check for region
        office_awips = alert['properties']['parameters'].get("AWIPSidentifier")[0]
        office_awips = office_awips[3:]
        if office_awips == 'SJU':
            region = 'PR'
        elif office_awips == 'AFC' or office_awips == 'AJK' or office_awips == 'AFG' or office_awips == 'ALU' or office_awips == 'NSB' or office_awips == 'AER':
            region = 'AK'
        elif office_awips == 'HFO':
            region = 'HI'
        elif office_awips == 'GUM' or issuing_office == 'NWS Tiyan GU':
            region = 'GU'
        else:
            region = 'US'
            
        if mrms_plot == True:
            subset, cmap, vmin, vmax, cbar_label, radar_valid_time = get_mrms_data_async(map_region2, alert_type, region)
            #directly plot the MRMS data onto the main axes (and colorbar, seperately)
            if subset is not None:
                im = ax.pcolormesh(
                    subset.longitude, subset.latitude, subset.unknown,
                    transform=ccrs.PlateCarree(),
                    cmap=cmap, vmin=vmin, vmax=vmax, zorder=1
                )
                '''this plots the colorbar off to the side (dont want)
                cbar = fig.colorbar(im, ax=ax, orientation='vertical', shrink=0.75, aspect=20, pad=0.02)
                cbar.set_label(cbar_label, color="#7a7a7a", fontsize=10, weight='bold')
                cbar.ax.tick_params(labelsize=8)
                '''
                # The list is [left, bottom, width, height] as fractions of the main plot area.
                cax = ax.inset_axes([0.885, 0.17, 0.027, 0.75])
                cax.set_facecolor("#00000034")
                
                cbar = fig.colorbar(im, cax=cax, orientation = 'vertical')
                cbar.set_label(cbar_label, color="#000000", fontsize=10, weight='bold')
                label_text = cbar.ax.yaxis.get_label()
                label_text.set_path_effects([PathEffects.withStroke(linewidth=1, foreground = 'white')])

                cbar.ax.tick_params(labelsize=8, color= 'white', labelcolor = 'white')
                
                for label in cbar.ax.get_yticklabels():
                    label.set_path_effects([PathEffects.withStroke(linewidth=1, foreground = 'black')])
                    label.set_fontweight('heavy')
                
                ax.text(0.01, 0.93, f"Radar data valid {radar_valid_time}", #radar time
                    transform=ax.transAxes, ha='left', va='top', 
                    fontsize=7, backgroundcolor="#eeeeeecc", zorder = 7)
                
            else:
                print("skipping plotting radar, no data returned from get_mrms_data")
        else:
            print('not plotting MRMS')
        
        #filter for only cities in map view
        visible_cities_df = cities_ds[
            (cities_ds['lng'] >= final_minx) & (cities_ds['lng'] <= final_maxx) &
            (cities_ds['lat'] >= final_miny) & (cities_ds['lat'] <= final_maxy)
        ].copy()
        
        #print(f'total cities available: {len(df_large)}')
        print(f'cities in view: {len(visible_cities_df)}')

        #plot cities
        fig.canvas.draw()
        text_candidates = []
        plotted_points = []
        impacted_cities = [] #to include in the caption
        alert_height = final_maxy - final_miny #how big is the box? 'normal' alert heights: seems like up to .9-1?(degree) Anything bigger than that gets a little cluttered
        print(f'alert height: {alert_height} degs') 

        min_distance_deg = alert_height/9 #8 or 9 or 10 seems to work well. lower if the map seems too cluttered
        for _, city in visible_cities_df.iterrows():
            city_x = city['lng']
            city_y = city['lat']
            city_pop = city['population']
            city_state = city['state_id']
            
            #skip if too close to already plotted city
            too_close = any(hypot(city_x - px, city_y - py) < min_distance_deg for px, py in plotted_points)
            if too_close:
                continue
            
            #now, actually plot city
            scatter = ax.scatter(city_x, city_y, transform = ccrs.PlateCarree(), color='black', s = 1.5, marker = ".", zorder = 5) #city marker icons
            if city_pop > 60000:
                name = city['city_ascii'] #.upper()
                fontsize = 12
                weight = 'semibold'
                color = "#101010"
                bgcolor = '#ffffff00'
            elif city_pop > 10000:
                name = city['city_ascii']
                fontsize = 11
                weight = 'normal'
                color = "#101010"
                bgcolor = "#ffffff00"
            elif city_pop > 1000:
                name = city['city_ascii']
                fontsize = 9
                weight = 'normal'
                color = "#101010"
                bgcolor = '#ffffff00'
            else:
                name = city['city_ascii']
                fontsize = 7
                weight = 'normal'
                color = "#232323"
                bgcolor = '#ffffff00'

            text_artist = ax.text(
                city_x, city_y, name,
                fontfamily='sans-serif', fontsize=fontsize, weight=weight,
                fontstretch='ultra-condensed', ha='center', va='bottom',
                c=color, transform=ccrs.PlateCarree(), clip_on=True,
                backgroundcolor=bgcolor, zorder = 5
            )
            text_artist.set_clip_box(clip_box)
            text_artist.set_path_effects([PathEffects.withStroke(linewidth=1.5, foreground='white'), PathEffects.Normal()])
            text_candidates.append((text_artist, scatter, city_x, city_y, city['city_ascii'], city_state, city_pop))
            plotted_points.append((city_x, city_y))
        
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        
        accepted_bboxes = []
        final_texts = []
        
        for text_artist, scatter, x, y, city_name, city_state, city_pop1 in text_candidates:
            bbox = text_artist.get_window_extent(renderer=renderer)
            
            if any(bbox.overlaps(existing) for existing in accepted_bboxes):
                text_artist.remove()
                scatter.remove()
                #print(f'removed {city_name}, population: {city_pop1}')
            else:
                accepted_bboxes.append(bbox)
                final_texts.append(text_artist)
                city_point = Point(x, y)
                if geom.contains(city_point):
                    impacted_cities.append(f'{city_name}, {city_state}')
                #print(f'plotted {city_name}, population: {city_pop1}')
                
        fig.text(0.90, 0.96, f'v.{VERSION_NUMBER}', ha='right', va='top', 
                 fontsize = 6, color="#000000", backgroundcolor="#96969636")
        fig.text(0.90, 0.92, f'Generated: {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ', ha='right', va='top', #time.strftime("%Y-%m-%d %H:%M:%S")
                 fontsize=6, color='#000000', backgroundcolor='#96969636')
        ax.text(0.01, 0.985, f"{alert_verb.capitalize()} {formatted_issued_time} by {issuing_office}", 
                transform=ax.transAxes, ha='left', va='top', 
                fontsize=9, backgroundcolor="#eeeeeecc", zorder = 7) #plotting this down here so it goes on top of city names

        # Draw the polygon
        draw_alert_shape(ax, geom, colors)
        #box to show info about hazards like hail/wind if applicable

        maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
        maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
        windObserved = alert['properties']['parameters'].get('windThreat', ["n/a"])[0]
        hailObserved = alert['properties']['parameters'].get('hailThreat', ["n/a"])[0]
        torDetection = alert['properties']['parameters'].get('tornadoDetection', ['n/a'])[0] #string, possible for svr; radar-indicated, radar-confirmed, need to see others for tor warning
        floodSeverity = alert['properties']['parameters'].get('flashFloodDamageThreat', ['n/a'])[0] #string, default level (unsure what this returns), considerable, catastophic
        tStormSeverity = alert['properties']['parameters'].get('thunderstormDamageThreat', ['n/a'])[0] 
        torSeverity = alert['properties']['parameters'].get('tornadoDamageThreat', ['n/a'])[0] #considerable for pds, catastrophic for tor e
        floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
        snowSquallDetection = alert['properties']['parameters'].get('snowSquallDetection', ['n/a'])[0] #"RADAR INDICATED" or "OBSERVED"
        snowSquallImpact = alert['properties']['parameters'].get('snowSquallImpact', ['n/a'])[0] # "SIGNIFICANT" or nothing
        waterspoutDetection = alert['properties']['parameters'].get('waterspoutDetection', ['n/a'])[0] #"OBSERVED" or "POSSIBLE"
        #sps stuff
        fireWeatherThreat = 'n/a'
        denseFogThreat = 'n/a'
        iceThreat = 'n/a'
        additionalHazard = 'n/a' 
        #watch stuff (add the word and percentage)
        torProb = 'n/a'
        sigTorProb = 'n/a'
        windProb = 'n/a'
        sigWindProb = 'n/a'
        hailProb = 'n/a'
        sigHailProb = 'n/a'
        
        watch_attribs, watch_percents = ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']  #default to these
        if alert_type == 'Severe Thunderstorm Watch' or alert_type == 'Tornado Watch':
            description_text = alert['properties'].get('description', '').lower()
            watch_id_match = re.search(r'\b\d{1,4}\b', description_text) #get the first instance of any 1 to 4 digit number in the watch desc (the watch number)
            if watch_id_match:
                watch_id = watch_id_match.group(0)
                watch_attribs, watch_percents = get_watch_attributes(watch_id)
                torProb = watch_attribs[0] + ' - ' + watch_percents[0]
                sigTorProb = watch_attribs[1] + ' - ' + watch_percents[1]
                windProb = watch_attribs[2] + ' - ' + watch_percents[2]
                sigWindProb = watch_attribs[3] + ' - ' + watch_percents[3]
                hailProb = watch_attribs[4] + ' - ' + watch_percents[4]
                sigHailProb = watch_attribs[5] + ' - ' + watch_percents[5]
            else:
                print('error getting watch id from watch text!')
                watch_attribs, watch_percents = ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']
        
        #handling SMWs because they don't have maxwind/maxhail in their parameters
        if alert_type == 'Special Marine Warning':
            description_text = alert['properties'].get('description','').lower()
            if maxWind == 'n/a':
                wind_match = re.search(r"wind gusts.*?(\d+)\s*knots", description_text) #regex is beyond me
                if wind_match:
                    maxWind = f"{wind_match.group(1)}kts"
            
            if maxHail == 'n/a':
                hail_match = re.search(r"hail.*?([\d.]+)\s*inch", description_text)
                if hail_match:
                    try:
                        #convert to float
                        maxHail = float(hail_match.group(1))
                    except ValueError:
                        print('could not parse hail size from description')
        
        #handle non-convective SPS                
        if alert_type == 'Special Weather Statement' and geom_type == 'zone':
            print('regexing SPS for more infos')
            description_text = alert['properties'].get('description', '').lower()
            headline_text = alert['properties']['parameters'].get('NWSheadline', [''])[0].lower()
            search_text = description_text + ' ' + headline_text

            # Define regex patterns, need to flesh these out some more
            fire_regex = r'\bfire\b|\bwildfire\b|red\s*flag'
            fog_regex = r'dense\s*fog|visibility\s*(?:one|a)\s*quarter\s*mile|zero\s*visibility|\bareas\s+of\s+fog\b'
            ice_regex = r'\bice\b|\bicy\b'
            blackice_regex =  r'black\s+ice'
            funnel_regex = r'funnel\s+cloud' #search sps for funnel clouds possible

            # Search for matches, ignoring case
            if re.search(fire_regex, search_text, re.IGNORECASE):
                fireWeatherThreat = "Elevated"
            if re.search(fog_regex, search_text, re.IGNORECASE):
                denseFogThreat = "Likely"
            if re.search(ice_regex, search_text, re.IGNORECASE):
                iceThreat = "Possible Across the Area"
            if re.search(blackice_regex, search_text, re.IGNORECASE):
                iceThreat = 'Black Ice Possible'
            if re.search(funnel_regex, search_text, re.IGNORECASE):
                additionalHazard = 'Funnel Clouds Possible'
             
        hazard_details = [
            (maxWind, 'Max. Wind Gusts', ""),
            (maxHail, 'Max. Hail Size', "in"),
            (floodSeverity, 'Damage Threat', ""),
            (tStormSeverity, 'Damage Threat', ""),
            (torSeverity, 'Damage Threat', ""),
            (snowSquallImpact, 'Impact', ""),
            (torDetection, 'Tornado', ""),
            (waterspoutDetection, 'Waterspout', ""),
            (snowSquallDetection, 'Snow Squall', ""),
            (floodDetection, 'Flash Flood', ""),
            (fireWeatherThreat, 'Risk of Fire Weather', ""),
            (denseFogThreat, 'Fog Development', ""),
            (iceThreat, 'Icy Conditions', ""),
            (additionalHazard, 'Additional Hazards', ""),
            (torProb, 'Tornado Probability', ""),
            (sigTorProb, 'Sig. Tornado Probability', ""),
            (windProb, 'Wind Probability', ""),
            (sigWindProb, 'Sig. Wind Probability', ""),
            (hailProb, 'Hail Probability', ""),
            (sigHailProb, 'Sig. Hail Probability', "")
        ]

        details_text_lines = []
        for value, label, suffix in hazard_details:
            if value != "n/a" and value != 'n/a - n/a': #second one is for the watch probs if there aren't any
                # Escape any spaces in the value for LaTeX rendering
                escaped_value = str(value).replace(" ", r"\ ")
                
                # Start the LaTeX string with the bolded value and its unit/suffix
                # Example: $\bf{1.25in}
                formatted_string = f"$\\bf{{{escaped_value}{suffix}}}"
                
                # Check if the 'OBSERVED' tag is needed for this specific hazard
                is_observed = False
                if label == 'Max. Wind Gusts' and windObserved == 'OBSERVED':
                    is_observed = True
                elif label == 'Max. Hail Size' and hailObserved == 'OBSERVED':
                    is_observed = True
                
                if is_observed:
                    # If observed, add a space and the italicized tag
                    # Example: \ \mathit{(OBSERVED)}
                    formatted_string += r"\ \mathit{(observed)}"

                # Close the LaTeX math string
                formatted_string += "$"
                
                details_text_lines.append(f"{label}: {formatted_string}")

        details_text = "\n".join(details_text_lines)
        
        #shrink fontsize if there are more than 3 things in the detailstext infobox (rare but i've seen it)
        if details_text_lines:
            if len(details_text_lines) < 4:
                info_box = AnchoredText(details_text, loc=3, prop={'size': 11}, frameon=True, zorder = 7)
            elif len(details_text_lines) >= 4:
                info_box = AnchoredText(details_text, loc=3, prop={'size': 10}, frameon=True, zorder = 7)
            ax.add_artist(info_box)
        
        pdsBox = None
        pdsBox_text = None
        pdsBox_color = None
        #set container contents, if applicable
        if torSeverity == 'CATASTROPHIC':  # Tornado Emergency
            pdsBox_text = "This is a TORNADO EMERGENCY!! \n A large and extremely dangerous tornado is ongoing \n Seek shelter immediately!"
            pdsBox_color = "#ff1717d8"
        elif floodSeverity == 'CATASTROPHIC':  # Flash Flood Emergency
            pdsBox_text = "This is a FLASH FLOOD EMERGENCY!! \n Get to higher ground NOW!"
            pdsBox_color = "#ff1717d8"
        elif tStormSeverity == 'DESTRUCTIVE': #destructive tstorm
            pdsBox_text = "This is a DESTRUCTIVE THUNDERSTORM!! \n Seek shelter immediately!"
            pdsBox_color = "#ff1717d8"
        elif torSeverity == 'CONSIDERABLE':  # PDS Tornado Warning
            pdsBox_text = "This is a PATICULARLY DANGEROUS SITUATION!! \n Seek shelter immediately!"
            pdsBox_color = "#ff1717d8"
        elif torDetection == 'POSSIBLE':  # Tornado Possible tag on SVR
            pdsBox_text = "A tornado is POSSIBLE with this storm!"
            pdsBox_color = colors['facecolor']
        elif waterspoutDetection == 'OBSERVED':
            pdsBox_text = "Waterspouts have been observed with this storm!\nSeek safe harbor immediately!"
            pdsBox_color = colors['facecolor'] #cyan/teal if its an SMW
        elif waterspoutDetection == 'POSSIBLE':
            pdsBox_text = "Waterspouts are POSSIBLE with this storm!\nSeek safe harbor immediately!"
            pdsBox_color = colors['facecolor']
        
        #create container #TODO: make the pds box a little bit smaller on the horizontal, maybe shift down slightly?
        if pdsBox_text:
            ax.text(
                x=0.5,                            # Horizontal position (center)
                y=0.8,                           # Vertical position (from bottom)
                s=pdsBox_text,                   # The message text
                transform=ax.transAxes,           # Use axes coordinates
                ha='center',                      # Horizontal alignment
                va='bottom',                      # Vertical alignment
                color='#000000',                  # Text color
                fontsize=10,
                weight='bold',
                backgroundcolor=pdsBox_color,    # The background color
                zorder=7                          # Set z-order to be on top
            )
        
        #add watermark
        imagebox = OffsetImage(logo, zoom = 0.15, alpha = 0.9)
        ab = AnnotationBbox(
            imagebox,
            xy=(0.98, 0.02),
            xycoords= 'axes fraction',
            frameon=False,
            box_alignment=(1,0),
            zorder = 7
        )
        ax.add_artist(ab)
        
        # Save the image
        
        ax.set_aspect('equal')  # or 'equal' if you want uniform scaling
        plt.savefig(output_path, bbox_inches='tight', dpi= 200)
        if len(impacted_cities) == 0:
            area_desc = alert['properties'].get('areaDesc', ['n/a'])
        elif len(impacted_cities) < 4:
            area_desc = ", ".join(impacted_cities) 
        elif len(impacted_cities) >= 4:
            area_desc = ", ".join(impacted_cities[:3]) 
          #area impacted #DONE: get this from the cities in the polygon, like the top 4 population. if there isnt any, then use the nws locations. 
        desc = alert['properties'].get('description', ['n/a'])#[7:] #long text, removing the "SVRILN" or "TORILN" thing at the start, except that isnt present on all warnings so i took it out...
        instructions = alert['properties'].get('instruction', ['n/a'])
        if alert_verb == None:
            alert_verb = 'issued'
                    
        if alert_type == 'Special Weather Statement' or alert_type == 'Special Marine Warning':
            if instructions != None: #sometimes instructions are null, which errors out the description generation. not good
                desc = desc + '\n' + instructions # Adds instructions for SPS/SMW. Sort of useful? Not all SMW include wind/hail params so hazard box doesnt always show.
        
        statement = f'''{alert_type} {alert_verb}, including {area_desc}! This alert is in effect until {formatted_expiry_time}!!\n{desc} '''
        if config.USE_TAGS:
            statement += config.DEFAULT_TAGS
        print(statement)
        elapsed_plot_time = time.time() - plot_start_time
        elapsed_total_time = time.time() - start_time
        print(Fore.LIGHTGREEN_EX + f"Map saved to {output_path} in {elapsed_plot_time:.2f}s. Total script time: {elapsed_total_time:.2f}s" + Fore.RESET)
        #print(statement)
        return output_path, statement
    except Exception as e:
        print(Fore.RED + f"Error plotting alert geometry: {e}" + Fore.RESET)
        return None, None
    finally:
        plt.close(fig) #hey dipshit dont comment this out 
        gc.collect()

if __name__ == '__main__': 
    with open('test_alerts/downtowncincy.json', 'r') as file: 
        print(Back.YELLOW + Fore.BLACK + 'testing mode! (local files)' + Style.RESET_ALL)
        test_alert = json.load(file) 
    plot_alert_polygon(test_alert, 'graphics/test/text7', False, 'issued')