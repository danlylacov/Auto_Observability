<template>
  <Transition name="modal">
    <div v-if="visible" class="modal-backdrop" @click.self="handleCancel">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">{{ title }}</h3>
          <button @click="handleCancel" class="btn-close" title="Close">×</button>
        </div>
        
        <div class="modal-body">
          <p class="modal-message">{{ message }}</p>
          <div v-if="details" class="modal-details">
            <p class="details-text">{{ details }}</p>
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            @click="handleCancel" 
            class="btn btn-secondary"
            :disabled="loading"
          >
            {{ cancelText }}
          </button>
          <button 
            @click="handleConfirm" 
            class="btn"
            :class="confirmButtonClass"
            :disabled="loading"
          >
            <span v-if="loading" class="loading"></span>
            <span v-else>{{ confirmText }}</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
  visible?: boolean
  title?: string
  message: string
  details?: string
  confirmText?: string
  cancelText?: string
  type?: 'warning' | 'danger' | 'info'
  loading?: boolean
}>(), {
  visible: false,
  title: 'Confirm',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  type: 'warning',
  loading: false
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const confirmButtonClass = computed(() => {
  if (props.type === 'danger') return 'btn-danger'
  if (props.type === 'warning') return 'btn-warning'
  return 'btn-primary'
})

const handleConfirm = () => {
  if (!props.loading) {
    emit('confirm')
  }
}

const handleCancel = () => {
  if (!props.loading) {
    emit('cancel')
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(2px);
}

.modal-dialog {
  background: var(--bg-card);
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: 28px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
  line-height: 1;
}

.btn-close:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.modal-message {
  font-size: 16px;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  line-height: 1.5;
}

.modal-details {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border-left: 3px solid var(--warning-bg, #f59e0b);
}

.details-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}

.btn {
  padding: 10px 20px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:hover:not(:disabled) {
  background: var(--bg-secondary);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color, #007bff);
  color: white;
  border-color: var(--primary-color, #007bff);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover, #0056b3);
}

.btn-secondary {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
}

.btn-warning {
  background: var(--warning-bg, #f59e0b);
  color: white;
  border-color: var(--warning-bg, #f59e0b);
}

.btn-warning:hover:not(:disabled) {
  background: var(--warning-hover, #d97706);
}

.btn-danger {
  background: var(--danger-bg, #dc3545);
  color: white;
  border-color: var(--danger-bg, #dc3545);
}

.btn-danger:hover:not(:disabled) {
  background: var(--danger-hover, #c82333);
}

.loading {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-dialog,
.modal-leave-active .modal-dialog {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-dialog,
.modal-leave-to .modal-dialog {
  transform: scale(0.9);
  opacity: 0;
}
</style>




