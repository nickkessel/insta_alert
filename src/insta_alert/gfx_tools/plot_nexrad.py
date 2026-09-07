from datetime import datetime, timezone
from io import BytesIO
from math import asin, cos, isfinite, radians, sin, sqrt
import re
import threading
import time

from colorama import Back, Fore
from matplotlib.colors import LinearSegmentedColormap
from metpy.calc import azimuth_range_to_lat_lon
from metpy.io import Level2File, Level3File
from metpy.units import units
import numpy as np
import requests
from scipy.ndimage import gaussian_filter
import xarray as xr
from requests.exceptions import RequestException
from http.client import IncompleteRead

##
## a good majority of this is AI generated code; i don't have any of my jupyter notebooks from 275 anymore, so i had nothing to ref
## to plot nexrad. at least it works, we can address this 'issue' when we inevitably rewrite the entire suite because it really
## needs it...
##

#import useful items from mrms module
from insta_alert.gfx_tools.plot_mrms2 import (
    get_mrms_data_async,
    qpe2_cmap,
)

##different colormap for testing because the radarscope one is mid, also differentiates from mrms
NEXRAD_REFLECTIVITY_STOPS = [
    (10, (29, 37, 60, 0)),
    (15, (95, 105, 110, 70)),
    (20, (75, 155, 175, 170)),
    (25, (15, 205, 160, 220)),
    (30, (10, 185, 55, 235)),
    (35, (0, 105, 0, 245)),
    (40, (250, 250, 0, 250)),
    (45, (255, 160, 0, 255)),
    (50, (255, 45, 0, 255)),
    (55, (225, 0, 0, 255)),
    (60, (150, 0, 0, 255)),
    (65, (95, 0, 0, 255)),
    (70, (245, 245, 250, 255)),
    (75, (245, 135, 235, 255)),
    (80, (145, 0, 210, 255)),
]

NEXRAD_MIN_DBZ = NEXRAD_REFLECTIVITY_STOPS[0][0]
NEXRAD_MAX_DBZ = 80
_normalized_nexrad_stops = [
    (
        (level - NEXRAD_MIN_DBZ) / (NEXRAD_MAX_DBZ - NEXRAD_MIN_DBZ),
        tuple(channel / 255 for channel in color),
    )
    for level, color in NEXRAD_REFLECTIVITY_STOPS
]
nws_cmap = LinearSegmentedColormap.from_list(
    "nexrad_radarscope", _normalized_nexrad_stops
)
nws_cmap.set_under((0, 0, 0, 0))
nws_cmap.set_bad((0, 0, 0, 0))


LEVEL3_BASE_URL = "https://tgftp.nws.noaa.gov/SL.us008001/DF.of/DC.radar"
LEVEL3_CACHE_SECONDS = 180
LEVEL3_MAX_PRODUCT_AGE_SECONDS = 30 * 60
LEVEL3_REQUEST_TIMEOUT_SECONDS = 15
LEVEL3_MAX_CACHE_SIZE = 6

LEVEL2_BASE_URL = "https://nomads.ncep.noaa.gov/pub/data/nccf/radar/nexrad_level2"
LEVEL2_CACHE_SECONDS = 180
LEVEL2_MAX_PRODUCT_AGE_SECONDS = 30 * 60
LEVEL2_REQUEST_TIMEOUT_SECONDS = (10, 60)
LEVEL2_MAX_CACHE_SIZE = 2
LEVEL2_DOWNLOAD_RETRIES = 6

REFLECTIVITY_PRODUCT = "p94r0"
ONE_HOUR_ACCUMULATION_PRODUCT = "169oh"
HYBRID_HYDROMETEOR_PRODUCT = "177hh"
FLOOD_ALERTS = {"Flash Flood Warning", "Flood Advisory", "Flood Warning"}

