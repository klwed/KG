<template>
  <div class="page-card kg-qa-container">
    <h3 class="page-title">知识图谱 + 智能问答</h3>
    
    <div class="main-content">
      <!-- 左侧：知识图谱 -->
      <div class="graph-panel">
        <div class="panel-header">
          <span>{{ showFullGraph ? '全局知识图谱' : '相关子图谱' }}</span>
          <div class="header-actions">
            <el-switch
              v-model="showFullGraph"
              active-text="全图"
              inactive-text="子图"
              @change="onGraphModeChange"
              size="small"
            />
            <el-button size="small" @click="loadGraph" :loading="loading">
              刷新
            </el-button>
          </div>
        </div>
        <div class="legend">
          <span class="legend-title">图例：</span>
          <span class="legend-item"><span class="dot course"></span>课程</span>
          <span class="legend-item"><span class="dot chapter"></span>章节</span>
          <span class="legend-item"><span class="dot knowledge"></span>知识点</span>
          <span class="legend-item"><span class="dot ct"></span>计算思维</span>
          <span class="legend-item"><span class="dot tag"></span>知识标签</span>
        </div>
        <div ref="chartRef" class="chart"></div>
        <div class="stats">
          节点: {{ nodeCount }} | 关系: {{ linkCount }}
          <span v-if="currentSubgraph" class="subgraph-hint">
            | 展示与"{{ currentSubgraph }}"相关的知识
          </span>
        </div>
      </div>

      <!-- 右侧：问答 -->
      <div class="qa-panel">
        <div class="panel-header">
          <span>智能问答</span>
          <el-button size="small" @click="clearChat">清空</el-button>
        </div>
        
        <div class="chat-container" ref="chatContainer">
          <div v-for="(msg, idx) in messages" :key="idx" 
               :class="['message', msg.role === 'user' ? 'user' : 'assistant']">
            <div class="avatar">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else><Robot /></el-icon>
            </div>
            <div class="content">
              <div class="text" v-html="formatMarkdown(msg.content)"></div>
              <div class="source" v-if="msg.source">
                <el-tag size="small" :type="msg.source === 'knowledge_graph' ? 'success' : 'info'">
                  {{ msg.source === 'knowledge_graph' ? '知识图谱' : msg.source === 'LLM' ? '大模型' : '混合' }}
                </el-tag>
              </div>
            </div>
          </div>
          
          <div v-if="loading" class="message assistant">
            <div class="avatar"><el-icon><Robot /></el-icon></div>
            <div class="content">
              <div class="text loading">
                <span class="el-icon-loading"></span>
                AI正在思考中...
              </div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="question"
            placeholder="输入问题，如：离散数学和信息安全有什么联系？"
            @keyup.enter="sendQuestion"
          >
            <template #append>
              <el-button @click="sendQuestion" :disabled="!question.trim() || loading">
                发送
              </el-button>
            </template>
          </el-input>
          <div class="history-hint" v-if="conversationHistory.length > 0">
            <el-tag size="small" type="info">
              对话历史: {{ conversationHistory.length }} 条
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 节点详情弹窗 -->
    <el-dialog v-model="showNodeDetail" title="节点详情" width="500px">
      <div v-if="nodeDetail" class="node-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="名称">
            <strong>{{ nodeDetail.name }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag>{{ nodeDetail.type }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">出边（该节点指向）</el-divider>
        <div v-if="nodeDetail.outgoing && nodeDetail.outgoing.length" class="relation-list">
          <div v-for="(rel, idx) in nodeDetail.outgoing" :key="idx" class="relation-item">
            <span class="rel-type">[{{ rel.relation }}]</span>
            <span class="rel-target">{{ rel.target }}</span>
            <span class="rel-type-tag">({{ rel.target_type }})</span>
          </div>
        </div>
        <el-empty v-else description="暂无出边" :image-size="50" />

        <el-divider content-position="left">入边（指向该节点）</el-divider>
        <div v-if="nodeDetail.incoming && nodeDetail.incoming.length" class="relation-list">
          <div v-for="(rel, idx) in nodeDetail.incoming" :key="idx" class="relation-item">
            <span class="rel-source">{{ rel.source }}</span>
            <span class="rel-type">[{{ rel.relation }}]</span>
          </div>
        </div>
        <el-empty v-else description="暂无入边" :image-size="50" />

        <el-divider content-position="left">相关节点</el-divider>
        <div v-if="nodeDetail.related && nodeDetail.related.length" class="related-list">
          <el-tag 
            v-for="(node, idx) in nodeDetail.related.slice(0, 10)" 
            :key="idx" 
            size="small" 
            class="mr-5 mb-5"
            @click="onNodeClick({ data: { id: node.node, type: node.type } })"
            style="cursor: pointer;"
          >
            {{ node.node }}
          </el-tag>
        </div>
        <el-empty v-else description="暂无相关节点" :image-size="50" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { qaApi, graphApi } from '@/api'

const chartRef = ref(null)
const chatContainer = ref(null)
let chart = null

const fullGraphData = ref({ nodes: [], links: [] })
const currentSubgraph = ref(null)
const subgraphData = ref({ nodes: [], links: [] })
const messages = ref([])
const question = ref('')
const loading = ref(false)
const highlightedNodes = ref(new Set())
const showFullGraph = ref(true)

const showNodeDetail = ref(false)
const nodeDetail = ref(null)

const conversationHistory = ref([])
const sessionId = ref(Date.now().toString())

const graphData = computed(() => {
  return showFullGraph.value ? fullGraphData.value : subgraphData.value
})

const nodeCount = computed(() => graphData.value.nodes?.length || 0)
const linkCount = computed(() => graphData.value.links?.length || 0)

const loadGraph = async () => {
  loading.value = true
  try {
    const res = await graphApi.getData()
    fullGraphData.value = res
    if (showFullGraph.value) {
      renderChart()
    }
  } catch (e) {
    console.error('加载图谱失败:', e)
  } finally {
    loading.value = false
  }
}

const loadSubgraph = async (keyword) => {
  loading.value = true
  try {
    const res = await graphApi.getSubgraph(keyword)
    subgraphData.value = res
    if (!showFullGraph.value) {
      renderChart()
    }
  } catch (e) {
    console.error('加载子图谱失败:', e)
  } finally {
    loading.value = false
  }
}

const onGraphModeChange = () => {
  if (showFullGraph.value) {
    currentSubgraph.value = null
    highlightedNodes.value.clear()
  }
  renderChart()
}

const getNodeColor = (node) => {
  if (highlightedNodes.value.has(node.id)) {
    return '#ff6b6b'
  }
  const colors = {
    '课程': '#67c23a',
    '章节': '#409EFF',
    '知识点': '#5470c6',
    '计算思维': '#f39c12',
    '知识标签': '#909399',
    '分解': '#e74c3c',
    '模式识别': '#3498db',
    '抽象': '#9b59b6',
    '算法思维': '#f39c12',
    '评估': '#1abc9c',
    '概念': '#5470c6',
    '定义': '#91cc75',
    '定理': '#fac858',
    '算法': '#ee6666',
    '协议': '#73c0de',
    '应用': '#3ba272',
    'Entity': '#5470c6'
  }
  return colors[node.type] || '#5470c6'
}

const getNodeSize = (node) => {
  if (node.type === '课程') return 65
  if (node.type === '章节') return 55
  if (node.type === '知识点') return 50
  if (node.type === '计算思维') return 60
  return 45
}

const onNodeClick = async (params) => {
  if (!params.data || !params.data.id) return
  
  const nodeName = params.data.id
  const nodeType = params.data.type || 'Entity'
  
  try {
    const res = await kgApi.getEntityDetails(nodeName)
    nodeDetail.value = res
    showNodeDetail.value = true
  } catch (e) {
    nodeDetail.value = {
      name: nodeName,
      type: nodeType,
      outgoing: [],
      incoming: [],
      related: []
    }
    showNodeDetail.value = true
  }
}

const renderChart = () => {
  if (!chart) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => chart.resize())
    
    chart.on('click', onNodeClick)
  }

  const categories = [...new Set(graphData.value.nodes.map(n => n.type || 'Entity'))]

  const option = {
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          const ct = ['分解', '模式识别', '抽象', '算法思维', '评估', '计算思维']
          if (ct.includes(params.data.type)) {
            return `<strong>${params.data.name}</strong><br/><span style="color:#e74c3c">💡 计算思维维度</span>`
          }
          return `${params.data.name}<br/>类型: ${params.data.type}`
        }
        return `${params.data.source} → ${params.data.target}<br/>关系: ${params.data.relation}`
      }
    },
    legend: {
      data: categories,
      top: 5
    },
    series: [{
      type: 'graph',
      layout: 'force',
      symbolSize: (val, params) => getNodeSize(params.data),
      roam: true,
      draggable: true,
      label: {
        show: true,
        position: 'bottom',
        fontSize: 11
      },
      edgeSymbol: ['circle', 'arrow'],
      edgeSymbolSize: [4, 10],
      data: graphData.value.nodes.map(n => ({
        id: n.id,
        name: n.id,
        type: n.type || 'Entity',
        itemStyle: { color: getNodeColor(n) }
      })),
      lineStyle: {
        width: 2,
        curveness: 0.3
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 4 }
      },
      categories: categories.map(c => ({ name: c })),
      force: {
        repulsion: 100,
        edgeLength: 120,
        layoutAnimation: true
      }
    }]
  }

  chart.setOption(option)
}

