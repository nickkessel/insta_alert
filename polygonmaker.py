#using this as like a test thing
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from shapely.geometry import shape
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

#DONE: set color "library" of sorts for the colors associated with each warning type, to unify between the gfx bg and the polygons
#DONE: figure out way to seperate the colorbar from the imagery in the plot stack, so the colorbar plots on top of
    #everything, but the imagery still plots towards the bottom. 
#TODO: wider polygon borders for more intense (destructive/tor-e) warnings
#DONE: consider shrinking hazards box when theres more than x (3?4?) things in there
#TODO: adjust city name boldness for readability (done-ish)
#DONE: space out city names slightly more
#DONE: have a greater min_deg_distance when the lat/lon is bigger than a certain area, so that for big warnings
    #there aren't like big boxes with super dense city names with them
#TODO: figure out/fix highway/road plotting so that they are better, basically, but also continuous (e.g no random gaps in the highway)
#DONE: use regex to pull hazard params from SMW alert text so they show in hazardbox (done? need to test w/ hail)

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
VERSION_NUMBER = "0.5.2" #Major version (dk criteria for this) Minor version (pushes to stable branch) Feature version (each push to dev branch)
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

#reader = shpreader.Reader('countyl010g.shp')
#counties = list(reader.geometries())
#COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())

start_time = time.time()
zone_geometry_cache = {}

print(Fore.BLACK + Back.LIGHTWHITE_EX + 'Loading cities' + Back.RESET)
df_large = pd.read_csv('filtered_cities_all.csv')

print(Back.LIGHTWHITE_EX + 'Cities loaded. Loading logo.' + Back.RESET)
logo_path= 'testlogo1.png'
logo = mpimg.imread(logo_path)

print(Back.LIGHTWHITE_EX + 'Logo loaded. Loading pre-processed 500k borders.' + Back.RESET)
# Load the two layers from the single, pre-processed gpkg file.
counties_gdf = gpd.read_file("gis/processed_borders_500k.gpkg", layer='counties')
states_gdf = gpd.read_file("gis/processed_borders_500k.gpkg", layer='states')

print(Back.LIGHTWHITE_EX + 'Borders loaded. Loading roads.' + Back.RESET)
highres_roads = gpd.read_file("gis/roads2/tl_2024_us_primaryroads.shp")
lowres_roads = gpd.read_file('gis/ne_10m_roads/ne_10m_roads.shp') #can't find a better national dataset for us highways
#print("Unique Route Types (RTTYP) found in the shapefile:", highres_roads['RTTYP'].unique())

print(Back.LIGHTWHITE_EX + 'Roads loaded. Filtering roads.' + Back.RESET)
interstates = highres_roads[highres_roads['RTTYP'] == 'I']
us_highways = lowres_roads[lowres_roads['level'] == 'Federal']

print(Back.LIGHTWHITE_EX + 'All data loaded successfully.' + Back.RESET)
#interstates.to_csv('interstates_filtered.csv')

with open('test_alerts/nonconvectivesps_1.json', 'r') as file:
    test_alert = json.load(file)

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
        return shape(geometry_data), 'polygon'

    # If no direct geometry, process as a zone-based alert (e.g., a Watch)
    print("Processing zone-based alert (geometry is null).")
    affected_zones = alert['properties'].get('affectedZones', [])
    if not affected_zones:
        print(Fore.YELLOW + "Alert has no geometry and no affected zones." + Fore.RESET)
        return None, None
    
    alert_type = alert['properties'].get("event")
    issuing_state = alert['properties'].get("senderName")[-2:]
    print(issuing_state)
    if issuing_state == 'AK' and alert_type == 'Special Weather Statement':
        print('not plotting due to known errors with Alaska zone-based SPS.')
        return None, None
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
                zone_geometry_cache[zone_url] = zone_shape # Add to cache
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


