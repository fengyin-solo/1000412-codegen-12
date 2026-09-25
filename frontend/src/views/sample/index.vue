<template>
  <section class="page" data-module="sample">
    <header class="page-head">
      <div>
        <h2>取样检测管理</h2>
        <p class="page-desc">维护检测单，围绕检测单号、取样点位、检测项目、检测值做登记、筛选与状态流转；提交检测值后按标准限值自动判定合格、临界超标或明显超标。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openSubmit()">提交检测值并判定</button>
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
            <span
              v-if="column === '检测结论' && row[column]"
              class="judge-badge"
              :class="badgeClass(String(row[column]))"
              :title="reasonHint(row)"
            >{{ row[column] }}</span>
            <span v-else-if="column === '判定方式' && row[column]"
              class="source-tag"
              :class="String(row[column]) === '人工改判' ? 'manual' : 'auto'"
            >{{ row[column] }}</span>
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
            <button class="link" type="button" @click="openOverride(row)">人工改判</button>
            <button
              v-if="!row['检测值']"
              class="link"
              type="button"
              @click="openSubmit(row)"
            >补录判定</button>
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
      <span v-else-if="successMessage" class="success-text">{{ successMessage }}</span>
    </footer>

    <!-- 提交检测值并自动判定 -->
    <div v-if="submitVisible" class="modal-mask" @click.self="closeSubmit">
      <div class="modal">
        <h3>提交检测值并自动判定</h3>
        <p class="modal-tip">按检测单号与取样点位读取检测单与标准限值；同一检测单号只允许提交一次。</p>
        <form @submit.prevent="fetchSheet">
          <label class="form-item">
            <span>检测单号 *</span>
            <input v-model="submitForm['检测单号']" placeholder="如 SAMP-0004" required />
          </label>
          <label class="form-item">
            <span>取样点位 *</span>
            <input v-model="submitForm['取样点位']" placeholder="提交时须与检测单登记点位一致" required />
          </label>
          <button class="btn" type="submit">读取检测单与限值</button>
        </form>

        <div v-if="submitLookup" class="lookup-box">
          <p>检测项目：<strong>{{ submitLookup.entry['检测项目'] ?? '—' }}</strong></p>
          <p>
            标准限值：
            <strong>{{ submitForm['标准限值'] || '未配置' }}</strong>
          </p>
          <p v-if="submitLookup.entry['检测值']" class="warn-text">
            该单号已提交检测值（{{ submitLookup.entry['检测值'] }}），重复提交会被拒绝，如需更正请走人工改判。
          </p>
        </div>

        <form class="submit-form" @submit.prevent="confirmSubmit">
          <label class="form-item">
            <span>检测值 *</span>
            <input v-model="submitForm['检测值']" placeholder="支持 1.95 mg/L 这类带单位录入" required />
          </label>
          <label class="form-item">
            <span>检测人员</span>
            <input v-model="submitForm['检测人员']" placeholder="选填，留空则不覆盖原检测人员" />
          </label>
          <p v-if="submitError" class="error-text">{{ submitError }}</p>
          <div class="modal-actions">
            <button class="btn ghost" type="button" @click="closeSubmit">取消</button>
            <button class="btn primary" type="submit">提交并自动判定</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 人工改判 -->
    <div v-if="overrideVisible" class="modal-mask" @click.self="closeOverride">
      <div class="modal">
        <h3>人工改判</h3>
        <p class="modal-tip">
          检测单 {{ overrideForm['检测单号'] }}（{{ overrideForm['取样点位'] }} ·
          {{ overrideForm['检测项目'] }}），系统结论：<strong>{{ overrideForm._原结论 || '无' }}</strong>
        </p>
        <form @submit.prevent="confirmOverride">
          <label class="form-item">
            <span>改判结论 *</span>
            <select v-model="overrideForm['检测结论']" required>
              <option value="" disabled>请选择改判结论</option>
              <option v-for="option in judgeOptions" :key="option" :value="option">{{ option }}</option>
            </select>
          </label>
          <label class="form-item">
            <span>改判原因 *</span>
            <textarea v-model="overrideForm['判定原因']" rows="3" placeholder="不少于 4 个字，将随检测单留痕"></textarea>
          </label>
          <label class="form-item">
            <span>改判人员</span>
            <input v-model="overrideForm['检测人员']" placeholder="选填" />
          </label>
          <p v-if="overrideError" class="error-text">{{ overrideError }}</p>
          <div class="modal-actions">
            <button class="btn ghost" type="button" @click="closeOverride">取消</button>
            <button class="btn primary" type="submit">确认改判</button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type FormState = Record<string, string>

