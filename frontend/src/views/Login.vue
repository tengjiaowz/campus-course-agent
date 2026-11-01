<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="login-title">校园课程智能助手</h1>
      <div class="login-sub">查课表、问资料、存计划</div>

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
        <div>
          <el-button
            size="large"
            type="primary"
            style="width: 100%"
            @click="login"
            :loading="loadingValue"
            >登 录</el-button
          >
          <div style="text-align: right; margin-top: 20px">
            还没有账号？请
            <router-link style="color: var(--el-color-primary)" to="/register">注册</router-link>
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'

const { saveLoginData } = useUser()

const formRef = ref()

const form = reactive({
  username: '',
  password: ''
})

const loadingValue = ref(false)

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const login = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loadingValue.value = true
  try {
    const res = await loginApi(form)
    if (res.code === 200) {
      saveLoginData(res.data)
      ElMessage.success('登录成功')
      await router.push('/manager/home')
    }
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background:
    radial-gradient(60% 55% at 12% 8%, rgba(31, 61, 52, 0.12), transparent 60%),
    radial-gradient(55% 50% at 88% 92%, rgba(179, 66, 47, 0.12), transparent 62%),
    var(--paper);
}
.login-box {
  width: 380px;
  border-radius: 12px;
  border: 1px solid var(--paper-line);
  box-shadow: 0 1px 2px rgba(35, 42, 33, 0.05), 0 28px 60px -46px rgba(35, 42, 33, 0.75);
  padding: 36px 32px 30px;
  text-align: center;
  background-color: var(--paper-card);
}
.login-title {
  font-size: 27px;
  letter-spacing: 0.05em;
  color: var(--forest);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", Georgia, serif;
}
.login-sub {
  margin-top: 8px;
  margin-bottom: 30px;
  font-size: 13px;
  letter-spacing: 0.08em;
  color: var(--ink-muted);
}
</style>
