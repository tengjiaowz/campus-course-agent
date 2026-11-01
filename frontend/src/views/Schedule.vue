<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">我的课表</h2>
        <p class="page-sub">按日期查看你的上课安排，清空日期则显示全部。</p>
      </div>
    </div>
    <el-card class="page-card" shadow="never">
      <div class="toolbar">
        <el-date-picker
          v-model="params.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="按日期筛选，清空则显示全部"
          clearable
          @change="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" @click="handleSearch">查询</el-button>
      </div>
      <el-table
        :data="tableData"
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f7f2e6', color: '#23302b' }"
      >
        <el-table-column prop="class_date" label="日期" width="140" />
        <el-table-column prop="period" label="节次" width="120" />
        <el-table-column prop="course_name" label="课程" min-width="140" />
        <el-table-column prop="location" label="地点" />
      </el-table>
      <div class="pager-row">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>
<script setup>
defineOptions({ name: 'Schedule' })
import { onMounted, reactive, ref } from 'vue'
import { listSchedulesApi } from '@/api/schedule'

const params = reactive({
  page: 1,
  pageSize: 10,
  date: null
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const load = async () => {
  loading.value = true
  try {
    const res = await listSchedulesApi({
      page: params.page,
      page_size: params.pageSize,
      date: params.date || undefined
    })
    if (res.code === 200) {
      tableData.value = res.data?.list || []
      total.value = res.data?.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  params.page = 1
  load()
}

onMounted(() => {
  load()
})
</script>