# codex assured me this was the best way to accomplish this, I don't believe it but frankly I can't be bothered to double check.
RADAR_SITES = {
    "KABR": (45.45, -98.42),
    "KABX": (35.15, -106.82),
    "KAKQ": (36.97, -77.00),
    "KAMA": (35.22, -101.72),
    "KAMX": (25.62, -80.42),
    "KAPX": (44.90, -84.72),
    "KARX": (43.82, -91.18),
    "KATX": (48.20, -122.50),
    "KBBX": (39.50, -121.63),
    "KBGM": (42.22, -75.98),
    "KBHX": (40.50, -124.30),
    "KBIS": (46.77, -100.75),
    "KBLX": (45.85, -108.60),
    "KBMX": (33.17, -86.77),
    "KBOX": (41.95, -71.13),
    "KBRO": (25.92, -97.42),
    "KBUF": (42.93, -78.73),
    "KBYX": (24.60, -81.70),
    "KCAE": (33.93, -81.12),
    "KCBW": (46.03, -67.80),
    "KCBX": (43.48, -116.23),
    "KCCX": (40.92, -78.00),
    "KCLE": (41.42, -81.84),
    "KCLX": (32.65, -81.05),
    "KCRP": (27.77, -97.50),
    "KCXX": (44.52, -73.17),
    "KCYS": (41.15, -104.80),
    "KDAX": (38.50, -121.68),
    "KDDC": (37.77, -99.97),
    "KDFX": (29.27, -100.28),
    "KDGX": (32.28, -89.98),
    "KDIX": (39.95, -74.42),
    "KDLH": (46.85, -92.20),
    "KDMX": (41.73, -93.72),
    "KDOX": (38.83, -75.43),
    "KDTX": (42.70, -83.47),
    "KDVN": (41.62, -90.58),
    "KDYX": (32.53, -99.25),
    "KEAX": (38.82, -94.27),
    "KEMX": (31.90, -110.63),
    "KENX": (42.58, -74.06),
    "KEOX": (31.47, -85.47),
    "KEPZ": (31.87, -106.70),
    "KESX": (35.70, -114.88),
    "KEVX": (30.57, -85.92),
    "KEWX": (29.70, -98.03),
    "KEYX": (35.10, -117.57),
    "KFCX": (37.02, -80.27),
    "KFDR": (34.35, -98.98),
    "KFDX": (34.63, -103.62),
    "KFFC": (33.35, -84.57),
    "KFSD": (43.58, -96.75),
    "KFSX": (34.57, -111.20),
    "KFTG": (39.78, -104.55),
    "KFWS": (32.57, -97.30),
    "KGGW": (48.22, -106.62),
    "KGJX": (39.07, -108.22),
    "KGLD": (39.36, -101.70),
    "KGRB": (44.48, -88.13),
    "KGRK": (31.07, -97.83),
    "KGRR": (42.88, -85.52),
    "KGSP": (34.90, -82.22),
    "KGWX": (33.90, -88.33),
    "KGYX": (43.88, -70.25),
    "KHDC": (30.52, -90.42),
    "KHDX": (33.08, -106.12),
    "KHGX": (29.47, -95.08),
    "KHNX": (36.32, -119.63),
    "KHPX": (36.72, -87.28),
    "KHTX": (34.93, -86.08),
    "KICT": (37.65, -97.43),
    "KICX": (37.58, -112.87),
    "KILN": (39.43, -83.80),
    "KILX": (40.15, -89.33),
    "KIND": (39.72, -86.30),
    "KINX": (36.18, -95.57),
    "KIWA": (33.29, -111.65),
    "KIWX": (41.37, -85.70),
    "KJAX": (30.50, -81.68),
    "KJGX": (32.68, -83.35),
    "KJKL": (37.60, -83.32),
    "KLBB": (33.67, -101.82),
    "KLCH": (30.13, -93.22),
    "KLGX": (47.12, -124.10),
    "KLNX": (41.95, -100.58),
    "KLOT": (41.60, -88.10),
    "KLRX": (40.72, -116.80),
    "KLSX": (38.70, -90.68),
    "KLTX": (33.97, -78.43),
    "KLVX": (37.97, -85.95),
    "KLWX": (38.97, -77.48),
    "KLZK": (34.83, -92.27),
    "KMAF": (31.95, -102.20),
    "KMAX": (42.08, -122.72),
    "KMBX": (48.40, -100.87),
    "KMHX": (34.77, -76.87),
    "KMKX": (42.97, -88.55),
    "KMLB": (28.10, -80.65),
    "KMOB": (30.68, -88.25),
    "KMPX": (44.85, -93.57),
    "KMQT": (46.53, -87.57),
    "KMRX": (36.17, -83.40),
    "KMSX": (47.03, -113.98),
    "KMTX": (41.27, -112.45),
    "KMUX": (37.15, -121.90),
    "KMVX": (47.53, -97.33),
    "KMXX": (32.53, -85.78),
    "KNKX": (32.86, -117.13),
    "KNQA": (35.35, -89.87),
    "KOAX": (41.32, -96.37),
    "KOHX": (36.25, -86.57),
    "KOKX": (40.86, -72.87),
    "KOTX": (47.68, -117.63),
    "KPAH": (37.07, -88.77),
    "KPBZ": (40.53, -80.22),
    "KPDT": (45.70, -118.83),
    "KPOE": (31.05, -93.20),
    "KPUX": (38.47, -104.18),
    "KRAX": (35.67, -78.48),
    "KRGX": (39.75, -119.47),
    "KRIW": (43.07, -108.47),
    "KRLX": (38.32, -81.72),
    "KRTX": (45.72, -122.97),
    "KSFX": (43.10, -112.68),
    "KSGF": (37.22, -93.38),
    "KSHV": (32.45, -93.83),
    "KSJT": (31.37, -100.50),
    "KSOX": (33.82, -117.63),
    "KSRX": (35.28, -94.37),
    "KTBW": (27.70, -82.40),
    "KTFX": (47.47, -111.38),
    "KTLH": (30.40, -84.35),
    "KTLX": (35.33, -97.28),
    "KTWX": (39.00, -96.23),
    "KTYX": (43.75, -75.68),
    "KUDX": (44.13, -102.83),
    "KUEX": (40.32, -98.45),
    "KVAX": (30.88, -83.00),
    "KVBX": (34.83, -120.40),
    "KVNX": (36.72, -98.13),
    "KVTX": (34.42, -119.18),
    "KVWX": (38.27, -87.72),
    "KYUX": (32.50, -114.65),
    "PABC": (60.80, -161.88),
    "PACG": (56.85, -135.53),
    "PAEC": (62.88, -149.83),
    "PAHG": (60.73, -151.35),
    "PAIH": (59.47, -146.30),
    "PAKC": (58.68, -156.63),
    "PAPD": (65.03, -147.50),
    "PGUA": (13.57, 144.91),
    "PHKI": (21.90, -159.55),
    "PHKM": (20.13, -155.78),
    "PHMO": (21.13, -157.18),
    "PHWA": (19.10, -155.57),
    "TJUA": (18.12, -66.08),
}


