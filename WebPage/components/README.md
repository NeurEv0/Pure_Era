# SPADE 导航组件库

## 概述

这是一套专为 SPADE 系统设计的导航组件库，包含侧边栏导航和顶部导航两个独立组件。所有组件都采用简约风格，支持响应式布局，提供流畅的用户交互体验。

## 组件列表

### 🧭 侧边栏导航组件 (Sidebar Navigation)
用于页面内容的分区导航，支持悬停展开和移动端切换。

### 📱 顶部导航组件 (Header Navigation)  
用于主要页面间的导航，专门处理移动端菜单切换功能。

## 文件结构

```
components/
├── sidebar-nav.css         # 侧边栏导航样式文件
├── sidebar-nav.js          # 侧边栏导航功能脚本
├── header-nav.css          # 顶部导航样式文件
├── header-nav.js           # 顶部导航功能脚本
├── header-nav-README.md    # 顶部导航使用说明
├── sidebar-nav-demo.html   # 侧边栏演示页面
├── header-nav-demo.html    # 顶部导航演示页面
└── README.md              # 组件总览说明
```

## 快速开始

### 1. 引入组件文件

在HTML文档的 `<head>` 部分添加样式文件：

```html
<!-- 预加载CSS -->
<link rel="preload" href="components/sidebar-nav.css" as="style" onload="this.onload=null;this.rel='stylesheet'">

<!-- 回退方案 -->
<noscript>
    <link rel="stylesheet" href="components/sidebar-nav.css">
</noscript>
```

在页面底部加载JavaScript文件：

```html
<script src="components/sidebar-nav.js"></script>
```

### 2. HTML 结构

组件需要以下HTML结构：

```html
<div class="shell">
    <ul class="nav">
        <li class="active">
            <a href="#general">
                <span class="icon"><i class="fas fa-info"></i></span>
                <span class="text">General Information</span>
            </a>
        </li>
        <li>
            <a href="#activity">
                <span class="icon"><i class="fas fa-vial"></i></span>
                <span class="text">Activity Information</span>
            </a>
        </li>
        <!-- 更多导航项... -->
    </ul>
</div>
```

### 3. CSS 变量配置

组件使用CSS变量进行样式定制：

```css
:root {
    --sidebar-bg: #2b1055;        /* 侧边栏背景色 */
    --sidebar-hover: #7597de;     /* 悬停色调 */
    --background: #F8F9FA;        /* 主背景色 */
    --header-height: 80px;        /* 顶部栏高度 */
    --primary: #2A5C8B;          /* 主色调 */
}
```

## 功能特性

### 核心功能
- 🎯 **智能导航**: 自动处理导航项的活动状态切换
- 🖱️ **平滑滚动**: 点击导航项平滑滚动到对应部分
- 📱 **响应式设计**: 自适应桌面、平板、手机屏幕
- ⌨️ **键盘支持**: 支持键盘导航（Enter/Space键）
- 🔄 **自动初始化**: 页面加载后自动初始化，无需手动调用

### 移动端优化
- 📲 **触摸友好**: 优化的触摸交互体验
- 🎛️ **自动切换按钮**: 在小屏幕下自动显示侧边栏切换按钮
- 🔒 **智能隐藏**: 小屏幕下侧边栏默认隐藏，点击外部自动关闭
- 📐 **安全边距**: 考虑移动设备的安全区域

### 辅助功能
- ⬆️ **回到顶部**: 自动生成滚动到顶部按钮
- 🎨 **悬停效果**: 优雅的悬停动画和视觉反馈
- 🔧 **灵活配置**: 支持多种配置选项和自定义

## API 参考

### SidebarNav 类

组件自动初始化后，可通过 `window.sidebarNav` 访问实例。

#### 方法

