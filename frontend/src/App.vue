<script setup lang="ts">
import { useWebSocket } from '@/composables/useWebSocket'
import { computed } from 'vue'
import DashboardStats from './components/DashboardStats.vue'
import TransactionTable from './components/TransactionTable.vue'

const { isConnected, predictions } = useWebSocket()

const stats = computed(() => {
  const p = predictions.value
  return {
    total: p.length,
    flagged: p.filter(pred => pred.risk_level !== 'LOW').length,
    approved: p.filter(pred => pred.status === 'APPROVE').length,
    denied: p.filter(pred => pred.status === 'DENY').length,
    critical: p.filter(pred => pred.risk_level === 'CRITICAL').length,
    high: p.filter(pred => pred.risk_level === 'HIGH').length,
    low: p.filter(pred => pred.risk_level === 'LOW').length
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-50 shadow-sm">
      <div class="max-w-[1400px] mx-auto flex items-center justify-between">
        <h1 class="text-2xl font-bold flex items-center gap-2">
          FraudShield
        </h1>
        <div class="flex items-center gap-2 text-sm">
          <div class="flex items-center gap-2">
            <span
              :class="isConnected ? 'bg-green-500' : 'bg-gray-400'"
              class="w-2 h-2 rounded-full animate-pulse"
            ></span>
            <span :class="isConnected ? 'text-green-600' : 'text-gray-400'">
              {{ isConnected ? '● Live' : '○ Disconnected' }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-[1400px] mx-auto p-6">
      <div class="mb-8">
        <h2 class="text-3xl font-bold mb-2">Real-Time Fraud Detection</h2>
        <p class="text-slate-600">{{ stats.total }} transactions processed</p>
      </div>

      <DashboardStats :stats="stats" />

      <div class="mb-4">
        <h3 class="text-xl font-semibold mb-4">Transaction History</h3>
      </div>

      <TransactionTable :predictions="predictions" />
    </main>
  </div>
</template>
