<template>
  <div class="container config-view">
    <div class="toolbar">
      <h2 class="title">Configuration</h2>
      <div class="toolbar-actions">
        <select v-model="selectedConfig" class="input select-config">
          <option value="prometheus-signature">Prometheus signature</option>
        </select>
        <button class="btn btn-secondary" @click="loadConfig" :disabled="loading">
          <span v-if="loading" class="loading"></span>
          <span v-else>Reload</span>
        </button>
        <button class="btn btn-primary" @click="saveConfig" :disabled="saving || !editorValue">
          <span v-if="saving" class="loading"></span>
          <span v-else>Save</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="error-box">
      {{ error }}
    </div>

    <div class="editor-wrapper">
      <textarea
        v-model="editorValue"
        class="code-editor"
        spellcheck="false"
      ></textarea>
    </div>

    <p class="hint">
      YAML syntax is checked locally before saving. If the content is not valid YAML, you will see an error.
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import yaml from 'js-yaml'
import { configApi } from '../services/api'

const selectedConfig = ref('prometheus-signature')
const editorValue = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const loadConfig = async () => {
  loading.value = true
  error.value = null
  try {
    if (selectedConfig.value === 'prometheus-signature') {
      const content = await configApi.getSignature()
      editorValue.value = content
    }
  } catch (e: any) {
    console.error('Failed to load config:', e)
    const msg = e.response?.data?.detail || e.message || 'Failed to load config'
    error.value = msg
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  if (!editorValue.value) {
    return
  }
  error.value = null

  // простая проверка YAML перед отправкой
  try {
    yaml.load(editorValue.value)
  } catch (e: any) {
    error.value = `YAML error: ${e.message || String(e)}`
    return
  }

  saving.value = true
  try {
    if (selectedConfig.value === 'prometheus-signature') {
      await configApi.updateSignature(editorValue.value)
    }
    alert('Configuration saved')
  } catch (e: any) {
    console.error('Failed to save config:', e)
    const msg = e.response?.data?.detail || e.message || 'Failed to save config'
    error.value = msg
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-view {
  padding: 16px 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.title {
  font-size: 20px;
  font-weight: 600;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.select-config {
  min-width: 200px;
}

.editor-wrapper {
  margin-top: 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}

.code-editor {
  width: 100%;
  min-height: 400px;
  padding: 12px;
  background-color: #111827;
  color: #e5e7eb;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  border: none;
  outline: none;
  resize: vertical;
  white-space: pre;
}

.code-editor::selection {
  background-color: rgba(96, 165, 250, 0.4);
}

.error-box {
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #b91c1c;
  background-color: #7f1d1d;
  color: #fee2e2;
  font-size: 13px;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>


