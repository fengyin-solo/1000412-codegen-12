"""取样检测接口：维护检测单，覆盖开始检测、判定合格、判定不合格、
检测值提交自动判定与人工改判。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.sample import MANUAL_OPTIONS, SampleService

router = APIRouter(prefix="/api/sample", tags=["取样检测"])

service = SampleService()

LIST_FIELDS = ["检测单号", "取样点位", "检测项目", "检测值", "标准限值", "检测结论", "检测人员", "检测状态"]
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


@router.get("/lookup", response_model=dict)
def lookup_entry(
    sheet_no: str = Query(description="检测单号"),
    point: str | None = Query(default=None, description="取样点位，用于核对并带出标准限值"),
) -> dict[str, Any]:
    """按检测单号与取样点位读取检测单、检测值与标准限值，供提交判定前核对。

    单号不存在、点位与登记不一致时返回 ok=False 并说明原因。
    """
    entry = service.find_by_no(sheet_no)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"检测单号「{sheet_no}」不存在")
    point_text = str(point or "").strip()
    mismatch = False
    if point_text and point_text != str(entry.get("取样点位", "")).strip():
        mismatch = True
    limit = entry.get("标准限值") or service.resolve_limit(
        str(entry.get("取样点位", "")), str(entry.get("检测项目", ""))
    )
    return {
        "ok": not mismatch,
        "entry": entry,
        "standard_limit": limit,
        "message": (
            f"取样点位「{point_text}」与检测单登记点位「{entry.get('取样点位', '')}」不一致"
            if mismatch
            else "检测单与标准限值已带出"
        ),
    }


@router.get("/limits", response_model=dict)
def get_limit(
    point: str = Query(description="取样点位"),
    project: str = Query(description="检测项目"),
) -> dict[str, Any]:
    """按取样点位与检测项目查询标准限值；未配置时 ok=False 并说明。"""
    limit = service.resolve_limit(point, project)
    if limit is None:
        return {
            "ok": False,
            "point": point,
            "project": project,
            "standard_limit": None,
            "message": f"取样点位「{point}」检测项目「{project}」尚未配置标准限值",
        }
    return {
        "ok": True,
        "point": point,
        "project": project,
        "standard_limit": limit,
        "message": "标准限值已带出",
    }


@router.post("/judgements", response_model=ActionResult)
def submit_judgement(payload: EntryPayload) -> ActionResult:
    """提交检测值并按标准限值自动判定（合格 / 临界超标 / 明显超标）。

    检测值为空、限值缺失、同一单号重复提交都会被拦下并在 message 中说明原因。
    """
    values = payload.values
    entry, message = service.auto_judge(
        sheet_no=str(values.get("检测单号") or ""),
        point=str(values.get("取样点位") or ""),
        value=values.get("检测值"),
        operator=str(values.get("检测人员") or "") or None,
        limit_override=values.get("标准限值"),
    )
    return ActionResult(ok=entry is not None, message=message, entry=entry)


@router.post("/manual-override", response_model=ActionResult)
def manual_override(payload: EntryPayload) -> ActionResult:
    """人工改判入口：在自动结论上改判为合格 / 临界超标 / 明显超标，原因必填。"""
    values = payload.values
    result = str(values.get("检测结论") or "").strip()
    if result and result not in MANUAL_OPTIONS:
        return ActionResult(
            ok=False,
            message=f"改判结论「{result}」不在允许范围（合格、临界超标、明显超标）",
        )
    entry, message = service.manual_override(
        sheet_no=str(values.get("检测单号") or ""),
        result=result,
        reason=str(values.get("判定原因") or payload.remark or ""),
        operator=str(values.get("检测人员") or "") or None,
    )
    return ActionResult(ok=entry is not None, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出取样检测清单：返回当前过滤条件下的全量数据。

    注意：该路由需放在 /{entry_id} 之前，否则 export 会被当成检测单 id 解析。
    """
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
    """对单条检测单执行开始检测、判定合格、判定不合格；不允许的动作会被拦下并说明原因。

    自动判定与人工改判不改变这里的状态流转口径，既有动作行为保持不变。
    """
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
