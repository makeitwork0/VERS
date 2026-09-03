import urllib.request
import PyPDF2
from io import BytesIO

url = "https://pubfiles.pagasa.dost.gov.ph/tamss/weather/weather_advisory/Advisory%2327.pdf"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        reader = PyPDF2.PdfReader(BytesIO(response.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        print(text)
except Exception as e:
    print("Error:", e)
