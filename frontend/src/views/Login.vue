<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h1>知识图谱问答系统</h1>
        <p>离散数学与信息安全课程知识图谱</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password />
            </el-form-item>
            <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-alert
            v-if="activeTab === 'register'"
            title="注册说明"
            type="info"
            description="注册需要邀请码，请联系老师获取"
            :closable="false"
            show-icon
            class="mb-15"
          />
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-position="top">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password />
            </el-form-item>
            <el-form-item label="姓名" prop="realName">
              <el-input v-model="registerForm.realName" placeholder="请输入真实姓名" />
            </el-form-item>
            <el-form-item label="邀请码" prop="inviteCode">
              <el-input v-model="registerForm.inviteCode" placeholder="请输入邀请码（必填）" />
            </el-form-item>
            <el-button type="primary" class="login-btn" @click="handleRegister" :loading="loading">
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  realName: '',
  inviteCode: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  inviteCode: [{ required: true, message: '请输入邀请码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    const response = await axios.post('http://localhost:8000/api/auth/login', {
      username: loginForm.username,
      password: loginForm.password
    })

    localStorage.setItem('token', response.access_token)
    localStorage.setItem('user', JSON.stringify(response.user))

    ElMessage.success('登录成功')
    
    if (response.user.role === 'teacher') {
      router.push('/')
    } else {
      router.push('/student-home')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.password) {
    ElMessage.warning('请填写完整信息')
    return
  }

  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.warning('两次输入密码不一致')
    return
  }

  if (!registerForm.inviteCode) {
    ElMessage.warning('请输入邀请码')
    return
  }

  loading.value = true
  try {
    const response = await axios.post('http://localhost:8000/api/auth/register', {
      username: registerForm.username,
      password: registerForm.password,
      real_name: registerForm.realName,
      invite_code: registerForm.inviteCode
    })

    ElMessage.success(`注册成功！您的角色是：${response.role === 'teacher' ? '老师' : '学生'}`)
    activeTab.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,.2);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  margin: 0 0 10px;
  font-size: 24px;
  color: #333;
}

.login-header p {
  margin: 0;
  color: #999;
  font-size: 14px;
}

.login-tabs {
  margin-top: 20px;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
  height: 45px;
  font-size: 16px;
}

.mb-15 {
  margin-bottom: 15px;
}
</style>
