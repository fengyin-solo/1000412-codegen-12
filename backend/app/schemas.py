"""接口出入参模型：列表分页、动作结果与各模块的明细结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class ActionResult(BaseModel):
    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    """登记或修改一条业务记录时提交的字段集合。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None



class PlantEntry(BaseModel):
    """工艺单元明细结构。"""

    field_0: str | None = None  # 单元编码
    field_1: str | None = None  # 单元名称
    field_2: str | None = None  # 处理工艺
    field_3: str | None = None  # 设计处理量
    field_4: str | None = None  # 实际处理量
    field_5: str | None = None  # 运行班组
    field_6: str | None = None  # 投运日期
    field_7: str | None = None  # 单元状态

class InflowEntry(BaseModel):
    """进水记录明细结构。"""

    field_0: str | None = None  # 监测编号
    field_1: str | None = None  # 采样时间
    field_2: str | None = None  # 进水流量
    field_3: str | None = None  # 化学需氧量
    field_4: str | None = None  # 氨氮浓度
    field_5: str | None = None  # 悬浮物
    field_6: str | None = None  # 酸碱度
    field_7: str | None = None  # 监测状态

class EffluentEntry(BaseModel):
    """出水记录明细结构。"""

    field_0: str | None = None  # 监测编号
    field_1: str | None = None  # 采样时间
    field_2: str | None = None  # 出水流量
    field_3: str | None = None  # 化学需氧量
    field_4: str | None = None  # 氨氮浓度
    field_5: str | None = None  # 总磷浓度
    field_6: str | None = None  # 达标判定
    field_7: str | None = None  # 监测状态

class AerationEntry(BaseModel):
    """曝气记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 曝气池编号
    field_2: str | None = None  # 溶解氧值
    field_3: str | None = None  # 风量设定
    field_4: str | None = None  # 风机频率
    field_5: str | None = None  # 调节时间
    field_6: str | None = None  # 操作人员
    field_7: str | None = None  # 控制状态

class DosingEntry(BaseModel):
    """加药单明细结构。"""

    field_0: str | None = None  # 加药单号
    field_1: str | None = None  # 药剂名称
    field_2: str | None = None  # 投加浓度
    field_3: str | None = None  # 投加量
    field_4: str | None = None  # 加药点位
    field_5: str | None = None  # 投加时间
    field_6: str | None = None  # 操作人员
    field_7: str | None = None  # 加药状态

class SludgeEntry(BaseModel):
    """污泥处置单明细结构。"""

    field_0: str | None = None  # 处置单号
    field_1: str | None = None  # 污泥来源
    field_2: str | None = None  # 含水率
    field_3: str | None = None  # 污泥量
    field_4: str | None = None  # 处置方式
    field_5: str | None = None  # 外运时间
    field_6: str | None = None  # 承运单位
    field_7: str | None = None  # 处置状态

class DewaterEntry(BaseModel):
    """脱水记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 脱水机编号
    field_2: str | None = None  # 进泥量
    field_3: str | None = None  # 出泥含水率
    field_4: str | None = None  # 絮凝剂用量
    field_5: str | None = None  # 运行时长
    field_6: str | None = None  # 操作人员
    field_7: str | None = None  # 运行状态

class PumpEntry(BaseModel):
    """泵站明细结构。"""

    field_0: str | None = None  # 泵站编号
    field_1: str | None = None  # 泵组台数
    field_2: str | None = None  # 运行泵号
    field_3: str | None = None  # 出水流量
    field_4: str | None = None  # 液位高度
    field_5: str | None = None  # 运行电流
    field_6: str | None = None  # 值守人员
    field_7: str | None = None  # 泵站状态

class BlowerEntry(BaseModel):
    """鼓风机组明细结构。"""

    field_0: str | None = None  # 机组编号
    field_1: str | None = None  # 机组型号
    field_2: str | None = None  # 额定风量
    field_3: str | None = None  # 出口压力
    field_4: str | None = None  # 运行时长
    field_5: str | None = None  # 维护周期
    field_6: str | None = None  # 所属单元
    field_7: str | None = None  # 机组状态

