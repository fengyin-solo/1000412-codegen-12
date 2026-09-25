"""取样检测业务规则：检测值与标准限值的自动判定、人工改判与状态流转。

判定口径：
- 限值支持「≤上限」「≥下限」「下限~上限」三种写法，未显式写方向时按上限处理
  （检测项目多为污染物浓度，默认越小越好）。
- 未超限：合格；超出限值但幅度在临界带（默认 10%）内：临界超标；
  超出临界带：明显超标。
- 自动判定只写检测结论，不改检测状态；合格/不合格状态仍由原有动作驱动，
  人工可以在自动结论基础上改判，改判需填写原因。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.store import store

MODULE = "sample"
REQUIRED_FIELDS = ["检测单号", "取样点位", "检测项目"]
STATUS_ORDER = ["待取样", "检测中", "合格", "不合格"]
ACTION_RULES = {"开始检测": "检测中", "判定合格": "合格", "判定不合格": "不合格"}
NEGATIVE_ACTIONS = []

# 判定结论口径
RESULT_QUALIFIED = "合格"
RESULT_CRITICAL = "临界超标"
RESULT_OBVIOUS = "明显超标"
AUTO_SOURCE = "自动判定"
MANUAL_SOURCE = "人工改判"
# 超出限值幅度 ≤ 该比例视为临界超标，超过则为明显超标
CRITICAL_RATIO = 0.10
MANUAL_OPTIONS = [RESULT_QUALIFIED, RESULT_CRITICAL, RESULT_OBVIOUS]

# 各取样点位 / 检测项目的标准限值。优先按（点位、项目）精确匹配，
# 项目名相同但点位对不上时使用项目级兜底限值；再没有则按限值缺失处理。
STANDARD_LIMITS: dict[tuple[str, str], str] = {
    ("粗格栅进水口", "COD"): "≤500",
    ("粗格栅进水口", "氨氮"): "≤45",
    ("生化池出口", "溶解氧"): "≥2.0",
    ("生化池出口", "氨氮"): "≤8.0",
    ("二沉池出口", "COD"): "≤50",
    ("二沉池出口", "总磷"): "≤0.5",
    ("二沉池出口", "pH"): "6.0~9.0",
    ("接触消毒池", "粪大肠菌群"): "≤1000",
}
PROJECT_FALLBACK_LIMITS: dict[str, str] = {
    "COD": "≤50",
    "氨氮": "≤5.0",
    "总磷": "≤0.5",
    "pH": "6.0~9.0",
}


def _to_number(raw: Any) -> float | None:
    """把「12.5 mg/L」这类录入值解析成数字；空值或非数字返回 None。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _parse_limit(text: Any) -> tuple[str, float, float | None] | None:
    """解析限值为（方向, 下界, 上界）。

    - 「≤50」/「50」→ ("max", 0.0, 50.0)
    - 「≥2」/「>=2」 → ("min", 2.0, None)
    - 「6~9」        → ("range", 6.0, 9.0)
    限值为空或解析不出数字时返回 None（限值缺失）。
    """
    if text is None:
        return None
    raw = str(text).strip().replace(",", "")
    if not raw:
        return None
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    if "~" in raw or "～" in raw or "-" in raw:
        range_match = re.findall(r"\d+(?:\.\d+)?", re.sub(r"[~～-]", " ", raw))
        if len(range_match) >= 2:
            low, high = float(range_match[0]), float(range_match[1])
            if low <= high:
                return "range", low, high
    if len(numbers) >= 2:
        low, high = float(numbers[0]), float(numbers[1])
        return "range", min(low, high), max(low, high)
    if not numbers:
        return None
    bound = float(numbers[0])
    if raw[:1] in {"≥", ">"} or ">=" in raw:
        return "min", bound, None
    # 「≤ / < / <=」或只写数字，统一按上限处理
    return "max", 0.0, bound


def _evaluate(value: float, limit: tuple[str, float, float | None]) -> tuple[str, float]:
    """按阈值规则给出结论；同时返回超限幅度（占限值的比例，合格时为 0）。"""
    direction, low, high = limit
    if direction == "range":
        assert high is not None
        if value < low:
            span = high - low or abs(low) or 1.0
            return RESULT_OBVIOUS, (low - value) / span
        if value > high:
            span = high - low or abs(high) or 1.0
            return RESULT_OBVIOUS, (value - high) / span
        return RESULT_QUALIFIED, 0.0
    if direction == "min":
        if value < low:
            base = abs(low) or 1.0
            ratio = (low - value) / base
            level = RESULT_CRITICAL if ratio <= CRITICAL_RATIO else RESULT_OBVIOUS
            return level, ratio
        return RESULT_QUALIFIED, 0.0
    assert high is not None
    if value > high:
        base = abs(high) or 1.0
        ratio = (value - high) / base
        level = RESULT_CRITICAL if ratio <= CRITICAL_RATIO else RESULT_OBVIOUS
        return level, ratio
    return RESULT_QUALIFIED, 0.0


