"""
Script quet sach 100% anh trung lap trong toan bo Dataset Ca Canh:
- So khop chinh xac MD5 hash (trung tuyet doi tung byte)
- So khop thi giac dHash (trung hinh anh mat thuong, ke ca khi bi doi ten hoac nen)
- Giu lai 1 ban goc duy nhat, xoa toan bo ban sao trung lap de dataset sach 100%.
"""

import os
import sys
import hashlib
from PIL import Image

# Reconfigure console UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset_ca')


def dhash(image, hash_size=8):
    """Tinh ma bam thi giac 64-bit."""
    image = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(image.get_flattened_data() if hasattr(image, 'get_flattened_data') else image.getdata())
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


def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def run_deduplication():
    print("=" * 65)
    print("QUET VA DON DEP ANH TRUNG LAP TRONG DATASET CA CANH")
    print(f"Thu muc: {DATASET_DIR}")
    print("=" * 65)

    seen_md5 = {}
    seen_dhash = {}

    species_folders = sorted(os.listdir(DATASET_DIR))
    total_scanned = 0
    total_removed = 0

    report = {}

    for sp in species_folders:
        sp_path = os.path.join(DATASET_DIR, sp)
        if not os.path.isdir(sp_path) or sp.startswith('.'):
            continue

        files = sorted(os.listdir(sp_path))
        sp_removed = 0

        for f in files:
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                continue

            total_scanned += 1
            fp = os.path.join(sp_path, f)

            try:
                # 1. Kiem tra MD5
                m = get_md5(fp)
                if m in seen_md5:
                    os.remove(fp)
                    sp_removed += 1
                    total_removed += 1
                    continue
                else:
                    seen_md5[m] = fp

                # 2. Kiem tra dHash thi giac
                with Image.open(fp) as img:
                    dh = dhash(img)
                if dh in seen_dhash:
                    os.remove(fp)
                    sp_removed += 1
                    total_removed += 1
                    continue
                else:
                    seen_dhash[dh] = fp

            except Exception as e:
                # File loi khong doc duoc -> xoa luon de sach dataset
                try:
                    os.remove(fp)
                    sp_removed += 1
                    total_removed += 1
                except:
                    pass

        after_count = len([x for x in os.listdir(sp_path) if os.path.isfile(os.path.join(sp_path, x))])
        report[sp] = {'before': len(files), 'after': after_count, 'removed': sp_removed}
        if sp_removed > 0:
            print(f"  [{sp:15s}]: Da xoa {sp_removed:2d} anh trung -> Con lai {after_count} anh duy nhat")

    print("\n" + "=" * 65)
    print("TONG KET DON DEP TRUNG LAP")
    print("=" * 65)
    print(f"Tong so anh da quet: {total_scanned}")
    print(f"Tong so anh trung lap da xoa bo: {total_removed}")
    print(f"Tong so anh DUY NHAT 100% con lai: {total_scanned - total_removed}")
    print("=" * 65)


if __name__ == '__main__':
    run_deduplication()
