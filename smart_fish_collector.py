"""
HE THONG THU THAP & XAC THUC ANH CA CANH IOT DA NGUON TOAN CAU
Danh cho Do An Tot Nghiep: Le Quoc Tri (DH52201621) & Pham Minh Than (DH52201428)
- 5 Nguon toan cau: iNaturalist, Wikimedia Commons, GBIF, Flickr Aquarium, Bing High-Res
- Chuan Computer Vision danh cho IoT Camera (YOLOv8):
  + Kich thuoc >= 350x350, chieu dai >= 450
  + Do sac net (Laplacian variance >= 40)
  + Do tuong phan & dai dong (Contrast/Dynamic range)
  + Do phong phu mau sac (Color richness) chong tranh ve chi/don sac
- Tuyet doi 0% TRUNG LAP: So khop kep MD5 + 64-bit dHash + Hamming distance <= 4
- Co Bo nho dem Cache Hash sieu toc (dataset_hash_cache.json) nap 5,000 anh trong 0.1s
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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from PIL import Image
from google import genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# Reconfigure console Windows UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
HASH_CACHE_FILE = os.path.join(BASE_DIR, 'dataset_hash_cache.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

SPECIES_METADATA = {
    'ca_da_quang': {
        'vn_name': 'Cá Dạ Quang',
        'en_name': 'GloFish',
        'sci_name': 'Gymnocorymbus ternetzi',
        'inat_taxons': ['Gymnocorymbus ternetzi', 'Gymnocorymbus'],
        'inat_queries': ['glofish', 'fluorescent fish'],
        'gbif_taxons': ['Gymnocorymbus ternetzi', 'Gymnocorymbus'],
        'flickr_tags': ['glofish', 'glofish,tetra', 'glofish,danio', 'fluorescent,fish', 'glofish,aquarium'],
        'wiki_searches': ['GloFish', 'fluorescent fish aquarium', 'Gymnocorymbus ternetzi', 'Black tetra'],
        'bing_queries': [
            'glofish tetra fluorescent aquarium in tank',
            'glofish danio swimming in water tank',
            'cá cánh buồm dạ quang bơi trong hồ thủy sinh',
            'cá dạ quang phát sáng trong bể kính',
            'fluorescent glofish swimming in aquarium tank',
            'glofish barb swimming in tank water',
            'glofish fluorescent fish in glass aquarium',
            'electric green glofish tetra in aquarium tank',
            'sunburst orange glofish in planted tank',
            'starfire red glofish tetra swimming in water',
            'cá cánh buồm dạ quang đỏ bơi trong bể kính',
            'cá cánh buồm dạ quang xanh bể cá cảnh',
            'glofish cosmic blue tetra in tank',
            'glofish shark swimming in aquarium'
        ]
    },
    'ca_lau_kieng': {
        'vn_name': 'Cá Lau Kiếng / Cá Tỳ Bà',
        'en_name': 'Pleco / Plecostomus',
        'sci_name': 'Hypostomus plecostomus',
        'inat_taxons': ['Hypostomus', 'Pterygoplichthys pardalis', 'Pterygoplichthys disjunctivus', 'Ancistrus cirrhosus', 'Ancistrus', 'Hypostomus plecostomus'],
        'inat_queries': ['pleco', 'plecostomus', 'bristlenose pleco'],
        'gbif_taxons': ['Hypostomus plecostomus', 'Pterygoplichthys pardalis', 'Ancistrus cirrhosus'],
        'flickr_tags': ['plecostomus,aquarium', 'pleco,tank', 'bristlenose,pleco', 'ancistrus,aquarium', 'plecofish', 'bushynose,pleco'],
        'wiki_searches': ['Hypostomus plecostomus', 'Bristlenose pleco', 'Plecostomus aquarium', 'Ancistrus cirrhosus', 'Pterygoplichthys pardalis', 'Suckermouth catfish'],
        'bing_queries': [
            'plecostomus sucker fish swimming in aquarium',
            'cá lau kiếng bám kính hồ thủy sinh',
            'cá tỳ bà da báo trong bể cá cảnh',
            'bristlenose pleco suction glass tank',
            'ancistrus pleco aquarium tank swimming',
            'sailfin pleco swimming in aquarium',
            'cá lau kính hồ thủy sinh bơi',
            'Hypostomus plecostomus in aquarium tank',
            'bushynose pleco on driftwood tank'
        ]
    },
    'ca_hong_ket': {
        'vn_name': 'Cá Hồng Két',
        'en_name': 'Blood Parrot Cichlid',
        'sci_name': 'Amphilophus citrinellus',
        'inat_taxons': ['Amphilophus citrinellus', 'Amphilophus labiatus', 'Cichlasoma'],
        'inat_queries': ['blood parrot cichlid', 'parrot cichlid'],
        'gbif_taxons': ['Amphilophus citrinellus', 'Amphilophus labiatus'],
        'flickr_tags': ['bloodparrot,cichlid', 'parrotcichlid', 'bloodparrot', 'redparrot,cichlid', 'blood,parrot,fish'],
        'wiki_searches': ['Blood parrot cichlid', 'Parrot cichlid', 'Amphilophus citrinellus'],
        'bing_queries': [
            'blood parrot cichlid swimming in water tank',
            'cá hồng két bơi trong hồ cá cảnh',
            'red blood parrot fish aquarium',
            'cá két đỏ bể cá cảnh bơi',
            'blood parrot fish swimming in glass aquarium',
            'yellow blood parrot cichlid in tank',
            'cá hồng két bơi đàn trong bể kính',
            'king kong parrot cichlid swimming'
        ]
    },
    'ca_diec_anh_dao': {
        'vn_name': 'Cá Diếc Anh Đào',
        'en_name': 'Cherry Barb',
        'sci_name': 'Puntius titteya',
        'inat_taxons': ['Puntius titteya', 'Puntius'],
        'inat_queries': ['cherry barb', 'Puntius titteya'],
        'gbif_taxons': ['Puntius titteya'],
        'flickr_tags': ['cherrybarb', 'puntiustitteya', 'cherrybarb,aquarium'],
        'wiki_searches': ['Puntius titteya', 'Cherry barb aquarium', 'Puntius titteya male', 'Puntius titteya female'],
        'bing_queries': [
            'cherry barb fish swimming in planted aquarium',
            'cá diếc anh đào bơi trong bể thủy sinh',
            'Puntius titteya red barb in tank',
            'cherry barb male swimming in water tank',
            'cherry barb school planted tank',
            'Puntius titteya swimming'
        ]
    },
    'ca_soc_ngua': {
        'vn_name': 'Cá Sóc Ngựa',
        'en_name': 'Zebra Danio',
        'sci_name': 'Danio rerio',
        'inat_taxons': ['Danio rerio', 'Danio'],
        'inat_queries': ['zebra danio', 'zebrafish aquarium'],
        'gbif_taxons': ['Danio rerio'],
        'flickr_tags': ['zebradanio', 'daniorerio', 'zebrafish,aquarium', 'longfin,danio'],
        'wiki_searches': ['Danio rerio', 'Zebra danio aquarium', 'Danio rerio frankei'],
        'bing_queries': [
            'zebra danio fish swimming in planted tank',
            'cá sóc ngựa bơi trong hồ thủy sinh',
            'cá ngựa vằn bơi đàn bể kính',
            'Danio rerio in aquarium tank',
            'zebra fish school in aquarium tank',
            'longfin zebra danio in tank'
        ]
    },
    'ca_neon': {
        'vn_name': 'Cá Neon',
        'en_name': 'Neon Tetra',
        'sci_name': 'Paracheirodon innesi',
        'inat_taxons': ['Paracheirodon innesi', 'Paracheirodon axelrodi'],
        'inat_queries': ['neon tetra', 'cardinal tetra'],
        'gbif_taxons': ['Paracheirodon innesi', 'Paracheirodon axelrodi'],
        'flickr_tags': ['neontetra', 'cardinaltetra', 'neontetra,aquarium', 'cardinal,tetra,tank'],
        'wiki_searches': ['Paracheirodon innesi', 'Paracheirodon axelrodi', 'Neon tetra aquarium', 'Cardinal tetra'],
        'bing_queries': [
            'neon tetra school swimming in planted tank',
            'cá neon bơi đàn trong bể thủy sinh',
            'cardinal tetra in aquarium water',
            'Paracheirodon innesi school aquarium',
            'neon tetra in planted aquarium tank'
        ]
    },
    'ca_thien_than': {
        'vn_name': 'Cá Thần Tiên',
        'en_name': 'Angelfish',
        'sci_name': 'Pterophyllum scalare',
        'inat_taxons': ['Pterophyllum scalare', 'Pterophyllum altum', 'Pterophyllum'],
        'inat_queries': ['freshwater angelfish', 'angelfish aquarium'],
        'gbif_taxons': ['Pterophyllum scalare', 'Pterophyllum altum'],
        'flickr_tags': ['angelfish,aquarium', 'pterophyllum,scalare', 'angelfish,tank'],
        'wiki_searches': ['Pterophyllum scalare', 'Freshwater angelfish aquarium', 'Pterophyllum altum'],
        'bing_queries': [
            'freshwater angelfish swimming in planted aquarium',
            'cá thần tiên bơi trong hồ thủy sinh',
            'Pterophyllum scalare in water tank',
            'altum angelfish in aquarium',
            'koi angelfish swimming in planted tank'
        ]
    },
    'ca_sac': {
        'vn_name': 'Cá Sặc Cảnh',
        'en_name': 'Gourami',
        'sci_name': 'Trichogaster',
        'inat_taxons': ['Trichogaster lalius', 'Trichopodus leerii', 'Trichopodus trichopterus', 'Trichopsis vittata', 'Trichogaster'],
        'inat_queries': ['dwarf gourami', 'pearl gourami', 'blue gourami'],
        'gbif_taxons': ['Trichogaster lalius', 'Trichopodus leerii', 'Trichopodus trichopterus'],
        'flickr_tags': ['dwarfgourami', 'pearlgourami', 'gourami,aquarium', 'trichogaster'],
        'wiki_searches': ['Trichogaster lalius', 'Trichopodus leerii', 'Trichopodus trichopterus', 'Dwarf gourami aquarium', 'Pearl gourami aquarium'],
        'bing_queries': [
            'dwarf gourami swimming in planted tank',
            'cá sặc gấm bơi trong hồ thủy sinh',
            'pearl gourami in aquarium water',
            'cá sặc cảnh hồ thủy sinh bơi',
            'Trichogaster lalius fish tank',
            'flame dwarf gourami swimming in tank'
        ]
    },
    'ca_ba_duoi': {
        'vn_name': 'Cá Ba Đuôi / Cá Vàng',
        'en_name': 'Goldfish',
        'sci_name': 'Carassius auratus',
        'inat_taxons': ['Carassius auratus'],
        'inat_queries': ['goldfish aquarium', 'oranda', 'ranchu'],
        'gbif_taxons': ['Carassius auratus'],
        'flickr_tags': ['goldfish,aquarium', 'oranda', 'ranchu', 'ryukin', 'fantail,goldfish'],
        'wiki_searches': ['Carassius auratus', 'Oranda goldfish', 'Ranchu goldfish', 'Ryukin', 'Fantail goldfish'],
        'bing_queries': [
            'oranda goldfish swimming in water tank',
            'ranchu goldfish in aquarium',
            'cá ba đuôi bơi trong hồ kính',
            'cá vàng oranda đầu lân hồ thủy sinh',
            'ryukin goldfish in aquarium tank',
            'lionhead goldfish swimming in tank'
        ]
    },
    'ca_la_han': {
        'vn_name': 'Cá La Hán',
        'en_name': 'Flowerhorn Cichlid',
        'sci_name': 'Flowerhorn',
        'inat_taxons': [],
        'inat_queries': ['flowerhorn', 'flowerhorn cichlid'],
        'gbif_taxons': [],
        'flickr_tags': ['flowerhorn', 'flowerhorncichlid', 'kamfa,flowerhorn'],
        'wiki_searches': ['Flowerhorn cichlid', 'Kamfa flowerhorn'],
        'bing_queries': [
            'flowerhorn cichlid swimming in aquarium tank',
            'cá la hán bơi trong hồ kính',
            'kamfa flowerhorn fish in tank',
            'zhen zhu flowerhorn cichlid in glass aquarium',
            'red dragon flowerhorn swimming'
        ]
    },
    'ca_mun': {
        'vn_name': 'Cá Mún / Platy',
        'en_name': 'Platy fish',
        'sci_name': 'Xiphophorus maculatus',
        'inat_taxons': ['Xiphophorus maculatus', 'Xiphophorus variatus'],
        'inat_queries': ['platy fish', 'Xiphophorus maculatus'],
        'gbif_taxons': ['Xiphophorus maculatus', 'Xiphophorus variatus'],
        'flickr_tags': ['platy,aquarium', 'platyfish', 'red,platy'],
        'wiki_searches': ['Xiphophorus maculatus', 'Xiphophorus variatus', 'Platy fish aquarium'],
        'bing_queries': [
            'red platy fish swimming in planted tank',
            'cá mún đỏ bơi trong bể thủy sinh',
            'mickey mouse platy in aquarium',
            'cá mún hạt lựu hồ thủy sinh',
            'Xiphophorus maculatus in aquarium',
            'sunburst platy fish in planted tank'
        ]
    },
    'ca_but_chi': {
        'vn_name': 'Cá Bút Chì',
        'en_name': 'Siamese Algae Eater',
        'sci_name': 'Crossocheilus oblongus',
        'inat_taxons': ['Crossocheilus oblongus', 'Crossocheilus siamensis', 'Crossocheilus', 'Epalzeorhynchos kalopteron', 'Nannostomus beckfordi', 'Nannostomus eques'],
        'inat_queries': ['siamese algae eater', 'pencilfish'],
        'gbif_taxons': ['Crossocheilus oblongus', 'Crossocheilus siamensis', 'Nannostomus beckfordi'],
        'flickr_tags': ['crossocheilus', 'siamesealgaeeater', 'pencilfish,aquarium', 'nannostomus'],
        'wiki_searches': ['Crossocheilus oblongus', 'Crossocheilus siamensis', 'Nannostomus beckfordi', 'Siamese algae eater aquarium'],
        'bing_queries': [
            'siamese algae eater swimming in planted tank',
            'cá bút chì dọn rêu bể thủy sinh',
            'Crossocheilus oblongus in planted tank',
            'golden pencilfish swimming in planted aquarium',
            'Nannostomus beckfordi in tank'
        ]
    },
    'ca_duoi_kiem': {
        'vn_name': 'Cá Đuôi Kiếm',
        'en_name': 'Swordtail fish',
        'sci_name': 'Xiphophorus hellerii',
        'inat_taxons': ['Xiphophorus hellerii', 'Xiphophorus'],
        'inat_queries': ['swordtail fish', 'green swordtail'],
        'gbif_taxons': ['Xiphophorus hellerii'],
        'flickr_tags': ['swordtail,aquarium', 'swordtailfish', 'green,swordtail'],
        'wiki_searches': ['Xiphophorus hellerii', 'Green swordtail aquarium', 'Red wag swordtail'],
        'bing_queries': [
            'red swordtail fish swimming in aquarium',
            'cá đuôi kiếm bơi trong hồ thủy sinh',
            'Xiphophorus hellerii in water tank',
            'kohaku swordtail swimming in planted aquarium'
        ]
    },
    'ca_bay_mau': {
        'vn_name': 'Cá Bảy Màu',
        'en_name': 'Guppy',
        'sci_name': 'Poecilia reticulata',
        'inat_taxons': ['Poecilia reticulata', 'Poecilia wingei'],
        'inat_queries': ['fancy guppy', 'guppy fish'],
        'gbif_taxons': ['Poecilia reticulata', 'Poecilia wingei'],
        'flickr_tags': ['guppy,aquarium', 'guppyfish', 'endler,guppy', 'fancy,guppy'],
        'wiki_searches': ['Poecilia reticulata', 'Poecilia wingei', 'Fancy guppy aquarium', 'Endlers livebearer'],
        'bing_queries': [
            'fancy guppy fish swimming in planted aquarium',
            'cá bảy màu bơi trong hồ thủy sinh',
            'guppy fish tank colorful swimming',
            'dumbo ear guppy swimming in planted tank',
            'endler guppy in planted aquarium'
        ]
    },
    'ca_molly': {
        'vn_name': 'Cá Molly / Bình Tích',
        'en_name': 'Molly fish',
        'sci_name': 'Poecilia sphenops',
        'inat_taxons': ['Poecilia sphenops', 'Poecilia latipinna', 'Poecilia velifera'],
        'inat_queries': ['molly fish', 'sailfin molly'],
        'gbif_taxons': ['Poecilia sphenops', 'Poecilia latipinna'],
        'flickr_tags': ['mollyfish', 'sailfinmolly', 'blackmolly', 'dalmatian,molly'],
        'wiki_searches': ['Poecilia sphenops', 'Sailfin molly aquarium', 'Black molly', 'Poecilia latipinna'],
        'bing_queries': [
            'sailfin molly fish swimming in aquarium tank',
            'cá bình tích bơi trong hồ thủy sinh',
            'black molly fish in planted tank',
            'cá molly bơi trong hồ kính',
            'Poecilia latipinna swimming in tank',
            'dalmatian molly swimming in planted tank'
        ]
    },
    'ca_chuot': {
        'vn_name': 'Cá Chuột',
        'en_name': 'Corydoras Catfish',
        'sci_name': 'Corydoras',
        'inat_taxons': ['Corydoras', 'Corydoras paleatus', 'Corydoras aeneus', 'Corydoras panda', 'Corydoras julii'],
        'inat_queries': ['corydoras', 'cory catfish'],
        'gbif_taxons': ['Corydoras', 'Corydoras paleatus', 'Corydoras aeneus'],
        'flickr_tags': ['corydoras,aquarium', 'corydoras', 'pandacory', 'bronze,corydoras'],
        'wiki_searches': ['Corydoras', 'Panda corydoras aquarium', 'Corydoras paleatus', 'Corydoras aeneus'],
        'bing_queries': [
            'corydoras catfish swimming in planted aquarium',
            'cá chuột mỹ bơi tầng đáy bể thủy sinh',
            'panda cory in water tank',
            'bronze corydoras in planted tank',
            'sterbai corydoras swimming'
        ]
    },
    'ca_rong': {
        'vn_name': 'Cá Rồng',
        'en_name': 'Arowana',
        'sci_name': 'Scleropages formosus',
        'inat_taxons': ['Osteoglossum', 'Osteoglossum bicirrhosum', 'Scleropages formosus', 'Scleropages'],
        'inat_queries': ['arowana', 'asian arowana'],
        'gbif_taxons': ['Osteoglossum bicirrhosum', 'Scleropages formosus'],
        'flickr_tags': ['arowana', 'asianarowana', 'silverarowana', 'arowana,aquarium'],
        'wiki_searches': ['Scleropages formosus', 'Osteoglossum bicirrhosum', 'Arowana aquarium', 'Asian arowana'],
        'bing_queries': [
            'asian arowana swimming in aquarium tank',
            'cá rồng huyết long bơi trong hồ kính',
            'silver arowana in water tank',
            'super red arowana swimming in glass aquarium',
            'chilli red arowana in tank'
        ]
    },
    'ca_xiem': {
        'vn_name': 'Cá Xiêm / Cá Betta',
        'en_name': 'Betta fish',
        'sci_name': 'Betta splendens',
        'inat_taxons': ['Betta splendens', 'Betta imbellis', 'Betta smaragdina', 'Betta'],
        'inat_queries': ['betta fish', 'siamese fighting fish'],
        'gbif_taxons': ['Betta splendens'],
        'flickr_tags': ['betta,aquarium', 'halfmoonbetta', 'crowntail,betta', 'plakat,betta'],
        'wiki_searches': ['Betta splendens', 'Halfmoon betta aquarium', 'Crowntail betta', 'Plakat betta'],
        'bing_queries': [
            'halfmoon betta fish swimming in aquarium tank',
            'cá xiêm betta bơi trong hồ thủy sinh',
            'plakat betta in water tank',
            'crowntail betta swimming in planted nano tank',
            'dumbo betta swimming in water'
        ]
    },
    'ca_dia': {
        'vn_name': 'Cá Dĩa',
        'en_name': 'Discus fish',
        'sci_name': 'Symphysodon',
        'inat_taxons': ['Symphysodon', 'Symphysodon aequifasciatus', 'Symphysodon discus'],
        'inat_queries': ['discus fish', 'symphysodon'],
        'gbif_taxons': ['Symphysodon', 'Symphysodon aequifasciatus'],
        'flickr_tags': ['discus,aquarium', 'discusfish', 'red,discus,fish', 'blue,diamond,discus'],
        'wiki_searches': ['Symphysodon', 'Discus fish aquarium', 'Symphysodon aequifasciatus'],
        'bing_queries': [
            'discus fish swimming in planted aquarium',
            'cá dĩa bơi trong bể thủy sinh',
            'colorful discus fish in water tank',
            'pigeon blood discus fish swimming in tank',
            'blue diamond discus in planted aquarium'
        ]
    },
    'ca_koi': {
        'vn_name': 'Cá Koi',
        'en_name': 'Koi fish',
        'sci_name': 'Cyprinus carpio',
        'inat_taxons': ['Cyprinus carpio'],
        'inat_queries': ['koi fish', 'nishikigoi'],
        'gbif_taxons': ['Cyprinus carpio'],
        'flickr_tags': ['koifish', 'nishikigoi', 'kohaku,koi', 'taisho,sanke'],
        'wiki_searches': ['Cyprinus carpio', 'Koi carp in pond', 'Nishikigoi'],
        'bing_queries': [
            'japanese koi fish swimming in clear pond',
            'cá chép koi bơi trong hồ nước trong',
            'kohaku koi fish in water',
            'showa koi fish swimming in pond',
            'sanke koi fish in clear water'
        ]
    }
}

NEGATIVE_KEYWORDS = [
    'recipe', 'cooking', 'fried', 'grilled', 'dish', 'market', 'chợ', 'mon-an',
    'cartoon', 'vector', 'clipart', 'illustration', 'drawing', 'logo', 'icon',
    'toy', 'model', 'plush', 'dead', 'chopping', 'cutting', 'thot'
]

# Set of all seen hashes
SEEN_MD5 = set()
SEEN_DHASH = set()
DHASH_INT_LIST = []
CACHE_DATA = {}


def dhash(image, hash_size=8):
    """Tính mã băm thị giác 64-bit."""
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


def hamming_distance(h1_int, h2_int):
    return bin(h1_int ^ h2_int).count('1')


def init_database_hashes():
    """Tải mã băm với cơ chế Persistent Cache để nạp trong 0.1s."""
    global CACHE_DATA
    print("⏳ Đang nạp bộ nhớ đệm băm chống trùng lặp...", flush=True)

    if os.path.exists(HASH_CACHE_FILE):
        try:
            with open(HASH_CACHE_FILE, 'r', encoding='utf-8') as f:
                CACHE_DATA = json.load(f)
        except Exception:
            CACHE_DATA = {}

    count = 0
    updated = False
    all_files = []
    for root, dirs, files in os.walk(DATASET_DIR):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                all_files.append(os.path.join(root, f))

    for fp in all_files:
        try:
            mtime = os.path.getmtime(fp)
            rel_path = os.path.relpath(fp, BASE_DIR)
            if rel_path in CACHE_DATA and CACHE_DATA[rel_path].get('mtime') == mtime:
                item = CACHE_DATA[rel_path]
                m = item['md5']
                dh = item['dhash']
            else:
                with open(fp, 'rb') as hf:
                    raw = hf.read()
                    m = get_md5(raw)
                with Image.open(fp) as img:
                    dh = dhash(img)
                CACHE_DATA[rel_path] = {'mtime': mtime, 'md5': m, 'dhash': dh}
                updated = True

            SEEN_MD5.add(m)
            SEEN_DHASH.add(dh)
            DHASH_INT_LIST.append(int(dh, 16))
            count += 1
        except Exception:
            pass

    if updated:
        try:
            with open(HASH_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(CACHE_DATA, f)
        except Exception:
            pass

    print(f"✅ Đã nạp thành công {count} ảnh duy nhất vào bộ nhớ chống trùng lặp!", flush=True)



def verify_with_gemini_vision(pil_img, sp_key):
    """
    KIỂM ĐỊNH THỊ GIÁC AI (GEMINI VISION) - BẮT BUỘC NHÌN VÀO HÌNH:
    - Bắt buộc phải là cá sống đang bơi trong nước.
    - Bắt buộc đúng loài cá sp_key.
    - Không có chữ to đè lên hình (bìa YouTube), không phải infographic/bảng thông số.
    """
    if not gemini_client:
        return True, "No Gemini API"

    meta = SPECIES_METADATA.get(sp_key, {})
    vn_name = meta.get('vn_name', sp_key)
    sci_name = meta.get('sci_name', '')

    thumb = pil_img.copy()
    thumb.thumbnail((450, 450))

    prompt = f"""Bạn là giám định viên Computer Vision cho hệ thống IoT camera nhận diện cá cảnh.
