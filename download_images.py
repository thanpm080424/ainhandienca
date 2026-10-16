"""
Script tai anh ca canh + dung Gemini AI kiem tra dung loai moi giu lai.
Quy trinh: Tai anh tu Bing -> Gemini nhin anh -> Dung loai? -> Giu / Xoa
"""

import os
import sys
import time
import json
import glob
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
from icrawler.builtin import BingImageCrawler
from PIL import Image

# ============================================================
# CAU HINH
# ============================================================
DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset_ca')
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_temp_download')
MIN_IMAGES = 200

API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Mapping loai ca -> thong tin tim kiem + ten khoa hoc
SPECIES_INFO = {
    'ca_ba_duoi': {
        'vn_name': 'Ca Ba Duoi',
        'en_name': 'Three Spot Gourami',
        'sci_name': 'Trichopodus trichopterus',
        'search_keywords': [
            'Three Spot Gourami fish',
            'Trichopodus trichopterus aquarium',
            'blue gourami fish',
        ],
        'verify_prompt': 'Ca ba duoi (Three Spot Gourami / Trichopodus trichopterus) - loai ca nuoc ngot co than det, co 2-3 cham den tren than, vay bung dai',
    },
    'ca_bay_mau': {
        'vn_name': 'Ca Bay Mau',
        'en_name': 'Guppy',
        'sci_name': 'Poecilia reticulata',
        'search_keywords': [
            'guppy fish colorful aquarium',
            'Poecilia reticulata fancy guppy',
            'guppy fish tank',
        ],
        'verify_prompt': 'Ca bay mau / Guppy (Poecilia reticulata) - ca nho, duoi xoe nhieu mau sac ruc ro, con duc co duoi dai dep',
    },
    'ca_but_chi': {
        'vn_name': 'Ca But Chi',
        'en_name': 'Pencilfish',
        'sci_name': 'Nannostomus',
        'search_keywords': [
            'pencilfish Nannostomus aquarium',
            'pencil fish freshwater',
            'Nannostomus beckfordi',
        ],
        'verify_prompt': 'Ca but chi / Pencilfish (Nannostomus) - ca nho, than dai thon nhu cay but chi, co soc ngang hoac doc tren than',
    },
    'ca_chuot': {
        'vn_name': 'Ca Chuot',
        'en_name': 'Corydoras Catfish',
        'sci_name': 'Corydoras',
        'search_keywords': [
            'corydoras catfish aquarium',
            'cory catfish fish tank',
            'Corydoras paleatus',
        ],
        'verify_prompt': 'Ca chuot / Corydoras - ca da tram nho, co rau, bung phang, thuong boi o day be, than co cham hoac soc',
    },
    'ca_da_quang': {
        'vn_name': 'Ca Da Quang',
        'en_name': 'GloFish',
        'sci_name': 'GloFish (transgenic)',
        'search_keywords': [
            'GloFish tetra aquarium glowing',
            'GloFish fluorescent fish neon',
            'GloFish danio bright colors',
            'glofish aquarium fish tank',
        ],
        'verify_prompt': 'Ca da quang / GloFish - ca phat sang mau neon (xanh, do, cam, hong, tim) duoi den UV, mau ruc ro bat thuong',
    },
    'ca_dia': {
        'vn_name': 'Ca Dia',
        'en_name': 'Discus',
        'sci_name': 'Symphysodon',
        'search_keywords': [
            'discus fish aquarium colorful',
            'Symphysodon discus',
            'discus fish freshwater',
        ],
        'verify_prompt': 'Ca dia / Discus (Symphysodon) - than tron det nhu cai dia, mau sac da dang (do, xanh, vang), co hoa van dep',
    },
    'ca_diec_anh_dao': {
        'vn_name': 'Ca Diec Anh Dao',
        'en_name': 'Cherry Barb',
        'sci_name': 'Puntius titteya',
        'search_keywords': [
            'cherry barb fish aquarium',
            'Puntius titteya cherry',
            'cherry barb freshwater red',
        ],
        'verify_prompt': 'Ca diec anh dao / Cherry Barb (Puntius titteya) - ca nho, mau do/hong nhu hoa anh dao, con duc mau do tuoi',
    },
    'ca_duoi_kiem': {
        'vn_name': 'Ca Duoi Kiem',
        'en_name': 'Swordtail',
        'sci_name': 'Xiphophorus hellerii',
        'search_keywords': [
            'swordtail fish aquarium',
            'Xiphophorus hellerii',
            'swordtail fish colorful',
        ],
        'verify_prompt': 'Ca duoi kiem / Swordtail (Xiphophorus hellerii) - ca co phan duoi duoi dai nhu luoi kiem (con duc), nhieu mau sac',
    },
    'ca_hong_ket': {
        'vn_name': 'Ca Hong Ket',
        'en_name': 'Blood Parrot Cichlid',
        'sci_name': 'Blood Parrot Cichlid (hybrid)',
        'search_keywords': [
            'blood parrot cichlid fish',
            'blood parrot fish aquarium red',
            'red parrot cichlid fish tank',
            'blood parrot fish orange',
        ],
        'verify_prompt': 'Ca hong ket / Blood Parrot Cichlid - ca co than tron, mieng nho hinh trai tim, mau do/cam, dau lon tron',
    },
    'ca_koi': {
        'vn_name': 'Ca Koi',
        'en_name': 'Koi',
        'sci_name': 'Cyprinus rubrofuscus',
        'search_keywords': [
            'koi fish pond japanese',
            'koi carp colorful',
            'koi fish varieties',
        ],
        'verify_prompt': 'Ca Koi (Cyprinus rubrofuscus) - ca chep Nhat Ban co lon, nhieu mau (do, trang, vang, den), thuong nuoi ho',
    },
    'ca_la_han': {
        'vn_name': 'Ca La Han',
        'en_name': 'Flowerhorn Cichlid',
        'sci_name': 'Flowerhorn (hybrid)',
        'search_keywords': [
            'flowerhorn cichlid fish',
            'flowerhorn fish aquarium',
            'flowerhorn fish big head',
        ],
        'verify_prompt': 'Ca la han / Flowerhorn Cichlid - ca co buou lon tren dau (nuchal hump), mau sac ruc ro, than co cham den',
    },
    'ca_lau_kieng': {
        'vn_name': 'Ca Lau Kieng',
        'en_name': 'Plecostomus / Pleco',
        'sci_name': 'Hypostomus plecostomus',
        'search_keywords': [
            'plecostomus fish aquarium',
            'pleco fish tank algae eater',
            'pleco catfish sucker fish',
            'bristlenose pleco aquarium',
        ],
        'verify_prompt': 'Ca lau kieng / Pleco (Hypostomus) - ca da tram lon, mieng hut, than co giap/vay cung, thuong bam vao kinh be',
    },
    'ca_molly': {
        'vn_name': 'Ca Molly',
        'en_name': 'Molly Fish',
        'sci_name': 'Poecilia sphenops',
        'search_keywords': [
            'molly fish aquarium',
            'Poecilia sphenops molly',
            'balloon molly fish',
        ],
        'verify_prompt': 'Ca Molly (Poecilia sphenops) - ca nho-vua, nhieu mau sac, than hoi tron, vay lung co the cao (sailfin molly)',
    },
    'ca_mun': {
        'vn_name': 'Ca Mun',
        'en_name': 'Black Molly',
        'sci_name': 'Poecilia sphenops (black)',
        'search_keywords': [
            'black molly fish aquarium',
            'black molly Poecilia',
            'black molly fish tank',
        ],
        'verify_prompt': 'Ca mun / Black Molly - ca molly mau den tuyen, than tron, boi nhanh nhen, mau den dong nhat',
    },
    'ca_neon': {
        'vn_name': 'Ca Neon',
        'en_name': 'Neon Tetra',
        'sci_name': 'Paracheirodon innesi',
        'search_keywords': [
            'neon tetra fish aquarium',
            'Paracheirodon innesi neon',
            'neon tetra school fish',
        ],
        'verify_prompt': 'Ca neon / Neon Tetra (Paracheirodon innesi) - ca nho, co soc xanh neon sang doc than va bung do/cam',
    },
    'ca_rong': {
        'vn_name': 'Ca Rong',
        'en_name': 'Arowana',
        'sci_name': 'Scleropages',
        'search_keywords': [
            'arowana fish aquarium',
            'asian arowana Scleropages',
            'arowana fish red golden',
        ],
        'verify_prompt': 'Ca rong / Arowana (Scleropages) - ca lon, than dai, vay to sang bong, co rau, boi o tang mat nuoc',
    },
    'ca_sac': {
        'vn_name': 'Ca Sac',
        'en_name': 'Gourami',
        'sci_name': 'Osphronemidae',
        'search_keywords': [
            'dwarf gourami fish aquarium',
            'gourami fish colorful',
            'pearl gourami fish',
        ],
        'verify_prompt': 'Ca sac / Gourami - ca nuoc ngot, than det, vay bung dai thanh soi, nhieu mau sac, boi cham',
    },
    'ca_soc_ngua': {
        'vn_name': 'Ca Soc Ngua',
        'en_name': 'Zebra Danio',
        'sci_name': 'Danio rerio',
        'search_keywords': [
            'zebra danio fish aquarium',
            'Danio rerio zebrafish',
            'zebra fish freshwater',
        ],
        'verify_prompt': 'Ca soc ngua / Zebra Danio (Danio rerio) - ca nho, than co soc ngang xanh va trang/vang giong van ngua',
    },
    'ca_thien_than': {
        'vn_name': 'Ca Than Tien',
        'en_name': 'Angelfish',
        'sci_name': 'Pterophyllum scalare',
        'search_keywords': [
            'angelfish freshwater aquarium',
            'Pterophyllum scalare',
            'angelfish fish tank',
        ],
        'verify_prompt': 'Ca than tien / Angelfish (Pterophyllum scalare) - than det hinh tam giac, vay lung va vay bung rat dai, di chuyen ung dung',
    },
    'ca_xiem': {
        'vn_name': 'Ca Xiem',
        'en_name': 'Betta / Siamese Fighting Fish',
        'sci_name': 'Betta splendens',
        'search_keywords': [
            'betta fish aquarium colorful',
            'siamese fighting fish',
            'betta splendens halfmoon',
        ],
        'verify_prompt': 'Ca xiem / Betta (Betta splendens) - ca co vay va duoi rat dai mong, mau sac ruc ro, con duc hung du',
    },
}


