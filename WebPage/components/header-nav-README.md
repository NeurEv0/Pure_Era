# SPADE 顶部导航栏组件

## 概述

这是一个专门用于处理顶部导航栏移动端菜单切换的独立组件。组件提供简约的设计风格，与网站主题色保持一致，支持完整的响应式体验和无障碍访问。

## 文件结构

```
components/
├── header-nav.css         # 顶部导航样式文件
├── header-nav.js          # 顶部导航功能脚本
└── header-nav-README.md   # 使用说明文档
```

## 快速开始

### 1. 引入组件文件

在HTML文档的 `<head>` 部分添加样式文件：

```html
<!-- 预加载CSS -->
<link rel="preload" href="components/header-nav.css" as="style" onload="this.onload=null;this.rel='stylesheet'">

<!-- 回退方案 -->
<noscript>
    <link rel="stylesheet" href="components/header-nav.css">
</noscript>
```

在页面底部加载JavaScript文件：

```html
<script src="components/header-nav.js"></script>
```

### 2. HTML 结构

组件需要以下HTML结构：

```html
<header>
    <div class="logo-container">
        <a href="#" class="logo">
            <img src="../icon/logo.png" style="vertical-align: middle; height: 30px;">
            SPADE
        </a>
        <div style="color: white; font-size: 0.6em;">
            System for Antimicrobial Peptide<br>Management and Database
        </div>
    </div>
    
    <!-- 导航菜单 -->
    <ul class="nav-menu">
        <li><a href="home.html">Home</a></li>
        <li><a href="search.html">Search</a></li>
        <li><a href="tools.html">Tools</a></li>
        <li><a href="statistics.html">Statistics</a></li>
        <li><a href="#" id="quick-notes-btn" class="notes-trigger" title="快速笔记">
            <i class="fas fa-sticky-note"></i>
        </a></li>
    </ul>
    
    <!-- 切换按钮会自动生成 -->
</header>
```

### 3. CSS 变量配置

组件使用CSS变量进行样式定制：

```css
:root {
    --sidebar-bg: #2b1055;        /* 导航栏背景色 */
    --sidebar-hover: #7597de;     /* 悬停/活动状态颜色 */
    --header-height: 80px;        /* 顶部栏高度 */
}
```

## 功能特性

### 🎯 核心功能
- **智能切换**: 自动检测屏幕尺寸，在移动端显示汉堡菜单按钮
- **平滑动画**: 菜单展开/收起具有流畅的过渡动画
- **活动状态**: 自动根据当前页面设置活动菜单项
- **自动关闭**: 点击菜单项后自动关闭移动端菜单

### 📱 移动端优化
- **触摸友好**: 44px的触摸目标，符合移动端设计规范
- **覆盖层**: 菜单展开时显示半透明覆盖层
- **滚动锁定**: 菜单打开时禁止页面滚动
- **延迟动画**: 菜单项依次出现的动画效果

### ⌨️ 无障碍支持
- **键盘导航**: 支持方向键、Home、End键导航
- **ARIA属性**: 完整的可访问性属性支持
- **焦点管理**: 智能的焦点流转和恢复
- **ESC键支持**: ESC键快速关闭菜单

### 🎨 设计特性
- **主题一致**: 使用网站主色调，保持视觉统一
- **简约风格**: 清晰的层次结构和简洁的视觉效果
- **响应式**: 完美适配桌面、平板、手机等设备
- **高性能**: 使用CSS3变换和节流优化性能

## API 参考

### HeaderNav 类

组件自动初始化后，可通过 `window.headerNav` 访问实例。

#### 方法

| 方法名 | 参数 | 描述 |
|--------|------|------|
| `toggleMenu()` | 无 | 切换菜单显示/隐藏状态 |
| `openMenu()` | 无 | 打开菜单 |
| `closeMenu()` | 无 | 关闭菜单 |
| `setActiveMenuItem(item)` | `item`: DOM元素 | 设置指定菜单项为活动状态 |
| `getCurrentActiveItem()` | 无 | 获取当前活动的菜单项 |
| `getMenuState()` | 无 | 获取菜单状态信息 |
| `destroy()` | 无 | 销毁组件，清理事件监听器 |

#### 示例用法

```javascript
// 访问组件实例
const headerNav = window.headerNav;

// 手动切换菜单
headerNav.toggleMenu();

// 获取菜单状态
const state = headerNav.getMenuState();
console.log('菜单是否打开:', state.isOpen);
console.log('当前活动项:', state.activeItem);

// 设置活动菜单项
const menuItem = document.querySelector('.nav-menu a[href="search.html"]');
headerNav.setActiveMenuItem(menuItem);
```

## 响应式断点

| 屏幕尺寸 | 断点 | 行为 |
|----------|------|------|
| 桌面端 | > 768px | 水平导航栏，无切换按钮 |
| 平板端 | 481px - 768px | 水平导航栏，间距调整 |
| 手机端 | ≤ 480px | 汉堡菜单，全宽适配 |

## 自定义样式

### 修改主题色

```css
:root {
    --sidebar-bg: #1a237e;        /* 深蓝主题 */
    --sidebar-hover: #3f51b5;     /* 配套悬停色 */
}
```

### 调整菜单尺寸

```css
@media (max-width: 768px) {
    .nav-menu {
        width: 300px;  /* 菜单宽度 */
    }
    
    .nav-menu a {
        padding: 18px 30px;  /* 菜单项内边距 */
    }
}
```

### 修改动画时长

```css
.nav-menu {
    transition: right 0.4s ease;  /* 更慢的动画 */
}

.nav-menu.active li:nth-child(1) { 
    transition-delay: 0.05s;  /* 更快的依次出现 */
}
```

## 事件监听

组件提供了完整的事件监听支持：

```javascript
// 监听菜单状态变化
window.addEventListener('headerNavToggle', (e) => {
    console.log('菜单状态:', e.detail.isOpen);
});

// 监听活动菜单项变化
window.addEventListener('headerNavActiveChange', (e) => {
    console.log('新活动项:', e.detail.activeItem);
});
```

## 最佳实践

### 1. 性能优化
- 使用 `preload` 预加载CSS文件
- 脚本放在页面底部避免阻塞渲染
- 组件自动进行事件节流优化

### 2. 可访问性
- 确保所有菜单项都有有意义的文本
- 为图标按钮添加适当的 `aria-label`
- 测试键盘导航功能

### 3. 移动端体验
- 确保触摸目标至少44px
- 测试不同设备的手势操作
- 考虑横屏模式的适配

## 兼容性

- ✅ Chrome 70+
- ✅ Firefox 65+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ iOS Safari 12+
- ✅ Android Chrome 70+

## 更新日志

### v1.0.0 (2024-12-18)
- ✨ 初始版本发布
- 🎯 完整的移动端菜单切换功能
- 📱 响应式设计和动画效果
- ⌨️ 键盘导航和无障碍支持
- 🎨 简约设计风格

## 许可证

MIT License - 详见项目根目录LICENSE文件。 