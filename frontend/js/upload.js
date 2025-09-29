// 上传页面逻辑
document.addEventListener('DOMContentLoaded', function() {
    console.log('📤 上传页面初始化...');
    initializeFileUpload();
    initializeForm();
});

// 初始化文件上传区域
function initializeFileUpload() {
    // 视频文件上传
    const videoUpload = document.getElementById('videoUploadArea');
    const videoInput = document.getElementById('videoFile');
    const videoName = document.getElementById('videoFileName');

    setupFileUpload(videoUpload, videoInput, videoName, 'video');

    // 教案文件上传
    const outlineUpload = document.getElementById('outlineUploadArea');
    const outlineInput = document.getElementById('outlineFile');
    const outlineName = document.getElementById('outlineFileName');

    setupFileUpload(outlineUpload, outlineInput, outlineName, 'outline');
}

// 设置文件上传区域
function setupFileUpload(uploadArea, fileInput, fileNameDisplay, type) {
    // 点击选择文件
    uploadArea.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // 显示选择的文件名
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileNameDisplay.textContent = file.name;
            
            // 显示文件大小
            const sizeInfo = formatFileSize(file.size);
            let sizeHtml = `<div class="file-size">大小: ${sizeInfo}</div>`;
            
            // 检查文件大小限制
            if (type === 'video' && file.size > 500 * 1024 * 1024) {
                sizeHtml += `<div class="file-size" style="color: #dc3545;">文件过大，最大支持500MB</div>`;
            }
            
            fileNameDisplay.innerHTML = file.name + sizeHtml;
        } else {
            fileNameDisplay.textContent = '未选择文件';
            fileNameDisplay.innerHTML = '未选择文件';
        }
    });

    // 拖拽功能
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            const file = fileInput.files[0];
            fileNameDisplay.textContent = file.name;
            
            const sizeInfo = formatFileSize(file.size);
            fileNameDisplay.innerHTML = file.name + `<div class="file-size">大小: ${sizeInfo}</div>`;
        }
    });
}

// 初始化表单
function initializeForm() {
    const form = document.getElementById('uploadForm');
    form.addEventListener('submit', handleFormSubmit);
    
    // 实时验证
    form.addEventListener('input', debounce(validateForm, 300));
}

// 处理表单提交
async function handleFormSubmit(e) {
    e.preventDefault();
    console.log('📝 开始处理表单提交...');
    
    if (!validateForm()) {
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    const progress = document.getElementById('uploadProgress');
    const progressFill = progress.querySelector('.progress-fill');
    
    // 禁用提交按钮，显示进度条
    submitBtn.disabled = true;
    progress.style.display = 'block';
    progressFill.style.width = '10%';

    try {
        const formData = new FormData(e.target);
        
        // 模拟进度更新
        progressFill.style.width = '30%';
        
        const response = await fetch('http://localhost:5000/api/upload', {
            method: 'POST',
            body: formData
        });

        progressFill.style.width = '70%';

        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }

        const result = await response.json();
        progressFill.style.width = '100%';

        if (result.success) {
            showSuccess(`上传成功！任务编号: ${result.data.task_id}`);
            console.log('✅ 上传成功，任务编号:', result.data.task_id);
            
            // 2秒后关闭窗口
            setTimeout(() => {
                if (window.opener) {
                    window.opener.refreshTasks();
                }
                window.close();
            }, 2000);
        } else {
            throw new Error(result.message || '上传失败');
        }
    } catch (error) {
        console.error('❌ 上传失败:', error);
        showError('上传失败: ' + error.message);
        progressFill.style.width = '0%';
    } finally {
        submitBtn.disabled = false;
        setTimeout(() => {
            progress.style.display = 'none';
        }, 1000);
    }
}

// 表单验证
function validateForm() {
    let isValid = true;
    
    // 清除之前的错误信息
    clearErrors();

    // 验证课程名称
    const courseName = document.getElementById('courseName').value.trim();
    if (!courseName) {
        showError('courseNameError', '请输入课程名称');
        isValid = false;
    } else if (courseName.length > 100) {
        showError('courseNameError', '课程名称不能超过100个字符');
        isValid = false;
    }

    // 验证授课教师
    const teacher = document.getElementById('teacher').value.trim();
    if (!teacher) {
        showError('teacherError', '请输入授课教师');
        isValid = false;
    } else if (teacher.length > 50) {
        showError('teacherError', '教师姓名不能超过50个字符');
        isValid = false;
    }

    // 验证授课对象
    const studentType = document.getElementById('studentType').value.trim();
    if (!studentType) {
        showError('studentTypeError', '请输入授课对象');
        isValid = false;
    } else if (studentType.length > 100) {
        showError('studentTypeError', '授课对象描述不能超过100个字符');
        isValid = false;
    }

    // 验证视频文件
    const videoFile = document.getElementById('videoFile').files[0];
    if (!videoFile) {
        showError('videoFileError', '请选择视频文件');
        isValid = false;
    } else {
        // 验证文件类型
        const allowedTypes = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'];
        const fileExt = '.' + videoFile.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExt)) {
            showError('videoFileError', `不支持的文件格式。支持格式: ${allowedTypes.join(', ')}`);
            isValid = false;
        }

        // 验证文件大小（最大500MB）
        const maxSize = 500 * 1024 * 1024;
        if (videoFile.size > maxSize) {
            showError('videoFileError', '文件大小不能超过500MB');
            isValid = false;
        }
    }

    return isValid;
}

// 显示错误信息
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.style.display = 'block';
}

// 显示成功信息
function showSuccess(message) {
    const successEl = document.getElementById('successMessage');
    successEl.textContent = message;
    successEl.style.display = 'block';
}

// 清除错误信息
function clearErrors() {
    const errorElements = document.querySelectorAll('.error-message');
    errorElements.forEach(element => {
        element.style.display = 'none';
        element.textContent = '';
    });
    
    document.getElementById('successMessage').style.display = 'none';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 页面关闭前提示
window.addEventListener('beforeunload', function (e) {
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn.disabled) {
        e.preventDefault();
        e.returnValue = '文件正在上传中，确定要离开吗？';
        return '文件正在上传中，确定要离开吗？';
    }
});