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
from plot_mrms2 import save_mrms_subset

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

def get_nws_alerts():
    try:
        response = requests.get(NWS_ALERTS_URL, headers={"User-Agent": "weather-alert-bot"})
        response.raise_for_status()
        alerts = response.json().get("features", [])
        print(f"Fetched {len(alerts)} total alerts from NWS")

        filtered_alerts = []
        for alert in alerts:
            properties = alert["properties"]
            event_type = properties.get("event")
            affected_zones = properties.get("geocode", {}).get("UGC", [])

            if event_type in ["Tornado Warning", "Severe Thunderstorm Warning", "Beach Hazards Statement", "Special Weather Statement"] and any(zone in AREA_FILTERS for zone in affected_zones):
                print(f"Matching alert found: {event_type}, Zones: {affected_zones}")
                filtered_alerts.append(alert)

        print(f"Returning {len(filtered_alerts)} filtered alerts")
        return filtered_alerts
    except requests.RequestException as e:
        print(f"Error fetching NWS alerts: {e}")
        return []
    

test_alert = {
            "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -80.28,
                            26.77
                        ],
                        [
                            -80.44,
                            26.7399999
                        ],
                        [
                            -80.53,
                            26.96
                        ],
                        [
                            -80.2,
                            26.96
                        ],
                        [
                            -80.15,
                            26.82
                        ],
                        [
                            -80.28,
                            26.77
                        ]
                    ]
                ]
            },
            "properties": {
                "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "@type": "wx:Alert",
                "id": "urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "areaDesc": "Palm Beach, FL",
                "geocode": {
                    "SAME": [
                        "012099"
                    ],
                    "UGC": [
                        "FLC099"
                    ]
                },
                "affectedZones": [
                    "https://api.weather.gov/zones/county/FLC099"
                ],
                "references": [],
                "sent": "2025-05-23T15:26:00-04:00",
                "effective": "2025-05-23T15:26:00-04:00",
                "onset": "2025-05-23T15:26:00-04:00",
                "expires": "2025-05-23T16:00:00-04:00",
                "ends": "2025-05-23T16:00:00-04:00",
                "status": "Actual",
                "messageType": "Alert",
                "category": "Met",
                "severity": "Severe",
                "certainty": "Observed",
                "urgency": "Immediate",
                "event": "Severe Thunderstorm Warning",
                "sender": "w-nws.webmaster@noaa.gov",
                "senderName": "NWS Miami FL",
                "headline": "Severe Thunderstorm Warning issued May 23 at 3:26PM EDT until May 23 at 4:00PM EDT by NWS Miami FL",
                "description": "SVRMFL\n\nThe National Weather Service in Miami has issued a\n\n* Severe Thunderstorm Warning for...\nNortheastern Palm Beach County in southeastern Florida...\n\n* Until 400 PM EDT.\n\n* At 326 PM EDT, a severe thunderstorm was located near Indiantown,\nmoving southeast at 20 mph.\n\nHAZARD...Ping pong ball size hail and 60 mph wind gusts.\n\nSOURCE...Radar indicated.\n\nIMPACT...People and animals outdoors will be injured. Expect hail\ndamage to roofs, siding, windows, and vehicles. Expect\nwind damage to roofs, siding, and trees.\n\n* Locations impacted include...\nWest Palm Beach, Palm Beach Gardens, North County Airport, The\nAcreage, Caloosa, and Jupiter Farms.",
                "instruction": "Remain alert for a possible tornado! Tornadoes can develop quickly\nfrom severe thunderstorms. If you spot a tornado go at once into a\nsmall central room in a sturdy structure.\n\nFor your protection move to an interior room on the lowest floor of a\nbuilding.",
                "response": "Shelter",
                "parameters": {
                    "AWIPSidentifier": [
                        "SVRMFL"
                    ],
                    "WMOidentifier": [
                        "WUUS52 KMFL 231926"
                    ],
                    "eventMotionDescription": [
                        "2025-05-23T19:26:00-00:00...storm...323DEG...16KT...26.97,-80.42"
                    ],
                    "windThreat": [
                        "RADAR INDICATED"
                    ],
                    "maxWindGust": [
                        "60 MPH"
                    ],
                    "hailThreat": [
                        "OBSERVED"
                    ],
                    "maxHailSize": [
                        "1.50"
                    ],
                    "tornadoDetection": [
                        "POSSIBLE"
                    ],
                    "thunderstormDamageThreat": [
                      "DESTRUCTIVE"  
                    ],
                    "BLOCKCHANNEL": [
                        "EAS",
                        "NWEM",
                        "CMAS"
                    ],
                    "EAS-ORG": [
                        "WXR"
                    ],
                    "VTEC": [
                        "/O.NEW.KMFL.SV.W.0047.250523T1926Z-250523T2000Z/"
                    ],
                    "eventEndingTime": [
                        "2025-05-23T16:00:00-04:00"
                    ]
                },
                "scope": "Public",
                "code": "IPAWSv1.0",
                "language": "en-US",
                "web": "http://www.weather.gov",
                "eventCode": {
                    "SAME": [
                        "SVR"
                    ],
                    "NationalWeatherService": [
                        "SVW"
                    ]
                }
            }
        }

