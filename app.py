"""
🐟 Quản Lý & Kiểm Định Dataset Cá Cảnh - Flask Web Application
Hỗ trợ:
- Xem, thống kê, kiểm tra số lượng ảnh 20 loài cá
- Gallery phân trang, phóng to, xóa ảnh
- Upload kéo thả nhiều ảnh cùng lúc
- 🤖 AI Gemini nhận diện tự động loài cá khi tải ảnh
- 🔍 AI Audit kiểm tra dataset hiện tại xem ảnh đúng hay sai loài
- 🕒 Live Activity: Hiển thị tiến trình đang tải/đang duyệt, ảnh được duyệt gần nhất, ảnh nghi ngờ sai loài
"""

import os
import io
import time
import json
import shutil
import urllib.parse
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, redirect, url_for, flash
)
from werkzeug.utils import secure_filename
from google import genai
from PIL import Image

app = Flask(__name__)
app.secret_key = 'fish-dataset-secret-key-2026'

# ============================================================
# CẤU HÌNH
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, '_temp_uploads')
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

MIN_IMAGES = 500  # Mục tiêu số ảnh tối thiểu cho đồ án IoT (500 - 1000 ảnh/loài)
IMAGES_PER_PAGE = 24  # Số ảnh mỗi trang gallery
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

def check_image_quality(img_path):
    """Tính toán mã băm MD5 và điểm độ nét Laplacian của ảnh."""
    import hashlib
    hasher = hashlib.md5()
    try:
        with open(img_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        md5_val = hasher.hexdigest()
    except Exception:
        md5_val = ""

    blur_score = 0.0
    try:
        import cv2
        cv_img = cv2.imread(img_path)
        if cv_img is not None:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            blur_score = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)
    except Exception:
        pass

    return md5_val, blur_score


_FACE_CASCADE = None

def detect_human_face(img_path):
    """Phát hiện khuôn mặt người bằng OpenCV Haar Cascade để loại bỏ ảnh người/hội thảo."""
    global _FACE_CASCADE
    try:
        if _FACE_CASCADE is None:
            import cv2
            cascade_p = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            _FACE_CASCADE = cv2.CascadeClassifier(cascade_p)
        from PIL import Image
        import numpy as np
        import cv2
        im = Image.open(img_path).convert('RGB')
        im.thumbnail((640, 640))
        gray = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 4)
        return len(faces) > 0, len(faces)
    except Exception:
        return False, 0


GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not GEMINI_API_KEY:
    env_file = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY='):
                        GEMINI_API_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Loi khoi tao Gemini: {e}")


def call_gemini_vision(client, contents, **kwargs):
    """Gọi Gemini ưu tiên Gemini 2.5 Flash, tự động fallback sang Gemini 3.5 Flash / Lite."""
    models_to_try = ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-flash-lite-latest', 'gemini-3.8-flash']
    last_err = None
    for m in models_to_try:
        try:
            resp = client.models.generate_content(model=m, contents=contents, **kwargs)
            return resp, m
        except Exception as e:
            last_err = e
            continue
    raise last_err

# Mapping tên thư mục -> tên tiếng Việt
SPECIES_MAP = {
    'ca_ba_duoi': 'Cá Ba Đuôi',
    'ca_bay_mau': 'Cá Bảy Màu',
    'ca_but_chi': 'Cá Bút Chì',
    'ca_chuot': 'Cá Chuột',
    'ca_da_quang': 'Cá Dạ Quang',
    'ca_dia': 'Cá Dĩa',
    'ca_diec_anh_dao': 'Cá Diếc Anh Đào',
    'ca_duoi_kiem': 'Cá Đuôi Kiếm',
    'ca_hong_ket': 'Cá Hồng Kết',
    'ca_koi': 'Cá Koi',
    'ca_la_han': 'Cá La Hán',
    'ca_lau_kieng': 'Cá Lau Kiếng',
    'ca_molly': 'Cá Molly',
    'ca_mun': 'Cá Mún',
    'ca_neon': 'Cá Neon',
    'ca_rong': 'Cá Rồng',
    'ca_sac': 'Cá Sặc',
    'ca_soc_ngua': 'Cá Sóc Ngựa',
    'ca_thien_than': 'Cá Thần Tiên',
    'ca_xiem': 'Cá Xiêm',
}

SPECIES_SPECS = {
    'ca_ba_duoi': 'Cá Ba Đuôi / Cá Vàng (Goldfish - Carassius auratus) - thân tròn béo mập, đuôi xòe 3-4 thùy hoặc đuôi voan kép thướt tha, vảy ánh kim nhiều màu sắc (đỏ, cam, trắng, ngũ hoa, đen). Bao gồm các dòng cá vàng kinh điển: Oranda (đầu lân gù thịt), Ranchu (không có vây lưng, lưng cong tròn), Ryukin (gù lưng cao), Lan Thọ, Ba đuôi mắt lồi (Black Moor), Hạc Đỉnh Hồng, Tosakin, đuôi quạt',
    'ca_bay_mau': 'Cá Bảy Màu (Guppy - Poecilia reticulata) - cá nhỏ (2.5 - 5cm), đuôi to xòe rộng với nhiều hoa văn và màu sắc sặc sỡ, con cái to hơn con đực',
    'ca_but_chi': 'Cá Bút Chì (Siamese Algae Eater / Crossocheilus oblongus hoặc Pencilfish) - cá thân thon dài như cây bút chì, đặc trưng có dải sọc đen đậm rõ nét chạy dọc từ mũi qua mắt đến hết cuống đuôi, miệng hướng xuống chuyên ăn rêu hại',
    'ca_chuot': 'Cá Chuột (Corydoras Catfish) - cá da trơn nhỏ bơi tầng đáy, miệng có các sợi râu xúc giác, bụng phẳng, thân ngắn mập, vây lưng nhọn',
    'ca_da_quang': 'Cá Dạ Quang (GloFish / Cá Cánh Buồm Dạ Quang / Cá Thủy Tinh biến đổi gen) - thân dẹp phát huỳnh quang màu neon chói lọi (đỏ neon, xanh lá mạ chuối, cam, tím, vàng huỳnh quang)',
    'ca_dia': 'Cá Dĩa (Discus - Symphysodon) - thân tròn xoe dẹp mỏng như chiếc đĩa tròn, hoa văn vân da rắn hoặc sọc hoa sen rực rỡ, bơi uyển chuyển thanh tao',
    'ca_diec_anh_dao': 'Cá Diếc Anh Đào (Cherry Barb - Puntius titteya) - cá nhỏ họ chép, toàn thân con đực có màu đỏ tươi như quả anh đào chín, có một dải sọc mờ dọc thân',
    'ca_duoi_kiem': 'Cá Đuôi Kiếm (Swordtail - Xiphophorus hellerii) - cá đẻ con, đặc trưng con đực có phần thùy dưới của vây đuôi nhọn hoắt kéo dài như lưỡi kiếm',
    'ca_hong_ket': 'Cá Hồng Két (Blood Parrot Cichlid) - thân tròn mập ú màu đỏ hoặc cam tươi, mõm nhô cao, miệng nhỏ hình chữ V hoặc trái tim không thể khép kín',
    'ca_koi': 'Cá Koi (Chép Koi Nhật Bản - Cyprinus carpio) - cá chép cảnh to lớn, vảy to óng ánh, trên lưng có các khoang mảng màu đỏ, trắng, đen, vàng (Kohaku, Showa, Sanke), miệng có râu chép',
    'ca_la_han': 'Cá La Hán (Flowerhorn Cichlid) - đầu có khối u bướu (gù đầu) to tròn nhô cao, trên thân có các đốm hoa văn đen như chữ Hán và ánh kim châu, dáng bơi hùng dũng',
    'ca_lau_kieng': 'Cá Lau Kiếng / Cá Tỳ Bà (Pleco - Hypostomus plecostomus) - cá da trơn giáp cứng màu nâu đen đốm da báo, miệng hình giác hút tròn bám chặt vào kính hồ hoặc đá để nạo rêu',
    'ca_molly': 'Cá Molly (Poecilia sphenops / Poecilia latipinna) - thân bầu dục tròn trịa, vây lưng rộng hình buồm, nhiều màu sắc (trắng bạc, vàng cam, đốm hoa cúc, đuôi đàn cầm/lyretail)',
    'ca_mun': 'Cá Mún / Hắc Molly / Platy (Xiphophorus maculatus hoặc Black Molly) - cá nhỏ thân ngắn mập đẻ con, màu sắc thường là đỏ cờ, cam (cá Mún đỏ) hoặc đen tuyền đồng nhất từ đầu đến đuôi (Hắc Molly)',
    'ca_neon': 'Cá Neon (Neon Tetra / Cardinal Tetra) - cá nhỏ bơi theo đàn, có một vệt màu xanh lam/ngọc lục bảo phát sáng rực rỡ chạy dọc sống lưng, nửa dưới thân và đuôi màu đỏ tươi',
    'ca_rong': 'Cá Rồng (Arowana - Scleropages formosus) - cá phong thủy cỡ lớn thân dài uy nghi, vảy to như vảy rồng sáng bóng (Huyết Long, Quá Bối, Kim Long), miệng chĩa lên trên có 2 sợi râu ở cằm',
    'ca_sac': 'Cá Sặc (Gourami - Trichogaster / Trichopodus) - thân dẹp đứng, đặc biệt 2 vây bụng tiêu biến thành 2 sợi râu dài như ăng-ten thò ra phía trước để cảm nhận môi trường (Sặc gấm, Sặc bướm, Sặc trân châu, Sặc cẩm thạch)',
    'ca_soc_ngua': 'Cá Sóc Ngựa / Cá Ngựa Vằn (Zebra Danio) - cá nhỏ thon thả, có 5 sọc màu xanh lam ánh kim chạy ngang song song từ mang tới hết vây đuôi như sọc ngựa vằn',
    'ca_thien_than': 'Cá Thần Tiên (Angelfish - Pterophyllum scalare) - thân dẹp mỏng hình tam giác cân, vây lưng và vây hậu môn vươn dài thanh thoát hướng lên xuống như cánh thiên thần',
    'ca_xiem': 'Cá Xiêm / Cá Betta (Betta splendens) - cá chọi cảnh, con đực có bộ vây đuôi xòe tròn lộng lẫy (Halfmoon, Dumbo, Plakat, Crowntail), màu sắc rực rỡ, bơi giương vây phùng mang',
}