class MembraneEntry(BaseModel):
    """膜组明细结构。"""

    field_0: str | None = None  # 膜组编号
    field_1: str | None = None  # 膜型号
    field_2: str | None = None  # 膜面积
    field_3: str | None = None  # 跨膜压差
    field_4: str | None = None  # 通量
    field_5: str | None = None  # 清洗周期
    field_6: str | None = None  # 投用日期
    field_7: str | None = None  # 膜组状态

class OnlineEntry(BaseModel):
    """在线仪表明细结构。"""

    field_0: str | None = None  # 仪表编号
    field_1: str | None = None  # 仪表类型
    field_2: str | None = None  # 测量范围
    field_3: str | None = None  # 校准周期
    field_4: str | None = None  # 安装点位
    field_5: str | None = None  # 校准到期日
    field_6: str | None = None  # 责任人
    field_7: str | None = None  # 仪表状态

class SampleEntry(BaseModel):
    """检测单明细结构。"""

    field_0: str | None = None  # 检测单号
    field_1: str | None = None  # 取样点位
    field_2: str | None = None  # 检测项目
    field_3: str | None = None  # 检测值
    field_4: str | None = None  # 标准限值
    field_5: str | None = None  # 检测结论
    field_6: str | None = None  # 检测人员
    field_7: str | None = None  # 检测状态

class ChemicalEntry(BaseModel):
    """药剂单据明细结构。"""

    field_0: str | None = None  # 单据编号
    field_1: str | None = None  # 药剂名称
    field_2: str | None = None  # 规格型号
    field_3: str | None = None  # 出入数量
    field_4: str | None = None  # 结存数量
    field_5: str | None = None  # 供应商
    field_6: str | None = None  # 经办人员
    field_7: str | None = None  # 单据状态

class EnergyEntry(BaseModel):
    """能耗记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 统计日期
    field_2: str | None = None  # 用电量
    field_3: str | None = None  # 单位电耗
    field_4: str | None = None  # 药剂单耗
    field_5: str | None = None  # 吨水电耗
    field_6: str | None = None  # 记录人员
    field_7: str | None = None  # 记录状态

class AlarmEntry(BaseModel):
    """报警事件明细结构。"""

    field_0: str | None = None  # 报警编号
    field_1: str | None = None  # 报警类型
    field_2: str | None = None  # 报警等级
    field_3: str | None = None  # 触发点位
    field_4: str | None = None  # 触发时间
    field_5: str | None = None  # 确认人员
    field_6: str | None = None  # 处置措施
    field_7: str | None = None  # 报警状态

class MaintEntry(BaseModel):
    """检修单明细结构。"""

    field_0: str | None = None  # 检修单号
    field_1: str | None = None  # 关联设备
    field_2: str | None = None  # 检修类型
    field_3: str | None = None  # 计划开始日
    field_4: str | None = None  # 实际完成日
    field_5: str | None = None  # 检修人员
    field_6: str | None = None  # 验收人员
    field_7: str | None = None  # 检修状态

class PermitEntry(BaseModel):
    """作业许可单明细结构。"""

    field_0: str | None = None  # 许可编号
    field_1: str | None = None  # 作业类型
    field_2: str | None = None  # 作业地点
    field_3: str | None = None  # 监护人
    field_4: str | None = None  # 安全措施
    field_5: str | None = None  # 许可时间
    field_6: str | None = None  # 有效期至
    field_7: str | None = None  # 许可状态

class AuditEntry(BaseModel):
    """审核记录明细结构。"""

    field_0: str | None = None  # 审核编号
    field_1: str | None = None  # 审核周期
    field_2: str | None = None  # 审核范围
    field_3: str | None = None  # 超标次数
    field_4: str | None = None  # 整改项数
    field_5: str | None = None  # 审核结论
    field_6: str | None = None  # 审核人员
    field_7: str | None = None  # 审核状态