const isHighlightedLink = (link) => {
  const src = typeof link.source === 'object' ? link.source.id : link.source
  const tgt = typeof link.target === 'object' ? link.target.id : link.target
  return highlightedNodes.value.has(src) && highlightedNodes.value.has(tgt)
}

const highlightRelatedNodes = (triples) => {
  highlightedNodes.value.clear()
  if (triples && triples.length) {
    triples.forEach(t => {
      highlightedNodes.value.add(t.head)
      highlightedNodes.value.add(t.tail)
    })
  }
  renderChart()
}

const getCurrentUser = () => {
  const user = localStorage.getItem('user')
  if (user) {
    return JSON.parse(user)
  }
  return null
}

const sendQuestion = async () => {
  if (!question.value.trim() || loading.value) return

  const q = question.value.trim()
  question.value = ''

  messages.value.push({ role: 'user', content: q })
  loading.value = true
  scrollToBottom()

  const currentUser = getCurrentUser()
  const username = currentUser?.username || null

  try {
    const res = await qaApi.ask(q, false, sessionId.value, conversationHistory.value, username)
    
    messages.value.push({
      role: 'assistant',
      content: res.answer,
      source: res.source,
      triples: res.related_triples,
      personalScores: res.personal_scores
    })

    conversationHistory.value.push({
      question: q,
      answer: res.answer,
      related_triples: res.related_triples
    })
    
    if (res.subgraph && res.subgraph.nodes && res.subgraph.nodes.length > 0) {
      subgraphData.value = res.subgraph
      showFullGraph.value = false
      
      const keywords = res.related_triples?.map(t => t.head).filter(Boolean) || []
      currentSubgraph.value = keywords[0] || q
      
      highlightedNodes.value.clear()
      res.subgraph.nodes.forEach(n => highlightedNodes.value.add(n.id))
      
      renderChart()
    } else if (res.related_triples && res.related_triples.length) {
      highlightRelatedNodes(res.related_triples)
    }
  } catch (e) {
    ElMessage.error('问答失败: ' + (e.message || '未知错误'))
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误，请稍后重试。',
      source: 'error'
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const clearChat = () => {
  messages.value = []
  conversationHistory.value = []
  sessionId.value = Date.now().toString()
  highlightedNodes.value.clear()
  renderChart()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const formatMarkdown = (text) => {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>')
}

onMounted(() => {
 // loadGraph()
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    window.removeEventListener('resize', () => chart.resize())
  }
})
</script>

<style lang="scss" scoped>
.kg-qa-container {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
  min-height: 0;
}

.graph-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
}

.qa-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 600;
  color: #333;

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }
}

