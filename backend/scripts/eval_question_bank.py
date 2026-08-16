"""Evaluate chatbot against bang_cau_hoi_nong_san.csv question bank.

Usage:
  python -m backend.scripts.eval_question_bank
  python -m backend.scripts.eval_question_bank --csv PATH --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.chatbot.llm import detect_price_unit, parse_price_bounds
from backend.app.chatbot.service import ChatbotService
from backend.app.core.database import get_db_context
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.chat import ChatRequest
from backend.app.schemas.product import ProductSearchParams

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("eval")
logger.setLevel(logging.INFO)

DEFAULT_CSV = Path.home() / "Downloads" / "bang_cau_hoi_nong_san.csv"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "eval_question_bank_report.json"


def parse_price_condition(cond: str) -> Tuple[Optional[float], Optional[float], str]:
    """Return (min_price, max_price, op_label) from CSV price_condition."""
    text = (cond or "").strip().replace(" ", "")
    if not text:
        return None, None, "none"

    m = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1)), float(m.group(2)), "range"

    m = re.fullmatch(r"<=(\d+(?:\.\d+)?)", text)
    if m:
        return None, float(m.group(1)), "lte"

    m = re.fullmatch(r"<(\d+(?:\.\d+)?)", text)
    if m:
        return None, float(m.group(1)) - 0.01, "lt"

    m = re.fullmatch(r">=(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1)), None, "ge"

    m = re.fullmatch(r">(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1)) + 0.01, None, "gt"

    m = re.fullmatch(r"(\d+(?:\.\d+)?)", text)
    if m:
        # bare number treated as max budget
        return None, float(m.group(1)), "eq_as_max"

    return None, None, f"unparsed:{text}"


def category_tokens(category: str) -> List[str]:
    cat = (category or "").strip().lower()
    if not cat:
        return []
    aliases = {
        "cà phê": ["cà phê", "cafe", "coffee", "robusta", "arabica", "phin"],
        "trà": ["trà", "chè", "tea", "oolong", "shan"],
        "gạo": ["gạo", "gao", "rice", "st25", "st24"],
        "hạt": ["hạt", "hat", "điều", "mắc ca", "macca", "hạnh nhân", "óc chó", "hạt dinh dưỡng"],
        "đậu": ["đậu", "dau", "bean"],
        "trái cây": ["trái cây", "trai cay", "xoài", "mít", "chuối"],
        "rau củ": ["rau củ"],
        "nông sản chế biến": ["chế biến", "nông sản chế biến"],
    }
    return aliases.get(cat, [cat])


def _category_name_aliases(category: str) -> List[str]:
    """How expected kind maps onto live catalog category names."""
    cat = (category or "").strip().lower()
    mapping = {
        "cà phê": ["cà phê", "cafe", "coffee"],
        "trà": ["trà", "chè", "tea"],
        "hạt": ["hạt", "hat"],
        "gạo": ["gạo"],
        "đậu": ["đậu"],
        "trái cây": ["trái cây"],
        "rau củ": ["rau", "rau củ"],
        "nông sản chế biến": ["chế biến"],
    }
    return mapping.get(cat, [cat] if cat else [])


def product_matches_category(
    name: str,
    category: str,
    category_name: Optional[str] = None,
) -> bool:
    if not category:
        return True
    cat_name = (category_name or "").lower()
    if cat_name:
        if any(tok in cat_name for tok in _category_name_aliases(category)):
            return True
    name_l = (name or "").lower()
    tokens = category_tokens(category)
    return any(t in name_l for t in tokens)


def product_matches_price(price: float, min_p: Optional[float], max_p: Optional[float]) -> bool:
    if min_p is not None and price < min_p:
        return False
    if max_p is not None and price > max_p:
        return False
    return True


def product_matches_origin(name: str, origin_field: str, product_origin: Optional[str], answer: str) -> bool:
    origin = (origin_field or "").strip().lower()
    if not origin:
        return True
    hay = f"{name} {product_origin or ''} {answer}".lower()
    # split multi-word origins
    parts = [p.strip() for p in re.split(r"[,/]| và ", origin) if p.strip()]
    return any(p in hay for p in parts)


@dataclass
class CaseResult:
    question_id: str
    question: str
    expected_category: str
    expected_price_condition: str
    expected_origin: str
    expected_application: str
    csv_intent: str
    chat_intent: str
    products: List[Dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None
    # scoring
    intent_ok: bool = False
    has_products: bool = False
    products_category_ok: Optional[bool] = None
    products_price_ok: Optional[bool] = None
    products_origin_ok: Optional[bool] = None
    answer_not_empty: bool = False
    answer_denies_with_products: bool = False
    honest_empty: bool = False
    score: float = 0.0
    grade: str = "F"
    notes: List[str] = field(default_factory=list)


def _card_price_for_unit(product: Dict[str, Any], per_kg: bool) -> float:
    if per_kg:
        ppk = product.get("price_per_kg")
        if ppk is not None:
            try:
                return float(ppk)
            except (TypeError, ValueError):
                pass
    return float(product.get("effective_price") or product.get("price") or 0)


def probe_catalog_hits(session, row: Dict[str, str], question: str) -> int:
    """Independent MySQL probe using the same repository as the chatbot."""
    csv_min, csv_max, _op = parse_price_condition(row.get("price_condition") or "")
    q_min, q_max = parse_price_bounds(question)
    # Prefer bounds parsed from the question (CSV columns are sometimes stale)
    min_p = q_min if q_min is not None else csv_min
    max_p = q_max if q_max is not None else csv_max
    category = (row.get("category") or "").strip() or None
    origin = (row.get("origin") or "").strip() or None
    if not category and not origin and min_p is None and max_p is None:
        return -1  # no constraints to verify
    repo = ProductRepository(session)
    result = repo.search_products_detailed(
        ProductSearchParams(
            category=category,
            origin=origin,
            min_price=min_p,
            max_price=max_p,
            price_unit=detect_price_unit(question),
            in_stock=False,
            limit=10,
        )
    )
    return len(result.products)


def grade_case(
    row: Dict[str, str],
    resp: Dict[str, Any],
    duration_ms: float,
    error: Optional[str] = None,
    catalog_hits: Optional[int] = None,
) -> CaseResult:
    min_p, max_p, _op = parse_price_condition(row.get("price_condition") or "")
    category = (row.get("category") or "").strip()
    origin = (row.get("origin") or "").strip()
    application = (row.get("application") or "").strip()

    result = CaseResult(
        question_id=row["question_id"],
        question=row["question"],
        expected_category=category,
        expected_price_condition=row.get("price_condition") or "",
        expected_origin=origin,
        expected_application=application,
        csv_intent=row.get("intent") or "",
        chat_intent=resp.get("intent") or "",
        products=resp.get("products") or [],
        answer=resp.get("answer") or "",
        duration_ms=duration_ms,
        error=error,
    )

    if error:
        result.notes.append(f"error: {error}")
        result.grade = "F"
        result.score = 0.0
        return result

    result.answer_not_empty = bool(result.answer.strip())
    result.has_products = len(result.products) > 0

    # Intent: all CSV cases expect product search / filter style
    search_intents = {
        "PRODUCT_SEARCH",
        "PRODUCT_RECOMMENDATION",
        "PRODUCT_DETAIL",
        "PRODUCT_COMPARE",
    }
    result.intent_ok = result.chat_intent in search_intents

    per_kg = detect_price_unit(result.question) == "PER_KG"

    # Category / price / origin checks on returned products
    if result.products:
        cat_hits = [
            product_matches_category(
                p.get("name") or "",
                category,
                p.get("category_name"),
            )
            for p in result.products
        ]
        result.products_category_ok = all(cat_hits) if category else True
        if category and not result.products_category_ok:
            bad = [p.get("name") for p, ok in zip(result.products, cat_hits) if not ok]
            result.notes.append(f"category_mismatch: {bad[:3]}")

        if min_p is not None or max_p is not None:
            price_hits = [
                product_matches_price(_card_price_for_unit(p, per_kg), min_p, max_p)
                for p in result.products
            ]
            result.products_price_ok = all(price_hits)
            if not result.products_price_ok:
                bad = [
                    f"{p.get('name')}={_card_price_for_unit(p, per_kg)}"
                    for p, ok in zip(result.products, price_hits)
                    if not ok
                ]
                label = "price_mismatch_per_kg" if per_kg else "price_mismatch_package"
                result.notes.append(f"{label}: {bad[:3]}")
            if per_kg and any(p.get("price_per_kg") is None for p in result.products):
                result.notes.append("unit_caveat: per-kg question but some cards lack price_per_kg")
        else:
            result.products_price_ok = True

        origin_hits = [
            product_matches_origin(
                p.get("name") or "",
                origin,
                p.get("origin"),
                result.answer,
            )
            for p in result.products
        ]
        result.products_origin_ok = all(origin_hits) if origin else True
        if origin and not result.products_origin_ok:
            result.notes.append("origin_mismatch_or_missing_in_product_cards")
    else:
        constrained = bool(category or origin or min_p is not None or max_p is not None)
        if constrained and catalog_hits == 0:
            result.honest_empty = True
            result.products_category_ok = True if category else None
            result.products_price_ok = True if (min_p is not None or max_p is not None) else None
            result.products_origin_ok = True if origin else None
            result.notes.append("honest_empty_catalog_verified")
        else:
            result.products_category_ok = None
            result.products_price_ok = None
            result.products_origin_ok = None
            if constrained:
                if catalog_hits and catalog_hits > 0:
                    result.notes.append(f"false_empty_catalog_has_{catalog_hits}")
                else:
                    result.notes.append("no_products_returned")

    lower = result.answer.lower()
    denial = any(
        x in lower
        for x in (
            "chưa có dữ liệu",
            "chưa có thông tin",
            "không có sản phẩm",
            "chưa có sản phẩm",
            "không tìm thấy",
        )
    )
    result.answer_denies_with_products = bool(result.has_products and denial)
    if result.answer_denies_with_products:
        result.notes.append("answer_denies_despite_products")

    # Scoring rubric (0-100)
    score = 0.0
    if result.intent_ok:
        score += 20
    if result.answer_not_empty:
        score += 15
    if result.has_products or result.honest_empty:
        score += 25
    else:
        score += 5
    if result.products_category_ok is True:
        score += 20
    elif result.products_category_ok is None and not category:
        score += 10
    if result.products_price_ok is True:
        score += 15
    elif result.products_price_ok is None and not (min_p or max_p):
        score += 8
    if result.products_origin_ok is True:
        score += 5
    elif result.products_origin_ok is None and not origin:
        score += 3
    if result.answer_denies_with_products:
        score -= 20
    result.score = max(0.0, min(100.0, score))

    if result.score >= 85:
        result.grade = "A"
    elif result.score >= 70:
        result.grade = "B"
    elif result.score >= 55:
        result.grade = "C"
    elif result.score >= 40:
        result.grade = "D"
    else:
        result.grade = "F"

    return result


async def run_one(service: ChatbotService, question: str) -> Tuple[Dict[str, Any], float, Optional[str]]:
    start = time.perf_counter()
    try:
        resp = await service.handle_chat(ChatRequest(message=question, session_id=None))
        duration = (time.perf_counter() - start) * 1000
        payload = {
            "intent": resp.intent,
            "answer": resp.answer,
            "products": [p.model_dump() for p in resp.products],
            "metadata": resp.metadata,
            "session_id": resp.session_id,
        }
        return payload, duration, None
    except Exception as exc:
        duration = (time.perf_counter() - start) * 1000
        return {}, duration, str(exc)


async def run_eval(csv_path: Path, limit: Optional[int] = None, offset: int = 0) -> Dict[str, Any]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    results: List[CaseResult] = []
    with get_db_context() as session:
        service = ChatbotService(session=session)
        for i, row in enumerate(rows, 1):
            qid = row["question_id"]
            logger.info("[%s/%s] %s %s", i, len(rows), qid, row["question"][:80])
            resp, duration, err = await run_one(service, row["question"])
            catalog_hits = None
            if not err:
                try:
                    catalog_hits = probe_catalog_hits(session, row, row["question"])
                except Exception as probe_exc:
                    logger.warning("catalog probe failed for %s: %s", row.get("question_id"), probe_exc)
                    catalog_hits = None
            case = grade_case(row, resp, duration, err, catalog_hits=catalog_hits)
            results.append(case)
            logger.info(
                "  -> grade=%s score=%.0f intent=%s products=%d ms=%.0f",
                case.grade,
                case.score,
                case.chat_intent,
                len(case.products),
                case.duration_ms,
            )

    # Aggregate
    n = len(results) or 1
    by_grade = {}
    for r in results:
        by_grade[r.grade] = by_grade.get(r.grade, 0) + 1

    avg_score = sum(r.score for r in results) / n
    intent_acc = sum(1 for r in results if r.intent_ok) / n
    product_return_rate = sum(1 for r in results if r.has_products) / n
    cat_ok = [r for r in results if r.products_category_ok is not None]
    price_ok = [r for r in results if r.products_price_ok is not None]
    denial_bad = sum(1 for r in results if r.answer_denies_with_products)

    failures = [r for r in results if r.grade in {"D", "F"}]
    top = sorted(results, key=lambda x: x.score, reverse=True)[:10]
    bottom = sorted(results, key=lambda x: x.score)[:15]

    # Category coverage gaps from notes
    no_product_ids = [r.question_id for r in results if "no_products_returned" in r.notes]
    cat_mismatch_ids = [r.question_id for r in results if any(n.startswith("category_mismatch") for n in r.notes)]
    price_mismatch_ids = [r.question_id for r in results if any(n.startswith("price_mismatch") for n in r.notes)]

    # Per-category stats
    by_category: Dict[str, Dict[str, Any]] = {}
    for r in results:
        key = r.expected_category or "(none)"
        bucket = by_category.setdefault(key, {"n": 0, "scores": [], "with_products": 0})
        bucket["n"] += 1
        bucket["scores"].append(r.score)
        if r.has_products:
            bucket["with_products"] += 1
    cat_summary = {
        k: {
            "n": v["n"],
            "avg_score": round(sum(v["scores"]) / v["n"], 1),
            "with_products_rate": round(v["with_products"] / v["n"], 3),
        }
        for k, v in sorted(by_category.items(), key=lambda kv: -kv[1]["n"])
    }

    report = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "csv": str(csv_path),
            "total_questions": len(results),
            "notes": [
                "Câu hỏi có tín hiệu /kg được chấm theo price_per_kg khi card có trường này.",
                "Category match dùng category_name trên card hoặc token trên tên — không hardcode question id.",
                "Empty được cộng điểm đầy đủ chỉ khi probe catalog độc lập cũng không có hàng khớp (honest_empty).",
            ],
        },
        "summary": {
            "avg_score": round(avg_score, 2),
            "grade_distribution": by_grade,
            "intent_accuracy": round(intent_acc, 3),
            "product_return_rate": round(product_return_rate, 3),
            "category_match_rate": round(
                sum(1 for r in cat_ok if r.products_category_ok) / len(cat_ok), 3
            )
            if cat_ok
            else None,
            "price_match_rate_package": round(
                sum(1 for r in price_ok if r.products_price_ok) / len(price_ok), 3
            )
            if price_ok
            else None,
            "answer_denies_with_products": denial_bad,
            "avg_latency_ms": round(sum(r.duration_ms for r in results) / n, 1),
            "no_products_count": len(no_product_ids),
            "honest_empty_count": sum(1 for r in results if r.honest_empty),
            "category_mismatch_count": len(cat_mismatch_ids),
            "price_mismatch_count": len(price_mismatch_ids),
        },
        "by_category": cat_summary,
        "top_cases": [asdict(r) for r in top],
        "bottom_cases": [asdict(r) for r in bottom],
        "failure_ids": [r.question_id for r in failures],
        "cases": [asdict(r) for r in results],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}")
        return 1

    report = asyncio.run(run_eval(args.csv, limit=args.limit, offset=args.offset))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md_path = args.out.with_suffix(".md")
    s = report["summary"]
    lines = [
        "# Báo cáo đánh giá chatbot — Bảng câu hỏi nông sản",
        "",
        f"- Thời điểm: {report['meta']['generated_at']}",
        f"- Số câu: **{report['meta']['total_questions']}**",
        f"- Điểm TB: **{s['avg_score']}/100**",
        f"- Phân bố grade: `{s['grade_distribution']}`",
        f"- Intent accuracy: **{s['intent_accuracy']*100:.1f}%**",
        f"- Tỷ lệ trả về sản phẩm: **{s['product_return_rate']*100:.1f}%**",
        f"- Category match (khi có SP): **{(s['category_match_rate'] or 0)*100:.1f}%**",
        f"- Price match package (khi có SP+điều kiện giá): **{(s['price_match_rate_package'] or 0)*100:.1f}%**",
        f"- Trả lời phủ nhận dù có SP: **{s['answer_denies_with_products']}**",
        f"- Honest empty (catalog xác nhận): **{s.get('honest_empty_count', 0)}**",
        f"- Latency TB: **{s['avg_latency_ms']:.0f} ms**",
        "",
        "## Theo danh mục",
        "",
        "| Category | N | Avg score | Product return |",
        "|---|---:|---:|---:|",
    ]
    for cat, st in report["by_category"].items():
        lines.append(
            f"| {cat} | {st['n']} | {st['avg_score']} | {st['with_products_rate']*100:.0f}% |"
        )
    lines += [
        "",
        "## Top 10 tốt nhất",
        "",
    ]
    for r in report["top_cases"]:
        lines.append(
            f"- **{r['question_id']}** ({r['grade']}/{r['score']:.0f}): {r['question'][:80]} → {len(r['products'])} SP, intent={r['chat_intent']}"
        )
    lines += ["", "## 15 case yếu nhất", ""]
    for r in report["bottom_cases"]:
        notes = "; ".join(r["notes"][:2]) if r["notes"] else ""
        lines.append(
            f"- **{r['question_id']}** ({r['grade']}/{r['score']:.0f}): {r['question'][:80]} | {notes}"
        )
    lines += [
        "",
        "## Lưu ý đánh giá",
        "",
    ]
    for n in report["meta"]["notes"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append(f"Chi tiết JSON: `{args.out}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {args.out}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
