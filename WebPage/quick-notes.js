/**
 * SPADE 快速笔记组件 - 简约版
 * 功能：跨页面保存、悬浮窗口、自由移动、折叠展开、内容下载
 * 设计理念：简约、清晰、功能优先
 */
class QuickNotes {
    constructor() {
        this.isVisible = false;
        this.isCollapsed = false;
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        this.noteContainer = null;
        this.textarea = null;
        this.storageKey = 'spade-quick-notes';
        this.positionKey = 'spade-notes-position';
        this.collapsedKey = 'spade-notes-collapsed';
        
        this.init();
    }

    init() {
        this.createNotesContainer();
        this.loadSavedNotes();
        this.loadSavedPosition();
        this.loadCollapsedState();
        this.setupEventListeners();
        console.log('🗒️ Quick Notes (简约版) initialized');
    }

    createNotesContainer() {
        this.noteContainer = document.createElement('div');
        this.noteContainer.className = 'quick-notes-container';
        this.noteContainer.style.display = 'none';
        
        this.noteContainer.innerHTML = `
            <div class="notes-header">
                <div class="notes-title">
                    <i class="fas fa-sticky-note"></i>
                    <span>快速笔记</span>
                </div>
                <div class="notes-controls">
                    <button class="notes-btn collapse-btn" title="折叠/展开">
                        <i class="fas fa-minus"></i>
                    </button>
                    <button class="notes-btn download-btn" title="下载笔记">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="notes-btn clear-btn" title="清空笔记">
                        <i class="fas fa-trash"></i>
                    </button>
                    <button class="notes-btn close-btn" title="关闭">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="notes-content">
                <textarea 
                    class="notes-textarea" 
                    placeholder="在这里记录您的想法和笔记..."
                    spellcheck="false"
                ></textarea>
                <div class="notes-footer">
                    <span class="notes-info">
                        <i class="fas fa-shield-alt"></i>
                        本地存储
                    </span>
                    <span class="notes-count">0 字符</span>
                </div>
            </div>
        `;

        this.addStyles();
        document.body.appendChild(this.noteContainer);
        this.textarea = this.noteContainer.querySelector('.notes-textarea');
    }

    addStyles() {
        const styleId = 'quick-notes-styles';
        if (document.getElementById(styleId)) return;

        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .quick-notes-container {
                position: fixed;
                top: 100px;
                right: 20px;
                width: 300px;
                background: white;
                border-radius: 6px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                z-index: 9999;
                font-family: 'Helvetica Neue', Arial, sans-serif;
                border: 1px solid #e0e0e0;
                transition: all 0.2s ease;
                user-select: none;
            }

            .quick-notes-container.collapsed .notes-content {
                display: none;
            }

            .quick-notes-container.dragging {
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                z-index: 10001;
            }

            .notes-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 12px;
                background: #2A5C8B;
                color: white;
                border-radius: 6px 6px 0 0;
                cursor: move;
                font-size: 14px;
                min-height: 46px;
                box-sizing: border-box;
            }

            .quick-notes-container.collapsed .notes-header {
                border-radius: 6px;
            }

            .notes-title {
                display: flex;
                align-items: center;
                font-weight: 500;
                gap: 6px;
                flex: 1;
                min-width: 0;
                white-space: nowrap;
                overflow: hidden;
            }

            .notes-title i {
                font-size: 12px;
            }

            .notes-controls {
                display: flex;
                gap: 6px;
                align-items: center;
                flex-shrink: 0;
            }

            .notes-btn {
                background: none;
                border: none;
                color: white;
                width: 26px;
                height: 26px;
                border-radius: 3px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                transition: background-color 0.2s ease;
                flex-shrink: 0;
                min-width: 26px;
                position: relative;
            }

            .notes-btn:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .notes-btn:active {
                background: rgba(255, 255, 255, 0.3);
            }

            .collapse-btn i {
                transition: transform 0.2s ease;
            }

            .quick-notes-container.collapsed .collapse-btn i {
                transform: rotate(180deg);
            }

            .notes-content {
                display: flex;
                flex-direction: column;
                height: 250px;
            }

