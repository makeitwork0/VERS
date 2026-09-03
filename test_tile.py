import urllib.request
from PIL import Image
import io

url = "https://tilecache.rainviewer.com/v2/radar/5aa72096e711/256/7/107/58/2/1_1.png"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    img_data = response.read()

img = Image.open(io.BytesIO(img_data)).convert('RGBA')
extrema = img.getextrema()
print("Tile size:", img.size)
print("Extrema (R, G, B, A):", extrema)
if extrema[3][1] == 0:
    print("This tile is COMPLETELY TRANSPARENT (No Rain!).")
else:
    print("This tile contains some opaque pixels (Rain is present).")
