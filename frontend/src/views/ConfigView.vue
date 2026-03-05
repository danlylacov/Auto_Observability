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
      <div ref="editorRef" class="code-editor-container"></div>
    </div>

    <p class="hint">
      YAML syntax is checked locally before saving. If the content is not valid YAML, you will see an error.
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, onBeforeUnmount } from 'vue'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { yaml } from '@codemirror/lang-yaml'
import { oneDark } from '@codemirror/theme-one-dark'
import { keymap } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { foldGutter, foldKeymap, syntaxHighlighting, defaultHighlightStyle, bracketMatching } from '@codemirror/language'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import { closeBrackets, autocompletion, closeBracketsKeymap, completionKeymap } from '@codemirror/autocomplete'
import { lintKeymap } from '@codemirror/lint'
import yamlLib from 'js-yaml'
import { configApi } from '../services/api'

const selectedConfig = ref('prometheus-signature')
const editorValue = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const editorRef = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null

const loadConfig = async () => {
  loading.value = true
  error.value = null
  try {
    if (selectedConfig.value === 'prometheus-signature') {
      let content = await configApi.getSignature()
      
      // Если контент является JSON строкой, пытаемся преобразовать в YAML
      if (content.trim().startsWith('{')) {
        try {
          const parsed = JSON.parse(content)
          // Если это объект с ключом "signature.yml", извлекаем значение
          if (parsed && typeof parsed === 'object' && 'signature.yml' in parsed) {
            content = parsed['signature.yml']
          } else {
            // Преобразуем объект в YAML
            content = yamlLib.dump(parsed, { 
              indent: 2,
              lineWidth: -1,
              noRefs: true
            })
          }
        } catch (parseError) {
          // Если не удалось распарсить как JSON, используем как есть
          console.warn('Failed to parse as JSON, using as-is:', parseError)
        }
      }
      
      editorValue.value = content
      updateEditor(content)
    }
  } catch (e: any) {
    console.error('Failed to load config:', e)
    const msg = e.response?.data?.detail || e.message || 'Failed to load config'
    error.value = msg
  } finally {
    loading.value = false
  }
}

const updateEditor = (content: string) => {
  if (!editorView) return
  
  editorView.dispatch({
    changes: {
      from: 0,
      to: editorView.state.doc.length,
      insert: content
    }
  })
}

const initEditor = () => {
  if (!editorRef.value) return

  const startState = EditorState.create({
    doc: editorValue.value,
    extensions: [
      history(),
      foldGutter(),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      highlightSelectionMatches(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      yaml(),
      oneDark,
      keymap.of([
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        ...lintKeymap,
      ]),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          editorValue.value = update.state.doc.toString()
        }
      }),
      EditorView.theme({
        '&': {
          height: '100%',
          fontSize: '14px',
        },
        '.cm-scroller': {
          fontFamily: "'Fira Code', 'Courier New', monospace",
          overflow: 'auto',
        },
        '.cm-editor': {
          height: '100%',
        },
        '.cm-content': {
          padding: '16px',
          minHeight: '400px',
        },
        '.cm-gutters': {
          backgroundColor: '#1a1a1a',
          borderRight: '1px solid #333',
        },
        '.cm-lineNumbers .cm-lineNumber': {
          color: '#888',
          padding: '0 8px',
          minWidth: '3ch',
        },
        '.cm-activeLine': {
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
        },
        '.cm-activeLineGutter': {
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
        },
        '.cm-selectionBackground': {
          backgroundColor: 'rgba(96, 165, 250, 0.3)',
        },
        '.cm-cursor': {
          borderLeftColor: '#60a5fa',
          borderLeftWidth: '2px',
        },
        '.cm-focused': {
          outline: 'none',
        },
        '.cm-foldGutter': {
          width: '16px',
        },
        '.cm-foldPlaceholder': {
          backgroundColor: 'transparent',
          border: 'none',
          color: '#888',
        },
      }),
    ],
  })

  editorView = new EditorView({
    state: startState,
    parent: editorRef.value,
  })
}

const saveConfig = async () => {
  if (!editorValue.value) {
    return
  }
  error.value = null

  // простая проверка YAML перед отправкой
  try {
    yamlLib.load(editorValue.value)
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
  initEditor()
  loadConfig()
})

onBeforeUnmount(() => {
  if (editorView) {
    editorView.destroy()
  }
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
  background-color: #1e1e1e;
  min-height: 500px;
  height: calc(100vh - 300px);
  max-height: 800px;
}

.code-editor-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.error-box {
  margin-bottom: 8px;
  padding: 12px 16px;
  border-radius: 6px;
  border: 1px solid #b91c1c;
  background-color: rgba(185, 28, 28, 0.1);
  color: #fee2e2;
  font-size: 13px;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
