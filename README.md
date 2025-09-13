# warnings_on_fb 
*4,179 (and counting) alerts generated*

---
## What it does:
1. Scrapes the publicly-facing [NWS alerts api](api.weather.gov/alerts/active) for chosen alerts in a chosen bounding box (see [supported alerts](#supported-alerts) and [areas](#supported-areas) for more info)
2. Generates a polygon from the alert geometry
3. Uses open-source GIS tools to add in US highways, interstates, county/state borders, and city names onto the selected map area. 
4. Polls the NCEP MRMS server (unless a recent cached scan is available) and downloads the latest reflectivity (default) or 1hr-QPE (FFW, FFA) data, and overlays that onto the map, for better context. 
5. After the graphic is generated, it can go to any number of end users. Currently supported are sending to a Facebook page and/or Discord server. Also included in the download is the `slideshow.py` file, which uses `pygame` to create an auto-updating slideshow with all active alerts.

## Supported Alerts:
- Tornado Warning
- Severe Thunderstorm Warning
- Flash Flood Warning 
- Special Weather Statement (convective & non-convective)
- Flood Advisory
- Special Marine Warning
- Dust Storm Warning
- Tornado Watch
- Severe Thunderstorm Watch
- Flood Watch
- Flash Flood Watch
## Supported Areas:
- Complete support of CONUS
- Complete support of Puerto Rico
- Partial support of Alaska
    - Known issues with plotting alerts issued for the Aleutians/near the International Date Line
    - Mainland AK seems fine, may need to adjust the Alaska cities dataset to include all locations with pop > 50, rather than pop > 500, for everywhere else.
- Partial support of Hawaii
    - No known issues, but more testing is needed
- Low support of Guam
    - No dataset for Guam cities
    - Can handle plotting Guam alerts
## Tools Used:
```python
 metpy, matplotlib, shapely, cartopy, geopandas, datetime, time, timezonefinder,
 pytz, math, colorama, re, requests, gc, json, gzip, xarray, os, threading, 
 tempfile, discord_webhook, dotenv

```
## Contact:
You can contact me (nick) at [kesse1ni@cmich.edu](mailto:kesse1ni@cmich.edu). 
## Examples:
![img](https://cdn.discordapp.com/attachments/1410438594799206583/1416515387670925397/Alert.png?ex=68c72042&is=68c5cec2&hm=b20622d3cb060b04647bfecf06e74ac3fcfcc54b59c71d09b062da9eb64dbca0& )
![Image](example_graphics/alert_map_mrms11.png) 
![Image](example_graphics/alert_map_mrms13.png) 
![Image](example_graphics/alert_map_mrms12.png)
![Image](example_graphics/watch_example1.png)  