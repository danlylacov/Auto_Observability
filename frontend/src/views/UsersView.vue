<template>
  <div class="container users-view">
    <h2 class="title">Пользователи</h2>
    <p class="hint">Создание учётных записей доступно только роли maintainer.</p>

    <div v-if="loading" class="loading-state">
      <div class="loading"></div>
    </div>
    <template v-else>
      <table class="table" v-if="users.length">
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Роль</th>
            <th>Активен</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.role }}</td>
            <td>{{ u.is_active ? 'да' : 'нет' }}</td>
          </tr>
        </tbody>
      </table>

      <h3 class="subtitle">Новый пользователь</h3>
      <form class="create-form" @submit.prevent="createUser">
        <input v-model="newUsername" class="input" placeholder="Логин" required />
        <input v-model="newPassword" type="password" class="input" placeholder="Пароль" required />
        <select v-model="newRole" class="input" style="width: auto">
          <option value="admin">admin</option>
          <option value="dev">dev</option>
          <option value="user">user</option>
        </select>
        <button type="submit" class="btn btn-primary" :disabled="saving">
          <span v-if="saving" class="loading"></span>
          <span v-else>Создать</span>
        </button>
      </form>
      <p v-if="formError" class="error">{{ formError }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usersAdminApi, type UserRow } from '../services/api'
import { showToast } from '../utils/toast'

const users = ref<UserRow[]>([])
const loading = ref(true)
const saving = ref(false)
const newUsername = ref('')
const newPassword = ref('')
const newRole = ref<'admin' | 'dev' | 'user'>('dev')
const formError = ref('')

async function load() {
  loading.value = true
  try {
    users.value = await usersAdminApi.list()
  } finally {
    loading.value = false
  }
}

async function createUser() {
  formError.value = ''
  saving.value = true
  try {
    await usersAdminApi.create({
      username: newUsername.value.trim(),
      password: newPassword.value,
      role: newRole.value
    })
    newUsername.value = ''
    newPassword.value = ''
    showToast('Пользователь создан', 'success')
    await load()
  } catch (e: unknown) {
    formError.value = 'Не удалось создать (проверьте уникальность логина и права).'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.users-view {
  padding-top: 16px;
}

.title {
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 20px;
}

.subtitle {
  margin: 24px 0 12px;
  font-size: 16px;
}

.create-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  max-width: 720px;
}

.error {
  color: #e74c3c;
  margin-top: 10px;
}

.table {
  width: 100%;
  max-width: 720px;
  border-collapse: collapse;
}

.table th,
.table td {
  border: 1px solid var(--border);
  padding: 8px 10px;
  text-align: left;
}
</style>
