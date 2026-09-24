import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from '@/views/Dashboard.vue'
const Plant = () => import('@/views/plant/index.vue')
const Inflow = () => import('@/views/inflow/index.vue')
const Effluent = () => import('@/views/effluent/index.vue')
const Aeration = () => import('@/views/aeration/index.vue')
const Dosing = () => import('@/views/dosing/index.vue')
const Sludge = () => import('@/views/sludge/index.vue')
const Dewater = () => import('@/views/dewater/index.vue')
const Pump = () => import('@/views/pump/index.vue')
const Blower = () => import('@/views/blower/index.vue')
const Membrane = () => import('@/views/membrane/index.vue')
const Online = () => import('@/views/online/index.vue')
const Sample = () => import('@/views/sample/index.vue')
const Chemical = () => import('@/views/chemical/index.vue')
const Energy = () => import('@/views/energy/index.vue')
const Alarm = () => import('@/views/alarm/index.vue')
const Maint = () => import('@/views/maint/index.vue')
const Permit = () => import('@/views/permit/index.vue')
const Audit = () => import('@/views/audit/index.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/plant', name: 'plant', component: Plant },
    { path: '/inflow', name: 'inflow', component: Inflow },
    { path: '/effluent', name: 'effluent', component: Effluent },
    { path: '/aeration', name: 'aeration', component: Aeration },
    { path: '/dosing', name: 'dosing', component: Dosing },
    { path: '/sludge', name: 'sludge', component: Sludge },
    { path: '/dewater', name: 'dewater', component: Dewater },
    { path: '/pump', name: 'pump', component: Pump },
    { path: '/blower', name: 'blower', component: Blower },
    { path: '/membrane', name: 'membrane', component: Membrane },
    { path: '/online', name: 'online', component: Online },
    { path: '/sample', name: 'sample', component: Sample },
    { path: '/chemical', name: 'chemical', component: Chemical },
    { path: '/energy', name: 'energy', component: Energy },
    { path: '/alarm', name: 'alarm', component: Alarm },
    { path: '/maint', name: 'maint', component: Maint },
    { path: '/permit', name: 'permit', component: Permit },
    { path: '/audit', name: 'audit', component: Audit },
  ],
})

export default router
