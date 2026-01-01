<script setup lang="ts">
import type { Stats } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Activity, AlertCircle, CheckCircle2, XCircle, AlertOctagon, AlertTriangle, Circle } from 'lucide-vue-next'

const props = defineProps<{
  stats: Stats
}>()

const cards = [
  { key: 'total' as keyof Stats, label: 'Total Transactions', icon: Activity },
  { key: 'flagged' as keyof Stats, label: 'Flagged', icon: AlertCircle },
  { key: 'approved' as keyof Stats, label: 'Approved', icon: CheckCircle2 },
  { key: 'denied' as keyof Stats, label: 'Denied', icon: XCircle },
  { key: 'critical' as keyof Stats, label: 'Critical Risk', icon: AlertOctagon },
  { key: 'high' as keyof Stats, label: 'High Risk', icon: AlertTriangle },
  { key: 'low' as keyof Stats, label: 'Low Risk', icon: Circle }
]
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
    <Card v-for="card in cards" :key="card.key" class="border transition-colors hover:border-primary/30">
      <CardHeader class="pb-2">
        <div class="flex items-center justify-between">
          <component :is="card.icon" class="w-5 h-5 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-bold mb-1">{{ stats[card.key] }}</div>
        <div class="text-xs text-muted-foreground">{{ card.label }}</div>
      </CardContent>
    </Card>
  </div>
</template>
