# --- API POLLING SETTINGS ---
# Define categories for alert types
SEVERE = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning']
OTHER = ['Special Weather Statement', 'Flood Advisory', 'Special Marine Warning', 'Dust Storm Warning', 'Dense Fog Advisory', 'High Wind Warning']
WINTER = ['Winter Storm Warning', 'Frost Advisory', 'Freeze Warning']
WATCHES = ['Tornado Watch', 'Severe Thunderstorm Watch', 'Flood Watch', 'Flash Flood Watch']

ALERT_TYPES_TO_MONITOR = (
    "Special Weather Statement"
)
# --- BOUNDING ZONES --- 
#use https://api.weather.gov/zones?type=county search to find county codes. best source.
#TODO: update these to be UGC codes (with a Z) so like State abbreviation + Z + ### 
#TODO: actually, I'm not sure if i want to do that, need more looking into. how did it get any cincy alerts if these had C's,
# and the affected zones got in main.py had Z's?
OLD_CINCY_ZONES = [ #clermont, brown, adams, highland, hamilton, warren, butler, clinton, franklin IN, dearborn IN, ohio IN, boone ky, kenton ky, campbell ky
  'OHC025', 'OHC015', 'OHC001', 'OHC071', 'OHC061', 'OHC165', 'OHC017', 'OHC027', 'INC047', 'INC029', 'INC115', 'KYC015', 'KYC117', 'KYC037']
OLD_MMWX_ZONES = [#probably don't use - see the todos above #IN A TO Z order kalamazoo, calhoun, jackson, washtenaw, oakland, livingston, ingham, eaton, barry, allegan, ottawa, kent, ionia, clinton, shiawassee, genesse, lapeer, saginaw, gratiot, montcalm, newaygo, muskegon, mecosta, isabella, midland, bay, gladwin, clare, osceola, lake zones
  "MIC005", "MIC015", "MIC025", "MIC037", "MIC045", "MIC049", "MIC051", "MIC057", "MIC065", "MIC067", "MIC073", "MIC075", "MIC081", "MIC111", "MIC117", "MIC121", "MIC123", "MIC125", "MIC139", "MIC143", "MIC155", "MIC161", 'LMZ845', 'LMZ846', 'LMZ847', 'LMZ876', 'LMZ874', 'LMZ872', 'LHZ422', 'LHZ421'
]

CINCY_ZONES = [
  'OHZ078', 'OHZ079', 'OHZ079', 'OHZ080', 'OHZ077', 'OHZ071', 'OHZ070', 'OHZ072', 'INZ066', 'INZ074', 'INZ075', 'KY091', 'KY092', 'KY093'
]
MMWX_ZONES = [
  'MIZ039', 'MIZ040', 'MIZ041', 'MIZ044', 'MIZ045', 'MIZ046', 'MIZ047', 'MIZ048', 'MIZ057', 'MIZ051', 'MIZ052', 'MIZ053', 'MIZ050', 'MIZ056', 'MIZ058', 'MIZ059', 'MIZ060', 'MIZ061', 'MIZ062', 'MIZ064', 'MIZ065', 'MIZ066', 'MIZ067', 'MIZ068', 'MIZ069', 'MIZ072', 'MIZ073', 'MIZ074', 'MIZ075','LMZ845', 'LMZ846', 'LMZ847', 'LMZ876', 'LMZ874', 'LMZ872', 'LHZ422', 'LHZ421'
]
EVERYWHERE = True #polls for all alerts, ignores the active_zones flag
ACTIVE_ZONES = MMWX_ZONES #counties are w/ a C, marine zones w/ a Z

# --- TARGETS ---
# Set to True to enable posting, False to disable
POST_TO_FACEBOOK = False
POST_TO_DISCORD = False
POST_TO_INSTAGRAM_GRID = False
POST_TO_INSTAGRAM_STORY = False
SEND_TO_SLIDESHOW = False 
# A list of Discord webhook URLs to send alerts to
DISCORD_PINGS_ALL = ['1427050976732254300'] #role to mention for all errors
ERROR_WEBHOOK = 'https://discord.com/api/webhooks/1427040206476808334/N3MzXEbasGKIcFcQ5bJZtQ3sExmzGp1Z-lFBxXXbK2MGe7FkdQtphwR0qleTP8lejZkn'
new_logs = 'https://discord.com/api/webhooks/1410375879305068605/KozzDWwx4tZGqOZFf5iUzw7bdXviILfgwkz1ggh0ujDlHjOWT9U_GnoCtklzWt7JPQaU'
cincy_wx = 'https://discord.com/api/webhooks/1419354620676804748/womab2v6YAhHcNoVtpq3USTqBbJ4uuA0O9vgWWnjo4UmIj-Wcz_EZ4VpJwEGmnX-Z5P7'
WEBHOOKS = [new_logs]

# --- CAPTION ---
DEFAULT_TAGS = '#weather #weatheralert #stayalert #wx'
USE_TAGS = True

# ---- COLORS ----
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
    'Dense Fog Advisory': {
        'facecolor': "#708090",
        'edgecolor': "#565F68",
        'fillalpha': '50'
    },
    'Freeze Warning': {
        'facecolor': "#5E54A5",
        'edgecolor': "#483D8B",
        'fillalpha': '50'
    },
    'Frost Advisory': {
        'facecolor': "#73A0F3",
        'edgecolor': "#437DEA",
        'fillalpha': '50'
    },
    'Winter Storm Warning': {
        'facecolor': "#FF69B4",
        'edgecolor': "#FF69B4",
        'fillalpha': '50'
    },
    'High Wind Warning':{
        'facecolor': '#DAA520',
        'edgecolor': '#DAA520',
        'fillalpha': '50'
    },
    "default": {
        "facecolor": "#b7b7b7", # grey
        "edgecolor": "#414141", # dark grey
        "fillalpha": "50"
    }
}