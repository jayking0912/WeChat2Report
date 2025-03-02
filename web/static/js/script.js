document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabLinks = document.querySelectorAll('nav a');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs
            tabLinks.forEach(l => l.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));
            
            // Add active class to current tab
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Toggle response content expansion
    document.querySelectorAll('.toggle-content').forEach(button => {
        button.addEventListener('click', function() {
            const contentDiv = this.previousElementSibling;
            contentDiv.classList.toggle('expanded');
            this.textContent = contentDiv.classList.contains('expanded') ? '收起' : '展开';
        });
    });
    
    // Refresh task history
    document.getElementById('refresh-tasks').addEventListener('click', function() {
        fetch('/api/task_history')
            .then(response => response.json())
            .then(data => {
                const tableBody = document.querySelector('#task-history-table tbody');
                tableBody.innerHTML = '';
                
                if (data.tasks && data.tasks.length > 0) {
                    // Sort tasks by time in descending order
                    const sortedTasks = [...data.tasks].reverse();
                    
                    sortedTasks.forEach(task => {
                        const tr = document.createElement('tr');
                        
                        // Time column
                        const tdTime = document.createElement('td');
                        tdTime.textContent = task.time;
                        tr.appendChild(tdTime);
                        
                        // Status column
                        const tdStatus = document.createElement('td');
                        tdStatus.textContent = task.status === 'success' ? '成功' : '失败';
                        tdStatus.className = task.status === 'success' ? 'success' : 'error';
                        tr.appendChild(tdStatus);
                        
                        // HTTP Status column
                        const tdHttpStatus = document.createElement('td');
                        tdHttpStatus.textContent = (task.response && task.response.status_code) 
                            ? task.response.status_code 
                            : 'N/A';
                        tr.appendChild(tdHttpStatus);
                        
                        // Response content column
                        const tdContent = document.createElement('td');
                        tdContent.className = 'response-content';
                        
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'truncate';
                        contentDiv.textContent = (task.response && task.response.content)
                            ? task.response.content
                            : 'N/A';
                        tdContent.appendChild(contentDiv);
                        
                        if (task.response && task.response.content) {
                            const toggleButton = document.createElement('button');
                            toggleButton.className = 'toggle-content';
                            toggleButton.textContent = '展开';
                            toggleButton.addEventListener('click', function() {
                                contentDiv.classList.toggle('expanded');
                                this.textContent = contentDiv.classList.contains('expanded') ? '收起' : '展开';
                            });
                            tdContent.appendChild(toggleButton);
                        }
                        
                        tr.appendChild(tdContent);
                        tableBody.appendChild(tr);
                    });
                } else {
                    const tr = document.createElement('tr');
                    const td = document.createElement('td');
                    td.colSpan = 4;
                    td.className = 'no-data';
                    td.textContent = '暂无任务执行记录';
                    tr.appendChild(td);
                    tableBody.appendChild(tr);
                }
            })
            .catch(error => {
                console.error('Error fetching task history:', error);
            });
    });
    
    // Group tags functionality
    const csvFilesList = document.getElementById('csv-files-list');
    const tagInput = document.getElementById('tag-input');
    const applyTagBtn = document.getElementById('apply-tag-btn');
    const selectedFileSpan = document.getElementById('selected-file');
    const tagsSummaryList = document.getElementById('tags-summary-list');
    
    let csvFiles = [];
    let groupTagsData = {}; // 新格式: { "标签": ["文件1.csv", "文件2.csv"] }
    let selectedFile = null;
    
    // 获取文件对应的标签
    function getTagForFile(file) {
        for (const [tag, files] of Object.entries(groupTagsData)) {
            if (files.includes(file)) {
                return tag;
            }
        }
        return null;
    }
    
    // 从文件中移除标签
    function removeFileFromTags(file) {
        for (const [tag, files] of Object.entries(groupTagsData)) {
            const index = files.indexOf(file);
            if (index !== -1) {
                files.splice(index, 1);
                // 如果标签下没有文件了，删除这个标签
                if (files.length === 0) {
                    delete groupTagsData[tag];
                }
                return;
            }
        }
    }
    
    // Function to render CSV files list
    function renderCsvFilesList() {
        csvFilesList.innerHTML = '';
        
        csvFiles.forEach(file => {
            const li = document.createElement('li');
            li.className = selectedFile === file ? 'selected' : '';
            
            const fileNameSpan = document.createElement('span');
            fileNameSpan.textContent = file;
            fileNameSpan.className = 'file-name';
            
            const tag = getTagForFile(file);
            if (tag) {
                fileNameSpan.innerHTML += ` <span class="tag-badge">${tag}</span>`;
            }
            
            li.appendChild(fileNameSpan);
            
            li.addEventListener('click', () => {
                selectedFile = file;
                selectedFileSpan.textContent = file;
                // Update selected state in UI
                document.querySelectorAll('#csv-files-list li').forEach(item => {
                    item.className = '';
                });
                li.className = 'selected';
                
                // Pre-fill tag input if file already has a tag
                tagInput.value = getTagForFile(file) || '';
            });
            
            csvFilesList.appendChild(li);
        });
    }
    
    // Function to render tags summary
    function renderTagsSummary() {
        tagsSummaryList.innerHTML = '';
        
        // 直接使用新格式的groupTagsData
        for (const [tag, files] of Object.entries(groupTagsData)) {
            const li = document.createElement('li');
            
            const tagName = document.createElement('div');
            tagName.className = 'tag-name';
            tagName.textContent = tag;
            li.appendChild(tagName);
            
            const filesList = document.createElement('div');
            filesList.className = 'tag-files';
            filesList.textContent = files.join(', ');
            li.appendChild(filesList);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = '删除';
            deleteBtn.className = 'delete-btn';
            deleteBtn.addEventListener('click', () => {
                // 删除这个标签
                delete groupTagsData[tag];
                renderCsvFilesList();
                renderTagsSummary();
            });
            
            li.appendChild(deleteBtn);
            tagsSummaryList.appendChild(li);
        }
    }
    
    // Apply tag to selected file
    applyTagBtn.addEventListener('click', function() {
        const tag = tagInput.value.trim();
        if (selectedFile && tag) {
            // 先从所有标签中移除该文件
            removeFileFromTags(selectedFile);
            
            // 将文件添加到新标签中
            if (!groupTagsData[tag]) {
                groupTagsData[tag] = [];
            }
            groupTagsData[tag].push(selectedFile);
            
            renderCsvFilesList();
            renderTagsSummary();
        } else if (!selectedFile) {
            alert('请先选择一个CSV文件');
        } else {
            alert('请输入标签名称');
        }
    });
    
    // Apply tag on Enter key
    tagInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const tag = tagInput.value.trim();
            if (selectedFile && tag) {
                // 先从所有标签中移除该文件
                removeFileFromTags(selectedFile);
                
                // 将文件添加到新标签中
                if (!groupTagsData[tag]) {
                    groupTagsData[tag] = [];
                }
                groupTagsData[tag].push(selectedFile);
                
                renderCsvFilesList();
                renderTagsSummary();
            } else if (!selectedFile) {
                alert('请先选择一个CSV文件');
            } else {
                alert('请输入标签名称');
            }
        }
    });
    
    // Load CSV files
    fetch('/api/csv_files')
        .then(response => response.json())
        .then(data => {
            if (data.files && Array.isArray(data.files)) {
                csvFiles = data.files;
                renderCsvFilesList();
            }
        })
        .catch(error => {
            console.error('Error loading CSV files:', error);
            // If API call fails, try to parse from the rendered JSON
            try {
                const initialFiles = JSON.parse('{{ csv_files|tojson }}');
                if (Array.isArray(initialFiles)) {
                    csvFiles = initialFiles;
                    renderCsvFilesList();
                }
            } catch (err) {
                console.error('Error parsing initial CSV files:', err);
            }
        });
    
    // Load initial group tags data
    fetch('/api/group_tags')
        .then(response => response.json())
        .then(data => {
            groupTagsData = data || {};
            renderCsvFilesList();
            renderTagsSummary();
        })
        .catch(error => {
            console.error('Error loading group tags:', error);
            // If API call fails, try to parse from the rendered JSON
            try {
                const initialTags = JSON.parse('{{ group_tags|tojson }}');
                groupTagsData = initialTags || {};
                renderCsvFilesList();
                renderTagsSummary();
            } catch (err) {
                console.error('Error parsing initial group tags:', err);
            }
        });
    
    // Save group tags configuration
    document.getElementById('save-group-tags').addEventListener('click', function() {
        fetch('/api/group_tags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(groupTagsData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('群组标签配置已保存');
            } else {
                alert('保存失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            alert('保存失败: ' + error.message);
        });
    });
    
    // Decrypt parameters form functionality
    const decryptFields = [
        'wx_dir', 'filePath', 'key', 'mobile', 'name', 
        'pid', 'version', 'wxid', 'mobel'
    ];
    let decryptParams = {};
    
    // Function to populate decrypt parameter fields
    function populateDecryptFields(params) {
        decryptParams = params;
        
        // Fill each input field with its corresponding value
        for (const field of decryptFields) {
            const inputElement = document.getElementById(`decrypt-${field}`);
            if (inputElement && params[field]) {
                inputElement.value = params[field];
            }
        }
    }
    
    // Load initial decrypt parameters
    fetch('/api/decrypt_params')
        .then(response => response.json())
        .then(data => {
            populateDecryptFields(data);
        })
        .catch(error => {
            console.error('Error loading decrypt parameters:', error);
            // If API call fails, try to parse from the rendered JSON
            try {
                const initialParams = JSON.parse('{{ decrypt_params|tojson }}');
                populateDecryptFields(initialParams);
            } catch (err) {
                console.error('Error parsing initial decrypt parameters:', err);
            }
        });
    
    // Save decrypt parameters
    document.getElementById('save-decrypt-params').addEventListener('click', function() {
        const params = {};
        
        // Collect values from all input fields
        for (const field of decryptFields) {
            const inputElement = document.getElementById(`decrypt-${field}`);
            if (inputElement) {
                params[field] = inputElement.value.trim();
            }
        }
        
        fetch('/api/decrypt_params', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('解密参数已保存');
            } else {
                alert('保存失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            alert('保存失败: ' + error.message);
        });
    });
});