def count_images(folder_path):
    """Dem so anh hop le trong thu muc."""
    if not os.path.exists(folder_path):
        return 0
    valid_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    return sum(1 for f in os.listdir(folder_path)
               if os.path.isfile(os.path.join(folder_path, f))
               and os.path.splitext(f)[1].lower() in valid_ext)


def verify_image_with_gemini(client, image_path, species_info):
    """Dung Gemini AI nhin anh va xac nhan dung loai ca khong."""
    try:
        img = Image.open(image_path)
        # Resize de giam dung luong gui API
        img.thumbnail((512, 512))

        prompt = f"""Hay nhin anh nay va tra loi CHINH XAC:

Anh nay co phai la "{species_info['vn_name']}" ({species_info['en_name']}, {species_info['sci_name']}) khong?

Dac diem nhan dang: {species_info['verify_prompt']}

Quy tac:
- Neu anh la CON CA va DUNG LOAI nay -> tra loi CHINH XAC chi 1 tu: YES
- Neu anh KHONG PHAI loai ca nay, hoac khong phai anh ca, hoac anh mo/khong ro -> tra loi chi 1 tu: NO

Chi tra loi YES hoac NO, khong giai thich."""

        models_to_try = ['gemini-4-argon', 'gemini-3.5-flash', 'gemini-flash-lite-latest']
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[img, prompt]
                )
                answer = response.text.strip().upper()
                return 'YES' in answer
            except Exception as e:
                continue
        return False

    except Exception as e:
        print(f"    Loi Gemini: {e}")
        return False


