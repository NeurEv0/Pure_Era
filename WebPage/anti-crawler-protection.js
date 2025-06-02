/**
 * SPADE 反爬虫保护组件
 * 包含用户行为检测、数据混淆、请求频率限制等功能
 * 设计为纯前端组件，对用户透明
 */
class AntiCrawlerProtection {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.userBehavior = {
            mouseMovements: 0,
            keyPresses: 0,
            scrolls: 0,
            clicks: 0,
            pageStartTime: Date.now(),
            humanScore: 0,
            lastActivityTime: Date.now()
        };
        this.requestHistory = new Map();
        this.encryptionKey = this.generateEncryptionKey();
        this.decoyRequests = [];
        
        // 初始化保护机制
        this.init();
    }

    /**
     * 初始化保护机制
     */
    init() {
        this.setupBehaviorTracking();
        this.setupRequestInterceptor();
        this.startDecoySystem();
        console.log('🛡️ Anti-crawler protection initialized');
    }

    /**
     * 生成会话ID
     */
    generateSessionId() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < 32; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    /**
     * 生成加密密钥
     */
    generateEncryptionKey() {
        const timestamp = Date.now().toString();
        const userAgent = navigator.userAgent;
        const screenInfo = `${screen.width}x${screen.height}`;
        return this.simpleHash(timestamp + userAgent + screenInfo).substring(0, 16);
    }

    /**
     * 简单哈希函数
     */
    simpleHash(str) {
        let hash = 0;
        if (str.length === 0) return hash.toString();
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return Math.abs(hash).toString(36);
    }

    /**
     * 设置行为追踪
     */
    setupBehaviorTracking() {
        // 鼠标移动追踪
        document.addEventListener('mousemove', () => {
            this.userBehavior.mouseMovements++;
            this.userBehavior.lastActivityTime = Date.now();
            this.updateHumanScore();
        });

        // 键盘按键追踪
        document.addEventListener('keydown', () => {
            this.userBehavior.keyPresses++;
            this.userBehavior.lastActivityTime = Date.now();
            this.updateHumanScore();
        });

        // 滚动追踪
        document.addEventListener('scroll', () => {
            this.userBehavior.scrolls++;
            this.userBehavior.lastActivityTime = Date.now();
            this.updateHumanScore();
        });

        // 点击追踪
        document.addEventListener('click', () => {
            this.userBehavior.clicks++;
            this.userBehavior.lastActivityTime = Date.now();
            this.updateHumanScore();
        });

        // 页面可见性变化追踪
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.userBehavior.lastActivityTime = Date.now();
            }
        });
    }

    /**
     * 更新人类行为评分
     */
    updateHumanScore() {
        const timeSpent = Date.now() - this.userBehavior.pageStartTime;
        const activityScore = Math.min(
            (this.userBehavior.mouseMovements * 0.1) +
            (this.userBehavior.keyPresses * 0.5) +
            (this.userBehavior.scrolls * 0.3) +
            (this.userBehavior.clicks * 0.8),
            50
        );
        const timeScore = Math.min(timeSpent / 1000 * 0.1, 30);
        this.userBehavior.humanScore = activityScore + timeScore;
    }

    /**
     * 检查是否为人类用户
     */
    isHumanBehavior() {
        this.updateHumanScore();
        const minTimeSpent = Date.now() - this.userBehavior.pageStartTime;
        
        // 基本检查：是否有足够的用户交互
        if (this.userBehavior.humanScore < 5 && minTimeSpent > 2000) {
            return false;
        }

        // 检查是否有最近的活动
        if (Date.now() - this.userBehavior.lastActivityTime > 30000) {
            return false;
        }

        return true;
    }

    /**
     * 检查请求频率
     */
    checkRequestFrequency(url) {
        const now = Date.now();
        const key = this.getUrlKey(url);
        
        if (!this.requestHistory.has(key)) {
            this.requestHistory.set(key, []);
        }
        
        const requests = this.requestHistory.get(key);
        
        // 清理旧请求记录（超过5分钟）
        const recentRequests = requests.filter(time => now - time < 300000);
        this.requestHistory.set(key, recentRequests);
        
        // 检查频率限制
        const shortTermRequests = recentRequests.filter(time => now - time < 60000); // 1分钟内
        if (shortTermRequests.length > 10) {
            throw new Error('请求过于频繁，请稍后再试');
        }
        
        const mediumTermRequests = recentRequests.filter(time => now - time < 180000); // 3分钟内
        if (mediumTermRequests.length > 20) {
            throw new Error('请求频率超限，请稍后再试');
        }
        
        // 记录当前请求
        recentRequests.push(now);
        this.requestHistory.set(key, recentRequests);
    }

    /**
     * 获取URL关键字
     */
    getUrlKey(url) {
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.pathname;
        } catch {
            return url;
        }
    }

    /**
     * 简单加密
     */
    encrypt(data) {
        const jsonStr = JSON.stringify(data);
        const encrypted = this.xorEncrypt(jsonStr, this.encryptionKey);
        return btoa(encrypted); // Base64编码
    }

    /**
     * 简单解密
     */
    decrypt(encryptedData) {
        try {
            const decoded = atob(encryptedData);
            const decrypted = this.xorDecrypt(decoded, this.encryptionKey);
            return JSON.parse(decrypted);
        } catch (error) {
            throw new Error('数据解密失败');
        }
    }

    /**
     * XOR 加密
     */
    xorEncrypt(text, key) {
        let result = '';
        for (let i = 0; i < text.length; i++) {
            const textChar = text.charCodeAt(i);
            const keyChar = key.charCodeAt(i % key.length);
            result += String.fromCharCode(textChar ^ keyChar);
        }
        return result;
    }

    /**
     * XOR 解密
     */
    xorDecrypt(encryptedText, key) {
        return this.xorEncrypt(encryptedText, key); // XOR解密与加密相同
    }

    /**
     * 添加随机延迟
     */
    async addRandomDelay() {
        const delay = Math.random() * 1000 + 500; // 500-1500ms随机延迟
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    /**
     * 生成诱饵请求
     */
    generateDecoyRequest() {
        const decoyIds = ['FAKE001', 'FAKE002', 'FAKE003', 'TEST001', 'DUMMY001'];
        const randomId = decoyIds[Math.floor(Math.random() * decoyIds.length)];
        const timestamp = Date.now();
        
        // 发送诱饵请求到不存在的资源
        fetch(`./Database/decoy_${randomId}_${timestamp}.json`, {
            method: 'HEAD',
            cache: 'no-cache'
        }).catch(() => {
            // 静默忽略错误，这是预期的
        });
    }

    /**
     * 启动诱饵系统
     */
    startDecoySystem() {
        // 随机发送诱饵请求
        setInterval(() => {
            if (Math.random() < 0.1) { // 10% 概率
                this.generateDecoyRequest();
            }
        }, 30000); // 每30秒检查一次
    }

    /**
     * 设置请求拦截器
     */
    setupRequestInterceptor() {
        const originalFetch = window.fetch;
        const self = this;
        
        window.fetch = async function(url, options = {}) {
            // 检查是否为数据请求
            if (self.isDataRequest(url)) {
                // 执行保护检查
                await self.performProtectionChecks(url);
            }
            
            // 执行原始请求
            const response = await originalFetch.call(this, url, options);
            
            // 如果是数据请求且成功，处理响应
            if (self.isDataRequest(url) && response.ok) {
                return self.processDataResponse(response);
            }
            
            return response;
        };
    }

    /**
     * 检查是否为数据请求
     */
    isDataRequest(url) {
        const dataPatterns = [
            /\/Database\/.*\.json$/,
            /\/database\/.*\.json$/,
            /\/result\/.*\.json$/,
            /peptide.*\.json$/
        ];
        
        return dataPatterns.some(pattern => pattern.test(url));
    }

    /**
     * 执行保护检查
     */
    async performProtectionChecks(url) {
        // 1. 检查人类行为
        if (!this.isHumanBehavior()) {
            await this.addRandomDelay();
            throw new Error('访问被限制：检测到非正常用户行为');
        }

        // 2. 检查请求频率
        this.checkRequestFrequency(url);

        // 3. 添加随机延迟
        await this.addRandomDelay();

        // 4. 发送随机诱饵请求
        if (Math.random() < 0.2) { // 20% 概率
            this.generateDecoyRequest();
        }
    }

    /**
     * 处理数据响应
     */
    async processDataResponse(response) {
        const originalJson = response.json;
        
        response.json = async function() {
            const data = await originalJson.call(this);
            
            // 添加水印和混淆数据
            const protectedData = {
                ...data,
                _metadata: {
                    session: Math.random().toString(36).substring(7),
                    timestamp: Date.now(),
                    checksum: Math.random().toString(36).substring(7)
                }
            };
            
            return protectedData;
        };
        
        return response;
    }

    /**
     * 创建安全的数据获取函数
     */
    createSecureFetch() {
        const self = this;
        
        return async function(url, options = {}) {
            try {
                // 执行保护检查
                if (self.isDataRequest(url)) {
                    await self.performProtectionChecks(url);
                }
                
                // 执行原始fetch
                const response = await fetch(url, options);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                return response;
            } catch (error) {
                console.warn('🛡️ Protected fetch intercepted request:', error.message);
                throw error;
            }
        };
    }

    /**
     * 获取保护状态
     */
    getProtectionStatus() {
        return {
            sessionId: this.sessionId,
            humanScore: this.userBehavior.humanScore,
            isHuman: this.isHumanBehavior(),
            requestCount: Array.from(this.requestHistory.values())
                .reduce((total, requests) => total + requests.length, 0),
            uptime: Date.now() - this.userBehavior.pageStartTime
        };
    }

    /**
     * 清理保护数据
     */
    cleanup() {
        this.requestHistory.clear();
        this.decoyRequests.length = 0;
        console.log('🛡️ Anti-crawler protection cleaned up');
    }
}

// 创建全局保护实例
window.AntiCrawlerProtection = AntiCrawlerProtection;

// 自动初始化保护
if (typeof window !== 'undefined') {
    window.protectionInstance = new AntiCrawlerProtection();
    
    // 页面卸载时清理
    window.addEventListener('beforeunload', () => {
        if (window.protectionInstance) {
            window.protectionInstance.cleanup();
        }
    });
    
    // 开发者控制台检测（额外保护）
    let devtools = {
        open: false,
        orientation: null
    };
    
    setInterval(() => {
        if (window.outerHeight - window.innerHeight > 200 || 
            window.outerWidth - window.innerWidth > 200) {
            if (!devtools.open) {
                devtools.open = true;
                console.warn('🛡️ 检测到开发者工具，某些功能可能受限');
            }
        } else {
            devtools.open = false;
        }
    }, 500);
}

console.log('🛡️ SPADE Anti-Crawler Protection System Loaded'); 