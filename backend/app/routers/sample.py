"""取样检测接口：维护检测单，覆盖开始检测、判定合格、判定不合格，以及检测值对标准限值的自动判定与人工改判。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.sample import SampleService

router = APIRouter(prefix="/api/sample", tags=["取样检测"])

service = SampleService()

LIST_FIELDS = ["检测单号", "取样点位", "检测项目", "检测值", "标准限值", "检测结论", "判定方式", "超标口径", "判定说明", "检测人员", "检测状态"]
STATUSES = ["待取样", "检测中", "合格", "不合格"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按检测单号检索"),
    status: str | None = Query(default=None, description="待取样、检测中、合格、不合格"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按检测单号与状态过滤取样检测列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/judgement/lookup", response_model=ActionResult)
def lookup_judgement(
    order_no: str = Query(alias="orderNo", description="检测单号"),
    point: str = Query(description="取样点位"),
) -> ActionResult:
    """按检测单号与取样点位读取检测值与标准限值，供自动判定前核对。"""
    entry = service.find_by_key(order_no, point)
    if entry is None:
        same_order = service.find_by_order(order_no)
        if same_order is not None:
            return ActionResult(
                ok=False,
                message=f"检测单号 {order_no} 登记的取样点位是「{same_order.get('取样点位')}」，"
                f"与查询的「{point}」不一致",
            )
        return ActionResult(ok=False, message=f"检测单号 {order_no}（点位 {point}）尚未登记")
    return ActionResult(ok=True, message="已读取检测值与标准限值", entry=entry)


@router.post("/judgement/auto", response_model=ActionResult)
def auto_judge(payload: EntryPayload) -> ActionResult:
    """自动判定：按检测单号与取样点位读取检测值与限值，按阈值给出合格判定。

    检测值为空、限值缺失、单号点位对不上、同一单号重复提交都会在 message 里说明原因。
    """
    values = payload.values
    entry, message, ok = service.auto_judge(
        str(values.get("检测单号") or ""),
        str(values.get("取样点位") or ""),
    )
    return ActionResult(ok=ok, message=message, entry=entry)


@router.post("/judgement/override", response_model=ActionResult)
def manual_override(payload: EntryPayload) -> ActionResult:
    """人工改判入口：可覆盖自动判定结论，但必须填写改判原因。"""
    values = payload.values
    entry, message = service.manual_override(
        str(values.get("检测单号") or ""),
        str(values.get("取样点位") or ""),
        str(values.get("检测结论") or ""),
        str(values.get("改判原因") or ""),
    )
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出取样检测清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "sample", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条检测单明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"检测单 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条检测单，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="检测单已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条检测单执行开始检测、判定合格、判定不合格；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
