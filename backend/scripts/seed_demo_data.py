"""Seed comprehensive demo data for LifeGift Agricultural Chatbot."""

import json
import logging
from sqlalchemy import text
from backend.app.core.database import get_db_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORIES = [
    {"id": 1, "name": "Cà phê", "slug": "ca-phe", "status": "ACTIVE"},
    {"id": 2, "name": "Trà & Thảo mộc", "slug": "tra-thao-moc", "status": "ACTIVE"},
    {"id": 3, "name": "Mật ong tự nhiên", "slug": "mat-ong-tu-nhien", "status": "ACTIVE"},
    {"id": 4, "name": "Hạt dinh dưỡng", "slug": "hat-dinh-duong", "status": "ACTIVE"},
    {"id": 5, "name": "Nông sản sấy", "slug": "nong-san-say", "status": "ACTIVE"},
    {"id": 6, "name": "Hộp quà tặng", "slug": "hop-qua-tang", "status": "ACTIVE"},
]

BRANDS = [
    {"id": 1, "name": "Cầu Đất Farm", "status": "ACTIVE"},
    {"id": 2, "name": "Tây Nguyên Origin", "status": "ACTIVE"},
    {"id": 3, "name": "Hà Giang EcoTea", "status": "ACTIVE"},
    {"id": 4, "name": "Bảo Lộc Premium", "status": "ACTIVE"},
    {"id": 5, "name": "Mật Ong Rừng U Minh", "status": "ACTIVE"},
    {"id": 6, "name": "Bình Phước Cashew", "status": "ACTIVE"},
    {"id": 7, "name": "LifeGift Special", "status": "ACTIVE"},
]

