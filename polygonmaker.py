#using this as like a test thing
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from metpy.plots import USCOUNTIES
from shapely.geometry import shape
from matplotlib.transforms import Bbox
import requests
import pandas as pd
from datetime import datetime
import pytz
from math import hypot
from matplotlib.offsetbox import AnchoredText, OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import matplotlib.patheffects as PathEffects
import geopandas as gpd
from shapely.geometry import box
import time
from siphon.catalog import TDSCatalog
import xarray as xr
from colorama import Back, Fore, Style
from plot_mrms2 import save_mrms_subset, get_mrms_data

#TODO: set color "library" of sorts for the colors associated with each warning type, to unify between the gfx bg and the polygons
#TODO: figure out way to seperate the colorbar from the imagery in the plot stack, so the colorbar plots on top of
    #everything, but the imagery still plots towards the bottom. 
#TODO: wider polygon borders for more intense (destructive/tor-e) warnings
#TODO: consider shrinking hazards box when theres more than x (3?4?) things in there

#reader = shpreader.Reader('countyl010g.shp')
#counties = list(reader.geometries())
#COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
AREA_FILTERS = ["OHZ052", "OHC061", "NCZ203", "LAZ143", "FLC099"]  # Replace with your local zone/county codes
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
start_time = time.time()


df_large = pd.read_csv('filtered_cities_all.csv')
logo_path= 'cincyweathernobg.png'
logo = mpimg.imread(logo_path)

roads = gpd.read_file("ne_10m_roads/ne_10m_roads.shp")

