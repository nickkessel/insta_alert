

# --- API POLLING SETTINGS ---
# Define categories for alert types
SEVERE = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning']
OTHER = ['Special Weather Statement', 'Flood Advisory', 'Special Marine Warning', 'Dust Storm Warning']
WATCHES = ['Tornado Watch', 'Severe Thunderstorm Watch', 'Flood Watch', 'Flash Flood Watch']
# comment out a list to exclude it
WARNING_TYPES_TO_MONITOR = (
    SEVERE + OTHER + WATCHES
)
# --- BOUNDING BOXES --- 
#figure out how to do like polygons or just have a list of counties

CINCY_BBOX = {
    "lon_min": -85.124817,
    "lon_max": -83.364258,
    "lat_min": 38.736946,
    "lat_max": 39.664914
}

'''
MMWX_BBOX = { #this isnt formatted right, but this is the FA 
     [
        -83.5420466,
        42.173762
      ],
      [
        -83.5410507,
        42.2052802
      ],
      [
        -83.5533847,
        42.4331114
      ],
      [
        -83.0813059,
        42.4445952
      ],
      [
        -83.1046185,
        42.8885877
      ],
      [
        -82.9836783,
        42.8949575
      ],
      [
        -83.0020026,
        43.2786034
      ],
      [
        -83.119736,
        43.282601
      ],
      [
        -83.1238589,
        43.3215633
      ],
      [
        -83.3492474,
        43.3215633
      ],
      [
        -83.3529122,
        43.2326127
      ],
      [
        -83.4628578,
        43.2176082
      ],
      [
        -83.6951178,
        43.2206094
      ],
      [
        -83.695365,
        43.4085093
      ],
      [
        -83.6907324,
        43.5230654
      ],
      [
        -83.6902178,
        43.573115
      ],
      [
        -83.7184812,
        43.622757
      ],
      [
        -83.8779023,
        43.667459
      ],
      [
        -83.9323371,
        43.7284392
      ],
      [
        -83.947923,
        43.7588678
      ],
      [
        -83.9286763,
        43.7856377
      ],
      [
        -83.9195265,
        43.8193344
      ],
      [
        -83.9044183,
        43.9048189
      ],
      [
        -84.0409882,
        43.9102532
      ],
      [
        -84.0437368,
        43.995245
      ],
      [
        -84.1671719,
        43.9957769
      ],
      [
        -84.1648865,
        44.1582348
      ],
      [
        -84.6070882,
        44.1595472
      ],
      [
        -85.089136,
        44.1622378
      ],
      [
        -85.5646506,
        44.1642074
      ],
      [
        -85.5701478,
        43.8132539
      ],
      [
        -86.0374165,
        43.8125935
      ],
      [
        -86.0284588,
        43.4787959
      ],
      [
        -86.0430895,
        43.4685374
      ],
      [
        -86.0622744,
        43.4692008
      ],
      [
        -86.2088232,
        43.4655135
      ],
      [
        -86.4597792,
        43.4771376
      ],
      [
        -86.495386,
        43.4289819
      ],
      [
        -86.4661207,
        43.3471478
      ],
      [
        -86.449563,
        43.2365349
      ],
      [
        -86.4092455,
        43.2041688
      ],
      [
        -86.3194566,
        43.1056731
      ],
      [
        -86.35977,
        42.903476
      ],
      [
        -86.3488413,
        42.6555127
      ],
      [
        -86.3506613,
        42.4410174
      ],
      [
        -86.1910034,
        42.4187205
      ],
      [
        -85.7647232,
        42.4180242
      ],
      [
        -85.7619684,
        42.0717641
      ],
      [
        -85.2955805,
        42.0703855
      ],
      [
        -84.7082403,
        42.0727874
      ],
      [
        -83.7788136,
        42.0818299
      ],
      [
        -83.5392352,
        42.0865238
      ],
      [
        -83.5420466,
        42.173762
      ]
}
'''
CONUS_BBOX = { #just everywhere
        "lon_min": -175,
        "lon_max": -55,
        "lat_min": 12,
        "lat_max": 72
}

ACTIVE_BBOX = CONUS_BBOX

# --- TARGETS ---
# Set to True to enable posting, False to disable
POST_TO_FACEBOOK = False
POST_TO_DISCORD = False
SEND_TO_SLIDESHOW = False 
# A list of Discord webhook URLs to send alerts to
#'https://discord.com/api/webhooks/1410375879305068605/KozzDWwx4tZGqOZFf5iUzw7bdXviILfgwkz1ggh0ujDlHjOWT9U_GnoCtklzWt7JPQaU' default/'new-logs'
WEBHOOKS = ['https://discord.com/api/webhooks/1419354620676804748/womab2v6YAhHcNoVtpq3USTqBbJ4uuA0O9vgWWnjo4UmIj-Wcz_EZ4VpJwEGmnX-Z5P7']

# --- CAPTION ---
DEFAULT_TAGS = '#weather #weatheralert #stayalert #wx'
USE_TAGS = True