PRODUCTS = [
    # 1. Coffee
    {
        "id": 1,
        "category_id": 1,
        "brand_id": 1,
        "name": "Cà phê Arabica Cầu Đất 500g",
        "slug": "ca-phe-arabica-cau-dat-500g",
        "description": "Cà phê Arabica Cầu Đất thượng hạng với hương thơm thanh tao, vị chua dịu nhẹ và hậu vị ngọt sâu.",
        "price": 260000.0,
        "sale_price": 239000.0,
        "origin": "Cầu Đất - Đà Lạt",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500",
        "stock": 85,
        "details": {
            "ingredients": "100% hạt cà phê Arabica Cầu Đất chọn lọc chín cây",
            "taste_profile": "Thơm nhẹ, hương hoa quả, acidity chua thanh dịu, ít đắng, hậu vị ngọt sâu cân bằng",
            "key_benefits": "Giúp tỉnh táo tự nhiên, giàu chất chống oxy hóa, tốt cho tim mạch khi dùng lượng vừa phải",
            "suitable_for": "Người thích gu cà phê thanh nhẹ, thơm thanh tao, uống buổi sáng hoặc làm việc văn phòng",
            "usage_instructions": "Thích hợp pha Pour Over (V60, Chemex), Espresso máy hoặc Cold Brew",
            "storage_instructions": "Bảo quản nơi khô ráo thoáng mát, đậy kín sau khi mở túi, tránh ánh nắng trực tiếp",
            "shelf_life": "12 tháng kể từ ngày sản xuất",
            "producer_name": "HTX Nông Sản Cầu Đất Farm",
            "production_area": "Cầu Đất, TP. Đà Lạt, Lâm Đồng (độ cao 1.500m)",
            "product_story": "Được canh tác ở độ cao trên 1500m nơi sương mù bao phủ quanh năm, từng hạt Arabica Cầu Đất hấp thụ tinh hoa đất trời để mang đến hương vị chuẩn mực quốc tế.",
            "extra_attributes": {"roast_level": "medium", "bitterness": "low", "acidity": "medium", "brewing_methods": ["pour_over", "espresso", "cold_brew"]}
        }
    },
    {
        "id": 2,
        "category_id": 1,
        "brand_id": 2,
        "name": "Cà phê Robusta Buôn Ma Thuột Nguyên Hạt 500g",
        "slug": "ca-phe-robusta-buon-ma-thuot-500g",
        "description": "Robusta Buôn Ma Thuột rang mộc đậm đà, vị đắng đậm truyền thống, thể chất dày dặn cho người thích gu mạnh.",
        "price": 195000.0,
        "sale_price": 180000.0,
        "origin": "Buôn Ma Thuột - Đắk Lắk",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500",
        "stock": 120,
        "details": {
            "ingredients": "100% hạt cà phê Robusta sẻ Buôn Ma Thuột chế biến ướt",
            "taste_profile": "Đắng đậm đà, hương chocolate đen, hạnh nhân nướng, thể chất dày (full body)",
            "key_benefits": "Hàm lượng caffeine cao giúp tăng cường tập trung tối đa, nạp năng lượng nhanh",
            "suitable_for": "Người thích cà phê đậm truyền thống, pha phin Việt Nam, cà phê sữa đá đậm đà",
            "usage_instructions": "Pha phin truyền thống hoặc pha máy espresso đậm",
            "storage_instructions": "Để nơi thoáng mát, khô ráo, tránh mùi lạ",
            "shelf_life": "12 tháng",
            "producer_name": "Công ty Nông Sản Tây Nguyên Origin",
            "production_area": "Cư M'gar, Buôn Ma Thuột, Đắk Lắk",
            "product_story": "Buôn Ma Thuột được mệnh danh là thủ phủ cà phê của Việt Nam. Hạt Robusta hạt sẻ được chọn lọc kỹ càng, lên men bán ướt giữ trọn vị đắng thuần khiết.",
            "extra_attributes": {"roast_level": "dark", "bitterness": "high", "acidity": "low", "brewing_methods": ["phin", "espresso"]}
        }
    },
    {
        "id": 3,
        "category_id": 1,
        "brand_id": 2,
        "name": "Cà phê Phin Blend Hảo Hạng 500g",
        "slug": "ca-phe-phin-blend-hao-hang-500g",
        "description": "Sự kết hợp hoàn hảo giữa 70% Robusta đậm đà và 30% Arabica thơm ngát, chuyên biệt cho pha phin Việt Nam.",
        "price": 220000.0,
        "sale_price": None,
        "origin": "Lâm Đồng & Đắk Lắk",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1587080413959-06b859fb107d?w=500",
        "stock": 50,
        "details": {
            "ingredients": "70% Robusta Buôn Ma Thuột, 30% Arabica Cầu Đất",
            "taste_profile": "Đậm đà hài hòa, thơm nồng nàn, đắng vừa phải, hậu vị êm dịu kéo dài",
            "key_benefits": "Tạo năng lượng sảng khoái mỗi sáng, cân bằng hoàn hảo giữa vị đậm và hương thơm",
            "suitable_for": "Gia đình và văn phòng yêu thích cà phê phin sữa đá, cà phê đen đá truyền thống",
            "usage_instructions": "Dùng 20-25g bột cho vào phin nhôm/inox, ủ nước sôi 92 độ C trong 2 phút rồi châm thêm nước",
            "storage_instructions": "Bảo quản nơi khô ráo, đậy kín sau khi sử dụng",
            "shelf_life": "12 tháng",
            "producer_name": "Tây Nguyên Origin",
            "production_area": "Tây Nguyên, Việt Nam",
            "product_story": "Bản phối hòa quyện giữa vị mạnh mẽ của Robusta và nét hương hoa thanh tao của Arabica.",
            "extra_attributes": {"roast_level": "medium_dark", "bitterness": "medium", "acidity": "low", "brewing_methods": ["phin"]}
        }
    },
    {
        "id": 4,
        "category_id": 1,
        "brand_id": 1,
        "name": "Cà phê Specialty Typica Cầu Đất 250g",
        "slug": "ca-phe-specialty-typica-cau-dat-250g",
        "description": "Giống Typica cổ thụ quý hiếm, hương hoa nhài và vị ngọt mật ong tự nhiên, điểm cupping SCA trên 85.",
        "price": 380000.0,
        "sale_price": 350000.0,
        "origin": "Cầu Đất - Đà Lạt",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1511920170033-f8396924c348?w=500",
        "stock": 15,
        "details": {
            "ingredients": "100% hạt cà phê Typica cổ thuần chủng tuyển chọn",
            "taste_profile": "Hương hoa cam, hoa nhài, vị ngọt mật ong, acid trái cây phức hợp, cực kỳ tinh tế",
            "key_benefits": "Thưởng thức nghệ thuật cà phê specialty đỉnh cao, độ sạch và phẩm chất thượng lưu",
            "suitable_for": "Người sành cà phê, chuyên gia thẩm vị, làm quà tặng đối tác cao cấp",
            "usage_instructions": "Pha thủ công Pour Over V60, Kalita Wave, Aeropress với tỉ lệ 1:15",
            "storage_instructions": "Bảo quản hộp van 1 chiều, tránh nhiệt độ cao",
            "shelf_life": "6 tháng để hương vị tươi ngon nhất",
            "producer_name": "Cầu Đất Farm Specialty Reserve",
            "production_area": "Đồi Cầu Đất, Đà Lạt",
            "product_story": "Những cây giống Typica từ thời Pháp được gìn giữ qua nhiều thế hệ, hái chín 100% thủ công.",
            "extra_attributes": {"roast_level": "light", "bitterness": "very_low", "acidity": "high", "brewing_methods": ["pour_over", "aeropress"]}
        }
    },

    # 2. Tea & Herbal
    {
        "id": 5,
        "category_id": 2,
        "brand_id": 3,
        "name": "Trà Shan Tuyết Cổ Thụ Hà Giang 100g",
        "slug": "tra-shan-tuyet-co-thu-ha-giang-100g",
        "description": "Búp chè Shan Tuyết 1 tôm 2 lá thu hái từ cây chè cổ thụ trên 300 năm tuổi tại đỉnh Tây Côn Lĩnh.",
        "price": 320000.0,
        "sale_price": 290000.0,
        "origin": "Tây Côn Lĩnh - Hà Giang",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500",
        "stock": 60,
        "details": {
            "ingredients": "100% búp chè Shan Tuyết cổ thụ tự nhiên phủ lớp lông tuyết trắng",
            "taste_profile": "Hương khói bếp bảng lảng, mật ong rừng, vị chát thanh dịu, hậu ngọt kéo dài sâu trong cổ họng",
            "key_benefits": "Thanh lọc cơ thể, hỗ trợ tiêu hóa, giảm căng thẳng, chống lão hóa mạnh mẽ",
            "suitable_for": "Người yêu trà đạo, thư giãn sau giờ làm việc, quà biếu người lớn tuổi",
            "usage_instructions": "Pha với nước sôi khoảng 85-90 độ C, hãm trà 30-45 giây cho mỗi lần nước (uống được 6-8 nước)",
            "storage_instructions": "Đựng trong hộp kín khí, để nơi râm mát, tránh ánh sáng trực tiếp",
            "shelf_life": "24 tháng",
            "producer_name": "HTX Chè Cổ Thụ Tây Côn Lĩnh",
            "production_area": "Hoàng Su Phì, Tây Côn Lĩnh, Hà Giang (độ cao trên 2.000m)",
            "product_story": "Những cây trà cổ thụ hàng trăm năm tuổi sinh trưởng tự nhiên trong sương mù tuyết lạnh, rễ đâm sâu vào lòng núi đá hút tinh túy của đất trời.",
            "extra_attributes": {"tea_type": "shan_tuyet", "fermentation": "none", "brewing_temp": "85-90C"}
        }
    },
    {
        "id": 6,
        "category_id": 2,
        "brand_id": 4,
        "name": "Trà Oolong Tứ Quý Bảo Lộc 250g",
        "slug": "tra-oolong-tu-quy-bao-loc-250g",
        "description": "Trà Oolong cao cấp Bảo Lộc viên tròn đều, nước vàng óng, hương thơm hoa mộc lan lan tỏa quyến rũ.",
        "price": 280000.0,
        "sale_price": 260000.0,
        "origin": "Bảo Lộc - Lâm Đồng",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1597481499750-3e6b22637e12?w=500",
        "stock": 70,
        "details": {
            "ingredients": "100% búp trà Oolong giống Đài Loan trồng tại vùng cao Bảo Lộc",
            "taste_profile": "Hương hoa mộc lan nồng nàn, vị chát rất nhẹ, ngọt hậu mượt mà nơi cuống họng",
            "key_benefits": "Giúp hỗ trợ giảm cân, đào thải mỡ thừa, làm đẹp da, tạo cảm giác thư thái",
            "suitable_for": "Phụ nữ, nhân viên văn phòng, người thích hương hoa tự nhiên thanh tao",
            "usage_instructions": "Nước sôi 95 độ C, hãm trong ấm tử sa hoặc ấm thủy tinh 40 giây",
            "storage_instructions": "Bảo quản nơi khô ráo, tránh xa các gia vị có mùi mạnh",
            "shelf_life": "18 tháng",
            "producer_name": "Bảo Lộc Premium Tea Co.",
            "production_area": "Bảo Lộc, Lâm Đồng",
            "product_story": "Quy trình chế biến bán lên men công nghệ Đài Loan kết hợp đất bazan Bảo Lộc tạo nên vị trà tròn trịa.",
            "extra_attributes": {"tea_type": "oolong", "fermentation": "semi-fermented", "brewing_temp": "90-95C"}
        }
    },
    {
        "id": 7,
        "category_id": 2,
        "brand_id": 3,
        "name": "Trà Hoa Cúc Mật Ong Dưỡng Tâm 150g",
        "slug": "tra-hoa-cuc-mat-ong-150g",
        "description": "Bông hoa cúc tiến vua sấy lạnh giữ nguyên màu vàng óng, thảo mộc an thần giúp ngủ ngon tự nhiên.",
        "price": 180000.0,
        "sale_price": 165000.0,
        "origin": "Hưng Yên",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1594631252845-29fc4cc8cde9?w=500",
        "stock": 90,
        "details": {
            "ingredients": "Hoa cúc tiến vua sấy lạnh, kỷ tử hữu cơ, cỏ ngọt tự nhiên",
            "taste_profile": "Thơm dịu thanh mát, ngọt nhẹ tự nhiên không gắt, êm dịu",
            "key_benefits": "Giúp an thần, ngủ ngon sâu giấc, thanh nhiệt, sáng mắt, giải tỏa stress",
            "suitable_for": "Người mất ngủ, mỏi mắt do nhìn màn hình nhiều, người lớn tuổi",
            "usage_instructions": "Dùng 5-7 bông hoa cúc hãm với 250ml nước sôi 90 độ C trong 5 phút, có thể thêm mật ong",
            "storage_instructions": "Đậy kín nắp sau khi mở, để nơi thoáng mát",
            "shelf_life": "12 tháng",
            "producer_name": "Nông Trại Thảo Dược Sạch Hưng Yên",
            "production_area": "Văn Giang, Hưng Yên",
            "product_story": "Hoa cúc được hái vào lúc sáng sớm khi sương mai còn đọng trên cánh hoa, sấy lạnh thăng hoa giữ nguyên hoạt chất.",
            "extra_attributes": {"tea_type": "herbal", "caffeine_free": True}
        }
    },

    # 3. Natural Honey
    {
        "id": 8,
        "category_id": 3,
        "brand_id": 5,
        "name": "Mật Ong Rừng U Minh Nguyên Chất 500ml",
        "slug": "mat-ong-rung-u-minh-500ml",
        "description": "Mật ong rừng tràm U Minh hạ tự nhiên nguyên chất 100%, mùi thơm đặc trưng của hoa tràm, sánh đậm.",
        "price": 350000.0,
        "sale_price": 320000.0,
        "origin": "Rừng Tràm U Minh - Cà Mau",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=500",
        "stock": 45,
        "details": {
            "ingredients": "100% mật ong rừng tự nhiên từ hoa tràm U Minh",
            "taste_profile": "Ngọt đậm tự nhiên, thơm nồng mùi hoa tràm rừng, vị hơi chua nhẹ hậu vị",
            "key_benefits": "Bồi bổ sức khỏe, tăng cường đề kháng, hỗ trợ dạ dày và làm dịu cơn ho",
            "suitable_for": "Cả gia đình, người cần bồi bổ cơ thể, làm gia vị nấu ăn cao cấp, pha trà",
            "usage_instructions": "Pha 2 thìa mật ong cùng nước ấm 40 độ C vào buổi sáng hoặc buổi tối trước khi ngủ",
            "storage_instructions": "Bảo quản nhiệt độ phòng nơi thoáng mát, không bảo quản tủ lạnh để tránh kết tinh",
            "shelf_life": "24 tháng",
            "producer_name": "HTX Khai Thác Mật Ong Rừng U Minh",
            "production_area": "U Minh Hạ, Cà Mau",
            "product_story": "Những người thợ gác kèo ong lành nghề len lỏi trong rừng tràm bạt ngàn để thu hoạch những tổ ong tự nhiên mùa hoa nở rộ.",
            "extra_attributes": {"honey_type": "wild_forest", "water_content": "<19%"}
        }
    },
    {
        "id": 9,
        "category_id": 3,
        "brand_id": 2,
        "name": "Mật Ong Hoa Cà Phê Tây Nguyên 1000ml",
        "slug": "mat-ong-hoa-ca-phe-tay-nguyen-1000ml",
        "description": "Mật ong hoa cà phê nguyên chất mùa hoa trắng Tây Nguyên, màu vàng sáng óng ả, ngọt thanh không khé cổ.",
        "price": 210000.0,
        "sale_price": 189000.0,
        "origin": "Gia Lai - Đắk Lắk",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=500",
        "stock": 110,
        "details": {
            "ingredients": "100% mật ong hoa cà phê nguyên chất",
            "taste_profile": "Vàng óng trong vắt, mùi thơm nhẹ dịu của hoa cà phê, ngọt thanh mát không khé cổ",
            "key_benefits": "Cung cấp năng lượng lành mạnh, hỗ trợ tiêu hóa, dưỡng ẩm làm đẹp da",
            "suitable_for": "Pha chế nước uống hàng ngày (nước chanh, cam mật ong), làm bánh, ướp thực phẩm",
            "usage_instructions": "Uống trực tiếp hoặc pha cùng nước ấm, nước hoa quả, sinh tố",
            "storage_instructions": "Để nơi khô ráo, tránh ánh nắng trực tiếp",
            "shelf_life": "24 tháng",
            "producer_name": "Tây Nguyên Origin",
            "production_area": "Pleiku, Gia Lai",
            "product_story": "Thu hoạch vào tháng 2-3 khi những ngọn đồi Tây Nguyên phủ trắng muốt hoa cà phê ngát hương.",
            "extra_attributes": {"honey_type": "floral_coffee", "color": "light_amber"}
        }
    },

    # 4. Healthy Nuts
    {
        "id": 10,
        "category_id": 4,
        "brand_id": 6,
        "name": "Hạt Điều Rang Muối Bình Phước Loại A 500g",
        "slug": "hat-dieu-rang-muoi-binh-phuoc-500g",
        "description": "Hạt điều vỏ lụa Bình Phước size A cồ to đều, rang củi thủ công giòn tan béo ngậy.",
        "price": 175000.0,
        "sale_price": 155000.0,
        "origin": "Bình Phước",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=500",
        "stock": 140,
        "details": {
            "ingredients": "99% hạt điều Bình Phước tuyển chọn size A, 1% muối tinh",
            "taste_profile": "Giòn rụm, béo ngậy thơm ngon tự nhiên, vị mặn nhẹ vừa vặn trên lớp vỏ lụa",
            "key_benefits": "Giàu protein thực vật, chất béo không bão hòa tốt cho tim mạch, bổ sung magie",
            "suitable_for": "Ăn vặt lành mạnh, thực đơn ăn kiêng eat clean, quà biếu lễ tết",
            "usage_instructions": "Bóc lớp vỏ lụa mỏng và ăn trực tiếp",
            "storage_instructions": "Đậy kín hộp sau khi ăn để giữ độ giòn, để nơi khô ráo",
            "shelf_life": "12 tháng",
            "producer_name": "Công ty Nông Sản Hạt Điều Bình Phước",
            "production_area": "Bù Đăng, Bình Phước",
            "product_story": "Bình Phước là thủ phủ hạt điều ngon nhất thế giới với hàm lượng dinh dưỡng và vị ngọt béo đậm đà đặc trưng.",
            "extra_attributes": {"nut_type": "cashew", "size": "A_grade", "roasting_method": "wood_roasted"}
        }
    },
    {
        "id": 11,
        "category_id": 4,
        "brand_id": 1,
        "name": "Hạt Mắc Ca Lâm Đồng Nứt Vỏ 500g",
        "slug": "hat-mac-ca-lam-dong-500g",
        "description": "Nữ hoàng hạt dinh dưỡng trồng tại cao nguyên Lâm Đồng, nhân dày tròn đều, béo bùi ngọt sữa.",
        "price": 210000.0,
        "sale_price": 195000.0,
        "origin": "Lâm Hà - Lâm Đồng",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1543208541-0961a29a7337?w=500",
        "stock": 80,
        "details": {
            "ingredients": "100% hạt mắc ca sấy nứt vỏ tự nhiên, kèm dụng cụ tách vỏ",
            "taste_profile": "Béo ngậy vị bơ sữa, thơm giòn nhẹ, hậu vị bùi béo tự nhiên",
            "key_benefits": "Bổ sung Omega 3-6-9 tốt cho não bộ và thai nhi, kiểm soát cholesterol",
            "suitable_for": "Mẹ bầu, trẻ nhỏ, người tập gym, người theo chế độ dinh dưỡng lành mạnh",
            "usage_instructions": "Dùng dụng cụ kim loại chèn vào khe nứt và xoay nhẹ để lấy nhân ăn liền",
            "storage_instructions": "Bảo quản nơi mát mẻ, tránh ẩm ướt",
            "shelf_life": "12 tháng",
            "producer_name": "Cầu Đất Farm Maca Reserve",
            "production_area": "Lâm Hà, Lâm Đồng",
            "product_story": "Khí hậu mát mẻ và thổ nhưỡng cao nguyên Lâm Đồng cho ra đời những hạt mắc ca chất lượng cao tương đương hàng nhập khẩu.",
            "extra_attributes": {"nut_type": "macadamia", "packaging": "jar_with_key"}
        }
    },

    # 5. Dried Fruits
    {
        "id": 12,
        "category_id": 5,
        "brand_id": 7,
        "name": "Xoài Sấy Dẻo Cam Ranh Hảo Hạng 250g",
        "slug": "xoai-say-deo-cam-ranh-250g",
        "description": "Miếng xoài cát Cam Ranh vàng ươm, dẻo mềm chua ngọt tự nhiên không tẩm đường hóa học.",
        "price": 95000.0,
        "sale_price": 85000.0,
        "origin": "Cam Ranh - Khánh Hòa",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1553279768-865429fa0078?w=500",
        "stock": 130,
        "details": {
            "ingredients": "95% xoài cát Cam Ranh chín tự nhiên, 5% đường mía",
            "taste_profile": "Dẻo mềm dai dai, chua ngọt hài hòa, thơm lừng hương xoài chín tươi",
            "key_benefits": "Bổ sung vitamin C, vitamin A, chất xơ tự nhiên cho cơ thể",
            "suitable_for": "Món ăn vặt thơm ngon cho mọi lứa tuổi, dân văn phòng ăn nhẹ",
            "usage_instructions": "Ăn trực tiếp hoặc dùng kèm sữa chua, granola",
            "storage_instructions": "Bảo quản nơi khô ráo, đậy kín túi zip sau mỗi lần dùng",
            "shelf_life": "9 tháng",
            "producer_name": "Nông Sản Sấy LifeGift",
            "production_area": "Cam Ranh, Khánh Hòa",
            "product_story": "Xoài Cam Ranh nức tiếng với vị ngọt đậm đà, được thái lát vừa ăn và sấy nhiệt độ thấp giữ nguyên dưỡng chất.",
            "extra_attributes": {"fruit_type": "mango", "sugar_content": "low"}
        }
    },
    {
        "id": 13,
        "category_id": 5,
        "brand_id": 7,
        "name": "Mít Sấy Giòn Tây Ninh Loại 1 Túi 500g",
        "slug": "mit-say-gion-tay-ninh-500g",
        "description": "Mít sấy thăng hoa nguyên múi dày cùi, vàng óng, giòn rụm và ngọt thơm tự nhiên.",
        "price": 120000.0,
        "sale_price": None,
        "origin": "Tây Ninh",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1601493700631-2b16ec4b4716?w=500",
        "stock": 95,
        "details": {
            "ingredients": "100% mít nghệ tươi Tây Ninh chín cây",
            "taste_profile": "Giòn xốp, thơm nồng nàn vị mít chín, ngọt dịu tự nhiên không gắt dầu",
            "key_benefits": "Bổ sung chất xơ và khoáng chất, món ăn vặt lành mạnh không chất bảo quản",
            "suitable_for": "Gia đình, tiệc trà, ăn vặt cùng bạn bè",
            "usage_instructions": "Mở gói ăn ngay",
            "storage_instructions": "Đóng chặt túi zip tránh không khí làm yểu giòn",
            "shelf_life": "12 tháng",
            "producer_name": "Nông Sản Sấy LifeGift",
            "production_area": "Tây Ninh",
            "product_story": "Mít nghệ quả to múi vàng ươm được tuyển chọn và sấy bằng công nghệ chân không hiện đại.",
            "extra_attributes": {"fruit_type": "jackfruit", "crispy": True}
        }
    },

    # 6. Gift Boxes
    {
        "id": 14,
        "category_id": 6,
        "brand_id": 7,
        "name": "Hộp Quà Nông Sản Dưỡng Lành LifeGift Cao Cấp",
        "slug": "hop-qua-nong-san-duong-lanh-cao-cap",
        "description": "Hộp quà thiết kế sang trọng gồm Trà Shan Tuyết, Mật ong rừng U Minh và Hạt mắc ca Lâm Đồng.",
        "price": 850000.0,
        "sale_price": 790000.0,
        "origin": "Việt Nam (Hà Giang, Cà Mau, Lâm Đồng)",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=500",
        "stock": 35,
        "details": {
            "ingredients": "1 hũ Mật ong rừng U Minh 350ml, 1 hộp Trà Shan Tuyết 100g, 1 hộp Hạt mắc ca 250g, 1 hộp Xoài sấy dẻo 150g",
            "taste_profile": "Hương vị đa dạng từ thanh tao, béo bùi đến ngọt mát tự nhiên của nông sản ba miền",
            "key_benefits": "Bộ quà tặng chăm sóc sức khỏe toàn diện từ những đặc sản trứ danh đất Việt",
            "suitable_for": "Quà tặng doanh nghiệp, tri ân đối tác, biếu bố mẹ và người thân dịp lễ Tết",
            "usage_instructions": "Thưởng thức từng món đặc sản theo hướng dẫn trên bao bì mỗi sản phẩm",
            "storage_instructions": "Để hộp quà nơi khô ráo, thoáng mát, tránh ánh nắng trực tiếp",
            "shelf_life": "12 tháng",
            "producer_name": "LifeGift Premium Collection",
            "production_area": "Việt Nam",
            "product_story": "Bộ quà gom trọn hương vị núi rừng Tây Bắc, phù sa sông nước miền Tây và gió đại ngàn Tây Nguyên thành một món quà trân quý gửi trao tấm lòng.",
            "extra_attributes": {"gift_occasion": ["tet", "corporate", "parents"], "box_material": "premium_wood_paper"}
        }
    },
    {
        "id": 15,
        "category_id": 6,
        "brand_id": 7,
        "name": "Set Quà Tinh Hoa Trà Cà Phê Việt",
        "slug": "set-qua-tinh-hoa-tra-ca-phe-viet",
        "description": "Set quà tinh tế gồm Cà phê Arabica Cầu Đất, Trà Oolong Bảo Lộc và Hạt điều rang muối Bình Phước.",
        "price": 620000.0,
        "sale_price": 580000.0,
        "origin": "Lâm Đồng & Bình Phước",
        "status": "ACTIVE",
        "image": "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=500",
        "stock": 40,
        "details": {
            "ingredients": "1 hộp Cà phê Arabica Cầu Đất 250g, 1 hộp Trà Oolong Tứ Quý 150g, 1 hộp Hạt điều vỏ lụa 250g",
            "taste_profile": "Hương hoa trà ngát, cà phê thơm thanh tao và hạt điều giòn béo đậm đà",
            "key_benefits": "Món quà tinh tế kích thích mọi giác quan, tạo không gian thưởng thức tao nhã",
            "suitable_for": "Tặng thầy cô, đồng nghiệp, đối tác kinh doanh yêu văn hóa thưởng trà cà phê",
            "usage_instructions": "Dùng pha trà và cà phê nóng, thưởng thức cùng hạt điều giòn",
            "storage_instructions": "Bảo quản nơi khô ráo thoáng mát",
            "shelf_life": "12 tháng",
            "producer_name": "LifeGift Specialty",
            "production_area": "Việt Nam",
            "product_story": "Món quà của sự tao nhã và nồng ấm cho những buổi đàm đạo thân tình.",
            "extra_attributes": {"gift_occasion": ["teachers_day", "colleagues", "friends"]}
        }
    },
    # 7. Out of stock item for testing
    {
        "id": 16,
        "category_id": 1,
        "brand_id": 1,
        "name": "Cà phê Robusta Mật Ong Honey Process 250g",
        "slug": "ca-phe-robusta-honey-process-250g",
        "description": "Cà phê sơ chế Honey vị ngọt đậm trái cây chín, tạm hết hàng mùa vụ.",
        "price": 160000.0,
        "sale_price": None,
        "origin": "Lâm Đồng",
        "status": "OUT_OF_STOCK",
        "image": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500",
        "stock": 0,
        "details": {
            "ingredients": "100% Robusta sơ chế Honey",
            "taste_profile": "Ngọt đậm vị đường mía, hương mận chín, ít đắng",
            "key_benefits": "Tăng lực tự nhiên, vị ngọt dễ uống",
            "suitable_for": "Người thích cà phê hương vị mới lạ",
            "usage_instructions": "Pha phin hoặc máy",
            "storage_instructions": "Nơi thoáng mát",
            "shelf_life": "12 tháng",
            "producer_name": "Cầu Đất Farm",
            "production_area": "Lâm Đồng",
            "product_story": "Sơ chế giữ lại lớp chất nhầy quả chín để lên men tự nhiên mang lại vị ngọt đậm đà.",
            "extra_attributes": {"roast_level": "medium"}
        }
    }
]

