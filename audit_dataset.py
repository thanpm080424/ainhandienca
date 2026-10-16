"""
Chuong trinh kiem tra (Audit) dataset hien tai bang AI Gemini Vision.
Moi anh duoc AI kiem tra:
- Co phai con ca that khong?
- Co dung la loai ca nay khong?
Neu SAI: Di chuyen sang thu muc '_anh_nghi_ngo/' kem bao cao ly do.
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from google import genai
from PIL import Image

# UTF-8 output cho console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_KEY = os.environ.get('GEMINI_API_KEY', '')
client = genai.Client(api_key=API_KEY) if API_KEY else None

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset_ca')
SUSPECT_DIR = os.path.join(DATASET_DIR, '_anh_nghi_ngo')

SPECIES_SPECS = {
    'ca_ba_duoi': {
        'name': 'Ca Ba Duoi (Three-spot Gourami)',
        'features': 'Ca nuoc ngot than det, co 2-3 cham den tren than, vay bung dai nhu soi',
    },
    'ca_bay_mau': {
        'name': 'Ca Bay Mau (Guppy - Poecilia reticulata)',
        'features': 'Ca nho, duoi to xoe rong nhieu mau sac ruc ro',
    },
    'ca_but_chi': {
        'name': 'Ca But Chi (Pencilfish - Nannostomus)',
        'features': 'Ca nho, than thon dai nhu cay but chi, soc doc hoac ngang',
    },
    'ca_chuot': {
        'name': 'Ca Chuot (Corydoras)',
        'features': 'Ca da tram nho boi day be, co rau o mieng, bung phang',
    },
    'ca_da_quang': {
        'name': 'Ca Da Quang (GloFish - Transgenic fluorescent fish)',
        'features': 'Ca phat sang mau neon ruc ro (do, xanh la, cam, tim, hong). Chu y: Khong nham voi Ca Neon (Neon Tetra co soc xanh bung do)',
    },
    'ca_dia': {
        'name': 'Ca Dia (Discus - Symphysodon)',
        'features': 'Than tron det nhu cai dia, mau sac hoa van ruc ro',
    },
    'ca_diec_anh_dao': {
        'name': 'Ca Diec Anh Dao (Cherry Barb - Puntius titteya)',
        'features': 'Ca nho mau do hong dam nhu trai anh dao, con duc mau do tuoi',
    },
    'ca_duoi_kiem': {
        'name': 'Ca Duoi Kiem (Swordtail - Xiphophorus hellerii)',
        'features': 'Phan thuy duoi phia duoi keo dai nhu luoi kiem o con duc',
    },
    'ca_hong_ket': {
        'name': 'Ca Hong Ket (Blood Parrot Cichlid)',
        'features': 'Ca than tron map, mau cam/do, mieng nho khong khep duoc hinh trai tim',
    },
    'ca_koi': {
        'name': 'Ca Koi (Cyprinus rubrofuscus)',
        'features': 'Ca chep Nhat Ban to lon nhieu khoang mau do, trang, den, vang tren lung',
    },
    'ca_la_han': {
        'name': 'Ca La Han (Flowerhorn Cichlid)',
        'features': 'Ca co cuc buou lon tren dau (gu), hoa van chu han va cham ngoc doc than',
    },
    'ca_lau_kieng': {
        'name': 'Ca Lau Kieng (Plecostomus / Pleco)',
        'features': 'Ca da tram giap cung, mieng hut o mat duoi, thuong bam vao kinh be ca',
    },
    'ca_molly': {
        'name': 'Ca Molly (Poecilia sphenops)',
        'features': 'Ca than bau duc, nhieu mau (trang, vang, dom), khong phai mau den tuyen',
    },
    'ca_mun': {
        'name': 'Ca Mun (Black Molly)',
        'features': 'Toan than mau den tuyen dong nhat, vay den',
    },
    'ca_neon': {
        'name': 'Ca Neon (Neon Tetra - Paracheirodon innesi)',
        'features': 'Ca nho dai soc xanh da troi phat sang doc nua than tren, bung duoi mau do tuoi',
    },
    'ca_rong': {
        'name': 'Ca Rong (Arowana)',
        'features': 'Ca co lon than dai uy nghi, vay to sang bong, mieng huong len co rau',
    },
    'ca_sac': {
        'name': 'Ca Sac (Gourami)',
        'features': 'Than det, vay bung dai thanh 2 soi rau cam giac, boi cham',
    },
    'ca_soc_ngua': {
        'name': 'Ca Soc Ngua (Zebra Danio - Danio rerio)',
        'features': 'Ca nho boi dan, co cac soc ngang xanh trang doc theo than nhu ngua van',
    },
    'ca_thien_than': {
        'name': 'Ca Than Tien (Angelfish - Pterophyllum)',
        'features': 'Than det hinh tam giac vuong, vay lung va vay bung rat cao va dai',
    },
    'ca_xiem': {
        'name': 'Ca Xiem (Betta / Siamese Fighting Fish)',
        'features': 'Ca betta vay duoi dai thuot tha nhieu mau, boi hung du xoe vay',
    },
}

def verify_single_image(img_path, species_key):
    """Goi Gemini Flash Lite kiem tra anh."""
    spec = SPECIES_SPECS.get(species_key, {})
    try:
        img = Image.open(img_path)
        img.thumbnail((512, 512))
        
        prompt = f"""Ban la chuyen gia sinh hoc va ca canh quoc te.
