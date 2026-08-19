"""Coupon / voucher API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import get_db

router = APIRouter()


@router.get(
    "/coupons",
    response_model=List[Dict[str, Any]],
    summary="List active vouchers / coupons",
)
def list_coupons(
    active_only: bool = Query(True, description="Only return currently valid ACTIVE coupons"),
    db: Session = Depends(get_db),
):
    """Return voucher rows from the coupons table."""
    sql = """
        SELECT
            id,
            code,
            name,
            discount_type,
            discount_value,
            min_order_value,
            max_discount,
            usage_limit,
            usage_limit_per_user,
            used_count,
            start_at,
            end_at,
            status
        FROM coupons
    """
    params: Dict[str, Any] = {}
    if active_only:
        sql += """
            WHERE status = 'ACTIVE'
              AND start_at <= :now
              AND end_at >= :now
        """
        params["now"] = datetime.utcnow()
    sql += " ORDER BY id ASC"

    rows = db.execute(text(sql), params).mappings().all()
    return [
        {
            "id": int(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "discount_type": r["discount_type"],
            "discount_value": float(r["discount_value"]),
            "min_order_value": float(r["min_order_value"]),
            "max_discount": float(r["max_discount"]) if r["max_discount"] is not None else None,
            "usage_limit": r["usage_limit"],
            "usage_limit_per_user": r["usage_limit_per_user"],
            "used_count": int(r["used_count"]),
            "start_at": str(r["start_at"]),
            "end_at": str(r["end_at"]),
            "status": r["status"],
        }
        for r in rows
    ]


@router.get(
    "/coupons/{code}",
    response_model=Dict[str, Any],
    summary="Look up one voucher by code",
)
def get_coupon(code: str, db: Session = Depends(get_db)):
    """Fetch a single coupon/voucher by its code."""
    row = db.execute(
        text(
            """
            SELECT
                id, code, name, discount_type, discount_value,
                min_order_value, max_discount, usage_limit,
                usage_limit_per_user, used_count, start_at, end_at, status
            FROM coupons
            WHERE code = :code
            LIMIT 1
            """
        ),
        {"code": code.strip().upper()},
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{code}' not found.",
        )

    now = datetime.utcnow()
    is_valid = (
        row["status"] == "ACTIVE"
        and row["start_at"] <= now
        and row["end_at"] >= now
        and (row["usage_limit"] is None or int(row["used_count"]) < int(row["usage_limit"]))
    )

    return {
        "id": int(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "discount_type": row["discount_type"],
        "discount_value": float(row["discount_value"]),
        "min_order_value": float(row["min_order_value"]),
        "max_discount": float(row["max_discount"]) if row["max_discount"] is not None else None,
        "usage_limit": row["usage_limit"],
        "usage_limit_per_user": row["usage_limit_per_user"],
        "used_count": int(row["used_count"]),
        "start_at": str(row["start_at"]),
        "end_at": str(row["end_at"]),
        "status": row["status"],
        "is_valid": is_valid,
    }