CERTIFICATES = [
    {
        "id": 1,
        "product_id": 1,
        "name": "Chứng nhận VietGAP Trồng trọt",
        "issuer": "Trung tâm Chứng nhận Phù hợp Quacert",
        "certificate_code": "VIETGAP-TT-2024-0891",
        "issued_at": "2024-01-15",
        "expires_at": "2027-01-15",
        "description": "Chứng nhận quy trình sản xuất cà phê an toàn theo tiêu chuẩn VietGAP, không dư lượng thuốc bảo vệ thực vật.",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "product_id": 1,
        "name": "Chứng nhận OCOP 4 Sao Tỉnh Lâm Đồng",
        "issuer": "UBND Tỉnh Lâm Đồng",
        "certificate_code": "OCOP-LD-2023-4S-012",
        "issued_at": "2023-11-20",
        "expires_at": "2026-11-20",
        "description": "Sản phẩm OCOP 4 sao đại diện nông sản thế mạnh chất lượng cao của địa phương.",
        "status": "ACTIVE",
    },
    {
        "id": 3,
        "product_id": 5,
        "name": "Chứng nhận Hữu cơ Organic USDA",
        "issuer": "Control Union Certifications",
        "certificate_code": "CU-ORG-89210",
        "issued_at": "2024-03-10",
        "expires_at": "2027-03-10",
        "description": "Chứng nhận vùng nguyên liệu trà Shan Tuyết cổ thụ canh tác 100% tự nhiên không hóa chất theo tiêu chuẩn USDA.",
        "status": "ACTIVE",
    },
    {
        "id": 4,
        "product_id": 8,
        "name": "Chứng nhận Chỉ dẫn Địa lý Mật ong U Minh",
        "issuer": "Cục Sở hữu Trí tuệ Việt Nam",
        "certificate_code": "CDDL-VN-UM-004",
        "issued_at": "2022-05-18",
        "expires_at": "2032-05-18",
        "description": "Chỉ dẫn địa lý bảo hộ nguồn gốc đặc sản Mật ong rừng tràm U Minh nguyên chất.",
        "status": "ACTIVE",
    },
    {
        "id": 5,
        "product_id": 10,
        "name": "Chứng nhận An toàn Thực phẩm HACCP & ISO 22000",
        "issuer": "Tổ chức Chứng nhận Quốc tế SGS",
        "certificate_code": "SGS-HACCP-2024-991",
        "issued_at": "2024-02-01",
        "expires_at": "2027-02-01",
        "description": "Hệ thống quản lý an toàn vệ sinh thực phẩm quốc tế cho dây chuyền chế biến hạt điều.",
        "status": "ACTIVE",
    },
]