interstates_all = roads[roads['level'] == 'Interstate']
federal_roads_all = roads[roads['level'] == 'Federal']
#interstates.to_csv('interstates_filtered.csv')


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
        ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth = 1.5, zorder = 2)
        ax.add_feature(USCOUNTIES.with_scale('5m'), linewidth = 0.5, edgecolor = "#9e9e9e", zorder = 2)
        interstates_all.plot(ax=ax, linewidth = 1, edgecolor='blue', transform = ccrs.PlateCarree(), zorder = 3)
        federal_roads_all.plot(ax=ax, linewidth= 0.5, edgecolor= 'red', transform = ccrs.PlateCarree(), zorder = 3)
        
        if alert_type == "Severe Thunderstorm Warning":
            fig.set_facecolor('yellow')
        elif alert_type == 'Tornado Warning':
            fig.set_facecolor('red') 
        elif alert_type == 'Flash Flood Warning':
            fig.set_facecolor('green')
        elif alert_type == 'Special Weather Statement':
            fig.set_facecolor("#ff943d")
        elif alert_type == 'Special Marine Warning':
            fig.set_facecolor("#009691")
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
        map_region2 = { #for the mrms stuff
            "lon_min": minx,
            "lon_max": maxx,
            "lat_min": miny,
            "lat_max": maxy
        }
        #print(map_region)
        ax.set_extent(map_region)
        clip_box = ax.get_window_extent() #for the text on screen
        #NEW: plotting MRMS data here
        print("calling get_mrms_data")
        subset, cmap, vmin, vmax, cbar_label, radar_valid_time = get_mrms_data(map_region2, alert_type)
        print("data got")
        #directly plot the MRMS data onto the main axes (and colorbar, seperately)
        if subset is not None:
            im = ax.pcolormesh(
                subset.longitude, subset.latitude, subset.unknown,
                transform=ccrs.PlateCarree(),
                cmap=cmap, vmin=vmin, vmax=vmax, zorder=1
            )
            # Add the colorbar directly to the main figure
            cbar = fig.colorbar(im, ax=ax, orientation='vertical', shrink=0.75, aspect=20, pad=0.02)
            cbar.set_label(cbar_label, color="#7a7a7a", fontsize=10, weight='bold')
            cbar.ax.tick_params(labelsize=8)
        else:
            print("skipping plotting radar, no data returned from get_mrms_data")
        
        #filter for only cities in map view
        visible_cities_df = df_large[
            (df_large['lng'] >= minx) & (df_large['lng'] <= maxx) &
            (df_large['lat'] >= miny) & (df_large['lat'] <= maxy)
        ].copy()
        
        #print(f'total cities available: {len(df_large)}')
        print(f'cities in view: {len(visible_cities_df)}')
        #TESTING!!
        #radar_valid_time, radar_image_path = save_mrms_subset(map_region2, alert_type, False)
        
        
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
            
            scatter = ax.scatter(city_x, city_y, transform = ccrs.PlateCarree(), color='black', s = 1.5, marker = ".", zorder = 5) #city marker icons
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
                backgroundcolor=bgcolor, zorder = 5
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
                fontsize=10, backgroundcolor="#eeeeeecc", zorder = 6) #plotting this down here so it goes on top of city names
        ax.text(0.97, 0.97, f"Radar data valid {radar_valid_time}", #radar time
                transform=ax.transAxes, ha='right', va='top', 
                fontsize=7, backgroundcolor="#eeeeeecc", zorder = 6)
        
        #draw radar data in bg, only above the polygon
        #mrms_img = mpimg.imread(radar_image_path) 
        #ax.imshow(mrms_img, origin = 'upper', extent = map_region, transform = ccrs.PlateCarree(), zorder = 1)
        
        # Draw the polygon
        if geom.geom_type == 'Polygon':
            if alert_type == "Severe Thunderstorm Warning":
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color='yellow', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor='#ffff0050', zorder = 0)
            elif alert_type == 'Tornado Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor="#ff000050", zorder = 0)
            elif alert_type == 'Flash Flood Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color='green', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor = "#00ff2f50", zorder = 0)
            elif alert_type == 'Special Weather Statement':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color='#ff943d', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor = "#ff943d50", zorder = 0)
            elif alert_type == 'Special Marine Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color='#009691', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor = "#00969150", zorder = 0)
            else:
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=4, transform=ccrs.PlateCarree(), zorder = 4)
                ax.plot(x, y, color="#414141", linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
                ax.fill(x, y, facecolor = "#8e8e8e49", zorder = 0)  
                  
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                x, y = poly.exterior.xy
                print("how is there a multipolygon warning?? should look at this...")
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree(), zorder = 4)
        
        #box to show info about hazards like hail/wind if applicable
        maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
        maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
        torDetection = alert['properties']['parameters'].get('tornadoDetection', ['n/a'])[0] #string, possible for svr; radar-indicated, radar-confirmed, need to see others for tor warning
        floodSeverity = alert['properties']['parameters'].get('flashFloodDamageThreat', ['n/a'])[0] #string, default level (unsure what this returns), considerable, catastophic
        tStormSeverity = alert['properties']['parameters'].get('thunderstormDamageThreat', ['n/a'])[0] 
        torSeverity = alert['properties']['parameters'].get('tornadoDamageThreat', ['n/a'])[0] #considerable for pds, not sure for tor-e. 
        floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
        snowSquallDetection = alert['properties']['parameters'].get('snowSquallDetection', ['n/a'])[0] #"RADAR INDICATED" or "OBSERVED"
        snowSquallImpact = alert['properties']['parameters'].get('snowSquallImpact', ['n/a'])[0] # "SIGNIFICANT" or nothing
        waterspoutDetection = alert['properties']['parameters'].get('waterspoutDetection', ['n/a'])[0] #"OBSERVED" or "POSSIBLE"
        
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
                val_str = str(value).replace(" ", r"\ ") + suffix
                details_text_lines.append(f"{label}: $\\bf{{{val_str}}}$")

        details_text = "\n".join(details_text_lines)
        info_box = AnchoredText(details_text, loc=3, prop={'size': 12}, frameon=True)
        ax.add_artist(info_box)
        
        if tStormSeverity == 'DESTRUCTIVE': #need to check this is what pds/tor-e have as their tags
            pdsBox = ax.text(0.5, 0.85, "This is a DESTRUCTIVE THUNDERSTORM!! \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        if torDetection == 'POSSIBLE': #for TOR possible SVR? Kinda cool idea
            pdsBox = ax.text(0.5, 0.85, "A tornado is POSSIBLE with this storm!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="yellow", )
            ax.add_artist(pdsBox)
        if waterspoutDetection == 'POSSIBLE': #waterspouts
            pdsBox = ax.text(0.5, 0.85, "A Waterspout is POSSIBLE with this storm!\nHead to shore immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="#009691", )
            ax.add_artist(pdsBox)
        if waterspoutDetection == 'OBSERVED': #waterspouts
            pdsBox = ax.text(0.5, 0.85, "Waterspouts have been observed with this storm!\nHead to shore immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="#009691", )
            ax.add_artist(pdsBox)
        elif torSeverity == 'CONSIDERABLE':
            pdsBox = ax.text(0.5, 0.85, "This is a PATICULARLY DANGEROUS SITUATION!! \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        elif torSeverity == 'CATASTROPHIC':
            pdsBox = ax.text(0.5, 0.85, "This is a TORNADO EMERGENCY!! \n A large and extremely dangerous tornado is ongoing \n Seek shelter immediately!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
                fontsize=10, weight = 'bold', backgroundcolor="#ff1717a7", )
            ax.add_artist(pdsBox)
        elif floodSeverity == 'CATASTROPHIC':
            pdsBox = ax.text(0.5, 0.85, "This is a FLASH FLOOD EMERGENCY!! \n Get to higher ground NOW!", 
                transform=ax.transAxes, ha='center', va='bottom', color = '#000000',
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
        desc = alert['properties'].get('description', ['n/a'])#[7:] #long text, removing the "SVRILN" or "TORILN" thing at the start, except that isnt present on all warnings so i took it out...
        if alert_type == 'Special Weather Statement' or alert_type == 'Special Marine Warning':
            desc = desc + '\n' + alert['properties'].get('instruction', ['n/a']) # Adds instructions for SPS/SMW. Sort of useful? Not all SMW include wind/hail params so hazard box doesnt always show.
        statement = (f"A {alert_type} has been issued, including {area_desc}! This alert is in effect until {formatted_expiry_time}!!\n{desc} \n#cincywx #cincinnati #weather #ohwx #ohiowx #cincy #cincinnatiwx")
        elapsed_plot_time = time.time() - plot_start_time
        elapsed_total_time = time.time() - start_time
        print(Fore.LIGHTGREEN_EX + f"Map saved to {output_path} in {elapsed_plot_time:.2f}s. Total script time: {elapsed_total_time:.2f}s")
        #print(statement)
        return output_path, statement
    except Exception as e:
        print(Fore.RED + f"Error plotting alert geometry: {e}")
        return None


#plot_alert_polygon(test_alert2)