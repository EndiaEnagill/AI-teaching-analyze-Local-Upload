// 配置
const CONFIG = {
    API_BASE_URL: 'http://localhost:5000/api',
    PAGE_SIZE: 10,
    REFRESH_INTERVAL: 3000, // 3秒刷新一次
    AUTO_REFRESH: true
};

// 全局变量
let currentPage = 1;
let totalPages = 1;
let allTasks = [];
let refreshInterval;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 视频分析平台前端初始化...');
    initializeApp();
});

// 初始化应用
function initializeApp() {
    loadTasks();
    setupAutoRefresh();
    setupEventListeners();
}

// 设置事件监听器
function setupEventListeners() {
    // 键盘快捷键
    document.addEventListener('keydown', function(e) {
        // F5 刷新
        if (e.key === 'F5') {
            e.preventDefault();
            refreshTasks();
        }
        // Ctrl + R 刷新
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            refreshTasks();
        }
    });

    // 页面可见性变化时刷新
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            refreshTasks();
        }
    });
}

// 设置自动刷新
function setupAutoRefresh() {
    if (CONFIG.AUTO_REFRESH) {
        refreshInterval = setInterval(() => {
            if (!document.hidden) { // 只在页面可见时刷新
                loadTasks(false);
            }
        }, CONFIG.REFRESH_INTERVAL);
    }
}

// 加载任务列表
async function loadTasks(showLoading = true) {
    if (showLoading) {
        showLoadingIndicator();
    }

    try {
        console.log('📡 获取任务列表...');
        const response = await fetch(`${CONFIG.API_BASE_URL}/tasks`);
        
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const result = await response.json();

        if (result.success) {
            console.log(`✅ 获取到 ${result.data.length} 个任务`);
            allTasks = result.data;
            updateLastUpdateTime();
            renderTable();
        } else {
            throw new Error(result.message || '未知错误');
        }
    } catch (error) {
        console.error('❌ 加载任务列表失败:', error);
        showError('加载任务列表失败: ' + error.message);
    } finally {
        if (showLoading) {
            hideLoadingIndicator();
        }
    }
}

// 渲染表格
function renderTable() {
    const tableBody = document.getElementById('taskTableBody');
    
    if (allTasks.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <div class="empty-content">
                        <h3>暂无分析任务</h3>
                        <p>点击右上角的"上传视频"按钮开始第一个分析任务</p>
                    </div>
                </td>
            </tr>
        `;
        updatePagination();
        return;
    }

    // 计算分页
    const startIndex = (currentPage - 1) * CONFIG.PAGE_SIZE;
    const endIndex = startIndex + CONFIG.PAGE_SIZE;
    const pageTasks = allTasks.slice(startIndex, endIndex);

    tableBody.innerHTML = pageTasks.map(task => `
        <tr>
            <td><strong>${escapeHtml(task.course_name)}</strong></td>
            <td><code class="task-id">${task.task_id}</code></td>
            <td>${escapeHtml(task.teacher)}</td>
            <td>${escapeHtml(task.student_type)}</td>
            <td>${formatDateTime(task.upload_time)}</td>
            <td>
                <div class="step-info">
                    <div class="step-name">${task.progress.current_step_name || '--'}</div>
                    <div class="step-progress">步骤 ${task.progress.current_step}/${task.progress.total_steps}</div>
                </div>
            </td>
            <td class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${Math.max(0, Math.min(100, task.progress.progress_percentage))}%"></div>
                </div>
                <div class="progress-text">${task.progress.progress_percentage}%</div>
            </td>
            <td>${task.progress.estimated_remaining || '--'}</td>
            <td>
                <span class="status status-${task.status}">${task.status}</span>
            </td>
            <td class="course-link">无</td>
        </tr>
    `).join('');

    updatePagination();
}

// 更新分页信息
function updatePagination() {
    totalPages = Math.max(1, Math.ceil(allTasks.length / CONFIG.PAGE_SIZE));
    
    document.getElementById('pageInfo').textContent = `第 ${currentPage} 页，共 ${totalPages} 页`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages || totalPages === 0;
}

// 切换页面
function changePage(direction) {
    const newPage = currentPage + direction;
    
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderTable();
        
        // 滚动到表格顶部
        document.querySelector('.table-container').scrollTop = 0;
    }
}

// 刷新任务列表
function refreshTasks() {
    console.log('🔄 手动刷新任务列表');
    currentPage = 1;
    loadTasks(true);
}

// 打开上传页面
function openUploadPage() {
    console.log('📤 打开上传页面');
    const uploadWindow = window.open('upload.html', '_blank', 'width=600,height=700,scrollbars=no,resizable=yes');
    
    if (uploadWindow) {
        // 监听上传窗口关闭事件
        const checkClose = setInterval(() => {
            if (uploadWindow.closed) {
                clearInterval(checkClose);
                refreshTasks(); // 上传窗口关闭后刷新列表
            }
        }, 500);
    }
}

// 更新最后更新时间
function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('lastUpdateTime').textContent = timeString;
}

// 显示加载指示器
function showLoadingIndicator() {
    document.getElementById('loading').classList.add('show');
}

// 隐藏加载指示器
function hideLoadingIndicator() {
    document.getElementById('loading').classList.remove('show');
}

// 显示错误信息
function showError(message) {
    const toast = document.getElementById('errorToast');
    const messageEl = document.getElementById('errorMessage');
    
    messageEl.textContent = message;
    toast.style.display = 'flex';
    
    // 5秒后自动隐藏
    setTimeout(hideError, 5000);
}

// 隐藏错误信息
function hideError() {
    document.getElementById('errorToast').style.display = 'none';
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '--';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).replace(/\//g, '-');
    } catch (error) {
        return dateString;
    }
}

// HTML转义函数
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 导出到全局作用域
window.refreshTasks = refreshTasks;
window.openUploadPage = openUploadPage;
window.changePage = changePage;
window.hideError = hideError;