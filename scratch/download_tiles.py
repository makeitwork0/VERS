import math
import os
import urllib.request
import urllib.error
import time

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile

# Bounding box for Bagumbayan, Taguig
lat_min, lat_max = 14.4600, 14.4950
lon_min, lon_max = 121.0450, 121.0700

# Base dir for tiles
base_dir = "/home/rasp-pi/vers_project/static/tiles"
os.makedirs(base_dir, exist_ok=True)

print("Starting offline Google Maps tile download for Bagumbayan, Taguig...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

downloaded = 0
failed = 0

for zoom in range(12, 18):
    x_min, y_max = latlon_to_tile(lat_min, lon_min, zoom)
    x_max, y_min = latlon_to_tile(lat_max, lon_max, zoom)
    
    y_start, y_end = min(y_min, y_max), max(y_min, y_max)
    x_start, x_end = min(x_min, x_max), max(x_min, x_max)
    
    for x in range(x_start, x_end + 1):
        x_dir = os.path.join(base_dir, str(zoom), str(x))
        os.makedirs(x_dir, exist_ok=True)
        
        for y in range(y_start, y_end + 1):
            tile_url = f"https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={zoom}"
            tile_path = os.path.join(x_dir, f"{y}.png")
            
            if os.path.exists(tile_path):
                print(f"Skipping (already exists): {zoom}/{x}/{y}.png")
                continue
                
            try:
                req = urllib.request.Request(tile_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    with open(tile_path, 'wb') as f:
                        f.write(response.read())
                downloaded += 1
                print(f"Downloaded: {zoom}/{x}/{y}.png")
                time.sleep(0.05) # Polite delay
            except Exception as e:
                failed += 1
                print(f"Failed {zoom}/{x}/{y}.png: {e}")

print(f"\nDownload completed! Successfully downloaded: {downloaded}, Failed: {failed}")
