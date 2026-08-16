"""Property-style tests for search/grounding hardening (no eval-bank hardcoding)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.chatbot.llm import parse_price_bounds, detect_price_unit, _parse_vnd_number
from backend.app.chatbot.prompts import ANSWER_SYSTEM_PROMPT, INTENT_EXTRACTION_SYSTEM_PROMPT
from backend.app.chatbot.router import normalize_extraction
from backend.app.chatbot.service import ChatbotService
from backend.app.models.tables import Category, Product
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.chat import IntentExtractionResult, IntentEnum, PriceUnitEnum
from backend.app.schemas.product import ProductCard, ProductSearchParams


class TestPriceParsing:
    def test_thousand_separators_range(self):
        lo, hi = parse_price_bounds("từ 100.000 đến 200.000 đồng")
        assert lo == 100000
        assert hi == 200000

    def test_en_dash_range(self):
        lo, hi = parse_price_bounds("khoảng 120–180k")
        assert lo == 120000
        assert hi == 180000

    def test_under_k(self):
        lo, hi = parse_price_bounds("dưới 150k")
        assert lo is None
        assert hi == 150000

    def test_parse_vnd_number_k(self):
        assert _parse_vnd_number("200k") == 200000

    def test_detect_per_kg(self):
        assert detect_price_unit("cà phê dưới 200.000 đồng/kg") == "PER_KG"
        assert detect_price_unit("cà phê dưới 200 nghìn") == "PACKAGE"


class TestNormalizeExtraction:
    def test_nudge_knowledge_to_search_on_discovery(self):
        raw = IntentExtractionResult(
            intent=IntentEnum.KNOWLEDGE,
            category="cà phê",
            max_price=200000,
        )
        out = normalize_extraction("Có cà phê nào dưới 200k không?", raw)
        assert out.intent == IntentEnum.PRODUCT_SEARCH
        assert out.max_price == 200000
        assert out.price_unit == PriceUnitEnum.PACKAGE

    def test_per_kg_unit(self):
        raw = IntentExtractionResult(intent=IntentEnum.PRODUCT_SEARCH, category="cà phê")
        out = normalize_extraction("Có cà phê nào dưới 200.000 đồng/kg không?", raw)
        assert out.price_unit == PriceUnitEnum.PER_KG
        assert out.max_price == 200000

    def test_sanitize_price_query(self):
        raw = IntentExtractionResult(
            intent=IntentEnum.PRODUCT_SEARCH,
            category="cà phê",
            query="200.000 đồng/kg",
        )
        out = normalize_extraction("Cà phê 200.000 đồng/kg", raw)
        assert out.query is None


class TestDenialGuard:
    def test_answer_ignores_products(self):
        svc = ChatbotService.__new__(ChatbotService)
        products = [
            ProductCard(
                id=1,
                name="Cà phê Test 500g",
                price=100000,
                sale_price=None,
                effective_price=100000,
            )
        ]
        denial = "Hiện tại tôi chưa có dữ liệu cụ thể về các loại cà phê."
        assert svc._answer_ignores_products(denial, products) is True
        ok = "Bạn có thể xem Cà phê Test 500g giá 100.000đ."
        assert svc._answer_ignores_products(ok, products) is False

    def test_empty_structured_fallback_surfaces_facets(self):
        svc = ChatbotService.__new__(ChatbotService)
        context = (
            "NO PRODUCTS MATCH FILTERS (MYSQL DATA).\n"
            "Reason: UNKNOWN_KIND.\n"
            "Available in-stock categories: Cà phê, Trà, Hạt dinh dưỡng"
        )
        answer = svc._format_deterministic_fallback("Có gạo nào không?", context)
        assert "không" in answer.lower() or "chưa" in answer.lower()
        assert "Cà phê" in answer
        assert "xin chào" not in answer.lower()


@pytest.mark.parametrize(
    "message,expect_unit",
    [
        ("sản phẩm dưới 100k", "PACKAGE"),
        ("sản phẩm 50k/kg", "PER_KG"),
        ("một ký không quá 200 nghìn", "PER_KG"),
    ],
)
def test_detect_price_unit_matrix(message, expect_unit):
    assert detect_price_unit(message) == expect_unit


# ---------------------------------------------------------------------------
# Integration: hard filters / facets / price units (seeded SQLite demo data)
# ---------------------------------------------------------------------------


def _product_category_ids(session: Session, product_ids: list[int]) -> dict[int, int]:
    rows = (
        session.query(Product.id, Product.category_id)
        .filter(Product.id.in_(product_ids))
        .all()
    )
    return {int(r.id): int(r.category_id) for r in rows if r.category_id is not None}


def test_hard_category_isolation_coffee_vs_tea(db_session: Session):
    """Every hit for a resolved category must belong only to that category_id."""
    repo = ProductRepository(db_session)

    coffee_id, coffee_ok = repo.resolve_category_id("cà phê")
    tea_id, tea_ok = repo.resolve_category_id("trà")
    assert coffee_ok and coffee_id is not None
    assert tea_ok and tea_id is not None
    assert coffee_id != tea_id

    coffee = repo.search_products_detailed(
        ProductSearchParams(category="cà phê", in_stock=False, limit=10)
    )
    tea = repo.search_products_detailed(
        ProductSearchParams(category="trà", in_stock=False, limit=10)
    )

    assert coffee.products, "expected seeded coffee products"
    assert tea.products, "expected seeded tea products"
    assert coffee.category_resolved is True
    assert tea.category_resolved is True
    assert coffee.empty_reason is None
    assert tea.empty_reason is None

    coffee_map = _product_category_ids(db_session, [p.id for p in coffee.products])
    tea_map = _product_category_ids(db_session, [p.id for p in tea.products])

    for pid, cid in coffee_map.items():
        assert cid == coffee_id, f"product {pid} leaked into coffee search (cat={cid})"
    for pid, cid in tea_map.items():
        assert cid == tea_id, f"product {pid} leaked into tea search (cat={cid})"

    coffee_ids = {p.id for p in coffee.products}
    tea_ids = {p.id for p in tea.products}
    assert coffee_ids.isdisjoint(tea_ids), "cross-category product id overlap"


def test_unknown_kind_empty_with_facets(db_session: Session):
    """Unresolvable kind with no name hits → 0 products, UNKNOWN_KIND, facets."""
    repo = ProductRepository(db_session)
    result = repo.search_products_detailed(
        ProductSearchParams(category="sầu riêng lạ xyz", in_stock=False)
    )

    assert result.products == []
    assert result.empty_reason == "UNKNOWN_KIND"
    assert result.category_resolved is False
    assert result.applied_filters.get("category_resolved") is False
    assert result.applied_filters.get("kind")
    assert result.available_categories, "facets should list active categories"
    facets = repo.list_available_categories()
    assert facets
    assert set(result.available_categories).issubset(set(facets)) or set(
        result.available_categories
    ) == set(facets)


def test_per_kg_filter_excludes_missing_weight_and_bounds(db_session: Session):
    """
    PER_KG requires positive weight; filter uses effective_price / (weight/1000).
    Seed products do not set weight — assign in-session for the test.
    """
    # Product 1: 500g, effective 239000 → 478000 /kg
    # Product 2: 500g, effective 180000 → 360000 /kg
    # Product 3: leave weight NULL → must be excluded under PER_KG
    # Product 4: 250g, effective 350000 → 1_400_000 /kg (above typical max)
    p1 = db_session.get(Product, 1)
    p2 = db_session.get(Product, 2)
    p3 = db_session.get(Product, 3)
    p4 = db_session.get(Product, 4)
    assert all(x is not None for x in (p1, p2, p3, p4))

    p1.weight = 500
    p2.weight = 500
    p3.weight = None
    p4.weight = 250
    db_session.commit()

    try:
        repo = ProductRepository(db_session)
        # Cap under 400k/kg: only product 2 (360k/kg) qualifies among weighted coffee
        result = repo.search_products_detailed(
            ProductSearchParams(
                category="cà phê",
                max_price=400000,
                price_unit="PER_KG",
                in_stock=False,
                limit=10,
            )
        )
        returned_ids = {p.id for p in result.products}
        assert 3 not in returned_ids, "missing weight must be excluded for PER_KG"
        assert 1 not in returned_ids, "478k/kg exceeds max 400k/kg"
        assert 4 not in returned_ids, "1.4M/kg exceeds max 400k/kg"
        assert 2 in returned_ids

        for card in result.products:
            assert card.weight is not None and card.weight > 0
            expected_ppk = card.effective_price / (card.weight / 1000.0)
            assert card.price_per_kg is not None
            assert abs(card.price_per_kg - expected_ppk) < 1.0
            assert card.price_per_kg <= 400000
            assert card.price_basis == "per_kg"

        # Without max, weighted products still exclude null weight
        all_per_kg = repo.search_products_detailed(
            ProductSearchParams(
                category="cà phê",
                price_unit="PER_KG",
                in_stock=False,
                limit=10,
            )
        )
        all_ids = {p.id for p in all_per_kg.products}
        assert 3 not in all_ids
        assert {1, 2, 4}.issubset(all_ids)
    finally:
        # Restore seed state (weights unset) so other tests stay deterministic
        for pid in (1, 2, 3, 4):
            prod = db_session.get(Product, pid)
            if prod is not None:
                prod.weight = None
        db_session.commit()


def test_package_price_filter_still_works(db_session: Session):
    """PACKAGE max_price filters on effective package price (existing behavior)."""
    repo = ProductRepository(db_session)
    result = repo.search_products_detailed(
        ProductSearchParams(
            category="cà phê",
            max_price=240000,
            price_unit="PACKAGE",
            in_stock=False,
            limit=10,
        )
    )
    assert result.products
    for p in result.products:
        assert p.effective_price <= 240000
        assert p.price_basis == "package"
        # Arabica Cầu Đất: sale 239k under 240k package cap
    ids = {p.id for p in result.products}
    assert 1 in ids
    # Specialty package effective 350k must not pass 240k package filter
    assert 4 not in ids


def test_kind_phrase_in_seeded_name_isolates_hits(db_session: Session):
    """Unresolved kind that appears as a whole token in a name returns only those rows."""
    extra = Product(
        id=9001,
        category_id=5,
        brand_id=1,
        name="Gạo nếp demo 750g",
        slug="gao-nep-demo-750g",
        price=120000,
        sale_price=None,
        origin="Yên Bái",
        status="ACTIVE",
        weight=750,
    )
    db_session.add(extra)
    db_session.commit()
    try:
        repo = ProductRepository(db_session)
        result = repo.search_products_detailed(
            ProductSearchParams(category="gạo", in_stock=False, limit=10)
        )
        assert result.products
        assert all(kind_token_ok(p.name, "gạo") for p in result.products)
        assert any(p.id == 9001 for p in result.products)
        assert all("cà phê" not in (p.name or "").lower() for p in result.products)
        assert all(p.category_name for p in result.products)
    finally:
        db_session.delete(extra)
        db_session.commit()


def kind_token_ok(name: str, kind: str) -> bool:
    from backend.app.repositories.product_repository import kind_token_matches_name

    return kind_token_matches_name(kind, name)


def test_kind_does_not_substring_match_shorter_category(db_session: Session):
    """'trái cây' must not resolve to 'Trà' via the 'tra' substring."""
    repo = ProductRepository(db_session)
    cid, ok = repo.resolve_category_id("trái cây")
    tea_id, tea_ok = repo.resolve_category_id("trà")
    assert tea_ok and tea_id is not None
    if ok:
        assert cid != tea_id
    result = repo.search_products_detailed(
        ProductSearchParams(category="trái cây", in_stock=False, limit=10)
    )
    if result.products:
        for p in result.products:
            assert "trái cây" in (p.name or "").lower()
    else:
        assert result.empty_reason == "UNKNOWN_KIND"


def test_empty_parent_category_does_not_win(db_session: Session):
    parent = Category(id=90, name="Nông sản", slug="nong-san-parent", status="ACTIVE")
    db_session.add(parent)
    db_session.commit()
    try:
        repo = ProductRepository(db_session)
        cid, ok = repo.resolve_category_id("nông sản chế biến")
        assert cid != 90
        # Empty parent must never be selected
        live_id, live_ok = repo.resolve_category_id("nông sản")
        if live_ok:
            assert live_id != 90
    finally:
        db_session.delete(parent)
        db_session.commit()


def test_resolve_by_name_rejects_stopword_overlap(db_session: Session):
    repo = ProductRepository(db_session)
    assert repo.resolve_by_name("nhân") is None
    assert repo.resolve_by_name("giá") is None
    cashew = repo.resolve_by_name("hạt điều")
    assert cashew is not None
    assert "điều" in cashew.name.lower()


def test_usage_and_info_leave_knowledge():
    usage = normalize_extraction(
        "Hạt macca nào phù hợp làm sữa hạt?",
        IntentExtractionResult(intent=IntentEnum.KNOWLEDGE),
    )
    assert usage.intent == IntentEnum.PRODUCT_RECOMMENDATION
    assert usage.category == "hạt"

    info = normalize_extraction(
        "Thông tin về hạt macca rang",
        IntentExtractionResult(intent=IntentEnum.KNOWLEDGE),
    )
    assert info.intent in (IntentEnum.PRODUCT_DETAIL, IntentEnum.PRODUCT_SEARCH)
    assert info.intent != IntentEnum.KNOWLEDGE

    howto = normalize_extraction(
        "Cách bảo quản cà phê đúng cách",
        IntentExtractionResult(intent=IntentEnum.KNOWLEDGE),
    )
    assert howto.intent == IntentEnum.KNOWLEDGE


def test_spoken_price_and_tro_xuong():
    lo, hi = parse_price_bounds("dưới hai trăm nghìn")
    assert lo is None
    assert hi == 200000
    lo, hi = parse_price_bounds("từ 100k trở xuống")
    assert lo is None
    assert hi == 100000


def test_compare_without_two_names_falls_back_to_search(db_session: Session):
    svc = ChatbotService(session=db_session, llm=None)
    extracted = IntentExtractionResult(
        intent=IntentEnum.PRODUCT_COMPARE,
        category="cà phê",
        max_price=240000,
        product_names=[],
    )

    async def _run():
        return await svc._handle_product_compare(extracted)

    import asyncio

    products, context = asyncio.run(_run())
    assert products
    assert "two sku" in context.lower() or "constrained search" in context.lower()
    for p in products:
        assert p.effective_price <= 240000


def test_prompts_loaded_in_english_require_vietnamese_replies():
    assert "intent classifier" in INTENT_EXTRACTION_SYSTEM_PROMPT.lower()
    assert "Reply to the customer in natural, polite Vietnamese" in ANSWER_SYSTEM_PROMPT
    assert "Never answer the customer in English" in ANSWER_SYSTEM_PROMPT
    # Extraction prompt must not instruct a customer-facing English reply
    assert "Do not answer the customer" in INTENT_EXTRACTION_SYSTEM_PROMPT
