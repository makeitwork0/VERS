import math

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile

# Bounding box for Bagumbayan, Taguig
lat_min, lat_max = 14.4700, 14.4950
lon_min, lon_max = 121.0450, 121.0700

total_tiles = 0
for zoom in range(12, 18):
    x_min, y_max = latlon_to_tile(lat_min, lon_min, zoom)
    x_max, y_min = latlon_to_tile(lat_max, lon_max, zoom)
    
    # Coordinates might be inverted for Y depending on hemisphere/calculation direction
    y_start, y_end = min(y_min, y_max), max(y_min, y_max)
    x_start, x_end = min(x_min, x_max), max(x_min, x_max)
    
    count = (x_end - x_start + 1) * (y_end - y_start + 1)
    total_tiles += count
    print(f"Zoom {zoom}: X [{x_start} to {x_end}], Y [{y_start} to {y_end}] -> {count} tiles")

print(f"Total tiles: {total_tiles}")
