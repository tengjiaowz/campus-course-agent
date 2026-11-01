<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">文档管理</h2>
        <p class="page-sub">上传课程资料并入库，课程助手回答时会引用这些内容。</p>
      </div>
    </div>
    <el-card class="page-card" shadow="never">
      <div v-if="isAdmin" style="margin-bottom: 12px">
        <el-upload
          ref="uploadRef"
          v-model:file-list="fileList"
          :auto-upload="false"
          :disabled="uploadLoading"
          multiple
        >
          <el-button type="primary" :disabled="uploadLoading">选择文件</el-button>
        </el-upload>
        <div style="margin-top: 10px">
          <el-button type="success" :loading="uploadLoading" @click="handleUpload">
            上传并入库
          </el-button>
        </div>
        <div style="margin-top: 6px; color: #7a8479; font-size: 12px">
          支持 .txt / .md / .pdf / .docx，单个文件不超过 100 MiB。同名不可重复；扫描版 PDF 可能抽不出文字。
          同一批中任一文件上传或入库失败，整批撤销。
        </div>
      </div>
      <el-alert v-else type="warning" :closable="false" title="仅管理员可管理文档" />

      <el-table
        :data="pagedData"
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f7f2e6', color: '#23302b' }"
        style="margin-top: 12px"
      >
        <el-table-column prop="original_name" label="名称" min-width="220" />
        <el-table-column prop="size" label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="ext" label="类型" width="90" />
        <el-table-column prop="ingested" label="已入库" width="90">
          <template #default="{ row }">
            <el-tag :type="row.ingested ? 'success' : 'info'" size="small">
              {{ row.ingested ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text bg size="small" @click="handlePreview(row)">
              预览
            </el-button>
            <el-button
              type="primary"
              text
              bg
              size="small"
              :loading="reingestLoadingId === row.id"
              @click="handleReingest(row)"
            >
              重新入库
            </el-button>
            <el-button type="danger" text bg size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="params.page"
          :page-size="params.pageSize"
          :total="tableData.length"
          background
          layout="total, prev, pager, next"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="60%"
      destroy-on-close
      append-to-body
    >
      <div v-loading="previewLoading" style="max-height: 60vh; overflow-y: auto">
        <pre class="preview-text">{{ previewText }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'Documents' })
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUser } from '@/utils/user'
import {
  deleteDocumentApi,
  listDocumentsApi,
  previewDocumentApi,
  reingestDocumentApi,
  uploadDocumentsApi
} from '@/api/document'

const { userInfo } = useUser()
const isAdmin = computed(() => userInfo.value?.role === 'admin')

const uploadRef = ref()
const fileList = ref([])
const uploadLoading = ref(false)
const loading = ref(false)
const params = reactive({ page: 1, pageSize: 10 })
const tableData = ref([])
const reingestLoadingId = ref(null) // 正在重新入库的文档 ID，控制对应按钮的加载状态

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewText = ref('')
const previewRequestId = ref(0)

const pagedData = computed(() => {
  const start = (params.page - 1) * params.pageSize
  return tableData.value.slice(start, start + params.pageSize)
})

const formatSize = (size) => {
  if (!size && size !== 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`
  return `${(size / 1024 / 1024).toFixed(1)} MiB`
}

const formatTime = (value) => {
  if (!value) return '-'
  const text = String(value).replace('T', ' ')
  return text.length >= 19 ? text.slice(0, 19) : text
}

const load = async () => {
  loading.value = true
  try {
    const res = await listDocumentsApi()
    if (res.code === 200) {
      tableData.value = res.data || []
      // 删除最后一页的记录后，把页码限制在有效范围内。
      const maxPage = Math.max(1, Math.ceil(tableData.value.length / params.pageSize))
      if (params.page > maxPage) params.page = maxPage
    }
  } finally {
    loading.value = false
  }
}

const handleUpload = async () => {
  const files = fileList.value.map((item) => item.raw).filter(Boolean)
  if (!files.length) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  uploadLoading.value = true
  try {
    const res = await uploadDocumentsApi(files)
    if (res.code === 200) {
      ElMessage.success(`已上传并入库 ${res.data.length} 份资料`)
      fileList.value = []
      params.page = 1
      await load()
    }
  } finally {
    uploadLoading.value = false
  }
}

const handlePreview = async (row) => {
  // 每次预览递增编号，先打开 A 再打开 B 时以 B 的请求为准。
  const requestId = ++previewRequestId.value
  previewVisible.value = true
  previewTitle.value = row.original_name
  previewText.value = ''
  previewLoading.value = true
  try {
    const res = await previewDocumentApi(row.id)
    if (requestId !== previewRequestId.value) return
    if (res.code === 200) {
      previewText.value = res.data.text
    }
  } catch {
    // 请求拦截器已提示网络或 HTTP 错误。
  } finally {
    if (requestId === previewRequestId.value) {
      previewLoading.value = false
    }
  }
}

const handleReingest = async (row) => {
  // 已有一份资料在入库时，不重复发起新的入库请求。
  if (reingestLoadingId.value !== null) return
  reingestLoadingId.value = row.id
  try {
    const res = await reingestDocumentApi(row.id)
    if (res.code === 200) {
      ElMessage.success(`「${row.original_name}」已重新入库`)
    }
  } catch {
    // 请求拦截器已提示网络或 HTTP 错误。
  } finally {
    reingestLoadingId.value = null
    // 失败时原文件仍在，但状态可能由“是”变成“否”，因此也刷新列表。
    await load()
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认删除文档「${row.original_name}」及其原文件和向量片段？`,
      '确认删除',
      { type: 'warning' }
    )
  } catch {
    // 取消或关闭确认框时，不调用删除接口。
    return
  }
  try {
    const res = await deleteDocumentApi(row.id)
    if (res.code === 200) ElMessage.success('已删除')
  } catch {
    // 错误已由请求拦截器提示。
  } finally {
    await load() // 删除失败也可能已清理向量，需要同步最新入库状态。
  }
}

onMounted(() => {
  if (isAdmin.value) load()
})
</script>

<style scoped>
.preview-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.6;
  color: #23302b;
}
</style>
