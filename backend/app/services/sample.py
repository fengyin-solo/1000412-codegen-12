"""取样检测业务规则：状态流转、字段校验、限值自动判定都收在这里。

自动判定口径：
- 按「检测单号 + 取样点位」定位检测单，读取检测值与标准限值；
- 限值支持上限（≤300 / <300 / 300）、下限（≥6 / >6）、区间（6~9 / 6-9）三种写法；
- 超限幅度不超过 CRITICAL_RATIO（默认 10%）记为「临界超标」，否则记为「明显超标」；
- 检测值为空、限值缺失或无法识别、同一单号重复提交，都给出可读原因，不落结论；
- 人工改判是唯一可以覆盖结论的入口，必须填写改判原因。
"""
from __future__ import annotations

import re
from typing import Any

from app.store import store

MODULE = "sample"
REQUIRED_FIELDS = ["检测单号", "取样点位", "检测项目"]
STATUS_ORDER = ["待取样", "检测中", "合格", "不合格"]
ACTION_RULES = {"开始检测": "检测中", "判定合格": "合格", "判定不合格": "不合格"}
NEGATIVE_ACTIONS = []

# 判定结论与判定方式口径
RESULT_PASS = "合格"
RESULT_CRITICAL = "临界超标"
RESULT_SERIOUS = "明显超标"
JUDGE_RESULTS = [RESULT_PASS, RESULT_CRITICAL, RESULT_SERIOUS]
MODE_AUTO = "自动判定"
MODE_MANUAL = "人工改判"

# 超限幅度 ≤ 10% 算临界，超出即明显超标
CRITICAL_RATIO = 0.10

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_SIGNED_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _to_number(raw: Any) -> float | None:
    """从「265」「265mg/L」这类填报值里取出数值；空值或取不到数字返回 None。"""
    if raw is None:
        return None
    match = _SIGNED_NUMBER_RE.search(str(raw).strip())
    return float(match.group()) if match else None


def _is_blank(raw: Any) -> bool:
    return raw is None or not str(raw).strip() or str(raw).strip() in {"—", "-", "－"}


def _parse_limit(raw: Any) -> tuple[str, float, float] | None:
    """把标准限值解析成 (方向, 下界, 上界)。

    方向取 upper / lower / range；识别不出来返回 None，由调用方说明原因。
    """
    if _is_blank(raw):
        return None
    text = (
        str(raw)
        .strip()
        .replace("＜", "<")
        .replace("＞", ">")
        .replace("≤", "<")
        .replace("≥", ">")
        .replace("＝", "=")
        .replace("～", "~")
        .replace("—", "-")
    )
    numbers = [float(item) for item in _NUMBER_RE.findall(text)]
    if "~" in text and len(numbers) >= 2:
        # 区间内单个端点才可能带负号，用带符号正则按 ~ 两侧分别取
        left, right = text.split("~", 1)
        low = float(_SIGNED_NUMBER_RE.search(left).group())
        high = float(_SIGNED_NUMBER_RE.search(right).group())
        return ("range", min(low, high), max(low, high))
    if "<" in text:
        signed = _SIGNED_NUMBER_RE.findall(text)
        return ("upper", float(signed[-1]), float(signed[-1])) if signed else None
    if ">" in text:
        signed = _SIGNED_NUMBER_RE.findall(text)
        return ("lower", float(signed[-1]), float(signed[-1])) if signed else None
    # 「6-9」这种没有波浪线、两端都不带符号的区间写法
    if "-" in text and len(numbers) >= 2 and not text.lstrip().startswith(("-", ">-", "≥-")):
        low, high = numbers[0], numbers[1]
        return ("range", min(low, high), max(low, high))
    if len(numbers) == 1:
        # 污染物限值默认按上限处理
        return ("upper", numbers[0], numbers[0])
    return None