const ENDPOINT = '/api/sample'
// 判定方式列紧随检测结论，结论与检测单的对应关系以检测单号为准持久化
const columns = ["检测单号", "取样点位", "检测项目", "检测值", "标准限值", "检测结论", "判定方式", "检测人员", "检测状态"]
// 既有三个动作及其状态流转口径保持不变
const actions = ["开始检测", "判定合格", "判定不合格"]
const judgeOptions = ["合格", "临界超标", "明显超标"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const stats = computed(() => {
  const pending = rows.value.filter((row) => row['检测状态'] === '待取样' || row['status'] === '待取样').length
  const judged = rows.value.filter((row) => judgeOptions.includes(String(row['检测结论'] ?? '')))
  const qualified = judged.filter((row) => row['检测结论'] === '合格').length
  const failed = rows.value.filter((row) => row['检测状态'] === '不合格' || row['status'] === '不合格').length
  const rate = judged.length ? `${Math.round((qualified / judged.length) * 1000) / 10}%` : '—'
  return [
    { label: '待取样检测', value: pending },
    { label: '检测合格率', value: rate },
    { label: '不合格批次', value: failed },
  ]
})

// ---- 提交检测值并判定 ----
const submitVisible = ref(false)
const submitLookup = ref<{ entry: Row } | null>(null)
const submitError = ref('')
const submitForm = reactive<FormState>({
  '检测单号': '', '取样点位': '', '检测项目': '', '检测值': '', '标准限值': '', '检测人员': '',
})

// ---- 人工改判 ----
const overrideVisible = ref(false)
const overrideError = ref('')
const overrideForm = reactive<FormState & { _原结论: string }>({
  '检测单号': '', '取样点位': '', '检测项目': '', '检测结论': '', '判定原因': '', '检测人员': '', _原结论: '',
})

function badgeClass(conclusion: string) {
  if (conclusion === '合格') return 'pass'
  if (conclusion === '临界超标') return 'critical'
  if (conclusion === '明显超标') return 'obvious'
  return ''
}

function reasonHint(row: Row) {
  const parts = [String(row['判定原因'] ?? '')]
  if (row['超限幅度']) parts.unshift(`超限幅度：${row['超限幅度']}`)
  if (row['判定时间']) parts.push(`（${row['判定方式']} · ${row['判定时间']}）`)
  return parts.filter(Boolean).join('\n')
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openSubmit(row?: Row) {
  submitError.value = ''
  submitLookup.value = null
  Object.assign(submitForm, {
    '检测单号': row ? String(row['检测单号'] ?? '') : '',
    '取样点位': row ? String(row['取样点位'] ?? '') : '',
    '检测项目': row ? String(row['检测项目'] ?? '') : '',
    '检测值': '',
    '标准限值': row ? String(row['标准限值'] ?? '') : '',
    '检测人员': '',
  })
  submitVisible.value = true
}

function closeSubmit() {
  submitVisible.value = false
}

async function fetchSheet() {
  submitError.value = ''
  successMessage.value = ''
  try {
    const query = new URLSearchParams({
      sheet_no: submitForm['检测单号'],
      point: submitForm['取样点位'],
    }).toString()
    const response = await request(`${ENDPOINT}/lookup?${query}`)
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(payload?.detail ?? '检测单读取失败')
    }
    if (!payload.ok) {
      throw new Error(payload.message ?? '检测单与取样点位核对未通过')
    }
    submitLookup.value = { entry: payload.entry }
    submitForm['检测项目'] = String(payload.entry['检测项目'] ?? '')
    submitForm['标准限值'] = String(payload.standard_limit ?? '')
  } catch (error) {
    submitLookup.value = null
    submitError.value = error instanceof Error ? error.message : '检测单读取失败'
  }
}

async function confirmSubmit() {
  submitError.value = ''
  try {
    const response = await request(`${ENDPOINT}/judgements`, {
      method: 'POST',
      body: JSON.stringify({ values: { ...submitForm } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.detail ?? payload?.message ?? '自动判定未生效')
    }
    closeSubmit()
    successMessage.value = payload.message
    await reload()
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : '自动判定提交失败'
  }
}

function openOverride(row: Row) {
  overrideError.value = ''
  Object.assign(overrideForm, {
    '检测单号': String(row['检测单号'] ?? ''),
    '取样点位': String(row['取样点位'] ?? ''),
    '检测项目': String(row['检测项目'] ?? ''),
    '检测结论': '',
    '判定原因': '',
    '检测人员': '',
    _原结论: String(row['检测结论'] ?? ''),
  })
  overrideVisible.value = true
}

function closeOverride() {
  overrideVisible.value = false
}

async function confirmOverride() {
  overrideError.value = ''
  try {
    const response = await request(`${ENDPOINT}/manual-override`, {
      method: 'POST',
      body: JSON.stringify({
        values: {
          '检测单号': overrideForm['检测单号'],
          '检测结论': overrideForm['检测结论'],
          '判定原因': overrideForm['判定原因'],
          '检测人员': overrideForm['检测人员'],
        },
      }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.detail ?? payload?.message ?? '人工改判未生效')
    }
    closeOverride()
    successMessage.value = payload.message
    await reload()
  } catch (error) {
    overrideError.value = error instanceof Error ? error.message : '人工改判失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('取样检测动作未生效，请稍后重试')
    }
    const payload = await response.json().catch(() => null)
    successMessage.value = payload?.message ?? `检测单已${action}`
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '取样检测操作失败'
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
.page-actions { display: flex; gap: 8px; }
.success-text { color: #067647; }
.warn-text { color: #b54708; font-size: 12px; margin: 6px 0 0; }
.judge-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; line-height: 1.6; white-space: pre-line; }
.judge-badge.pass { background: #e7f6ec; color: #067647; border: 1px solid #aee3c2; }
.judge-badge.critical { background: #fff4e0; color: #b54708; border: 1px solid #f5d29a; }
.judge-badge.obvious { background: #fdecec; color: #b42318; border: 1px solid #f3b4b0; }
.source-tag { font-size: 12px; color: var(--muted); }
.source-tag.manual { color: #b54708; }
.modal-mask { position: fixed; inset: 0; background: rgba(16, 24, 40, 0.45); display: flex; align-items: center; justify-content: center; z-index: 20; }
.modal { background: #fff; border-radius: 10px; padding: 20px 24px; width: 460px; max-width: calc(100vw - 32px); max-height: calc(100vh - 48px); overflow: auto; }
.modal h3 { margin: 0 0 4px; font-size: 16px; }
.modal-tip { color: var(--muted); font-size: 12px; margin: 0 0 12px; }
.form-item { display: block; margin-bottom: 10px; }
.form-item span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.form-item input, .form-item select, .form-item textarea { width: 100%; border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font: inherit; }
.lookup-box { background: #f6f8fb; border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; }
.lookup-box p { margin: 4px 0; font-size: 13px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
</style>
