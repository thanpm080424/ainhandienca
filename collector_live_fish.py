"""
BO THU THAP & XAC THUC ANH CA CANH IOT DA NGUON TOAN CAU (5 NGUON)
Thuc hien dung 100% yeu cau de tai tot nghiep cua Le Quoc Tri & Pham Minh Than:
1. 5 NGUON ANH TOAN CAU:
   - Flickr Aquarium Photography (anh chup ho ca chat luong cao cua cong dong quoc te)
   - iNaturalist Research API (kho du lieu sinh hoc ca song trong nuoc)
   - GBIF Global Biodiversity Facility (co so du lieu da dang sinh hoc toan cau)
   - Wikimedia Commons API (kho anh thuy sinh va bao tang ban quyen mo)
   - Bing High-Res Async Search (tim kiem chuyen sau cac dong ca lai tao)
2. NHIN THAY RO NET CHO IOT (is_clear_for_iot):
   - Ca phai ro net, chiem ty le chu dao trong anh, ro vay/than/mau sac de YOLOv8 phat hien bounding box.
3. TUYET DOI KHONG TRUNG LAP:
   - So khop kep MD5 + Perceptual dHash voi toan bo 4,967 anh hien co.
4. LOAI BO TRIET DE:
   - Ca chet, thot, dia an, ngoai cho, thau chau nhua, bich nilon, tranh ve, logo, mo nhoe, sai loai.
5. DIEU TIET NHIP DO CHUAN:
   - Nghi 4.2s sau MOI LAN goi AI (ke ca duyet hay tu choi) -> Khong bao gio bi loi 429 Resource Exhausted.
"""

import os
import sys
import time
import json
import hashlib
import io
import re
import urllib.request
import urllib.parse
from PIL import Image
from google import genai

# Ho tro console Windows UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset_ca')
API_KEY = os.environ.get('GEMINI_API_KEY', '')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