_level3_cache = {}
_level2_cache = {}
_cache_lock = threading.Lock()

# what is a haversine?
# its used for "as the crow flies"
def _haversine_km(lat1, lon1, lat2, lon2):
    """Return great-circle distance between two points in kilometers."""
    earth_radius_km = 6371.0088
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(a))


def nearest_radar_site(latitude, longitude):
    """Find the operational NEXRAD site nearest a latitude/longitude point."""
    nearest = None
    for site_id, (site_latitude, site_longitude) in RADAR_SITES.items():
        if not isfinite(site_latitude) or not isfinite(site_longitude):
            continue
        distance = _haversine_km(
            latitude, longitude, site_latitude, site_longitude
        )
        if nearest is None or distance < nearest[1]:
            nearest = (site_id, distance)

    if nearest is None:
        raise RuntimeError("No NEXRAD site coordinates are available")
    return nearest


def _trim_polar_range_to_bbox(dataset, bbox, padding_km=10):
    """Drop distant gates that cannot appear inside the requested map extent."""
    radar_lat = dataset.attrs["radar_latitude"]
    radar_lon = dataset.attrs["radar_longitude"]
    corner_distances = [
        _haversine_km(radar_lat, radar_lon, latitude, longitude)
        for latitude in (bbox["lat_min"], bbox["lat_max"])
        for longitude in (bbox["lon_min"], bbox["lon_max"])
    ]
    maximum_range = max(corner_distances) + padding_km
    gate_count = int(
        np.searchsorted(dataset.range.values, maximum_range, side="right")
    )
    gate_count = max(1, min(gate_count, dataset.sizes["range"]))
    return dataset.isel(
        range=slice(0, gate_count),
        range_edge=slice(0, gate_count + 1),
    )


def _product_url(site_id, product):
    return (
        f"{LEVEL3_BASE_URL}/DS.{product}/SI.{site_id.lower()}/sn.last"
    )


def _iter_packets(value):
    """Yield dictionaries nested in a Level III symbology block."""
    if isinstance(value, dict):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_packets(item)


