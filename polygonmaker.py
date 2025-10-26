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
import matplotlib.font_manager as fm
import geopandas as gpd
import time
from colorama import Back, Fore, Style
from plot_mrms2 import get_mrms_data_async
from timezonefinderL import TimezoneFinder
import gc
import json
from config_manager import config #diasble for testing w/ just this script
from constants import ALERT_COLORS
from gfx_tools.details_box import get_hazard_details
from gfx_tools.get_alert_geometry import get_alert_geometry
from gfx_tools.winter_product import is_alert_winter
import importlib.metadata

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
-1 - ocean, lakes fill
0 - polygon fill
1 - radar imagery
2 - county/state borders
3 - roads
4 - polygon border
5 - city/town names
7 - UI elements (issued time, logo, colorbar, radar time, hazards box, pdsbox)
'''
try:    
    VERSION_NUMBER = importlib.metadata.version('insta-alert') #Major version (dk criteria for this) Minor version (pushes to stable branch) Feature version (each push to dev branch)
except importlib.metadata.PackageNotFoundError:
    VERSION_NUMBER = '0.7.12'
    
print(Back.BLUE + f'Running graphics v{VERSION_NUMBER}' + Back.RESET)


start_time = time.time()
tf = TimezoneFinder()

#font loading
try:
    # Point to the specific .ttf files
    FP_XLIGHT = fm.FontProperties(fname='assets/fonts/Roboto-ExtraLight.ttf')
    FP_LIGHT = fm.FontProperties(fname='assets/fonts/Roboto-Light.ttf')
    FP_REGULAR = fm.FontProperties(fname='assets/fonts/Roboto-Regular.ttf')
    FP_MEDIUM = fm.FontProperties(fname='assets/fonts/Roboto-Medium.ttf')
    FP_SEMIBOLD = fm.FontProperties(fname='assets/fonts/Roboto-SemiBold.ttf')
    FP_BOLD = fm.FontProperties(fname='assets/fonts/Roboto-Bold.ttf')
    FP_XBOLD = fm.FontProperties(fname='assets/fonts/Roboto-ExtraBold.ttf')
    print(Back.GREEN + "Custom fonts loaded successfully from 'assets/fonts/'" + Back.RESET)
except FileNotFoundError:
    print(Back.YELLOW + "Font files not found in 'assets/fonts/'. Falling back to default sans-serif." + Back.RESET)
    # Fallback to default if fonts aren't found
    FP_REGULAR = fm.FontProperties(family='sans-serif', weight='normal')
    FP_MEDIUM = fm.FontProperties(family='sans-serif', weight='normal') # Will look like regular
    FP_SEMIBOLD = fm.FontProperties(family='sans-serif', weight='semibold') # Might just look bold
except Exception as e:
    print(Back.RED + f"Error loading fonts: {e}. Falling back to default." + Back.RESET)
    # Generic fallback
    FP_REGULAR = fm.FontProperties(family='sans-serif', weight='normal')
    FP_MEDIUM = fm.FontProperties(family='sans-serif', weight='normal')
    FP_SEMIBOLD = fm.FontProperties(family='sans-serif', weight='semibold')

print(Fore.BLACK + Back.LIGHTWHITE_EX + 'Loading cities' + Back.RESET)
#cities w/pop >250
conus_cities_ds = pd.read_csv('assets/gis/cities_100_lite.csv')
ak_cities_ds = pd.read_csv('assets/gis/ak_cities.csv')

print(Back.LIGHTWHITE_EX + 'Cities loaded. Loading logo.' + Back.RESET)
logo_path= 'assets/logo2.png'
logo = mpimg.imread(logo_path)

print(Back.LIGHTWHITE_EX + 'Logo loaded. Loading pre-processed 500k borders.' + Back.RESET)
# Load the two layers from the single, pre-processed gpkg file.
counties_gdf = gpd.read_file("assets/gis/processed_borders_500k.gpkg", layer='counties')
states_gdf = gpd.read_file("assets/gis/processed_borders_500k.gpkg", layer='states')

print(Back.LIGHTWHITE_EX + 'Borders loaded. Loading water features.' + Back.RESET)

lakes4km = gpd.read_file("assets/gis/water/lakes_4km_compressed.fgb")
lakes15km = gpd.read_file('assets/gis/water/lakes_15km_compressed.fgb')
oceans = gpd.read_file("assets/gis/water/water_background.fgb")

print(Back.LIGHTWHITE_EX + 'Water features loaded. Loading roads.' + Back.RESET)
interstates = gpd.read_file("assets/gis/processed_interstates_500k_5prec_10tol.fgb") #3  decimals on the coords
us_highways = gpd.read_file('assets/gis/all_us_highways_10tol.fgb') #us highways for conus and state highways for ak/hi. dataset does not have us/state highways equivalents for PR...

print(Back.LIGHTWHITE_EX + 'All data loaded successfully.' + Back.RESET + Fore.RESET)
#interstates.to_csv('interstates_filtered.csv')

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

def plot_alert_polygon(alert, output_path, mrms_plot, alert_verb):
    plot_start_time = time.time()
    geom, geom_type = get_alert_geometry(alert) #returns geometry shape and if it is polygon or zone/county
    minx0, _, maxx0, _ = geom.bounds #i swear i've got minx and maxx defined in like 10k places so these will be unique ones
    width = maxx0 - minx0
    # factor of the width to buffer
    buffer_dist = width * 0.017 #0.0175 works well, 0.02 might be too much
    geom = geom.buffer(buffer_dist).buffer(-buffer_dist) #smooths out (expanding like circle thing from the points) and then back in, removing some of the complex points/geoms 
    
    tolerance = width * 0.001 #simplify to reduce vertices #0.001 works well
    geom = geom.simplify(tolerance, preserve_topology= True)
    
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
            print("now plotting: " + alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
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
            print("now plotting:" + alert_type + " issued " + formatted_issued_time + " expires " + formatted_expiry_time )
        
        #plot setup
        minx, _, maxx, _ = geom.bounds #ignore the lat, as its not relevant here
        #print(minx, maxx)
        fig, ax = plt.subplots(figsize=(9, 6), subplot_kw={'projection': ccrs.PlateCarree()})
        colors = ALERT_COLORS.get(alert_type, ALERT_COLORS['default'])
        formatted_alert_type = alert_type.upper().replace(' ', r'\ ')

        if alert_verb == 'upgraded':
            # Use the pre-formatted variable in the title string.
            ax.set_title(fr"$\mathbf{{{formatted_alert_type}}}$" + " -" + fr" $\mathit{{{alert_verb.capitalize()}!}}$" + "\n" + f"expires {formatted_expiry_time}", fontsize=14, loc='left') #latex/math formatting is also beyond me. ALSO the exclamation point wont be italicized because the default MPL font just straight up doesnt have a glyph for it and the workaround seems way worse than what its at now
        else:
            # Also use the pre-formatted variable here.
            ax.set_title(fr"$\mathbf{{{formatted_alert_type}}}$" + "\n" + f"expires {formatted_expiry_time}", fontsize=14, loc='left')  #dont really need a verb if it is not upgraded i dont think

        counties_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='#9e9e9e', facecolor='none', linewidth=0.75, zorder=2) 
        states_gdf.plot(ax=ax, transform=ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=1.5, zorder=2)
        us_highways.plot(ax=ax, linewidth= 0.5, edgecolor= 'red', transform = ccrs.PlateCarree(), zorder = 4)
        interstates.plot(ax=ax, linewidth = 1, edgecolor='blue', transform = ccrs.PlateCarree(), zorder = 4)
        oceans.plot(ax=ax, linewidth = 0, edgecolor="#000000ff", facecolor="#66baffff", transform = ccrs.PlateCarree(), zorder = -1)
        
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

        map_region2 = { # For the MRMS stuff, pad it a little bit to not have blank space at the edges
            "lon_min": final_minx - 0.01,
            "lon_max": final_maxx + 0.01,
            "lat_min": final_miny - 0.01,
            "lat_max": final_maxy + 0.01
        }
        
        ax.set_extent(map_region, crs=ccrs.PlateCarree())

        clip_box = ax.get_window_extent() #for the text on screen
        #check for region
        office_awips = alert['properties']['parameters'].get("AWIPSidentifier")[0]
        office_awips = office_awips[3:]
        if office_awips == 'SJU':
            region = 'PR'
        elif office_awips in ['AFC', 'AJK', 'AFG', 'ALU', 'NSB', 'AER', 'WCZ']:
            region = 'AK'
        elif office_awips == 'HFO':
            region = 'HI'
        elif office_awips == 'GUM' or issuing_office == 'NWS Tiyan GU':
            region = 'GU'
        else:
            region = 'US'
            
        use_snow_cmap = is_alert_winter(alert)
            
        if mrms_plot == True:
            subset, cmap, vmin, vmax, cbar_label, radar_valid_time = get_mrms_data_async(map_region2, alert_type, region, use_snow_cmap)
            #directly plot the MRMS data onto the main axes (and colorbar, seperately)
            if subset is not None and subset.unknown.size > 0:
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
            print('not plotting MRMS (recieved plot_mrms = False.)')
        
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
        #plotting lakes down here after we know the alert height
        if alert_height > 1.5: #might need tweaking, but should basically mean big alerts like watches and the like plot fewer lakes
            lakes15km.plot(ax=ax, linewidth = 0.4, edgecolor="#000000ff", facecolor="#a5d5fdff", transform = ccrs.PlateCarree(), zorder = -1)
        else:
            lakes4km.plot(ax=ax, linewidth = 0.4, edgecolor="#000000ff", facecolor="#a5d5fdff", transform = ccrs.PlateCarree(), zorder = -1)

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
                font_props = FP_XBOLD.copy() 
                font_props.set_size(13)
                print(f'{name} 60k+')
                color = "#101010"
                bgcolor = '#ffffff00'
            elif city_pop > 10000:
                name = city['city_ascii']
                font_props = FP_SEMIBOLD.copy() 
                font_props.set_size(11)
                color = "#101010"
                bgcolor = "#ffffff00"
            elif city_pop > 1000:
                name = city['city_ascii']
                font_props = FP_MEDIUM.copy() 
                font_props.set_size(10)
                color = "#101010"
                bgcolor = '#ffffff00'
            else:
                name = city['city_ascii']
                font_props = FP_REGULAR.copy() 
                font_props.set_size(8)
                color = "#232323"
                bgcolor = '#ffffff00'

            text_artist = ax.text(
                city_x, city_y, name,  
                fontproperties = font_props, fontstretch='normal', ha='center', va='bottom',
                c=color, transform=ccrs.PlateCarree(), clip_on=True,
                backgroundcolor=bgcolor, zorder = 5
            )
            text_artist.set_clip_box(clip_box)
            text_artist.set_path_effects([PathEffects.withStroke(linewidth=1.45, foreground='white'), PathEffects.Normal()])
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
        #box to show info about hazards like hail/wind if applicable, also get tags for the pdsBox
        details_text_lines, torSeverity, tStormSeverity, floodSeverity, torDetection, waterspoutDetection = get_hazard_details(alert, geom_type)
        details_text = "\n".join(details_text_lines)
        
        #shrink fontsize if there are more than 3 things in the detailstext infobox (rare but i've seen it)
        if details_text_lines:
            if len(details_text_lines) < 4:
                info_box = AnchoredText(details_text, loc=3, prop={'size': 11}, frameon=True, zorder = 7)
            elif len(details_text_lines) >= 4:
                info_box = AnchoredText(details_text, loc=3, prop={'size': 10}, frameon=True, zorder = 7)
            ax.add_artist(info_box)
        
        #add a pop-up box if any of these criteria are hit
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
        imagebox = OffsetImage(logo, zoom = 0.08, alpha = 1.0)
        ab = AnnotationBbox(
            imagebox,
            xy=(0.97, 0.02),
            xycoords= 'axes fraction',
            frameon=False,
            box_alignment=(1,0),
            zorder = 7
        )
        ax.add_artist(ab)
        
        # Save the plot image
        ax.set_aspect('equal')  # or 'equal' if you want uniform scaling
        plt.savefig(output_path, bbox_inches='tight', dpi= 400)
        
        if not impacted_cities: 
            area_desc = alert['properties'].get('areaDesc', ['n/a'])
        else:
            # If the list is long, limit it to the top 3 most populous cities
            cities_to_format = impacted_cities[:3] if len(impacted_cities) >= 4 else impacted_cities

            # Format the list with 'and' before the last item
            if len(cities_to_format) == 1:
                area_desc = cities_to_format[0]
            else:
                area_desc = f"{', '.join(cities_to_format[:-1])} and {cities_to_format[-1]}"
        #area impacted #DONE: get this from the cities in the polygon, like the top 4 population. if there isnt any, then use the nws locations. 
        desc = alert['properties'].get('description', ['n/a'])#[7:] #long text, removing the "SVRILN" or "TORILN" thing at the start, except that isnt present on all warnings so i took it out...
        instructions = alert['properties'].get('instruction', ['n/a'])
        if alert_verb == None:
            alert_verb = 'issued'
                    
        if alert_type == 'Special Weather Statement' or alert_type == 'Special Marine Warning':
            if instructions != None: #sometimes instructions are null, which errors out the description generation. not good
                desc = desc + '\n' + instructions # Adds instructions for SPS/SMW. Sort of useful? Not all SMW include wind/hail params so hazard box doesnt always show.
        
        #use exclamation marks or just a period:
        if alert_type in ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning', 'Special Marine Warning']:
            punc = "!"
        else: 
            punc = "."
        statement = f'''{alert_type} {alert_verb}, including {area_desc}{punc} This alert is in effect until {formatted_expiry_time}{punc}\n{desc} '''
        #if config.USE_TAGS:
         #   statement += config.DEFAULT_TAGS
        #print(statement)
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
    with open('test_alerts/spstesttext.json', 'r') as file: 
        print(Back.YELLOW + Fore.BLACK + 'testing mode! (local files)' + Style.RESET_ALL)
        test_alert = json.load(file) 
    plot_alert_polygon(test_alert, 'graphics/test/text1', True, 'issued')