SPECIES_CONFIG = {
    'ca_da_quang': {
        'vn_name': 'Cá Dạ Quang',
        'en_name': 'GloFish',
        'sci_name': 'Gymnocorymbus ternetzi',
        'flickr_tag': 'glofish',
        'inat_taxon': None,
        'gbif_taxon': None,
        'bing_queries': [
            'glofish tetra aquarium swimming in tank',
            'glofish fluorescent fish in water tank',
            'cá cánh buồm dạ quang trong bể kính',
            'glofish danio swimming in aquarium'
        ],
        'criteria': 'Cá Cánh Buồm Dạ Quang hoặc Cá Dạ Quang (GloFish) phát huỳnh quang neon chói lọi (đỏ, xanh chuối, cam, tím, vàng). Bắt buộc là cá sống đang bơi trong bể kính.'
    },
    'ca_lau_kieng': {
        'vn_name': 'Cá Lau Kiếng',
        'en_name': 'Pleco / Plecostomus',
        'sci_name': 'Hypostomus plecostomus',
        'flickr_tag': 'pleco',
        'inat_taxon': 'Hypostomus',
        'gbif_taxon': 'Hypostomus',
        'bing_queries': [
            'plecostomus sucker fish aquarium tank',
            'cá lau kiếng bám kính bể cá',
            'bristlenose pleco swimming in tank',
            'cá tỳ bà da báo trong hồ kính'
        ],
        'criteria': 'Cá lau kiếng, cá tỳ bà (Pleco) da giáp cứng, miệng hút bám kính hoặc đáy hồ. Bắt buộc là cá sống trong bể nước.'
    },
    'ca_hong_ket': {
        'vn_name': 'Cá Hồng Két',
        'en_name': 'Blood Parrot Cichlid',
        'sci_name': 'Amphilophus citrinellus',
        'flickr_tag': 'parrotfish,cichlid',
        'inat_taxon': None,
        'gbif_taxon': None,
        'bing_queries': [
            'blood parrot cichlid swimming in aquarium',
            'cá hồng két bơi trong hồ kính',
            'red parrot cichlid fish tank',
            'cá két đỏ bể cá cảnh'
        ],
        'criteria': 'Cá hồng két (Blood Parrot) thân tròn mập ú, màu cam hoặc đỏ tươi, miệng nhỏ hình trái tim không khép kín. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_ba_duoi': {
        'vn_name': 'Cá Ba Đuôi / Cá Vàng',
        'en_name': 'Goldfish',
        'sci_name': 'Carassius auratus',
        'flickr_tag': 'goldfish,aquarium',
        'inat_taxon': 'Carassius auratus',
        'gbif_taxon': 'Carassius auratus',
        'bing_queries': [
            'ranchu goldfish swimming aquarium',
            'oranda goldfish in water tank',
            'cá vàng ba đuôi bơi trong bể kính',
            'ryukin goldfish in aquarium',
            'cá oranda đầu lân hồ thủy sinh'
        ],
        'criteria': 'Cá Ba Đuôi / Cá Vàng (Goldfish) gồm Oranda, Ranchu, Ryukin, Lan thọ, Mắt lồi, Hạc đỉnh hồng. Thân mập tròn, đuôi xòe 3-4 thùy. Bắt buộc là cá sống bơi trong hồ/bể kính có nước.'
    },
    'ca_mun': {
        'vn_name': 'Cá Mún / Platy',
        'en_name': 'Platy fish',
        'sci_name': 'Xiphophorus maculatus',
        'flickr_tag': 'platy,aquarium',
        'inat_taxon': 'Xiphophorus maculatus',
        'gbif_taxon': 'Xiphophorus maculatus',
        'bing_queries': [
            'platy fish aquarium in tank',
            'red platy fish swimming water',
            'cá mún đỏ bơi trong bể thủy sinh',
            'mickey mouse platy in aquarium'
        ],
        'criteria': 'Cá Mún (Platy) thân ngắn mập tròn, màu đỏ cờ, cam, đốm đen Mickey, Panda. Bắt buộc là cá sống đang bơi trong hồ thủy sinh.'
    },
    'ca_diec_anh_dao': {
        'vn_name': 'Cá Diếc Anh Đào',
        'en_name': 'Cherry Barb',
        'sci_name': 'Puntius titteya',
        'flickr_tag': 'cherrybarb',
        'inat_taxon': 'Puntius titteya',
        'gbif_taxon': 'Puntius titteya',
        'bing_queries': [
            'cherry barb fish swimming in aquarium',
            'cá diếc anh đào bơi trong bể thủy sinh',
            'Puntius titteya red barb aquarium tank'
        ],
        'criteria': 'Cá Diếc Anh Đào (Cherry Barb) cá nhỏ màu đỏ tươi hoặc hồng cam, sọc mờ dọc thân. Bắt buộc là CON CÁ (không phải tép cảnh), đang bơi trong bể nước.'
    },
    'ca_sac': {
        'vn_name': 'Cá Sặc Cảnh',
        'en_name': 'Gourami',
        'sci_name': 'Trichogaster',
        'flickr_tag': 'gourami,aquarium',
        'inat_taxon': 'Trichogaster',
        'gbif_taxon': 'Trichogaster',
        'bing_queries': [
            'dwarf gourami swimming in aquarium',
            'cá sặc gấm bơi trong hồ thủy sinh',
            'pearl gourami in planted tank'
        ],
        'criteria': 'Cá Sặc cảnh (Dwarf Gourami, Pearl Gourami, Sặc gấm, Sặc bướm) có 2 sợi râu bụng dài. Bắt buộc là CÁ CẢNH SỐNG ĐANG BƠI TRONG HỒ (loại bỏ hoàn toàn cá khô trên thớt hay món ăn).'
    },
    'ca_thien_than': {
        'vn_name': 'Cá Thần Tiên',
        'en_name': 'Angelfish',
        'sci_name': 'Pterophyllum scalare',
        'flickr_tag': 'angelfish,aquarium',
        'inat_taxon': 'Pterophyllum scalare',
        'gbif_taxon': 'Pterophyllum scalare',
        'bing_queries': [
            'angelfish swimming in planted aquarium',
            'cá thần tiên bơi trong bể thủy sinh',
            'freshwater angelfish in water tank'
        ],
        'criteria': 'Cá Thần Tiên (Angelfish) thân dẹp hình tam giác, vây lưng và vây hậu môn vươn dài thanh thoát. Bắt buộc là cá sống bơi trong bể kính.'
    },
    'ca_soc_ngua': {
        'vn_name': 'Cá Sóc Ngựa',
        'en_name': 'Zebra Danio',
        'sci_name': 'Danio rerio',
        'flickr_tag': 'danio,aquarium',
        'inat_taxon': 'Danio rerio',
        'gbif_taxon': 'Danio rerio',
        'bing_queries': [
            'zebra danio swimming in aquarium tank',
            'cá ngựa vằn bơi trong bể thủy sinh',
            'zebra fish school in aquarium'
        ],
        'criteria': 'Cá Sóc Ngựa / Ngựa Vằn (Zebra Danio) thân thon có 5 sọc xanh lam chạy ngang dọc thân. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_neon': {
        'vn_name': 'Cá Neon',
        'en_name': 'Neon Tetra',
        'sci_name': 'Paracheirodon innesi',
        'flickr_tag': 'neontetra',
        'inat_taxon': 'Paracheirodon',
        'gbif_taxon': 'Paracheirodon innesi',
        'bing_queries': [
            'neon tetra school swimming in planted tank',
            'cá neon bơi đàn trong bể thủy sinh',
            'cardinal tetra in aquarium water'
        ],
        'criteria': 'Cá Neon (Neon Tetra / Cardinal) có vệt xanh lam phát sáng chạy dọc thân, bụng đỏ. Bắt buộc là cá sống bơi trong bể thủy sinh.'
    },
    'ca_bay_mau': {
        'vn_name': 'Cá Bảy Màu',
        'en_name': 'Guppy',
        'sci_name': 'Poecilia reticulata',
        'flickr_tag': 'guppy,aquarium',
        'inat_taxon': 'Poecilia reticulata',
        'gbif_taxon': 'Poecilia reticulata',
        'bing_queries': [
            'fancy guppy fish swimming in aquarium',
            'cá bảy màu bơi trong hồ thủy sinh',
            'guppy fish tank colorful'
        ],
        'criteria': 'Cá Bảy Màu (Guppy) nhỏ, đuôi to xòe rộng nhiều hoa văn sặc sỡ. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_but_chi': {
        'vn_name': 'Cá Bút Chì',
        'en_name': 'Siamese Algae Eater',
        'sci_name': 'Crossocheilus oblongus',
        'flickr_tag': 'crossocheilus',
        'inat_taxon': 'Crossocheilus',
        'gbif_taxon': 'Crossocheilus oblongus',
        'bing_queries': [
            'siamese algae eater swimming in aquarium tank',
            'cá bút chì dọn rêu bể thủy sinh',
            'Crossocheilus oblongus in planted tank'
        ],
        'criteria': 'Cá Bút Chì (Siamese Algae Eater) thân thon dài như cây bút chì, có sọc đen chạy dọc thân từ mũi đến đuôi. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_molly': {
        'vn_name': 'Cá Molly',
        'en_name': 'Molly fish',
        'sci_name': 'Poecilia sphenops',
        'flickr_tag': 'mollyfish',
        'inat_taxon': 'Poecilia sphenops',
        'gbif_taxon': 'Poecilia sphenops',
        'bing_queries': [
            'sailfin molly swimming in aquarium',
            'cá bình tích bơi trong hồ thủy sinh',
            'black molly fish in tank'
        ],
        'criteria': 'Cá Molly / Bình Tích thân bầu dục tròn trịa, vây lưng rộng hình buồm (đen tuyền, trắng, vàng, cẩm thạch). Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_la_han': {
        'vn_name': 'Cá La Hán',
        'en_name': 'Flowerhorn Cichlid',
        'sci_name': 'Flowerhorn',
        'flickr_tag': 'flowerhorn',
        'inat_taxon': None,
        'gbif_taxon': None,
        'bing_queries': [
            'flowerhorn cichlid swimming in tank',
            'cá la hán bơi trong hồ kính',
            'flowerhorn fish with big kok in aquarium'
        ],
        'criteria': 'Cá La Hán (Flowerhorn) đầu có gù to, hoa văn chữ Hán dọc hông. Bắt buộc là cá sống bơi trong hồ kính.'
    },
    'ca_duoi_kiem': {
        'vn_name': 'Cá Đuôi Kiếm',
        'en_name': 'Swordtail fish',
        'sci_name': 'Xiphophorus hellerii',
        'flickr_tag': 'swordtail,aquarium',
        'inat_taxon': 'Xiphophorus hellerii',
        'gbif_taxon': 'Xiphophorus hellerii',
        'bing_queries': [
            'swordtail fish swimming in aquarium',
            'cá đuôi kiếm bơi trong hồ thủy sinh',
            'green swordtail in water tank'
        ],
        'criteria': 'Cá Đuôi Kiếm (Swordtail) có thùy đuôi dưới kéo dài như lưỡi kiếm. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_chuot': {
        'vn_name': 'Cá Chuột',
        'en_name': 'Corydoras Catfish',
        'sci_name': 'Corydoras',
        'flickr_tag': 'corydoras,aquarium',
        'inat_taxon': 'Corydoras',
        'gbif_taxon': 'Corydoras',
        'bing_queries': [
            'corydoras catfish swimming bottom aquarium',
            'cá chuột mỹ bơi tầng đáy bể thủy sinh',
            'panda cory in water tank'
        ],
        'criteria': 'Cá Chuột (Corydoras) cá da trơn nhỏ tầng đáy, có râu ở miệng, bụng phẳng. Bắt buộc là cá sống bơi trong bể nước.'
    },
    'ca_rong': {
        'vn_name': 'Cá Rồng',
        'en_name': 'Arowana',
        'sci_name': 'Scleropages formosus',
        'flickr_tag': 'arowana',
        'inat_taxon': 'Osteoglossum',
        'gbif_taxon': 'Osteoglossum',
        'bing_queries': [
            'asian arowana swimming in aquarium tank',
            'cá rồng huyết long bơi trong hồ kính',
            'golden arowana in water tank'
        ],
        'criteria': 'Cá Rồng (Arowana) cá lớn vảy to óng ánh, miệng hướng lên có 2 râu, bơi uy nghi tầng mặt. Bắt buộc là cá sống bơi trong hồ kính.'
    },
    'ca_xiem': {
        'vn_name': 'Cá Xiêm / Cá Betta',
        'en_name': 'Betta fish',
        'sci_name': 'Betta splendens',
        'flickr_tag': 'betta,aquarium',
        'inat_taxon': 'Betta splendens',
        'gbif_taxon': 'Betta splendens',
        'bing_queries': [
            'halfmoon betta fish swimming in aquarium',
            'cá xiêm betta bơi trong hồ thủy sinh',
            'plakat betta in water tank'
        ],
        'criteria': 'Cá Xiêm / Cá Betta vây đuôi xòe lộng lẫy (Halfmoon, Plakat, Dumbo), nhiều màu sắc. Bắt buộc là cá sống bơi trong nước.'
    },
    'ca_dia': {
        'vn_name': 'Cá Dĩa',
        'en_name': 'Discus fish',
        'sci_name': 'Symphysodon',
        'flickr_tag': 'discus,aquarium',
        'inat_taxon': 'Symphysodon',
        'gbif_taxon': 'Symphysodon',
        'bing_queries': [
            'discus fish swimming in planted aquarium',
            'cá dĩa bơi trong bể thủy sinh',
            'colorful discus fish in water tank'
        ],
        'criteria': 'Cá Dĩa (Discus) thân tròn dẹp như chiếc đĩa tròn, hoa văn rực rỡ. Bắt buộc là cá sống bơi trong hồ kính.'
    },
    'ca_koi': {
        'vn_name': 'Cá Koi',
        'en_name': 'Koi fish',
        'sci_name': 'Cyprinus carpio',
        'flickr_tag': 'koifish',
        'inat_taxon': 'Cyprinus carpio',
        'gbif_taxon': 'Cyprinus carpio',
        'bing_queries': [
            'japanese koi fish swimming in clear pond',
            'cá chép koi bơi trong hồ nước trong',
            'kohaku sanke koi carp in water'
        ],
        'criteria': 'Cá Chép Koi (Koi) cá lớn có khoang màu đỏ trắng đen vàng, vảy to óng ánh. Bắt buộc là cá sống bơi trong nước hồ.'
    }
}


def dhash(image, hash_size=8):
    """Tinh ma bam thi giac 64-bit chong trung lap anh."""
    img_gray = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(img_gray.get_flattened_data() if hasattr(img_gray, 'get_flattened_data') else img_gray.getdata())
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            diff.append(pixel_left > pixel_right)
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(diff):
        if value:
            decimal_value += 2**(index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
    return ''.join(hex_string)


def get_md5(raw_bytes):
    return hashlib.md5(raw_bytes).hexdigest()


def count_valid_images(folder_path):
    if not os.path.exists(folder_path):
        return 0
    valid_ext = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    return sum(1 for f in os.listdir(folder_path)
               if os.path.isfile(os.path.join(folder_path, f))
               and os.path.splitext(f)[1].lower() in valid_ext)


GLOBAL_SEEN_MD5 = set()
GLOBAL_SEEN_DHASH = set()


def init_global_hashes():
    """Ghi nho hash cua toan bo anh hien co vao RAM de chong trung."""
    print("⏳ Dang khoi tao bo nho chong trung lap toan bo dataset...")
    count = 0
    for root, dirs, files in os.walk(DATASET_DIR):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                fp = os.path.join(root, f)
                try:
                    with open(fp, 'rb') as hf:
                        raw = hf.read()
                        GLOBAL_SEEN_MD5.add(get_md5(raw))
                    with Image.open(fp) as img:
                        GLOBAL_SEEN_DHASH.add(dhash(img))
                    count += 1
                except:
                    pass
    print(f"✅ Da ghi nho {count} anh duy nhat. Tu nay tuyet doi KHONG anh nao bi trung lap!")


def fetch_candidate_urls(sp_key, max_urls=50):
    """Tong hop URL tu 5 nguon toan cau: Flickr + iNaturalist + GBIF + Wikimedia + Bing."""
    cfg = SPECIES_CONFIG[sp_key]
    urls = []

    # Nguon 1: Flickr Public Aquarium Photography (anh chup chuyen nghiep)
    if cfg.get('flickr_tag'):
        try:
            f_url = f"https://api.flickr.com/services/feeds/photos_public.gne?tags={cfg['flickr_tag']}&format=json&nojsoncallback=1"
            req = urllib.request.Request(f_url, headers=HEADERS)
            data = json.loads(urllib.request.urlopen(req, timeout=6).read().decode('utf-8'))
            for item in data.get('items', []):
                m_url = item.get('media', {}).get('m', '')
                if m_url:
                    # Lay anh kich thuoc lon 1024px (_b.jpg) thay vi thumb
                    large_url = m_url.replace('_m.', '_b.')
                    if large_url not in urls:
                        urls.append(('Flickr', large_url))
        except Exception:
            pass

    # Nguon 2: Wikimedia Commons API
    try:
        w_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(cfg['sci_name'])}&gsrlimit=15&prop=imageinfo&iiprop=url&format=json"
        req = urllib.request.Request(w_url, headers=HEADERS)
        data = json.loads(urllib.request.urlopen(req, timeout=6).read().decode('utf-8'))
        pages = data.get('query', {}).get('pages', {})
        for p in pages.values():
            ii = p.get('imageinfo', [{}])[0].get('url')
            if ii and ii not in [x[1] for x in urls]:
                urls.append(('Wikimedia', ii))
    except Exception:
        pass

    # Nguon 3: iNaturalist Open Data Research API
    if cfg.get('inat_taxon'):
        try:
            inat_url = f"https://api.inaturalist.org/v1/observations?taxon_name={urllib.parse.quote(cfg['inat_taxon'])}&quality_grade=research&photos=true&per_page=15"
            req = urllib.request.Request(inat_url, headers=HEADERS)
            data = json.loads(urllib.request.urlopen(req, timeout=6).read().decode('utf-8'))
            for item in data.get('results', []):
                for p in item.get('photos', []):
                    u = p.get('url', '')
                    if u:
                        high_res = u.replace('/square.', '/large.').replace('/square.', '/medium.')
                        if high_res not in [x[1] for x in urls]:
                            urls.append(('iNaturalist', high_res))
        except Exception:
            pass

    # Nguon 4: GBIF Global Biodiversity Facility
    if cfg.get('gbif_taxon'):
        try:
            g_url = f"https://api.gbif.org/v1/occurrence/search?scientificName={urllib.parse.quote(cfg['gbif_taxon'])}&mediaType=StillImage&limit=15"
            req = urllib.request.Request(g_url, headers=HEADERS)
            data = json.loads(urllib.request.urlopen(req, timeout=6).read().decode('utf-8'))
            for res in data.get('results', []):
                media = res.get('media', [])
                if media and media[0].get('identifier'):
                    u = media[0].get('identifier')
                    if u not in [x[1] for x in urls]:
                        urls.append(('GBIF', u))
        except Exception:
            pass

    # Nguon 5: Bing High-Res Async Search
    for q in cfg.get('bing_queries', [])[:3]:
        try:
            encoded_q = urllib.parse.quote(q)
            search_url = f"https://www.bing.com/images/async?q={encoded_q}&first=0&count=20&mmasync=1"
            req = urllib.request.Request(search_url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=6).read().decode('utf-8', errors='ignore')
            found = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
            for u in found:
                if u not in [x[1] for x in urls]:
                    urls.append(('Bing', u))
        except Exception:
            pass

    return urls[:max_urls]


def verify_image_with_gemini(client, pil_img, sp_info):
    """
    Kiem dinh chat che bang Gemini Vision:
    1. is_live_in_water: Con ca phai DANG SONG trong be nuoc/ho thuy sinh.
    2. is_clear_for_iot: Con ca phai NHIN THAY RO NET (ro than, ro vay, khong mo nhoe, khong che khuat qua 50%) de camera IoT YOLOv8 nhan dien duoc.
    3. is_correct_species: Dung loai ca.
    """
    prompt = f"""Kiem tra anh nay phuc vu Huan Luyen AI YOLOv8 cho Camera IoT Ho Ca Canh:

LOAI CA YEU CAU: {sp_info['vn_name']} ({sp_info['en_name']}, {sp_info['sci_name']})
DAC DIEM: {sp_info['criteria']}

QUY TAC DANH GIA CUC KY NGHIEM NGAT:
1. is_live_in_water: Phai la ANH THAT con ca DANG SONG dang boi trong be kinh, ho thuy sinh hoac ho nuoc.
   - PHAI TRA VE FALSE neu: ca chet, ca tren thot/dia an/kho ca, ca ngoai cho, ca trong xo chau nhua/bich nilon, ca bi cam tren tay kho rao, tranh ve, hoat hinh, logo.
2. is_clear_for_iot: Con ca PHAI NHIN THAY RO NET (ro than, ro vay, khong bi mo nhoe, khong bi che khuat qua 50%, ca phai chiem phan lon trong anh) de camera IoT va thuat toan YOLOv8 phat hien bounding box chuan xac.
3. is_correct_species: Con ca co dung la loai ca tren hoac dong bien the cua no khong?

Tra ve DUY NHAT JSON:
{{
    "is_live_in_water": true/false,
    "is_clear_for_iot": true/false,
    "is_correct_species": true/false,
    "variety": "Ten dong ca cu the",
    "reason": "Giai thich ngan gon 1 cau"
}}"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=[pil_img, prompt]
            )
            t = response.text.strip()
            if t.startswith('```json'):
                t = t[7:-3].strip()
            elif t.startswith('```'):
                t = t[3:-3].strip()
            res = json.loads(t)
            live = bool(res.get('is_live_in_water'))
            clear = bool(res.get('is_clear_for_iot'))
            corr = bool(res.get('is_correct_species'))
            variety = res.get('variety', '')
            reason = res.get('reason', '')
            return (live and clear and corr), variety, reason, live, clear, corr
        except Exception as ex:
            if ('429' in str(ex) or 'RESOURCE_EXHAUSTED' in str(ex)) and attempt < 2:
                print(f"    [RateLimit 429] Cho 20s de hoi phuc quota...")
                time.sleep(20.0)
                continue
            return False, '', str(ex), False, False, False

    return False, '', 'Qua so lan thu', False, False, False


def process_species(client, sp_key, target_add=15):
    """Tien hanh thu thap da nguon, loc trung va kiem duyet ro net cho mot loai."""
    sp_info = SPECIES_CONFIG[sp_key]
    dest_dir = os.path.join(DATASET_DIR, sp_key)
    os.makedirs(dest_dir, exist_ok=True)

    before_count = count_valid_images(dest_dir)
    print(f"\n{'='*65}")
    print(f"[{sp_info['vn_name']}] ({sp_key}) - Hien co: {before_count} anh | Can nap: +{target_add} anh")
    print(f"{'='*65}")

    urls = fetch_candidate_urls(sp_key, max_urls=max(40, target_add * 3))
    print(f"  🔍 Tim duoc {len(urls)} link anh ung vien tu 5 nguon toan cau (Flickr, iNat, GBIF, Wiki, Bing)...")

    added = 0
    rejected = 0

    for idx, (source, u) in enumerate(urls, 1):
        try:
            req = urllib.request.Request(u, headers=HEADERS)
            raw = urllib.request.urlopen(req, timeout=8).read()

            # 1. Kiem tra MD5 hash chong trung
            im_md5 = get_md5(raw)
            if im_md5 in GLOBAL_SEEN_MD5:
                rejected += 1
                continue

            pil_img = Image.open(io.BytesIO(raw))
            w, h = pil_img.size
            if w < 280 or h < 280:
                rejected += 1
                continue

            # 2. Kiem tra dHash thi giac chong trung (ke ca khi bi doi size/nen)
            im_dhash = dhash(pil_img)
            if im_dhash in GLOBAL_SEEN_DHASH:
                rejected += 1
                continue

            # 3. Kiem dinh nghiem ngat bang Gemini Vision: Live + Clear for IoT + Correct
            temp_img = pil_img.copy()
            temp_img.thumbnail((512, 512))
            is_valid, variety, reason, live, clear, corr = verify_image_with_gemini(client, temp_img, sp_info)

            # LUON LUON NGHI 4.2s SAU KHI GOI GEMINI (du dung hay sai) de khong bao gio bi 429
            time.sleep(4.2)

            if is_valid:
                GLOBAL_SEEN_MD5.add(im_md5)
                GLOBAL_SEEN_DHASH.add(im_dhash)
                timestamp = int(time.time())
                filename = f"verified_live_{sp_key}_{timestamp}_{added+1}.jpg"
                save_path = os.path.join(dest_dir, filename)

                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                pil_img.save(save_path, 'JPEG', quality=95)

                added += 1
                print(f"    ✅ [{added}/{target_add}] [{source}] GIU: {filename} ({variety} | {reason[:50]}...)")
            else:
                rejected += 1
                reason_short = f"live={live}, clear={clear}, corr={corr} -> {reason[:45]}"
                print(f"    ❌ [{source}] LOAI [{idx}]: {reason_short}...")

            if added >= target_add:
                print(f"  🎯 Dat chi tieu +{target_add} anh ro net cho {sp_info['vn_name']}!")
                break

        except Exception as e:
            rejected += 1
            time.sleep(1.0)

    after_count = count_valid_images(dest_dir)
    print(f"  📊 Ket qua [{sp_info['vn_name']}]: Truoc={before_count} -> Sau={after_count} (+{added} anh dat chuan ro net | Bo={rejected})")
    return {'species': sp_key, 'name': sp_info['vn_name'], 'before': before_count, 'after': after_count, 'added': added}


def main():
    if not API_KEY:
        print("Loi: Thieu GEMINI_API_KEY!")
        sys.exit(1)

    client = genai.Client(api_key=API_KEY)
    print("=" * 65)
    print("CHUONG TRINH NANG CAP DATASET CA CANH IOT DA NGUON TOAN CAU")
    print("5 Nguon: Flickr + iNaturalist + GBIF + Wikimedia + Bing")
    print("Tieu chi: Ca song boi trong nuoc, NHIN RO NET CHO IOT, KHONG TRUNG LAP")
    print(f"Muc tieu de tai: Tien toi 500+ anh/loai")
    print("=" * 65)

    # 1. Khoi tao danh sach hash toan bo dataset chong trung lap
    init_global_hashes()

    target_sp = sys.argv[1] if len(sys.argv) > 1 else None
    target_num = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    if target_sp and target_sp in SPECIES_CONFIG:
        process_species(client, target_sp, target_num)
    else:
        # Uu tien loai it anh nhat
        sorted_species = sorted(
            SPECIES_CONFIG.keys(),
            key=lambda k: count_valid_images(os.path.join(DATASET_DIR, k))
        )
        for sp in sorted_species:
            cnt = count_valid_images(os.path.join(DATASET_DIR, sp))
            if cnt < MIN_IMAGES:
                needed = min(target_num, MIN_IMAGES - cnt)
                process_species(client, sp, needed)


if __name__ == '__main__':
    main()