def download_and_verify(client, species_folder, species_info, target=30):
    """Tai anh ung vien -> Gemini kiem tra -> Giu lai anh dung."""

    folder_path = os.path.join(DATASET_DIR, species_folder)
    temp_path = os.path.join(TEMP_DIR, species_folder)
    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(temp_path, exist_ok=True)

    current_count = count_images(folder_path)
    print(f"  Hien tai: {current_count} anh")

    # Buoc 1: Tai anh ung vien vao thu muc tam
    per_keyword = max(10, (target * 2) // len(species_info['search_keywords']))

    for keyword in species_info['search_keywords']:
        print(f"  Tim kiem: '{keyword}'...")
        try:
            crawler = BingImageCrawler(
                feeder_threads=1,
                parser_threads=1,
                downloader_threads=2,
                storage={'root_dir': temp_path}
            )
            crawler.crawl(keyword=keyword, max_num=per_keyword, min_size=(150, 150))
            time.sleep(1)
        except Exception as e:
            print(f"    Loi tai: {e}")

    # Buoc 2: Gemini kiem tra tung anh
    temp_images = sorted(glob.glob(os.path.join(temp_path, '*')))
    valid_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    temp_images = [f for f in temp_images
                   if os.path.isfile(f) and os.path.splitext(f)[1].lower() in valid_ext]

    print(f"  Tai duoc {len(temp_images)} anh ung vien. Gemini dang kiem tra...")

    kept = 0
    removed = 0
    errors = 0

    for i, img_path in enumerate(temp_images):
        try:
            is_correct = verify_image_with_gemini(client, img_path, species_info)

            if is_correct:
                # Di chuyen vao dataset chinh
                filename = f"added_{species_folder}_{int(time.time())}_{i}.jpg"
                dest = os.path.join(folder_path, filename)
                os.rename(img_path, dest)
                kept += 1
                print(f"    [{i+1}/{len(temp_images)}] YES -> Giu lai")
            else:
                os.remove(img_path)
                removed += 1
                print(f"    [{i+1}/{len(temp_images)}] NO  -> Xoa")

            # Rate limit - doi 0.5 giay giua cac request
            time.sleep(0.5)

        except Exception as e:
            print(f"    [{i+1}/{len(temp_images)}] LOI: {e}")
            errors += 1
            try:
                os.remove(img_path)
            except:
                pass

    new_count = count_images(folder_path)
    print(f"  Ket qua: +{kept} anh dung | -{removed} anh sai | {errors} loi")
    print(f"  Tong: {current_count} -> {new_count} anh")

    return {
        'folder': species_folder,
        'name': species_info['vn_name'],
        'before': current_count,
        'after': new_count,
        'added': kept,
        'removed': removed,
        'errors': errors,
    }


def main():
    if not API_KEY:
        print("LOI: Chua co GEMINI_API_KEY!")
        print("Hay dat bien moi truong: set GEMINI_API_KEY=your_key")
        sys.exit(1)

    # Khoi tao Gemini client
    client = genai.Client(api_key=API_KEY)

    # Test API key
    print("Kiem tra API key...")
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents='Tra loi 1 tu: OK'
            )
            print(f"API key hop le! Response: {response.text.strip()}")
            break
        except Exception as e:
            if '503' in str(e) and attempt < 4:
                print(f"  Server ban, thu lai sau 10 giay... (lan {attempt+1}/5)")
                time.sleep(10)
            elif attempt == 4:
                print(f"LOI API key: {e}")
                print("Server qua tai. Thu lai sau.")
                sys.exit(1)
            else:
                print(f"LOI API key: {e}")
                print("Vui long kiem tra lai API key tai: https://aistudio.google.com/apikey")
                sys.exit(1)

    print("\n" + "=" * 60)
    print("TAI ANH CA CANH + GEMINI AI KIEM TRA")
    print("=" * 60)
    print(f"Dataset: {DATASET_DIR}")
    print(f"Muc tieu: {MIN_IMAGES} anh/loai")
    print(f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Tao thu muc tam
    os.makedirs(TEMP_DIR, exist_ok=True)

    all_results = []

    # Uu tien loai thieu anh truoc
    species_order = sorted(
        SPECIES_INFO.items(),
        key=lambda x: count_images(os.path.join(DATASET_DIR, x[0]))
    )

    for species_folder, info in species_order:
        folder_path = os.path.join(DATASET_DIR, species_folder)
        current = count_images(folder_path)

        # Xac dinh so anh can tai
        if current < 150:
            target = 50
        elif current < MIN_IMAGES:
            target = 30
        else:
            target = 15

        print(f"\n{'='*60}")
        print(f"[{info['vn_name']}] ({info['en_name']})")
        print(f"  Thu muc: {species_folder}/")

        result = download_and_verify(client, species_folder, info, target)
        all_results.append(result)

    # Xoa thu muc tam
    import shutil
    try:
        shutil.rmtree(TEMP_DIR)
    except:
        pass

    # Ghi log
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download_log.json')
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'method': 'Bing Image Search + Gemini AI verification',
        'note': 'Moi anh duoc Gemini AI xac nhan dung loai truoc khi them vao dataset',
        'results': all_results
    }
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    # Tong ket
    print("\n" + "=" * 60)
    print("TONG KET")
    print("=" * 60)
    total_added = 0
    for r in all_results:
        status = "DU" if r['after'] >= MIN_IMAGES else "THIEU"
        print(f"  {r['name']}: {r['before']} -> {r['after']} (+{r['added']}) [{status}]")
        total_added += r['added']

    total_images = sum(count_images(os.path.join(DATASET_DIR, f)) for f in SPECIES_INFO)
    print(f"\n  Tong anh them: +{total_added}")
    print(f"  Tong dataset: {total_images} anh")
    print(f"  Log: {log_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
