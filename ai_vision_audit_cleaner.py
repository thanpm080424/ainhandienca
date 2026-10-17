"""
HỆ THỐNG KIỂM ĐỊNH & THANH LỌC THỊ GIÁC BẰNG AI VISION (GEMINI VISION)
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Mục đích:
- KHÔNG ĐỌC CHỮ / TIÊU ĐỀ NỮA, MÀ DÙNG MẮT AI (GEMINI VISION) NHÌN TRỰC TIẾP TỪNG BỨC ẢNH.
- Loại bỏ triệt để:
  1. Ảnh bìa YouTube có chữ to, hình ghép collage, mặt người.
  2. Ảnh slide/infographic bảng thông số kỹ thuật (pH, nhiệt độ).
  3. Ảnh phụ kiện bể cá (máy lọc, đèn LED, lọ thuốc, thức ăn).
  4. Ảnh nhầm loài (ví dụ ảnh cá Betta/Thần Tiên nằm nhầm trong thư mục Cá Dạ Quang).
  5. Ảnh mô hình nhựa, tranh vẽ chì, đồ chơi.
- Tự động di chuyển ảnh sai vào '_anh_nghi_ngo/<loài>/' và ghi nhật ký lên Web App.
"""

import os
import sys
import time
import json
import shutil
from google import genai
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
SUSPECT_DIR = os.path.join(DATASET_DIR, '_anh_nghi_ngo')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')

API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not API_KEY:
    env_file = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY='):
                        API_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass

client = genai.Client(api_key=API_KEY) if API_KEY else None


SPECIES_GUIDE = {
    'ca_ba_duoi': {
        'name': 'Cá Ba Đuôi / Cá Vàng',
        'sci_name': 'Carassius auratus (Goldfish)',
        'description': 'Cá vàng thân tròn mập, đuôi xòe voan hoặc 3-4 thùy, các dòng Oranda đầu lân, Ranchu không vây lưng, Ryukin gù. Tuyệt đối không phải cá nhiệt đới khác.',
    },
    'ca_bay_mau': {
        'name': 'Cá Bảy Màu / Guppy',
        'sci_name': 'Poecilia reticulata',
        'description': 'Cá nhỏ, con đực đuôi xòe to rực rỡ nhiều hoa văn, vây lưng đẹp. Tuyệt đối không phải cá khác.',
    },
    'ca_but_chi': {
        'name': 'Cá Bút Chì',
        'sci_name': 'Crossocheilus oblongus (Siamese Algae Eater) hoặc Nannostomus',
        'description': 'Thân dài thon như bút chì, đặc trưng dải sọc đen đậm chạy dọc từ mũi qua mắt đến hết đuôi. Tuyệt đối không phải cây bút chì thật hay cá khác.',
    },
    'ca_chuot': {
        'name': 'Cá Chuột',
        'sci_name': 'Corydoras Catfish',
        'description': 'Cá da trơn nhỏ bơi tầng đáy, bụng phẳng, miệng có râu xúc giác, vây lưng nhọn.',
    },
    'ca_da_quang': {
        'name': 'Cá Dạ Quang / GloFish',
        'sci_name': 'Gymnocorymbus ternetzi / GloFish fluorescent fish',
        'description': 'Cá phát màu huỳnh quang neon rực rỡ (xanh lá mạ, hồng, cam, đỏ, tím). Tuyệt đối không phải cá Betta, cá Thần Tiên hay đèn LED, đồ chơi nhựa.',
    },
    'ca_dia': {
        'name': 'Cá Dĩa',
        'sci_name': 'Symphysodon (Discus)',
        'description': 'Thân tròn xoe dẹp mỏng như chiếc đĩa tròn, hoa văn vân da rắn hoặc sọc hoa sen rực rỡ.',
    },
    'ca_diec_anh_dao': {
        'name': 'Cá Diếc Anh Đào',
        'sci_name': 'Puntius titteya (Cherry Barb)',
        'description': 'Cá nhỏ màu đỏ anh đào đậm hoặc hồng đỏ, thân thon có sọc mờ.',
    },
    'ca_duoi_kiem': {
        'name': 'Cá Đuôi Kiếm',
        'sci_name': 'Xiphophorus hellerii (Swordtail)',
        'description': 'Thân thon, đặc trưng con đực có thùy dưới vây đuôi nhọn hoắt kéo dài như mũi kiếm.',
    },
    'ca_hong_ket': {
        'name': 'Cá Hồng Két',
        'sci_name': 'Blood Parrot Cichlid (Amphilophus citrinellus)',
        'description': 'Cá thân tròn mập ú màu đỏ hoặc cam tươi, miệng hình chữ V/trái tim không khép kín được.',
    },
    'ca_koi': {
        'name': 'Cá Koi',
        'sci_name': 'Cyprinus carpio (Nishikigoi)',
        'description': 'Cá chép cảnh to lớn, vảy to óng ánh, các mảng khoang màu đỏ/trắng/đen/vàng trên lưng, có râu.',
    },
    'ca_la_han': {
        'name': 'Cá La Hán',
        'sci_name': 'Flowerhorn Cichlid',
        'description': 'Đầu có khối u bướu (gù đầu) to tròn nhô cao, thân có hoa văn đốm đen chữ hán và ánh kim châu.',
    },
    'ca_lau_kieng': {
        'name': 'Cá Lau Kiếng / Tỳ Bà',
        'sci_name': 'Hypostomus plecostomus / Ancistrus',
        'description': 'Cá da trơn giáp cứng màu nâu đen đốm da báo, miệng hình giác hút bám vào kính hồ hoặc đá để nạo rêu.',
    },
    'ca_molly': {
        'name': 'Cá Molly / Bình Tích',
        'sci_name': 'Poecilia sphenops / Poecilia latipinna',
        'description': 'Thân bầu dục tròn trịa, vây lưng rộng hình buồm, nhiều màu sắc (trắng, vàng, đốm hoa cúc).',
    },
    'ca_mun': {
        'name': 'Cá Mún / Hắc Molly / Platy',
        'sci_name': 'Xiphophorus maculatus hoặc Black Molly',
        'description': 'Cá nhỏ thân ngắn mập, màu đỏ cờ/cam (cá Mún) hoặc đen tuyền đồng nhất (Hắc Molly).',
    },
    'ca_neon': {
        'name': 'Cá Neon',
        'sci_name': 'Paracheirodon innesi (Neon Tetra / Cardinal Tetra)',
        'description': 'Cá nhỏ bơi theo đàn, có một dải sọc xanh lam/ngọc phát sáng chạy dọc lưng, nửa dưới bụng và đuôi đỏ tươi.',
    },
    'ca_rong': {
        'name': 'Cá Rồng',
        'sci_name': 'Scleropages formosus (Arowana)',
        'description': 'Cá cỡ lớn thân dài uy nghi, vảy to như vảy rồng sáng bóng (Huyết Long, Quá Bối, Kim Long), miệng chĩa lên có 2 râu.',
    },
    'ca_sac': {
        'name': 'Cá Sặc Cảnh',
        'sci_name': 'Trichogaster / Trichopodus (Gourami)',
        'description': 'Thân dẹp, đặc biệt có 2 vây bụng tiêu biến thành 2 sợi râu dài như ăng-ten thò ra phía trước để cảm nhận môi trường.',
    },
    'ca_soc_ngua': {
        'name': 'Cá Sóc Ngựa / Ngựa Vằn',
        'sci_name': 'Danio rerio (Zebra Danio)',
        'description': 'Cá nhỏ thon, có 5 sọc màu xanh lam ánh kim chạy ngang song song từ mang tới hết đuôi như ngựa vằn.',
    },
    'ca_thien_than': {
        'name': 'Cá Thần Tiên',
        'sci_name': 'Pterophyllum scalare (Angelfish)',
        'description': 'Thân dẹp mỏng hình tam giác cân, vây lưng và vây hậu môn vươn dài thanh thoát hướng lên xuống như cánh thiên thần.',
    },
    'ca_xiem': {
        'name': 'Cá Xiêm / Betta',
        'sci_name': 'Betta splendens (Siamese Fighting Fish)',
        'description': 'Cá chọi cảnh, bộ vây đuôi xòe tròn lộng lẫy (Halfmoon, Plakat, Crowntail), màu sắc rực rỡ.',
    },
}


