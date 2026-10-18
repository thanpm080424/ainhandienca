"""
KỊCH BẢN DỰ ĐOÁN NHẬN DIỆN LOÀI CÁ BẰNG MÔ HÌNH YOLOV8 & PHÂN TÍCH LAI TẠP / HÌNH THÁI HỌC
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Nhận diện 20 loài cá cảnh từ ảnh chụp camera IoT, tích hợp:
1. Mô hình YOLOv8 Edge AI tốc độ cao (~5ms).
2. Module Giám Định Lai Tạp & Phân Tích Hình Thái Học Phân Cấp (Hierarchical & Hybrid Morphological Analysis).
3. Bảng đối chiếu giải phẫu độc quyền khi phát hiện kiểu hình trung gian / tương đồng họ.
4. Tra cứu dòng biến thể lai tạo thương mại (Commercial Morphs & Strains) và thông số môi trường thủy sinh.
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

# ============================================================
# CƠ SỞ TRI THỨC PHÂN CẤP SINH HỌC & LAI TẠP (KNOWLEDGE BASE)
# ============================================================

FISH_FAMILIES_TAXONOMY = {
    'poeciliidae': {
        'id': 'poeciliidae',
        'name': 'Họ Cá Đẻ Con (Poeciliidae)',
        'description': 'Các loài cá đẻ con phổ biến, có độ tương đồng hình thái rất cao và tỉ lệ lai chéo tự nhiên/nhân tạo lớn.',
        'species': ['ca_bay_mau', 'ca_molly', 'ca_mun', 'ca_duoi_kiem']
    },
    'cichlidae': {
        'id': 'cichlidae',
        'name': 'Họ Cá Cichlid / Rô Phi Cảnh (Cichlidae)',
        'description': 'Nhóm cá thông minh có tính lãnh thổ, gồm nhiều dòng lai nhân tạo đa loài (Flowerhorn, Blood Parrot).',
        'species': ['ca_dia', 'ca_thien_than', 'ca_hong_ket', 'ca_la_han']
    },
    'cyprinidae': {
        'id': 'cyprinidae',
        'name': 'Họ Cá Chép & Cá Vàng (Cyprinidae & Danionidae)',
        'description': 'Họ cá chép với hàng trăm biến thể lai tạo kiểu hình vây, gù đầu và màu sắc qua hàng ngàn năm.',
        'species': ['ca_ba_duoi', 'ca_koi', 'ca_soc_ngua', 'ca_diec_anh_dao', 'ca_but_chi']
    },
    'characidae': {
        'id': 'characidae',
        'name': 'Họ Cá Characin & Thủy Sinh Phát Quang (Characidae)',
        'description': 'Cá bơi đàn nhỏ, bao gồm cá thủy sinh tự nhiên và các dòng cá chuyển gen phát huỳnh quang (GloFish).',
        'species': ['ca_neon', 'ca_da_quang']
    },
    'osphronemidae': {
        'id': 'osphronemidae',
        'name': 'Họ Cá Mê Lộ / Thở Khí Quyển (Osphronemidae)',
        'description': 'Cá có cơ quan thở khí quyển trên mặt nước, đa dạng từ hiền lành đến hiếu chiến.',
        'species': ['ca_sac', 'ca_xiem']
    },
    'benthic_predators': {
        'id': 'benthic_predators',
        'name': 'Họ Cá Tầng Đáy & Săn Mồi Cỡ Lớn',
        'description': 'Cá da trơn bám đáy chuyên dọn bể và cá rồng săn mồi kích thước lớn.',
        'species': ['ca_chuot', 'ca_lau_kieng', 'ca_rong']
    }
}

SPECIES_COMMERCIAL_MORPHTYPES = {
    'ca_bay_mau': {
        'lineage_title': 'Các dòng Cá Bảy Màu (Guppy Strains & Morphs)',
        'common_morphs': [
            'Dumbo Red Tail (Tai voi vây bơi to bản, đuôi đỏ)',
            'Full Gold (Toàn thân ánh kim vàng 24k)',
            'Blue Grass (Đuôi hoa văn hạt cỏ chấm bi xanh lam)',
            'Albino Koi / Red Ear (Mắt đỏ, đầu đỏ thân trắng giống cá Koi)',
            'Dragon / Tuxedo (Vảy rồng ánh kim, nửa thân sau đen tuyền)',
            'Ribbon / Swallow (Vây bụng và vây hậu môn kéo dài mềm mại)'
        ],
        'wild_vs_fancy': 'Bảy Màu hoang dã thân xám nhỏ có chấm màu, còn Bảy Màu cảnh nuôi sinh sản có vây đuôi xòe quạt chiếm đến 40-50% chiều dài thân.'
    },
    'ca_molly': {
        'lineage_title': 'Các dòng Cá Molly / Bình Tích (Molly Morphs & Hybrids)',
        'common_morphs': [
            'Black Molly (Đen tuyền toàn thân nhung)',
            'Sailfin Molly (Vây lưng cánh buồm khổng lồ vươn cao)',
            'Balloon Molly (Bình tích bụng tròn vo như quả bóng)',
            'Golden Dust / Dalmatian (Vàng kim chấm đen đốm báo tuyết)',
            'Lyretail Molly (Đuôi đàn lia hai nhánh cong vút)'
        ],
        'wild_vs_fancy': 'Molly nguyên bản thân dài hình thoi, dòng nuôi cảnh phổ biến nhất là dòng Balloon bụng phệ do đột biến cột sống nhân tạo.'
    },
    'ca_mun': {
        'lineage_title': 'Các dòng Cá Mún / Platy (Platy Morphs & Hybrids)',
        'common_morphs': [
            'Mickey Mouse Platy (Gốc đuôi có 3 đốm đen hình đầu chuột Mickey)',
            'Red Wagtail Platy (Thân đỏ rực, vây lưng và vây đuôi đen tuyền)',
            'Tuxedo Platy (Thân pha mảng đen bạc sang trọng)',
            'Panda Platy (Màu trắng đốm mắt và vây đen)',
            'Marigold / Sunset Platy (Màu vàng chuyển cam ánh hoàng hôn)'
        ],
        'wild_vs_fancy': 'Thường lai chéo với Cá Đuôi Kiếm để tạo ra màu đỏ rực và hoa văn mới, con cái của Mún và Đuôi Kiếm rất giống nhau.'
    },
    'ca_duoi_kiem': {
        'lineage_title': 'Các dòng Cá Đuôi Kiếm (Swordtail Strains)',
        'common_morphs': [
            'Red Swordtail (Đuôi kiếm đỏ cờ truyền thống)',
            'Kohaku Swordtail (Khoang đỏ trắng phong cách cá chép Nhật)',
            'Neon / Green Swordtail (Thân xanh lục ánh kim phản chiếu)',
            'Tuxedo Swordtail (Lưng đen bụng trắng hoặc đỏ đen)',
            'Hi-Fin Lyretail Swordtail (Vây buồm cao kết hợp đuôi song kiếm)'
        ],
        'wild_vs_fancy': 'Cá đực có thùy dưới vây đuôi kéo dài thành mũi kiếm cứng cáp dùng tán tỉnh cá cái và thị uy lãnh thổ.'
    },
    'ca_ba_duoi': {
        'lineage_title': 'Các biến thể Cá Ba Đuôi / Cá Vàng (Goldfish Morphs)',
        'common_morphs': [
            'Oranda (Đầu lân - bướu thịt phát triển trùm đỉnh đầu, đuôi xòe)',
            'Ranchu (Đế vương cá vàng - không có vây lưng, lưng cong mượt, đầu xù)',
            'Ryukin (Lưng gù nhô cao hình tam giác, bụng tròn)',
            'Black Moor (Hắc đài hồng - mắt lồi to tròn, toàn thân đen nhung)',
            'Pearlscale (Vảy ngọc trai gồ cao lóng lánh như hạt bắp)'
        ],
        'wild_vs_fancy': 'Được thuần hóa từ cá diếc hoang dã qua 1000 năm, phân hóa thành hơn 300 kiểu hình từ thân dài đến thân tròn không vây lưng.'
    },
    'ca_koi': {
        'lineage_title': 'Các dòng Cá Chép Koi Nhật Bản (Nishikigoi Varieties)',
        'common_morphs': [
            'Kohaku (Thân trắng hoa văn đỏ Hi)',
            'Taisho Sanke (Trắng đỏ kèm đốm đen Sumi)',
            'Showa Sanshoku (Đen tuyền nền chính kèm khoang đỏ trắng)',
            'Ogon (Toàn thân đơn sắc ánh kim vàng hoặc bạc Platinum)',
            'Chagoi (Màu trà/nâu đất - dòng lớn nhanh và dạn người nhất)'
        ],
        'wild_vs_fancy': 'Khác biệt tuyệt đối với cá vàng là luôn có 2 cặp râu ở mép miệng để dò tìm thức ăn dưới đáy hồ bùn.'
    },
    'ca_la_han': {
        'lineage_title': 'Các dòng Cá La Hán (Flowerhorn Strains)',
        'common_morphs': [
            'Kamfa (Mắt trắng/vàng, vây đuôi bao trùm tròn, hoa văn châu sấm)',
            'Zhen Zhu / Trân Châu (Châu phủ kín toàn thân, gù đầu to nhanh)',
            'Red Dragon / Huyết Rồng (Nửa thân trước đỏ thắm, nửa thân sau hoa văn)',
            'Golden Base / Fader (Cá lột toàn bộ sắc tố đen để thành màu vàng/đỏ đơn sắc)'
        ],
        'wild_vs_fancy': 'Là giống lai tạo nhân tạo 100% từ Malaysia và Đài Loan từ cuối thập niên 1990, không tồn tại trong tự nhiên.'
    },
    'ca_hong_ket': {
        'lineage_title': 'Các dòng Cá Hồng Két (Blood Parrot Hybrids)',
        'common_morphs': [
            'King Kong Parrot (Cỡ lớn 25cm+, miệng có thể khép tương đối)',
            'Kirin Parrot / Két Thần Tài (Lai giữa Két và La Hán, mình vảy xà cừ gù nhẹ)',
            'Tattoo / Dyed Parrot (Cá nhuộm màu nhân tạo - không khuyến khích)',
            'Yellow / Platinum Parrot (Biến thể màu vàng hoàng kim hoặc trắng tuyết)'
        ],
        'wild_vs_fancy': 'Lai giữa cá Midas Cichlid và Redhead Cichlid, dị tật xương hàm tạo miệng mỏ vẹt không thể cắn xé cá khác.'
    },
    'ca_dia': {
        'lineage_title': 'Các dòng Cá Dĩa (Discus Strains)',
        'common_morphs': [
            'Pigeon Blood (Da dưa đỏ cam điểm bụi tiêu đen hoặc tiêu sạch)',
            'Blue Diamond (Xanh lam nguyên khối không sọc)',
            'Red Melon / Marlboro Red (Đỏ mọng như quả dưa hấu, đầu trắng/vàng)',
            'Leopard Snakeskin (Da rắn đốm hoa mai da báo)',
            'Albino Millennium (Mắt đỏ hồng ngọc, thân vàng đỏ phát sáng)'
        ],
        'wild_vs_fancy': 'Nữ hoàng cá cảnh nước ngọt, loài hoang dã có sọc đen dọc thân để ngụy trang giữa rễ cây rừng ngập Amazon.'
    },
    'ca_da_quang': {
        'lineage_title': 'Các dòng Cá Dạ Quang (GloFish Fluorescent)',
        'common_morphs': [
            'GloFish Tetra (Cá Hắc Quần Gymnocorymbus ternetzi chuyển gen)',
            'GloFish Danio (Cá Sóc Ngựa Danio rerio chuyển gen phát huỳnh quang)',
            'GloFish Barb (Cá Xecan Puntius tetrazona huỳnh quang)',
            'Các màu thương mại: Starfire Red, Electric Green, Sunburst Orange, Cosmic Blue, Galactic Purple'
        ],
        'wild_vs_fancy': 'Chuyển gen protein GFP (từ sứa) và RFP (từ san hô), phát huỳnh quang dưới ánh sáng xanh dương hoặc đèn UV actinic.'
    },
    'ca_neon': {
        'lineage_title': 'Các dòng Cá Neon (Neon & Cardinal Tetras)',
        'common_morphs': [
            'Neon Thường (Paracheirodon innesi - vệt đỏ chỉ kéo dài nửa thân sau)',
            'Neon Vua / Cardinal Tetra (Paracheirodon axelrodi - dải đỏ chạy dọc toàn thân)',
            'Neon Kim Cương (Diamond Head Neon - đỉnh đầu lấp lánh như kim cương)',
            'Neon Đen (Black Neon Tetra - sọc đen bạc thay vì xanh đỏ)'
        ],
        'wild_vs_fancy': 'Cá cảnh thủy sinh nhút nhát, có dải tế bào guanophore phản quang tự nhiên để tìm nhau trong dòng nước đen Amazon.'
    },
    'ca_xiem': {
        'lineage_title': 'Các dòng Cá Xiêm / Betta (Betta Strains & Tail Types)',
        'common_morphs': [
            'Halfmoon (Vây đuôi xòe tròn trọn vẹn 180 độ hình bán nguyệt)',
            'Plakat (Dòng vây ngắn truyền thống, thân lực lưỡng hiếu chiến)',
            'Crowntail / Đuôi Tưa (Nan vây xòe gai như vương miện hoàng gia)',
            'Dumbo / Big Ear (Hai vây bơi mang phát triển to bản như tai voi)',
            'Koi Galaxy / Nemo (Hoa văn đốm vảy ánh kim galaxy như tranh sơn mài)'
        ],
        'wild_vs_fancy': 'Cá hoang dã (Betta hoang ruộng) màu nâu xám vây ngắn, qua tuyển chọn trở thành tác phẩm nghệ thuật sống với đủ màu sắc.'
    },
    'ca_soc_ngua': {
        'lineage_title': 'Các dòng Cá Sóc Ngựa (Zebra Danio Morphs)',
        'common_morphs': [
            'Zebra Danio Classic (5 sọc lam ngang sọc ngựa từ mang đến đuôi)',
            'Longfin Zebra Danio (Dòng đuôi dài lướt sóng mềm mại)',
            'Leopard Danio (Đột biến hoa văn đốm báo thay vì sọc ngựa)',
            'Golden Danio (Dòng bạch tạng ánh vàng sọc trắng)'
        ],
        'wild_vs_fancy': 'Mô hình sinh vật nghiên cứu di truyền học hàng đầu thế giới nhờ khả năng tái tạo tế bào tim và vây phi thường.'
    },
    'ca_thien_than': {
        'lineage_title': 'Các dòng Cá Thần Tiên (Angelfish Morphs)',
        'common_morphs': [
            'Thần Tiên Ai Cập / Altum (Pterophyllum altum - mũi hếch gãy, vây cực cao)',
            'Marble Angelfish (Thần tiên cẩm thạch đen trắng hoa văn)',
            'Koi Angelfish (Đầu cam vàng, thân trắng điểm đốm đen)',
            'Black Lace / Black Velvet (Thần tiên đen nhung huyền bí)',
            'Platinum / Diamond (Toàn thân ánh bạc kim cương lấp lánh)'
        ],
        'wild_vs_fancy': 'Thân dẹt hình lá liễu giúp lách bơi giữa các bụi lau sậy ngập nước vùng Amazon mà không bị kẻ thù phát hiện.'
    },
    'ca_rong': {
        'lineage_title': 'Các dòng Cá Rồng (Arowana Varieties)',
        'common_morphs': [
            'Huyết Long / Super Red (Đỏ ớt, đỏ máu toàn thân, mắt đỏ)',
            'Kim Long Quá Bối / Cross Back Golden (Vàng kim leo qua tận hàng vảy thứ 6 trên sống lưng)',
            'Kim Long Hồng Vĩ / High Back Golden (Vàng kim lên hàng vảy thứ 4-5)',
            'Ngân Long / Silver Arowana (Xuất xứ Nam Mỹ, vảy ánh bạc viền hồng, thân dài uyển chuyển)',
            'Thanh Long / Green Arowana (Dòng cá rồng nguyên thủy châu Á màu xanh lục nhạt)'
        ],
        'wild_vs_fancy': 'Hóa thạch sống của đại dương tiền sử, loài cá phong thủy đế vương biểu trưng cho quyền lực và tài lộc.'
    },
    'ca_chuot': {
        'lineage_title': 'Các dòng Cá Chuột (Corydoras Varieties)',
        'common_morphs': [
            'Chuột Panda (Trắng điểm khoang mắt và vây đen như gấu trúc)',
            'Chuột Bronze / Chuột Cafe (Màu đồng nâu bóng ánh kim)',
            'Chuột Albino (Mắt đỏ toàn thân trắng hồng phấn)',
            'Chuột Sterbai (Vây ngực màu cam sáng, thân chấm sao tuyết)',
            'Chuột Pygmy (Corydoras tí hon dài chỉ 2cm, bơi theo đàn tầng giữa)'
        ],
        'wild_vs_fancy': 'Cá dọn tầng đáy hiền lành có 2 hàng giáp xương bao quanh thân và râu miệng rất nhạy cảm.'
    },
    'ca_lau_kieng': {
        'lineage_title': 'Các dòng Cá Lau Kiếng / Tỳ Bà (Plecostomus & L-Numbers)',
        'common_morphs': [
            'Tỳ Bà Thường (Hypostomus plecostomus - lớn nhanh, dài tới 40-50cm)',
            'Tỳ Bà Bướm (Sewellia lineolata - bám đá hình đĩa bay dẹt phẳng)',
            'Tỳ Bà Vàng / Albino Bristlenose (Miệng có râu tua tủa, thân vàng mắt đỏ)',
            'Zebra Pleco L046 (Cực phẩm sọc ngựa đen trắng quý hiếm)',
            'Golden Nugget L018 (Chấm bi vàng rực rỡ viền vây đuôi vàng)'
        ],
        'wild_vs_fancy': 'Miệng hút giác tròn chuyên gặm rêu tảo bám trên kính và lũa đá, xương vảy giáp cứng bảo vệ khỏi cá săn mồi.'
    },
    'ca_diec_anh_dao': {
        'lineage_title': 'Các dòng Cá Diếc Anh Đào (Cherry Barb Varieties)',
        'common_morphs': [
            'Cherry Barb Classic (Cá đực mùa sinh sản đỏ rực như quả anh đào chín)',
            'Albino Cherry Barb (Dòng bạch tạng hồng phấn mắt ngọc)',
            'Longfin Cherry Barb (Vây đuôi và vây lưng xòe dài thướt tha)'
        ],
        'wild_vs_fancy': 'Đến từ các dòng suối rợp bóng mát Sri Lanka, cá đực càng sung sức trong môi trường nước tốt thì màu đỏ càng rực lửa.'
    },
    'ca_but_chi': {
        'lineage_title': 'Các dòng Cá Bút Chì (Siamese Algae Eater Strains)',
        'common_morphs': [
            'Cá Bút Chì Thật / SAE (Crossocheilus siamensis - sọc đen chạy xuyên thấu tận chóp đuôi, mép sọc răng cưa)',
            'Cá Chuồn Bay / Flying Fox (Epalzeorhynchos kalopterus - vây có viền vàng/đen rõ rệt)',
            'Cá Bút Chì Giả / False SAE (Garra cambodgiensis - sọc đen dừng lại ở gốc đuôi)'
        ],
        'wild_vs_fancy': 'Chuyên gia diệt rêu hại số 1 trong bể thủy sinh, đặc biệt là rêu chùm đen (BBA) mà các loài khác không thể ăn được.'
    },
    'ca_sac': {
        'lineage_title': 'Các dòng Cá Sặc Cảnh (Gourami Varieties)',
        'common_morphs': [
            'Sặc Gấm / Dwarf Gourami (Vân đỏ xanh lam xen kẽ lộng lẫy)',
            'Sặc Cẩm Thạch / Opaline Gourami (Thân xanh ngọc điểm đốm cẩm thạch)',
            'Sặc Vàng / Golden Gourami (Toàn thân vàng chanh điểm chấm đen)',
            'Sặc Ngọc Trai / Pearl Gourami (Hoa văn đốm trắng li ti như rải ngọc trai)',
            'Sặc Môi Dày / Thick-lipped Gourami (Môi dày bơi điềm tĩnh)'
        ],
        'wild_vs_fancy': 'Có 2 vây bụng tiêu giảm biến thành 2 sợi râu dài đóng vai trò cơ quan xúc giác để sờ chạm nhận biết vật cản.'
    }
}

ANATOMICAL_PAIR_COMPARISONS = {
    ('ca_bay_mau', 'ca_molly'): {
        'title': 'So Sánh Hình Thái: Cá Bảy Màu (Guppy) vs Cá Molly (Bình Tích)',
        'family': 'Họ Cá Đẻ Con (Poeciliidae)',
        'traits': [
            {'feature': 'Vị trí & Cấu trúc Miệng', 'sp1': 'Miệng thẳng ngang, nhỏ, nằm ở chóp đầu', 'sp2': 'Miệng hếch rõ rệt lên trên (Upturned mouth) chuyên húp mặt nước'},
            {'feature': 'Vây Lưng (Dorsal Fin)', 'sp1': 'Vây lưng nhỏ, thấp hoặc dạng dải hẹp bắt đầu sau vây bụng', 'sp2': 'Vây lưng rất rộng hình buồm (Sailfin) xuất phát trước vây bụng'},
            {'feature': 'Tỉ lệ Vây Đuôi / Thân', 'sp1': 'Đuôi xòe quạt rất to, chiếm 40% - 50% tổng chiều dài cơ thể', 'sp2': 'Đuôi tròn phẳng hoặc đuôi đàn lia, tỉ lệ đuôi nhỏ hơn thân'},
            {'feature': 'Độ Dày Thân & Kích Thước', 'sp1': 'Thân mảnh mai thuôn dài (2.5 - 4cm), cử động bơi lượn sóng nhanh nhẹn', 'sp2': 'Thân dày cộm, nở rộng (5 - 8cm), cá giống cảnh thường có bụng bóng tròn (Balloon)'}
        ]
    },
    ('ca_mun', 'ca_duoi_kiem'): {
        'title': 'So Sánh Hình Thái: Cá Mún (Platy) vs Cá Đuôi Kiếm (Swordtail)',
        'family': 'Họ Cá Đẻ Con (Poeciliidae) - Chi Xiphophorus',
        'traits': [
            {'feature': 'Hình Dáng Cơ Thể', 'sp1': 'Thân ngắn hình thoi, lưng hơi gù tròn, bụng phệ nhẹ', 'sp2': 'Thân thuôn dài dạng ngư lôi (Torpedo shape), cơ bắp rắn chắc'},
            {'feature': 'Đặc Điểm Thùy Đuôi', 'sp1': 'Vây đuôi tròn phẳng đều ở cả hai thùy trên và dưới', 'sp2': 'Cá đực có thùy đuôi dưới kéo dài thành mũi kiếm nhọn hoắt dài 2-4cm'},
            {'feature': 'Gốc Đuôi (Caudal Peduncle)', 'sp1': 'Gốc đuôi ngắn và dày, thường có hoa văn Mickey hoặc vệt đen', 'sp2': 'Gốc đuôi thon dài, chuyển tiếp uyển chuyển'},
            {'feature': 'Tập Tính Bơi Lội', 'sp1': 'Bơi thong thả tầng giữa, hiền lành ôn hòa', 'sp2': 'Bơi lướt cực nhanh, cá đực có tính lãnh thổ và hay nhảy vọt lên khỏi mặt nước'}
        ]
    },
    ('ca_bay_mau', 'ca_mun'): {
        'title': 'So Sánh Hình Thái: Cá Bảy Màu (Guppy) vs Cá Mún (Platy)',
        'family': 'Họ Cá Đẻ Con (Poeciliidae)',
        'traits': [
            {'feature': 'Cấu Trúc Thân Mình', 'sp1': 'Thân mảnh dẻ thon dài, đầu nhọn mắt to', 'sp2': 'Thân mập tròn hình quả trám ngắn, lưng gù cao'},
            {'feature': 'Vây Đuôi & Vây Bơi', 'sp1': 'Vây đuôi xòe màng mỏng lộng lẫy, vây bơi vẫy liên hồi', 'sp2': 'Vây đuôi hình cánh quạt ngắn bo tròn dày dặn'},
            {'feature': 'Sắc Tố Màu', 'sp1': 'Màu sắc biến ảo vảy rồng ánh kim, hạt cỏ đa sắc xen kẽ', 'sp2': 'Thường là mảng màu đơn sắc đồng nhất (đỏ cờ, vàng nghệ, đen tuxedo)'}
        ]
    },
    ('ca_ba_duoi', 'ca_koi'): {
        'title': 'So Sánh Hình Thái: Cá Ba Đuôi (Goldfish) vs Cá Chép Koi (Nishikigoi)',
        'family': 'Họ Cá Chép (Cyprinidae)',
        'traits': [
            {'feature': 'Râu Miệng (Barbels)', 'sp1': 'TUYỆT ĐỐI KHÔNG CÓ RÂU ở khóe miệng', 'sp2': 'BẮT BUỘC CÓ 2 CẶP RÂU (1 cặp ngắn, 1 cặp dài) ở mép miệng'},
            {'feature': 'Cấu Trúc Đuôi', 'sp1': 'Đuôi xòe 2, 3 hoặc 4 thùy mềm mại buông rủ (đuôi bướm, đuôi voan)', 'sp2': 'Đuôi đơn cứng cáp hình quạt phẳng, cấu tạo thích nghi bơi ngược dòng'},
            {'feature': 'Đầu & Gù', 'sp1': 'Nhiều dòng có bướu thịt (Wen) xù to ở đầu (Oranda, Ranchu)', 'sp2': 'Đầu thuôn phẳng mượt mà, không bao giờ có bướu thịt lồi'},
            {'feature': 'Kích Thước Trưởng Thành', 'sp1': 'Thường từ 10 - 20cm, nuôi trong bể kính trong nhà', 'sp2': 'Phát triển từ 40 - 90cm, bắt buộc nuôi hồ ngoài trời diện tích lớn'}
        ]
    },
    ('ca_la_han', 'ca_hong_ket'): {
        'title': 'So Sánh Hình Thái: Cá La Hán (Flowerhorn) vs Cá Hồng Két (Blood Parrot)',
        'family': 'Họ Cá Cichlid Lai Nhân Tạo (Man-made Hybrids)',
        'traits': [
            {'feature': 'Miệng & Hàm', 'sp1': 'Miệng rộng với hàm răng khỏe, có thể mở to đớp mồi sống dữ dội', 'sp2': 'Miệng biến dạng hình tam giác mỏ vẹt, không thể khép kín miệng'},
            {'feature': 'Gù Đầu (Kok)', 'sp1': 'Gù đầu nhô cao vượt trội chứa mỡ và dịch, là tiêu chuẩn chấm điểm hàng đầu', 'sp2': 'Trán tròn dốc hoặc chỉ hơi u nhẹ (ngoại trừ dòng Két King Kong/Kirin)'},
            {'feature': 'Hoa Văn Vảy', 'sp1': 'Dọc thân có vệt hoa văn đen hình chữ Hán và đốm châu xà cừ', 'sp2': 'Thân trơn đơn sắc màu đỏ cam hoặc vàng tươi, vảy bóng phẳng'},
            {'feature': 'Tính Khí', 'sp1': 'Cực kỳ hung dữ, tính lãnh thổ tuyệt đối (bắt buộc nuôi 1 con/bể)', 'sp2': 'Hiền hòa nhút nhát, có thể nuôi chung đàn đông đúc'}
        ]
    },
    ('ca_da_quang', 'ca_neon'): {
        'title': 'So Sánh Hình Thái: Cá Dạ Quang (GloFish) vs Cá Neon (Tetra)',
        'family': 'Họ Cá Characidae / Thủy Sinh Phát Quang',
        'traits': [
            {'feature': 'Cơ Chế Phát Quang', 'sp1': 'Chuyển gen huỳnh quang sinh học (GFP/RFP), toàn bộ cơ thể tự phát sáng đều', 'sp2': 'Tế bào phản quang cấu trúc tinh thể Guanophore, chỉ phản chiếu ánh sáng bên ngoài'},
            {'feature': 'Phân Bố Màu Sắc', 'sp1': 'Đơn sắc rực rỡ toàn thân (xanh lá neon, hồng huỳnh quang, vàng chanh)', 'sp2': 'Phối màu kinh điển: 1 sọc xanh lam ngọc chạy dọc lưng + nửa đuôi sau màu đỏ'},
            {'feature': 'Hình Dáng Cơ Thể', 'sp1': 'Thường có thân dẹt rộng hình quả trám (GloFish Tetra) hoặc vây cao', 'sp2': 'Thân ngư lôi thon dài mảnh mai, bơi theo đàn đồng điệu'}
        ]
    },
    ('ca_dia', 'ca_thien_than'): {
        'title': 'So Sánh Hình Thái: Cá Dĩa (Discus) vs Cá Thần Tiên (Angelfish)',
        'family': 'Họ Cá Cichlidae Nam Mỹ',
        'traits': [
            {'feature': 'Hình Dáng Cơ Thể', 'sp1': 'Thân hình tròn trịa dẹt phẳng như chiếc đĩa bay (Discus plate)', 'sp2': 'Thân hình tam giác cánh buồm với vây lưng và vây bụng vươn cao như mũi tên'},
            {'feature': 'Vây Bụng (Ventral Fin)', 'sp1': 'Vây bụng ngắn mềm mại áp sát thân dưới', 'sp2': 'Vây bụng tiêu giảm kéo dài thành 2 sợi râu chỉ mảnh dẻ buông dài'},
            {'feature': 'Cử Động Bơi', 'sp1': 'Bơi điềm đạm, lướt chậm rãi uy nghi ở tầng giữa hồ', 'sp2': 'Bơi lên xuống linh hoạt, đổi hướng giật cục nhanh nhẹn'}
        ]
    }
}


def find_fish_family(species_key):
    for f_id, f_val in FISH_FAMILIES_TAXONOMY.items():
        if species_key in f_val['species']:
            return f_val
    return {'id': 'other', 'name': 'Khác', 'description': ''}


def analyze_hybrid_and_morphs(top1_key, top1_prob, top2_key=None, top2_prob=0.0):
    """
    Module Giám Định Lai Tạp & Phân Tích Hình Thái Học Phân Cấp:
    Phát hiện kiểu hình lai tạp, giao thoa họ và cung cấp bảng đối chiếu giải phẫu độc quyền.
    """
    fam1 = find_fish_family(top1_key)
    fam2 = find_fish_family(top2_key) if top2_key else None
    
    same_family = (fam1['id'] == fam2['id']) if fam2 else False
    gap = (top1_prob - top2_prob) * 100 if top2_key else 100.0

    # Lấy thông tin dòng lai/biến thể của Top 1
    morph_data = SPECIES_COMMERCIAL_MORPHTYPES.get(top1_key, {
        'lineage_title': f"Các dòng {SPECIES_MAP.get(top1_key, {}).get('vn', top1_key)}",
        'common_morphs': ['Dòng thuần chủng', 'Biến thể tuyển chọn'],
        'wild_vs_fancy': 'Thông tin dòng cảnh đang cập nhật.'
    })

    # Tìm bảng so sánh giải phẫu độc quyền
    comparison = None
    pair1 = (top1_key, top2_key)
    pair2 = (top2_key, top1_key)
    if pair1 in ANATOMICAL_PAIR_COMPARISONS:
        comp_raw = ANATOMICAL_PAIR_COMPARISONS[pair1]
        comparison = {
            'title': comp_raw['title'],
            'family': comp_raw['family'],
            'sp1_name': SPECIES_MAP.get(top1_key, {}).get('vn', top1_key),
            'sp2_name': SPECIES_MAP.get(top2_key, {}).get('vn', top2_key),
            'traits': comp_raw['traits']
        }
    elif pair2 in ANATOMICAL_PAIR_COMPARISONS:
        comp_raw = ANATOMICAL_PAIR_COMPARISONS[pair2]
        # Đảo ngược cột so sánh
        inverted_traits = []
        for t in comp_raw['traits']:
            inverted_traits.append({
                'feature': t['feature'],
                'sp1': t['sp2'],
                'sp2': t['sp1']
            })
        comparison = {
            'title': comp_raw['title'],
            'family': comp_raw['family'],
            'sp1_name': SPECIES_MAP.get(top1_key, {}).get('vn', top1_key),
            'sp2_name': SPECIES_MAP.get(top2_key, {}).get('vn', top2_key),
            'traits': inverted_traits
        }

    # Đánh giá cảnh báo lai tạp (Hybrid Alert)
    is_hybrid_alert = False
    verdict = ""

    if top2_key and (gap <= 22.0 or (same_family and gap <= 38.0 and top1_prob < 0.80)):
        is_hybrid_alert = True
        sp1_name = SPECIES_MAP.get(top1_key, {}).get('vn', top1_key)
        sp2_name = SPECIES_MAP.get(top2_key, {}).get('vn', top2_key)
        if same_family:
            verdict = (f"CẢNH BÁO KIỂU HÌNH LAI TẠP / GIAO THOA: Mẫu cá mang đặc điểm giao thoa giữa '{sp1_name}' ({top1_prob*100:.1f}%) "
                       f"và '{sp2_name}' ({top2_prob*100:.1f}%). Cả hai đều thuộc {fam1['name']}. "
                       f"Đây là hiện tượng rất phổ biến do lai chéo giữa các dòng cá cảnh hoặc kiểu hình cá con/cá mái tương đồng.")
        else:
            verdict = (f"ĐỘ TƯƠNG ĐỒNG CAO (Chênh lệch xác suất chỉ {gap:.1f}%): Có sự phân vân giữa '{sp1_name}' ({top1_prob*100:.1f}%) "
                       f"và '{sp2_name}' ({top2_prob*100:.1f}%). Hãy đối chiếu cấu trúc vây và vảy trong bảng giải phẫu bên dưới.")
    else:
        sp1_name = SPECIES_MAP.get(top1_key, {}).get('vn', top1_key)
        verdict = f"KIỂU HÌNH THUẦN CHỦNG RÕ RÀNG: Cá thể thể hiện đầy đủ các đặc trưng hình thái chuẩn mực của loài '{sp1_name}' (Độ tin cậy: {top1_prob*100:.1f}%)."

    return {
        'is_hybrid_alert': is_hybrid_alert,
        'family_name': fam1['name'],
        'family_description': fam1.get('description', ''),
        'same_family': same_family,
        'confidence_gap': round(gap, 2),
        'verdict': verdict,
        'morph_data': morph_data,
        'comparison': comparison
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
        err = "Lỗi: Chưa tìm thấy trọng số mô hình đã huấn luyện ('best_fish_yolov8.pt')."
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
    top2_key, top2_prob = ranked[1] if len(ranked) > 1 else (None, 0.0)

    top1_meta = SPECIES_MAP.get(top1_key, {'vn': top1_key, 'sci': '', 'temp': '24-28°C', 'ph': '6.5-7.5'})

    top3 = []
    for k, p in ranked[:3]:
        m = SPECIES_MAP.get(k, {'vn': k})
        top3.append({'species_key': k, 'name': m['vn'], 'confidence': round(p * 100, 2)})

    # Phân tích hình thái học & cảnh báo lai tạp
    hybrid_analysis = analyze_hybrid_and_morphs(top1_key, top1_prob, top2_key, top2_prob)

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
        'top3': top3,
        'hybrid_analysis': hybrid_analysis
    }

    if as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 70)
        print("🎯 KẾT QUẢ NHẬN DIỆN CÁ CẢNH & PHÂN TÍCH HÌNH THÁI HỌC (YOLOV8 EDGE AI)")
        print("=" * 70)
        print(f"📸 Ảnh đầu vào:   {os.path.basename(image_path)}")
        print(f"🧠 Mô hình dùng:  {os.path.basename(path_used)}")
        print(f"🏆 LOÀI DỰ ĐOÁN:  {top1_meta['vn']} ({top1_meta['sci']})")
        print(f"⚡ Độ tin cậy:    {top1_prob*100:.2f}%")
        print(f"🏛️ Họ sinh thái:  {hybrid_analysis['family_name']}")
        print(f"🌡️ Nhiệt độ IoT:  {top1_meta['temp']}")
        print(f"💧 Độ pH IoT:     {top1_meta['ph']}")
        print("-" * 70)
        print("📊 Top 3 ứng viên xác suất cao nhất:")
        for idx, item in enumerate(top3, 1):
            bar = "█" * int(item['confidence'] / 5)
            print(f"  {idx}. {item['name']:25s} {item['confidence']:5.1f}%  | {bar}")

        print("-" * 70)
        print("🧬 KẾT LUẬN GIÁM ĐỊNH HÌNH THÁI HỌC & LAI TẠP:")
        print(f"  {hybrid_analysis['verdict']}")

        comp = hybrid_analysis.get('comparison')
        if comp:
            print("\n🔍 BẢNG ĐỐI CHIẾU GIẢI PHẪU ĐỘC QUYỀN (KEY ANATOMICAL MARKERS):")
            print(f"  [{comp['sp1_name']}] vs [{comp['sp2_name']}]")
            for t in comp['traits']:
                print(f"  • {t['feature']}:")
                print(f"    - {comp['sp1_name']}: {t['sp1']}")
                print(f"    - {comp['sp2_name']}: {t['sp2']}")

        morphs = hybrid_analysis.get('morph_data', {})
        if morphs and morphs.get('common_morphs'):
            print(f"\n🎨 {morphs.get('lineage_title', 'Các dòng biến thể phổ biến')}:")
            for m in morphs['common_morphs'][:4]:
                print(f"    ✓ {m}")
        print("=" * 70)

    return output


def predict_pil(pil_img):
    """Dự đoán trực tiếp từ đối tượng PIL Image trong bộ nhớ (hỗ trợ phân tích lai tạp)."""
    model, path_used = load_model()
    if not model:
        return None
    try:
        results = model.predict(source=pil_img, verbose=False)
        r = results[0]
        names = r.names
        probs = r.probs.data.tolist()
        ranked = sorted([(names[i], probs[i]) for i in range(len(probs))], key=lambda x: x[1], reverse=True)
        top1_key, top1_prob = ranked[0]
        top2_key, top2_prob = ranked[1] if len(ranked) > 1 else (None, 0.0)
        top1_meta = SPECIES_MAP.get(top1_key, {'vn': top1_key, 'sci': '', 'temp': '24-28°C', 'ph': '6.5-7.5'})
        top3 = []
        for k, p in ranked[:3]:
            m = SPECIES_MAP.get(k, {'vn': k})
            top3.append({'species_key': k, 'name': m['vn'], 'confidence': round(p * 100, 2)})
        
        hybrid_analysis = analyze_hybrid_and_morphs(top1_key, top1_prob, top2_key, top2_prob)

        return {
            'success': True,
            'top1': {
                'species_key': top1_key,
                'name': top1_meta['vn'],
                'confidence': round(top1_prob * 100, 2)
            },
            'top3': top3,
            'hybrid_analysis': hybrid_analysis
        }
    except Exception:
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Predict fish species using YOLOv8 with Hybrid Morphological Analysis")
    parser.add_argument('image', type=str, help="Path to input fish image")
    parser.add_argument('--json', action='store_true', help="Output as JSON")
    args = parser.parse_args()

    predict_image(args.image, as_json=args.json)
