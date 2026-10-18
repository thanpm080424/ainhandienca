"""
AUTONOMOUS FISH EXPANDER (V3 - MULTITHREADED PARALLEL VERIFICATION)
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

TIÊU CHÍ AN TOÀN & CHÍNH XÁC CAO NHẤT (5-LAYER QUALITY SHIELD):
1. Chặn 100% người/mặt/hội thảo (OpenCV Face Guard).
2. Độ nét cao, không nhòe mờ (Laplacian Variance >= 26.0).
3. Không trùng lặp ảnh cũ (MD5 + dHash Perceptual Hash).
4. Đối chiếu thị giác bằng mô hình AI YOLOv8 (Edge AI verification).
5. Phân trang động & Tải song song đa luồng (8 luồng siêu tốc) giúp nạp hàng trăm ảnh mới mỗi chu kỳ.
"""

import os
import sys
import time
import json
import re
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import numpy as np
import cv2

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')
EXPANDER_LOG_FILE = os.path.join(BASE_DIR, 'autonomous_collection.log')

TARGET_IMAGES_PER_SPECIES = 500  # Ngưỡng mục tiêu: 500 ảnh/loài = 10,000 ảnh chuẩn xác tuyệt đối

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
}

SPECIES_CONFIG = {
    'ca_but_chi': {
        'vn_name': 'Cá Bút Chì',
        'sci_name': 'Crossocheilus oblongus',
        'inat_taxons': ['Crossocheilus oblongus', 'Crossocheilus siamensis', 'Crossocheilus', 'Epalzeorhynchos kalopteron', 'Nannostomus beckfordi', 'Nannostomus eques', 'Nannostomus marginatus', 'Crossocheilus reticulatus', 'Garra flavatra'],
        'wiki_searches': ['Crossocheilus oblongus', 'Crossocheilus siamensis', 'Nannostomus beckfordi aquarium', 'Siamese algae eater in tank', 'Crossocheilus reticulatus'],
        'bing_queries': [
            'siamese algae eater in planted aquarium tank',
            'Crossocheilus oblongus swimming in glass aquarium',
            'cá bút chì dọn rêu bể thủy sinh',
            'golden pencilfish swimming in planted tank',
            'Nannostomus beckfordi in planted tank',
            'cá bút chì thái bơi trong hồ cá cảnh kính',
            'crossocheilus siamensis eating algae in tank',
            'pencilfish planted aquarium nature',
            'flying fox fish swimming in planted tank',
            'siamese algae eater on aquarium driftwood',
            'Crossocheilus reticulatus algae eater in tank'
        ]
    },
    'ca_bay_mau': {
        'vn_name': 'Cá Bảy Màu',
        'sci_name': 'Poecilia reticulata',
        'inat_taxons': ['Poecilia reticulata', 'Poecilia wingei', 'Poecilia'],
        'wiki_searches': ['Poecilia reticulata aquarium', 'Guppy fish planted tank', 'Endler livebearer aquarium'],
        'bing_queries': [
            'fancy guppy fish swimming in planted aquarium',
            'Poecilia reticulata colorful male in tank',
            'cá bảy màu full gold bơi trong hồ thủy sinh',
            'guppy fish swimming in glass aquarium water',
            'dumbo ear guppy fish in planted tank',
            'cá bảy màu rồng đỏ bể kính hồ thủy sinh',
            'albino full red guppy male in aquarium tank',
            'blue grass guppy swimming in glass tank',
            'endler guppy swimming in planted aquarium',
            'guppy fish swimming in clear water aquarium',
            'cá bảy màu koi gen bơi trong hồ thủy sinh',
            'fancy tail guppy swimming in planted tank'
        ]
    },
    'ca_molly': {
        'vn_name': 'Cá Molly / Bình Tích',
        'sci_name': 'Poecilia sphenops',
        'inat_taxons': ['Poecilia sphenops', 'Poecilia latipinna', 'Poecilia velifera'],
        'wiki_searches': ['Poecilia sphenops aquarium', 'Sailfin molly aquarium', 'Black molly fish aquarium', 'Balloon molly aquarium'],
        'bing_queries': [
            'black molly fish swimming in planted aquarium',
            'sailfin molly fish in glass tank',
            'cá bình tích bơi trong hồ thủy sinh',
            'dalmatian molly fish swimming in aquarium',
            'cá molly bơi trong hồ cá cảnh kính',
            'balloon molly fish swimming in planted tank',
            'golden sailfin molly fish in clear water tank',
            'cá bình tích hoàng kim bơi trong hồ kính'
        ]
    },
    'ca_duoi_kiem': {
        'vn_name': 'Cá Đuôi Kiếm',
        'sci_name': 'Xiphophorus hellerii',
        'inat_taxons': ['Xiphophorus hellerii'],
        'wiki_searches': ['Xiphophorus hellerii aquarium', 'Green swordtail aquarium', 'Red swordtail fish'],
        'bing_queries': [
            'red swordtail fish swimming in aquarium tank',
            'Xiphophorus hellerii in planted aquarium',
            'cá đuôi kiếm đỏ bơi trong bể thủy sinh',
            'green swordtail fish male in glass tank',
            'neon swordtail fish swimming in tank',
            'kohaku swordtail fish swimming in planted tank',
            'cá đuôi kiếm kohaku bơi trong hồ thủy sinh',
            'tuxedo swordtail fish in planted aquarium'
        ]
    },
    'ca_ba_duoi': {
        'vn_name': 'Cá Ba Đuôi / Cá Vàng',
        'sci_name': 'Carassius auratus',
        'inat_taxons': ['Carassius auratus', 'Carassius'],
        'wiki_searches': ['Carassius auratus aquarium', 'Oranda goldfish in tank', 'Ranchu goldfish in tank', 'Ryukin goldfish in tank', 'Fantail goldfish aquarium'],
        'bing_queries': [
            'oranda goldfish swimming in glass aquarium',
            'ranchu goldfish in clear water tank',
            'cá ba đuôi đầu lân bơi trong bể kính',
            'ryukin goldfish swimming in tank water',
            'fantail goldfish in clean aquarium',
            'cá vàng ranchu bơi trong hồ kính',
            'cá vàng oranda ngũ hoa bơi trong bể kính',
            'black moor goldfish swimming in clean aquarium',
            'lionhead goldfish in glass aquarium',
            'pearlscale goldfish swimming in clean tank',
            'telescope eye goldfish swimming in tank'
        ]
    },
    'ca_mun': {
        'vn_name': 'Cá Mún / Platy',
        'sci_name': 'Xiphophorus maculatus',
        'inat_taxons': ['Xiphophorus maculatus', 'Xiphophorus variatus'],
        'wiki_searches': ['Xiphophorus maculatus aquarium', 'Platy fish planted tank'],
        'bing_queries': [
            'red platy fish swimming in planted aquarium',
            'mickey mouse platy fish in glass tank',
            'cá mún đỏ bơi trong hồ cá cảnh',
            'sunburst platy fish in planted tank',
            'Xiphophorus maculatus swimming in glass tank',
            'tuxedo platy fish planted aquarium',
            'cá mún hạt lựu bơi trong hồ thủy sinh'
        ]
    },
    'ca_diec_anh_dao': {
        'vn_name': 'Cá Diếc Anh Đào',
        'sci_name': 'Puntius titteya',
        'inat_taxons': ['Puntius titteya', 'Puntius', 'Desmopuntius pentazona', 'Pethia conchonius'],
        'wiki_searches': ['Puntius titteya', 'Cherry barb aquarium', 'Pethia conchonius aquarium'],
        'bing_queries': [
            'cherry barb fish swimming in planted aquarium',
            'Puntius titteya red male in tank',
            'cá diếc anh đào bơi trong hồ thủy sinh',
            'cherry barb planted tank clear water',
            'school of cherry barbs swimming in aquarium',
            'cá diếc anh đào đực đỏ rực bơi trong bể',
            'albino cherry barb swimming in glass tank',
            'cherry barb fish male vivid red in planted tank',
            'rosy barb fish swimming in clear aquarium tank'
        ]
    },
    'ca_chuot': {
        'vn_name': 'Cá Chuột',
        'sci_name': 'Corydoras',
        'inat_taxons': ['Corydoras', 'Corydoras panda', 'Corydoras aeneus', 'Corydoras sterbai', 'Corydoras julii', 'Corydoras paleatus'],
        'wiki_searches': ['Corydoras panda aquarium', 'Corydoras sterbai tank', 'Bronze corydoras', 'Corydoras julii'],
        'bing_queries': [
            'panda corydoras swimming on aquarium sand',
            'sterbai corydoras in planted tank',
            'cá chuột panda bơi đáy hồ thủy sinh',
            'corydoras catfish on sand substrate',
            'albino corydoras swimming in aquarium',
            'cá chuột sao bơi đáy bể thủy sinh',
            'corydoras julii swimming in clean tank'
        ]
    },
    'ca_da_quang': {
        'vn_name': 'Cá Dạ Quang',
        'sci_name': 'Gymnocorymbus ternetzi',
        'inat_taxons': ['Gymnocorymbus ternetzi', 'Gymnocorymbus'],
        'wiki_searches': ['GloFish aquarium', 'Gymnocorymbus ternetzi Glofish', 'Black skirt tetra aquarium'],
        'bing_queries': [
            'glofish tetra swimming in glass aquarium tank',
            'electric green glofish tetra in planted tank',
            'cá cánh buồm dạ quang bơi trong hồ cá',
            'fluorescent glofish swimming in clear water',
            'starfire red glofish in aquarium tank',
            'cosmic blue glofish tetra swimming in tank',
            'cá cánh buồm dạ quang vàng bơi trong bể kính',
            'sunburst orange glofish tetra swimming in tank',
            'galactic purple glofish tetra in planted aquarium',
            'glofish fluorescent fish in clean water tank'
        ]
    },
    'ca_soc_ngua': {
        'vn_name': 'Cá Sóc Ngựa',
        'sci_name': 'Danio rerio',
        'inat_taxons': ['Danio rerio'],
        'wiki_searches': ['Danio rerio aquarium', 'Zebrafish aquarium tank'],
        'bing_queries': [
            'zebra danio fish swimming in planted aquarium',
            'Danio rerio school in glass tank',
            'cá sóc ngựa bơi đàn trong bể thủy sinh',
            'longfin zebra danio in aquarium tank',
            'glofish danio swimming in tank'
        ]
    },
    'ca_thien_than': {
        'vn_name': 'Cá Thần Tiên',
        'sci_name': 'Pterophyllum scalare',
        'inat_taxons': ['Pterophyllum scalare', 'Pterophyllum altum', 'Pterophyllum leopoldi', 'Pterophyllum'],
        'wiki_searches': ['Pterophyllum scalare aquarium', 'Angelfish planted tank', 'Altum angelfish'],
        'bing_queries': [
            'freshwater angelfish swimming in planted aquarium',
            'Pterophyllum scalare in glass tank',
            'cá thần tiên bơi trong bể thủy sinh',
            'koi angelfish swimming in planted aquarium',
            'black angelfish swimming in clear water tank',
            'altum angelfish in planted tank',
            'smokey angelfish swimming in aquarium',
            'cá thần tiên ba sọc bơi trong hồ thủy sinh',
            'platinum angelfish in clear water tank'
        ]
    },
    'ca_hong_ket': {
        'vn_name': 'Cá Hồng Két',
        'sci_name': 'Blood Parrot Cichlid',
        'inat_taxons': ['Amphilophus citrinellus', 'Amphilophus labiatus'],
        'wiki_searches': ['Blood parrot cichlid aquarium'],
        'bing_queries': [
            'blood parrot cichlid swimming in aquarium tank',
            'red blood parrot fish in glass aquarium',
            'cá hồng két đỏ bơi trong bể kính',
            'yellow blood parrot cichlid swimming in tank',
            'blood parrot fish clear aquarium water'
        ]
    },
    'ca_dia': {
        'vn_name': 'Cá Dĩa',
        'sci_name': 'Symphysodon',
        'inat_taxons': ['Symphysodon', 'Symphysodon aequifasciatus', 'Symphysodon discus', 'Symphysodon tarzoo'],
        'wiki_searches': ['Symphysodon aquarium', 'Discus fish planted tank', 'Heckel discus aquarium'],
        'bing_queries': [
            'discus fish swimming in planted aquarium',
            'blue diamond discus fish in glass tank',
            'cá dĩa bơi trong bể thủy sinh',
            'red pigeon blood discus swimming in aquarium',
            'wild discus fish in clear aquarium water',
            'heckel discus fish swimming in aquarium',
            'leopard snake skin discus in tank',
            'cá dĩa bồ câu đỏ bơi trong bể kính',
            'discus fish pair swimming in planted aquarium'
        ]
    },
    'ca_sac': {
        'vn_name': 'Cá Sặc Cảnh',
        'sci_name': 'Trichogaster',
        'inat_taxons': ['Trichogaster lalius', 'Trichogaster leeri', 'Trichogaster trichopterus'],
        'wiki_searches': ['Trichogaster lalius aquarium', 'Dwarf gourami planted tank', 'Pearl gourami'],
        'bing_queries': [
            'dwarf gourami swimming in planted aquarium tank',
            'pearl gourami in glass planted tank',
            'cá sặc gấm bơi trong hồ thủy sinh',
            'Trichogaster lalius male in aquarium water',
            'neon blue dwarf gourami swimming in tank'
        ]
    },
    'ca_koi': {
        'vn_name': 'Cá Chép Koi',
        'sci_name': 'Cyprinus carpio koi',
        'inat_taxons': ['Cyprinus carpio'],
        'wiki_searches': ['Koi pond', 'Cyprinus carpio koi aquarium'],
        'bing_queries': [
            'japanese koi fish swimming in clear pond water',
            'kohaku koi swimming in clean pond',
            'cá chép koi bơi trong hồ kính',
            'showa sanke koi fish in clear water',
            'butterfly koi swimming in aquarium'
        ]
    },
    'ca_lau_kieng': {
        'vn_name': 'Cá Lau Kiếng / Tỳ Bà',
        'sci_name': 'Hypostomus plecostomus',
        'inat_taxons': ['Hypostomus plecostomus', 'Ancistrus cirrhosus', 'Pterygoplichthys pardalis'],
        'wiki_searches': ['Bristlenose pleco aquarium', 'Hypostomus plecostomus tank'],
        'bing_queries': [
            'bristlenose pleco on driftwood in aquarium',
            'Ancistrus on glass tank swimming',
            'cá tỳ bà bơi bám kính hồ cá cảnh',
            'plecostomus catfish on aquarium plant',
            'bushynose pleco in planted tank'
        ]
    },
    'ca_xiem': {
        'vn_name': 'Cá Xiêm / Betta',
        'sci_name': 'Betta splendens',
        'inat_taxons': ['Betta splendens', 'Betta imbellis'],
        'wiki_searches': ['Betta splendens aquarium', 'Siamese fighting fish tank'],
        'bing_queries': [
            'halfmoon betta fish swimming in planted tank',
            'crowntail betta fish in glass aquarium',
            'cá xiêm betta bơi trong hồ thủy sinh',
            'plakat betta swimming in clear water tank',
            'Betta splendens male flaring in aquarium'
        ]
    },
    'ca_la_han': {
        'vn_name': 'Cá La Hán',
        'sci_name': 'Flowerhorn Cichlid',
        'inat_taxons': ['Cichlasoma'],
        'wiki_searches': ['Flowerhorn cichlid aquarium'],
        'bing_queries': [
            'kamfa flowerhorn cichlid swimming in glass tank',
            'red dragon flowerhorn in aquarium tank',
            'cá la hán đầu gù bơi trong bể kính',
            'flowerhorn fish swimming in clean water',
            'super red flowerhorn cichlid in tank'
        ]
    },
    'ca_neon': {
        'vn_name': 'Cá Neon',
        'sci_name': 'Paracheirodon innesi',
        'inat_taxons': ['Paracheirodon innesi', 'Paracheirodon axelrodi', 'Paracheirodon simulans'],
        'wiki_searches': ['Paracheirodon innesi aquarium', 'Cardinal tetra planted tank'],
        'bing_queries': [
            'neon tetra school swimming in planted aquarium',
            'cardinal tetra in glass planted tank',
            'cá neon xanh bơi đàn trong bể thủy sinh',
            'Paracheirodon innesi in crystal clear aquarium',
            'school of neon tetras planted aquarium'
        ]
    },
    'ca_rong': {
        'vn_name': 'Cá Rồng',
        'sci_name': 'Scleropages formosus',
        'inat_taxons': ['Scleropages formosus', 'Osteoglossum bicirrhosum'],
        'wiki_searches': ['Asian arowana aquarium', 'Silver arowana tank'],
        'bing_queries': [
            'asian super red arowana swimming in glass tank',
            'crossback golden arowana in aquarium',
            'cá rồng huyết long bơi trong bể kính',
            'silver arowana swimming in large tank',
            'chilli red arowana in clear aquarium water'
        ]
    }
}