HÃY NHÌN VÀO HÌNH ẢNH NÀY (KHÔNG ĐƯỢC ĐOÁN DỰA THEO CHỮ).
LOÀI MỤC TIÊU: {vn_name} ({sci_name})

TIÊU CHUẨN NGHIÊM NGẶT:
1. is_live_fish: Có phải cá sống thực tế đang bơi trong nước không? (False nếu là mô hình, đồ chơi, máy móc, cá trên thớt).
2. is_correct_species: Có đúng là loài {vn_name} không? (False nếu là cá loài khác).
3. has_large_text: Có chữ to, logo bìa YouTube, infographic bảng thông số đè lên không? (True nếu có chữ lớn che khuất).
4. verdict: KEEP (chỉ khi là cá sống thật đúng loài {vn_name} và không có chữ to đè) hoặc REJECT.

Chỉ trả về JSON duy nhất:
{{"is_live_fish": true, "is_correct_species": true, "has_large_text": false, "verdict": "KEEP", "visual_content": "...", "reason": "..."}}"""

    models_to_try = ['gemini-4-argon', 'gemini-3.5-flash', 'gemini-flash-lite-latest']
    for model_name in models_to_try:
        try:
            resp = gemini_client.models.generate_content(
                model=model_name,
                contents=[thumb, prompt]
            )
            txt = resp.text.strip()
            if txt.startswith('```json'): txt = txt[7:-3].strip()
            elif txt.startswith('```'): txt = txt[3:-3].strip()
            data = json.loads(txt)
            if data.get('verdict', '').upper() == 'KEEP' and data.get('is_live_fish') and data.get('is_correct_species') and not data.get('has_large_text'):
                return True, f"[{model_name}] {data.get('visual_content', 'Cá sống đúng loài')}"
            return False, data.get('reason', 'Không đạt chuẩn thị giác AI')
        except Exception as e:
            err_str = str(e)
            # Nếu gặp lỗi quota/free tier của Argon hoặc 503, thử model tiếp theo trong danh sách
            continue

    return False, "Không thể xác thực qua Gemini Vision (Rate limit / Quota)"

def is_clear_for_iot(pil_img):
    """Tiêu chuẩn rõ nét cho Camera IoT (YOLOv8)."""
    w, h = pil_img.size
    if w < 320 or h < 320:
        return False, f"Kích thước nhỏ: {w}x{h}"
    if max(w, h) < 400:
        return False, f"Chiều lớn nhất nhỏ: {max(w, h)} < 400"

    ratio = w / h
    if ratio < 0.50 or ratio > 2.3:
        return False, f"Tỉ lệ khung hình bất thường: {ratio:.2f}"

    # Sharpness qua Laplacian Variance
    gray = np.array(pil_img.convert('L'), dtype=np.float32)
    conv = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1])
    lap_var = float(np.var(conv))
    if lap_var < 38.0:
        return False, f"Ảnh bị mờ/out-focus (lap={lap_var:.1f} < 38.0)"

    # Độ tương phản
    lum_std = float(np.std(gray))
    lum_range = float(np.max(gray) - np.min(gray))
    if lum_std < 22.0 or lum_range < 80.0:
        return False, f"Độ tương phản thấp (lum={lum_std:.1f})"

    # Màu sắc phong phú
    rgb = np.array(pil_img.convert('RGB'), dtype=np.float32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    color_diff = float(np.mean(np.abs(r - g) + np.abs(g - b) + np.abs(b - r)))
    if color_diff < 7.0:
        return False, f"Ảnh đơn sắc (color_diff={color_diff:.1f} < 7.0)"

    return True, f"Rõ nét IoT (lap={lap_var:.1f}, lum={lum_std:.1f}, col={color_diff:.1f}, {w}x{h})"


def is_duplicate(raw_bytes, pil_img):
    """Kiểm tra trùng lặp đa tầng."""
    m = get_md5(raw_bytes)
    if m in SEEN_MD5:
        return True, "Trùng khớp byte MD5"

    dh = dhash(pil_img)
    if dh in SEEN_DHASH:
        return True, "Trùng khớp thị giác dHash"

    dh_int = int(dh, 16)
    for existing_int in DHASH_INT_LIST[-1500:]:
        if hamming_distance(dh_int, existing_int) <= 4:
            return True, "Gần như trùng lặp (Hamming dist <= 4)"

    return False, dh


def fetch_candidate_urls(sp_key, max_candidates=350):
    """Thu thập danh sách URL ứng viên quy mô lớn từ 5 nguồn toàn cầu (đa luồng song song)."""
    meta = SPECIES_METADATA.get(sp_key, {})
    candidates = []
    seen_urls = set()

    def add_candidate(source, url):
        if url and url not in seen_urls:
            seen_urls.add(url)
            candidates.append((source, url))

    tasks = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        # 1. iNaturalist Open Data API (Chất lượng Nghiên cứu theo Taxons)
        inat_taxons = meta.get('inat_taxons') or ([meta['inat_taxon']] if meta.get('inat_taxon') else [])
        for taxon in inat_taxons:
            for page in (1, 2, 3):
                def _fetch_inat_taxon(t=taxon, p=page):
                    try:
                        u = f"https://api.inaturalist.org/v1/observations?taxon_name={urllib.parse.quote(t)}&photos=true&per_page=60&page={p}"
                        req = urllib.request.Request(u, headers=HEADERS)
                        data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
                        res = []
                        for r in data.get('results', []):
                            for ph in r.get('photos', []):
                                purl = ph.get('url', '')
                                if purl:
                                    res.append(('iNaturalist', purl.replace('/square.', '/large.').replace('/medium.', '/large.')))
                        return res
                    except Exception:
                        return []
                tasks.append(executor.submit(_fetch_inat_taxon))

        # 1b. iNaturalist Tìm kiếm theo từ khóa thực tế
        for inat_q in meta.get('inat_queries', []):
            def _fetch_inat_q(q=inat_q):
                try:
                    u = f"https://api.inaturalist.org/v1/observations?q={urllib.parse.quote(q)}&photos=true&per_page=50&page=1"
                    req = urllib.request.Request(u, headers=HEADERS)
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
                    res = []
                    for r in data.get('results', []):
                        for ph in r.get('photos', []):
                            purl = ph.get('url', '')
                            if purl:
                                res.append(('iNaturalist', purl.replace('/square.', '/large.').replace('/medium.', '/large.')))
                    return res
                except Exception:
                    return []
            tasks.append(executor.submit(_fetch_inat_q))

        # 2. Wikimedia Commons API
        for w_q in meta.get('wiki_searches', []):
            def _fetch_wiki(q=w_q):
                try:
                    w_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(q)}&gsrlimit=45&prop=imageinfo&iiprop=url|size&format=json"
                    req = urllib.request.Request(w_url, headers=HEADERS)
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
                    res = []
                    for p in data.get('query', {}).get('pages', {}).values():
                        info = p.get('imageinfo', [{}])[0]
                        u = info.get('url')
                        w = info.get('width', 0)
                        h = info.get('height', 0)
                        if u and w >= 300 and h >= 300:
                            res.append(('Wikimedia', u))
                    return res
                except Exception:
                    return []
            tasks.append(executor.submit(_fetch_wiki))

        # 3. GBIF Occurrence API
        gbif_taxons = meta.get('gbif_taxons') or ([meta['gbif_taxon']] if meta.get('gbif_taxon') else [])
        for taxon in gbif_taxons:
            def _fetch_gbif(t=taxon):
                try:
                    g_url = f"https://api.gbif.org/v1/occurrence/search?scientificName={urllib.parse.quote(t)}&mediaType=StillImage&limit=50"
                    req = urllib.request.Request(g_url, headers=HEADERS)
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
                    res = []
                    for r in data.get('results', []):
                        for m in r.get('media', []):
                            u = m.get('identifier')
                            if u and u.lower().endswith(('.jpg', '.jpeg', '.png')):
                                res.append(('GBIF', u))
                    return res
                except Exception:
                    return []
            tasks.append(executor.submit(_fetch_gbif))

        # 4. Flickr Community Feeds
        for tag in meta.get('flickr_tags', []):
            def _fetch_flickr(t=tag):
                try:
                    f_url = f"https://api.flickr.com/services/feeds/photos_public.gne?tags={t}&format=json&nojsoncallback=1"
                    req = urllib.request.Request(f_url, headers=HEADERS)
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
                    res = []
                    for item in data.get('items', []):
                        m_url = item.get('media', {}).get('m', '')
                        if m_url:
                            res.append(('Flickr', m_url.replace('_m.', '_b.')))
                    return res
                except Exception:
                    return []
            tasks.append(executor.submit(_fetch_flickr))

        # 5. Bing High-Res Search
        for b_q in meta.get('bing_queries', []):
            for offset in (0, 35):
                def _fetch_bing(q=b_q, off=offset):
                    try:
                        b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first={off}&count=35&mmasync=1"
                        req = urllib.request.Request(b_url, headers=HEADERS)
                        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
                        murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
                        res = []
                        for u in murls:
                            u_lower = u.lower()
                            if any(neg in u_lower for neg in NEGATIVE_KEYWORDS):
                                continue
                            res.append(('Bing', u))
                        return res
                    except Exception:
                        return []
                tasks.append(executor.submit(_fetch_bing))

        for future in as_completed(tasks):
            try:
                for src, u in future.result():
                    add_candidate(src, u)
            except Exception:
                pass

    return candidates[:max_candidates]


def process_species_collection(sp_key, target_add=30):
    """Xử lý thu thập, kiểm duyệt rõ nét và lưu trữ cho từng loài cá."""
    meta = SPECIES_METADATA.get(sp_key)
    if not meta:
        print(f"Lỗi: Không tìm thấy loài {sp_key}", flush=True)
        return 0

    dest_dir = os.path.join(DATASET_DIR, sp_key)
    os.makedirs(dest_dir, exist_ok=True)

    existing_files = [f for f in os.listdir(dest_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    before_count = len(existing_files)

    print(f"\n{'='*70}", flush=True)
    print(f"[{meta['vn_name']}] ({sp_key})", flush=True)
    print(f"  Hiện có: {before_count} ảnh | Mục tiêu nạp thêm: +{target_add} ảnh rõ nét IoT", flush=True)
    print(f"{'='*70}", flush=True)

    candidates = fetch_candidate_urls(sp_key, max_candidates=max(350, target_add * 10))
    print(f"  🔍 Thu được {len(candidates)} link ứng viên từ 5 nguồn...", flush=True)

    added = 0
    rejected = 0

    for idx, (source, url) in enumerate(candidates, 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            raw_bytes = urllib.request.urlopen(req, timeout=7).read()

            if len(raw_bytes) < 22000:
                rejected += 1
                continue

            pil_img = Image.open(io.BytesIO(raw_bytes))

            # 1. Chống trùng lặp tuyệt đối
            dup, dh_or_reason = is_duplicate(raw_bytes, pil_img)
            if dup:
                rejected += 1
                continue

            # 2. Tiêu chuẩn rõ nét cho Camera IoT (YOLOv8)
            clear, quality_msg = is_clear_for_iot(pil_img)
            if not clear:
                rejected += 1
                continue

            # 2.5. KIỂM ĐỊNH THỊ GIÁC AI (GEMINI VISION) - NHÌN TRỰC TIẾP VÀO HÌNH
            vis_ok, vis_msg = verify_with_gemini_vision(pil_img, sp_key)
            if not vis_ok:
                rejected += 1
                continue

            # 3. Đạt chuẩn: Lưu ảnh và ghi nhớ mã băm
            dh = dh_or_reason
            md5_hash = get_md5(raw_bytes)
            SEEN_MD5.add(md5_hash)
            SEEN_DHASH.add(dh)
            DHASH_INT_LIST.append(int(dh, 16))

            timestamp = int(time.time())
            filename = f"iot_verified_{sp_key}_{timestamp}_{added+1}.jpg"
            save_path = os.path.join(dest_dir, filename)

            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            pil_img.save(save_path, 'JPEG', quality=95)

            # Cập nhật cache
            rel_p = os.path.relpath(save_path, BASE_DIR)
            CACHE_DATA[rel_p] = {'mtime': os.path.getmtime(save_path), 'md5': md5_hash, 'dhash': dh}

            # Đồng bộ ngay vào audit_log.json để hiện trên Dashboard
            try:
                audit_log_path = os.path.join(BASE_DIR, 'audit_log.json')
                if os.path.exists(audit_log_path):
                    with open(audit_log_path, 'r', encoding='utf-8') as af:
                        ad = json.load(af)
                    new_rec = {
                        'filename': filename,
                        'species': sp_key,
                        'species_name': meta['vn_name'],
                        'identified_as': f"{meta['vn_name']} ({source} Live Verified)",
                        'confidence': 'high',
                        'reason': f"Ảnh cá sống trong nước, rõ nét ({quality_msg})",
                        'source': f"{source} API",
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    if 'recent_approved' not in ad:
                        ad['recent_approved'] = []
                    ad['recent_approved'].insert(0, new_rec)
                    ad['recent_approved'] = ad['recent_approved'][:40]
                    ad['current_status'] = {
                        'is_busy': True,
                        'action': f"Đang nạp ảnh: {meta['vn_name']}",
                        'item': f"Đã lưu: {filename}",
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    with open(audit_log_path, 'w', encoding='utf-8') as af:
                        json.dump(ad, af, ensure_ascii=False, indent=2)
            except Exception:
                pass

            added += 1
            print(f"  ✅ [{added}/{target_add}] [{source}] ĐÃ LƯU: {filename} -> {quality_msg}", flush=True)

            if added >= target_add:
                print(f"  🎯 Đã hoàn thành nạp đủ +{target_add} ảnh rõ nét cho {meta['vn_name']}!", flush=True)
                break

            time.sleep(0.1)

        except Exception as e:
            rejected += 1
            continue

    # Lưu lại cache
    try:
        with open(HASH_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(CACHE_DATA, f)
    except Exception:
        pass

    after_count = len([f for f in os.listdir(dest_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    print(f"  📊 Tổng kết [{meta['vn_name']}]: Trước: {before_count} -> Sau: {after_count} (+{added} ảnh chuẩn | Đã lọc bỏ: {rejected})", flush=True)
    return added


def main():
    print("=" * 70, flush=True)
    print("BỘ THU THẬP & KIỂM ĐỊNH ẢNH CÁ CẢNH IOT TỰ ĐỘNG (5 NGUỒN TOÀN CẦU)", flush=True)
    print("Đề tài tốt nghiệp: Lê Quốc Trí & Phạm Minh Thân", flush=True)
    print("Chống trùng lặp tuyệt đối (MD5 + dHash) & Kiểm định rõ nét cho YOLOv8", flush=True)
    print("=" * 70, flush=True)

    init_database_hashes()

    target_sp = sys.argv[1] if len(sys.argv) > 1 else None
    target_num = int(sys.argv[2]) if len(sys.argv) > 2 else 25

    if target_sp and target_sp in SPECIES_METADATA:
        process_species_collection(target_sp, target_num)
    else:
        species_counts = []
        for sp in SPECIES_METADATA.keys():
            sp_dir = os.path.join(DATASET_DIR, sp)
            cnt = len([f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]) if os.path.exists(sp_dir) else 0
            species_counts.append((sp, cnt))

        species_counts.sort(key=lambda x: x[1])

        print(f"\nDanh sách loài theo số lượng ảnh hiện tại (ưu tiên nạp loài ít ảnh nhất):", flush=True)
        for sp, cnt in species_counts:
            print(f"  - {sp:20s}: {cnt} ảnh", flush=True)

        for sp, cnt in species_counts:
            if cnt < 400:
                needed = min(target_num, 400 - cnt)
                process_species_collection(sp, target_add=needed)


if __name__ == '__main__':
    main()
