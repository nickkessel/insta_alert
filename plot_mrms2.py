import requests
import gzip
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import glob

#TODO: fix scaling/distortion of the colorbar/legend
#TODO: optimize the loading/subsetting of data - could cache to do multiple warnings in the same "wave"
#TODO: Possible: Threading, and have save_mrms_subset running in the background every 2 minutes, 
    #creating a national composite for both QPE and REF, that can then be accessed from other functions
    #by passing in a bbox and getting that part of the image back.

#recreate radarscope colortable for colormap
# List of (dBZ, RGBA) tuples 
stops = [
    (-15, (0, 0, 0, 0)),
    (5, (29, 37, 60)),
    (17.5, (89, 155, 171)),
    (22.5, (33, 186, 72)),
    (32.5, (5, 101, 1)),
    (37.5, (251, 252, 0)),  # to (199,176,0) maybe a typo? Using first set
    (42.5, (253, 149, 2)),  # to (172,92,2) same, using first
    (50, (253, 38, 0)),     # to (135,43,22) same
    (60, (193, 148, 179)),  # to (200,23,119) — mixed RGB? Use first
    (70, (165, 2, 215)),    # to (64,0,146)
    (75, (135, 255, 253)),  # to (54,120,142)
    (80, (173, 99, 64)),
    (85, (105, 0, 4)),
    (95, (0, 0, 0)),
]

# Normalize dBZ values to 0–1 for matplotlib
min_dbz = stops[0][0]
max_dbz = stops[-1][0]
normalized_stops = [
    ((level - min_dbz) / (max_dbz - min_dbz), tuple(c/255 for c in color))
    for level, color in stops
]

# Create the colormap
radarscope_cmap = LinearSegmentedColormap.from_list("radarscope", normalized_stops)

#inches, (R G B)
stops2 = [ #QPE colorscale, 0 to 6"
    (0.0,  (0, 0, 0, 0)),         
    (0.01, (68, 166, 255, 120)),
    (0.1,  (155, 255, 155, 255)), 
    (0.5,  (0, 200, 0, 255)),     
    (1.0,  (255, 255, 0, 255)),   
    (2.0,  (255, 128, 0, 255)),   
    (3.0,  (255, 0, 0, 255)),     
    (4.5,  (150, 0, 75, 255)),    
    (6.0,  (255, 0, 255, 255)),   
]

# Normalize dBZ values to 0–1 for matplotlib
min_val2 = stops2[0][0]
max_val2 = stops2[-1][0]
normalized_stops2 = [
    ((level - min_val2) / (max_val2 - min_val2), tuple(c/255 for c in color))
    for level, color in stops2
]
# Create the colormap
qpe_cmap = LinearSegmentedColormap.from_list("QPE", normalized_stops2)

#inches, (R G B)
stops3 = [ #gQPE colorscale 0-4"
    (0.0,  (0, 0, 0, 0)),         
    (0.01, (68, 166, 255, 120)),
    (0.1,    (155, 255, 155, 255)),
    (0.5,    (0, 200, 0, 255)),
    (1.0,    (255, 255, 0, 255)),
    (1.5,    (255, 128, 0, 255)),
    (2.0,    (255, 64, 0, 255)),
    (2.5,    (255, 0, 0, 255)),
    (3.0,    (210, 0, 45, 255)),
    (3.5,    (150, 0, 75, 255)),
    (4.0,    (255, 0, 255, 255)),
]

# Normalize dBZ values to 0–1 for matplotlib
min_val3 = stops3[0][0]
max_val3 = stops3[-1][0]
normalized_stops3 = [
    ((level - min_val3) / (max_val3 - min_val3), tuple(c/255 for c in color))
    for level, color in stops3
]
# Create the colormap
qpe2_cmap = LinearSegmentedColormap.from_list("QPE", normalized_stops3)