class SampleService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("检测单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def find_by_no(self, sheet_no: str) -> dict[str, Any] | None:
        """按检测单号定位检测单。"""
        sheet_no = str(sheet_no or "").strip()
        if not sheet_no:
            return None
        for row in store.rows(MODULE):
            if str(row.get("检测单号", "")).strip() == sheet_no:
                return row
        return None

    def resolve_limit(self, point: str, project: str) -> str | None:
        """按取样点位 + 检测项目读取标准限值；点位不匹配时走项目级兜底。"""
        point, project = str(point or "").strip(), str(project or "").strip()
        limit = STANDARD_LIMITS.get((point, project))
        if limit is None:
            limit = PROJECT_FALLBACK_LIMITS.get(project)
        return limit

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def auto_judge(
        self,
        *,
        sheet_no: str,
        point: str,
        value: Any,
        operator: str | None = None,
        limit_override: Any = None,
    ) -> tuple[dict[str, Any] | None, str]:
        """按检测单号与取样点位提交检测值并自动判定。

        返回（检测单, 说明）；检测单为 None 时说明里给出被拦下的原因：
        检测值为空、限值缺失、同一单号重复提交、单号不存在等。
        """
        sheet_no, point = str(sheet_no or "").strip(), str(point or "").strip()
        if not sheet_no:
            return None, "检测单号为空，无法定位检测单"
        entry = self.find_by_no(sheet_no)
        if entry is None:
            return None, f"检测单号「{sheet_no}」不存在，未提交判定"
        if not point:
            return None, "取样点位为空，无法匹配标准限值"
        if str(entry.get("取样点位", "")).strip() != point:
            return None, (
                f"取样点位「{point}」与检测单登记点位"
                f"「{entry.get('取样点位', '')}」不一致，未提交判定"
            )
        # 同一单号只允许提交一次检测结果；重录需先走人工改判
        if entry.get("检测值") not in (None, ""):
            return None, (
                f"检测单 {sheet_no} 已提交过检测值（{entry.get('检测值')}），"
                "同一单号不可重复提交；如需更正请使用人工改判"
            )
        number = _to_number(value)
        if number is None:
            return None, "检测值为空或不是有效数字，无法自动判定"
        limit_text = limit_override if str(limit_override or "").strip() else None
        if limit_text is None:
            limit_text = self.resolve_limit(point, str(entry.get("检测项目", "")).strip())
        parsed = _parse_limit(limit_text)
        if parsed is None:
            return None, (
                f"取样点位「{point}」检测项目「{entry.get('检测项目', '')}」"
                "缺少可解析的标准限值，无法自动判定；请先在限值表中配置限值"
            )

        result, ratio = _evaluate(number, parsed)
        entry["检测值"] = str(value).strip()
        entry["标准限值"] = str(limit_text).strip()
        entry["检测结论"] = result
        entry["判定方式"] = AUTO_SOURCE
        entry["判定时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry["超限幅度"] = f"{ratio * 100:.1f}%"
        entry["判定原因"] = self._reason(result, number, str(limit_text).strip(), ratio)
        if operator:
            entry["检测人员"] = str(operator).strip()
        if result == RESULT_QUALIFIED:
            return entry, f"检测单 {sheet_no} 自动判定：合格（{number}，限值{limit_text}）"
        return entry, (
            f"检测单 {sheet_no} 自动判定：{result}"
            f"（检测值 {number}，限值{limit_text}，超限 {ratio * 100:.1f}%）"
        )

    def manual_override(
        self,
        *,
        sheet_no: str,
        result: str,
        reason: str,
        operator: str | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        """人工改判：保留自动判定痕迹，以改判结论为准，原因必填。"""
        sheet_no = str(sheet_no or "").strip()
        entry = self.find_by_no(sheet_no)
        if entry is None:
            return None, f"检测单号「{sheet_no}」不存在，未改判"
        result = str(result or "").strip()
        if result not in MANUAL_OPTIONS:
            return None, f"改判结论「{result}」不在允许范围（合格、临界超标、明显超标）"
        reason = str(reason or "").strip()
        if len(reason) < 4:
            return None, "人工改判必须填写不少于 4 个字的改判原因"
        auto_result = entry.get("检测结论")
        entry["自动判定结论"] = auto_result if entry.get("判定方式") == AUTO_SOURCE else entry.get("自动判定结论")
        entry["检测结论"] = result
        entry["判定方式"] = MANUAL_SOURCE
        entry["判定时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry["判定原因"] = reason
        entry["改判人员"] = str(operator or "").strip() or entry.get("改判人员")
        return entry, f"检测单 {sheet_no} 已人工改判为「{result}」（原结论：{auto_result or '无'}）"

    @staticmethod
    def _reason(result: str, value: float, limit_text: str, ratio: float) -> str:
        if result == RESULT_QUALIFIED:
            return f"检测值 {value} 未超出限值 {limit_text}，系统自动判定合格"
        label = "处于限值 10% 临界带内" if result == RESULT_CRITICAL else "已明显偏离限值"
        return (
            f"检测值 {value} 超出限值 {limit_text}，超限 {ratio * 100:.1f}%，{label}，"
            f"系统自动判定{result}"
        )

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"检测单 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于取样检测可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"检测单已{action}"
