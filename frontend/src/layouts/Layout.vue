<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header class="app-header">
        <div class="brand">
          <img class="brand-logo" src="@/assets/imgs/logo.png" alt="" />
          <div class="brand-title">校园课程智能助手</div>
        </div>
        <div>
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">{{ userInfo?.name }}</div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px" class="app-aside">
          <el-menu class="app-menu" router :default-active="router.currentRoute.value.path">
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>
            <el-menu-item index="/manager/chat">
              <el-icon><ChatDotRound /></el-icon>
              <span>课程助手</span>
            </el-menu-item>
            <el-menu-item index="/manager/schedule" v-if="userInfo?.role === 'student'">
              <el-icon><Reading /></el-icon>
              <span>我的课表</span>
            </el-menu-item>
            <el-menu-item index="/manager/study-plan" v-if="userInfo?.role === 'student'">
              <el-icon><Notebook /></el-icon>
              <span>学习计划</span>
            </el-menu-item>
            <el-menu-item index="/manager/schedule-manage" v-if="userInfo?.role === 'admin'">
              <el-icon><Reading /></el-icon>
              <span>课表管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/course" v-if="userInfo?.role === 'admin'">
              <el-icon><Calendar /></el-icon>
              <span>课程管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/documents" v-if="userInfo?.role === 'admin'">
              <el-icon><Document /></el-icon>
              <span>文档管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
import {
  Menu as IconMenu,
  User,
  Reading,
  Calendar,
  Notebook,
  ChatDotRound,
  Document
} from '@element-plus/icons-vue'

const { userInfo } = useUser()

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 24px;
  background: var(--paper-card);
  border-bottom: 1px solid var(--paper-line);
}

.brand {
  flex: 1;
  display: flex;
  align-items: center;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  object-fit: cover;
  box-shadow: 0 0 0 1px var(--paper-line);
}

.brand-title {
  margin-left: 10px;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: var(--forest);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", Georgia, serif;
}

.app-aside {
  background: var(--forest);
}

.app-menu {
  height: 100%;
  padding: 10px 12px;
  border-right: none;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(242, 239, 227, 0.72);
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.08);
  --el-menu-active-color: var(--forest);
}

.app-menu :deep(.el-menu-item) {
  height: 44px;
  margin-bottom: 4px;
  border-radius: 10px;
  font-size: 13.5px;
}

.app-menu :deep(.el-menu-item:hover) {
  color: #f4f0e5;
}

.app-menu :deep(.el-menu-item.is-active) {
  background: #f2efe3;
  color: var(--forest);
  font-weight: 600;
}

.app-main {
  padding: 22px 24px 28px;
  background: var(--paper);
}
</style>