# ============================================================
# PHÂN LOẠI 20 LOÀI THEO 6 HỌ SINH THÁI & MÔI TRƯỜNG SỐNG (BIOTOPES)
# ============================================================
FISH_FAMILIES = {
    'poeciliidae': {
        'id': 'poeciliidae',
        'name': 'Họ Cá Khổng Tước / Cá Đẻ Con',
        'scientific_name': 'Poeciliidae',
        'icon': 'fa-heart',
        'badge_class': 'bg-primary',
        'color': '#0d6efd',
        'water_type': 'Nước ngọt nhiệt đới / Nước lợ nhẹ',
        'ph_range': '7.0 - 8.2 (Ưa nước cứng & kiềm nhẹ)',
        'temp_range': '22°C - 28°C',
        'temperament': 'Hòa bình, hiền lành, bơi đàn',
        'biotope_description': 'Nhóm cá đẻ con cực kỳ phổ biến, thích nghi cao, bơi tầng mặt và giữa. Thích hồ có cây thủy sinh và dòng nước êm.',
        'species_keys': ['ca_bay_mau', 'ca_molly', 'ca_mun', 'ca_duoi_kiem']
    },
    'cyprinidae': {
        'id': 'cyprinidae',
        'name': 'Họ Cá Chép, Cá Vàng & Cá Bống Nhỏ',
        'scientific_name': 'Cyprinidae & Danionidae',
        'icon': 'fa-water',
        'badge_class': 'bg-success',
        'color': '#198754',
        'water_type': 'Nước ngọt trung tính, giàu oxy',
        'ph_range': '6.5 - 7.5',
        'temp_range': '18°C - 26°C (Chịu mát tốt)',
        'temperament': 'Đa dạng (Cá Vàng bơi chậm, Cá Ngựa Vằn bơi đàn cực nhanh)',
        'biotope_description': 'Cùng họ cá chép. Cá Vàng (Ba Đuôi, Ranchu, Oranda) và Cá Koi ăn nhiều, cần nước giàu oxy và lọc mạnh. Cá Sóc Ngựa, Diếc Anh Đào hiếu động thích hợp thủy sinh.',
        'species_keys': ['ca_ba_duoi', 'ca_koi', 'ca_soc_ngua', 'ca_diec_anh_dao', 'ca_but_chi']
    },
    'characidae': {
        'id': 'characidae',
        'name': 'Họ Cá Characin / Thủy Sinh Phát Sáng',
        'scientific_name': 'Characidae',
        'icon': 'fa-gem',
        'badge_class': 'bg-info',
        'color': '#0dcaf0',
        'water_type': 'Nước ngọt mềm, hơi axit (Amazon)',
        'ph_range': '6.0 - 7.0 (Nước mềm, TDS thấp)',
        'temp_range': '22°C - 27°C',
        'temperament': 'Nhút nhát, hiền hòa tuyệt đối',
        'biotope_description': 'Cá cảnh thủy sinh điển hình, thích bơi theo bầy đàn từ 10 con trở lên ở tầng giữa. Rất nhạy cảm với chất lượng nước và amoniac.',
        'species_keys': ['ca_neon', 'ca_da_quang']
    },
    'cichlidae': {
        'id': 'cichlidae',
        'name': 'Họ Cá Cichlid / Rô Phi Cảnh & Cá Dĩa',
        'scientific_name': 'Cichlidae',
        'icon': 'fa-crown',
        'badge_class': 'bg-warning text-dark',
        'color': '#ffc107',
        'water_type': 'Nước nhiệt đới ấm, lọc vi sinh mạnh',
        'ph_range': '6.0 - 8.2 (Tùy loài)',
        'temp_range': '26°C - 32°C (Ưa nước ấm)',
        'temperament': 'Có tính lãnh thổ, từ nhút nhát (Cá Dĩa) đến hung dữ (La Hán)',
        'biotope_description': 'Nhóm cá thông minh bậc nhất, ăn nhiều, bài tiết lớn (Bioload cao). Cần hệ thống lọc nước công suất lớn. Cá La Hán bắt buộc nuôi riêng.',
        'species_keys': ['ca_dia', 'ca_thien_than', 'ca_hong_ket', 'ca_la_han']
    },
    'osphronemidae': {
        'id': 'osphronemidae',
        'name': 'Họ Cá Mê Lộ / Thở Khí Quyển',
        'scientific_name': 'Osphronemidae',
        'icon': 'fa-lungs',
        'badge_class': 'bg-danger',
        'color': '#dc3545',
        'water_type': 'Nước ngọt tĩnh, ít dòng chảy',
        'ph_range': '6.0 - 7.5',
        'temp_range': '24°C - 29°C',
        'temperament': 'Hiền hòa (Cá Sặc) đến hiếu chiến (Cá Xiêm đực)',
        'biotope_description': 'Có cơ quan hô hấp phụ (mê lộ) tự hít thở oxy không khí trên mặt nước. Bể cần mặt nước tĩnh và bèo rong nổi che chở.',
        'species_keys': ['ca_sac', 'ca_xiem']
    },
    'benthic_predators': {
        'id': 'benthic_predators',
        'name': 'Họ Cá Tầng Đáy & Cá Săn Mồi Cỡ Lớn',
        'scientific_name': 'Siluriformes & Osteoglossidae',
        'icon': 'fa-shield-alt',
        'badge_class': 'bg-secondary',
        'color': '#6c757d',
        'water_type': 'Tầng đáy chuyên biệt / Bể lớn',
        'ph_range': '6.5 - 7.8',
        'temp_range': '22°C - 30°C',
        'temperament': 'Đặc thù (Dọn bể đáy hoặc Săn mồi đỉnh cao)',
        'biotope_description': 'Gồm Cá Chuột (dọn thức ăn thừa nền đáy), Cá Lau Kiếng (ăn rêu, giáp cứng) và Cá Rồng (đế vương săn mồi tầng mặt, cần bể trên 1.5m).',
        'species_keys': ['ca_chuot', 'ca_lau_kieng', 'ca_rong']
    }
}

# ============================================================
# CÁC MÔ HÌNH HỒ NUÔI THỰC TẾ (AQUARIUM TANK ECOSYSTEMS)
# Giải quyết cốt lõi: Các loài cá KHÔNG THỂ nuôi bừa chung 1 hồ!
# ============================================================
TANK_ECOSYSTEMS = {
    'amazon_community': {
        'id': 'amazon_community',
        'name': 'Hồ Thủy Sinh Amazon (Nước mềm, hơi axit, cây cối rậm)',
        'water_type': 'Nước ngọt nhiệt đới mềm (TDS thấp)',
        'ph_range': '6.2 - 7.0',
        'temp_range': '24°C - 27°C',
        'compatible_species': ['ca_neon', 'ca_diec_anh_dao', 'ca_but_chi', 'ca_chuot', 'ca_da_quang'],
        'forbidden_species': ['ca_la_han', 'ca_rong', 'ca_koi', 'ca_xiem'],
        'description': 'Cá kích thước nhỏ (3-7cm), hiền hòa, bơi đàn lung linh tầng giữa và tầng đáy. Cần nền cát mịn và cây xanh. Tuyệt đối cấm cá săn mồi cỡ lớn hay cá hung dữ cắn xé.'
    },
    'livebearer_alkaline': {
        'id': 'livebearer_alkaline',
        'name': 'Hồ Cá Đẻ Con & Nước Kiềm Nhẹ (Nước cứng, pH 7.2 - 8.2)',
        'water_type': 'Nước ngọt cứng / Nước lợ nhẹ',
        'ph_range': '7.2 - 8.2',
        'temp_range': '24°C - 27°C',
        'compatible_species': ['ca_bay_mau', 'ca_molly', 'ca_mun', 'ca_duoi_kiem', 'ca_chuot'],
        'forbidden_species': ['ca_dia', 'ca_la_han', 'ca_rong'],
        'description': 'Cá đẻ con cần nước có khoáng chất và độ cứng cao (GH > 8-10) để phòng nấm trắng và túm lắc. Không nuôi chung với Cá Dĩa vì Cá Dĩa cần nước rất mềm, pH thấp.'
    },
    'discus_angelfish': {
        'id': 'discus_angelfish',
        'name': 'Hồ Cá Dĩa & Cá Thần Tiên (Nước ấm sạch 29°C, bể sâu)',
        'water_type': 'Nước ấm mềm, lọc vi sinh chuẩn cao',
        'ph_range': '6.2 - 6.8',
        'temp_range': '28.5°C - 30.5°C',
        'compatible_species': ['ca_dia', 'ca_thien_than', 'ca_chuot', 'ca_neon'],
        'forbidden_species': ['ca_koi', 'ca_soc_ngua', 'ca_la_han', 'ca_rong'],
        'description': 'Cá Dĩa cần môi trường nước ấm và tĩnh. Cá Sóc Ngựa bơi quá nhanh làm cá Dĩa sợ hãi bỏ ăn; La Hán cắn rách vây; Cá Koi chịu nhiệt kém.'
    },
    'monster_predator': {
        'id': 'monster_predator',
        'name': 'Hồ Đại Bang Săn Mồi (Bể lớn > 500L, kính dày)',
        'water_type': 'Nước ngọt nhiệt đới, lọc tràn cực mạnh',
        'ph_range': '6.8 - 7.5',
        'temp_range': '27°C - 30°C',
        'compatible_species': ['ca_rong', 'ca_hong_ket', 'ca_lau_kieng'],
        'forbidden_species': ['ca_neon', 'ca_bay_mau', 'ca_molly', 'ca_soc_ngua', 'ca_diec_anh_dao'],
        'description': 'Cá Rồng săn mồi mặt nước, Hồng Két bơi tầng giữa dọn mồi thừa, Lau Kiếng mút rêu đáy. Mọi cá nhỏ dưới 10cm sẽ biến thành mồi ngon trong tích tắc!'
    },
    'solitary_aggressive': {
        'id': 'solitary_aggressive',
        'name': 'Hồ Cá Độc Tôn / Bắt Buộc Nuôi Đơn (Lãnh thổ cực đoan)',
        'water_type': 'Bể riêng biệt 1 con/hồ',
        'ph_range': '7.4 - 8.0',
        'temp_range': '28°C - 31°C',
        'compatible_species': [],
        'forbidden_species': ['ca_la_han', 'ca_xiem'],
        'description': 'Cá La Hán và Cá Xiêm (Betta đực) có tính hiếu chiến cực đoan. Không thả bất kỳ cá nào khác vào chung hồ vì sẽ cắn nhau đến chết!'
    },
    'outdoor_koi_pond': {
        'id': 'outdoor_koi_pond',
        'name': 'Hồ Cá Vàng & Cá Koi Nước Mát (Nước giàu oxy, lọc mạnh)',
        'water_type': 'Nước ngọt mát mẻ, oxy dồi dào, lọc tràn/thùng lớn',
        'ph_range': '7.0 - 7.8',
        'temp_range': '18°C - 24°C',
        'compatible_species': ['ca_ba_duoi', 'ca_koi'],
        'forbidden_species': ['ca_neon', 'ca_dia', 'ca_la_han', 'ca_rong', 'ca_bay_mau', 'ca_xiem', 'ca_thien_than'],
        'description': 'Cá Vàng (Ba Đuôi, Ranchu, Oranda, Ryukin) và Cá Koi cùng thuộc họ Cá Chép, thích nước mát lạnh giàu oxy. Chúng ăn nhiều và thải phân cực lớn (Bioload cao), tuyệt đối không thả chung cá nhiệt đới nước ấm hoặc cá nhỏ yếu ớt.'
    }
}