def inspect_image_visually(img_path, species_key):
    """
    Sử dụng Gemini Vision NHÌN TRỰC TIẾP VÀO ẢNH.
    Trả về: (verdict: 'KEEP'|'REJECT', visual_content: str, reason: str)
    """
    guide = SPECIES_GUIDE.get(species_key, {})
    try:
        with Image.open(img_path) as raw_img:
            img = raw_img.copy()
        img.thumbnail((512, 512))

        prompt = f"""Bạn là chuyên gia giám định thị giác AI (Computer Vision) cho hệ thống IoT camera nhận diện cá cảnh.
HÃY NHÌN TRỰC TIẾP VÀO HÌNH ẢNH NÀY (KHÔNG ĐƯỢC ĐOÁN DỰA THEO TÊN FILE HAY CHỮ VIẾT).

LOÀI CẦN KIỂM TRA: {guide.get('name', species_key)}
TÊN KHOA HỌC: {guide.get('sci_name', '')}
ĐẶC ĐIỂM HÌNH THÁI CHUẨN: {guide.get('description', '')}

TIÊU CHUẨN BẮT BUỘC:
1. Phải là CON CÁ THỰC TẾ ĐANG BƠI TRONG NƯỚC (hồ kính, bể thủy sinh, ao hồ).
2. Phải ĐÚNG CHÍNH XÁC là loài {guide.get('name', species_key)}.
3. BẮT BUỘC TỪ CHỐI (REJECT) nếu ảnh thuộc các trường hợp sau:
   - Ảnh bìa YouTube, ảnh có chữ to đè lên hình, ảnh ghép nhiều hình (collage).
   - Ảnh slide, infographic, bảng thông số kỹ thuật (pH, nhiệt độ, chữ viết).
   - Ảnh đồ vật, máy lọc, đèn LED, bao bì thuốc/cám, vợt cá, bàn tay người.
   - Ảnh cá loài khác (ví dụ: cá Betta/Thần Tiên nằm nhầm trong thư mục Cá Dạ Quang).
   - Ảnh cá chết, cá đĩa trên thớt, chảo chiên.
   - Ảnh tranh vẽ chì, hoạt hình, mô hình đồ chơi nhựa.

Chỉ trả về JSON duy nhất theo định dạng này:
{{
  "verdict": "KEEP" hoặc "REJECT",
  "is_live_fish": true hoặc false,
  "is_correct_species": true hoặc false,
  "has_large_text_or_collage": true hoặc false,
  "visual_content": "Mô tả ngắn bạn nhìn thấy gì trong hình",
  "reason": "Giải thích ngắn gọn 1 câu lý do KEEP hoặc REJECT"
}}"""

        models_to_try = ['gemini-4-argon', 'gemini-3.5-flash', 'gemini-flash-lite-latest']
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[img, prompt]
                )
                txt = response.text.strip()
                if txt.startswith('```json'):
                    txt = txt[7:-3].strip()
                elif txt.startswith('```'):
                    txt = txt[3:-3].strip()
                data = json.loads(txt)
                verdict = data.get('verdict', 'REJECT').upper()
                if not data.get('is_live_fish') or not data.get('is_correct_species') or data.get('has_large_text_or_collage'):
                    verdict = 'REJECT'
                visual_desc = f"[{model_name}] {data.get('visual_content', '')}"
                return verdict, visual_desc, data.get('reason', '')
            except Exception as e:
                # Nếu model hết quota hoặc 503, thử model tiếp theo trong danh sách
                continue

        return 'ERROR', 'Lỗi kết nối', 'Không thể gọi AI Vision sau khi thử các model'
    except Exception as e:
        return 'ERROR', 'Lỗi file ảnh', str(e)


