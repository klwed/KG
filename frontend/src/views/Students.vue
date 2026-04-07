<template>
  <div class="page-card student-container">
    <h3 class="page-title">学生掌握情况管理</h3>
    
    <div class="main-content">
      <!-- 左侧：操作区 -->
      <div class="control-panel">
        <el-card shadow="hover">
          <template #header>
            <span>数据管理</span>
          </template>
          
          <div class="action-item">
            <h4>导入学生数据</h4>
            <el-upload
              class="upload"
              drag
              :action="uploadUrl"
              :on-success="handleUpload"
              :show-file-list="false"
              accept=".csv,.xlsx"
            >
              <el-icon><UploadFilled /></el-icon>
              <div>上传 CSV 或 Excel 文件</div>
            </el-upload>
          </div>

          <el-divider />

          <div class="action-item">
            <h4>导入到图谱</h4>
            <p class="hint">将学生数据转换为三元组并导入Neo4j</p>
            <el-button type="primary" @click="importToKG" :loading="importing">
              开始导入
            </el-button>
          </div>

          <el-divider />

          <div class="action-item">
            <h4>查看报告</h4>
            <el-button @click="loadReport">生成报告</el-button>
          </div>
        </el-card>

        <el-card shadow="hover" class="stats-card">
          <template #header>
            <span>图谱结构说明</span>
          </template>
          <div class="structure-hint">
            <pre class="graph-structure">
学生 --[掌握]--> 知识点
学生 --[学习]--> 离散数学
知识点 --[属于]--> 离散数学
知识点 --[体现]--> 计算思维
            </pre>
          </div>
        </el-card>
      </div>

      <!-- 右侧：数据展示 -->
      <div class="display-panel">
        <el-card shadow="hover">
          <template #header>
            <span>学生掌握情况汇总</span>
          </template>
          
          <el-table :data="studentSummary" stripe>
            <el-table-column prop="姓名" label="姓名" width="100" />
            <el-table-column prop="平均分" label="平均分" width="80">
              <template #default="{ row }">
                <el-tag :type="getScoreType(row.平均分)">
                  {{ row.平均分 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="总评" label="总评" width="80">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.总评)">
                  {{ row.总评 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="薄弱点" label="薄弱点">
              <template #default="{ row }">
                <el-tag v-for="t in row.薄弱点" :key="t" size="small" type="danger" class="mr-5">
                  {{ t }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="强项" label="强项">
              <template #default="{ row }">
                <el-tag v-for="t in row.强项" :key="t" size="small" type="success" class="mr-5">
                  {{ t }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="hover" class="topic-card">
          <template #header>
            <span>各知识点统计</span>
          </template>
          
          <el-table :data="topicStats" stripe>
            <el-table-column prop="知识点" label="知识点" width="120" />
            <el-table-column prop="平均分" label="平均分" width="100">
              <template #default="{ row }">
                <el-progress 
                  :percentage="row.平均分 * 100" 
                  :color="getProgressColor(row.平均分)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="最高分" label="最高分" width="80" />
            <el-table-column prop="最低分" label="最低分" width="80" />
            <el-table-column prop="计算思维" label="关联计算思维">
              <template #default="{ row }">
                <el-tag 
                  v-for="ct in row.计算思维" 
                  :key="ct" 
                  size="small" 
                  class="mr-5"
                  :type="getCTType(ct)"
                >
                  {{ ct }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>

    <!-- 报告弹窗 -->
    <el-dialog v-model="showReport" title="学生掌握情况报告" width="80%">
      <pre class="report-content">{{ report }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { studentApi } from '@/api'

const uploadUrl = 'http://localhost:8000/api/student/upload'
const studentSummary = ref([])
const topicStats = ref([])
const report = ref('')
const showReport = ref(false)
const importing = ref(false)

const handleUpload = () => {
  ElMessage.success('上传成功')
  loadData()
}

const loadData = async () => {
  try {
    const res = await studentApi.getSummary()
    studentSummary.value = res.students || []
    topicStats.value = Object.entries(res.topic_stats || {}).map(([topic, stats]) => ({
      知识点: topic,
      ...stats
    }))
  } catch (e) {
    console.error(e)
  }
}

const importToKG = async () => {
  importing.value = true
  try {
    await studentApi.importToKG()
    ElMessage.success('导入成功')
  } catch (e) {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

const loadReport = async () => {
  try {
    const res = await studentApi.getReport()
    report.value = res.report
    showReport.value = true
  } catch (e) {
    ElMessage.error('生成报告失败')
  }
}

const getScoreType = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
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

const getCTType = (ct) => {
  const types = { '分解': 'danger', '算法思维': 'warning', '抽象': 'success', '模式识别': 'primary' }
  return types[ct] || 'info'
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.student-container {
  min-height: calc(100vh - 140px);
}

.main-content {
  display: flex;
  gap: 20px;
}

.control-panel {
  width: 320px;
  flex-shrink: 0;

  .action-item {
    h4 {
      margin: 0 0 10px;
    }

    .hint {
      color: #999;
      font-size: 12px;
      margin: 5px 0 10px;
    }

    .upload {
      :deep(.el-upload-dragger) {
        padding: 20px;
      }
    }

    .el-button {
      width: 100%;
    }
  }

  .stats-card {
    margin-top: 20px;
  }
}

.display-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;

  .topic-card {
    flex: 1;
  }
}

.structure-hint {
  .graph-structure {
    font-size: 12px;
    background: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    margin: 0;
    overflow-x: auto;
  }
}

.mr-5 {
  margin-right: 5px;
  margin-bottom: 2px;
}

.report-content {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 13px;
}
</style>
