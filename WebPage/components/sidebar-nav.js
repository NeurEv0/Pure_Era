/**
 * SPADE 侧边栏导航组件 JavaScript
 * 处理侧边栏的交互逻辑和响应式行为
 */

class SidebarNav {
    constructor() {
        this.isExpanded = false;
        this.currentActiveItem = null;
        this.init();
    }

    init() {
        this.setupNavigationInteraction();
        this.setupSidebarToggle();
        this.setupResponsiveHandlers();
        this.setupScrollToTopButton();
        this.initializeActiveNavItem();
        console.log('🧭 Sidebar Navigation Component initialized');
    }

    /**
     * 初始化导航交互
     */
    setupNavigationInteraction() {
        const navItems = document.querySelectorAll(".shell .nav li");
        
        navItems.forEach((item, index) => {
            const link = item.querySelector('a');
            if (!link) return;

            // 点击事件处理
            item.addEventListener("click", (e) => {
                this.setActiveNavItem(item);
                
                // 处理锚点链接的平滑滚动
                const href = link.getAttribute('href');
                if (href && href.startsWith('#')) {
                    e.preventDefault();
                    this.smoothScrollToSection(href);
                }
            });

            // 键盘支持
            link.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    item.click();
                }
            });
        });
    }

    /**
     * 设置活动导航项
     */
    setActiveNavItem(activeItem) {
        // 移除所有活动状态
        document.querySelectorAll(".shell .nav li").forEach(item => {
            item.classList.remove("active");
        });
        
        // 设置新的活动状态
        activeItem.classList.add("active");
        this.currentActiveItem = activeItem;
    }

    /**
     * 平滑滚动到指定部分
     */
    smoothScrollToSection(targetId) {
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            const headerHeight = parseInt(getComputedStyle(document.documentElement)
                .getPropertyValue('--header-height') || '80');
            const offsetTop = targetElement.offsetTop - headerHeight - 20;
            
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    }

    /**
     * 初始化活动导航项（基于当前URL或默认第一个）
     */
    initializeActiveNavItem() {
        const navItems = document.querySelectorAll(".shell .nav li");
        
        // 检查URL哈希
        const currentHash = window.location.hash;
        if (currentHash) {
            const matchingItem = Array.from(navItems).find(item => {
                const link = item.querySelector('a');
                return link && link.getAttribute('href') === currentHash;
            });
            
            if (matchingItem) {
                this.setActiveNavItem(matchingItem);
                return;
            }
        }
        
        // 默认激活第一个项目
        if (navItems.length > 0) {
            this.setActiveNavItem(navItems[0]);
        }
    }

    /**
     * 设置侧边栏切换功能
     */
    setupSidebarToggle() {
        // 创建切换按钮（如果不存在）
        let toggleButton = document.getElementById('sidebar-toggle');
        if (!toggleButton) {
            toggleButton = this.createSidebarToggleButton();
        }

        const sidebar = document.querySelector('.shell');
        
        if (toggleButton && sidebar) {
            toggleButton.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // 点击外部区域关闭侧边栏（移动端）
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 767 && this.isExpanded) {
                const sidebar = document.querySelector('.shell');
                const toggleButton = document.getElementById('sidebar-toggle');
                
                if (sidebar && toggleButton && 
                    !sidebar.contains(e.target) && 
                    !toggleButton.contains(e.target)) {
                    this.closeSidebar();
                }
            }
        });
    }

    /**
     * 创建侧边栏切换按钮
     */
    createSidebarToggleButton() {
        const button = document.createElement('button');
        button.id = 'sidebar-toggle';
        button.className = 'sidebar-toggle';
        button.setAttribute('aria-label', 'Toggle sidebar');
        button.innerHTML = '<i class="fas fa-grip-lines"></i>';
        document.body.appendChild(button);
        return button;
    }

    /**
     * 切换侧边栏显示状态
     */
    toggleSidebar() {
        const sidebar = document.querySelector('.shell');
        if (!sidebar) return;

        if (this.isExpanded) {
            this.closeSidebar();
        } else {
            this.openSidebar();
        }
    }

    /**
     * 打开侧边栏
     */
    openSidebar() {
        const sidebar = document.querySelector('.shell');
        if (sidebar) {
            sidebar.classList.add('expanded');
            this.isExpanded = true;
            
            // 更新body类名以调整主内容区域
            document.body.classList.add('sidebar-expanded');
        }
    }

    /**
     * 关闭侧边栏
     */
    closeSidebar() {
        const sidebar = document.querySelector('.shell');
        if (sidebar) {
            sidebar.classList.remove('expanded');
            this.isExpanded = false;
            
            // 移除body类名
            document.body.classList.remove('sidebar-expanded');
        }
    }

    /**
     * 设置响应式处理程序
     */
    setupResponsiveHandlers() {
        // 节流函数
        const throttle = (func, limit) => {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        };

        // 窗口大小变化处理
        const handleResize = throttle(() => {
            // 在桌面端自动关闭展开的侧边栏
            if (window.innerWidth > 767 && this.isExpanded) {
                this.closeSidebar();
            }
        }, 250);

        window.addEventListener('resize', handleResize);
        window.addEventListener('orientationchange', () => {
            setTimeout(handleResize, 300);
        });
    }

    /**
     * 设置滚动到顶部按钮
     */
    setupScrollToTopButton() {
        // 创建滚动到顶部按钮（如果不存在）
        let scrollTopBtn = document.getElementById('scrollTop');
        if (!scrollTopBtn) {
            scrollTopBtn = this.createScrollTopButton();
        }

        // 节流滚动事件
        const throttle = (func, limit) => {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        };

        const handleScroll = throttle(() => {
            if (window.pageYOffset > 300) {
                scrollTopBtn.classList.add('visible');
            } else {
                scrollTopBtn.classList.remove('visible');
            }
        }, 100);

        window.addEventListener('scroll', handleScroll, { passive: true });

        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    /**
     * 创建滚动到顶部按钮
     */
    createScrollTopButton() {
        const button = document.createElement('div');
        button.id = 'scrollTop';
        button.className = 'scroll-top';
        button.innerHTML = '<i class="fas fa-arrow-up"></i>';
        button.setAttribute('title', 'Scroll to top');
        button.style.cssText = `
            position: fixed;
            right: 15px;
            bottom: 15px;
            width: 40px;
            height: 40px;
            background: var(--primary, #2A5C8B);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transition: 0.3s;
            z-index: 950;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        
        // 添加可见状态的样式
        const style = document.createElement('style');
        style.textContent = `
            .scroll-top.visible {
                opacity: 1;
                visibility: visible;
            }
            .scroll-top:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(button);
        return button;
    }

    /**
     * 根据页面内容自动设置活动导航项
     */
    updateActiveNavBasedOnScroll() {
        const sections = document.querySelectorAll('[id^="general"], [id^="activity"], [id^="structure"], [id^="properties"], [id^="comments"], [id^="literature"]');
        const navItems = document.querySelectorAll(".shell .nav li");
        
        if (sections.length === 0) return;

        const headerHeight = parseInt(getComputedStyle(document.documentElement)
            .getPropertyValue('--header-height') || '80');
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        // 找到当前可见的部分
        let currentSection = null;
        sections.forEach(section => {
            const sectionTop = section.offsetTop - headerHeight - 50;
            if (scrollTop >= sectionTop) {
                currentSection = section;
            }
        });

        if (currentSection) {
            const sectionId = currentSection.id;
            const matchingNavItem = Array.from(navItems).find(item => {
                const link = item.querySelector('a');
                return link && link.getAttribute('href') === `#${sectionId}`;
            });

            if (matchingNavItem && !matchingNavItem.classList.contains('active')) {
                this.setActiveNavItem(matchingNavItem);
            }
        }
    }

    /**
     * 启用基于滚动的导航项自动更新
     */
    enableScrollBasedNavigation() {
        const throttle = (func, limit) => {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        };

        const handleScroll = throttle(() => {
            this.updateActiveNavBasedOnScroll();
        }, 150);

        window.addEventListener('scroll', handleScroll, { passive: true });
    }

    /**
     * 获取当前活动的导航项
     */
    getCurrentActiveItem() {
        return this.currentActiveItem;
    }

    /**
     * 销毁组件
     */
    destroy() {
        // 移除事件监听器
        window.removeEventListener('resize', this.handleResize);
        window.removeEventListener('scroll', this.handleScroll);
        
        // 移除创建的元素
        const toggleButton = document.getElementById('sidebar-toggle');
        const scrollTopButton = document.getElementById('scrollTop');
        
        if (toggleButton) toggleButton.remove();
        if (scrollTopButton) scrollTopButton.remove();
        
        console.log('🧭 Sidebar Navigation Component destroyed');
    }
}

// 自动初始化
let sidebarNavInstance = null;

function initializeSidebarNav() {
    if (!sidebarNavInstance && document.querySelector('.shell')) {
        sidebarNavInstance = new SidebarNav();
        
        // 将实例暴露到全局，便于外部调用
        window.sidebarNav = sidebarNavInstance;
    }
}

// DOM加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSidebarNav);
} else {
    initializeSidebarNav();
}

// 确保页面加载后初始化
window.addEventListener('load', () => {
    if (!sidebarNavInstance) {
        initializeSidebarNav();
    }
});

// 导出类以供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SidebarNav;
} 