            .notes-textarea {
                flex: 1;
                border: none;
                outline: none;
                padding: 12px;
                font-family: inherit;
                font-size: 13px;
                line-height: 1.4;
                resize: none;
                background: transparent;
                color: #333;
            }

            .notes-textarea::placeholder {
                color: #999;
            }

            .notes-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
                font-size: 11px;
                color: #666;
            }

            .notes-info {
                display: flex;
                align-items: center;
                gap: 4px;
            }

            .notes-info i {
                color: #4CAF50;
                font-size: 10px;
            }

            .notes-count {
                font-weight: 500;
                color: #333;
            }

            /* 响应式设计 */
            @media (max-width: 1024px) {
                .quick-notes-container {
                    width: 290px;
                }
            }

            @media (max-width: 768px) {
                .quick-notes-container {
                    width: 280px;
                    right: 10px;
                    top: 80px;
                    max-width: calc(100vw - 20px);
                }
                
                .notes-content {
                    height: 200px;
                }

                .notes-header {
                    padding: 8px 10px;
                    font-size: 13px;
                }

                .notes-btn {
                    width: 28px;
                    height: 28px;
                    min-width: 28px;
                    font-size: 12px;
                }

                .notes-controls {
                    gap: 5px;
                }

                .notes-textarea {
                    padding: 10px;
                    font-size: 14px;
                }
            }

            @media (max-width: 480px) {
                .quick-notes-container {
                    width: calc(100vw - 20px);
                    right: 10px;
                    left: 10px;
                    top: 70px;
                    max-width: none;
                }

                .notes-header {
                    padding: 8px;
                    font-size: 12px;
                }

                .notes-title {
                    gap: 4px;
                }

                .notes-title span {
                    display: none; /* 在超小屏幕上隐藏文字，只显示图标 */
                }

                .notes-btn {
                    width: 30px;
                    height: 30px;
                    min-width: 30px;
                    font-size: 13px;
                }

                .notes-controls {
                    gap: 4px;
                }

                .notes-content {
                    height: 180px;
                }

                .notes-textarea {
                    padding: 8px;
                    font-size: 15px; /* 移动端稍大的字体 */
                    line-height: 1.5;
                }

                .notes-footer {
                    padding: 6px 8px;
                    font-size: 10px;
                }
            }

            @media (max-width: 360px) {
                .quick-notes-container {
                    width: calc(100vw - 16px);
                    right: 8px;
                    left: 8px;
                }

                .notes-content {
                    height: 160px;
                }
            }

            /* 触摸设备优化 */
            @media (hover: none) and (pointer: coarse) {
                .notes-btn {
                    width: 32px;
                    height: 32px;
                    min-width: 32px;
                    font-size: 14px;
                }

                .notes-btn:hover {
                    background: none; /* 移除触摸设备的hover效果 */
                }

                .notes-btn:active {
                    background: rgba(255, 255, 255, 0.3);
                    transform: scale(0.95);
                }

                .notes-textarea {
                    font-size: 16px; /* 防止iOS缩放 */
                    line-height: 1.5;
                }
            }

            /* 横屏适配 */
            @media (max-height: 600px) and (orientation: landscape) {
                .quick-notes-container {
                    top: 60px;
                }

                .notes-content {
                    height: 150px;
                }
            }

            /* 简化的滚动条 */
            .notes-textarea::-webkit-scrollbar {
                width: 4px;
            }
            
            .notes-textarea::-webkit-scrollbar-track {
                background: #f1f1f1;
            }
            
            .notes-textarea::-webkit-scrollbar-thumb {
                background: #c1c1c1;
                border-radius: 2px;
            }

            .notes-textarea::-webkit-scrollbar-thumb:hover {
                background: #a8a8a8;
            }
        `;

        document.head.appendChild(style);
    }

    setupEventListeners() {
        const header = this.noteContainer.querySelector('.notes-header');
        const collapseBtn = this.noteContainer.querySelector('.collapse-btn');
        const downloadBtn = this.noteContainer.querySelector('.download-btn');
        const clearBtn = this.noteContainer.querySelector('.clear-btn');
        const closeBtn = this.noteContainer.querySelector('.close-btn');

        // 拖拽事件
        header.addEventListener('mousedown', this.startDrag.bind(this));
        document.addEventListener('mousemove', this.drag.bind(this));
        document.addEventListener('mouseup', this.endDrag.bind(this));

        // 触摸设备支持
        header.addEventListener('touchstart', this.startDrag.bind(this));
        document.addEventListener('touchmove', this.drag.bind(this));
        document.addEventListener('touchend', this.endDrag.bind(this));

        // 按钮事件
        collapseBtn.addEventListener('click', this.toggleCollapse.bind(this));
        downloadBtn.addEventListener('click', this.downloadNotes.bind(this));
        clearBtn.addEventListener('click', this.clearNotes.bind(this));
        closeBtn.addEventListener('click', this.hide.bind(this));

        // 笔记内容变化
        this.textarea.addEventListener('input', () => {
            this.saveNotes();
            this.updateCharCount();
        });

        // 全局快捷键
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
                e.preventDefault();
                this.toggle();
            }
        });

        // 防止事件冒泡
        this.noteContainer.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // 监听窗口大小变化，自动调整位置
        window.addEventListener('resize', this.handleResize.bind(this));
        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.handleResize(), 300); // 延迟处理方向变化
        });
    }

    startDrag(e) {
        if (e.target.closest('.notes-btn')) return;
        
        this.isDragging = true;
        this.noteContainer.classList.add('dragging');
        
        const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
        
        const rect = this.noteContainer.getBoundingClientRect();
        this.dragOffset.x = clientX - rect.left;
        this.dragOffset.y = clientY - rect.top;
        
        // 在移动设备上添加触觉反馈
        if (e.type === 'touchstart' && 'vibrate' in navigator) {
            navigator.vibrate(50);
        }
        
        e.preventDefault();
    }

    drag(e) {
        if (!this.isDragging) return;
        
        const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
        
        let newX = clientX - this.dragOffset.x;
        let newY = clientY - this.dragOffset.y;
        
        // 增强的边界检测，考虑移动设备的安全区域
        const containerRect = this.noteContainer.getBoundingClientRect();
        const safeMargin = window.innerWidth < 768 ? 10 : 0; // 移动设备增加安全边距
        const maxX = window.innerWidth - containerRect.width - safeMargin;
        const maxY = window.innerHeight - containerRect.height - safeMargin;
        
        newX = Math.max(safeMargin, Math.min(newX, maxX));
        newY = Math.max(safeMargin, Math.min(newY, maxY));
        
        this.noteContainer.style.left = newX + 'px';
        this.noteContainer.style.top = newY + 'px';
        this.noteContainer.style.right = 'auto';
        
        e.preventDefault();
    }

    endDrag() {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        this.noteContainer.classList.remove('dragging');
        this.savePosition();
    }

    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed;
        
        if (this.isCollapsed) {
            this.noteContainer.classList.add('collapsed');
        } else {
            this.noteContainer.classList.remove('collapsed');
        }
        
        localStorage.setItem(this.collapsedKey, this.isCollapsed);
    }

    show() {
        this.isVisible = true;
        this.noteContainer.style.display = 'block';
        this.textarea.focus();
    }

    hide() {
        this.isVisible = false;
        this.noteContainer.style.display = 'none';
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }

    saveNotes() {
        const content = this.textarea.value;
        localStorage.setItem(this.storageKey, content);
        
        // 自动备份
        const backup = {
            content: content,
            timestamp: new Date().toISOString()
        };
        localStorage.setItem(this.storageKey + '_backup', JSON.stringify(backup));
    }

    loadSavedNotes() {
        try {
            const savedContent = localStorage.getItem(this.storageKey);
            if (savedContent) {
                this.textarea.value = savedContent;
                this.updateCharCount();
            }
        } catch (error) {
            console.error('Failed to load saved notes:', error);
        }
    }

    savePosition() {
        const rect = this.noteContainer.getBoundingClientRect();
        const position = {
            top: rect.top,
            left: rect.left
        };
        localStorage.setItem(this.positionKey, JSON.stringify(position));
    }

    loadSavedPosition() {
        try {
            const savedPosition = localStorage.getItem(this.positionKey);
            if (savedPosition) {
                const position = JSON.parse(savedPosition);
                
                // 根据设备类型调整验证逻辑
                const containerWidth = window.innerWidth < 480 ? window.innerWidth - 20 : 300;
                const safeMargin = window.innerWidth < 768 ? 10 : 0;
                const maxX = window.innerWidth - containerWidth - safeMargin;
                const maxY = window.innerHeight - 100 - safeMargin;
                
                if (position.left >= safeMargin && position.left <= maxX && 
                    position.top >= safeMargin && position.top <= maxY) {
                    this.noteContainer.style.left = position.left + 'px';
                    this.noteContainer.style.top = position.top + 'px';
                    this.noteContainer.style.right = 'auto';
                } else {
                    // 如果保存的位置无效，设置默认位置
                    this.setDefaultPosition();
                }
            } else {
                this.setDefaultPosition();
            }
        } catch (error) {
            console.error('Failed to load saved position:', error);
            this.setDefaultPosition();
        }
    }

    setDefaultPosition() {
        // 根据屏幕尺寸设置默认位置
        if (window.innerWidth < 480) {
            // 移动设备：居中显示
            this.noteContainer.style.left = '10px';
            this.noteContainer.style.right = '10px';
            this.noteContainer.style.top = '70px';
        } else if (window.innerWidth < 768) {
            // 平板设备：右侧显示
            this.noteContainer.style.right = '10px';
            this.noteContainer.style.left = 'auto';
            this.noteContainer.style.top = '80px';
        } else {
            // 桌面设备：右侧显示
            this.noteContainer.style.right = '20px';
            this.noteContainer.style.left = 'auto';
            this.noteContainer.style.top = '100px';
        }
    }

    handleResize() {
        if (!this.noteContainer) return;

        const rect = this.noteContainer.getBoundingClientRect();
        const containerWidth = window.innerWidth < 480 ? window.innerWidth - 20 : 300;
        const safeMargin = window.innerWidth < 768 ? 10 : 0;
        const maxX = window.innerWidth - containerWidth - safeMargin;
        const maxY = window.innerHeight - rect.height - safeMargin;

        let currentLeft = rect.left;
        let currentTop = rect.top;

        // 确保窗口在可见区域内
        if (currentLeft > maxX || currentLeft < safeMargin) {
            this.setDefaultPosition();
            return;
        }

        if (currentTop > maxY || currentTop < safeMargin) {
            // 只调整垂直位置
            const newTop = Math.max(safeMargin, Math.min(currentTop, maxY));
            this.noteContainer.style.top = newTop + 'px';
        }

        // 移动设备时强制宽度适配
        if (window.innerWidth < 480) {
            this.noteContainer.style.left = '10px';
            this.noteContainer.style.right = '10px';
        }
    }

    loadCollapsedState() {
        try {
            const isCollapsed = localStorage.getItem(this.collapsedKey) === 'true';
            if (isCollapsed) {
                this.isCollapsed = true;
                this.noteContainer.classList.add('collapsed');
            }
        } catch (error) {
            console.error('Failed to load collapsed state:', error);
        }
    }

    updateCharCount() {
        const count = this.textarea.value.length;
        const countElement = this.noteContainer.querySelector('.notes-count');
        if (countElement) {
            countElement.textContent = `${count} 字符`;
        }
    }

    downloadNotes() {
        const content = this.textarea.value;
        if (!content.trim()) {
            alert('笔记内容为空，无法下载。');
            return;
        }

        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SPADE_笔记_${new Date().toISOString().slice(0, 10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    clearNotes() {
        if (confirm('确定要清空笔记内容吗？此操作无法撤销。')) {
            this.textarea.value = '';
            this.saveNotes();
            this.updateCharCount();
        }
    }

    // 公共API
    getContent() {
        return this.textarea.value;
    }

    setContent(content) {
        this.textarea.value = content;
        this.saveNotes();
        this.updateCharCount();
    }

    appendContent(content) {
        this.textarea.value += content;
        this.saveNotes();
        this.updateCharCount();
    }

    isShown() {
        return this.isVisible;
    }
}

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    if (!window.quickNotes) {
        window.quickNotes = new QuickNotes();
    }
});

// 确保在页面加载后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.quickNotes) {
            window.quickNotes = new QuickNotes();
        }
    });
} else {
    if (!window.quickNotes) {
        window.quickNotes = new QuickNotes();
    }
} 