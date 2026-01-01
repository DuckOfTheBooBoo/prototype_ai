<script setup lang="ts">
import { computed } from 'vue'
import { Clock } from 'lucide-vue-next'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

export interface TimeRange {
  startHour: number
  startMinute: number
  endHour: number
  endMinute: number
}

const props = defineProps<{
  modelValue: TimeRange
}>()

const emit = defineEmits<{
  'update:modelValue': [value: TimeRange]
}>()

const timeRange = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Generate hour and minute options
const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'))

const updateStartHour = (value: any) => {
  if (value !== null && value !== undefined) {
    const numValue = typeof value === 'string' ? parseInt(value) : Number(value)
    timeRange.value = { ...timeRange.value, startHour: numValue }
  }
}

const updateStartMinute = (value: any) => {
  if (value !== null && value !== undefined) {
    const numValue = typeof value === 'string' ? parseInt(value) : Number(value)
    timeRange.value = { ...timeRange.value, startMinute: numValue }
  }
}

const updateEndHour = (value: any) => {
  if (value !== null && value !== undefined) {
    const numValue = typeof value === 'string' ? parseInt(value) : Number(value)
    timeRange.value = { ...timeRange.value, endHour: numValue }
  }
}

const updateEndMinute = (value: any) => {
  if (value !== null && value !== undefined) {
    const numValue = typeof value === 'string' ? parseInt(value) : Number(value)
    timeRange.value = { ...timeRange.value, endMinute: numValue }
  }
}

// Quick presets
const applyPreset = (preset: string) => {
  switch (preset) {
    case 'all-day':
      timeRange.value = { startHour: 0, startMinute: 0, endHour: 23, endMinute: 59 }
      break
    case 'business':
      timeRange.value = { startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }
      break
    case 'after-hours':
      timeRange.value = { startHour: 17, startMinute: 0, endHour: 9, endMinute: 0 }
      break
    case 'night':
      timeRange.value = { startHour: 22, startMinute: 0, endHour: 6, endMinute: 0 }
      break
  }
}

const displayText = computed(() => {
  const { startHour, startMinute, endHour, endMinute } = timeRange.value
  const format = (h: number, m: number) => `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
  
  // Check if it's all day
  if (startHour === 0 && startMinute === 0 && endHour === 23 && endMinute === 59) {
    return 'All Day'
  }
  
  return `${format(startHour, startMinute)} - ${format(endHour, endMinute)}`
})

const isCustomTime = computed(() => {
  const { startHour, startMinute, endHour, endMinute } = timeRange.value
  
  // Check if matches any preset
  if (startHour === 0 && startMinute === 0 && endHour === 23 && endMinute === 59) return false
  if (startHour === 9 && startMinute === 0 && endHour === 17 && endMinute === 0) return false
  if (startHour === 17 && startMinute === 0 && endHour === 9 && endMinute === 0) return false
  if (startHour === 22 && startMinute === 0 && endHour === 6 && endMinute === 0) return false
  
  return true
})
</script>

<template>
  <Popover>
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        :class="cn(
          'w-[200px] justify-start text-left font-normal',
          isCustomTime && 'border-primary'
        )"
      >
        <Clock class="mr-2 h-4 w-4" />
        {{ displayText }}
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-[340px]" align="start">
      <div class="space-y-4">
        <!-- Quick Presets -->
        <div class="space-y-2">
          <div class="text-sm font-medium">Quick Presets</div>
          <div class="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              class="justify-start"
              @click="applyPreset('all-day')"
            >
              All Day
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="justify-start"
              @click="applyPreset('business')"
            >
              Business Hours
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="justify-start"
              @click="applyPreset('after-hours')"
            >
              After Hours
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="justify-start"
              @click="applyPreset('night')"
            >
              Night
            </Button>
          </div>
        </div>

        <div class="border-t pt-4">
          <div class="text-sm font-medium mb-3">Custom Time Range</div>
          
          <!-- Start Time -->
          <div class="space-y-2 mb-4">
            <div class="text-xs text-muted-foreground">Start Time</div>
            <div class="flex gap-2">
              <Select :model-value="timeRange.startHour.toString().padStart(2, '0')" @update:model-value="updateStartHour">
                <SelectTrigger class="w-[80px]">
                  <SelectValue placeholder="Hour" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="hour in hours" :key="hour" :value="hour">
                    {{ hour }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <span class="flex items-center text-muted-foreground">:</span>
              <Select :model-value="timeRange.startMinute.toString().padStart(2, '0')" @update:model-value="updateStartMinute">
                <SelectTrigger class="w-[80px]">
                  <SelectValue placeholder="Min" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="minute in minutes" :key="minute" :value="minute">
                    {{ minute }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <!-- End Time -->
          <div class="space-y-2">
            <div class="text-xs text-muted-foreground">End Time</div>
            <div class="flex gap-2">
              <Select :model-value="timeRange.endHour.toString().padStart(2, '0')" @update:model-value="updateEndHour">
                <SelectTrigger class="w-[80px]">
                  <SelectValue placeholder="Hour" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="hour in hours" :key="hour" :value="hour">
                    {{ hour }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <span class="flex items-center text-muted-foreground">:</span>
              <Select :model-value="timeRange.endMinute.toString().padStart(2, '0')" @update:model-value="updateEndMinute">
                <SelectTrigger class="w-[80px]">
                  <SelectValue placeholder="Min" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="minute in minutes" :key="minute" :value="minute">
                    {{ minute }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>
    </PopoverContent>
  </Popover>
</template>
