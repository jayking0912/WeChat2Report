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
    
    // Irrelevant groups list functionality
    const irrelevantGroupsList = document.getElementById('irrelevant-groups-list');
    const newGroupInput = document.getElementById('new-group-input');
    const addGroupBtn = document.getElementById('add-group-btn');
    let groupsData = [];
    
    // Function to render groups list
    function renderGroupsList() {
        irrelevantGroupsList.innerHTML = '';
        
        groupsData.forEach((group, index) => {
            const li = document.createElement('li');
            
            const groupName = document.createElement('span');
            groupName.textContent = group;
            li.appendChild(groupName);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = '删除';
            deleteBtn.className = 'delete-btn';
            deleteBtn.addEventListener('click', () => {
                groupsData.splice(index, 1);
                renderGroupsList();
            });
            
            li.appendChild(deleteBtn);
            irrelevantGroupsList.appendChild(li);
        });
    }
    
    // Add new group
    addGroupBtn.addEventListener('click', function() {
        const newGroup = newGroupInput.value.trim();
        if (newGroup) {
            groupsData.push(newGroup);
            newGroupInput.value = '';
            renderGroupsList();
        }
    });
    
    // Add group on Enter key
    newGroupInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const newGroup = newGroupInput.value.trim();
            if (newGroup) {
                groupsData.push(newGroup);
                newGroupInput.value = '';
                renderGroupsList();
            }
        }
    });
    
    // Load initial groups data
    fetch('/api/irrelevant_groups')
        .then(response => response.json())
        .then(data => {
            if (data.groups && Array.isArray(data.groups)) {
                groupsData = data.groups;
                renderGroupsList();
            } else if (Array.isArray(data)) {
                // For backward compatibility
                groupsData = data;
                renderGroupsList();
            }
        })
        .catch(error => {
            console.error('Error loading irrelevant groups:', error);
            // If API call fails, try to parse from the rendered JSON
            try {
                const initialGroups = JSON.parse('{{ irrelevant_groups|tojson }}');
                if (Array.isArray(initialGroups)) {
                    groupsData = initialGroups;
                    renderGroupsList();
                }
            } catch (err) {
                console.error('Error parsing initial groups:', err);
            }
        });
    
    // Save irrelevant groups configuration
    document.getElementById('save-irrelevant-groups').addEventListener('click', function() {
        fetch('/api/irrelevant_groups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ groups: groupsData })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('不相关群组配置已保存');
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
            const inputElement = document.getElementById(field);
            if (inputElement && params[field] !== undefined) {
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
        // Gather values from all input fields
        const params = {};
        for (const field of decryptFields) {
            const inputElement = document.getElementById(field);
            if (inputElement) {
                // Convert to number if the field is pid
                if (field === 'pid') {
                    const value = parseInt(inputElement.value);
                    params[field] = isNaN(value) ? null : value;
                } else {
                    params[field] = inputElement.value;
                }
            }
        }
        
        // Send data to server
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
                alert('解密参数配置已保存');
            } else {
                alert('保存失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            alert('保存失败: ' + error.message);
        });
    });
});
