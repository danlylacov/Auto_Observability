<template>
  <div ref="editorRef" class="code-block"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { yaml } from '@codemirror/lang-yaml'
import { oneDark } from '@codemirror/theme-one-dark'

const props = defineProps<{
  code: string
  language?: string
  readOnly?: boolean
}>()

const editorRef = ref<HTMLDivElement | null>(null)
let view: EditorView | null = null

const createEditor = () => {
  if (!editorRef.value) return

  // Destroy existing editor if any
  if (view) {
    view.destroy()
    view = null
  }

  const state = EditorState.create({
    doc: props.code || '',
    extensions: [
      yaml(),
      EditorView.editable.of(!props.readOnly),
      EditorView.theme({
        '&': {
          fontSize: '13px',
          fontFamily: 'Monaco, "Courier New", monospace'
        },
        '.cm-content': {
          padding: '12px'
        },
        '.cm-scroller': {
          overflow: 'auto'
        }
      }),
      oneDark
    ]
  })

  view = new EditorView({
    state,
    parent: editorRef.value
  })
}

const updateEditor = () => {
  if (view && props.code !== view.state.doc.toString()) {
    view.dispatch({
      changes: {
        from: 0,
        to: view.state.doc.length,
        insert: props.code || ''
      }
    })
  }
}

onMounted(() => {
  createEditor()
})

watch(() => props.code, () => {
  if (view) {
    updateEditor()
  } else if (editorRef.value) {
    createEditor()
  }
}, { immediate: false })

onBeforeUnmount(() => {
  view?.destroy()
})
</script>

<style scoped>
.code-block {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.code-block :deep(.cm-editor) {
  background: transparent;
}

.code-block :deep(.cm-scroller) {
  font-family: 'Monaco', 'Courier New', monospace;
}
</style>