test_alert2 = { #cincy one
            "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -84.41,
                            39.26
                        ],
                        [
                            -84.33,
                            39.16
                        ],
                        [
                            -84.36,
                            39.04
                        ],
                        [
                            -84.62,
                            39.02
                        ],
                        [
                            -84.59,
                            39.13
                        ],
                        [
                            -84.62,
                            39.23
                        ]
                    ]
                ]
            },
            "properties": {
                "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "@type": "wx:Alert",
                "id": "urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "areaDesc": "Cincinnati, OH",
                "geocode": {
                    "SAME": [
                        "012099"
                    ],
                    "UGC": [
                        "OHZ077"
                    ]
                },
                "affectedZones": [
                    "https://api.weather.gov/zones/county/OHZ077"
                ],
                "references": [],
                "sent": "2025-05-24T15:26:00-04:00",
                "effective": "2025-05-24T15:26:00-04:00",
                "onset": "2025-05-24T15:26:00-04:00",
                "expires": "2025-05-24T16:00:00-04:00",
                "ends": "2025-05-24T16:00:00-04:00",
                "status": "Actual",
                "messageType": "Alert",
                "category": "Met",
                "severity": "Severe",
                "certainty": "Observed",
                "urgency": "Immediate",
                "event": "Severe Thunderstorm Warning",
                "sender": "w-nws.webmaster@noaa.gov",
                "senderName": "NWS Wilmington OH",
                "headline": "Severe Thunderstorm Warning issued May 24 at 3:26PM EDT until May 24 at 4:00PM EDT by NWS Wilmington OH",
                "description": "SVRMFL\n\nThe National Weather Service in Wilmington has issued a\n\n* Severe Thunderstorm Warning for...\nNortheastern Palm Beach County in southeastern Florida...\n\n* Until 400 PM EDT.\n\n* At 326 PM EDT, a severe thunderstorm was located near Indiantown,\nmoving southeast at 20 mph.\n\nHAZARD...Ping pong ball size hail and 60 mph wind gusts.\n\nSOURCE...Radar indicated.\n\nIMPACT...People and animals outdoors will be injured. Expect hail\ndamage to roofs, siding, windows, and vehicles. Expect\nwind damage to roofs, siding, and trees.\n\n* Locations impacted include...\nWest Palm Beach, Palm Beach Gardens, North County Airport, The\nAcreage, Caloosa, and Jupiter Farms.",
                "instruction": "Remain alert for a possible tornado! Tornadoes can develop quickly\nfrom severe thunderstorms. If you spot a tornado go at once into a\nsmall central room in a sturdy structure.\n\nFor your protection move to an interior room on the lowest floor of a\nbuilding.",
                "response": "Shelter",
                "parameters": {
                    "AWIPSidentifier": [
                        "SVRMFL"
                    ],
                    "WMOidentifier": [
                        "WUUS52 KMFL 231926"
                    ],
                    "eventMotionDescription": [
                        "2025-05-23T19:26:00-00:00...storm...323DEG...16KT...26.97,-80.42"
                    ],
                    "windThreat": [
                        "RADAR INDICATED"
                    ],
                    "maxWindGust": [
                        "90 MPH"
                    ],
                    "thunderstormDamageThreat": [
                        "DESTRUCTIVE"
                    ],
                    "hailThreat": [
                        "OBSERVED"
                    ],
                    "maxHailSize": [
                        "4.50"
                    ],
                    "tornadoDetection": [
                        "POSSIBLE"
                    ],
                    "BLOCKCHANNEL": [
                        "EAS",
                        "NWEM",
                        "CMAS"
                    ],
                    "EAS-ORG": [
                        "WXR"
                    ],
                    "VTEC": [
                        "/O.NEW.KMFL.SV.W.0047.250523T1926Z-250523T2000Z/"
                    ],
                    "eventEndingTime": [
                        "2025-05-23T16:00:00-04:00"
                    ]
                },
                "scope": "Public",
                "code": "IPAWSv1.0",
                "language": "en-US",
                "web": "http://www.weather.gov",
                "eventCode": {
                    "SAME": [
                        "SVR"
                    ],
                    "NationalWeatherService": [
                        "SVW"
                    ]
                }
            }
        }

