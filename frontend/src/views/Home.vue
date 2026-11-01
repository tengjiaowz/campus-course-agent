<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">系统首页</h2>
        <p class="page-sub">欢迎回来，这里是你的课程助手工作台。</p>
      </div>
    </div>
    <el-card class="page-card" shadow="never">
      <div style="font-size: 18px; color: #23302b">欢迎您：{{ userInfo?.name || '同学' }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { useUser } from '@/utils/user'
const { userInfo } = useUser()
</script>
