/**
 * SPADE 顶部导航栏组件 JavaScript
 * 专门处理顶部导航菜单的移动端切换功能
 */

class HeaderNav {
    constructor() {
        this.isMenuOpen = false;
        this.navToggle = null;
        this.navMenu = null;
        this.navOverlay = null;
        this.activeMenuItem = null;
        this.init();
    }

    /**
     * 初始化组件
     */
    init() {
        this.findElements();
        this.createToggleButton();
        this.createOverlay();
        this.setupEventListeners();
        this.initializeActiveMenuItem();
        this.setupKeyboardNavigation();
        console.log('🧭 Header Navigation Component initialized');
    }

    /**
     * 查找DOM元素
     */
    findElements() {
        this.navMenu = document.querySelector('.nav-menu');
        this.navToggle = document.querySelector('.nav-toggle');
        
        if (!this.navMenu) {
            console.warn('⚠️ .nav-menu element not found');
            return;
        }
    }

    /**
     * 创建切换按钮（如果不存在）
     */
    createToggleButton() {
        if (!this.navToggle && this.navMenu) {
            const header = document.querySelector('header');
            if (header) {
                this.navToggle = document.createElement('button');
                this.navToggle.className = 'nav-toggle';
                this.navToggle.setAttribute('aria-label', 'Toggle navigation menu');
                this.navToggle.setAttribute('aria-expanded', 'false');
                this.navToggle.innerHTML = '<i class="fas fa-bars"></i>';
                
                // 插入到header中
                header.appendChild(this.navToggle);
                console.log('✅ Navigation toggle button created');
            }
        }
    }