def plot_alert_polygon(alert, output_path, mrms_plot):
    plot_start_time = time.time()
    geom, geom_type = get_alert_geometry(alert) #returns geometry shape and if it is polygon or zone/county
    
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
        tf = TimezoneFinder()
        centerlon, centerlat = geom.centroid.x, geom.centroid.y
        timezone_str = tf.timezone_at(lng=centerlon, lat= centerlat)
        print(timezone_str)
        alert_tz = pytz.timezone(timezone_str)
        
        dt_sent = datetime.fromisoformat(issued_time).astimezone(alert_tz)
        dt_expires = datetime.fromisoformat(expiry_time).astimezone(alert_tz)
        
        formatted_issued_time = dt_sent.strftime("%I:%M %p %Z")
        formatted_expiry_time = dt_expires.strftime("%B %d, %I:%M %p %Z")
        print(alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
        
        '''
        #time formatting (old)
        dt = datetime.fromisoformat(expiry_time)
        eastern = pytz.timezone("US/Eastern")
        dt_eastern = dt.astimezone(eastern)
        formatted_expiry_time = dt_eastern.strftime("%B %d, %I:%M %p %Z")
        dt1 = datetime.fromisoformat(issued_time)
        dt1_eastern = dt1.astimezone(eastern)
        formatted_issued_time = dt1_eastern.strftime("%I:%M %p %Z")
        print(alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
        '''
        #plot setup
        fig, ax = plt.subplots(figsize=(9, 6), subplot_kw={'projection': ccrs.PlateCarree()})
        colors = ALERT_COLORS.get(alert_type, ALERT_COLORS['default'])
        ax.set_title(f"{alert_type.upper()}\nexpires {formatted_expiry_time}", fontsize=14, fontweight='bold', loc='left')
        
        counties_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='#9e9e9e', facecolor='none', linewidth=0.75, zorder=2) 
        states_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=1.5, zorder=2)
        #ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth = 1.5, zorder = 2)
        #ax.add_feature(USCOUNTIES.with_scale('5m'), linewidth = 0.5, edgecolor = "#9e9e9e", zorder = 2)
        us_highways.plot(ax=ax, linewidth= 0.5, edgecolor= 'red', transform = ccrs.PlateCarree(), zorder = 4)
        interstates.plot(ax=ax, linewidth = 1, edgecolor='blue', transform = ccrs.PlateCarree(), zorder = 4)
        
        #simplified
        colors = ALERT_COLORS.get(alert_type, ALERT_COLORS['default'])
        fig.set_facecolor(colors['facecolor'])
                   
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
        padding_factor = 0.3 #0.3 dont change from this
        pad_x = (maxx - minx) *padding_factor
        pad_y = (maxy - miny) * padding_factor
        
        minx -= pad_x
        maxx += pad_x
        miny -= pad_y
        maxy += pad_y
        #scale = 0.2 #more is more zoomed out, less is more zoomed in #0.2-0.3 is probably ideal
        map_region = [minx, maxx, miny, maxy]
        #print(map_region)
        map_region2 = { #for the mrms stuff
            "lon_min": minx - 0.01,
            "lon_max": maxx + 0.01,
            "lat_min": miny - 0.01,
            "lat_max": maxy + 0.01
        }
        #print(map_region2)
        ax.set_extent(map_region)
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
        elif office_awips == 'GUM':
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
        alert_height = maxy - miny #how big is the box? 'normal' alert heights: seems like up to .9-1?(degree) Anything bigger than that gets a little cluttered
        print(f'alert height: {alert_height}') 
        '''
        #this could honestly maybe be like dynamically scaled?
        if alert_height > 1 and alert_height <= 1.75: 
            min_distance_deg = 0.08 #0.065 is good for 0.2-0.3 scale
        elif alert_height > 1.75 and alert_height <= 2.5:
            min_distance_deg = 0.12
        elif alert_height > 2.5:
            min_distance_deg = 0.2
        elif alert_height <= 1:
            min_distance_deg = 0.04
        '''
        min_distance_deg = alert_height/8
        
        for _, city in visible_cities_df.iterrows():
            city_x = city['lng']
            city_y = city['lat']
            city_pop = city['population']
            
            #skip if too close to already plotted city
            too_close = any(hypot(city_x - px, city_y - py) < min_distance_deg for px, py in plotted_points)
            if too_close:
                continue
            #actually plot city
            
            scatter = ax.scatter(city_x, city_y, transform = ccrs.PlateCarree(), color='black', s = 1.5, marker = ".", zorder = 5) #city marker icons
            if city_pop > 60000:
                name = city['city_ascii'].upper()
                fontsize = 12
                weight = 'semibold'
                color = "#222222"
                bgcolor = '#ffffff00'
            elif city_pop > 10000:
                name = city['city_ascii']
                fontsize = 10
                weight = 'semibold'
                color = "#313131"
                bgcolor = "#ffffff00"
            else:
                name = city['city_ascii']
                fontsize = 8
                weight = 'semibold'
                color = "#313131"
                bgcolor = '#ffffff00'

            text_artist = ax.text(
                city_x, city_y, name,
                fontfamily='monospace', fontsize=fontsize, weight=weight,
                fontstretch='ultra-condensed', ha='center', va='bottom',
                c=color, transform=ccrs.PlateCarree(), clip_on=True,
                backgroundcolor=bgcolor, zorder = 5
            )
            text_artist.set_clip_box(clip_box)
            text_artist.set_path_effects([PathEffects.withStroke(linewidth=1.5, foreground='white'), PathEffects.Normal()])
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
        fig.text(0.90, 0.96, f'v.{VERSION_NUMBER}', ha='right', va='top', 
                 fontsize = 6, color="#000000", backgroundcolor="#96969636")
        fig.text(0.90, 0.92, f'Generated: {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ', ha='right', va='top', #time.strftime("%Y-%m-%d %H:%M:%S")
                 fontsize=6, color='#000000', backgroundcolor='#96969636')
        ax.text(0.01, 0.985, f"Issued {formatted_issued_time} by {issuing_office}", 
                transform=ax.transAxes, ha='left', va='top', 
                fontsize=9, backgroundcolor="#eeeeeecc", zorder = 7) #plotting this down here so it goes on top of city names

        
        #draw radar data in bg, only above the polygon
        #mrms_img = mpimg.imread(radar_image_path) 
        #ax.imshow(mrms_img, origin = 'upper', extent = map_region, transform = ccrs.PlateCarree(), zorder = 1)
        
        # Draw the polygon
        draw_alert_shape(ax, geom, colors)
        '''
        if geom.geom_type == 'Polygon':
            fill_color = colors['facecolor'] + colors['fillalpha'] #rebuild the hexcode w/ alpha
            edge_color = colors ['edgecolor']
            
            x, y = geom.exterior.xy
            ax.plot(x,y, color='black', linewidth=4, transform = ccrs.PlateCarree(), zorder = 4)
            ax.plot(x,y, color=edge_color, linewidth=2, transform = ccrs.PlateCarree(), zorder = 4)
            ax.fill(x,y, fill_color, zorder = 0)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                print("how is there a multipolygon warning?? should look at this...")
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)   
        '''
        #box to show info about hazards like hail/wind if applicable
        
        maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
        maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
        windObserved = alert['properties']['parameters'].get('windThreat', ["n/a"])[0]
        hailObserved = alert['properties']['parameters'].get('hailThreat', ["n/a"])[0]
        torDetection = alert['properties']['parameters'].get('tornadoDetection', ['n/a'])[0] #string, possible for svr; radar-indicated, radar-confirmed, need to see others for tor warning
        floodSeverity = alert['properties']['parameters'].get('flashFloodDamageThreat', ['n/a'])[0] #string, default level (unsure what this returns), considerable, catastophic
        tStormSeverity = alert['properties']['parameters'].get('thunderstormDamageThreat', ['n/a'])[0] 
        torSeverity = alert['properties']['parameters'].get('tornadoDamageThreat', ['n/a'])[0] #considerable for pds, not sure for tor-e. 
        floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
        snowSquallDetection = alert['properties']['parameters'].get('snowSquallDetection', ['n/a'])[0] #"RADAR INDICATED" or "OBSERVED"
        snowSquallImpact = alert['properties']['parameters'].get('snowSquallImpact', ['n/a'])[0] # "SIGNIFICANT" or nothing
        waterspoutDetection = alert['properties']['parameters'].get('waterspoutDetection', ['n/a'])[0] #"OBSERVED" or "POSSIBLE"
        
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
            (floodDetection, 'Flash Flood', "")
        ]

        details_text_lines = []
        for value, label, suffix in hazard_details:
            if value != "n/a":
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
                info_box = AnchoredText(details_text, loc=3, prop={'size': 12}, frameon=True, zorder = 7)
            elif len(details_text_lines) >= 4:
                info_box = AnchoredText(details_text, loc=3, prop={'size': 10}, frameon=True, zorder = 7)
            ax.add_artist(info_box)
        
        pdsBox = None
        pdsBox_text = None
        pdsBox_color = None
        #set container contents, if applicable
        if torSeverity == 'CATASTROPHIC':  # Tornado Emergency
            pdsBox_text = "This is a TORNADO EMERGENCY!! \n A large and extremely dangerous tornado is ongoing \n Seek shelter immediately!"
            pdsBox_color = "#ff1717a7"
        elif floodSeverity == 'CATASTROPHIC':  # Flash Flood Emergency
            pdsBox_text = "This is a FLASH FLOOD EMERGENCY!! \n Get to higher ground NOW!"
            pdsBox_color = "#ff1717a7"
        elif tStormSeverity == 'DESTRUCTIVE': #destructive tstorm
            pdsBox_text = "This is a DESTRUCTIVE THUNDERSTORM!! \n Seek shelter immediately!"
            pdsBox_color = "#ff1717a7"
        elif torSeverity == 'CONSIDERABLE':  # PDS Tornado Warning
            pdsBox_text = "This is a PATICULARLY DANGEROUS SITUATION!! \n Seek shelter immediately!"
            pdsBox_color = "#ff1717a7"
        elif torDetection == 'POSSIBLE':  # Tornado Possible tag on SVR
            pdsBox_text = "A tornado is POSSIBLE with this storm!"
            pdsBox_color = colors['facecolor']
        elif waterspoutDetection == 'OBSERVED':
            pdsBox_text = "Waterspouts have been observed with this storm!\nSeek safe harbor immediately!"
            pdsBox_color = colors['facecolor'] #cyan/teal if its an SMW
        elif waterspoutDetection == 'POSSIBLE':
            pdsBox_text = "Waterspouts are POSSIBLE with this storm!\nSeek safe harbor immediately!"
            pdsBox_color = colors['facecolor']
        
        #create container
        if pdsBox_text:
            ax.text(
                x=0.5,                            # Horizontal position (center)
                y=0.85,                           # Vertical position (from bottom)
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
        
        area_desc = alert['properties'].get('areaDesc', ['n/a']) #area impacted
        desc = alert['properties'].get('description', ['n/a'])#[7:] #long text, removing the "SVRILN" or "TORILN" thing at the start, except that isnt present on all warnings so i took it out...
        instructions = alert['properties'].get('instruction', ['n/a'])
        
        if alert_type == 'Special Weather Statement' or alert_type == 'Special Marine Warning':
            if instructions != None: #sometimes instructions are null, which errors out the description generation. not good
                desc = desc + '\n' + instructions # Adds instructions for SPS/SMW. Sort of useful? Not all SMW include wind/hail params so hazard box doesnt always show.
        
        statement = (f"A {alert_type} has been issued, including {area_desc}! This alert is in effect until {formatted_expiry_time}!!\n{desc} \n#cincywx #cincinnati #weather #ohwx #ohiowx #cincy #cincinnatiwx")
        elapsed_plot_time = time.time() - plot_start_time
        elapsed_total_time = time.time() - start_time
        print(Fore.LIGHTGREEN_EX + f"Map saved to {output_path} in {elapsed_plot_time:.2f}s. Total script time: {elapsed_total_time:.2f}s" + Fore.RESET)
        #print(statement)
        return output_path, statement
    except Exception as e:
        print(Fore.RED + f"Error plotting alert geometry: {e}" + Fore.RESET)
        return None, None
    finally:
        plt.close(fig)
        gc.collect()


if __name__ == '__main__':  
    plot_alert_polygon(test_alert, 'graphics/test/cbartest3', True)