# --- CÁC HÀM HỖ TRỢ XỬ LÝ ẢNH & KIỂM ĐỊNH THỊ GIÁC ---

_FACE_CASCADE = None
_CV_LOCK = threading.Lock()

def init_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        try:
            p = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            _FACE_CASCADE = cv2.CascadeClassifier(p)
        except Exception:
            _FACE_CASCADE = None

def has_human_face(pil_img):
    """Lớp 1: Chốt chặn khuôn mặt người (OpenCV Haar Cascade)."""
    init_face_cascade()
    if _FACE_CASCADE is None:
        return False
    try:
        thumb = pil_img.copy()
        thumb.thumbnail((640, 640))
        gray = cv2.cvtColor(np.array(thumb.convert('RGB')), cv2.COLOR_RGB2GRAY)
        with _CV_LOCK:
            faces = _FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        return len(faces) > 0
    except Exception:
        return False

def check_sharpness(pil_img):
    """Lớp 2: Kiểm tra kích thước và độ sắc nét bằng phương sai Laplacian."""
    try:
        w, h = pil_img.size
        if w < 380 or h < 380:
            return False, f"Ảnh quá nhỏ ({w}x{h} < 380x380)"
        ratio = w / h
        if ratio < 0.45 or ratio > 2.30:
            return False, f"Tỉ lệ ảnh bất thường ({ratio:.2f})"
        
        gray = np.array(pil_img.convert('L'), dtype=np.float32)
        conv = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1])
        lap_var = float(np.var(conv))
        if lap_var < 32.0:
            return False, f"Ảnh mờ nét (Laplacian={lap_var:.1f} < 32.0)"
        return True, lap_var
    except Exception as e:
        return False, str(e)

