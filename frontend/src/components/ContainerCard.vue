<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">{{ containerName }}</h3>
      <span :class="['badge', statusBadgeClass]">{{ status }}</span>
    </div>
    <div class="card-body">
      <div class="info-row">
        <span class="label">Image:</span>
        <span class="value">{{ image }}</span>
      </div>
      <div class="info-row" v-if="stack">
        <span class="label">Stack:</span>
        <span class="value">{{ stack }}</span>
      </div>
      <div class="info-row">
        <span class="label">ID:</span>
        <span class="value text-xs">{{ shortId }}</span>
      </div>
    </div>
    <div class="card-actions">
      <button 
        v-if="status === 'running'"
        @click="$emit('stop')" 
        class="btn btn-danger"
        :disabled="loading"
      >
        Stop
      </button>
      <button 
        v-else
        @click="$emit('start')" 
        class="btn btn-success"
        :disabled="loading"
      >
        Start
      </button>
      <button 
        @click="$emit('remove')" 
        class="btn btn-secondary"
        :disabled="loading"
      >
        Remove
      </button>
      <button 
        @click="$emit('view-details')" 
        class="btn btn-primary"
      >
        Details
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  containerId: string
  containerName: string
  status: string
  image: string
  stack?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  start: []
  stop: []
  remove: []
  'view-details': []
}>()

const shortId = computed(() => props.containerId.substring(0, 12))

const statusBadgeClass = computed(() => {
  if (props.status === 'running') return 'badge-success'
  return 'badge-error'
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-body {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.label {
  color: var(--text-secondary);
}

.value {
  color: var(--text-primary);
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>