# ============================================================
# CƠ SỞ DỮ LIỆU MÔI TRƯỜNG SỐNG & QUY TẮC CẢM BIẾN IOT (20 LOÀI)
# ============================================================
SPECIES_ENVIRONMENT = {
    'ca_ba_duoi': {
        'name': 'Cá Ba Đuôi / Cá Vàng (Goldfish)',
        'scientific_name': 'Carassius auratus',
        'water_type': 'Nước ngọt mát, giàu oxy hòa tan (Họ Cá Chép)',
        'water_layer': 'Tầng giữa & Tầng đáy',
        'temp_min': 18,
        'temp_max': 24,
        'temp_optimal': '19°C - 23°C (Ưa nước mát)',
        'ph_min': 6.8,
        'ph_max': 7.8,
        'ph_optimal': '7.0 - 7.5 (Nước trung tính đến kiềm nhẹ)',
        'habitat_requirements': 'Các dòng cá vàng (Ranchu, Oranda, Ryukin, Lan Thọ) bơi chậm, ăn nhiều và thải lượng phân rất lớn (Bioload cao). Bắt buộc hệ thống lọc công suất lớn, bổ sung sục khí oxy liên tục. Tuyệt đối không nuôi chung cá rỉa vây hay cá nhiệt đới ưa ấm.',
        'diet': 'Ăn tạp thiên thực vật/cám chìm chuyên dụng cho cá vàng, trùn huyết',
        'compatibility': 'Chỉ nên nuôi chung với các giống cá vàng khác (Oranda, Ranchu, Ryukin) hoặc Cá Koi nhỏ; không nuôi chung cá nhiệt đới nhanh nhẹn',
        'iot_sensor_rules': {
            'temp_alert': '< 16°C hoặc > 26°C',
            'ph_alert': '< 6.5 hoặc > 8.0',
            'oxygen_demand': 'Rất cao (cần máy sủi khí liên tục)'
        }
    },
    'ca_bay_mau': {
        'name': 'Cá Bảy Màu (Guppy)',
        'scientific_name': 'Poecilia reticulata',
        'water_type': 'Nước ngọt nhiệt đới / Nước lợ nhẹ',
        'water_layer': 'Tầng mặt & Tầng giữa',
        'temp_min': 22,
        'temp_max': 28,
        'temp_optimal': '24°C - 26°C',
        'ph_min': 7.0,
        'ph_max': 8.2,
        'ph_optimal': '7.2 - 7.8',
        'habitat_requirements': 'Bể có dòng chảy êm, nhiều cây thủy sinh (rong đuôi chó, rêu java) để cá con ẩn nấp. Thích ánh sáng nhẹ.',
        'diet': 'Ăn tạp bề mặt, ấu trùng muỗi (bọ gậy), cám hạt nhỏ micro',
        'compatibility': 'Rất hiền lành, nuôi theo bầy đàn 10-30 con',
        'iot_sensor_rules': {
            'temp_alert': '< 20°C hoặc > 29°C',
            'ph_alert': '< 6.8 hoặc > 8.5',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_but_chi': {
        'name': 'Cá Bút Chì',
        'scientific_name': 'Crossocheilus / Nannostomus',
        'water_type': 'Nước ngọt mềm, giàu oxy',
        'water_layer': 'Tầng giữa & Tầng đáy (thường bám lá/đá)',
        'temp_min': 24,
        'temp_max': 28,
        'temp_optimal': '25°C - 27°C',
        'ph_min': 6.0,
        'ph_max': 7.5,
        'ph_optimal': '6.5 - 7.0',
        'habitat_requirements': 'Chuyên ăn rêu hại, rêu tóc trong bể thủy sinh. Thích nước trong sạch, dòng chảy tuần hoàn tốt, có đá lũa để bám nghỉ.',
        'diet': 'Ăn rêu tảo bám bề mặt, tảo nâu, thức ăn chìm vụn',
        'compatibility': 'Hiền hòa, chăm chỉ dọn dẹp bể',
        'iot_sensor_rules': {
            'temp_alert': '< 22°C hoặc > 29°C',
            'ph_alert': '< 6.0 hoặc > 7.8',
            'oxygen_demand': 'Cao (cần lọc sủi oxy liên tục)'
        }
    },
    'ca_chuot': {
        'name': 'Cá Chuột',
        'scientific_name': 'Corydoras',
        'water_type': 'Nước ngọt nhiệt đới',
        'water_layer': 'Tầng đáy chuyên biệt',
        'temp_min': 22,
        'temp_max': 26,
        'temp_optimal': '23°C - 25°C',
        'ph_min': 6.5,
        'ph_max': 7.5,
        'ph_optimal': '6.8 - 7.2',
        'habitat_requirements': 'Cần nền cát mịn màng (tránh sỏi sắc nhọn làm tổn thương râu cảm biến). Thích hang hốc tối, lũa đá che chắn.',
        'diet': 'Ăn cặn đáy, thức ăn thừa chìm xuống đáy, giun chỉ',
        'compatibility': 'Siêu hiền lành, vệ sinh tầng đáy cực tốt',
        'iot_sensor_rules': {
            'temp_alert': '< 21°C hoặc > 27°C',
            'ph_alert': '< 6.2 hoặc > 7.8',
            'oxygen_demand': 'Cao'
        }
    },
    'ca_da_quang': {
        'name': 'Cá Dạ Quang (GloFish)',
        'scientific_name': 'Danio rerio / Gymnocorymbus (gen phát huỳnh quang)',
        'water_type': 'Nước ngọt nhiệt đới',
        'water_layer': 'Tầng giữa & Tầng mặt',
        'temp_min': 24,
        'temp_max': 28,
        'temp_optimal': '25°C - 27°C',
        'ph_min': 6.5,
        'ph_max': 7.8,
        'ph_optimal': '6.8 - 7.4',
        'habitat_requirements': 'Rất thích đèn huỳnh quang ánh xanh (Actinic Blue / UV) giúp màu dạ quang phát sáng rực rỡ trong bóng tối. Bể thoáng đãng.',
        'diet': 'Ăn tạp, cám nổi, trùng chỉ',
        'compatibility': 'Bơi đàn năng động, thân thiện',
        'iot_sensor_rules': {
            'temp_alert': '< 22°C hoặc > 29°C',
            'ph_alert': '< 6.3 hoặc > 8.0',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_dia': {
        'name': 'Cá Dĩa (Discus - Nhất Đại Mỹ Ngư)',
        'scientific_name': 'Symphysodon',
        'water_type': 'Nước ngọt ấm, mềm, độ tinh khiết cao',
        'water_layer': 'Tầng giữa',
        'temp_min': 28,
        'temp_max': 31,
        'temp_optimal': '29°C - 30.5°C',
        'ph_min': 5.8,
        'ph_max': 6.8,
        'ph_optimal': '6.2 - 6.6',
        'habitat_requirements': 'Loài cá cao cấp cực kỳ nhạy cảm với nước! Cần hệ thống lọc vi sinh hoàn hảo (Ammonia = 0). Nước phải ấm và thay nước định kỳ.',
        'diet': 'Tim bò xay, trùn huyết đông lạnh, cám chuyên dụng cho cá Dĩa',
        'compatibility': 'Hiền lành, nhút nhát, sợ tiếng động mạnh và ánh sáng gắt',
        'iot_sensor_rules': {
            'temp_alert': '< 27.5°C (cá dễ bệnh sình bụng) hoặc > 32°C',
            'ph_alert': '< 5.5 hoặc > 7.2',
            'oxygen_demand': 'Rất cao (cần sục khí liên tục)'
        }
    },
    'ca_diec_anh_dao': {
        'name': 'Cá Diếc Anh Đào (Cherry Barb)',
        'scientific_name': 'Puntius titteya',
        'water_type': 'Nước ngọt mát',
        'water_layer': 'Tầng giữa & Tầng đáy',
        'temp_min': 23,
        'temp_max': 27,
        'temp_optimal': '24°C - 26°C',
        'ph_min': 6.0,
        'ph_max': 7.2,
        'ph_optimal': '6.5 - 7.0',
        'habitat_requirements': 'Màu đỏ anh đào nổi bật nhất khi bể trồng nhiều cây lá xanh sẫm và nền tối màu. Bơi đàn 6-10 con.',
        'diet': 'Ăn tạp, cám viên nhỏ, ấu trùng artemia',
        'compatibility': 'Hòa đồng, không rỉa vây cá khác',
        'iot_sensor_rules': {
            'temp_alert': '< 21°C hoặc > 28°C',
            'ph_alert': '< 6.0 hoặc > 7.5',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_duoi_kiem': {
        'name': 'Cá Đuôi Kiếm (Swordtail)',
        'scientific_name': 'Xiphophorus hellerii',
        'water_type': 'Nước ngọt / Nước lợ nhẹ',
        'water_layer': 'Tầng giữa & Tầng mặt',
        'temp_min': 22,
        'temp_max': 28,
        'temp_optimal': '24°C - 26°C',
        'ph_min': 7.0,
        'ph_max': 8.2,
        'ph_optimal': '7.2 - 7.8',
        'habitat_requirements': 'Cực kỳ nhanh nhẹn và thích phóng nhảy, bắt buộc bể phải có nắp đậy! Nước có độ cứng trung bình đến cao.',
        'diet': 'Ăn tạp, cám vẩy, giun quế đông lạnh',
        'compatibility': 'Năng động, con đực có tính phô trương đuôi kiếm',
        'iot_sensor_rules': {
            'temp_alert': '< 20°C hoặc > 29°C',
            'ph_alert': '< 6.8 hoặc > 8.5',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_hong_ket': {
        'name': 'Cá Hồng Két (Blood Parrot Cichlid)',
        'scientific_name': 'Amphilophus citrinellus × Vieja melanura',
        'water_type': 'Nước ngọt nhiệt đới ấm',
        'water_layer': 'Tầng giữa & Tầng đáy',
        'temp_min': 26,
        'temp_max': 30,
        'temp_optimal': '27°C - 29°C',
        'ph_min': 6.5,
        'ph_max': 7.8,
        'ph_optimal': '6.8 - 7.4',
        'habitat_requirements': 'Ăn rất khỏe và bài tiết nhiều, cần máy lọc công suất lớn. Bể có hang hốc bằng gốm/đá để cá ngủ.',
        'diet': 'Thức ăn hạt tăng màu đỏ (astaxanthin), tôm tép nhỏ băm nhỏ',
        'compatibility': 'Bán hung dữ nhẹ, thường nuôi chung với Cá Rồng, Cá Sam',
        'iot_sensor_rules': {
            'temp_alert': '< 25°C hoặc > 31°C',
            'ph_alert': '< 6.2 hoặc > 8.0',
            'oxygen_demand': 'Cao (hệ lọc mạnh)'
        }
    },
    'ca_koi': {
        'name': 'Cá Chép Koi Nhật Bản',
        'scientific_name': 'Cyprinus carpio koi',
        'water_type': 'Nước ngọt ngoài trời / Hồ koi lớn',
        'water_layer': 'Bơi toàn bộ mọi tầng nước',
        'temp_min': 15,
        'temp_max': 26,
        'temp_optimal': '18°C - 24°C',
        'ph_min': 7.0,
        'ph_max': 8.5,
        'ph_optimal': '7.2 - 7.8',
        'habitat_requirements': 'Cần dung tích nước lớn (tối thiểu 500L - vài nghìn lít/hồ). Hệ thống lọc Drum filter/lọc lắng cực mạnh, thác nước tạo dòng chảy và oxy dồi dào.',
        'diet': 'Cám hạt koi chuyên dụng cân đối đạm, tằm, tôm khô',
        'compatibility': 'Thân thiện, nhận biết chủ cho ăn',
        'iot_sensor_rules': {
            'temp_alert': '< 12°C hoặc > 30°C',
            'ph_alert': '< 6.8 hoặc > 8.8',
            'oxygen_demand': 'Cực cao (> 6-7 mg/L, báo động nếu mất sục khí)'
        }
    },
    'ca_la_han': {
        'name': 'Cá La Hán (Flowerhorn Cichlid)',
        'scientific_name': 'Cichlasoma sp. hybrid',
        'water_type': 'Nước ngọt nhiệt đới ấm',
        'water_layer': 'Tầng giữa & Tầng đáy',
        'temp_min': 28,
        'temp_max': 32,
        'temp_optimal': '29°C - 31°C',
        'ph_min': 7.4,
        'ph_max': 8.2,
        'ph_optimal': '7.6 - 8.0',
        'habitat_requirements': 'Cần bể riêng từ 120-200L trở lên. Tính lãnh thổ cực cao, không nuôi chung với cá khác (sẽ cắn chết). Giữ nước ấm để bướu đầu phát triển.',
        'diet': 'Cám tăng gù/đỏ, tôm tươi bóc vỏ, trùn huyết',
        'compatibility': 'Nuôi đơn độc lập',
        'iot_sensor_rules': {
            'temp_alert': '< 27°C (xẹp bướu đầu) hoặc > 33°C',
            'ph_alert': '< 7.2 hoặc > 8.5',
            'oxygen_demand': 'Cao'
        }
    },
    'ca_lau_kieng': {
        'name': 'Cá Lau Kiếng (Cá Dọn Bể / Pleco)',
        'scientific_name': 'Hypostomus plecostomus / Loricariidae',
        'water_type': 'Nước ngọt nhiệt đới',
        'water_layer': 'Tầng đáy & Bám thành kính, lũa đá',
        'temp_min': 22,
        'temp_max': 28,
        'temp_optimal': '24°C - 27°C',
        'ph_min': 6.5,
        'ph_max': 7.8,
        'ph_optimal': '6.8 - 7.5',
        'habitat_requirements': 'Chuyên bám kính và đáy ăn rêu, thức ăn vụn. Cần khúc lũa gỗ trong bể vì chúng cần chất xơ từ gỗ để tiêu hóa tốt.',
        'diet': 'Rêu tảo bám, viên nén tảo Spirulina, thức ăn chìm',
        'compatibility': 'Hiền với cá bơi tầng trên, có thể lớn rất nhanh',
        'iot_sensor_rules': {
            'temp_alert': '< 21°C hoặc > 29°C',
            'ph_alert': '< 6.3 hoặc > 8.0',
            'oxygen_demand': 'Trung bình đến cao'
        }
    },
    'ca_molly': {
        'name': 'Cá Molly / Cá Bình Tích',
        'scientific_name': 'Poecilia sphenops / Poecilia latipinna',
        'water_type': 'Nước ngọt / Nước lợ nhẹ',
        'water_layer': 'Tầng mặt & Tầng giữa',
        'temp_min': 24,
        'temp_max': 28,
        'temp_optimal': '25°C - 27°C',
        'ph_min': 7.5,
        'ph_max': 8.5,
        'ph_optimal': '7.6 - 8.2 (Thích nước cứng & kiềm)',
        'habitat_requirements': 'Thân bầu dục tròn trịa, vây lưng rộng hình buồm. Gồm các dòng Hắc Molly (đen tuyền), Bình Tích trắng, Bình Tích vàng, Molly cẩm thạch, đuôi én (Lyretail). Thích thêm chút muối khoáng vào nước.',
        'diet': 'Ăn tạp, đặc biệt rất thích rỉa màng vi sinh và rêu nhớt mặt nước',
        'compatibility': 'Hiền hòa, sinh sản nhanh',
        'iot_sensor_rules': {
            'temp_alert': '< 22°C hoặc > 30°C',
            'ph_alert': '< 7.2 hoặc > 8.8',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_mun': {
        'name': 'Cá Mún / Platy (Cá Hà Lan)',
        'scientific_name': 'Xiphophorus maculatus',
        'water_type': 'Nước ngọt nhiệt đới / Nước lợ nhẹ',
        'water_layer': 'Tầng mặt & Tầng giữa',
        'temp_min': 22,
        'temp_max': 28,
        'temp_optimal': '24°C - 26°C',
        'ph_min': 7.0,
        'ph_max': 8.2,
        'ph_optimal': '7.2 - 7.8 (Ưa nước cứng & kiềm nhẹ)',
        'habitat_requirements': 'Loài cá đẻ con hiền lành, thân ngắn mập tròn, bơi nhanh nhẹn. Đa dạng màu sắc (Mún đỏ cờ, Mún hạt lựu, Mún Mickey, Mún Panda, Mún đen). Cần bể có cây thủy sinh để cá con ẩn nấp.',
        'diet': 'Ăn tạp, cám hạt nhỏ micro, giun chỉ, rêu tảo mềm',
        'compatibility': 'Rất hiền hòa, sống hòa đồng cùng Bảy Màu, Molly, Đuôi Kiếm',
        'iot_sensor_rules': {
            'temp_alert': '< 20°C hoặc > 29°C',
            'ph_alert': '< 6.8 hoặc > 8.5',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_neon': {
        'name': 'Cá Neon (Neon Tetra)',
        'scientific_name': 'Paracheirodon innesi',
        'water_type': 'Nước ngọt mềm, hơi axit (Amazon)',
        'water_layer': 'Tầng giữa',
        'temp_min': 21,
        'temp_max': 26,
        'temp_optimal': '22°C - 25°C',
        'ph_min': 6.0,
        'ph_max': 7.0,
        'ph_optimal': '6.2 - 6.8',
        'habitat_requirements': 'Tuyệt tác của bể thủy sinh thiên nhiên! Cần nước mát, độ cứng thấp (TDS thấp). Bắt buộc nuôi theo đàn từ 10-30 con trở lên để cá bơi đồng điệu.',
        'diet': 'Cám vi sinh siêu nhỏ, bobo (Moina), artemia mới nở',
        'compatibility': 'Tuyệt đối hiền hòa, không nuôi chung cá ăn thịt lớn',
        'iot_sensor_rules': {
            'temp_alert': '< 20°C hoặc > 27°C (chịu nóng kém)',
            'ph_alert': '< 5.8 hoặc > 7.4',
            'oxygen_demand': 'Cao (nước sạch không ô nhiễm hữu cơ)'
        }
    },
    'ca_rong': {
        'name': 'Cá Rồng (Arowana - Kim Long / Huyết Long)',
        'scientific_name': 'Scleropages formosus',
        'water_type': 'Nước ngọt nhiệt đới',
        'water_layer': 'Tầng mặt (chuyên săn mồi bề mặt)',
        'temp_min': 26,
        'temp_max': 30,
        'temp_optimal': '28°C - 29.5°C',
        'ph_min': 6.5,
        'ph_max': 7.5,
        'ph_optimal': '6.8 - 7.2',
        'habitat_requirements': 'Loài cá phong thủy đế vương! Cần bể cực lớn (tối thiểu 1m5 - 2m dài). Nắp đậy bể phải cực kỳ nặng và chắc chắn vì sức nhảy của cá rất mạnh.',
        'diet': 'Sâu bột, dế mèn, gián dubia, tôm tép tươi nguyên vỏ, cá mồi',
        'compatibility': 'Cá săn mồi đỉnh cao, chỉ ghép với cá tầng đáy như Hồng Két, Sam cảnh, Hổ',
        'iot_sensor_rules': {
            'temp_alert': '< 25°C hoặc > 31°C',
            'ph_alert': '< 6.2 hoặc > 7.8',
            'oxygen_demand': 'Rất cao (sục khí + lọc tràn liên tục)'
        }
    },
    'ca_sac': {
        'name': 'Cá Sặc (Sặc Cẩm Thạch / Sặc Gấm)',
        'scientific_name': 'Trichogaster lalius / Trichogaster trichopterus',
        'water_type': 'Nước ngọt nhiệt đới tĩnh',
        'water_layer': 'Tầng giữa & Tầng mặt',
        'temp_min': 23,
        'temp_max': 28,
        'temp_optimal': '25°C - 27°C',
        'ph_min': 6.0,
        'ph_max': 7.5,
        'ph_optimal': '6.5 - 7.2',
        'habitat_requirements': 'Có 2 sợi râu xúc giác dài dưới bụng để dò tìm môi trường. Có cơ quan hô hấp khí quyển. Ưa thích bể nhiều rong rêu, bèo hoa dâu.',
        'diet': 'Ăn tạp nhẹ, cám vụn, sâu đỏ',
        'compatibility': 'Điềm tĩnh, uyển chuyển',
        'iot_sensor_rules': {
            'temp_alert': '< 22°C hoặc > 29°C',
            'ph_alert': '< 6.0 hoặc > 7.8',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_soc_ngua': {
        'name': 'Cá Sóc Ngựa (Cá Ngựa Vằn / Zebra Danio)',
        'scientific_name': 'Danio rerio',
        'water_type': 'Nước ngọt',
        'water_layer': 'Tầng mặt & Tầng giữa',
        'temp_min': 18,
        'temp_max': 26,
        'temp_optimal': '20°C - 24°C',
        'ph_min': 6.5,
        'ph_max': 7.5,
        'ph_optimal': '6.8 - 7.2',
        'habitat_requirements': 'Loài cá khỏe nhất trong giới thủy sinh! Thích nước có dòng chảy tạo sóng để bơi ngược dòng. Bơi đàn cực kỳ năng động.',
        'diet': 'Ăn mọi loại thức ăn kích thước nhỏ',
        'compatibility': 'Rất hiền lành, bơi nhanh thoăn thoắt',
        'iot_sensor_rules': {
            'temp_alert': '< 16°C hoặc > 28°C',
            'ph_alert': '< 6.2 hoặc > 8.0',
            'oxygen_demand': 'Trung bình'
        }
    },
    'ca_thien_than': {
        'name': 'Cá Thần Tiên (Cá Thiên Thần / Angelfish)',
        'scientific_name': 'Pterophyllum scalare',
        'water_type': 'Nước ngọt nhiệt đới mềm',
        'water_layer': 'Tầng giữa',
        'temp_min': 25,
        'temp_max': 29,
        'temp_optimal': '26°C - 28°C',
        'ph_min': 6.5,
        'ph_max': 7.2,
        'ph_optimal': '6.8 - 7.0',
        'habitat_requirements': 'Thân hình dẹp tam giác với vây dài thướt tha, yêu cầu bể có chiều cao cột nước sâu (trên 50cm). Trồng các cây lá bản rộng như Lan Nước.',
        'diet': 'Trùn huyết, artemia, tôm băm, cám mảnh giàu đạm',
        'compatibility': 'Điềm đạm nhưng khi trưởng thành có thể rỉa vây cá chậm hoặc ăn cá sơ sinh',
        'iot_sensor_rules': {
            'temp_alert': '< 23°C hoặc > 30°C',
            'ph_alert': '< 6.2 hoặc > 7.6',
            'oxygen_demand': 'Cao'
        }
    },
    'ca_xiem': {
        'name': 'Cá Xiêm (Cá Betta / Cá Chọi)',
        'scientific_name': 'Betta splendens',
        'water_type': 'Nước ngọt nhiệt đới ấm',
        'water_layer': 'Tầng mặt & Tầng giữa',
        'temp_min': 25,
        'temp_max': 30,
        'temp_optimal': '26°C - 28.5°C',
        'ph_min': 6.5,
        'ph_max': 7.2,
        'ph_optimal': '6.8 - 7.0',
        'habitat_requirements': 'Hô hấp trực tiếp qua cơ quan mê lộ ở mặt nước. Tránh dòng nước sủi quá mạnh làm rách bộ vây xòe lộng lẫy. Tuyệt đối không nhốt chung 2 con đực.',
        'diet': 'Lăng quăng, trùn chỉ, artemia sấy khô, cám betta dạng viên nổi',
        'compatibility': 'Cá đực nuôi đơn; cá cái có thể nuôi hồ cộng đồng',
        'iot_sensor_rules': {
            'temp_alert': '< 23°C (cá lười bơi, khép vây) hoặc > 31°C',
            'ph_alert': '< 6.2 hoặc > 7.5',
            'oxygen_demand': 'Thấp (tự thở mặt nước, không cần lọc oxy mạnh)'
        }
    }
}



def load_audit_log():
    """Tải lịch sử thẩm định và danh sách ảnh nhầm lẫn."""
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_status": {"is_busy": False, "action": "Sẵn sàng", "item": "", "timestamp": ""},
        "recent_approved": [],
        "flagged_wrong": []
    }


def save_audit_log(data):
    """Lưu lịch sử thẩm định."""
    try:
        with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Loi luu audit_log: {e}")


@app.context_processor
def inject_globals():
    return {
        'species_map': SPECIES_MAP,
        'min_images': MIN_IMAGES,
        'species_env': SPECIES_ENVIRONMENT,
        'fish_families': FISH_FAMILIES
    }


def allowed_file(filename):
    """Kiểm tra file có phải ảnh hợp lệ không."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_species_stats():
    """Lấy thống kê số lượng ảnh cho từng loài cá."""
    stats = []
    for folder_name, display_name in sorted(SPECIES_MAP.items(), key=lambda x: x[1]):
        folder_path = os.path.join(DATASET_DIR, folder_name)
        if os.path.exists(folder_path):
            images = [f for f in os.listdir(folder_path)
                      if os.path.isfile(os.path.join(folder_path, f)) and allowed_file(f)]
            count = len(images)
        else:
            count = 0

        percentage = min(100, int((count / MIN_IMAGES) * 100))

        if count >= MIN_IMAGES:
            status = 'enough'
            status_text = 'Đủ mục tiêu'
            color = 'success'
        elif count >= int(MIN_IMAGES * 0.5):
            status = 'warning'
            status_text = 'Đang thu thập'
            color = 'warning'
        else:
            status = 'danger'
            status_text = 'Thiếu nhiều'
            color = 'danger'

        # Tìm họ cá
        fam_id = 'other'
        fam_name = 'Khác'
        for f_key, f_val in FISH_FAMILIES.items():
            if folder_name in f_val.get('species_keys', []):
                fam_id = f_key
                fam_name = f_val.get('name', '')
                break

        stats.append({
            'folder': folder_name,
            'name': display_name,
            'count': count,
            'percentage': percentage,
            'status': status,
            'status_text': status_text,
            'color': color,
            'need_more': max(0, MIN_IMAGES - count),
            'family_id': fam_id,
            'family_name': fam_name
        })

    return stats


def get_images_for_species(species_folder, page=1, sort_by='newest'):
    """Lấy danh sách ảnh cho một loài cá với phân trang, ưu tiên ảnh mới thêm lên đầu."""
    folder_path = os.path.join(DATASET_DIR, species_folder)
    if not os.path.exists(folder_path):
        return [], 0, 0

    valid_files = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and allowed_file(f)
    ]

    # Mặc định sắp xếp ảnh mới nhất lên đầu tiên (newest first)
    if sort_by == 'name':
        all_images = sorted(valid_files)
    else:
        all_images = sorted(
            valid_files,
            key=lambda f: os.path.getmtime(os.path.join(folder_path, f)),
            reverse=True
        )

    total = len(all_images)
    total_pages = max(1, (total + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE)
    page = max(1, min(page, total_pages))

    start = (page - 1) * IMAGES_PER_PAGE
    end = start + IMAGES_PER_PAGE
    page_images = all_images[start:end]

    return page_images, total, total_pages


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Dashboard - Trang chủ hiển thị tổng quan dataset & Live AI Monitor."""
    stats = get_species_stats()
    total_images = sum(s['count'] for s in stats)
    total_species = len(stats)
    enough_species = sum(1 for s in stats if s['status'] == 'enough')
    need_more = total_species - enough_species
    audit_data = load_audit_log()

    return render_template('index.html',
                           stats=stats,
                           total_images=total_images,
                           total_species=total_species,
                           enough_species=enough_species,
                           need_more=need_more,
                           min_images=MIN_IMAGES,
                           audit_data=audit_data,
                           species_map=SPECIES_MAP)


@app.route('/gallery/<species>')
def gallery(species):
    """Gallery - Xem ảnh của một loài cá."""
    if species not in SPECIES_MAP:
        flash('Loài cá không tồn tại!', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    images, total, total_pages = get_images_for_species(species, page)

    species_stats = None
    for s in get_species_stats():
        if s['folder'] == species:
            species_stats = s
            break

    return render_template('gallery.html',
                           species=species,
                           species_name=SPECIES_MAP[species],
                           images=images,
                           total=total,
                           page=page,
                           total_pages=total_pages,
                           species_stats=species_stats,
                           min_images=MIN_IMAGES,
                           species_map=SPECIES_MAP)


@app.route('/upload')
def upload_page():
    """Trang upload ảnh mới."""
    return render_template('upload.html',
                           species_map=SPECIES_MAP,
                           stats=get_species_stats())


@app.route('/audit')
def audit_page():
    """Trang AI Kiểm tra (Audit) Dataset."""
    audit_data = load_audit_log()
    return render_template('audit.html',
                           species_map=SPECIES_MAP,
                           stats=get_species_stats(),
                           audit_data=audit_data)


@app.route('/image_preview')
def image_preview():
    """Phục vụ ảnh an toàn bằng query parameter, giải quyết triệt để ký tự #, space, ngoặc vuông."""
    species = request.args.get('species')
    filename = request.args.get('file')
    if not species or not filename:
        return "Missing parameters", 400
    folder_path = os.path.join(DATASET_DIR, species)
    return send_from_directory(folder_path, filename)


@app.route('/dataset_ca/<species>/<filename>')
@app.route('/dataset_ca/<path:filepath>')
def serve_image(species=None, filename=None, filepath=None):
    """Phục vụ ảnh từ thư mục dataset."""
    if species and filename:
        folder_path = os.path.join(DATASET_DIR, species)
        return send_from_directory(folder_path, filename)
    return send_from_directory(DATASET_DIR, filepath)


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/stats')
def api_stats():
    """API trả về thống kê dataset dạng JSON."""
    stats = get_species_stats()
    total_images = sum(s['count'] for s in stats)
    return jsonify({
        'total_species': len(stats),
        'total_images': total_images,
        'min_images': MIN_IMAGES,
        'species': stats
    })


@app.route('/api/audit/logs', methods=['GET'])
def api_audit_logs():
    """API trả về trạng thái thời gian thực và lịch sử duyệt/nhầm lẫn."""
    data = load_audit_log()
    return jsonify({
        'success': True,
        'current_status': data.get('current_status', {}),
        'recent_approved': data.get('recent_approved', []),
        'flagged_wrong': data.get('flagged_wrong', [])
    })


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """API upload ảnh mới hỗ trợ cả chọn loài thủ công và Tự Động Phân Loại Bằng AI (YOLOv8 Edge)."""
    species = (request.form.get('species') or 'auto').strip()
    is_auto = (species in ('auto', '', 'all', 'none'))

    if not is_auto and species not in SPECIES_MAP:
        return jsonify({'success': False, 'error': f"Loài cá '{species}' không hợp lệ!"}), 400

    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Không có file nào được chọn!'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Không có file nào được chọn!'}), 400

    os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)
    audit_data = load_audit_log()
    processed_items = []
    errors = []
    species_summary = {}

    import predict_fish

    for file in files:
        if not file or not allowed_file(file.filename):
            errors.append(f"File '{file.filename}' không hợp lệ (chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)})")
            continue

        raw_filename = secure_filename(file.filename)
        temp_path = os.path.join(TEMP_UPLOADS_DIR, f"upl_{int(time.time() * 1000)}_{raw_filename}")
        file.save(temp_path)

        # Lọc an toàn: Từ chối ảnh có khuôn mặt người (tránh nhầm người/hội thảo vào dataset)
        has_human, face_cnt = detect_human_face(temp_path)
        if has_human:
            try:
                os.remove(temp_path)
            except Exception:
                pass
            errors.append(f"Từ chối '{file.filename}': Phát hiện {face_cnt} khuôn mặt người trong ảnh. Hệ thống chỉ chấp nhận ảnh cá cảnh thật!")
            continue

        md5_val, blur_score = check_image_quality(temp_path)

        # Chạy YOLOv8 nhận diện nhanh (~5ms)
        pred_res = predict_fish.predict_image(temp_path, as_json=False)
        pred_key = None
        pred_name = None
        confidence = 0.0

        if pred_res and pred_res.get('success'):
            top1 = pred_res.get('top1', {})
            pred_key = top1.get('species_key')
            pred_name = top1.get('name')
            confidence = top1.get('confidence', 0.0)

        # Quyết định thư mục đích
        if is_auto:
            target_species = pred_key if pred_key in SPECIES_MAP else 'ca_ba_duoi'
            target_name = SPECIES_MAP.get(target_species, target_species)
        else:
            target_species = species
            target_name = SPECIES_MAP[species]

        target_folder = os.path.join(DATASET_DIR, target_species)
        os.makedirs(target_folder, exist_ok=True)

        # Tránh trùng tên file trong thư mục đích
        base, ext = os.path.splitext(raw_filename)
        clean_ext = ext if ext else '.jpg'
        final_filename = f"{target_species}_{int(time.time() * 1000)}{clean_ext}"
        final_save_path = os.path.join(target_folder, final_filename)

        # Di chuyển từ temp sang thư mục đích
        shutil.move(temp_path, final_save_path)

        species_summary[target_species] = species_summary.get(target_species, 0) + 1

        # Cập nhật nhật ký audit log cho Dashboard
        audit_data.setdefault('recent_approved', []).insert(0, {
            'file': final_filename,
            'species': target_species,
            'species_name': target_name,
            'source': 'YOLOv8 Edge Auto-Sort' if is_auto else 'Manual Upload',
            'confidence': f"{confidence:.1f}%",
            'blur_score': blur_score,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        if len(audit_data['recent_approved']) > 50:
            audit_data['recent_approved'] = audit_data['recent_approved'][:50]

        processed_items.append({
            'original_name': file.filename,
            'filename': final_filename,
            'species_key': target_species,
            'species_name': target_name,
            'confidence': confidence,
            'blur_score': blur_score,
            'is_sharp': blur_score >= 25.0,
            'status': 'success'
        })

    save_audit_log(audit_data)

    return jsonify({
        'success': True,
        'mode': 'auto' if is_auto else 'manual',
        'uploaded_count': len(processed_items),
        'items': processed_items,
        'species_summary': species_summary,
        'errors': errors,
        'species': species if not is_auto else 'auto',
        'species_name': 'Tự động phân loại bằng AI (YOLOv8)' if is_auto else SPECIES_MAP.get(species, '')
    })



@app.route('/api/ai_classify', methods=['POST'])
def api_ai_classify():
    """Dùng Gemini Vision tự động nhận diện loài cá từ ảnh upload."""
    if not gemini_client:
        return jsonify({'success': False, 'error': 'Chưa cấu hình GEMINI_API_KEY'}), 500

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Chưa chọn file'}), 400

    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File không hợp lệ'}), 400

    try:
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        img.thumbnail((512, 512))

        species_list = "\n".join([f"- {k}: {v}" for k, v in SPECIES_MAP.items()])
        prompt = f"""Bạn là chuyên gia phân loại sinh vật học.
Hãy nhận diện con cá trong ảnh thuộc loài nào trong danh sách 20 loài cá cảnh sau:
{species_list}

Nếu không phải cá, hoặc không thuộc loài nào ở trên, ghi 'khac'.
Định dạng JSON:
{{
    "is_fish": true,
    "species_key": "ca_la_han",
    "species_name": "Cá La Hán",
    "confidence": "high/medium/low",
    "reason": "Giải thích đặc điểm nhận dạng (hình dáng, màu sắc, vây, đầu...)"
}}
Chỉ trả về JSON duy nhất."""

        response, used_model = call_gemini_vision(
            gemini_client,
            contents=[img, prompt]
        )

        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:-3].strip()
        elif text.startswith('```'):
            text = text[3:-3].strip()

        data = json.loads(text)
        data['success'] = True
        return jsonify(data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/yolo_classify', methods=['POST'])
def api_yolo_classify():
    """Nhận diện loài cá bằng mô hình cục bộ YOLOv8 (Edge IoT AI - không cần internet)."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Chưa chọn file'}), 400

    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File không hợp lệ'}), 400

    try:
        import predict_fish
        temp_dir = os.path.join(BASE_DIR, '_temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"temp_{int(time.time())}_{file.filename}")
        file.save(temp_path)

        res = predict_fish.predict_image(temp_path, as_json=False)
        try:
            os.remove(temp_path)
        except Exception:
            pass

        if not res or not res.get('success'):
            return jsonify({'success': False, 'error': 'Lỗi khi chạy dự đoán YOLOv8'}), 500

        top1 = res['top1']
        return jsonify({
            'success': True,
            'model': 'YOLOv8 Edge AI',
            'species_key': top1['species_key'],
            'species_name': top1['name'],
            'sci_name': top1['sci_name'],
            'confidence': f"{top1['confidence']}%",
            'environment': top1['environment'],
            'top3': res['top3'],
            'reason': f"Mô hình YOLOv8 nhận diện xác suất cao nhất: {top1['confidence']}%"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audit/<species>', methods=['GET'])
def api_audit(species):
    """Kiểm tra ảnh của loài theo từng đợt (chunk) bằng YOLOv8 Edge AI hoặc Gemini Vision."""
    engine = request.args.get('engine', 'auto').lower()
    auto_quarantine = request.args.get('auto_quarantine', 'false').lower() == 'true'

    use_gemini = (engine == 'gemini') or (engine == 'auto' and gemini_client is not None)

    if engine == 'gemini' and not gemini_client:
        return jsonify({'success': False, 'error': 'Chưa cấu hình GEMINI_API_KEY để dùng Gemini Vision'}), 500

    if species not in SPECIES_MAP:
        return jsonify({'success': False, 'error': 'Loài không hợp lệ'}), 400

    limit = request.args.get('limit', 15, type=int)
    offset = request.args.get('offset', 0, type=int)
    folder = os.path.join(DATASET_DIR, species)
    if not os.path.exists(folder):
        return jsonify({'success': True, 'results': [], 'total_scanned': 0, 'total_in_folder': 0, 'done': True})

    valid_ext = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    all_files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(valid_ext)]
    total_in_folder = len(all_files)
    files = all_files[offset : offset + limit]

    spec_desc = SPECIES_SPECS.get(species, SPECIES_MAP[species])
    results = []

    audit_data = load_audit_log()
    engine_name = 'Gemini Vision' if use_gemini else 'YOLOv8 Edge AI'
    audit_data['current_status'] = {
        'is_busy': True,
        'action': f"Đang quét kiểm tra ({engine_name}): {SPECIES_MAP[species]}",
        'item': f"Đợt [{offset+1}-{offset+len(files)} / {total_in_folder}] ảnh",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_audit_log(audit_data)

    import predict_fish

    for idx, fname in enumerate(files):
        p = os.path.join(folder, fname)
        curr_num = offset + idx + 1
        audit_data['current_status']['item'] = f"[{curr_num}/{total_in_folder}] {fname[:35]}..."
        save_audit_log(audit_data)

        md5_val, blur_score = check_image_quality(p)
        is_blur = (blur_score > 0 and blur_score < 18.0)

        if use_gemini:
            try:
                img = Image.open(p)
                img.thumbnail((512, 512))

                prompt = f"""Phân tích ảnh này xem có đúng là: {spec_desc} không.
Trả về JSON:
{{
    "is_fish": true,
    "is_correct": true,
    "identified_as": "Tên loài cá trong ảnh",
    "suggested_key": "mã_thư_mục_nếu_nhận_ra_loài (vd: ca_koi, ca_neon... hoặc khac)",
    "confidence": "high/medium/low",
    "reason": "Giải thích ngắn gọn 1 câu"
}}
Chỉ trả về JSON duy nhất."""

                response, used_model = call_gemini_vision(
                    gemini_client,
                    contents=[img, prompt]
                )

                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:-3].strip()
                elif text.startswith('```'):
                    text = text[3:-3].strip()
                parsed = json.loads(text)

                is_ok = parsed.get('is_fish') and parsed.get('is_correct')
                res_entry = {
                    'file': fname,
                    'is_correct': is_ok,
                    'status': 'Đúng chuẩn' if is_ok else 'Nghi ngờ sai',
                    'identified_as': parsed.get('identified_as', ''),
                    'suggested_key': parsed.get('suggested_key', 'khac'),
                    'reason': parsed.get('reason', ''),
                    'engine': used_model
                }
                time.sleep(0.5)
            except Exception as e:
                # Fallback sang YOLOv8 nếu Gemini gặp lỗi
                pred_res = predict_fish.predict_image(p, as_json=False)
                if pred_res and pred_res.get('success'):
                    top1 = pred_res.get('top1', {})
                    pred_key = top1.get('species_key')
                    pred_name = top1.get('name')
                    conf = top1.get('confidence', 0.0)
                    is_ok = (pred_key == species) and not is_blur
                    res_entry = {
                        'file': fname,
                        'is_correct': is_ok,
                        'status': 'Đúng chuẩn' if is_ok else ('Ảnh mờ' if is_blur else 'Nghi ngờ sai loài'),
                        'identified_as': pred_name,
                        'suggested_key': pred_key,
                        'reason': f"YOLOv8 Edge: {pred_name} ({conf:.1f}%)" if is_ok else f"YOLOv8 nhận diện {pred_name} ({conf:.1f}%) thay vì {SPECIES_MAP[species]}",
                        'engine': 'YOLOv8 (Fallback)'
                    }
                else:
                    res_entry = {
                        'file': fname,
                        'is_correct': False,
                        'status': 'Lỗi quét',
                        'identified_as': 'Lỗi',
                        'suggested_key': 'khac',
                        'reason': str(e),
                        'engine': 'Error'
                    }
        else:
            # Chạy trực tiếp bằng YOLOv8 Edge AI siêu tốc (~5ms)
            try:
                pred_res = predict_fish.predict_image(p, as_json=False)
                if pred_res and pred_res.get('success'):
                    top1 = pred_res.get('top1', {})
                    pred_key = top1.get('species_key')
                    pred_name = top1.get('name')
                    has_human, face_cnt = detect_human_face(p)

                    if has_human:
                        is_ok = False
                        status_str = 'Ảnh có người / Không phải cá'
                        reason_str = f"OpenCV Face Guard phát hiện {face_cnt} khuôn mặt người trong ảnh. Không phải cá cảnh!"
                        pred_name = "Người / Hội thảo"
                        pred_key = "khac"
                    elif is_blur:
                        is_ok = False
                        status_str = 'Ảnh mờ/Kém nét'
                        reason_str = f"Độ nét Laplacian quá thấp ({blur_score} < 18). Ảnh mờ hoặc rung nhòe."
                    elif pred_key == species and conf >= 45.0:
                        is_ok = True
                        status_str = 'Đúng chuẩn'
                        reason_str = f"YOLOv8 đối chiếu chính xác đặc trưng {pred_name} (Độ tin cậy: {conf:.1f}%)"
                    elif pred_key == species and conf < 45.0:
                        is_ok = False
                        status_str = 'Độ tin cậy thấp'
                        reason_str = f"YOLOv8 nhận diện {pred_name} nhưng độ tin cậy quá thấp ({conf:.1f}% < 45%)"
                    else:
                        is_ok = False
                        status_str = 'Nghi ngờ sai loài'
                        reason_str = f"YOLOv8 phát hiện đặc trưng giống {pred_name} ({conf:.1f}%) hơn là {SPECIES_MAP[species]}"

                    res_entry = {
                        'file': fname,
                        'is_correct': is_ok,
                        'status': status_str,
                        'identified_as': pred_name,
                        'suggested_key': pred_key,
                        'reason': reason_str,
                        'blur_score': blur_score,
                        'confidence': f"{conf:.1f}%",
                        'engine': 'YOLOv8 Edge AI'
                    }
                else:
                    res_entry = {
                        'file': fname,
                        'is_correct': False,
                        'status': 'Lỗi nhận diện',
                        'identified_as': 'Không rõ',
                        'suggested_key': 'khac',
                        'reason': 'Không chạy được mô hình nhận diện',
                        'engine': 'YOLOv8 Edge AI'
                    }
            except Exception as e:
                res_entry = {
                    'file': fname,
                    'is_correct': False,
                    'status': 'Lỗi file ảnh',
                    'identified_as': 'Lỗi',
                    'suggested_key': 'khac',
                    'reason': str(e),
                    'engine': 'YOLOv8 Edge AI'
                }

        # Tự động cách ly nếu auto_quarantine=True và ảnh không đạt
        if auto_quarantine and not res_entry.get('is_correct'):
            suspect_sub = os.path.join(DATASET_DIR, '_anh_nghi_ngo', species)
            os.makedirs(suspect_sub, exist_ok=True)
            target_suspect_path = os.path.join(suspect_sub, fname)
            try:
                shutil.move(p, target_suspect_path)
                res_entry['auto_quarantined'] = True
                res_entry['status'] += ' (Đã tự động cách ly)'
            except Exception:
                pass

        results.append(res_entry)

        # Cập nhật lịch sử audit
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if res_entry.get('is_correct'):
            audit_data['recent_approved'].insert(0, {
                'filename': fname,
                'species': species,
                'species_name': SPECIES_MAP[species],
                'identified_as': res_entry.get('identified_as', SPECIES_MAP[species]),
                'confidence': res_entry.get('confidence', 'high'),
                'reason': res_entry.get('reason', 'Đặc điểm cá chuẩn loài.'),
                'source': f"Kiểm định {res_entry.get('engine', 'AI')}",
                'timestamp': now_str
            })
            if len(audit_data['recent_approved']) > 50:
                audit_data['recent_approved'] = audit_data['recent_approved'][:50]
        else:
            exists = any(item.get('filename') == fname and item.get('original_species') == species
                         for item in audit_data['flagged_wrong'])
            if not exists:
                audit_data['flagged_wrong'].insert(0, {
                    'id': f"flag_{int(time.time()*1000)}_{curr_num}",
                    'filename': fname,
                    'original_species': species,
                    'original_species_name': SPECIES_MAP[species],
                    'detected_as': res_entry.get('identified_as', 'Không rõ / Khác'),
                    'suggested_species_key': res_entry.get('suggested_key', 'khac'),
                    'reason': res_entry.get('reason', 'Ảnh nghi ngờ không đúng chuẩn.'),
                    'timestamp': now_str
                })
                if len(audit_data['flagged_wrong']) > 50:
                    audit_data['flagged_wrong'] = audit_data['flagged_wrong'][:50]

        save_audit_log(audit_data)


    is_done = (offset + len(files) >= total_in_folder)
    audit_data['current_status'] = {
        'is_busy': not is_done,
        'action': f"{'Đã hoàn thành' if is_done else 'Đang quét'}: {SPECIES_MAP[species]}",
        'item': f"Đã quét {offset + len(files)}/{total_in_folder} ảnh",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_audit_log(audit_data)

    return jsonify({
        'success': True,
        'species': species,
        'species_name': SPECIES_MAP[species],
        'total_scanned': len(results),
        'total_in_folder': total_in_folder,
        'offset': offset,
        'limit': limit,
        'next_offset': offset + len(files),
        'done': is_done,
        'results': results
    })


@app.route('/api/move_image', methods=['POST'])
def api_move_image():
    """Di chuyển một ảnh sang thư mục loài cá khác nếu gán nhãn nhầm."""
    data = request.json or {}
    from_species = urllib.parse.unquote(str(data.get('from_species', ''))).strip()
    to_species = urllib.parse.unquote(str(data.get('to_species', ''))).strip()
    filename = urllib.parse.unquote(str(data.get('filename', ''))).strip()

    if not from_species or not to_species or not filename:
        return jsonify({'success': False, 'error': 'Thiếu tham số bắt buộc!'}), 400

    if from_species not in SPECIES_MAP or to_species not in SPECIES_MAP:
        return jsonify({'success': False, 'error': 'Loài cá không hợp lệ!'}), 400

    src = os.path.join(DATASET_DIR, from_species, filename)
    dest_dir = os.path.join(DATASET_DIR, to_species)
    os.makedirs(dest_dir, exist_ok=True)

    if not os.path.exists(src):
        return jsonify({'success': False, 'error': f'Không tìm thấy ảnh gốc: "{filename}"'}), 404

    # Tránh trùng tên khi chuyển thư mục
    base, ext = os.path.splitext(filename)
    counter = 1
    final_filename = filename
    dest = os.path.join(dest_dir, final_filename)
    while os.path.exists(dest):
        final_filename = f"{base}_{counter}{ext}"
        dest = os.path.join(dest_dir, final_filename)
        counter += 1

    try:
        shutil.move(src, dest)

        # Xóa khỏi danh sách cảnh báo sai loài trong audit_log
        audit_data = load_audit_log()
        audit_data['flagged_wrong'] = [
            f for f in audit_data.get('flagged_wrong', [])
            if not (f.get('filename') == filename and f.get('original_species') == from_species)
        ]
        save_audit_log(audit_data)

        # Tính lại số ảnh của 2 thư mục
        valid_ext = ('.jpg', '.jpeg', '.png', '.webp')
        from_count = len([f for f in os.listdir(os.path.join(DATASET_DIR, from_species)) if f.lower().endswith(valid_ext)])
        to_count = len([f for f in os.listdir(os.path.join(DATASET_DIR, to_species)) if f.lower().endswith(valid_ext)])

        return jsonify({
            'success': True,
            'message': f'Đã chuyển thành công sang "{SPECIES_MAP[to_species]}"!',
            'final_filename': final_filename,
            'from_species': from_species,
            'to_species': to_species,
            'from_count': from_count,
            'to_count': to_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete/<species>/<filename>', methods=['DELETE'])
def api_delete(species, filename):
    """API xóa một ảnh với giải mã URL an toàn."""
    species = urllib.parse.unquote(species).strip()
    filename = urllib.parse.unquote(filename).strip()

    if species not in SPECIES_MAP:
        return jsonify({'success': False, 'error': 'Loài cá không hợp lệ!'}), 400

    file_path = os.path.join(DATASET_DIR, species, filename)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': f'File không tồn tại: "{filename}"'}), 404

    try:
        os.remove(file_path)

        # Xóa khỏi danh sách cảnh báo sai loài trong audit_log
        audit_data = load_audit_log()
        audit_data['flagged_wrong'] = [
            f for f in audit_data.get('flagged_wrong', [])
            if not (f.get('filename') == filename and f.get('original_species') == species)
        ]
        save_audit_log(audit_data)

        valid_ext = ('.jpg', '.jpeg', '.png', '.webp')
        new_count = len([f for f in os.listdir(os.path.join(DATASET_DIR, species)) if f.lower().endswith(valid_ext)])

        return jsonify({'success': True, 'message': f'Đã xóa "{filename}"', 'new_count': new_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# CỔNG KẾT NỐI IOT (NHẬN DIỆN CÁ & MÔI TRƯỜNG THỦY SINH)
# ============================================================

@app.route('/iot')
def iot_page():
    """Giao diện mô phỏng & kiểm thử thiết bị IoT nhận diện cá và môi trường sống."""
    return render_template('iot.html',
                           species_map=SPECIES_MAP,
                           species_env=SPECIES_ENVIRONMENT)


@app.route('/api/iot/predict', methods=['POST'])
def api_iot_predict():
    """
    API dành riêng cho thiết bị IoT (ESP32-CAM, Raspberry Pi, Python client, Mobile App).
    Gửi ảnh cá -> AI nhận diện loài cá + Phân tích môi trường sống (Nước, Tầng bơi, Nhiệt độ, pH, Quy tắc cảm biến IoT).
    """
    if not gemini_client:
        return jsonify({'success': False, 'error': 'Chưa cấu hình GEMINI_API_KEY'}), 500

    img = None
    filename = "iot_capture.jpg"

    if 'file' in request.files:
        file = request.files['file']
        filename = file.filename or filename
        img = Image.open(file.stream)
    elif request.is_json and 'image_base64' in request.json:
        import base64
        b64_data = request.json['image_base64']
        if ',' in b64_data:
            b64_data = b64_data.split(',', 1)[1]
        img_bytes = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(img_bytes))
    else:
        return jsonify({'success': False, 'error': 'Vui lòng gửi file ảnh (key "file") hoặc JSON {"image_base64": "..."}'}), 400

    try:
        img_resized = img.copy()
        img_resized.thumbnail((512, 512))

        species_list_desc = "\n".join([f"- {k}: {v}" for k, v in SPECIES_MAP.items()])

        prompt = f"""Bạn là hệ thống AI IoT chuyên phân tích cá cảnh và điều kiện môi trường thủy sinh.
Hãy nhận diện loài cá trong ảnh dựa trên danh mục 20 loài sau:
{species_list_desc}

Nếu không phải 20 loài này hoặc không phải cá, đặt species_key là "khac".

Trả về kết quả dưới định dạng JSON duy nhất:
{{
    "is_fish": true,
    "species_key": "mã_loài_trong_danh_sách (vd: ca_koi, ca_bay_mau, ca_neon... hoặc khac)",
    "species_name": "Tên loài cá nhận diện được",
    "confidence_percent": 95,
    "confidence_level": "Cao/Trung bình/Thấp",
    "visual_features": "Mô tả ngắn đặc điểm nhìn thấy (màu sắc, vây, hình dáng)",
    "water_clarity_assessment": "Đánh giá sơ bộ độ trong/chất lượng nước nhìn qua ảnh"
}}
Chỉ trả về JSON hợp lệ, không kèm văn bản nào khác."""

        response, used_model = call_gemini_vision(
            gemini_client,
            contents=[img_resized, prompt]
        )
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:-3].strip()
        elif text.startswith('```'):
            text = text[3:-3].strip()
        ai_result = json.loads(text)

        species_key = ai_result.get('species_key', 'khac')
        env_info = SPECIES_ENVIRONMENT.get(species_key, None)

        if not env_info:
            env_info = {
                'name': ai_result.get('species_name', 'Không xác định'),
                'scientific_name': 'N/A',
                'water_type': 'Nước ngọt nhiệt đới (mặc định)',
                'water_layer': 'Tầng giữa',
                'temp_min': 24,
                'temp_max': 28,
                'temp_optimal': '24°C - 28°C',
                'ph_min': 6.5,
                'ph_max': 7.5,
                'ph_optimal': '6.8 - 7.2',
                'habitat_requirements': 'Chưa có thông tin môi trường cụ thể cho loài này.',
                'diet': 'Ăn tạp',
                'compatibility': 'Cần theo dõi thêm',
                'iot_sensor_rules': {
                    'temp_alert': '< 22°C hoặc > 29°C',
                    'ph_alert': '< 6.5 hoặc > 7.8',
                    'oxygen_demand': 'Trung bình'
                }
            }

        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'device_type': request.headers.get('User-Agent', 'IoT-Device'),
            'detection': {
                'is_fish': ai_result.get('is_fish', True),
                'species_key': species_key,
                'species_name': env_info['name'],
                'scientific_name': env_info.get('scientific_name', ''),
                'confidence': ai_result.get('confidence_percent', 90),
                'confidence_level': ai_result.get('confidence_level', 'Cao'),
                'visual_features': ai_result.get('visual_features', ''),
                'water_clarity': ai_result.get('water_clarity_assessment', 'Bình thường')
            },
            'aquatic_environment': {
                'water_type': env_info['water_type'],
                'water_layer': env_info['water_layer'],
                'optimal_temperature': env_info['temp_optimal'],
                'temp_range': {'min': env_info['temp_min'], 'max': env_info['temp_max']},
                'optimal_ph': env_info['ph_optimal'],
                'ph_range': {'min': env_info['ph_min'], 'max': env_info['ph_max']},
                'habitat_requirements': env_info['habitat_requirements'],
                'diet': env_info['diet'],
                'compatibility': env_info['compatibility']
            },
            'iot_sensor_thresholds': env_info['iot_sensor_rules']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



def calculate_tank_bioload(length_cm, width_cm, height_cm, fish_inventory, filter_type='hang-on', has_plants=True):
    raw_vol = (float(length_cm) * float(width_cm) * float(height_cm)) / 1000.0
    actual_vol = max(1.0, raw_vol * 0.85)

    filter_mults = {
        'sponge': 0.85,
        'hang-on': 1.0,
        'canister': 1.25,
        'sump': 1.4
    }
    f_mult = filter_mults.get(filter_type, 1.0)
    p_mult = 1.1 if has_plants else 1.0

    effective_capacity_liters = actual_vol * f_mult * p_mult

    bioload_per_species = {
        'ca_neon': 1.0, 'ca_bay_mau': 1.0, 'ca_soc_ngua': 1.0, 'ca_xiem': 1.0,
        'ca_da_quang': 1.2, 'ca_diec_anh_dao': 1.2, 'ca_chuot': 1.5, 'ca_but_chi': 1.5,
        'ca_mun': 1.6, 'ca_molly': 1.8, 'ca_sac': 1.8, 'ca_duoi_kiem': 2.0,
        'ca_ba_duoi': 2.5, 'ca_thien_than': 2.8, 'ca_dia': 3.5, 'ca_hong_ket': 3.8,
        'ca_lau_kieng': 4.0, 'ca_la_han': 4.5, 'ca_rong': 5.0, 'ca_koi': 5.0
    }

    total_bioload_needed = 0.0
    for item in fish_inventory:
        sp_key = item.get('species')
        count = int(item.get('count', 1))
        b_score = bioload_per_species.get(sp_key, 1.5)
        total_bioload_needed += (b_score * count * 10.0)

    load_ratio = round((total_bioload_needed / effective_capacity_liters) * 100, 1)

    if load_ratio < 65:
        status = 'safe'
        status_text = 'Bể thoáng đãng (An toàn)'
        color = 'success'
        advice = 'Hệ vi sinh xử lý tốt, chất lượng nước ổn định. Bạn có thể thả thêm cá nếu muốn.'
    elif load_ratio <= 95:
        status = 'optimal'
        status_text = 'Tải lượng lý tưởng (Cân bằng sinh thái)'
        color = 'primary'
        advice = 'Hồ đạt tỷ lệ sinh thái vàng! Thay nước 20-30% mỗi tuần một lần để giữ nước trong.'
    elif load_ratio <= 120:
        status = 'warning'
        status_text = 'Hơi đông (Cần theo dõi)'
        color = 'warning'
        advice = 'Tải lượng sinh học chạm ngưỡng cảnh báo. Nên tăng sủi oxy và không cho ăn dư thừa.'
    else:
        status = 'overloaded'
        status_text = 'Quá tải sinh học nghiêm trọng (Nguy hiểm)'
        color = 'danger'
        advice = 'Cảnh báo! Số lượng cá vượt quá thể tích nước của hồ. Nguy cơ thiếu oxy và sụp đổ hệ vi sinh gây ngộ độc amoniac!'

    return {
        'raw_volume_liters': round(raw_vol, 1),
        'actual_water_liters': round(actual_vol, 1),
        'effective_capacity_liters': round(effective_capacity_liters, 1),
        'total_bioload_needed': round(total_bioload_needed, 1),
        'load_percentage': load_ratio,
        'status': status,
        'status_text': status_text,
        'color': color,
        'advice': advice
    }


@app.route('/api/iot/bioload', methods=['POST'])
def api_iot_bioload():
    """API tính toán Bioload (Tải lượng sinh học & Thể tích nước thực tế của hồ cá)."""
    data = request.json or {}
    l = data.get('length_cm', 60)
    w = data.get('width_cm', 40)
    h = data.get('height_cm', 40)
    f_type = data.get('filter_type', 'hang-on')
    plants = data.get('has_plants', True)
    inventory = data.get('fish_inventory', [])

    result = calculate_tank_bioload(l, w, h, inventory, f_type, plants)
    return jsonify({'success': True, 'bioload_analysis': result})


# ============================================================
# CHẠY ỨNG DỤNG
# ============================================================

if __name__ == '__main__':
    os.makedirs(DATASET_DIR, exist_ok=True)
    for folder in SPECIES_MAP:
        os.makedirs(os.path.join(DATASET_DIR, folder), exist_ok=True)

    print("=" * 50)
    print("QUAN LY DATASET CA CANH")
    print("=" * 50)
    print(f"Dataset: {DATASET_DIR}")
    print(f"Mo trinh duyet: http://127.0.0.1:5000")
    print("=" * 50)

    app.run(debug=True, host='127.0.0.1', port=5000)