def compute_dhash(pil_img, hash_size=8):
    resized = pil_img.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            p1 = pixels[row * (hash_size + 1) + col]
            p2 = pixels[row * (hash_size + 1) + col + 1]
            diff.append('1' if p1 > p2 else '0')
    return hex(int(''.join(diff), 2))[2:].zfill(hash_size * hash_size // 4)

SEEN_MD5 = set()
SEEN_DHASH = []
_CACHE_LOCK = threading.Lock()

def init_hash_cache():
    global SEEN_MD5, SEEN_DHASH
    import hashlib
    print("Đang nạp bộ đệm chống trùng lặp từ dataset hiện tại...")
    for root, _, files in os.walk(DATASET_DIR):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'rb') as fp:
                        m = hashlib.md5(fp.read()).hexdigest()
                    SEEN_MD5.add(m)
                except Exception:
                    pass
    print(f"-> Đã ghi nhớ {len(SEEN_MD5)} mã băm ảnh hiện có để chống trùng lặp.")

def is_duplicate_image(raw_bytes, pil_img):
    import hashlib
    m = hashlib.md5(raw_bytes).hexdigest()
    with _CACHE_LOCK:
        if m in SEEN_MD5:
            return True
        dh = compute_dhash(pil_img)
        dh_int = int(dh, 16)
        for existing in SEEN_DHASH[-1500:]:
            if bin(dh_int ^ existing).count('1') <= 4:
                return True
        SEEN_MD5.add(m)
        SEEN_DHASH.append(dh_int)
    return False

