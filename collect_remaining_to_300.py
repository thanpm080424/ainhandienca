"""
NẠP BỔ SUNG 5 LOÀI CUỐI ĐỂ TẤT CẢ 20 LOÀI CÁN MỐC >= 300 - 350 ẢNH
Đồ án tốt nghiệp: Lê Quốc Trí & Phạm Minh Thân
"""

import sys
import smart_fish_collector
import sync_recent_approved

TARGET_REMAINING = [
    ('ca_neon', 10),
    ('ca_diec_anh_dao', 15),
    ('ca_hong_ket', 20),
    ('ca_lau_kieng', 40),
    ('ca_da_quang', 50),
    ('ca_sac', 10),
    ('ca_thien_than', 15),
]

def main():
    print("=" * 70, flush=True)
    print("🚀 NẠP NỐT CÁC LOÀI ĐỂ 100% 20 LOÀI ĐẠT TRÊN 300 - 350 ẢNH", flush=True)
    print("=" * 70, flush=True)

    smart_fish_collector.init_database_hashes()

    total = 0
    for sp_key, target in TARGET_REMAINING:
        try:
            added = smart_fish_collector.process_species_collection(sp_key, target_add=target)
            total += added
            try:
                sync_recent_approved.sync_approved()
            except Exception:
                pass
        except Exception as e:
            print(f"Lỗi {sp_key}: {e}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"🎉 HOÀN THÀNH! ĐÃ THÊM: +{total} ẢNH", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