.chart {
  flex: 1;
  min-height: 400px;
  background: #fafafa;
  border-radius: 8px;
}

.stats {
  text-align: center;
  color: #666;
  font-size: 13px;
  margin-top: 8px;

  .subgraph-hint {
    color: #409EFF;
    margin-left: 10px;
  }
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
}

.message {
  display: flex;
  margin-bottom: 15px;

  &.user {
    flex-direction: row-reverse;

    .content {
      align-items: flex-end;
    }

    .text {
      background: #409EFF;
      color: #fff;
    }
  }

  &.assistant {
    .text {
      background: #fff;
      color: #333;
    }
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #ddd;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 8px;
    font-size: 16px;
  }

  .content {
    max-width: 80%;
    display: flex;
    flex-direction: column;
    gap: 5px;

    .text {
      padding: 10px 14px;
      border-radius: 12px;
      line-height: 1.5;
      font-size: 14px;

      &.loading {
        background: #fff;
        color: #999;
      }
    }
  }
}

.legend {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 10px;
  font-size: 12px;
  flex-wrap: wrap;

  .legend-title {
    font-weight: 600;
    color: #333;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #666;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    
    &.course { background: #67c23a; }
    &.chapter { background: #409EFF; }
    &.knowledge { background: #5470c6; }
    &.ct { background: #f39c12; }
    &.tag { background: #909399; }
  }

  .line {
    width: 20px;
    height: 2px;
    
    &.solid { background: #f39c12; }
    &.dashed { 
      background: repeating-linear-gradient(
        90deg,
        #999 0, #999 4px, transparent 4px, transparent 8px
      );
    }
  }
}

.input-area {
  :deep(.el-input__wrapper) {
    border-radius: 20px;
  }

  .history-hint {
    margin-top: 8px;
  }
}

.mr-5 {
  margin-right: 5px;
}

.mb-5 {
  margin-bottom: 5px;
}

.node-detail {
  .relation-list {
    padding: 0 10px;
  }

  .relation-item {
    padding: 6px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 13px;

    .rel-type {
      color: #f39c12;
      margin: 0 5px;
    }

    .rel-target, .rel-source {
      color: #333;
      font-weight: 500;
    }

    .rel-type-tag {
      color: #999;
      font-size: 12px;
      margin-left: 5px;
    }
  }

  .related-list {
    padding: 0 10px;
  }
}
</style>
