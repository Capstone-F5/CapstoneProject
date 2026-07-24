from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.security import get_current_admin
from dao import order_dao, user_dao
from schemas.admin_schemas import PointsAdjustIn, UserAdminOut, UserDetailOut
from schemas.coupon_schemas import UserCouponOut
from schemas.order_schemas import OrderAdminOut, OrderItemOut

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(get_current_admin)],
)


def _to_user_admin_out(user, tier: str | None) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        phone_number=user.phone_number,
        current_points=user.current_points,
        tier=tier,
        is_guest=user.is_guest,
        created_at=str(user.created_at),
    )


def _to_order_admin_out(order) -> OrderAdminOut:
    latest_payment = max(order.payments, key=lambda p: p.created_at) if order.payments else None
    return OrderAdminOut(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        status=order.status,
        table_number=order.table_number,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        points_used=order.points_used,
        points_earned=order.points_earned,
        created_at=str(order.created_at),
        items=[
            OrderItemOut(
                menu_item_id=item.menu_item_id,
                name_ko=item.menu_item.name_ko if item.menu_item else "",
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                selected_options=item.selected_options or [],
                special_note=item.special_note,
            )
            for item in order.items
        ],
        payment_status=latest_payment.status if latest_payment else None,
    )


@router.get("", response_model=list[UserAdminOut])
async def list_users(phone: str | None = None, db: AsyncSession = Depends(get_session)):
    users = await user_dao.search_users(db, phone)
    result = []
    for user in users:
        membership = await user_dao.get_membership(db, user.id)
        result.append(_to_user_admin_out(user, membership.tier if membership else None))
    return result


@router.get("/{user_id}", response_model=UserDetailOut)
async def get_user_detail(user_id: str, db: AsyncSession = Depends(get_session)):
    user = await user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, "등록된 회원이 아닙니다")

    membership = await user_dao.get_membership(db, user.id)
    recent_orders = await order_dao.get_recent_orders_by_user(db, user.id)
    coupons = await user_dao.get_all_user_coupons(db, user.id)

    base = _to_user_admin_out(user, membership.tier if membership else None)
    return UserDetailOut(
        **base.model_dump(),
        recent_orders=[_to_order_admin_out(o) for o in recent_orders],
        coupons=[
            UserCouponOut(
                user_coupon_id=uc.id,
                user_id=uc.user_id,
                coupon_id=uc.coupon_id,
                issued_at=str(uc.issued_at),
            )
            for uc in coupons
        ],
    )


@router.patch("/{user_id}/points", response_model=UserAdminOut)
async def adjust_user_points(
    user_id: str, payload: PointsAdjustIn, db: AsyncSession = Depends(get_session)
):
    if not payload.reason.strip():
        raise HTTPException(400, "포인트 조정 사유를 입력해 주세요")

    user = await user_dao.adjust_points(db, user_id, payload.delta, payload.reason)
    if user is None:
        raise HTTPException(404, "등록된 회원이 아닙니다")
    await db.commit()

    membership = await user_dao.get_membership(db, user.id)
    return _to_user_admin_out(user, membership.tier if membership else None)
