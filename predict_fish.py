"""
KỊCH BẢN DỰ ĐOÁN NHẬN DIỆN LOÀI CÁ BẰNG MÔ HÌNH YOLOV8
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Nhận diện 20 loài cá cảnh từ ảnh chụp camera IoT, trả về độ tin cậy và thông số môi trường thủy sinh.
"""

import os
import sys
import json
import argparse
from ultralytics import YOLO

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATHS = [
    os.path.join(BASE_DIR, 'weights', 'best_fish_yolov8.pt'),
    os.path.join(BASE_DIR, 'runs', 'classify', 'fish_yolov8_model', 'weights', 'best.pt'),
    'yolov8n-cls.pt'
]

SPECIES_MAP = {
    'ca_ba_duoi': {'vn': 'Cá Ba Đuôi / Cá Vàng', 'sci': 'Carassius auratus', 'temp': '18-24°C', 'ph': '7.0-7.8'},
    'ca_bay_mau': {'vn': 'Cá Bảy Màu / Guppy', 'sci': 'Poecilia reticulata', 'temp': '22-28°C', 'ph': '7.0-8.2'},
    'ca_but_chi': {'vn': 'Cá Bút Chì', 'sci': 'Crossocheilus oblongus', 'temp': '24-26°C', 'ph': '6.5-7.5'},
    'ca_chuot': {'vn': 'Cá Chuột', 'sci': 'Corydoras spp.', 'temp': '22-26°C', 'ph': '6.0-7.5'},
    'ca_da_quang': {'vn': 'Cá Dạ Quang / GloFish', 'sci': 'Gymnocorymbus ternetzi', 'temp': '22-27°C', 'ph': '6.5-7.5'},
    'ca_dia': {'vn': 'Cá Dĩa / Discus', 'sci': 'Symphysodon spp.', 'temp': '28-31°C', 'ph': '6.0-6.8'},
    'ca_diec_anh_dao': {'vn': 'Cá Diếc Anh Đào', 'sci': 'Puntius titteya', 'temp': '23-27°C', 'ph': '6.0-7.2'},
    'ca_duoi_kiem': {'vn': 'Cá Đuôi Kiếm', 'sci': 'Xiphophorus hellerii', 'temp': '22-28°C', 'ph': '7.0-8.2'},
    'ca_hong_ket': {'vn': 'Cá Hồng Két', 'sci': 'Blood Parrot Cichlid', 'temp': '26-30°C', 'ph': '6.5-7.8'},
    'ca_koi': {'vn': 'Cá Chép Koi', 'sci': 'Cyprinus carpio koi', 'temp': '15-26°C', 'ph': '7.0-8.5'},
    'ca_la_han': {'vn': 'Cá La Hán', 'sci': 'Flowerhorn Cichlid', 'temp': '27-31°C', 'ph': '7.2-8.0'},
    'ca_lau_kieng': {'vn': 'Cá Lau Kiếng / Tỳ Bà', 'sci': 'Hypostomus plecostomus', 'temp': '20-28°C', 'ph': '6.5-7.8'},
    'ca_molly': {'vn': 'Cá Molly / Bình Tích', 'sci': 'Poecilia sphenops', 'temp': '24-28°C', 'ph': '7.2-8.2'},
    'ca_mun': {'vn': 'Cá Mún / Platy', 'sci': 'Xiphophorus maculatus', 'temp': '20-26°C', 'ph': '7.0-8.2'},
    'ca_neon': {'vn': 'Cá Neon', 'sci': 'Paracheirodon innesi', 'temp': '20-26°C', 'ph': '6.0-7.0'},
    'ca_rong': {'vn': 'Cá Rồng / Arowana', 'sci': 'Scleropages formosus', 'temp': '26-30°C', 'ph': '6.5-7.5'},
    'ca_sac': {'vn': 'Cá Sặc Cảnh', 'sci': 'Trichogaster spp.', 'temp': '22-28°C', 'ph': '6.0-7.5'},
    'ca_soc_ngua': {'vn': 'Cá Sóc Ngựa', 'sci': 'Danio rerio', 'temp': '18-25°C', 'ph': '6.5-7.5'},
    'ca_thien_than': {'vn': 'Cá Thần Tiên', 'sci': 'Pterophyllum scalare', 'temp': '24-29°C', 'ph': '6.0-7.4'},
    'ca_xiem': {'vn': 'Cá Xiêm / Betta', 'sci': 'Betta splendens', 'temp': '24-30°C', 'ph': '6.5-7.5'}
}


