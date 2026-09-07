## Cincy weather domain
# --- API POLLING SETTINGS ---
# Define categories for alert types
from insta_alert.utils.constants import SEVERE, WATCHES, WINTER, OTHER, ALL
from dotenv import load_dotenv
import os
from pathlib import Path
cwd = Path(os.getcwd())
env_path = cwd / ".env"
load_dotenv(env_path)
ALERT_TYPES_TO_MONITOR = (
    ALL
)
LOG_FILE = 'logs/posted_alerts_cincy.log'
# --- BOUNDING ZONES --- 
#use https://api.weather.gov/zones?type=county search to find county codes. best source.

CINCY_ZONES = [
    # forecast zones
    'OHZ078', 'OHZ079', 'OHZ080', 'OHZ081', 'OHZ077', 'OHZ070', 'OHZ071', 'OHZ072', 'OHZ060', 'OHZ061', 'OHZ062', 'INZ066', 'INZ074', 'INZ075', 'KYZ091', 'KYZ092', 'KYZ093',
    # county codes
    'OHC025', 'OHC015', 'OHC071', 'OHC001', 'OHC061', 'OHC017', 'OHC165', 'OHC027', 'OHC135', 'OHC113', 'OHC057', 'INC047', 'INC029', 'INC115', 'KYC015', 'KYC117', 'KYC037'
    # clermont, brown, highland, adams, hamilton, butler, warren, clinton, preble, montgomery, greene, franklin, dearborn, ohio, boone, kenton, campbell
]
MMWX_ZONES = [
  'MIZ039', 'MIZ040', 'MIZ041', 'MIZ044', 'MIZ045', 'MIZ046', 'MIZ047', 'MIZ048', 'MIZ057', 'MIZ051', 'MIZ052', 'MIZ053', 'MIZ050', 'MIZ056', 'MIZ058', 'MIZ059', 'MIZ060', 'MIZ061', 'MIZ062', 'MIZ064', 'MIZ065', 'MIZ066', 'MIZ067', 'MIZ068', 'MIZ069', 'MIZ072', 'MIZ073', 'MIZ074', 'MIZ075','LMZ845', 'LMZ846', 'LMZ847', 'LMZ876', 'LMZ874', 'LMZ872', 'LHZ422', 'LHZ421'
]
EVERYWHERE = False #polls for all alerts, ignores the active_zones flag
ACTIVE_ZONES = CINCY_ZONES #counties are w/ a C, marine zones w/ a Z

# --- PREFS ---
POST_ZONE_SPS = False #BOOL; gets kinda annoying, they are like by definition things not high enough priority to warrant the "real" thing, whether that be a DFA, WWA, etc. 
USE_NEXRAD = "LEVEL2"  # "LEVEL2", "LEVEL3", or False for MRMS
NEXRAD_SMOOTHING = False

# --- TARGETS ---
# Set to True to enable posting, False to disable
OUTPUT_DIR = 'graphics/cincy' #should be graphics/something
POST_TO_FACEBOOK = True
POST_TO_DISCORD = True
POST_TO_INSTAGRAM_GRID = True
POST_TO_INSTAGRAM_STORY = False
SEND_TO_SLIDESHOW = False 
# A list of Discord webhook URLs to send alerts to
WEBHOOKS = [os.getenv('CINCYWX_DISCORD_WEBHOOK')]

# --- CAPTION ---
DEFAULT_TAGS = '#cincywx #wx #weatheralert'
USE_TAGS = True
