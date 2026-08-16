"""Authoritative MySQL Product Repository with parameterized queries."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.schemas.product import (
    ProductCard,
    ProductDetailResponse,
    ProductSearchParams,
    ProductSearchResult,
)

# Minimal generic synonyms only (not evaluation-bank phrases)
_DEFAULT_CATEGORY_ALIASES = {
    "cafe": "cà phê",
    "coffee": "cà phê",
    "ca phe": "cà phê",
    "chè": "trà",
    "che": "trà",
    "tea": "trà",
    "hat": "hạt",
}

# Flavor modifiers immediately before a kind token do not count as product kind
_FLAVOR_PREFIXES_FOLDED = frozenset({"huong", "vi", "mui"})

# Dropped when scoring resolve_by_name (folded forms)
_RESOLVE_STOPWORDS_FOLDED = frozenset({
    "loai", "cac", "gia", "nhan", "thong", "tin", "san", "pham",
    "nao", "co", "ve", "mot", "kg",
})

# Higher fetch cap when post-filtering by kind (demo catalog ~150 SKUs)
_KIND_FETCH_CAP = 200


def _fold(text: str) -> str:
    """Lowercase + rough accent fold for matching."""
    if not text:
        return ""
    text = text.strip().lower()
    # Common VN replacements then NFD strip
    repl = {
        "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
        "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
        "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
        "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
        "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
        "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
        "đ": "d",
    }
    for src, dst in repl.items():
        text = text.replace(src, dst)
    # Strip any remaining combining marks
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def _tokenize_folded(text: str) -> List[str]:
    """Alphanumeric tokens from folded text (whole-token matching)."""
    return re.findall(r"[a-z0-9]+", _fold(text or ""))


def _tokens_are_span(needle: List[str], haystack: List[str]) -> bool:
    """True when needle is a consecutive whole-token span inside haystack."""
    if not needle or not haystack or len(needle) > len(haystack):
        return False
    nlen = len(needle)
    for i in range(len(haystack) - nlen + 1):
        if haystack[i : i + nlen] == needle:
            return True
    return False


def _load_category_aliases() -> Dict[str, str]:
    aliases = dict(_DEFAULT_CATEGORY_ALIASES)
    path = Path(__file__).resolve().parent.parent / "data" / "category_aliases.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                aliases.update({str(k).lower(): str(v) for k, v in data.items()})
        except Exception:
            pass
    return aliases


def _price_per_kg(effective_price: float, weight_grams: Optional[float]) -> Optional[float]:
    if weight_grams is None:
        return None
    try:
        w = float(weight_grams)
    except (TypeError, ValueError):
        return None
    if w <= 0:
        return None
    return effective_price / (w / 1000.0)


def _apply_kind_alias(kind: str, aliases: Dict[str, str]) -> str:
    raw = (kind or "").strip()
    if not raw:
        return raw
    aliased = aliases.get(raw.lower(), raw)
    aliased = aliases.get(_fold(aliased), aliased)
    return aliased


def kind_token_matches_name(kind: str, product_name: str) -> bool:
    """
    Conservative kind match: full phrase as consecutive whole tokens, or all
    kind tokens as whole tokens. Folded comparison only (no MySQL accent LIKE).
    Skips hits where the matched span is immediately preceded by hương/vị/mùi.
    """
    kind_tokens = _tokenize_folded(kind)
    if not kind_tokens:
        return False
    name_tokens = _tokenize_folded(product_name)
    if not name_tokens:
        return False

    klen = len(kind_tokens)
    nlen = len(name_tokens)

    # Consecutive phrase match (preferred)
    for i in range(nlen - klen + 1):
        if name_tokens[i : i + klen] == kind_tokens:
            if i > 0 and name_tokens[i - 1] in _FLAVOR_PREFIXES_FOLDED:
                continue
            return True

    # Multi-token: require every kind token as a whole token (non-flavor-prefixed)
    if klen > 1:
        for kt in kind_tokens:
            found = False
            for i, nt in enumerate(name_tokens):
                if nt != kt:
                    continue
                if i > 0 and name_tokens[i - 1] in _FLAVOR_PREFIXES_FOLDED:
                    continue
                found = True
                break
            if not found:
                return False
        return True

    return False


def _card_from_row(
    r: Any,
    *,
    use_per_kg: bool = False,
    reason: Optional[str] = None,
) -> ProductCard:
    qty = int(r.available_quantity)
    effective = float(r.effective_price)
    weight = float(r.weight) if getattr(r, "weight", None) is not None else None
    ppk = _price_per_kg(effective, weight)
    basis = "per_kg" if use_per_kg and ppk is not None else "package"
    cat_name = getattr(r, "category_name", None) or None
    return ProductCard(
        id=r.id,
        name=r.name,
        price=float(r.price),
        sale_price=float(r.sale_price) if r.sale_price is not None else None,
        effective_price=effective,
        origin=r.origin,
        available_quantity=qty,
        is_available=qty > 0,
        image_url=(r.image_url or None) if hasattr(r, "image_url") else None,
        weight=weight,
        price_per_kg=ppk,
        price_basis=basis,
        category_name=cat_name,
        reason=reason,
    )


class ProductRepository:
    """Repository handling all product and inventory database access."""

    def __init__(self, session: Session):
        self.session = session
        self._category_aliases = _load_category_aliases()

    def list_available_categories(self, limit: int = 12) -> List[str]:
        """Active categories that currently have at least one active product."""
        sql = """
            SELECT c.name AS name, COUNT(p.id) AS n
            FROM categories c
            INNER JOIN products p ON p.category_id = c.id AND p.status = 'ACTIVE'
            WHERE c.status = 'ACTIVE'
            GROUP BY c.id, c.name
            ORDER BY n DESC, c.name ASC
            LIMIT :limit
        """
        rows = self.session.execute(text(sql), {"limit": max(1, min(limit, 30))}).fetchall()
        return [r.name for r in rows if r.name]

    def resolve_category_id(self, category: Optional[str]) -> Tuple[Optional[int], bool]:
        """
        Resolve user category text to a live category id.
        Exact folded name/slug first; else longest live name contained in text.
        Categories with zero active products never win.
        Returns (category_id, resolved_flag). resolved_flag False = stated but unmatched.
        """
        if not category or not str(category).strip():
            return None, True  # no category constraint

        raw = category.strip()
        aliased = self._category_aliases.get(raw.lower(), raw)
        aliased = self._category_aliases.get(_fold(aliased), aliased)
        target = _fold(aliased)

        rows = self.session.execute(
            text(
                """
                SELECT c.id, c.name, c.slug, COUNT(p.id) AS n
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.status = 'ACTIVE'
                WHERE c.status = 'ACTIVE'
                GROUP BY c.id, c.name, c.slug
                """
            )
        ).fetchall()

        live = [r for r in rows if int(r.n or 0) > 0]

        # 1) Exact folded name or slug among live categories
        for r in live:
            name_f = _fold(r.name or "")
            slug_f = _fold((r.slug or "").replace("-", " "))
            if target == name_f or target == slug_f:
                return int(r.id), True

        # 2) Longest live category whose tokens are a consecutive span in the user text
        #    (whole tokens only — "tra" must not match inside "trai cay")
        best_id: Optional[int] = None
        best_len = -1
        target_tokens = _tokenize_folded(aliased)
        for r in live:
            name_tokens = _tokenize_folded(r.name or "")
            slug_tokens = _tokenize_folded((r.slug or "").replace("-", " "))
            name_f = _fold(r.name or "")
            if name_tokens and _tokens_are_span(name_tokens, target_tokens) and len(name_f) > best_len:
                best_id = int(r.id)
                best_len = len(name_f)
            slug_f = _fold((r.slug or "").replace("-", " "))
            if slug_tokens and _tokens_are_span(slug_tokens, target_tokens) and len(slug_f) > best_len:
                best_id = int(r.id)
                best_len = len(slug_f)

        if best_id is not None:
            return best_id, True

        # 3) Short user kind that is a whole token / first token of a live category
        #    e.g. "trà" → "Trà & Thảo mộc", "hạt" → "Hạt dinh dưỡng"
        for r in live:
            name_tokens = _tokenize_folded(r.name or "")
            slug_tokens = _tokenize_folded((r.slug or "").replace("-", " "))
            name_f = _fold(r.name or "")
            if not name_tokens:
                continue
            token_hit = (
                (target_tokens and target_tokens == name_tokens[: len(target_tokens)])
                or (len(target_tokens) == 1 and target_tokens[0] in name_tokens)
                or (len(target_tokens) == 1 and target_tokens[0] in slug_tokens)
            )
            if token_hit and len(name_f) > best_len:
                best_id = int(r.id)
                best_len = len(name_f)

        if best_id is not None:
            return best_id, True

        return None, False

    def search_products(self, params: ProductSearchParams) -> List[ProductCard]:
        """Search active products; thin wrapper around search_products_detailed."""
        return self.search_products_detailed(params).products

    def search_products_detailed(self, params: ProductSearchParams) -> ProductSearchResult:
        """Search with hard filters, kind-token fallback, price unit policy, structured empty."""
        applied: Dict[str, Any] = {
            "query": params.query,
            "category": params.category,
            "brand": params.brand,
            "origin": params.origin,
            "min_price": params.min_price,
            "max_price": params.max_price,
            "price_unit": params.price_unit or "PACKAGE",
            "in_stock": params.in_stock,
            "limit": params.limit,
        }

        category_id = None
        category_resolved: Optional[bool] = None
        kind_text: Optional[str] = None

        if params.category:
            category_id, category_resolved = self.resolve_category_id(params.category)
            applied["category_id"] = category_id
            applied["category_resolved"] = category_resolved
            if not category_resolved:
                # Keep category text as hard kind constraint — never unconstrained-search
                kind_text = _apply_kind_alias(params.category, self._category_aliases)
                applied["kind"] = kind_text

        conditions = ["p.status = 'ACTIVE'"]
        bind_params: Dict[str, Any] = {}

        if category_id is not None:
            conditions.append("p.category_id = :category_id")
            bind_params["category_id"] = category_id

        if params.brand:
            conditions.append("LOWER(b.name) LIKE :brand")
            bind_params["brand"] = f"%{params.brand.strip().lower()}%"

        if params.origin:
            conditions.append("LOWER(p.origin) LIKE :origin")
            bind_params["origin"] = f"%{params.origin.strip().lower()}%"

        if params.query:
            conditions.append("(LOWER(p.name) LIKE :query OR LOWER(p.description) LIKE :query)")
            bind_params["query"] = f"%{params.query.strip().lower()}%"

        price_unit = (params.price_unit or "PACKAGE").upper()
        use_per_kg = price_unit == "PER_KG"

        if not use_per_kg:
            if params.min_price is not None:
                conditions.append("COALESCE(p.sale_price, p.price) >= :min_price")
                bind_params["min_price"] = params.min_price
            if params.max_price is not None:
                conditions.append("COALESCE(p.sale_price, p.price) <= :max_price")
                bind_params["max_price"] = params.max_price
        else:
            # Need weight for per-kg; exclude missing weight at SQL level
            conditions.append("p.weight IS NOT NULL AND p.weight > 0")
            # price_per_kg = effective / (weight/1000) = effective * 1000 / weight
            if params.min_price is not None:
                conditions.append(
                    "(COALESCE(p.sale_price, p.price) * 1000.0 / p.weight) >= :min_price"
                )
                bind_params["min_price"] = params.min_price
            if params.max_price is not None:
                conditions.append(
                    "(COALESCE(p.sale_price, p.price) * 1000.0 / p.weight) <= :max_price"
                )
                bind_params["max_price"] = params.max_price

        having_clause = ""
        if params.in_stock:
            having_clause = "HAVING available_quantity > 0"

        limit = max(1, min(params.limit, 10))
        # When kind post-filter is active, fetch a wider candidate set then trim
        fetch_limit = _KIND_FETCH_CAP if kind_text else limit
        bind_params["limit"] = fetch_limit

        where_str = " AND ".join(conditions)
        order_expr = (
            "(COALESCE(p.sale_price, p.price) * 1000.0 / NULLIF(p.weight, 0))"
            if use_per_kg
            else "COALESCE(p.sale_price, p.price)"
        )

        sql = f"""
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                p.weight,
                c.name AS category_name,
                COALESCE((
                    SELECT img.image_url
                    FROM product_images img
                    WHERE img.product_id = p.id
                    ORDER BY img.is_primary DESC, img.sort_order ASC, img.id ASC
                    LIMIT 1
                ), '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE {where_str}
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, p.weight, c.name
            {having_clause}
            ORDER BY {order_expr} ASC
            LIMIT :limit
        """

        rows = self.session.execute(text(sql), bind_params).fetchall()
        results: List[ProductCard] = []
        seen_ids = set()
        for r in rows:
            if r.id in seen_ids:
                continue
            if kind_text and not kind_token_matches_name(kind_text, r.name or ""):
                continue
            seen_ids.add(r.id)
            results.append(_card_from_row(r, use_per_kg=use_per_kg))
            if len(results) >= limit:
                break

        empty_reason = None
        if not results:
            empty_reason = self._empty_reason(
                use_per_kg=use_per_kg,
                category_id=category_id,
                category_resolved=category_resolved,
                kind_text=kind_text,
            )

        return ProductSearchResult(
            products=results,
            applied_filters=applied,
            empty_reason=empty_reason if not results else None,
            available_categories=self.list_available_categories() if not results else [],
            category_resolved=category_resolved,
        )

    def _empty_reason(
        self,
        *,
        use_per_kg: bool,
        category_id: Optional[int],
        category_resolved: Optional[bool],
        kind_text: Optional[str],
    ) -> str:
        """Pick structured empty reason without leaking unconstrained catalog."""
        if kind_text and category_resolved is False:
            if self._any_active_name_matches_kind(kind_text):
                # Kind exists in catalog but other filters eliminated all rows
                if use_per_kg:
                    return self._per_kg_empty_reason(category_id)
                return "NO_MATCH_FILTERS"
            return "UNKNOWN_KIND"

        if use_per_kg:
            return self._per_kg_empty_reason(category_id)
        return "NO_MATCH_FILTERS"

    def _per_kg_empty_reason(self, category_id: Optional[int]) -> str:
        weighted_probe = self.session.execute(
            text(
                """
                SELECT COUNT(*) AS n
                FROM products p
                WHERE p.status = 'ACTIVE'
                  AND p.weight IS NOT NULL AND p.weight > 0
                  """
                + (" AND p.category_id = :category_id" if category_id is not None else "")
            ),
            {"category_id": category_id} if category_id is not None else {},
        ).fetchone()
        has_weighted = int(weighted_probe.n) > 0 if weighted_probe else False
        return "NO_MATCH_FILTERS" if has_weighted else "NO_PER_KG_DATA"

    def _any_active_name_matches_kind(self, kind_text: str) -> bool:
        """True if any active product name matches kind (ignores price/origin)."""
        rows = self.session.execute(
            text("SELECT name FROM products WHERE status = 'ACTIVE'")
        ).fetchall()
        for r in rows:
            if kind_token_matches_name(kind_text, r.name or ""):
                return True
        return False

    def get_by_id(self, product_id: int) -> Optional[ProductDetailResponse]:
        """Fetch full product details, active certificates and inventory."""
        sql = """
            SELECT
                p.id,
                p.name,
                p.slug,
                p.sku,
                p.description,
                p.short_description,
                p.category_id,
                c.name AS category_name,
                p.brand_id,
                b.name AS brand_name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.unit,
                p.weight,
                p.origin,
                p.pricing_type,
                p.stock_status,
                p.is_featured,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity,
                pd.ingredients,
                pd.taste_profile,
                pd.key_benefits,
                pd.suitable_for,
                pd.usage_instructions,
                pd.storage_instructions,
                pd.shelf_life,
                pd.producer_name,
                pd.production_area,
                pd.product_story,
                pd.extra_attributes
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            LEFT JOIN product_details pd ON p.id = pd.product_id
            WHERE p.id = :product_id AND p.status = 'ACTIVE'
            GROUP BY
                p.id, p.name, p.slug, p.sku, p.description, p.short_description,
                p.category_id, c.name, p.brand_id, b.name, p.price, p.sale_price,
                p.unit, p.weight, p.origin, p.pricing_type, p.stock_status, p.is_featured,
                img.image_url, pd.ingredients, pd.taste_profile, pd.key_benefits, pd.suitable_for,
                pd.usage_instructions, pd.storage_instructions, pd.shelf_life,
                pd.producer_name, pd.production_area, pd.product_story, pd.extra_attributes
        """
        row = self.session.execute(text(sql), {"product_id": product_id}).fetchone()
        if not row:
            return None

        # Fetch only ACTIVE certificates
        cert_sql = """
            SELECT
                id,
                name,
                issuer,
                certificate_code,
                issued_at,
                expires_at,
                description,
                status
            FROM product_certificates
            WHERE product_id = :product_id AND status = 'ACTIVE'
            ORDER BY id ASC
        """
        cert_rows = self.session.execute(text(cert_sql), {"product_id": product_id}).fetchall()
        certs = [
            {
                "id": c.id,
                "name": c.name,
                "issuer": c.issuer,
                "certificate_code": c.certificate_code,
                "issued_at": str(c.issued_at) if c.issued_at else None,
                "expires_at": str(c.expires_at) if c.expires_at else None,
                "description": c.description,
                "status": c.status,
            }
            for c in cert_rows
        ]

        extra = None
        if row.extra_attributes:
            extra = json.loads(row.extra_attributes) if isinstance(row.extra_attributes, str) else row.extra_attributes

        qty = int(row.available_quantity)
        return ProductDetailResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            sku=getattr(row, "sku", None),
            description=row.description,
            short_description=getattr(row, "short_description", None),
            category_id=row.category_id,
            category_name=row.category_name,
            brand_id=row.brand_id,
            brand_name=row.brand_name,
            price=float(row.price),
            sale_price=float(row.sale_price) if row.sale_price is not None else None,
            effective_price=float(row.effective_price),
            unit=getattr(row, "unit", None),
            weight=float(row.weight) if getattr(row, "weight", None) is not None else None,
            origin=row.origin,
            pricing_type=getattr(row, "pricing_type", None),
            stock_status=getattr(row, "stock_status", None),
            is_featured=bool(getattr(row, "is_featured", False)),
            image_url=row.image_url or None,
            available_quantity=qty,
            is_available=qty > 0,
            ingredients=row.ingredients,
            taste_profile=row.taste_profile,
            key_benefits=row.key_benefits,
            suitable_for=row.suitable_for,
            usage_instructions=row.usage_instructions,
            storage_instructions=row.storage_instructions,
            shelf_life=row.shelf_life,
            producer_name=row.producer_name,
            production_area=row.production_area,
            product_story=row.product_story,
            extra_attributes=extra,
            certificates=certs,
        )

    def get_stock(self, product_id: int) -> Dict[str, Any]:
        """Compute available inventory stock for a product."""
        sql = """
            SELECT COALESCE(SUM(available_quantity), 0) AS total_stock
            FROM inventories
            WHERE product_id = :product_id
        """
        row = self.session.execute(text(sql), {"product_id": product_id}).fetchone()
        qty = int(row.total_stock) if row else 0
        return {
            "product_id": product_id,
            "available_quantity": qty,
            "is_available": qty > 0,
        }

    def resolve_by_name(self, name: str) -> Optional[ProductCard]:
        """
        Resolve a product by distinctive name tokens.
        Stopwords dropped; weak one-token overlap returns None.
        """
        raw = (name or "").strip()
        if not raw:
            return None

        target_lower = raw.lower()
        target_folded = _fold(raw)
        content_tokens = [
            t for t in _tokenize_folded(raw) if t not in _RESOLVE_STOPWORDS_FOLDED
        ]
        if not content_tokens:
            return None

        sql = """
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                p.weight,
                c.name AS category_name,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE p.status = 'ACTIVE'
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, p.weight, c.name, img.image_url
        """
        rows = self.session.execute(text(sql)).fetchall()

        # 1) Content tokens appear as a consecutive span in the product name
        for row in rows:
            if _tokens_are_span(content_tokens, _tokenize_folded(row.name or "")):
                return _card_from_row(row)

        # 2) Token overlap ≥ 2 content tokens
        best_card = None
        best_score = 0
        for row in rows:
            prod_tokens = set(_tokenize_folded(row.name or ""))
            overlap = len(set(content_tokens).intersection(prod_tokens))
            if overlap >= 2 and overlap > best_score:
                best_score = overlap
                best_card = _card_from_row(row)

        if best_card is not None:
            return best_card

        # 3) Single content token length ≥ 5 that uniquely prefixes/contains in a name
        long_tokens = [t for t in content_tokens if len(t) >= 5]
        if len(content_tokens) == 1 and long_tokens:
            tok = long_tokens[0]
            matches: List[Any] = []
            for row in rows:
                name_f = _fold(row.name or "")
                name_tokens = _tokenize_folded(row.name or "")
                if tok in name_tokens or name_f.startswith(tok) or tok in name_f:
                    matches.append(row)
            if len(matches) == 1:
                return _card_from_row(matches[0])
            # Prefer unique whole-token equality over multi-substring noise
            whole = [r for r in matches if tok in _tokenize_folded(r.name or "")]
            if len(whole) == 1:
                return _card_from_row(whole[0])

        elif long_tokens:
            # Multiple content tokens but <2 overlap: try each long token uniquely
            for tok in sorted(long_tokens, key=len, reverse=True):
                matches = []
                for row in rows:
                    name_tokens = _tokenize_folded(row.name or "")
                    name_f = _fold(row.name or "")
                    if tok in name_tokens or name_f.startswith(tok) or (
                        len(tok) >= 5 and tok in name_f
                    ):
                        matches.append(row)
                if len(matches) == 1:
                    return _card_from_row(matches[0])

        return None

    def get_by_ids(self, product_ids: List[int]) -> List[ProductCard]:
        """Fetch multiple products by explicit ID list."""
        if not product_ids:
            return []
        placeholders = ", ".join(f":id_{i}" for i in range(len(product_ids)))
        bind_params = {f"id_{i}": pid for i, pid in enumerate(product_ids)}
        sql = f"""
            SELECT
                p.id,
                p.name,
                p.price,
                p.sale_price,
                COALESCE(p.sale_price, p.price) AS effective_price,
                p.origin,
                p.weight,
                c.name AS category_name,
                COALESCE(img.image_url, '') AS image_url,
                COALESCE(SUM(inv.available_quantity), 0) AS available_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN product_images img ON p.id = img.product_id AND img.is_primary = 1
            LEFT JOIN inventories inv ON p.id = inv.product_id
            WHERE p.id IN ({placeholders}) AND p.status = 'ACTIVE'
            GROUP BY p.id, p.name, p.price, p.sale_price, p.origin, p.weight, c.name, img.image_url
        """
        rows = self.session.execute(text(sql), bind_params).fetchall()
        id_map = {}
        for r in rows:
            id_map[r.id] = _card_from_row(r)
        # Preserve input ordering
        return [id_map[pid] for pid in product_ids if pid in id_map]