USERS = [
    {"id": 1, "email": "customer@lifegift.vn", "full_name": "Nguyễn Văn An", "phone": "0912345678"},
    {"id": 2, "email": "phong.tuan@gmail.com", "full_name": "Phan Tuấn Phong", "phone": "0987654321"},
]

WAREHOUSES = [
    {"id": 1, "name": "Kho Tổng TP. Hồ Chí Minh", "status": "ACTIVE"},
    {"id": 2, "name": "Kho Hà Nội", "status": "ACTIVE"},
]

BLOG_CATEGORIES = [
    {"id": 1, "name": "Kiến thức cà phê", "slug": "kien-thuc-ca-phe"},
    {"id": 2, "name": "Kiến thức trà & thảo mộc", "slug": "kien-thuc-tra"},
    {"id": 6, "name": "Quà tặng doanh nghiệp", "slug": "qua-tang-doanh-nghiep"},
]

REVIEWS = [
    {
        "id": 1,
        "product_id": 1,
        "user_id": 1,
        "rating": 5,
        "title": "Cà phê thơm dịu rất vừa gu",
        "content": "Mình pha Pour Over buổi sáng mùi hoa quả thơm lừng cả phòng, vị chua thanh dễ chịu và không hề gắt.",
        "status": "APPROVED",
    },
    {
        "id": 2,
        "product_id": 1,
        "user_id": 2,
        "rating": 5,
        "title": "Hạt rang chuẩn medium",
        "content": "Chất lượng hạt đều tăm tắp, pha espresso hay cold brew đều ngon xuất sắc.",
        "status": "APPROVED",
    },
    {
        "id": 3,
        "product_id": 2,
        "user_id": 1,
        "rating": 4,
        "title": "Rất đậm đà, tỉnh táo cả ngày",
        "content": "Robusta pha phin với sữa đặc chuẩn vị truyền thống. Uống xong tập trung làm việc cực tốt.",
        "status": "APPROVED",
    },
    {
        "id": 4,
        "product_id": 5,
        "user_id": 2,
        "rating": 5,
        "title": "Trà Shan Tuyết ngọt hậu sâu",
        "content": "Nước trà vàng óng, uống vào vị ngọt hậu lưu giữ rất lâu, xứng đáng trà cổ thụ trăm năm.",
        "status": "APPROVED",
    },
    {
        "id": 5,
        "product_id": 1,
        "user_id": 2,
        "rating": 1,
        "title": "Spam test review",
        "content": "Nội dung spam không được phê duyệt.",
        "status": "REJECTED",
    },
    {
        "id": 6,
        "product_id": 1,
        "user_id": 1,
        "rating": 4,
        "title": "Chờ duyệt",
        "content": "Đang trong hàng đợi kiểm duyệt.",
        "status": "PENDING",
    },
]