def audit_and_clean_species(species_key, max_check=50, move_suspect=True):
    """Quét và thanh lọc bằng AI Vision cho 1 loài cá."""
    guide = SPECIES_GUIDE.get(species_key, {})
    folder = os.path.join(DATASET_DIR, species_key)
    if not os.path.exists(folder):
        return 0, 0

    files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))]
    if max_check:
        # Ưu tiên kiểm tra các file từ YouTube / Google / web tải về
        files = files[:max_check]

    print(f"\n{'='*70}", flush=True)
    print(f"👁️ ĐANG DÙNG AI VISION SOI TỪNG ẢNH: [{guide.get('name', species_key)}]", flush=True)
    print(f"   Thư mục: dataset_ca/{species_key} | Kiểm tra: {len(files)} ảnh", flush=True)
    print(f"{'='*70}", flush=True)

    keep_count = 0
    reject_count = 0

    for idx, fname in enumerate(files, 1):
        fp = os.path.join(folder, fname)
        verdict, visual_content, reason = inspect_image_visually(fp, species_key)

        safe_fname = fname[:32]
        if verdict == 'KEEP':
            keep_count += 1
            print(f"  ✅ [{idx}/{len(files)}] {safe_fname} -> [ĐẠT CHUẨN] {visual_content[:45]}", flush=True)
        elif verdict == 'REJECT':
            reject_count += 1
            print(f"  ❌ [{idx}/{len(files)}] {safe_fname} -> [LOẠI BỎ] {reason[:60]} ({visual_content[:35]})", flush=True)

            if move_suspect:
                target_sub = os.path.join(SUSPECT_DIR, species_key)
                os.makedirs(target_sub, exist_ok=True)
                dest = os.path.join(target_sub, fname)
                try:
                    shutil.move(fp, dest)
                    print(f"      ↪️ Đã chuyển ra: _anh_nghi_ngo/{species_key}/{safe_fname}", flush=True)
                except Exception as e:
                    pass

                # Cập nhật vào audit_log.json để hiện lên Web Dashboard
                try:
                    if os.path.exists(AUDIT_LOG_FILE):
                        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as af:
                            ad = json.load(af)
                        if 'flagged_wrong' not in ad:
                            ad['flagged_wrong'] = []
                        rec = {
                            'filename': fname,
                            'species': species_key,
                            'species_name': guide.get('name', species_key),
                            'identified_as': visual_content[:60],
                            'confidence': 'high',
                            'reason': f"AI Vision phát hiện: {reason[:80]}",
                            'source': 'Bộ lọc Thị Giác Gemini Vision',
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        ad['flagged_wrong'].insert(0, rec)
                        ad['flagged_wrong'] = ad['flagged_wrong'][:200]
                        with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as af:
                            json.dump(ad, af, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        else:
            print(f"  ⚠️ [{idx}/{len(files)}] {safe_fname} -> [BỎ QUA] {reason[:50]}", flush=True)

        time.sleep(0.3)

    print(f"\n📊 Kết quả [{guide.get('name', species_key)}]: Giữ lại: {keep_count} | Đã loại bỏ: {reject_count}", flush=True)
    return keep_count, reject_count


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'ca_da_quang'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    audit_and_clean_species(target, max_check=limit, move_suspect=True)
