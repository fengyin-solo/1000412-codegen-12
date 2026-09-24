"""业务模块路由汇总。

这里统一按别名导入再暴露 ROUTERS：模块名有可能和内置名撞车（某个业务模块就叫 dict、list
这种名字时），按名字直接 import 会把内置类型覆盖掉，函数注解在运行时求值就会报
'module' object is not subscriptable。
"""
from __future__ import annotations

from app.routers import plant as router_plant
from app.routers import inflow as router_inflow
from app.routers import effluent as router_effluent
from app.routers import aeration as router_aeration
from app.routers import dosing as router_dosing
from app.routers import sludge as router_sludge
from app.routers import dewater as router_dewater
from app.routers import pump as router_pump
from app.routers import blower as router_blower
from app.routers import membrane as router_membrane
from app.routers import online as router_online
from app.routers import sample as router_sample
from app.routers import chemical as router_chemical
from app.routers import energy as router_energy
from app.routers import alarm as router_alarm
from app.routers import maint as router_maint
from app.routers import permit as router_permit
from app.routers import audit as router_audit

ROUTERS = [router_plant, router_inflow, router_effluent, router_aeration, router_dosing, router_sludge, router_dewater, router_pump, router_blower, router_membrane, router_online, router_sample, router_chemical, router_energy, router_alarm, router_maint, router_permit, router_audit]