BLOG_POSTS = [
    {
        "id": 1,
        "category_id": 1,
        "title": "Bí quyết chọn cà phê nguyên chất chuẩn vị không pha tạp",
        "slug": "bi-quyet-chon-ca-phe-nguyen-chat",
        "summary": "Hướng dẫn nhận biết cà phê hạt rang mộc nguyên chất qua màu sắc bột, độ phồng khi gặp nước sôi và hương thơm tự nhiên.",
        "content": """Để nhận biết cà phê nguyên chất 100%, bạn có thể dựa vào các dấu hiệu thực tế sau:
1. Độ xốp và khối lượng: Bột cà phê nguyên chất rất nhẹ, xốp, tơi xốp đồng đều và không dính bết như bột pha bắp hoặc đậu nành rang cháy.
2. Màu sắc bột: Cà phê rang mộc có màu nâu cánh gián đến nâu đậm đồng nhất, không có màu đen kịt bóng dầu của bơ hay phẩm màu.
3. Phản ứng với nước sôi: Khi rót nước sôi 90-95 độ C vào phin, bột cà phê nguyên chất sẽ nở phồng sủi bọt mạnh mẽ do khí CO2 thoát ra từ cấu trúc xơ hạt. Bột pha tạp chất sẽ xẹp nhanh và vón cục.
4. Mùi thơm và vị giác: Cà phê thật có mùi thơm thanh tao tự nhiên, vị đắng thanh hòa cùng vị chua dịu nhẹ và hậu vị ngọt sâu, không có mùi nồng gắt nhân tạo.
Tại LifeGift, toàn bộ dòng cà phê Arabica Cầu Đất và Robusta Buôn Ma Thuột đều được rang mộc 100%, có chứng nhận VietGAP an toàn tuyệt đối.""",
        "status": "PUBLISHED",
    },
    {
        "id": 2,
        "category_id": 2,
        "title": "Lợi ích sức khỏe tuyệt vời của Trà Shan Tuyết cổ thụ Tây Côn Lĩnh",
        "slug": "loi-ich-tra-shan-tuyet-co-thu",
        "summary": "Khám phá hàm lượng chất chống oxy hóa EGCG và khoáng chất quý trong những búp chè Shan Tuyết cổ thụ trên núi cao Hà Giang.",
        "content": """Trà Shan Tuyết cổ thụ sinh trưởng trên độ cao 2.000m tại đỉnh Tây Côn Lĩnh (Hà Giang), quanh năm mây mù che phủ. 
Những cây chè cổ thụ hàng trăm năm tuổi hấp thụ khoáng chất tự nhiên sâu trong lòng núi, tạo nên búp chè phủ tuyết trắng giàu dưỡng chất:
- Chống lão hóa: Hàm lượng Polyphenol và EGCG cao gấp nhiều lần chè trồng công nghiệp giúp ngăn ngừa lão hóa tế bào.
- Hỗ trợ tim mạch: Giúp ổn định huyết áp, thanh lọc mỡ máu và tăng cường sức bền thành mạch.
- Tỉnh táo mà không gây xót ruột: Hàm lượng theanine tự nhiên giúp tinh thần sảng khoái, thư giãn sâu mà không gây cồn cào bao tử.
Cách pha chuẩn: Sử dụng nước suối tinh khiết đun sôi đến 85-90 độ C, hãm trà trong 30-45 giây. Một ấm trà có thể châm từ 6 đến 8 tuần nước vẫn giữ nguyên vị ngọt hậu sâu sắc.""",
        "status": "PUBLISHED",
    },
    {
        "id": 3,
        "category_id": 6,
        "title": "Gợi ý chọn quà tặng doanh nghiệp tinh tế từ nông sản Việt",
        "slug": "goi-y-qua-tang-doanh-nghiep-nong-san-viet",
        "summary": "Xu hướng quà tặng xanh chăm sóc sức khỏe bằng đặc sản nông sản hữu cơ ba miền cho đối tác và khách hàng.",
        "content": """Quà tặng doanh nghiệp ngày nay đang dịch chuyển mạnh mẽ sang xu hướng 'quà tặng sức khỏe' và 'nông sản xanh':
1. Set quà Nông Sản Dưỡng Lành: Kết hợp Trà Shan Tuyết cổ thụ Hà Giang, Mật ong rừng U Minh và Hạt mắc ca Lâm Đồng là lựa chọn cao cấp, thể hiện sự trân trọng tối đa đến đối tác VIP.
2. Set quà Tinh Hoa Trà Cà Phê: Phù hợp tri ân đồng nghiệp, thầy cô giáo hoặc quà tặng sự kiện với chi phí hợp lý nhưng tràn đầy hương vị truyền thống.
Tất cả các sản phẩm quà tặng của LifeGift đều có chứng chỉ nguồn gốc xuất xứ rõ ràng, bao bì gỗ giấy cao cấp thân thiện môi trường.""",
        "status": "PUBLISHED",
    },
    {
        "id": 4,
        "category_id": 1,
        "title": "Bản nháp: Xu hướng canh tác nông nghiệp tuần hoàn",
        "slug": "ban-nhap-canh-tac-tuan-hoan",
        "summary": "Bài viết chưa hoàn thiện về mô hình nông nghiệp xanh.",
        "content": "Nội dung đang soạn thảo, chưa phát hành ra công chúng.",
        "status": "DRAFT",
    }
]