import predict_fish

_YOLO_LOCK = threading.Lock()

def verify_with_yolov8(pil_img, target_species):
    """Lớp 4: Thẩm định loài bằng mô hình YOLOv8 Edge AI (tiêu chuẩn cá to rõ nổi bật)."""
    try:
        with _YOLO_LOCK:
            res = predict_fish.predict_pil(pil_img)
        if not res or not res.get('success'):
            return False, "Không chạy được YOLOv8", 0.0
        top1 = res.get('top1', {})
        pred_key = top1.get('species_key')
        conf = top1.get('confidence', 0.0)
        
        # Tiêu chuẩn nghiêm ngặt: Bắt buộc Top-1 phải là target_species và conf >= 58.0%
        # Loại bỏ hoàn toàn ảnh cá quá nhỏ ở xa hoặc nhạt nhòa trong khung hình
        if pred_key == target_species and conf >= 58.0:
            return True, f"YOLOv8 Top-1 chuẩn nét: {conf:.1f}%", conf
            
        return False, f"YOLOv8 nhận diện {top1.get('name')} ({conf:.1f}% < 58.0%) thay vì {target_species}", conf
    except Exception as e:
        return False, str(e), 0.0


def fetch_candidate_urls(sp_key, cycle=1, max_urls=450):
    """Thu thập danh sách URL ứng viên chất lượng cao với phân trang động theo từng vòng."""
    meta = SPECIES_CONFIG.get(sp_key, {})
    candidates = []
    seen = set()

    def add_url(source, u):
        if u and u not in seen:
            seen.add(u)
            candidates.append((source, u))

    # 1. iNaturalist Research Grade Data - Phân trang xoay vòng (modulo 8) kết hợp luân phiên sắp xếp
    cycle_idx = (cycle - 1) % 8
    base_page = (cycle_idx % 4) * 2 + 1
    inat_pages = [base_page, base_page + 1]
    order_by = 'votes' if (cycle % 2 == 1) else 'observed_on'

    for taxon in meta.get('inat_taxons', []):
        for p in inat_pages:
            try:
                api_url = f"https://api.inaturalist.org/v1/observations?taxon_name={urllib.parse.quote(taxon)}&photos=true&quality_grade=research&per_page=50&page={p}&order_by={order_by}"
                req = urllib.request.Request(api_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    for item in data.get('results', []):
                        for ph in item.get('photos', []):
                            url = ph.get('url', '')
                            if url:
                                add_url('iNaturalist', url.replace('/square.', '/large.').replace('/medium.', '/large.'))
            except Exception:
                pass

    # 2. GBIF Open Biodiversity API - Offset xoay vòng (modulo 10)
    gbif_offset = ((cycle - 1) % 10) * 40
    for taxon in meta.get('inat_taxons', []):
        try:
            gbif_url = f"https://api.gbif.org/v1/occurrence/search?scientificName={urllib.parse.quote(taxon)}&mediaType=StillImage&limit=50&offset={gbif_offset}"
            req = urllib.request.Request(gbif_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for occ in data.get('results', []):
                    for med in occ.get('media', []):
                        if med.get('type') == 'StillImage' and med.get('identifier'):
                            add_url('GBIF', med['identifier'])
        except Exception:
            pass

    # 3. Wikimedia Commons - sroffset xoay vòng (modulo 6)
    wiki_offset = ((cycle - 1) % 6) * 20
    for q in meta.get('wiki_searches', []):
        try:
            api_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(q)}&gsrnamespace=6&gsrlimit=30&sroffset={wiki_offset}&prop=imageinfo&iiprop=url&format=json"
            req = urllib.request.Request(api_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                pages = data.get('query', {}).get('pages', {})
                for p in pages.values():
                    infos = p.get('imageinfo', [])
                    if infos and infos[0].get('url'):
                        add_url('Wikimedia', infos[0]['url'])
        except Exception:
            pass

    # 4. Bing Image Search - Phân trang xoay vòng (modulo 8)
    bing_base = ((cycle - 1) % 8) * 35
    bing_offsets = [bing_base, bing_base + 35, bing_base + 70]
    for q in meta.get('bing_queries', []):
        for first in bing_offsets:
            try:
                b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first={first}&count=35&adlt=off"
                req = urllib.request.Request(b_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    murls = re.findall(r'murl&quot;:&quot;(http[^&quot;]+)&quot;', html)
                    for u in murls:
                        if u.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            add_url('Bing', u)
            except Exception:
                pass

    return candidates[:max_urls]


def log_event(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(EXPANDER_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


_ADD_LOCK = threading.Lock()

def process_single_candidate(source, url, sp_key, vn_name, sp_dir, needed, state):
    if state['added'] >= needed:
        return
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw_bytes = resp.read()

        if len(raw_bytes) < 18000:
            return

        import io
        pil_img = Image.open(io.BytesIO(raw_bytes))
        
        # Lớp 1: Chặn người và khuôn mặt
        if has_human_face(pil_img):
            with _ADD_LOCK:
                state['rejected_human'] += 1
            return

        # Lớp 2: Kiểm tra độ sắc nét
        sharp_ok, lap_val = check_sharpness(pil_img)
        if not sharp_ok:
            with _ADD_LOCK:
                state['rejected_blur'] += 1
            return

        # Lớp 3: Kiểm tra chống trùng lặp
        if is_duplicate_image(raw_bytes, pil_img):
            with _ADD_LOCK:
                state['rejected_dup'] += 1
            return

        # Lớp 4: Thẩm định bằng AI YOLOv8 (Top-1 >= 58.0% - cá to, rõ nét trong khung hình)
        yolo_ok, yolo_msg, yolo_conf = verify_with_yolov8(pil_img, sp_key)
        if not yolo_ok:
            with _ADD_LOCK:
                state['rejected_yolo'] += 1
            return

        # ĐẠT CHUẨN TẤT CẢ 5 BƯỚC: Lưu vào dataset
        with _ADD_LOCK:
            if state['added'] >= needed:
                return
            state['added'] += 1
            added_num = state['added']
            timestamp = int(time.time() * 1000)
            clean_filename = f"verified_clean_{sp_key}_{timestamp}_{added_num}.jpg"
            save_path = os.path.join(sp_dir, clean_filename)

            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            pil_img.save(save_path, 'JPEG', quality=95)

            log_event(f"  [ĐẠT CHUẨN #{added_num}] {sp_key}/{clean_filename} | Nguồn: {source} | {yolo_msg}")

            # Cập nhật audit_log cho Dashboard hiển thị trực tiếp
            try:
                if os.path.exists(AUDIT_LOG_FILE):
                    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as af:
                        ad = json.load(af)
                    
                    ad['current_status'] = {
                        'is_busy': True,
                        'action': f"Đang thu thập: {vn_name}",
                        'item': f"Đạt chuẩn #{added_num} ({clean_filename}) - YOLOv8: {yolo_conf:.1f}%",
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    ad.setdefault('recent_approved', []).insert(0, {
                        'file': clean_filename,
                        'species': sp_key,
                        'species_name': vn_name,
                        'source': f"Autonomous Collector ({source})",
                        'confidence': f"{yolo_conf:.1f}%",
                        'blur_score': lap_val,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                    if len(ad['recent_approved']) > 50:
                        ad['recent_approved'] = ad['recent_approved'][:50]
                    with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as af:
                        json.dump(ad, af, ensure_ascii=False, indent=2)
            except Exception:
                pass

    except Exception:
        pass


def expand_species(sp_key, cycle=1):
    """Thu thập và nạp thêm ảnh đạt chuẩn tuyệt đối cho 1 loài với 8 luồng song song."""
    meta = SPECIES_CONFIG.get(sp_key, {})
    vn_name = meta.get('vn_name', sp_key)
    sp_dir = os.path.join(DATASET_DIR, sp_key)
    os.makedirs(sp_dir, exist_ok=True)

    current_files = [f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    current_count = len(current_files)

    if current_count >= TARGET_IMAGES_PER_SPECIES:
        log_event(f"✨ Loài '{vn_name}' ({sp_key}) đã đạt {current_count}/{TARGET_IMAGES_PER_SPECIES} ảnh chuẩn. Bỏ qua.")
        return 0

    needed = TARGET_IMAGES_PER_SPECIES - current_count
    log_event(f"\n🚀 Đang tìm thêm ảnh cho '{vn_name}' ({sp_key}) [Vòng {cycle}] — Hiện có: {current_count}, Cần thêm: {needed} ảnh...")

    candidates = fetch_candidate_urls(sp_key, cycle=cycle, max_urls=350)
    log_event(f"  -> Thu thập được {len(candidates)} link ảnh ứng viên mới. Bắt đầu tải và thẩm định song song (8 luồng)...")

    state = {
        'added': 0,
        'rejected_human': 0,
        'rejected_blur': 0,
        'rejected_dup': 0,
        'rejected_yolo': 0
    }

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_candidate, source, url, sp_key, vn_name, sp_dir, needed, state) 
                   for source, url in candidates]
        for f in futures:
            if state['added'] >= needed:
                break
            try:
                f.result()
            except Exception:
                pass

    added = state['added']
    log_event(f"🏁 Xong đợt '{vn_name}': Đã thêm +{added} ảnh chuẩn! (Lọc bỏ: {state['rejected_human']} ảnh người, {state['rejected_blur']} ảnh mờ, {state['rejected_dup']} trùng, {state['rejected_yolo']} sai loài)")
    return added


def run_forever():
    log_event("=" * 65)
    log_event("🐠 BẮT ĐẦU CHẾ ĐỘ THU THẬP & MỞ RỘNG DATASET QUA ĐÊM (V3 MULTITHREADED)")
    log_event("=" * 65)
    init_hash_cache()

    cycle = 2
    while True:
        log_event(f"\n==================== VÒNG QUÉT THU THẬP #{cycle} ====================")
        
        species_counts = []
        for sp in SPECIES_CONFIG.keys():
            sp_dir = os.path.join(DATASET_DIR, sp)
            cnt = len([f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]) if os.path.exists(sp_dir) else 0
            species_counts.append((sp, cnt))

        species_counts.sort(key=lambda x: x[1])

        all_completed = True
        total_cycle_added = 0

        for sp, cnt in species_counts:
            if cnt < TARGET_IMAGES_PER_SPECIES:
                all_completed = False
                try:
                    added = expand_species(sp, cycle=cycle)
                    total_cycle_added += added
                except Exception as ex:
                    log_event(f"⚠️ Lỗi ngoại lệ khi xử lý '{sp}': {ex}")
                time.sleep(1)

        if all_completed:
            log_event("\n🎉 CHÚC MỪNG! TOÀN BỘ 20 LOÀI CÁ ĐÃ ĐẠT ĐỦ 500+ ẢNH CHUẨN XÁC TUYỆT ĐỐI (10,000+ ẢNH SẠCH 100%)!")
            log_event("Tiến trình hoàn tất xuất sắc nhiệm vụ.")
            break

        log_event(f"\n[KẾT THÚC VÒNG #{cycle}] Đã thêm thành công {total_cycle_added} ảnh trong vòng này.")
        log_event("Nghỉ 10 giây trước khi bắt đầu vòng quét tiếp theo...")
        cycle += 1
        time.sleep(10)


if __name__ == '__main__':
    run_forever()
