<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">污水处理厂工艺管控平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向污水处理厂进出水监测、工艺单元、加药曝气、污泥处置与达标排放的一体化工艺管控后台。</span>
        <span class="head-user">当前值班：{{ store.operator }} · {{ store.shiftLabel }}</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()

const navItems = [{ label: "运营概览", path: "/" }, { label: "厂区单元", path: "/plant" }, { label: "进水监测", path: "/inflow" }, { label: "出水监测", path: "/effluent" }, { label: "曝气控制", path: "/aeration" }, { label: "加药管理", path: "/dosing" }, { label: "污泥处置", path: "/sludge" }, { label: "脱水运行", path: "/dewater" }, { label: "泵站运行", path: "/pump" }, { label: "鼓风机组", path: "/blower" }, { label: "膜组件", path: "/membrane" }, { label: "在线仪表", path: "/online" }, { label: "取样检测", path: "/sample" }, { label: "药剂出入", path: "/chemical" }, { label: "能耗管理", path: "/energy" }, { label: "报警中心", path: "/alarm" }, { label: "设备检修", path: "/maint" }, { label: "受限空间作业", path: "/permit" }, { label: "达标审核", path: "/audit" }]
</script>