ORDERS = [
    {
        "id": 1,
        "order_code": "ORD-20260812-0001",
        "user_id": 1,
        "total_amount": 559000.0,
        "order_status": "SHIPPING",
        "payment_status": "PAID",
        "items": [
            {"product_id": 1, "quantity": 1, "price": 239000.0},
            {"product_id": 8, "quantity": 1, "price": 320000.0}
        ],
        "history": [
            {"status": "PENDING", "notes": "Đơn hàng mới được tạo thành công trên hệ thống."},
            {"status": "PROCESSING", "notes": "Đã xác nhận thanh toán trực tuyến và chuyển kho đóng gói."},
            {"status": "SHIPPING", "notes": "Kiện hàng đã giao cho đơn vị vận chuyển Viettel Post (Mã vận đơn: VP88291029). Dự kiến giao trong 24h tới."}
        ]
    },
    {
        "id": 2,
        "order_code": "ORD-20260810-0099",
        "user_id": 2,
        "total_amount": 320000.0,
        "order_status": "DELIVERED",
        "payment_status": "PAID",
        "items": [
            {"product_id": 5, "quantity": 1, "price": 290000.0}
        ],
        "history": [
            {"status": "PENDING", "notes": "Đơn hàng được khởi tạo."},
            {"status": "PROCESSING", "notes": "Đóng gói hoàn tất tại kho Hà Nội."},
            {"status": "SHIPPING", "notes": "Đang trên đường giao hàng."},
            {"status": "DELIVERED", "notes": "Người nhận đã ký nhận bưu phẩm thành công."}
        ]
    }
]