| 方法名 | 参数 | 描述 |
|--------|------|------|
| `setActiveNavItem(element)` | `element`: DOM元素 | 设置指定导航项为活动状态 |
| `toggleSidebar()` | 无 | 切换侧边栏显示/隐藏状态 |
| `openSidebar()` | 无 | 打开侧边栏 |
| `closeSidebar()` | 无 | 关闭侧边栏 |
| `smoothScrollToSection(targetId)` | `targetId`: 字符串 | 平滑滚动到指定ID的部分 |
| `getCurrentActiveItem()` | 无 | 获取当前活动的导航项 |
| `enableScrollBasedNavigation()` | 无 | 启用基于滚动位置的自动导航 |
| `destroy()` | 无 | 销毁组件，清理事件监听器 |

#### 示例用法

```javascript
// 访问组件实例
const sidebar = window.sidebarNav;

// 手动设置活动导航项
const navItem = document.querySelector('.nav li:nth-child(2)');
sidebar.setActiveNavItem(navItem);

// 切换侧边栏
sidebar.toggleSidebar();

// 启用基于滚动的导航（可选）
sidebar.enableScrollBasedNavigation();
```

## 响应式断点

| 屏幕尺寸 | 断点 | 侧边栏行为 |
|----------|------|------------|
| 桌面端 | > 992px | 正常显示，悬停展开 |
| 平板端 | 768px - 992px | 适度缩小，保持功能 |
| 手机端 | < 768px | 默认隐藏，按钮切换 |
| 小屏手机 | < 480px | 全宽适配，优化触摸 |

## 自定义样式

### 修改颜色主题

```css
:root {
    --sidebar-bg: #1a237e;        /* 深蓝主题 */
    --sidebar-hover: #3f51b5;     /* 配套悬停色 */
}
```

### 调整尺寸

```css
.shell {
    width: 100px;  /* 默认宽度 */
}

.shell:hover {
    width: 320px;  /* 展开宽度 */
}
```

### 修改动画

```css
.shell {
    transition: width 0.3s ease;  /* 更快的动画 */
}
```

## 最佳实践

### 1. 性能优化
- 使用 `preload` 预加载CSS文件
- 脚本放在页面底部以避免阻塞渲染
- 组件自动进行事件节流优化

### 2. 可访问性
- 为按钮添加适当的 `aria-label`
- 支持键盘导航
- 确保足够的颜色对比度

### 3. 移动端体验
- 测试不同设备的触摸交互
- 考虑横屏模式的适配
- 为触摸操作提供足够的点击区域

## 故障排除

### 常见问题

**Q: 组件没有正确初始化**
A: 确认HTML结构正确，且CSS/JS文件路径无误。检查浏览器控制台的错误信息。

**Q: 移动端侧边栏无法切换**
A: 检查是否有其他脚本冲突，确认FontAwesome图标库已正确加载。

**Q: 样式显示异常**
A: 确认CSS变量已正确定义，检查是否有样式覆盖冲突。

**Q: 平滑滚动不工作**
A: 确认目标元素ID存在，检查是否有其他滚动脚本冲突。

### 调试工具

组件初始化时会在控制台输出确认信息：
```
🧭 Sidebar Navigation Component initialized
```

## 更新日志

### v1.1.0 (2024-12-18)
- 🎯 **新增顶部导航组件**
- 📱 专门的移动端菜单切换功能
- 🎨 与网站主题色保持一致的简约设计
- ⌨️ 完整的键盘导航和无障碍支持
- 🔄 组件化架构，便于复用和维护

### v1.0.1 (2024-12-18)
- 🐛 **修复侧边栏展开时文字不显示的问题**
- ✨ 添加 `.shell.expanded .text` 样式规则确保展开状态下文字显示
- 🔧 统一悬停和展开状态的文字显示逻辑
- 📱 改进移动端文字显示体验
- 🎯 使用 `!important` 确保样式优先级正确

### v1.0.0 (2024-12-18)
- ✨ 初始版本发布
- 🎯 完整的响应式侧边栏功能
- 📱 移动端优化
- ⌨️ 键盘导航支持
- 🎨 简约设计风格

## 兼容性

- ✅ Chrome 70+
- ✅ Firefox 65+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ iOS Safari 12+
- ✅ Android Chrome 70+

## 许可证

MIT License - 详见项目根目录LICENSE文件。 