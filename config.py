

# --- API POLLING SETTINGS ---
# Define categories for alert types
SEVERE = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning']
OTHER = ['Special Weather Statement', 'Flood Advisory', 'Special Marine Warning', 'Dust Storm Warning']
WATCHES = ['Tornado Watch', 'Severe Thunderstorm Watch', 'Flood Watch', 'Flash Flood Watch']
# comment out a list to exclude it
WARNING_TYPES_TO_MONITOR = (
     WATCHES
)
# --- BOUNDING BOXES --- 
#figure out how to do like polygons or just have a list of counties

CINCY_BBOX = {
    "lon_min": -85.124817,
    "lon_max": -83.364258,
    "lat_min": 38.736946,
    "lat_max": 39.664914
}

CONUS_BBOX = { #just everywhere
        "lon_min": -175,
        "lon_max": -55,
        "lat_min": 12,
        "lat_max": 72
}
#use https://api.weather.gov/zones?type=county search to find county codes. best source.
CINCY_ZONES = [ #clermont, brown, adams, highland, hamilton, warren, butler, clinton, franklin IN, dearborn IN, ohio IN, boone ky, kenton ky, campbell ky
  'OHC025', 'OHC015', 'OHC001', 'OHC071', 'OHC061', 'OHC165', 'OHC017', 'OHC027', 'INC047', 'INC029', 'INC115', 'KYC015', 'KYC117', 'KYC037']
MMWX_ZONES = [#IN A TO Z order kalamazoo, calhoun, jackson, washtenaw, oakland, livingston, ingham, eaton, barry, allegan, ottawa, kent, ionia, clinton, shiawassee, genesse, lapeer, saginaw, gratiot, montcalm, newaygo, muskegon, mecosta, isabella, midland, bay, gladwin, clare, osceola, lake zones
  "MIC005", "MIC015", "MIC025", "MIC037", "MIC045", "MIC049", "MIC051", "MIC057", "MIC065", "MIC067", "MIC073", "MIC075", "MIC081", "MIC111", "MIC117", "MIC121", "MIC123", "MIC125", "MIC139", "MIC143", "MIC155", "MIC161", 'LMZ845', 'LMZ846', 'LMZ847', 'LMZ876', 'LMZ874', 'LMZ872', 'LHZ422', 'LHZ421'
]
ACTIVE_BBOX = CONUS_BBOX #kinda deprecated
EVERYWHERE = True #polls for all alerts, ignores the active_zones flag
ACTIVE_ZONES = CINCY_ZONES #counties are w/ a C, marine zones w/ a Z
# --- TARGETS ---
# Set to True to enable posting, False to disable
POST_TO_FACEBOOK = False
POST_TO_DISCORD = False
SEND_TO_SLIDESHOW = False 
# A list of Discord webhook URLs to send alerts to
new_logs = 'https://discord.com/api/webhooks/1410375879305068605/KozzDWwx4tZGqOZFf5iUzw7bdXviILfgwkz1ggh0ujDlHjOWT9U_GnoCtklzWt7JPQaU'
cincy_wx = 'https://discord.com/api/webhooks/1419354620676804748/womab2v6YAhHcNoVtpq3USTqBbJ4uuA0O9vgWWnjo4UmIj-Wcz_EZ4VpJwEGmnX-Z5P7'
WEBHOOKS = [new_logs]
# --- CAPTION ---
DEFAULT_TAGS = '#weather #weatheralert #stayalert #wx'
USE_TAGS = True