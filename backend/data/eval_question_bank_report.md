# Báo cáo đánh giá chatbot — Bảng câu hỏi nông sản

- Thời điểm: 2026-08-16T19:41:22.239765
- Số câu: **120**
- Điểm TB: **96.32/100**
- Phân bố grade: `{'A': 109, 'B': 8, 'C': 2, 'D': 1}`
- Intent accuracy: **99.2%**
- Tỷ lệ trả về sản phẩm: **57.5%**
- Category match (khi có SP): **98.2%**
- Price match package (khi có SP+điều kiện giá): **100.0%**
- Trả lời phủ nhận dù có SP: **2**
- Honest empty (catalog xác nhận): **48**
- Latency TB: **6478 ms**

## Theo danh mục

| Category | N | Avg score | Product return |
|---|---:|---:|---:|
| cà phê | 37 | 99.3 | 92% |
| (none) | 20 | 88.8 | 65% |
| gạo | 12 | 97.7 | 25% |
| trà | 11 | 99.0 | 73% |
| hạt | 10 | 99.8 | 90% |
| đậu | 10 | 95.4 | 0% |
| trái cây | 8 | 96.2 | 0% |
| rau củ | 6 | 95.7 | 0% |
| nông sản chế biến | 6 | 92.0 | 33% |

## Top 10 tốt nhất

- **Q001** (A/100): Có cà phê nào từ 100.000 đến 200.000 đồng/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q002** (A/100): Có cà phê nào dưới 150k/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q003** (A/100): Có cà phê nào không quá 200.000/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q004** (A/100): Có cà phê nào dưới 200.000 đồng/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q009** (A/100): Có trà nào từ 100.000 đến 200.000 đồng/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q011** (A/100): Có trà nào dưới 200.000 đồng/kg không? → 1 SP, intent=PRODUCT_SEARCH
- **Q013** (A/100): Có hạt nào không quá 200.000/kg không? → 2 SP, intent=PRODUCT_SEARCH
- **Q014** (A/100): Có hạt nào dưới 200.000 đồng/kg không? → 2 SP, intent=PRODUCT_SEARCH
- **Q016** (A/100): Có hạt nào giá dưới 100k không? → 1 SP, intent=PRODUCT_SEARCH
- **Q033** (A/100): Sản phẩm cà phê nào dưới 200k? → 5 SP, intent=PRODUCT_SEARCH

## 15 case yếu nhất

- **Q102** (D/41): Bột ngũ cốc dùng để làm gì? | 
- **Q094** (C/61): Cho tôi thông tin về gạo ST25. | 
- **Q095** (C/61): Gạo ST25 có đặc điểm gì? | 
- **Q084** (B/80): Tôi cần nguyên liệu nông sản để làm bánh. | category_mismatch: ['Trà sen Tây Hồ 300g', 'Mắc khén Tây Bắc 1000g', 'Hạt óc chó 500g']
- **Q086** (B/80): Có cà phê pha espresso nào dưới 200 nghìn không? | answer_denies_despite_products
- **Q092** (B/80): Nguyên liệu làm bánh dưới 100 nghìn/kg có loại nào? | category_mismatch: ['Mắc khén Tây Bắc 1000g', 'Bộ quà Cà phê Premium 1200g']
- **Q097** (B/80): Có thông tin gì về cà phê Robusta nhân? | answer_denies_despite_products
- **Q057** (B/83): Cho tôi xem các sản phẩm có nguồn gốc Sóc Trăng. | honest_empty_catalog_verified
- **Q058** (B/83): Tôi muốn tìm nông sản Đồng Tháp. | honest_empty_catalog_verified
- **Q059** (B/83): Có sản phẩm nào đến từ An Giang? | honest_empty_catalog_verified
- **Q062** (B/83): Có nông sản nào của Bình Thuận không? | honest_empty_catalog_verified
- **Q078** (A/91): Có loại đậu nào phù hợp làm bánh? | honest_empty_catalog_verified
- **Q079** (A/91): Tôi cần đậu để nấu chè. | honest_empty_catalog_verified
- **Q082** (A/91): Có trái cây nào phù hợp làm nước ép? | honest_empty_catalog_verified
- **Q083** (A/91): Tìm rau củ phù hợp để nấu ăn. | honest_empty_catalog_verified

## Lưu ý đánh giá

- Câu hỏi có tín hiệu /kg được chấm theo price_per_kg khi card có trường này.
- Category match dùng category_name trên card hoặc token trên tên — không hardcode question id.
- Empty được cộng điểm đầy đủ chỉ khi probe catalog độc lập cũng không có hàng khớp (honest_empty).

Chi tiết JSON: `backend\data\eval_question_bank_report.json`