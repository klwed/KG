<template>
  <div class="page-card">
    <h3 class="page-title">文档管理</h3>
    
    <el-upload
      class="upload-area"
      drag
      :action="uploadUrl"
      :on-success="handleUploadSuccess"
      :on-error="handleUploadError"
      :show-file-list="false"
      accept=".pdf,.docx,.doc,.txt"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽文件到此处 或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 PDF、Word、TXT 格式</div>
      </template>
    </el-upload>

    <el-divider />

    <div class="document-list">
      <h4>已上传文档</h4>
      <el-table :data="documents" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="文件名" />
        <el-table-column prop="size" label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="extractTriples(row.name)" :loading="extracting === row.name">
              抽取三元组
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-divider />

    <div class="batch-actions">
      <el-button type="success" @click="extractAll" :loading="extracting === 'all'">
        批量抽取所有文档
      </el-button>
      <el-button type="danger" @click="clearGraph" :loading="clearing">
        清空知识图谱
      </el-button>
    </div>

    <el-dialog v-model="showResult" title="抽取结果" width="600px">
      <el-descriptions :column="1" border v-if="result">
        <el-descriptions-item label="文件名">{{ result.filename || '批量处理' }}</el-descriptions-item>
        <el-descriptions-item label="处理块数">{{ result.chunks || result.total_chunks }}</el-descriptions-item>
        <el-descriptions-item label="抽取三元组数">{{ result.triples || result.total_triples }}</el-descriptions-item>
      </el-descriptions>
      <el-alert v-if="resultError" :title="resultError" type="error" show-icon />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { documentApi, graphApi } from '@/api'

const uploadUrl = '/api/upload'
const documents = ref([])
const loading = ref(false)
const extracting = ref(false)
const clearing = ref(false)
const showResult = ref(false)
const result = ref(null)
const resultError = ref('')

const loadDocuments = async () => {
  loading.value = true
  try {
    const res = await documentApi.list()
    documents.value = res.documents || []
  } catch (e) {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  loadDocuments()
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const extractTriples = async (filename) => {
  extracting.value = filename
  try {
    const res = await documentApi.extract(filename)
    result.value = res
    resultError.value = ''
    showResult.value = true
    ElMessage.success('抽取完成')
  } catch (e) {
    resultError.value = e.message || '抽取失败'
    result.value = null
    showResult.value = true
    ElMessage.error('抽取失败')
  } finally {
    extracting.value = false
  }
}

const extractAll = async () => {
  extracting.value = 'all'
  try {
    const res = await documentApi.extractAll()
    result.value = { filename: '批量处理', ...res }
    resultError.value = ''
    showResult.value = true
    ElMessage.success('批量抽取完成')
    loadDocuments()
  } catch (e) {
    resultError.value = e.message || '批量抽取失败'
    result.value = null
    showResult.value = true
    ElMessage.error('批量抽取失败')
  } finally {
    extracting.value = false
  }
}

const clearGraph = async () => {
  clearing.value = true
  try {
    await graphApi.clear()
    ElMessage.success('知识图谱已清空')
  } catch (e) {
    ElMessage.error('清空失败')
  } finally {
    clearing.value = false
  }
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(() => {
  loadDocuments()
})
</script>

<style lang="scss" scoped>
.upload-area {
  margin-bottom: 20px;
}

.document-list {
  margin: 20px 0;
}

.batch-actions {
  display: flex;
  gap: 10px;
}
</style>