def _data_packet(level3):
    for packet in _iter_packets(getattr(level3, "sym_block", [])):
        if {"data", "start_az", "end_az"}.issubset(packet):
            return packet
    raise ValueError("Level III product does not contain a radial data packet")


def _as_magnitude(values):
    return np.asarray(getattr(values, "magnitude", values), dtype=float)


def _level3_to_dataset(level3):
    """Convert a MetPy Level3File radial packet to the plotting data contract."""
    try:
        packet = _data_packet(level3)
    except ValueError:
        # Accumulation products intentionally contain only a text packet when
        # the RPG reports that no precipitation was detected. Represent that
        # valid observation as a transparent grid instead of treating it as a
        # radar outage. Other null reasons indicate unavailable/incomplete data.
        if level3.metadata.get("null_product") not in {2, 4, 5}:
            raise
        gate_count = max(1, round(float(level3.max_range) / 2))
        data = np.full((360, gate_count), np.nan)
        start_az = np.arange(360, dtype=float)
        end_az = start_az + 1
    else:
        mapped = level3.map_data(packet["data"])
        data = np.ma.asarray(mapped, dtype=float).filled(np.nan)
        start_az = np.asarray(packet["start_az"], dtype=float)
        end_az = np.asarray(packet["end_az"], dtype=float)

    if data.ndim != 2 or not data.size:
        raise ValueError(f"Unexpected Level III data shape: {data.shape}")

    if len(start_az) != data.shape[0] or len(end_az) != data.shape[0]:
        raise ValueError("Level III azimuth count does not match radial count")

    # Unwrap the azimuth dimension so xarray can interpolate it monotonically.
    azimuth_edges = np.rad2deg(
        np.unwrap(np.deg2rad(np.concatenate((start_az, [end_az[-1]]))))
    )
    azimuth_centers = (azimuth_edges[:-1] + azimuth_edges[1:]) / 2
    range_edges = np.linspace(0, float(level3.max_range), data.shape[1] + 1)
    range_centers = (range_edges[:-1] + range_edges[1:]) / 2

    edge_lons, edge_lats = azimuth_range_to_lat_lon(
        units.Quantity(azimuth_edges % 360, "degrees"),
        units.Quantity(range_edges, "kilometers"),
        level3.lon,
        level3.lat,
    )
    return xr.Dataset(
        data_vars={"unknown": (("azimuth", "range"), data)},
        coords={
            "azimuth": azimuth_centers,
            "range": range_centers,
            "longitude": (
                ("azimuth_edge", "range_edge"),
                _as_magnitude(edge_lons),
            ),
            "latitude": (
                ("azimuth_edge", "range_edge"),
                _as_magnitude(edge_lats),
            ),
        },
        attrs={
            "radar_source": "level3",
            "radar_site": level3.siteID,
            "radar_latitude": level3.lat,
            "radar_longitude": level3.lon,
            "max_range_km": float(level3.max_range),
            "product_name": level3.product_name,
        },
    )


def _product_time(level3):
    product_time = level3.metadata.get("prod_time")
    if not isinstance(product_time, datetime):
        raise ValueError("Level III product does not include a valid product time")
    if product_time.tzinfo is None:
        product_time = product_time.replace(tzinfo=timezone.utc)
    return product_time.astimezone(timezone.utc)


