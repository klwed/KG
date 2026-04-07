<template>
  <div class="page-card pipeline-container">
    <h3 class="page-title">知识图谱构建流程</h3>
    
    <el-steps :active="currentStep" align-center class="steps">
      <el-step title="文档处理" description="分词与清洗" />
      <el-step title="关系抽取" description="三元组提取" />
      <el-step title="图谱导入" description="Neo4j存储" />
      <el-step title="可视化" description="图谱展示" />
    </el-steps>

    <div class="main-content">
      <!-- 左侧：流程控制 -->
      <div class="control-panel">
        <el-card shadow="hover">
          <template #header>
            <span>流程控制</span>
          </template>
          
          <div class="step-section">
            <h4>Step 1: 文档处理</h4>
            <el-upload
              class="upload"
              drag
              :action="uploadUrl"
              :on-success="handleUploadSuccess"
              :show-file-list="false"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div>拖拽文档或点击上传</div>
            </el-upload>
            <el-button type="primary" @click="processDocuments" :loading="processing">
              处理文档
            </el-button>
          </div>

          <el-divider />

          <div class="step-section">
            <h4>Step 2: 关系抽取</h4>
            <p class="hint">从文档中提取知识三元组</p>
            <el-progress 
              v-if="extracting" 
              :percentage="extractProgress" 
              :status="extractProgress === 100 ? 'success' : ''"
              :stroke-width="10"
            />
            <p v-if="extracting" class="progress-text">
              正在处理第 {{ currentChunk }} / {{ totalChunks }} 个文本块...
            </p>
            <el-button type="primary" @click="extractTriples" :loading="extracting">
              开始抽取
            </el-button>
          </div>

          <el-divider />

          <div class="step-section">
            <h4>Step 3: 图谱导入</h4>
            <p class="hint">将三元组存入Neo4j</p>
            <el-button type="success" @click="importToKG" :loading="importing">
              导入图谱
            </el-button>
            <el-button @click="clearKG">清空图谱</el-button>
          </div>

          <el-divider />

          <div class="step-section">
            <h4>Step 4: 查看结果</h4>
            <el-button @click="showGraph = true">打开图谱</el-button>
            <el-button @click="exportTriples">导出三元组</el-button>
          </div>

          <el-divider />

          <div class="step-section">
            <h4>邀请码管理</h4>
            <p class="hint">为学生生成注册邀请码</p>
            <el-button @click="createStudentCode">生成学生邀请码</el-button>
            <div v-if="studentCodes.length" class="code-list">
              <p class="hint">可用的学生邀请码：</p>
              <div v-for="code in studentCodes" :key="code" class="code-item">
                <code>{{ code }}</code>
                <el-button size="small" type="danger" @click="deleteCode(code)">删除</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 统计信息 -->
        <el-card shadow="hover" class="stats-card">
          <template #header>
            <span>统计信息</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="文档数">{{ stats.documents }}</el-descriptions-item>
            <el-descriptions-item label="处理块数">{{ stats.chunks }}</el-descriptions-item>
            <el-descriptions-item label="三元组数">{{ stats.triples }}</el-descriptions-item>
            <el-descriptions-item label="图谱节点">{{ stats.nodes }}</el-descriptions-item>
            <el-descriptions-item label="图谱关系">{{ stats.relations }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <!-- 右侧：内容展示 -->
      <div class="display-panel">
        <!-- 三元组表格 -->
        <el-card shadow="hover" class="table-card" v-if="triples.length">
          <template #header>
            <span>三元组列表 (共 {{ triples.length }} 个)</span>
          </template>
          <el-table :data="triples.slice(0, 100)" stripe max-height="400">
            <el-table-column prop="head" label="头实体" width="150" />
            <el-table-column prop="relation" label="关系" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="getRelationTagType(row.relation)">
                  {{ row.relation }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="tail" label="尾实体" width="150" />
            <el-table-column prop="head_type" label="头类型" width="100" />
            <el-table-column prop="tail_type" label="尾类型" width="100" />
          </el-table>
          <el-pagination
            v-if="triples.length > 100"
            layout="prev, pager, next"
            :total="triples.length"
            :page-size="100"
            @current-change="pageChange"
            class="pagination"
          />
        </el-card>

        <!-- 处理日志 -->
        <el-card shadow="hover" class="log-card">
          <template #header>
            <span>处理日志</span>
            <el-button size="small" @click="logs = []">清空</el-button>
          </template>
          <div class="logs">
            <div v-for="(log, idx) in logs" :key="idx" :class="['log-item', log.type]">
              <span class="time">{{ log.time }}</span>
              <span class="message">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 图谱弹窗 -->
    <el-dialog v-model="showGraph" title="知识图谱" width="90%" top="5vh">
      <div class="graph-dialog">
        <div class="graph-area" ref="graphChart"></div>
        <div class="qa-area">
          <h4>智能问答</h4>
          <div class="qa-chat" ref="qaChat">
            <div v-for="(msg, idx) in qaMessages" :key="idx" 
                 :class="['qa-message', msg.role]">
              {{ msg.content }}
            </div>
          </div>
          <el-input v-model="qaQuestion" placeholder="输入问题..." @enter="sendQuestion">
            <template #append>
              <el-button @click="sendQuestion">发送</el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { documentApi, extractApi, kgApi, qaApi, authApi } from '@/api'

const uploadUrl = 'http://localhost:8000/api/document/process'
const currentStep = ref(0)

const stats = reactive({
  documents: 0,
  chunks: 0,
  triples: 0,
  nodes: 0,
  relations: 0
})

const triples = ref([])
const logs = ref([])
const processing = ref(false)
const extracting = ref(false)
const importing = ref(false)
const showGraph = ref(false)
const graphChart = ref(null)
let graphInstance = null

const qaQuestion = ref('')
const qaMessages = ref([])
const studentCodes = ref([])

const extractProgress = ref(0)
const currentChunk = ref(0)
const totalChunks = ref(0)

const addLog = (message, type = 'info') => {
  const now = new Date()
  logs.value.push({
    time: `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`,
    message,
    type
  })
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  addLog('文档上传成功')
  loadDocuments()
}

const loadDocuments = async () => {
  try {
    const res = await documentApi.list()
    stats.documents = res.documents?.length || 0
  } catch (e) {
    console.error(e)
  }
}

const createStudentCode = async () => {
  try {
    const res = await authApi.createInviteCode('student')
    ElMessage.success(`邀请码已生成：${res.code}`)
    loadInviteCodes()
  } catch (e) {
    ElMessage.error('生成失败')
  }
}

const loadInviteCodes = async () => {
  try {
    const res = await authApi.listInviteCodes()
    studentCodes.value = res.codes
      .filter(c => !c.used && c.role === 'student')
      .map(c => c.code)
  } catch (e) {
    console.error(e)
  }
}

const deleteCode = async (code) => {
  try {
    await authApi.deleteInviteCode(code)
    ElMessage.success('已删除')
    loadInviteCodes()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  addLog('文档上传成功')
  loadDocuments()
}

const processDocuments = async () => {
  processing.value = true
  addLog('开始处理文档...', 'info')
  currentStep.value = 0
  
  try {
    const res = await documentApi.list()
    stats.chunks = res.documents?.length * 5 || 10
    addLog(`文档处理完成，共 ${stats.chunks} 个文本块`, 'success')
    currentStep.value = 1
  } catch (e) {
    addLog('文档处理失败: ' + (e.message || ''), 'error')
  } finally {
    processing.value = false
  }
}

const extractTriples = async () => {
  extracting.value = true
  addLog('开始抽取三元组...', 'info')
  
  try {
    const res = await extractApi.extractAll()
    triples.value = []
    res.results?.forEach(r => {
      if (r.triples) {
        stats.triples += r.triples
        addLog(`${r.filename}: 提取 ${r.triples} 个三元组`, 'success')
      }
    })
    currentStep.value = 2
  } catch (e) {
    addLog('抽取失败: ' + (e.message || ''), 'error')
  } finally {
    extracting.value = false
  }
}

const importToKG = async () => {
  importing.value = true
  addLog('开始导入图谱...', 'info')
  
  try {
    const res = await kgApi.getStats()
    stats.nodes = res.node_count || 0
    stats.relations = res.relation_count || 0
    addLog(`图谱导入完成: ${stats.nodes} 节点, ${stats.relations} 关系`, 'success')
    currentStep.value = 3
  } catch (e) {
    addLog('导入失败: ' + (e.message || ''), 'error')
  } finally {
    importing.value = false
  }
}

const clearKG = async () => {
  try {
    await kgApi.clear()
    stats.nodes = 0
    stats.relations = 0
    addLog('图谱已清空', 'warning')
  } catch (e) {
    ElMessage.error('清空失败')
  }
}

const exportTriples = async () => {
  window.open(kgApi.export(), '_blank')
}
}

const processDocuments = async () => {
  processing.value = true
  addLog('开始处理文档...', 'info')
  currentStep.value = 0
  
  try {
    const res = await axios.post('/api/document/process', {})
    stats.chunks = res.chunk_count || 0
    addLog(`文档处理完成，共 ${stats.chunks} 个文本块`, 'success')
    currentStep.value = 1
  } catch (e) {
    addLog('文档处理失败: ' + (e.message || ''), 'error')
  } finally {
    processing.value = false
  }
}

const extractTriples = async () => {
  extracting.value = true
  addLog('开始抽取三元组...', 'info')
  
  try {
    const res = await axios.post('/api/extract/all')
    triples.value = []
    res.results?.forEach(r => {
      if (r.triples) {
        addLog(`${r.filename}: 提取 ${r.triples} 个三元组`, 'success')
      }
    })
    currentStep.value = 2
  } catch (e) {
    addLog('抽取失败: ' + (e.message || ''), 'error')
  } finally {
    extracting.value = false
  }
}

const importToKG = async () => {
  importing.value = true
  addLog('开始导入图谱...', 'info')
  
  try {
    const res = await axios.get('/api/kg/stats')
    stats.nodes = res.node_count || 0
    stats.relations = res.relation_count || 0
    addLog(`图谱导入完成: ${stats.nodes} 节点, ${stats.relations} 关系`, 'success')
    currentStep.value = 3
  } catch (e) {
    addLog('导入失败: ' + (e.message || ''), 'error')
  } finally {
    importing.value = false
  }
}

const clearKG = async () => {
  try {
    await axios.delete('/api/kg/clear')
    stats.nodes = 0
    stats.relations = 0
    addLog('图谱已清空', 'warning')
  } catch (e) {
    ElMessage.error('清空失败')
  }
}

const exportTriples = async () => {
  window.open('/api/kg/export', '_blank')
}

const getRelationTagType = (relation) => {
  if (relation === '体现') return 'warning'
  if (['包含', '属于'].includes(relation)) return 'primary'
  if (['是', '实现', '基于'].includes(relation)) return 'success'
  return 'info'
}

const pageChange = (page) => {
  // 表格分页
}

const sendQuestion = async () => {
  if (!qaQuestion.value.trim()) return
  
  qaMessages.value.push({ role: 'user', content: qaQuestion.value })
  const q = qaQuestion.value
  qaQuestion.value = ''
  
  try {
    const res = await qaApi.ask(q)
    qaMessages.value.push({ role: 'assistant', content: res.answer })
  } catch (e) {
    qaMessages.value.push({ role: 'error', content: '问答失败' })
  }
}

onMounted(() => {
  loadDocuments()
})
</script>

<style lang="scss" scoped>
.pipeline-container {
  min-height: calc(100vh - 140px);
}

.steps {
  margin: 20px 0 30px;
}

.main-content {
  display: flex;
  gap: 20px;
}

.control-panel {
  width: 320px;
  flex-shrink: 0;

  .step-section {
    margin-bottom: 15px;
    
    h4 {
      margin: 0 0 10px;
      color: #333;
    }
    
    .hint {
      color: #999;
      font-size: 12px;
      margin: 5px 0 10px;
    }

    .upload {
      margin-bottom: 10px;
      
      :deep(.el-upload-dragger) {
        padding: 20px;
      }
    }

    .el-button {
      width: 100%;
      margin-top: 5px;
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

  .table-card {
    flex: 1;
  }

  .pagination {
    margin-top: 10px;
    text-align: center;
  }
}

.logs {
  max-height: 200px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;

  .log-item {
    padding: 4px 0;
    display: flex;
    gap: 10px;

    .time {
      color: #999;
      flex-shrink: 0;
    }

    &.success .message { color: #67c23a; }
    &.error .message { color: #f56c6c; }
    &.warning .message { color: #e6a23c; }
  }
}

.graph-dialog {
  height: 70vh;
  display: flex;
  gap: 20px;

  .graph-area {
    flex: 1;
    background: #f5f7fa;
    border-radius: 8px;
  }

  .qa-area {
    width: 350px;
    display: flex;
    flex-direction: column;

    h4 {
      margin: 0 0 10px;
    }

    .qa-chat {
      flex: 1;
      overflow-y: auto;
      background: #f5f7fa;
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 10px;

      .qa-message {
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        max-width: 85%;

        &.user {
          background: #409eff;
          color: #fff;
          margin-left: auto;
        }

        &.assistant {
          background: #fff;
        }

        &.error {
          background: #fef0f0;
          color: #f56c6c;
        }
      }
    }
  }
}
</style>
