<script setup lang="ts">
import { reactive, computed, onMounted } from 'vue'
import type { Prediction, TransactionFilters } from '@/types'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import DateRangePicker from './DateRangePicker.vue'
import TimeRangeSelector from './TimeRangeSelector.vue'
import { today, getLocalTimeZone } from '@internationalized/date'

const props = defineProps<{
  predictions: Prediction[]
}>()

const filters = reactive<TransactionFilters>({
  riskLevel: 'ALL',
  status: 'ALL',
  dateRange: {
    start: undefined,
    end: undefined
  },
  timeRange: {
    startHour: 0,
    startMinute: 0,
    endHour: 23,
    endMinute: 59
  }
})

// Set today's date as default on mount
onMounted(() => {
  const todayDate = today(getLocalTimeZone())
  filters.dateRange = {
    start: todayDate,
    end: todayDate
  }
})

const filteredPredictions = computed(() => {
  return props.predictions.filter(pred => {
    // Risk Level filter
    if (filters.riskLevel !== 'ALL' && pred.risk_level !== filters.riskLevel) {
      return false
    }
    
    // Status filter
    if (filters.status !== 'ALL' && pred.status !== filters.status) {
      return false
    }
    
    const predDate = new Date(pred.timestamp)
    
    // Date range filter
    if (filters.dateRange.start) {
      const startDate = filters.dateRange.start.toDate ? 
        filters.dateRange.start.toDate(getLocalTimeZone()) : 
        new Date(filters.dateRange.start.year, filters.dateRange.start.month - 1, filters.dateRange.start.day)
      startDate.setHours(0, 0, 0, 0)
      
      if (predDate < startDate) {
        return false
      }
    }
    
    if (filters.dateRange.end) {
      const endDate = filters.dateRange.end.toDate ? 
        filters.dateRange.end.toDate(getLocalTimeZone()) : 
        new Date(filters.dateRange.end.year, filters.dateRange.end.month - 1, filters.dateRange.end.day)
      endDate.setHours(23, 59, 59, 999)
      
      if (predDate > endDate) {
        return false
      }
    }
    
    // Time range filter (applies daily within the date range)
    const predHour = predDate.getHours()
    const predMinute = predDate.getMinutes()
    const predTimeInMinutes = predHour * 60 + predMinute
    const startTimeInMinutes = filters.timeRange.startHour * 60 + filters.timeRange.startMinute
    const endTimeInMinutes = filters.timeRange.endHour * 60 + filters.timeRange.endMinute
    
    // Handle time ranges that cross midnight (e.g., 22:00 - 06:00)
    if (startTimeInMinutes > endTimeInMinutes) {
      // Time range crosses midnight
      if (predTimeInMinutes < startTimeInMinutes && predTimeInMinutes > endTimeInMinutes) {
        return false
      }
    } else {
      // Normal time range within same day
      if (predTimeInMinutes < startTimeInMinutes || predTimeInMinutes > endTimeInMinutes) {
        return false
      }
    }
    
    return true
  })
})

const displayedPredictions = computed(() => {
  // Take last 100 items (sliding window), sort by time descending
  return filteredPredictions.value
    .slice(-100)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
})

const formatAmount = (amount: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount)
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}

const getRiskVariant = (level: string) => {
  switch (level) {
    case 'CRITICAL':
      return 'destructive'
    case 'HIGH':
      return 'secondary'
    case 'LOW':
      return 'outline'
    default:
      return 'default'
  }
}

const getStatusColor = (status: string) => {
  return status === 'APPROVE' ? 'text-green-600' : 'text-red-600'
}

const resetFilters = () => {
  filters.riskLevel = 'ALL'
  filters.status = 'ALL'
  const todayDate = today(getLocalTimeZone())
  filters.dateRange = {
    start: todayDate,
    end: todayDate
  }
  filters.timeRange = {
    startHour: 0,
    startMinute: 0,
    endHour: 23,
    endMinute: 59
  }
}
</script>

<template>
  <div>
    <!-- Filter Bar -->
    <div class="flex flex-wrap items-center gap-3 mb-4 p-3 bg-muted/20 rounded-lg border">
      <!-- Risk Level Select -->
      <Select v-model="filters.riskLevel">
        <SelectTrigger class="w-35">
          <SelectValue placeholder="Risk Level" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Risk Levels</SelectItem>
          <SelectItem value="CRITICAL">Critical</SelectItem>
          <SelectItem value="HIGH">High</SelectItem>
          <SelectItem value="LOW">Low</SelectItem>
        </SelectContent>
      </Select>

      <!-- Status Select -->
      <Select v-model="filters.status">
        <SelectTrigger class="w-35">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Statuses</SelectItem>
          <SelectItem value="APPROVE">Approved</SelectItem>
          <SelectItem value="DENY">Denied</SelectItem>
        </SelectContent>
      </Select>

      <!-- Date Range Picker -->
      <DateRangePicker v-model="filters.dateRange" />

      <!-- Time Range Selector -->
      <TimeRangeSelector v-model="filters.timeRange" />

      <!-- Reset Button -->
      <Button variant="outline" size="sm" @click="resetFilters">
        Reset
      </Button>

      <!-- Active Filter Count -->
      <span class="text-xs text-muted-foreground ml-auto">
        {{ filteredPredictions.length }} of {{ predictions.length }}
      </span>
    </div>

    <!-- Table with native scroll -->
    <div class="rounded-md border max-h-100  overflow-auto">
      <Table class="relative">
        <TableHeader class="sticky top-0 z-10 bg-background">
          <TableRow>
            <TableHead>Transaction ID</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Fraud Probability</TableHead>
            <TableHead>Risk Level</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="pred in displayedPredictions" :key="pred.TransactionID">
            <TableCell class="font-mono">#{{ pred.TransactionID }}</TableCell>
            <TableCell class="font-medium">{{ formatAmount(pred.TransactionAmt) }}</TableCell>
            <TableCell>{{ (pred.fraud_probability * 100).toFixed(2) }}%</TableCell>
            <TableCell>
              <Badge :variant="getRiskVariant(pred.risk_level)">
                {{ pred.risk_level }}
              </Badge>
            </TableCell>
            <TableCell>
              <span :class="getStatusColor(pred.status)">
                {{ pred.status }}
              </span>
            </TableCell>
            <TableCell class="text-muted-foreground text-xs">{{ formatTime(pred.timestamp) }}</TableCell>
          </TableRow>
          <TableRow v-if="filteredPredictions.length === 0">
            <TableCell colspan="6" class="text-center text-muted-foreground py-8">
              Waiting for predictions...
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