def _download_product(site_id, product):
    url = _product_url(site_id, product)
    now = time.time()
    with _cache_lock:
        cached = _level3_cache.get(url)
        if cached and now - cached[0] < LEVEL3_CACHE_SECONDS:
            return cached[1], cached[2]

    try:
        response = requests.get(url, timeout=LEVEL3_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        level3 = Level3File(BytesIO(response.content))
        valid_time = _product_time(level3)
        age_seconds = (datetime.now(timezone.utc) - valid_time).total_seconds()
        if age_seconds > LEVEL3_MAX_PRODUCT_AGE_SECONDS:
            raise ValueError(
                f"product is {age_seconds / 60:.0f} minutes old"
            )
        if age_seconds < -5 * 60:
            raise ValueError("product time is unexpectedly in the future")
        dataset = _level3_to_dataset(level3)
    except Exception as exc:
        print(
            Back.RED
            + f"Level III: Failed to load {product} from {site_id}: {exc}"
            + Back.RESET
        )
        return None, None

    with _cache_lock:
        if len(_level3_cache) >= LEVEL3_MAX_CACHE_SIZE:
            oldest_url = min(_level3_cache, key=lambda key: _level3_cache[key][0])
            _level3_cache.pop(oldest_url, None)
        _level3_cache[url] = (now, dataset, valid_time)
    return dataset, valid_time


def _level2_file_time(filename):
    match = re.fullmatch(
        r"[A-Z0-9]{4}_(\d{8})_(\d{6})\.bz2", filename, flags=re.IGNORECASE
    )
    if not match:
        raise ValueError(f"Unexpected Level II filename: {filename}")
    return datetime.strptime(
        "".join(match.groups()), "%Y%m%d%H%M%S"
    ).replace(tzinfo=timezone.utc)


def _check_product_age(valid_time, max_age_seconds, product_name):
    age_seconds = (datetime.now(timezone.utc) - valid_time).total_seconds()
    if age_seconds > max_age_seconds:
        raise ValueError(f"{product_name} is {age_seconds / 60:.0f} minutes old")
    if age_seconds < -5 * 60:
        raise ValueError(f"{product_name} time is unexpectedly in the future")


def _azimuth_edges(azimuth_centers):
    """Convert ordered ray-center azimuths into pcolormesh boundaries."""
    if len(azimuth_centers) < 2:
        raise ValueError("Level II sweep contains fewer than two reflectivity rays")

    edges = np.empty(len(azimuth_centers) + 1, dtype=float)
    edges[1:-1] = (azimuth_centers[:-1] + azimuth_centers[1:]) / 2
    edges[0] = azimuth_centers[0] - (edges[1] - azimuth_centers[0])
    edges[-1] = azimuth_centers[-1] + (azimuth_centers[-1] - edges[-2])
    return edges


def _level2_to_dataset(level2):
    """Convert the lowest Level II reflectivity sweep to the plotting contract."""
    reflectivity_rays = None
    for sweep in level2.sweeps:
        candidates = [ray for ray in sweep if b"REF" in ray[4]]
        if candidates:
            reflectivity_rays = candidates
            break

    if not reflectivity_rays:
        raise ValueError("Level II volume does not contain reflectivity data")

    first_header = reflectivity_rays[0][4][b"REF"][0]
    gate_width = float(first_header.gate_width)
    first_gate = float(first_header.first_gate)
    gate_count = max(len(ray[4][b"REF"][1]) for ray in reflectivity_rays)

    azimuth_centers = np.asarray(
        [float(ray[0].az_angle) % 360 for ray in reflectivity_rays], dtype=float
    )
    order = np.argsort(azimuth_centers)
    azimuth_centers = azimuth_centers[order]
    reflectivity_rays = [reflectivity_rays[index] for index in order]

    # Duplicate ray centers produce zero-width pcolormesh cells. Retain the
    # first ray at each azimuth, which is sufficient for a single base sweep.
    keep = np.concatenate(([True], np.diff(azimuth_centers) > 1e-6))
    azimuth_centers = azimuth_centers[keep]
    reflectivity_rays = [
        ray for ray, should_keep in zip(reflectivity_rays, keep, strict=True)
        if should_keep
    ]

    data = np.full((len(reflectivity_rays), gate_count), np.nan, dtype=float)
    for index, ray in enumerate(reflectivity_rays):
        header, values = ray[4][b"REF"]
        if not np.isclose(float(header.gate_width), gate_width):
            raise ValueError("Level II reflectivity gate widths vary within a sweep")
        values = np.asarray(values, dtype=float)
        data[index, :len(values)] = values

    azimuth_edges = _azimuth_edges(azimuth_centers)
    range_edges = (
        (np.arange(gate_count + 1, dtype=float) - 0.5) * gate_width
        + first_gate
    )
    range_centers = (
        np.arange(gate_count, dtype=float) * gate_width + first_gate
    )

    volume_constants = reflectivity_rays[0][1]
    radar_lon = float(volume_constants.lon)
    radar_lat = float(volume_constants.lat)
    edge_lons, edge_lats = azimuth_range_to_lat_lon(
        units.Quantity(azimuth_edges % 360, "degrees"),
        units.Quantity(range_edges, "kilometers"),
        radar_lon,
        radar_lat,
    )

    return xr.Dataset(
        data_vars={"unknown": (("azimuth", "range"), data)},
        coords={
            "azimuth": azimuth_centers,
            "range": range_centers,
            "longitude": (
                ("azimuth_edge", "range_edge"),
                _as_magnitude(edge_lons),
            ),
            "latitude": (
                ("azimuth_edge", "range_edge"),
                _as_magnitude(edge_lats),
            ),
        },
        attrs={
            "radar_source": "level2",
            "radar_site": level2.stid,
            "radar_latitude": radar_lat,
            "radar_longitude": radar_lon,
            "max_range_km": float(range_edges[-1]),
            "product_name": "Level II Base Reflectivity",
            "gate_width_km": gate_width,
        },
    )


def _download_level2(site_id):
    """Download and decode the latest complete Level II radar volume."""
    now = time.time()
    with _cache_lock:
        cached = _level2_cache.get(site_id)
        if cached and now - cached[0] < LEVEL2_CACHE_SECONDS:
            return cached[2], cached[3]

    directory_url = f"{LEVEL2_BASE_URL}/{site_id}/"
    try:
        listing_response = requests.get(
            directory_url + "dir.list", timeout=LEVEL2_REQUEST_TIMEOUT_SECONDS
        )
        listing_response.raise_for_status()
        filenames = re.findall(
            rf"\b{re.escape(site_id)}_\d{{8}}_\d{{6}}\.bz2\b",
            listing_response.text,
            flags=re.IGNORECASE,
        )
        if not filenames:
            raise ValueError("directory listing contains no Level II volumes")

        latest_filename = max(filenames, key=str.upper)
        listing_time = _level2_file_time(latest_filename)
        _check_product_age(
            listing_time, LEVEL2_MAX_PRODUCT_AGE_SECONDS, "Level II volume"
        )

        with _cache_lock:
            cached = _level2_cache.get(site_id)
            if cached and cached[1] == latest_filename:
                _level2_cache[site_id] = (now, *cached[1:])
                return cached[2], cached[3]

        last_download_error = None
        for attempt in range(LEVEL2_DOWNLOAD_RETRIES):
            try:
                data_response = requests.get(
                    directory_url + latest_filename,
                    timeout=LEVEL2_REQUEST_TIMEOUT_SECONDS,
                )
                data_response.raise_for_status()
                break
            except (RequestException, IncompleteRead) as exc:
                last_download_error = exc
                if attempt + 1 >= LEVEL2_DOWNLOAD_RETRIES:
                    print(Back.RED + f"Failed to download {directory_url + latest_filename}" + Back.RESET)
                    return None, None
                time.sleep(2)
        else:
            raise last_download_error

        level2 = Level2File(BytesIO(data_response.content))
        valid_time = level2.dt
        if valid_time.tzinfo is None:
            valid_time = valid_time.replace(tzinfo=timezone.utc)
        else:
            valid_time = valid_time.astimezone(timezone.utc)
        _check_product_age(
            valid_time, LEVEL2_MAX_PRODUCT_AGE_SECONDS, "Level II volume"
        )
        dataset = _level2_to_dataset(level2)
    except Exception as exc:
        print(
            Back.RED
            + f"Level II: Failed to load latest volume from {site_id}: {exc}"
            + Back.RESET
        )
        return None, None

    with _cache_lock:
        if len(_level2_cache) >= LEVEL2_MAX_CACHE_SIZE:
            oldest_site = min(
                _level2_cache, key=lambda key: _level2_cache[key][0]
            )
            _level2_cache.pop(oldest_site, None)
        _level2_cache[site_id] = (
            now,
            latest_filename,
            dataset,
            valid_time,
        )
    return dataset, valid_time


def smooth_nexrad_field(data, sigma=0.65):
    """Return a lightly smoothed plotting copy without expanding echo coverage."""
    values = np.asarray(data.values, dtype=float)
    valid = np.isfinite(values)
    if not valid.any():
        return data

    # Normalize by the valid-data weights so missing radar bins do not pull
    # reflectivity toward zero. Keep the original mask to avoid false echoes.
    weights = gaussian_filter(
        valid.astype(float), sigma=sigma, mode=("wrap", "nearest")
    )
    filtered = gaussian_filter(
        np.where(valid, values, 0.0),
        sigma=sigma,
        mode=("wrap", "nearest"),
    )
    smoothed = np.divide(
        filtered,
        weights,
        out=np.full_like(filtered, np.nan),
        where=weights > 0,
    )
    smoothed[~valid] = np.nan
    return data.copy(data=smoothed)


def _ptype_flags_on_reflectivity_grid(hydrometeor_data, reflectivity_data):
    """Map Level III HHC categories to the rain/snow flags used by the plotter."""
    categories = hydrometeor_data.unknown.interp(
        azimuth=reflectivity_data.azimuth,
        range=reflectivity_data.range,
        method="nearest",
    )
    is_snow = categories.isin([3, 4, 5])  # ice crystals, dry snow, wet snow
    mapped = xr.where(is_snow, 3.0, xr.where(categories.notnull(), 6.0, np.nan))
    return xr.Dataset(
        data_vars={
            "unknown": (
                ("azimuth", "range"),
                np.asarray(mapped.values, dtype=float),
            )
        },
        coords={
            "azimuth": reflectivity_data.azimuth.values,
            "range": reflectivity_data.range.values,
            "longitude": reflectivity_data.longitude,
            "latitude": reflectivity_data.latitude,
        },
    )


def get_level3_data(bbox, alert_type, ptype, center_lat=None, center_lon=None):
    """Return nearest-site Level III data using the existing MRMS tuple shape.

    A ``None`` primary dataset signals the caller to use its MRMS fallback.
    """
    if center_lat is None:
        center_lat = (bbox["lat_min"] + bbox["lat_max"]) / 2
    if center_lon is None:
        center_lon = (bbox["lon_min"] + bbox["lon_max"]) / 2

    try:
        site_id, distance_km = nearest_radar_site(center_lat, center_lon)
    except (RuntimeError, TypeError, ValueError) as exc:
        print(Fore.RED + f"Level III: Site selection failed: {exc}" + Fore.RESET)
        return None, None, None, None, None, None, None

    is_flood = alert_type in FLOOD_ALERTS
    product = ONE_HOUR_ACCUMULATION_PRODUCT if is_flood else REFLECTIVITY_PRODUCT
    print(
        Fore.CYAN
        + f"Level III: Using nearest radar {site_id} ({distance_km:.0f} km away)"
        + Fore.RESET
    )
    main_data, valid_datetime = _download_product(site_id, product)
    if main_data is None:
        return None, None, None, None, None, None, None

    # A decoded product can still be unusable when the alert lies outside its range.
    if distance_km > main_data.attrs["max_range_km"]:
        print(
            Fore.RED
            + f"Level III: {site_id} does not cover the alert center; using MRMS"
            + Fore.RESET
        )
        return None, None, None, None, None, None, None

    main_data = _trim_polar_range_to_bbox(main_data, bbox)

    flag_data = None
    if is_flood:
        cmap = qpe2_cmap
        data_min, data_max = 0.0, 4.0
        cbar_label = "Radar Estimated Precipitation (1hr) (in)"
    else:
        cmap = nws_cmap
        data_min, data_max = NEXRAD_MIN_DBZ, NEXRAD_MAX_DBZ
        cbar_label = "Reflectivity (dBZ)"
        if ptype:
            hydrometeor_data, _ = _download_product(
                site_id, HYBRID_HYDROMETEOR_PRODUCT
            )
            if hydrometeor_data is None:
                print(
                    Fore.YELLOW
                    + "Level III: Winter HHC unavailable; using MRMS"
                    + Fore.RESET
                )
                return None, None, None, None, None, None, None
            if distance_km > hydrometeor_data.attrs["max_range_km"]:
                print(
                    Fore.YELLOW
                    + "Level III: Alert is outside HHC range; using MRMS"
                    + Fore.RESET
                )
                return None, None, None, None, None, None, None
            try:
                flag_data = _ptype_flags_on_reflectivity_grid(
                    hydrometeor_data, main_data
                )
            except Exception as exc:
                print(
                    Fore.YELLOW
                    + f"Level III: Could not apply winter HHC mask: {exc}; using MRMS"
                    + Fore.RESET
                )
                return None, None, None, None, None, None, None

    valid_time = valid_datetime.strftime("%H:%M UTC")
    valid_time += f" ({site_id})"
    return (
        main_data,
        flag_data,
        cmap,
        data_min,
        data_max,
        cbar_label,
        valid_time,
    )


def get_level2_data(bbox, alert_type, ptype, center_lat=None, center_lon=None):
    """Return nearest-site Level II reflectivity using the MRMS tuple shape.

    Level II contains base moments rather than derived accumulations or
    hydrometeor classifications. Flood alerts therefore use the Level III
    one-hour accumulation, and winter typing pairs Level II reflectivity with
    the colocated Level III hybrid hydrometeor classification.
    """
    if center_lat is None:
        center_lat = (bbox["lat_min"] + bbox["lat_max"]) / 2
    if center_lon is None:
        center_lon = (bbox["lon_min"] + bbox["lon_max"]) / 2

    try:
        site_id, distance_km = nearest_radar_site(center_lat, center_lon)
    except (RuntimeError, TypeError, ValueError) as exc:
        print(Fore.RED + f"Level II: Site selection failed: {exc}" + Fore.RESET)
        return None, None, None, None, None, None, None

    if alert_type in FLOOD_ALERTS:
        print(
            Fore.CYAN
            + "Level II has no one-hour accumulation; using the nearest-site "
            + "Level III accumulation product"
            + Fore.RESET
        )
        return get_level3_data(
            bbox,
            alert_type,
            ptype,
            center_lat=center_lat,
            center_lon=center_lon,
        )

    print(
        Fore.CYAN
        + f"Level II: Using nearest radar {site_id} ({distance_km:.0f} km away)"
        + Fore.RESET
    )
    main_data, valid_datetime = _download_level2(site_id)
    if main_data is None:
        return None, None, None, None, None, None, None

    if distance_km > main_data.attrs["max_range_km"]:
        print(
            Fore.RED
            + f"Level II: {site_id} does not cover the alert center; using MRMS"
            + Fore.RESET
        )
        return None, None, None, None, None, None, None


    main_data = _trim_polar_range_to_bbox(main_data, bbox)

    flag_data = None
    if ptype:
        hydrometeor_data, _ = _download_product(
            site_id, HYBRID_HYDROMETEOR_PRODUCT
        )
        if hydrometeor_data is None:
            print(
                Fore.YELLOW
                + "Level II: Winter HHC unavailable; using MRMS"
                + Fore.RESET
            )
            return None, None, None, None, None, None, None
        if distance_km > hydrometeor_data.attrs["max_range_km"]:
            print(
                Fore.YELLOW
                + "Level II: Alert is outside HHC range; using MRMS"
                + Fore.RESET
            )
            return None, None, None, None, None, None, None
        try:
            flag_data = _ptype_flags_on_reflectivity_grid(
                hydrometeor_data, main_data
            )
        except Exception as exc:
            print(
                Fore.YELLOW
                + f"Level II: Could not apply winter HHC mask: {exc}; using MRMS"
                + Fore.RESET
            )
            return None, None, None, None, None, None, None

    valid_time = valid_datetime.strftime("%H:%M UTC")
    valid_time += f" ({site_id})"
    return (
        main_data,
        flag_data,
        nws_cmap,
        NEXRAD_MIN_DBZ,
        NEXRAD_MAX_DBZ,
        "Reflectivity (dBZ)",
        valid_time,
    )


def get_radar_data(
    bbox,
    alert_type,
    region,
    ptype,
    use_nexrad=False,
    center_lat=None,
    center_lon=None,
):
    """Select Level II, Level III, or MRMS with a safe MRMS fallback."""
    nexrad_mode = use_nexrad.upper() if isinstance(use_nexrad, str) else use_nexrad
    if nexrad_mode == "LEVEL2":
        result = get_level2_data(
            bbox,
            alert_type,
            ptype,
            center_lat=center_lat,
            center_lon=center_lon,
        )
        if result[0] is not None:
            return result
        print(
            Fore.YELLOW
            + "Level II unavailable; falling back to MRMS."
            + Fore.RESET
        )
    elif nexrad_mode == "LEVEL3":
        result = get_level3_data(
            bbox,
            alert_type,
            ptype,
            center_lat=center_lat,
            center_lon=center_lon,
        )
        if result[0] is not None:
            return result
        print(
            Fore.YELLOW
            + "Level III unavailable; falling back to MRMS."
            + Fore.RESET
        )
    elif nexrad_mode is not False:
        print(
            Fore.YELLOW
            + f"Invalid USE_NEXRAD value {use_nexrad!r}; falling back to MRMS. "
            + 'Use "LEVEL2", "LEVEL3", or False.'
            + Fore.RESET
        )

    return get_mrms_data_async(bbox, alert_type, region, ptype)
