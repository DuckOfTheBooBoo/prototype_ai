<script setup lang="ts">
import { computed } from 'vue'
import { CalendarIcon } from 'lucide-vue-next'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { DateRange } from 'radix-vue'

const props = defineProps<{
  modelValue: DateRange
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DateRange]
}>()

const date = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const displayText = computed(() => {
  if (!date.value.start) {
    return 'Select date range'
  }
  
  const formatDate = (d: any) => {
    const jsDate = d.toDate ? d.toDate('UTC') : new Date(d.year, d.month - 1, d.day)
    return jsDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }
  
  if (date.value.end) {
    return `${formatDate(date.value.start)} - ${formatDate(date.value.end)}`
  }
  
  return formatDate(date.value.start)
})
</script>

<template>
  <Popover>
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        :class="cn(
          'w-[280px] justify-start text-left font-normal',
          !date.start && 'text-muted-foreground'
        )"
      >
        <CalendarIcon class="mr-2 h-4 w-4" />
        {{ displayText }}
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-auto p-0" align="start">
      <Calendar v-model="date" :number-of-months="2" />
    </PopoverContent>
  </Popover>
</template>
