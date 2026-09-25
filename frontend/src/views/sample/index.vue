<template>
  <section class="page" data-module="sample">
    <header class="page-head">
      <div>
        <h2>取样检测管理</h2>
        <p class="page-desc">维护检测单，围绕检测单号、取样点位、检测项目、检测值做登记、筛选与状态流转；检测值按标准限值自动判定，超限区分临界与明显超标，支持人工改判。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记检测单</button>
        <button class="btn" type="button" @click="exportRows">导出取样检测清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">
            <span v-if="column === '检测结论' && row[column]" class="result-badge" :class="badgeClass(String(row[column]))">{{ row[column] }}</span>
            <template v-else>{{ row[column] ?? '—' }}</template>
          </td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
            <button class="link" type="button" @click="autoJudge(row)">自动判定</button>
            <button class="link" type="button" @click="openOverride(row)">人工改判</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无取样检测数据，可先登记检测单</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条取样检测记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      <span v-else-if="noticeMessage" class="notice-text">{{ noticeMessage }}</span>
    </footer>

    <div v-if="overrideOpen" class="modal-mask" @click.self="closeOverride">
      <form class="modal-card" @submit.prevent="submitOverride">
        <h3>人工改判</h3>
        <p class="modal-hint">人工改判是唯一可以覆盖原结论的入口，改判原因必填，便于复核追溯。</p>
        <label class="modal-field">
          <span>检测单号 / 取样点位</span>
          <input :value="`${overrideForm['检测单号']} / ${overrideForm['取样点位']}`" readonly />
        </label>
        <label class="modal-field">
          <span>检测值 / 标准限值</span>
          <input :value="`${overrideRow?.['检测值'] || '（空）'} / ${overrideRow?.['标准限值'] || '（缺失）'}`" readonly />
        </label>
        <label class="modal-field">
          <span>改判结论</span>
          <select v-model="overrideForm['检测结论']">
            <option v-for="result in judgeResults" :key="result" :value="result">{{ result }}</option>
          </select>
        </label>
        <label class="modal-field">
          <span>改判原因</span>
          <textarea v-model="overrideForm['改判原因']" rows="3" placeholder="请说明改判依据，例如复测结果、样品异常等"></textarea>
        </label>
        <div class="modal-actions">
          <button class="btn" type="button" @click="closeOverride">取消</button>
          <button class="btn primary" type="submit" :disabled="submitting">确认改判</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/sample'
const columns = ["检测单号", "取样点位", "检测项目", "检测值", "标准限值", "检测结论", "判定方式", "判定说明", "检测人员", "检测状态"]
// 既有合格/不合格动作保持原样，自动判定与人工改判是新增入口
const actions = ["开始检测", "判定合格", "判定不合格"]
const statuses = ["待取样", "检测中", "合格", "不合格"]
const judgeResults = ["合格", "临界超标", "明显超标"]
const stats = [{"label": "待取样检测", "value": 0}, {"label": "检测合格率", "value": 0}, {"label": "不合格批次", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const noticeMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const overrideOpen = ref(false)
const submitting = ref(false)
const overrideRow = ref<Row | null>(null)
const overrideForm = reactive<Record<string, string>>({
  '检测单号': '',
  '取样点位': '',
  '检测结论': '合格',
  '改判原因': '',
})

function badgeClass(result: string): string {
  if (result === '合格') return 'badge-pass'
  if (result === '临界超标') return 'badge-critical'
  if (result === '明显超标') return 'badge-serious'
  return ''
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '检测单登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('取样检测动作未生效，请稍后重试')
    }
    const payload = await response.json()
    if (payload?.ok === false) {
      errorMessage.value = payload.message || '取样检测动作未生效'
      return
    }
    noticeMessage.value = payload?.message || '操作成功'
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '取样检测操作失败'
  }
}

async function autoJudge(row: Row) {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/judgement/auto`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          '检测单号': row['检测单号'],
          '取样点位': row['取样点位'],
        },
      }),
    })
    const payload = await response.json()
    if (!response.ok || payload?.ok === false) {
      // 检测值为空、限值缺失、重复提交等原因都由后端在 message 里给出
      errorMessage.value = payload?.message || '自动判定未执行，请核对检测值与标准限值'
      await reload()
      return
    }
    noticeMessage.value = payload.message || '自动判定完成'
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '自动判定请求失败'
  }
}

function openOverride(row: Row) {
  overrideRow.value = row
  overrideForm['检测单号'] = String(row['检测单号'] ?? '')
  overrideForm['取样点位'] = String(row['取样点位'] ?? '')
  overrideForm['检测结论'] = typeof row['检测结论'] === 'string' && judgeResults.includes(row['检测结论'])
    ? row['检测结论']
    : '合格'
  overrideForm['改判原因'] = ''
  overrideOpen.value = true
}

function closeOverride() {
  overrideOpen.value = false
  overrideRow.value = null
}

async function submitOverride() {
  if (submitting.value) return
  errorMessage.value = ''
  noticeMessage.value = ''
  submitting.value = true
  try {
    const response = await request(`${ENDPOINT}/judgement/override`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          '检测单号': overrideForm['检测单号'],
          '取样点位': overrideForm['取样点位'],
          '检测结论': overrideForm['检测结论'],
          '改判原因': overrideForm['改判原因'],
        },
      }),
    })
    const payload = await response.json()
    if (!response.ok || payload?.ok === false) {
      errorMessage.value = payload?.message || '人工改判未生效'
      return
    }
    noticeMessage.value = payload.message || '人工改判完成'
    closeOverride()
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '人工改判请求失败'
  } finally {
    submitting.value = false
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('检测单列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '取样检测列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.result-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 12px;
  border: 1px solid transparent;
  white-space: nowrap;
}
.badge-pass { background: #ecfdf3; color: #027a48; border-color: #abefc6; }
.badge-critical { background: #fffaeb; color: #b54708; border-color: #fedf89; }
.badge-serious { background: #fef3f2; color: #b42318; border-color: #fda29b; }
.notice-text { color: #027a48; }

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal-card {
  width: 460px;
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.modal-card h3 { margin: 0; font-size: 16px; }
.modal-hint { margin: 0; font-size: 12px; color: var(--muted); }
.modal-field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.modal-field input,
.modal-field select,
.modal-field textarea {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
  font-family: inherit;
  color: #1f2937;
}
.modal-field input[readonly] { background: #f8fafc; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
</style>
