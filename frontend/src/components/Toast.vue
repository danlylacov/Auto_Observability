<template>
  <TransitionGroup name="toast" tag="div" class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      :class="['toast', `toast-${toast.type}`]"
    >
      <div class="toast-content">
        <span class="toast-message">{{ toast.message }}</span>
      </div>
      <button @click="removeToast(toast.id)" class="toast-close">×</button>
    </div>
  </TransitionGroup>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration?: number
}

const toasts = ref<Toast[]>([])
let toastIdCounter = 0

const showToast = (message: string, type: Toast['type'] = 'info', duration: number = 5000) => {
  const id = toastIdCounter++
  const toast: Toast = { id, message, type, duration }
  toasts.value.push(toast)

  if (duration > 0) {
    setTimeout(() => {
      removeToast(id)
    }, duration)
  }
}

const removeToast = (id: number) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

// Expose methods globally
onMounted(() => {
  ;(window as any).showToast = showToast
})

defineExpose({
  showToast,
  removeToast
})
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 300px;
  max-width: 500px;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background: var(--bg-card);
  border: 1px solid var(--border);
  pointer-events: auto;
  animation: slideIn 0.3s ease-out;
}

.toast-success {
  background: var(--success-bg, #d4edda);
  border-color: var(--success-border, #c3e6cb);
  color: var(--success-text, #155724);
}

.toast-error {
  background: var(--error-bg, #f8d7da);
  border-color: var(--error-border, #f5c6cb);
  color: var(--error-text, #721c24);
}

.toast-info {
  background: var(--info-bg, #d1ecf1);
  border-color: var(--info-border, #bee5eb);
  color: var(--info-text, #0c5460);
}

.toast-warning {
  background: var(--warning-bg, #fff3cd);
  border-color: var(--warning-border, #ffeaa7);
  color: var(--warning-text, #856404);
}

.toast-content {
  flex: 1;
  display: flex;
  align-items: center;
}

.toast-message {
  font-size: 14px;
  line-height: 1.5;
}

.toast-close {
  background: none;
  border: none;
  font-size: 20px;
  color: inherit;
  cursor: pointer;
  padding: 0;
  margin-left: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.toast-close:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast-leave-active {
  transition: all 0.3s ease-in;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>