    /**
     * 创建覆盖层
     */
    createOverlay() {
        if (!this.navOverlay) {
            this.navOverlay = document.createElement('div');
            this.navOverlay.className = 'nav-overlay';
            this.navOverlay.setAttribute('aria-hidden', 'true');
            document.body.appendChild(this.navOverlay);
        }
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 切换按钮点击事件
        if (this.navToggle) {
            this.navToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleMenu();
            });
        }

        // 覆盖层点击事件
        if (this.navOverlay) {
            this.navOverlay.addEventListener('click', () => {
                this.closeMenu();
            });
        }

        // 菜单项点击事件
        if (this.navMenu) {
            this.navMenu.addEventListener('click', (e) => {
                if (e.target.tagName === 'A') {
                    this.handleMenuItemClick(e.target);
                }
            });
        }

        // 窗口大小变化事件
        window.addEventListener('resize', this.throttle(() => {
            this.handleResize();
        }, 250));

        // ESC键关闭菜单
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isMenuOpen) {
                this.closeMenu();
            }
        });

        // 点击外部区域关闭菜单
        document.addEventListener('click', (e) => {
            if (this.isMenuOpen && 
                !this.navMenu.contains(e.target) && 
                !this.navToggle.contains(e.target)) {
                this.closeMenu();
            }
        });
    }

    /**
     * 设置键盘导航
     */
    setupKeyboardNavigation() {
        if (!this.navMenu) return;

        const menuItems = this.navMenu.querySelectorAll('a');
        
        menuItems.forEach((item, index) => {
            item.addEventListener('keydown', (e) => {
                switch(e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        const nextIndex = (index + 1) % menuItems.length;
                        menuItems[nextIndex].focus();
                        break;
                    
                    case 'ArrowUp':
                        e.preventDefault();
                        const prevIndex = (index - 1 + menuItems.length) % menuItems.length;
                        menuItems[prevIndex].focus();
                        break;
                    
                    case 'Home':
                        e.preventDefault();
                        menuItems[0].focus();
                        break;
                    
                    case 'End':
                        e.preventDefault();
                        menuItems[menuItems.length - 1].focus();
                        break;
                }
            });
        });
    }

    /**
     * 切换菜单显示状态
     */
    toggleMenu() {
        if (this.isMenuOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }

    /**
     * 打开菜单
     */
    openMenu() {
        if (!this.navMenu || !this.navToggle) return;

        this.isMenuOpen = true;
        this.navMenu.classList.add('active');
        this.navOverlay.classList.add('active');
        this.navToggle.classList.add('active');
        
        // 更新ARIA属性
        this.navToggle.setAttribute('aria-expanded', 'true');
        this.navOverlay.setAttribute('aria-hidden', 'false');
        
        // 阻止页面滚动（仅移动端）
        if (window.innerWidth <= 768) {
            document.body.style.overflow = 'hidden';
        }
        
        // 聚焦到第一个菜单项
        setTimeout(() => {
            const firstMenuItem = this.navMenu.querySelector('a');
            if (firstMenuItem) {
                firstMenuItem.focus();
            }
        }, 100);

        console.log('📱 Mobile menu opened');
    }

    /**
     * 关闭菜单
     */
    closeMenu() {
        if (!this.navMenu || !this.navToggle || !this.isMenuOpen) return;

        this.isMenuOpen = false;
        this.navMenu.classList.remove('active');
        this.navOverlay.classList.remove('active');
        this.navToggle.classList.remove('active');
        
        // 更新ARIA属性
        this.navToggle.setAttribute('aria-expanded', 'false');
        this.navOverlay.setAttribute('aria-hidden', 'true');
        
        // 恢复页面滚动
        document.body.style.overflow = '';
        
        // 将焦点返回到切换按钮
        this.navToggle.focus();

        console.log('📱 Mobile menu closed');
    }

    /**
     * 处理菜单项点击
     */
    handleMenuItemClick(item) {
        // 设置活动状态
        this.setActiveMenuItem(item);
        
        // 移动端点击后关闭菜单
        if (window.innerWidth <= 768) {
            setTimeout(() => {
                this.closeMenu();
            }, 150);
        }
    }

    /**
     * 设置活动菜单项
     */
    setActiveMenuItem(item) {
        if (!this.navMenu) return;

        // 移除所有活动状态
        this.navMenu.querySelectorAll('a').forEach(link => {
            link.classList.remove('active');
        });
        
        // 设置新的活动状态
        item.classList.add('active');
        this.activeMenuItem = item;
    }

    /**
     * 初始化活动菜单项
     */
    initializeActiveMenuItem() {
        if (!this.navMenu) return;

        const currentPath = window.location.pathname.split('/').pop();
        const menuItems = this.navMenu.querySelectorAll('a');
        
        // 根据当前页面URL设置活动状态
        let found = false;
        menuItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href && (href === currentPath || href.endsWith(currentPath))) {
                this.setActiveMenuItem(item);
                found = true;
            }
        });
        
        // 如果没有找到匹配项，激活第一个
        if (!found && menuItems.length > 0) {
            this.setActiveMenuItem(menuItems[0]);
        }
    }

    /**
     * 处理窗口大小变化
     */
    handleResize() {
        // 桌面端自动关闭菜单
        if (window.innerWidth > 768 && this.isMenuOpen) {
            this.closeMenu();
        }
    }

    /**
     * 获取当前活动菜单项
     */
    getCurrentActiveItem() {
        return this.activeMenuItem;
    }

    /**
     * 获取菜单状态
     */
    getMenuState() {
        return {
            isOpen: this.isMenuOpen,
            activeItem: this.activeMenuItem ? this.activeMenuItem.textContent : null
        };
    }

    /**
     * 节流函数
     */
    throttle(func, limit) {
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
    }

    /**
     * 销毁组件
     */
    destroy() {
        // 关闭菜单
        this.closeMenu();
        
        // 移除事件监听器
        if (this.navToggle) {
            this.navToggle.removeEventListener('click', this.toggleMenu);
        }
        
        if (this.navOverlay) {
            this.navOverlay.remove();
        }
        
        // 恢复页面滚动
        document.body.style.overflow = '';
        
        console.log('🧭 Header Navigation Component destroyed');
    }
}

// 自动初始化
let headerNavInstance = null;

function initializeHeaderNav() {
    if (!headerNavInstance && document.querySelector('header')) {
        headerNavInstance = new HeaderNav();
        
        // 将实例暴露到全局，便于外部调用
        window.headerNav = headerNavInstance;
    }
}

// DOM加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeHeaderNav);
} else {
    initializeHeaderNav();
}

// 确保页面加载后初始化
window.addEventListener('load', () => {
    if (!headerNavInstance) {
        initializeHeaderNav();
    }
});

// 导出类以供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeaderNav;
} 