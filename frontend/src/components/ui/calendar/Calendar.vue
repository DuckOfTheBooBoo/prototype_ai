<script setup lang="ts">
import {
  RangeCalendarRoot,
  type RangeCalendarRootEmits,
  type RangeCalendarRootProps,
  RangeCalendarHeading,
  RangeCalendarGrid,
  RangeCalendarGridHead,
  RangeCalendarGridBody,
  RangeCalendarGridRow,
  RangeCalendarHeadCell,
  RangeCalendarCell,
  RangeCalendarCellTrigger,
  RangeCalendarNext,
  RangeCalendarPrev,
  useForwardPropsEmits,
} from 'radix-vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<RangeCalendarRootProps & { class?: string }>(),
  {
    numberOfMonths: 2,
  }
)

const emits = defineEmits<RangeCalendarRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <RangeCalendarRoot
    v-slot="{ grid, weekDays }"
    :class="cn('p-3', props.class)"
    v-bind="forwarded"
  >
    <div class="flex flex-col gap-y-4 sm:flex-row sm:gap-x-4 sm:gap-y-0">
      <div v-for="month in grid" :key="month.value.toString()" class="relative">
        <RangeCalendarHeading class="flex w-full items-center justify-between pt-1">
          <RangeCalendarPrev
            class="inline-flex h-7 w-7 items-center justify-center rounded-md border border-input bg-transparent p-0 opacity-50 transition-colors hover:bg-accent hover:text-accent-foreground hover:opacity-100 focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            <ChevronLeft class="h-4 w-4" />
          </RangeCalendarPrev>

          <div class="text-sm font-medium">
            {{ new Date(month.value.year, month.value.month - 1).toLocaleString('en-US', { month: 'long', year: 'numeric' }) }}
          </div>

          <RangeCalendarNext
            class="inline-flex h-7 w-7 items-center justify-center rounded-md border border-input bg-transparent p-0 opacity-50 transition-colors hover:bg-accent hover:text-accent-foreground hover:opacity-100 focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            <ChevronRight class="h-4 w-4" />
          </RangeCalendarNext>
        </RangeCalendarHeading>

        <RangeCalendarGrid class="mt-4">
          <RangeCalendarGridHead>
            <RangeCalendarGridRow class="mb-1 flex w-full justify-between">
              <RangeCalendarHeadCell
                v-for="day in weekDays"
                :key="day"
                class="w-8 text-xs font-normal text-muted-foreground"
              >
                {{ day }}
              </RangeCalendarHeadCell>
            </RangeCalendarGridRow>
          </RangeCalendarGridHead>
          <RangeCalendarGridBody>
            <RangeCalendarGridRow
              v-for="(weekDates, index) in month.rows"
              :key="`weekDate-${index}`"
              class="mt-1 flex w-full justify-between"
            >
              <RangeCalendarCell
                v-for="weekDate in weekDates"
                :key="weekDate.toString()"
                :date="weekDate"
                class="relative h-8 w-8 p-0 text-center text-sm focus-within:relative focus-within:z-20 [&:has([data-selected])]:rounded-md [&:has([data-selected])]:bg-accent [&:has([data-selected][data-selection-start])]:rounded-l-md [&:has([data-selected][data-selection-end])]:rounded-r-md [&:has([data-selected][data-outside-view])]:bg-accent/50"
              >
                <RangeCalendarCellTrigger
                  :day="weekDate"
                  :month="month.value"
                  class="inline-flex h-8 w-8 items-center justify-center rounded-md p-0 text-sm font-normal ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[disabled]:text-muted-foreground data-[selected]:bg-primary data-[selected]:text-primary-foreground data-[selected]:opacity-100 data-[selection-start]:rounded-l-md data-[selection-end]:rounded-r-md data-[outside-view]:text-muted-foreground data-[outside-view]:opacity-50"
                />
              </RangeCalendarCell>
            </RangeCalendarGridRow>
          </RangeCalendarGridBody>
        </RangeCalendarGrid>
      </div>
    </div>
  </RangeCalendarRoot>
</template>
