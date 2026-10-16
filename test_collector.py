import urllib.request, re, os, io, json, sys
from PIL import Image
from google import genai

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = os.environ.get('GEMINI_API_KEY', '')
client = genai.Client(api_key=API_KEY) if API_KEY else None

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

url = 'https://www.bing.com/images/async?q=glofish+tetra+aquarium+swimming&first=0&count=10&mmasync=1'
req = urllib.request.Request(url, headers=headers)
html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
print('Found URLs:', len(murls))

for idx, img_url in enumerate(murls[:5]):
    try:
        img_req = urllib.request.Request(img_url, headers=headers)
        img_bytes = urllib.request.urlopen(img_req, timeout=7).read()
        pil_img = Image.open(io.BytesIO(img_bytes))
        w, h = pil_img.size
        if w < 250 or h < 250:
            print(f'[{idx+1}] Skipped: too small ({w}x{h})')
            continue
        pil_img.thumbnail((512, 512))
        
        prompt = """Phan tich anh nay phuc vu huan luyen AI YOLOv8 cho ho ca IoT:
Loai ca can nhan: Ca Canh Buom Da Quang (GloFish Tetra) phat mau huynh quang neon chói loi.
Quy tac:
1. is_live_in_water: Phai la ANH THAT con ca DANG SONG boi trong be kinh/ho nuoc. (Tu choi ca chet, thot, dia an, chau nhua, bich nilon, tranh ve, logo, mo nhoe).
2. is_correct_species: Co dung la Ca Da Quang (GloFish) khong?
Tra ve JSON: {"is_live_in_water": true, "is_correct": true, "variety": "ten dong", "reason": "giai thich 1 cau"}"""
        
        resp = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=[pil_img, prompt]
        )
        t = resp.text.strip()
        if t.startswith('```json'): t = t[7:-3].strip()
        elif t.startswith('```'): t = t[3:-3].strip()
        res = json.loads(t)
        live = res.get('is_live_in_water')
        corr = res.get('is_correct')
        var = res.get('variety')
        reason = res.get('reason')
        print(f'[{idx+1}] live={live} correct={corr} | variety={var} | reason={reason}')
        if live and corr:
            print('  >>> HOP LE! Con ca that dang boi trong be nuoc, chuan loai!')
            break
    except Exception as e:
        print(f'[{idx+1}] Error: {e}')