def seed_database():
    """Execute SQL inserts into database."""
    with get_db_context() as session:
        logger.info("Seeding categories...")
        for c in CATEGORIES:
            session.execute(
                text("""
                    INSERT INTO categories (id, name, slug, status)
                    VALUES (:id, :name, :slug, :status)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status)
                """),
                c
            )

        logger.info("Seeding brands...")
        for b in BRANDS:
            session.execute(
                text("""
                    INSERT INTO brands (id, name, slug, status)
                    VALUES (:id, :name, :slug, :status)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), slug=VALUES(slug)
                """),
                {
                    "id": b["id"],
                    "name": b["name"],
                    "slug": b.get("slug") or f"brand-{b['id']}",
                    "status": b["status"],
                }
            )

        logger.info("Seeding users...")
        for u in USERS:
            session.execute(
                text("""
                    INSERT INTO users (id, username, password, email, full_name, phone, status)
                    VALUES (:id, :username, :password, :email, :full_name, :phone, 'ACTIVE')
                    ON DUPLICATE KEY UPDATE full_name=VALUES(full_name), phone=VALUES(phone), email=VALUES(email)
                """),
                {
                    "id": u["id"],
                    "username": u.get("username") or f"user_{u['id']}",
                    "password": u.get("password") or "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy",
                    "email": u["email"],
                    "full_name": u["full_name"],
                    "phone": u["phone"],
                }
            )

        logger.info("Seeding warehouses...")
        for w in WAREHOUSES:
            session.execute(
                text("""
                    INSERT INTO warehouses (id, code, name, status)
                    VALUES (:id, :code, :name, :status)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), status=VALUES(status), code=VALUES(code)
                """),
                {
                    "id": w["id"],
                    "code": w.get("code") or f"WH-{w['id']}",
                    "name": w["name"],
                    "status": w["status"],
                }
            )

        logger.info("Seeding products & details...")
        for p in PRODUCTS:
            status = p["status"]
            stock_status = "IN_STOCK"
            if status == "OUT_OF_STOCK":
                status = "INACTIVE"
                stock_status = "OUT_OF_STOCK"
            session.execute(
                text("""
                    INSERT INTO products (
                        id, category_id, brand_id, sku, name, slug, description,
                        price, sale_price, origin, unit, pricing_type, stock_status, status
                    )
                    VALUES (
                        :id, :category_id, :brand_id, :sku, :name, :slug, :description,
                        :price, :sale_price, :origin, :unit, 'FIXED_PRICE', :stock_status, :status
                    )
                    ON DUPLICATE KEY UPDATE
                        category_id=VALUES(category_id), brand_id=VALUES(brand_id), name=VALUES(name),
                        description=VALUES(description), price=VALUES(price), sale_price=VALUES(sale_price),
                        origin=VALUES(origin), status=VALUES(status), stock_status=VALUES(stock_status),
                        sku=VALUES(sku), unit=VALUES(unit)
                """),
                {
                    "id": p["id"],
                    "category_id": p["category_id"],
                    "brand_id": p["brand_id"],
                    "sku": p.get("sku") or f"SKU-{p['id']}",
                    "name": p["name"],
                    "slug": p["slug"],
                    "description": p["description"],
                    "price": p["price"],
                    "sale_price": p["sale_price"],
                    "origin": p["origin"],
                    "unit": p.get("unit") or "Sản phẩm",
                    "stock_status": stock_status,
                    "status": status,
                }
            )

            # Product image
            session.execute(
                text("""
                    INSERT INTO product_images (product_id, image_url, is_primary, sort_order)
                    VALUES (:product_id, :image_url, 1, 0)
                """),
                {"product_id": p["id"], "image_url": p["image"]}
            )

            # Product inventory (available_quantity is GENERATED from quantity - reserved)
            session.execute(
                text("""
                    INSERT INTO inventories (product_id, warehouse_id, quantity, reserved_quantity, min_stock)
                    VALUES (:product_id, 1, :quantity, 0, 0)
                    ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), reserved_quantity=VALUES(reserved_quantity)
                """),
                {"product_id": p["id"], "quantity": p["stock"]}
            )

            # Product details
            d = p["details"]
            session.execute(
                text("""
                    INSERT INTO product_details (
                        product_id, ingredients, taste_profile, key_benefits, suitable_for,
                        usage_instructions, storage_instructions, shelf_life, producer_name,
                        production_area, product_story, extra_attributes
                    ) VALUES (
                        :product_id, :ingredients, :taste_profile, :key_benefits, :suitable_for,
                        :usage_instructions, :storage_instructions, :shelf_life, :producer_name,
                        :production_area, :product_story, :extra_attributes
                    ) ON DUPLICATE KEY UPDATE
                        ingredients=VALUES(ingredients), taste_profile=VALUES(taste_profile),
                        key_benefits=VALUES(key_benefits), suitable_for=VALUES(suitable_for),
                        usage_instructions=VALUES(usage_instructions), storage_instructions=VALUES(storage_instructions),
                        shelf_life=VALUES(shelf_life), producer_name=VALUES(producer_name),
                        production_area=VALUES(production_area), product_story=VALUES(product_story),
                        extra_attributes=VALUES(extra_attributes)
                """),
                {
                    "product_id": p["id"],
                    "ingredients": d.get("ingredients"),
                    "taste_profile": d.get("taste_profile"),
                    "key_benefits": d.get("key_benefits"),
                    "suitable_for": d.get("suitable_for"),
                    "usage_instructions": d.get("usage_instructions"),
                    "storage_instructions": d.get("storage_instructions"),
                    "shelf_life": d.get("shelf_life"),
                    "producer_name": d.get("producer_name"),
                    "production_area": d.get("production_area"),
                    "product_story": d.get("product_story"),
                    "extra_attributes": json.dumps(d.get("extra_attributes", {})),
                }
            )

        logger.info("Seeding certificates...")
        for cert in CERTIFICATES:
            session.execute(
                text("""
                    INSERT INTO product_certificates (
                        id, product_id, name, issuer, certificate_code, issued_at, expires_at, description, status
                    ) VALUES (
                        :id, :product_id, :name, :issuer, :certificate_code, :issued_at, :expires_at, :description, :status
                    ) ON DUPLICATE KEY UPDATE
                        name=VALUES(name), status=VALUES(status)
                """),
                cert
            )

        logger.info("Seeding blog categories...")
        for bc in BLOG_CATEGORIES:
            session.execute(
                text("""
                    INSERT INTO blog_categories (id, name, slug, status)
                    VALUES (:id, :name, :slug, 'ACTIVE')
                    ON DUPLICATE KEY UPDATE name=VALUES(name), slug=VALUES(slug)
                """),
                bc
            )

        logger.info("Seeding blog posts...")
        for blog in BLOG_POSTS:
            blog_status = "HIDDEN" if blog["status"] == "ARCHIVED" else blog["status"]
            session.execute(
                text("""
                    INSERT INTO blog_posts (
                        id, category_id, author_id, title, slug, summary, content, status, published_at
                    )
                    VALUES (
                        :id, :category_id, :author_id, :title, :slug, :summary, :content, :status, CURRENT_TIMESTAMP
                    )
                    ON DUPLICATE KEY UPDATE title=VALUES(title), content=VALUES(content), status=VALUES(status)
                """),
                {
                    **blog,
                    "status": blog_status,
                    "author_id": 1,
                }
            )

        logger.info("Seeding orders...")
        for ord_data in ORDERS:
            user = next((u for u in USERS if u["id"] == ord_data["user_id"]), None)
            session.execute(
                text("""
                    INSERT INTO orders (
                        id, order_code, user_id, receiver_name, receiver_phone,
                        shipping_province, shipping_address, subtotal, total_amount,
                        payment_method, order_status, payment_status
                    )
                    VALUES (
                        :id, :order_code, :user_id, :receiver_name, :receiver_phone,
                        :shipping_province, :shipping_address, :subtotal, :total_amount,
                        'COD', :order_status, :payment_status
                    )
                    ON DUPLICATE KEY UPDATE order_status=VALUES(order_status), payment_status=VALUES(payment_status)
                """),
                {
                    "id": ord_data["id"],
                    "order_code": ord_data["order_code"],
                    "user_id": ord_data["user_id"],
                    "receiver_name": (user or {}).get("full_name") or f"User {ord_data['user_id']}",
                    "receiver_phone": (user or {}).get("phone") or "0000000000",
                    "shipping_province": "Việt Nam",
                    "shipping_address": "Địa chỉ demo",
                    "subtotal": ord_data["total_amount"],
                    "total_amount": ord_data["total_amount"],
                    "order_status": ord_data["order_status"],
                    "payment_status": ord_data["payment_status"],
                }
            )

            for item in ord_data["items"]:
                prod = next((p for p in PRODUCTS if p["id"] == item["product_id"]), None)
                product_name = prod["name"] if prod else f"Product {item['product_id']}"
                sku = (prod.get("sku") if prod else None) or f"SKU-{item['product_id']}"
                session.execute(
                    text("""
                        INSERT INTO order_items (
                            order_id, product_id, product_name, sku, unit_price, quantity, subtotal
                        ) VALUES (
                            :order_id, :product_id, :product_name, :sku, :unit_price, :quantity, :subtotal
                        )
                    """),
                    {
                        "order_id": ord_data["id"],
                        "product_id": item["product_id"],
                        "product_name": product_name,
                        "sku": sku,
                        "unit_price": item["price"],
                        "quantity": item["quantity"],
                        "subtotal": item["price"] * item["quantity"],
                    }
                )

            for hist in ord_data["history"]:
                session.execute(
                    text("""
                        INSERT INTO order_status_history (order_id, status, note)
                        VALUES (:order_id, :status, :note)
                    """),
                    {
                        "order_id": ord_data["id"],
                        "status": hist["status"],
                        "note": hist["notes"],
                    }
                )

        logger.info("Seeding reviews...")
        max_order_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM orders")).scalar() or 0
        for rev in REVIEWS:
            status = "HIDDEN" if rev["status"] == "REJECTED" else rev["status"]
            order_id = session.execute(
                text("""
                    SELECT o.id
                    FROM orders o
                    JOIN order_items oi ON oi.order_id = o.id
                    WHERE o.user_id = :user_id AND oi.product_id = :product_id
                    ORDER BY o.id
                    LIMIT 1
                """),
                {"user_id": rev["user_id"], "product_id": rev["product_id"]},
            ).scalar()
            if order_id is None:
                max_order_id += 1
                prod = next((p for p in PRODUCTS if p["id"] == rev["product_id"]), None)
                unit_price = float((prod or {}).get("sale_price") or (prod or {}).get("price") or 0)
                user = next((u for u in USERS if u["id"] == rev["user_id"]), None)
                session.execute(
                    text("""
                        INSERT INTO orders (
                            id, order_code, user_id, receiver_name, receiver_phone,
                            shipping_province, shipping_address, subtotal, total_amount,
                            payment_method, payment_status, order_status, note
                        ) VALUES (
                            :id, :order_code, :user_id, :receiver_name, :receiver_phone,
                            'Việt Nam', 'Đơn tổng hợp review (seed)', :unit_price, :unit_price,
                            'COD', 'PAID', 'COMPLETED', 'Synthetic review order'
                        )
                    """),
                    {
                        "id": max_order_id,
                        "order_code": f"MIG-REV-{max_order_id:08d}",
                        "user_id": rev["user_id"],
                        "receiver_name": (user or {}).get("full_name") or f"User {rev['user_id']}",
                        "receiver_phone": (user or {}).get("phone") or "0000000000",
                        "unit_price": unit_price,
                    },
                )
                session.execute(
                    text("""
                        INSERT INTO order_items (
                            order_id, product_id, product_name, sku, unit_price, quantity, subtotal
                        ) VALUES (
                            :order_id, :product_id, :product_name, :sku, :unit_price, 1, :unit_price
                        )
                    """),
                    {
                        "order_id": max_order_id,
                        "product_id": rev["product_id"],
                        "product_name": (prod or {}).get("name") or f"Product {rev['product_id']}",
                        "sku": (prod or {}).get("sku") or f"SKU-{rev['product_id']}",
                        "unit_price": unit_price,
                    },
                )
                order_id = max_order_id

            session.execute(
                text("""
                    INSERT INTO reviews (id, product_id, user_id, order_id, rating, title, content, status)
                    VALUES (:id, :product_id, :user_id, :order_id, :rating, :title, :content, :status)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), rating=VALUES(rating), order_id=VALUES(order_id)
                """),
                {
                    "id": rev["id"],
                    "product_id": rev["product_id"],
                    "user_id": rev["user_id"],
                    "order_id": order_id,
                    "rating": rev["rating"],
                    "title": rev["title"],
                    "content": rev["content"],
                    "status": status,
                },
            )

        logger.info("Seed data completed successfully!")


if __name__ == "__main__":
    seed_database()