test_alert3 = { #north burbs one
            "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -84.064,
                            39.500091
                        ],
                        [
                            -84.03168,
                            39.30133
                        ],
                        [
                            -84.38873,
                            39.30133
                        ],
                        [
                            -84.41620,
                            39.29907
                        ],
                        [
                            -84.39514,
                            39.42216
                        ]
                    ]
                ]
            },
            "properties": {
                "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "@type": "wx:Alert",
                "id": "urn:oid:2.49.0.1.840.0.4b4047b48b827b1700a30d1222ab3d671c5072ea.001.1",
                "areaDesc": "Cincinnati, OH",
                "geocode": {
                    "SAME": [
                        "012099"
                    ],
                    "UGC": [
                        "OHZ077"
                    ]
                },
                "affectedZones": [
                    "https://api.weather.gov/zones/county/OHZ077"
                ],
                "references": [],
                "sent": "2025-05-24T15:26:00-04:00",
                "effective": "2025-05-24T15:26:00-04:00",
                "onset": "2025-05-24T15:26:00-04:00",
                "expires": "2025-05-24T16:00:00-04:00",
                "ends": "2025-05-24T16:00:00-04:00",
                "status": "Actual",
                "messageType": "Alert",
                "category": "Met",
                "severity": "Severe",
                "certainty": "Observed",
                "urgency": "Immediate",
                "event": "Tornado Warning",
                "sender": "w-nws.webmaster@noaa.gov",
                "senderName": "NWS Wilmington OH",
                "headline": "Severe Thunderstorm Warning issued May 24 at 3:26PM EDT until May 24 at 4:00PM EDT by NWS Wilmington OH",
                "description": "SVRMFL\n\nThe National Weather Service in Wilmington has issued a\n\n* Severe Thunderstorm Warning for...\nNortheastern Palm Beach County in southeastern Florida...\n\n* Until 400 PM EDT.\n\n* At 326 PM EDT, a severe thunderstorm was located near Indiantown,\nmoving southeast at 20 mph.\n\nHAZARD...Ping pong ball size hail and 60 mph wind gusts.\n\nSOURCE...Radar indicated.\n\nIMPACT...People and animals outdoors will be injured. Expect hail\ndamage to roofs, siding, windows, and vehicles. Expect\nwind damage to roofs, siding, and trees.\n\n* Locations impacted include...\nWest Palm Beach, Palm Beach Gardens, North County Airport, The\nAcreage, Caloosa, and Jupiter Farms.",
                "instruction": "Remain alert for a possible tornado! Tornadoes can develop quickly\nfrom severe thunderstorms. If you spot a tornado go at once into a\nsmall central room in a sturdy structure.\n\nFor your protection move to an interior room on the lowest floor of a\nbuilding.",
                "response": "Shelter",
                "parameters": {
                    "AWIPSidentifier": [
                        "SVRMFL"
                    ],
                    "WMOidentifier": [
                        "WUUS52 KMFL 231926"
                    ],
                    "eventMotionDescription": [
                        "2025-05-23T19:26:00-00:00...storm...323DEG...16KT...26.97,-80.42"
                    ],
                    "hailThreat": [
                        "OBSERVED"
                    ],
                    "maxHailSize": [
                        "1.00"
                    ],
                    "tornadoDamageThreat": [
                      "CATASTROPHIC"  
                    ],
                    "tornadoDetection": [
                        "OBSERVED"
                    ],
                    "BLOCKCHANNEL": [
                        "EAS",
                        "NWEM",
                        "CMAS"
                    ],
                    "EAS-ORG": [
                        "WXR"
                    ],
                    "VTEC": [
                        "/O.NEW.KMFL.SV.W.0047.250523T1926Z-250523T2000Z/"
                    ],
                    "eventEndingTime": [
                        "2025-05-23T16:00:00-04:00"
                    ]
                },
                "scope": "Public",
                "code": "IPAWSv1.0",
                "language": "en-US",
                "web": "http://www.weather.gov",
                "eventCode": {
                    "SAME": [
                        "SVR"
                    ],
                    "NationalWeatherService": [
                        "SVW"
                    ]
                }
            }
        }