def _format_ratio(ratio: float) -> str:
    percent = round(ratio * 100, 1)
    if percent == int(percent):
        percent = int(percent)
    return f"{percent}%"


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

    def find_by_key(self, order_no: str, point: str) -> dict[str, Any] | None:
        """按检测单号与取样点位定位检测单；结论挂在记录 id 上，刷新后对应关系不变。"""
        order_no = (order_no or "").strip()
        point = (point or "").strip()
        for row in store.rows(MODULE):
            if str(row.get("检测单号", "")).strip() == order_no and str(
                row.get("取样点位", "")
            ).strip() == point:
                return row
        return None

    def find_by_order(self, order_no: str) -> dict[str, Any] | None:
        order_no = (order_no or "").strip()
        for row in store.rows(MODULE):
            if str(row.get("检测单号", "")).strip() == order_no:
                return row
        return None

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

    # ------------------------------------------------------------------
    # 检测值 vs 标准限值：自动判定 / 人工改判
    # ------------------------------------------------------------------
    def auto_judge(
        self, order_no: str, point: str
    ) -> tuple[dict[str, Any] | None, str, bool]:
        """按检测单号与取样点位读取检测值和标准限值，给出合格判定。

        返回 (检测单, 说明, 是否成功)；不成功时只给原因，不写结论。
        """
        order_no = (order_no or "").strip()
        point = (point or "").strip()
        if not order_no or not point:
            return None, "检测单号与取样点位都必须填写，才能定位检测单", False

        entry = self.find_by_key(order_no, point)
        if entry is None:
            same_order = self.find_by_order(order_no)
            if same_order is not None:
                return (
                    None,
                    f"检测单号 {order_no} 登记的取样点位是「{same_order.get('取样点位')}」，"
                    f"与本次提交的「{point}」不一致，请核对后再提交",
                    False,
                )
            return None, f"检测单号 {order_no}（点位 {point}）尚未登记，无法提交判定", False

        # 同一单号同一点位重复提交：保留原结论，说明原因，改判请走人工入口
        if entry.get("判定方式"):
            return (
                entry,
                f"检测单号 {order_no}（点位 {point}）已提交过{entry.get('判定方式')}"
                f"「{entry.get('检测结论')}」，重复提交不会覆盖原结论；如需调整请使用人工改判",
                False,
            )

        reasons: list[str] = []
        value_raw = entry.get("检测值")
        limit_raw = entry.get("标准限值")
        if _is_blank(value_raw):
            reasons.append("检测值为空，无法与标准限值比对（请先回填检测值）")
        if _is_blank(limit_raw):
            reasons.append("标准限值缺失，无法给出合格判定")
        if reasons:
            return entry, "；".join(reasons), False

        value = _to_number(value_raw)
        limit = _parse_limit(limit_raw)
        if value is None:
            return (
                entry,
                f"检测值「{value_raw}」无法识别为数值，不能自动比对限值；"
                "如确有结论请走人工改判",
                False,
            )
        if limit is None:
            return entry, f"标准限值「{limit_raw}」格式无法识别，自动判定未执行", False

        direction, low, high = limit
        result, detail = self._compare(value, direction, low, high)
        entry["检测结论"] = result
        entry["判定方式"] = MODE_AUTO
        entry["超标口径"] = "" if result == RESULT_PASS else result
        entry["判定说明"] = detail
        entry["改判原因"] = ""
        return entry, f"检测单号 {order_no}（点位 {point}）自动判定完成：{result}。{detail}", True

    def manual_override(
        self, order_no: str, point: str, result: str, reason: str
    ) -> tuple[dict[str, Any] | None, str]:
        """人工改判：唯一可以覆盖已有结论的入口，必须留改判原因。"""
        order_no = (order_no or "").strip()
        point = (point or "").strip()
        result = (result or "").strip()
        reason = (reason or "").strip()
        if not order_no or not point:
            return None, "检测单号与取样点位都必须填写，才能定位检测单"
        if result not in JUDGE_RESULTS:
            return None, f"改判结论只能是：{'、'.join(JUDGE_RESULTS)}"
        if not reason:
            return None, "人工改判必须填写改判原因，便于复核追溯"

        entry = self.find_by_key(order_no, point)
        if entry is None:
            same_order = self.find_by_order(order_no)
            if same_order is not None:
                return (
                    None,
                    f"检测单号 {order_no} 登记的取样点位是「{same_order.get('取样点位')}」，"
                    f"与本次提交的「{point}」不一致，请核对后再改判",
                )
            return None, f"检测单号 {order_no}（点位 {point}）尚未登记，无法改判"

        entry["检测结论"] = result
        entry["判定方式"] = MODE_MANUAL
        entry["超标口径"] = "" if result == RESULT_PASS else result
        entry["改判原因"] = reason
        entry["判定说明"] = f"人工改判为{result}，改判原因：{reason}"
        return entry, f"检测单号 {order_no}（点位 {point}）已人工改判为{result}"

    def _compare(
        self, value: float, direction: str, low: float, high: float
    ) -> tuple[str, str]:
        """按阈值规则比较，返回结论与说明；超限时区分临界 / 明显两种口径。"""
        if direction == "upper":
            if value <= high:
                return RESULT_PASS, f"检测值 {value:g} 未超过上限 {high:g}，判定合格"
            ratio = (value - high) / high if high else 0.0
            result = RESULT_CRITICAL if ratio <= CRITICAL_RATIO else RESULT_SERIOUS
            return (
                result,
                f"检测值 {value:g} 超过上限 {high:g}，超限幅度 {_format_ratio(ratio)}，"
                f"属{result}",
            )
        if direction == "lower":
            if value >= low:
                return RESULT_PASS, f"检测值 {value:g} 不低于下限 {low:g}，判定合格"
            ratio = (low - value) / low if low else 0.0
            result = RESULT_CRITICAL if ratio <= CRITICAL_RATIO else RESULT_SERIOUS
            return (
                result,
                f"检测值 {value:g} 低于下限 {low:g}，偏离幅度 {_format_ratio(ratio)}，"
                f"属{result}",
            )
        # range
        if low <= value <= high:
            return RESULT_PASS, f"检测值 {value:g} 处于限值区间 {low:g}~{high:g} 内，判定合格"
        if value > high:
            bound, ratio = high, (value - high) / high if high else 0.0
            word = "超过上限"
        else:
            bound, ratio = low, (low - value) / low if low else 0.0
            word = "低于下限"
        result = RESULT_CRITICAL if ratio <= CRITICAL_RATIO else RESULT_SERIOUS
        return (
            result,
            f"检测值 {value:g} {word} {bound:g}（限值区间 {low:g}~{high:g}），"
            f"超限幅度 {_format_ratio(ratio)}，属{result}",
        )