valid_time = 0
def save_mrms_subset(bbox, type, state_borders):
    """
    Fetches latest MRMS data, subsets it to a bounding box, 
    and saves it as a transparent PNG.

    Args:
        bbox (dict): A dictionary with keys 'lon_min', 'lon_max', 
                     'lat_min', 'lat_max'.
        type (str): The type of warning. This'll generate a different image & colormap
                    for a svr/tor (reflectivity) vs ffw (QPE). Pass in full names
        state_borders (bool): Draws state borders in white. Useful for testing, unnecessary for 
                    the warning graphics
    """
    #  Download and Decompress 
    ref_url = "https://mrms.ncep.noaa.gov/2D/ReflectivityAtLowestAltitude/MRMS_ReflectivityAtLowestAltitude.latest.grib2.gz"
    qpe1hr_url = "https://mrms.ncep.noaa.gov/2D/RadarOnly_QPE_01H/MRMS_RadarOnly_QPE_01H.latest.grib2.gz" #past 1 hour, updated every 2min, with a 4-5min lag
    qpe3hr_url = "https://mrms.ncep.noaa.gov/2D/RadarOnly_QPE_03H/MRMS_RadarOnly_QPE_03H.latest.grib2.gz" #past 3 hours (only updated at the top of every hour???? better data but thats not great)
    
    if type == "Flash Flood Warning":
        url = qpe1hr_url
        convert_units = True
        print("QPE")
        cmap_to_use = qpe2_cmap
        data_min, data_max = min_val3, max_val3
        cbar_label = "Radar Estimated Precipitation (1h)"
    else:
        url = ref_url
        convert_units = False
        print("REF")
        cmap_to_use = radarscope_cmap
        data_min, data_max = min_dbz, max_dbz
        cbar_label = "Reflectivity (dBZ)"
        
    print(f"Fetching data from {url}")    
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        grib_content = gzip.decompress(response.content)
        with open("latest.grib2", "wb") as f:
            f.write(grib_content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading data: {e}")
        return

    # 2. Load and Subset the Data
    print("Reading and subsetting data...")
    ds = xr.open_dataset("latest.grib2", engine="cfgrib")
    
    # slice dataset to just bounding box we care about (faster)
    lon_slice = slice(
        bbox['lon_min'] + 360 if bbox['lon_min'] < 0 else bbox['lon_min'],
        bbox['lon_max'] + 360 if bbox['lon_max'] < 0 else bbox['lon_max']
    )
    lat_slice = slice(bbox['lat_max'], bbox['lat_min'])

    subset = ds.sel(latitude=lat_slice, longitude=lon_slice)

    # Check if the subset is empty
    if subset.unknown.size == 0:
        print("Error: Data subset is empty. Check your bounding box coordinates.")
        os.remove("latest.grib2")
        return
    
    if convert_units: #so it scales correctly
        subset['unknown'] = subset['unknown'] / 25.4
        print("units converted")
        
    print(f"min: {subset.unknown.min().item()}, max: {subset.unknown.max().item()}")
        
    # create the Plot
    print("Generating plot...")
    fig = plt.figure(figsize=(10, 8))
    proj = ccrs.LambertConformal(central_longitude=(bbox['lon_min']), central_latitude=(bbox['lat_min'])) #should try finding middle of bbox for this
    ax = fig.add_subplot(1, 1, 1, projection=proj)

    # Set map extent to the bounding box
    ax.set_extent(
        [bbox['lon_min'], bbox['lon_max'], bbox['lat_min'], bbox['lat_max']], 
        crs=ccrs.PlateCarree()
    )
    
    # only add state borders if needed
    if state_borders:
        ax.add_feature(cfeature.STATES.with_scale('50m'), linestyle='-', edgecolor='white')

    # Plot the some mrms data
    im = ax.pcolormesh(
        subset.longitude, subset.latitude, subset.unknown,
        transform=ccrs.PlateCarree(),
        cmap=cmap_to_use, vmin= data_min, vmax=data_max
    )
    
    #add colorbar
    cbar = plt.colorbar(im, orientation = 'vertical', pad=-0.1, aspect=20,  #you can add location='left' before orientation if you want to shift the colorbar to the other side
                        shrink = 0.50)
    cbar.set_label(cbar_label, color="#7a7a7a", fontsize=12, weight='bold')

    # save figure
    valid_time = ds.time.dt.strftime('%Y-%m-%d %H:%M:%S UTC').item()
    valid_time_short = ds.time.dt.strftime('%H:%M UTC').item() #for showing on the graphic
    output_path = (f'mrms_stuff/{valid_time}_{cbar_label}.png'.replace(" ", "_").replace(":", "")) #filenames cant have ":", replace with a space
    print(f"Saving image to {output_path}...")
    plt.savefig(
        output_path,
        dpi=600,                  # Adjust for resolution
        transparent=True,         # Transparent background
        bbox_inches='tight',      # Remove whitespace padding
        pad_inches=0              # Remove padding
    )
    print(valid_time)
    
    plt.close(fig) # Close the figure to free up memory
    os.remove("latest.grib2")
    os.remove("latest.grib2.5b7b6.idx") # Clean up the downloaded files
    print(f"MRMS image saved.")
    return valid_time_short, output_path

def get_mrms_data(bbox, type):
    """
    Fetches and subsets the latest MRMS data.

    Returns:
        A tuple containing the subsetted xarray dataset, the appropriate colormap,
        vmin, vmax, colorbar label, and the valid time string.
    """
    ref_url = "https://mrms.ncep.noaa.gov/2D/ReflectivityAtLowestAltitude/MRMS_ReflectivityAtLowestAltitude.latest.grib2.gz"
    qpe1hr_url = "https://mrms.ncep.noaa.gov/2D/RadarOnly_QPE_01H/MRMS_RadarOnly_QPE_01H.latest.grib2.gz"
    grib_file = 'latest.grib2'
    try:
        if type == "Flash Flood Warning":
            url = qpe1hr_url
            convert_units = True
            cmap_to_use = qpe2_cmap
            data_min, data_max = min_val3, max_val3
            cbar_label = "Radar Estimated Precipitation (1h)"
        else:
            url = ref_url
            convert_units = False
            cmap_to_use = radarscope_cmap
            data_min, data_max = min_dbz, max_dbz
            cbar_label = "Reflectivity (dBZ)"
        
        print(f"Fetching data from {url}")
        # Download and write file
        response = requests.get(url, timeout=30)
        response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
        grib_content = gzip.decompress(response.content)
        with open(grib_file, "wb") as f:
            f.write(grib_content)

        # Open dataset with xarray
        # The decode_timedelta=False argument silences the FutureWarning
        ds = xr.open_dataset(grib_file, engine="cfgrib", backend_kwargs={'decode_timedelta': False})

        # Subset data
        lon_slice = slice(bbox['lon_min'] + 360, bbox['lon_max'] + 360)
        lat_slice = slice(bbox['lat_max'], bbox['lat_min'])
        subset = ds.sel(latitude=lat_slice, longitude=lon_slice)

        if subset.unknown.size == 0:
            print("Error: Data subset is empty.")
            return None, None, None, None, None, None
        
        if convert_units:
            subset['unknown'] = subset['unknown'] / 25.4

        valid_time_short = ds.time.dt.strftime('%H:%M UTC').item()
        ds.close()

        return subset, cmap_to_use, data_min, data_max, cbar_label, valid_time_short

    except Exception as e:
        # Catch any exception during download, write, or read
        print(f"An error occurred in get_mrms_data: {e}")
        return None, None, None, None, None, None

    finally:
        # This block ALWAYS runs, ensuring files are cleaned up
        if os.path.exists(grib_file):
            print(" i")
            #os.remove(grib_file)
        # Use glob to find and remove any matching index files
        for idx_file in glob.glob(f"{grib_file}*.idx"):
            if os.path.exists(idx_file):
                os.remove(idx_file)


if __name__ == '__main__':
    # Define a bounding box for the Ohio region
    cincy_bbox = { #this is the area that is being scanned for alerts as well
        "lon_min": -85.413208,
        "lon_max": -83.161011,
        "lat_min": 38.522384,
        "lat_max": 40.155786
    }
    test_bbox = {
        "lon_min": -97,
        "lon_max": -92,
        "lat_min": 34,
        "lat_max": 37
    }

    save_mrms_subset(test_bbox, "Flash Flood Warning", True)