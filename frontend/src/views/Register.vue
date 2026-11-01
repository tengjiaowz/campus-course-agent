<template>
  <div class="register-container">
    <div class="register-box">
      <h1 class="register-title">注册校园课程智能助手账号</h1>

      <el-form ref="formRef" :rules="rules" :model="form" label-width="0px" style="width: 100%">
        <el-form-item prop="username">
          <el-input
            size="large"
            v-model="form.username"
            placeholder="请输入账号"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            type="password"
            size="large"
            v-model="form.password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            type="password"
            size="large"
            v-model="form.confirmPassword"
            placeholder="请确认密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <div>
          <el-button
            size="large"
            type="primary"
            :loading="loadingValue"
            style="width: 100%"
            @click="register"
            >注 册</el-button
          >
          <div style="text-align: right; margin-top: 20px">
            已有账号？请
            <router-link style="color: var(--el-color-primary)" to="/login">登录</router-link>
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { registerApi } from '@/api/auth'
import router from '@/router'

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const loadingValue = ref(false)

const formRef = ref()

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请确认密码'))
  } else {
    if (value !== form.password) {
      callback(new Error('两次密码输入不一致'))
    } else {
      callback()
    }
  }
}
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [{ validator: validatePass, trigger: 'blur' }]
}

const register = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loadingValue.value = true
  try {
    const res = await registerApi(form)
    if (res.code === 200) {
      ElMessage.success('注册成功')
      await router.push('/login')
    }
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.register-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background:
    radial-gradient(60% 55% at 12% 8%, rgba(31, 61, 52, 0.12), transparent 60%),
    radial-gradient(55% 50% at 88% 92%, rgba(179, 66, 47, 0.12), transparent 62%),
    var(--paper);
}
.register-box {
  width: 380px;
  border-radius: 12px;
  border: 1px solid var(--paper-line);
  box-shadow: 0 1px 2px rgba(35, 42, 33, 0.05), 0 28px 60px -46px rgba(35, 42, 33, 0.75);
  padding: 36px 32px 30px;
  text-align: center;
  background-color: var(--paper-card);
}
.register-title {
  font-size: 23px;
  margin-bottom: 30px;
  letter-spacing: 0.05em;
  color: var(--forest);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", Georgia, serif;
}
</style>
