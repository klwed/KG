<template>
  <div class="page-card student-home">
    <div class="header">
      <h3>欢迎，{{ userInfo.real_name || userInfo.username }}</h3>
      <el-button @click="logout" size="small">退出登录</el-button>
    </div>

    <el-alert
      title="当前用户：学生"
      type="info"
      description="您只能查看本人的知识点掌握情况"
      :closable="false"
      show-icon
      class="mb-20"
    />

    <div class="main-content">
      <!-- 个人掌握情况 -->
      <el-card shadow="hover">
        <template #header>
          <span>我的知识点掌握情况</span>
        </template>
        
        <div v-if="myScores">
          <div class="score-overview">
            <div class="score-circle">
              <el-progress type="circle" :percentage="myScores.avgScore * 100" :width="120">
                <template #default>
                  <span class="score-text">{{ (myScores.avgScore * 100).toFixed(0) }}%</span>
                  <span class="score-label">平均</span>
                </template>
              </el-progress>
            </div>
            <div class="score-info">
              <p>总评：<el-tag :type="getLevelType(myScores.level)">{{ myScores.level }}</el-tag></p>
              <p>强项：<el-tag v-for="t in myScores.strong" :key="t" type="success" size="small" class="mr-5">{{ t }}</el-tag></p>
              <p>薄弱点：<el-tag v-for="t in myScores.weak" :key="t" type="danger" size="small" class="mr-5">{{ t }}</el-tag></p>
            </div>
          </div>

          <el-divider />

          <h4>各知识点详情</h4>
          <el-table :data="myScores.details" stripe size="small">
            <el-table-column prop="topic" label="知识点" width="120" />
            <el-table-column prop="score" label="得分" width="200">
              <template #default="{ row }">
                <el-progress :percentage="row.score * 100" :color="getProgressColor(row.score)" />
              </template>
            </el-table-column>
            <el-table-column prop="level" label="等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ct" label="计算思维" />
          </el-table>
        </div>

        <el-empty v-else description="暂无数据，请联系老师上传您的成绩" />
      </el-card>

      <!-- 图谱展示 -->
      <el-card shadow="hover" class="mt-20">
        <template #header>
          <span>知识图谱探索</span>
        </template>
        <div class="graph-area" ref="graphRef"></div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { studentApi } from '@/api'

const router = useRouter()
const userInfo = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const myScores = ref(null)
const graphRef = ref(null)

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

const loadMyScores = async () => {
  try {
    const res = await studentApi.getMyScores(userInfo.value.username)
    if (res && res.scores) {
      myScores.value = res.scores
    }
  } catch (e) {
    console.error(e)
  }
}

const getLevelType = (level) => {
  const types = { '优秀': 'success', '良好': 'primary', '一般': 'warning', '较差': 'danger', '很差': 'danger' }
  return types[level] || 'info'
}

const getProgressColor = (score) => {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  if (!localStorage.getItem('token')) {
    router.push('/login')
    return
  }
  loadMyScores()
})
</script>

<style scoped>
.student-home {
  min-height: calc(100vh - 140px);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h3 {
    margin: 0;
  }
}

.mb-20 {
  margin-bottom: 20px;
}

.mt-20 {
  margin-top: 20px;
}

.mr-5 {
  margin-right: 5px;
}

.score-overview {
  display: flex;
  gap: 40px;
  align-items: center;

  .score-circle {
    .score-text {
      display: block;
      font-size: 24px;
      font-weight: bold;
    }

    .score-label {
      display: block;
      font-size: 12px;
      color: #999;
    }
  }

  .score-info {
    p {
      margin: 8px 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }
  }
}

.graph-area {
  height: 400px;
  background: #f5f7fa;
  border-radius: 8px;
}
</style>