Hay danh gia anh nay xem co dat chuan lam dataset huan luyen AI cho loai:
LOAI CAN KIEM TRA: {spec.get('name', species_key)}
DAC DIEM: {spec.get('features', '')}

Yeu cau danh gia:
1. is_fish: Anh co chua con ca thuc te khong? (False neu la so do, chu, nguoi, hoat hinh, vat the la).
2. is_correct: Con ca trong anh co DUNG la {spec.get('name', species_key)} khong? (False neu la loai ca khac bi nhan nham).
3. identified_species: Ten loai ca ban nhan ra trong anh.
4. quality: 'good' neu anh ro net, 'bad' neu qua mo khong nhan dien duoc.
5. reason: Giai thich ngan gon 1 cau vi sao dung hoac sai.

Chi tra ve JSON duy nhat dung dinh dang nay:
{{
    "is_fish": true,
    "is_correct": true,
    "identified_species": "...",
    "quality": "good",
    "reason": "..."
}}"""

        models_to_try = ['gemini-4-argon', 'gemini-3.5-flash', 'gemini-flash-lite-latest']
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[img, prompt]
                )
                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:-3].strip()
                elif text.startswith('```'):
                    text = text[3:-3].strip()
                return json.loads(text)
            except Exception as e:
                continue
        return None
        return {'is_correct': False, 'reason': 'API retry failed'}
    except Exception as e:
        return {'is_correct': False, 'reason': str(e)}

def audit_species(species_key, limit=20, move_suspect=False):
    """Quet kiem tra thu muc cua 1 loai ca."""
    folder = os.path.join(DATASET_DIR, species_key)
    if not os.path.exists(folder):
        return []
        
    valid_ext = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(folder) if f.lower().endswith(valid_ext)]
    
    if limit:
        files = files[:limit]
        
    print(f"\nDang quet {len(files)} anh cua: {species_key}")
    
    results = []
    suspect_count = 0
    
    for i, fname in enumerate(files):
        p = os.path.join(folder, fname)
        res = verify_single_image(p, species_key)
        
        is_ok = res.get('is_fish') and res.get('is_correct') and res.get('quality') != 'bad'
        status = "DUNG" if is_ok else "NGHI NGO"
        
        entry = {
            'file': fname,
            'species': species_key,
            'status': status,
            'identified_as': res.get('identified_species', ''),
            'reason': res.get('reason', '')
        }
        results.append(entry)
        
        safe_fname = fname[:30].encode('ascii', 'ignore').decode()
        print(f"  [{i+1}/{len(files)}] {safe_fname} -> [{status}] {res.get('identified_species', '')}: {res.get('reason', '')[:50]}")
        
        if not is_ok:
            suspect_count += 1
            if move_suspect:
                target_dir = os.path.join(SUSPECT_DIR, species_key)
                os.makedirs(target_dir, exist_ok=True)
                dest = os.path.join(target_dir, fname)
                shutil.move(p, dest)
                print(f"    -> Da chuyen vao: _anh_nghi_ngo/{species_key}/")
                
        time.sleep(0.5)
        
    print(f"Tong ket {species_key}: {len(files)-suspect_count} Dung, {suspect_count} Nghi ngo/Sai")
    return results

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'ca_da_quang'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    move = '--move' in sys.argv
    
    os.makedirs(SUSPECT_DIR, exist_ok=True)
    audit_species(target, limit=limit, move_suspect=move)