test_alert4 =  { #ffw
            "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.cd9fca696e509c734f6e0628e089c15e84b7d00c.001.1",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -84.46289,
                            39.118
                        ],
                        [
                            -84.438,
                            39.07933
                        ],
                        [
                            -84.31732,
                            39.11132
                        ],
                        [
                            -84.21021,
                            39.19654
                        ],
                        [
                            -84.21661,
                            39.29605
                        ],
                        [
                            -84.20471,
                            39.40704
                        ],
                        [
                            -84.26102,
                            39.42296
                        ],
                        [
                            -84.30496,
                            39.42296
                        ],
                        [
                            -84.3132,
                            39.2859
                        ],
                        [
                            -84.31732,
                            39.23061
                        ],
                        [
                            -84.44092,
                            39.14116
                        ],
                        [
                            -84.45282,
                            39.12011
                        ],
                        [
                            -84.45190,
                            39.14329
                        ]
                    ]
                ]
            },
            "properties": {
                "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.cd9fca696e509c734f6e0628e089c15e84b7d00c.001.1",
                "@type": "wx:Alert",
                "id": "urn:oid:2.49.0.1.840.0.cd9fca696e509c734f6e0628e089c15e84b7d00c.001.1",
                "areaDesc": "Loveland, OH",
                "geocode": {
                    "SAME": [
                        "035047"
                    ],
                    "UGC": [
                        "NMC047"
                    ]
                },
                "affectedZones": [
                    "https://api.weather.gov/zones/county/NMC047"
                ],
                "references": [
                    {
                        "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.502bb0376969acc429253a3c33af73ed1323a594.001.1",
                        "identifier": "urn:oid:2.49.0.1.840.0.502bb0376969acc429253a3c33af73ed1323a594.001.1",
                        "sender": "w-nws.webmaster@noaa.gov",
                        "sent": "2025-06-09T12:54:00-06:00"
                    },
                    {
                        "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.97f4f3a2c4916c4f559d3b2473874e48db4ca309.001.1",
                        "identifier": "urn:oid:2.49.0.1.840.0.97f4f3a2c4916c4f559d3b2473874e48db4ca309.001.1",
                        "sender": "w-nws.webmaster@noaa.gov",
                        "sent": "2025-06-09T13:51:00-06:00"
                    }
                ],
                "sent": "2025-06-09T15:14:00-06:00",
                "effective": "2025-06-09T15:14:00-06:00",
                "onset": "2025-06-09T15:14:00-06:00",
                "expires": "2025-06-09T16:00:00-06:00",
                "ends": "2025-06-09T16:00:00-06:00",
                "status": "Actual",
                "messageType": "Update",
                "category": "Met",
                "severity": "Severe",
                "certainty": "Likely",
                "urgency": "Immediate",
                "event": "Flash Flood Warning",
                "sender": "w-nws.webmaster@noaa.gov",
                "senderName": "NWS Wilmington OH",
                "headline": "Flash Flood Warning issued June 9 at 3:14PM MDT until June 9 at 4:00PM MDT by NWS Albuquerque NM",
                "description": "At 314 PM MDT, Doppler radar indicated thunderstorms producing heavy\nrain over the Hermits Peak and Calf Canyon Burn Scar. Between 1 and\n1.5 inches of rain have fallen. Flash flooding is ongoing or\nexpected to begin shortly.\n\nExcessive rainfall over the burn scar will impact the Tecolote Creek\nand Gallinas River drainage areas. The debris flow can consist of\nrock, mud, vegetation and other loose materials.\n\nHAZARD...Life threatening flash flooding. Thunderstorms producing\nflash flooding in and around the Hermits Peak and Calf\nCanyon Burn Scar.\n\nSOURCE...Radar indicated.\n\nIMPACT...Life threatening flash flooding of areas in and around\nthe Hermits Peak and Calf Canyon Burn Scar.\n\nSome locations that will experience flash flooding include...\nEl Porvenir, Montezuma, Sapello, Tierra Monte, Gallinas, Mineral\nHill, Rociada, Manuelitas and San Geronimo.",
                "instruction": "This is a life threatening situation. Heavy rainfall will cause\nextensive and severe flash flooding of creeks, streams and ditches\nin the Hermits Peak and Calf Canyon Burn Scar. Severe debris flows\ncan also be anticipated across roads. Roads and driveways may be\nwashed away in places. If you encounter flood waters, climb to\nsafety.\n\nBe aware of your surroundings and do not drive on flooded roads.",
                "response": "Avoid",
                "parameters": {
                    "AWIPSidentifier": [
                        "FFSABQ"
                    ],
                    "WMOidentifier": [
                        "WGUS75 KABQ 092114"
                    ],
                    "NWSheadline": [
                        "FLASH FLOOD WARNING FOR THE HERMITS PEAK AND CALF CANYON BURN SCAR REMAINS IN EFFECT UNTIL 4 PM MDT THIS AFTERNOON FOR NORTHWESTERN SAN MIGUEL COUNTY"
                    ],
                    "flashFloodDetection": [
                        "RADAR INDICATED"
                    ],
                    "flashFloodDamageThreat": [
                        "CONSIDERABLE"
                    ],
                    "BLOCKCHANNEL": [
                        "EAS",
                        "NWEM",
                        "CMAS"
                    ],
                    "EAS-ORG": [
                        "WXR"
                    ],
                    "VTEC": [
                        "/O.CON.KABQ.FF.W.0031.000000T0000Z-250609T2200Z/"
                    ],
                    "eventEndingTime": [
                        "2025-06-09T16:00:00-06:00"
                    ]
                },
                "scope": "Public",
                "code": "IPAWSv1.0",
                "language": "en-US",
                "web": "http://www.weather.gov",
                "eventCode": {
                    "SAME": [
                        "FFS"
                    ],
                    "NationalWeatherService": [
                        "FFW"
                    ]
                }
            }
        }

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
        map_region2 = { #for the mrms stuff
            "lon_min": minx,
            "lon_max": maxx,
            "lat_min": miny,
            "lat_max": maxy
        }
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
        #TESTING!!
        radar_valid_time = save_mrms_subset(map_region2, alert_type, False)
        
        
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
        ax.text(0.80, 0.97, f"Radar data valid {radar_valid_time}", #radar time
                transform=ax.transAxes, ha='left', va='bottom', 
                fontsize=7, backgroundcolor="#eeeeeecc")
        
        #draw radar data in bg
        mrms_img = mpimg.imread('mrms_stuff/test0.png') #need to update this to be a relative, changing location not a fixed 1!!!
        ax.imshow(mrms_img, origin = 'upper', extent = map_region, transform = ccrs.PlateCarree(), zorder = 2)
        
        # Draw the polygon
        if geom.geom_type == 'Polygon':
            if alert_type == "Severe Thunderstorm Warning":
                x, y = geom.exterior.xy
                ax.plot(x, y, color='black', linewidth=2, transform=ccrs.PlateCarree(), zorder = 1)
                ax.fill(x, y, facecolor='#ffff0050')
            elif alert_type == 'Tornado Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='red', linewidth=2, transform=ccrs.PlateCarree(), zorder = 1)
                ax.fill(x, y, facecolor="#ff000050")
            elif alert_type == 'Flash Flood Warning':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='green', linewidth=2, transform=ccrs.PlateCarree(), zorder = 1)
                ax.fill(x, y, facecolor = "#00ff2f50", zorder = 1)
            else:
                x, y = geom.exterior.xy
                ax.plot(x, y, color="#414141", linewidth=2, transform=ccrs.PlateCarree(), zorder = 1)
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
        desc = alert['properties'].get('description', ['n/a'])#[7:] #long text, removing the "SVRILN" or "TORILN" thing at the start, except that isnt present on all warnings so i took it out...
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