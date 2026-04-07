<template>
  <div id="app">
    <el-container>
      <el-aside width="200px">
        <div class="logo">知识图谱QA</div>
        <el-menu
          :default-active="$route.path"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <template v-if="!isStudent">
            <el-menu-item index="/">
              <el-icon><Setting /></el-icon>
              <span>流程构建</span>
            </el-menu-item>
            <el-menu-item index="/kgqa">
              <el-icon><ChatDotRound /></el-icon>
              <span>图谱问答</span>
            </el-menu-item>
            <el-menu-item index="/students">
              <el-icon><User /></el-icon>
              <span>学生管理</span>
            </el-menu-item>
          </template>
          <template v-else>
            <el-menu-item index="/student-home">
              <el-icon><HomeFilled /></el-icon>
              <span>我的首页</span>
            </el-menu-item>
            <el-menu-item index="/kgqa">
              <el-icon><ChatDotRound /></el-icon>
              <span>图谱问答</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header>
          <h2>知识图谱问答系统</h2>
          <div class="user-info">
            <el-tag :type="isStudent ? 'primary' : 'success'" size="small">
              {{ isStudent ? '学生' : '管理员' }}
            </el-tag>
            <span class="username">{{ userInfo.real_name || userInfo.username }}</span>
            <el-button type="danger" size="small" @click="handleLogout">
              退出
            </el-button>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()
const userInfo = ref({})

const isStudent = computed(() => userInfo.value.role === 'student')

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

onMounted(() => {
  const stored = localStorage.getItem('user')
  if (stored) {
    userInfo.value = JSON.parse(stored)
  } else {
    router.push('/login')
  }
})
</script>

<style lang="scss" scoped>
#app {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #304156;
  
  .logo {
    height: 60px;
    line-height: 60px;
    text-align: center;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    background-color: #2b3a4a;
  }
}

.el-header {
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
  
  h2 {
    margin: 0;
    color: #333;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 10px;

    .username {
      color: #333;
      font-weight: 500;
    }
  }
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