_CACHED_MODEL = None
_CACHED_PATH = None

def load_model():
    global _CACHED_MODEL, _CACHED_PATH
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL, _CACHED_PATH

    for p in MODEL_PATHS:
        if os.path.exists(p):
            _CACHED_MODEL = YOLO(p)
            _CACHED_PATH = p
            return _CACHED_MODEL, _CACHED_PATH
    return None, None



def predict_image(image_path, as_json=False):
    if not os.path.exists(image_path):
        err = f"Lỗi: Không tìm thấy file '{image_path}'"
        if as_json:
            print(json.dumps({'success': False, 'error': err}))
        else:
            print(f"❌ {err}")
        return None

    model, path_used = load_model()
    if not model:
        err = "Lỗi: Chưa tìm thấy trọng số mô hình đã huấn luyện ('best_fish_yolov8.pt'). Vui lòng chạy 'train_yolo.py' trước!"
        if as_json:
            print(json.dumps({'success': False, 'error': err}))
        else:
            print(f"❌ {err}")
        return None

    results = model.predict(source=image_path, verbose=False)
    r = results[0]

    names = r.names
    probs = r.probs.data.tolist()

    ranked = sorted([(names[i], probs[i]) for i in range(len(probs))], key=lambda x: x[1], reverse=True)
    top1_key, top1_prob = ranked[0]
    top1_meta = SPECIES_MAP.get(top1_key, {'vn': top1_key, 'sci': '', 'temp': '24-28°C', 'ph': '6.5-7.5'})

    top3 = []
    for k, p in ranked[:3]:
        m = SPECIES_MAP.get(k, {'vn': k})
        top3.append({'species_key': k, 'name': m['vn'], 'confidence': round(p * 100, 2)})

    output = {
        'success': True,
        'model_used': os.path.basename(path_used),
        'top1': {
            'species_key': top1_key,
            'name': top1_meta['vn'],
            'sci_name': top1_meta['sci'],
            'confidence': round(top1_prob * 100, 2),
            'environment': {
                'temperature': top1_meta['temp'],
                'ph': top1_meta['ph']
            }
        },
        'top3': top3
    }

    if as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 65)
        print("🎯 KẾT QUẢ NHẬN DIỆN CÁ CẢNH (YOLOV8 COMPUTER VISION)")
        print("=" * 65)
        print(f"📸 Ảnh đầu vào:   {os.path.basename(image_path)}")
        print(f"🧠 Mô hình dùng:  {os.path.basename(path_used)}")
        print(f"🏆 LOÀI DỰ ĐOÁN:  {top1_meta['vn']} ({top1_meta['sci']})")
        print(f"⚡ Độ tin cậy:    {top1_prob*100:.2f}%")
        print(f"🌡️ Nhiệt độ IoT:  {top1_meta['temp']}")
        print(f"💧 Độ pH IoT:     {top1_meta['ph']}")
        print("\n📊 Top 3 ứng viên có xác suất cao nhất:")
        for idx, item in enumerate(top3, 1):
            bar = "█" * int(item['confidence'] / 5)
            print(f"  {idx}. {item['name']:25s} {item['confidence']:5.1f}%  | {bar}")
        print("=" * 65)

    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Predict fish species using YOLOv8")
    parser.add_argument('image', type=str, help="Path to input fish image")
    parser.add_argument('--json', action='store_true', help="Output as JSON")
    args = parser.parse_args()

    predict_image(args.image, as_json=args.json)
