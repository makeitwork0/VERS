import requests
from bs4 import BeautifulSoup
import re

url = "https://www.pagasa.dost.gov.ph/regional-forecast/ncrprsd"
try:
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Just grab all text from the page and search for "RED WARNING LEVEL:" etc.
    text = soup.get_text(separator=' ')
    
    red_match = re.search(r'RED WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|ORANGE|YELLOW|$)', text, re.IGNORECASE | re.DOTALL)
    orange_match = re.search(r'ORANGE WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|YELLOW|RED|$)', text, re.IGNORECASE | re.DOTALL)
    yellow_match = re.search(r'YELLOW WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|Meanwhile|$)', text, re.IGNORECASE | re.DOTALL)
    
    print("RED:", red_match.group(1).strip() if red_match else "None")
    print("ORANGE:", orange_match.group(1).strip() if orange_match else "None")
    print("YELLOW:", yellow_match.group(1).strip() if yellow_match else "None")
except Exception as e:
    print("Error:", e)
