/**
 * SPADE 数据混淆器
 * 用于对敏感数据进行混淆和解混淆处理
 * 设计为轻量级组件，不影响性能
 */
class DataObfuscator {
    constructor() {
        this.obfuscationKey = this.generateObfuscationKey();
        this.fieldMasks = new Map();
        this.initializeFieldMasks();
    }

    /**
     * 生成混淆密钥
     */
    generateObfuscationKey() {
        const base = navigator.userAgent + window.location.hostname + Date.now().toString().slice(-6);
        return this.simpleHash(base) % 255;
    }

    /**
     * 简单哈希函数
     */
    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash);
    }

    /**
     * 初始化字段掩码
     */
    initializeFieldMasks() {
        // 定义需要混淆的敏感字段
        const sensitiveFields = [
            'Sequence',
            'DRAMP ID', 
            'UniProt Entry',
            'PDB ID',
            'Pubmed ID',
            'Gene',
            'Formula'
        ];
        
        sensitiveFields.forEach(field => {
            this.fieldMasks.set(field, this.generateFieldMask(field));
        });
    }

    /**
     * 生成字段特定的掩码
     */
    generateFieldMask(fieldName) {
        return this.simpleHash(fieldName + this.obfuscationKey) % 100;
    }

    /**
     * 混淆字符串
     */
    obfuscateString(str, fieldName = '') {
        if (!str || typeof str !== 'string') return str;
        
        const mask = this.fieldMasks.get(fieldName) || this.obfuscationKey;
        let result = '';
        
        for (let i = 0; i < str.length; i++) {
            const charCode = str.charCodeAt(i);
            const obfuscatedCode = charCode ^ (mask + i) % 255;
            result += String.fromCharCode(obfuscatedCode);
        }
        
        return btoa(result); // Base64编码
    }

    /**
     * 解混淆字符串
     */
    deobfuscateString(obfuscatedStr, fieldName = '') {
        if (!obfuscatedStr || typeof obfuscatedStr !== 'string') return obfuscatedStr;
        
        try {
            const decoded = atob(obfuscatedStr); // Base64解码
            const mask = this.fieldMasks.get(fieldName) || this.obfuscationKey;
            let result = '';
            
            for (let i = 0; i < decoded.length; i++) {
                const charCode = decoded.charCodeAt(i);
                const originalCode = charCode ^ (mask + i) % 255;
                result += String.fromCharCode(originalCode);
            }
            
            return result;
        } catch (error) {
            console.warn('解混淆失败，返回原始数据:', error);
            return obfuscatedStr;
        }
    }

    /**
     * 混淆数组
     */
    obfuscateArray(arr, fieldName = '') {
        if (!Array.isArray(arr)) return arr;
        
        return arr.map(item => {
            if (typeof item === 'string') {
                return this.obfuscateString(item, fieldName);
            } else if (typeof item === 'object') {
                return this.obfuscateObject(item);
            }
            return item;
        });
    }

    /**
     * 解混淆数组
     */
    deobfuscateArray(arr, fieldName = '') {
        if (!Array.isArray(arr)) return arr;
        
        return arr.map(item => {
            if (typeof item === 'string') {
                return this.deobfuscateString(item, fieldName);
            } else if (typeof item === 'object') {
                return this.deobfuscateObject(item);
            }
            return item;
        });
    }

    /**
     * 混淆对象
     */
    obfuscateObject(obj) {
        if (!obj || typeof obj !== 'object' || obj === null) return obj;
        
        const result = {};
        
        for (const [key, value] of Object.entries(obj)) {
            if (this.shouldObfuscateField(key)) {
                if (typeof value === 'string') {
                    result[key] = this.obfuscateString(value, key);
                } else if (Array.isArray(value)) {
                    result[key] = this.obfuscateArray(value, key);
                } else if (typeof value === 'object') {
                    result[key] = this.obfuscateObject(value);
                } else {
                    result[key] = value;
                }
            } else {
                if (typeof value === 'object' && value !== null) {
                    result[key] = this.obfuscateObject(value);
                } else {
                    result[key] = value;
                }
            }
        }
        
        // 添加混淆标记
        result._obfuscated = true;
        result._timestamp = Date.now();
        
        return result;
    }

    /**
     * 解混淆对象
     */
    deobfuscateObject(obj) {
        if (!obj || typeof obj !== 'object' || obj === null) return obj;
        
        const result = {};
        
        for (const [key, value] of Object.entries(obj)) {
            // 跳过混淆标记
            if (key === '_obfuscated' || key === '_timestamp') continue;
            
            if (this.shouldObfuscateField(key)) {
                if (typeof value === 'string') {
                    result[key] = this.deobfuscateString(value, key);
                } else if (Array.isArray(value)) {
                    result[key] = this.deobfuscateArray(value, key);
                } else if (typeof value === 'object') {
                    result[key] = this.deobfuscateObject(value);
                } else {
                    result[key] = value;
                }
            } else {
                if (typeof value === 'object' && value !== null) {
                    result[key] = this.deobfuscateObject(value);
                } else {
                    result[key] = value;
                }
            }
        }
        
        return result;
    }

    /**
     * 判断字段是否需要混淆
     */
    shouldObfuscateField(fieldName) {
        return this.fieldMasks.has(fieldName);
    }

    /**
     * 混淆完整数据
     */
    obfuscateData(data) {
        if (Array.isArray(data)) {
            return data.map(item => this.obfuscateObject(item));
        } else if (typeof data === 'object') {
            return this.obfuscateObject(data);
        }
        return data;
    }

    /**
     * 解混淆完整数据
     */
    deobfuscateData(data) {
        if (Array.isArray(data)) {
            return data.map(item => this.deobfuscateObject(item));
        } else if (typeof data === 'object') {
            return this.deobfuscateObject(data);
        }
        return data;
    }

    /**
     * 添加诱饵数据
     */
    addDecoyData(data) {
        if (!data || typeof data !== 'object') return data;
        
        const decoyData = { ...data };
        
        // 添加虚假字段
        const decoyFields = {
            '_decoy_checksum': Math.random().toString(36).substring(7),
            '_decoy_version': '1.0.0',
            '_decoy_timestamp': Date.now() - Math.random() * 86400000, // 随机过去24小时内时间
            '_decoy_source': 'backup_server',
            '_decoy_format': 'json_v2'
        };
        
        Object.assign(decoyData, decoyFields);
        
        return decoyData;
    }

    /**
     * 移除诱饵数据
     */
    removeDecoyData(data) {
        if (!data || typeof data !== 'object') return data;
        
        const cleanData = { ...data };
        
        // 移除诱饵字段
        Object.keys(cleanData).forEach(key => {
            if (key.startsWith('_decoy_')) {
                delete cleanData[key];
            }
        });
        
        return cleanData;
    }

    /**
     * 检查数据完整性
     */
    verifyDataIntegrity(data) {
        if (!data || typeof data !== 'object') return false;
        
        // 检查是否包含必要字段
        const requiredFields = ['DRAMP ID'];
        return requiredFields.some(field => 
            this.findValueInObject(data, field) !== undefined
        );
    }

    /**
     * 在对象中查找值
     */
    findValueInObject(obj, key) {
        if (!obj || typeof obj !== 'object') return undefined;
        
        if (obj.hasOwnProperty(key)) return obj[key];
        
        for (const value of Object.values(obj)) {
            if (typeof value === 'object' && value !== null) {
                const found = this.findValueInObject(value, key);
                if (found !== undefined) return found;
            }
        }
        
        return undefined;
    }

    /**
     * 创建数据代理
     * 在获取敏感数据时自动解混淆
     */
    createDataProxy(data) {
        const self = this;
        
        if (typeof data !== 'object' || data === null) return data;
        
        return new Proxy(data, {
            get(target, property) {
                const value = target[property];
                
                if (self.shouldObfuscateField(property) && typeof value === 'string') {
                    return self.deobfuscateString(value, property);
                }
                
                if (typeof value === 'object' && value !== null) {
                    return self.createDataProxy(value);
                }
                
                return value;
            }
        });
    }

    /**
     * 获取混淆统计信息
     */
    getObfuscationStats(data) {
        let totalFields = 0;
        let obfuscatedFields = 0;
        
        const countFields = (obj) => {
            if (!obj || typeof obj !== 'object') return;
            
            for (const [key, value] of Object.entries(obj)) {
                totalFields++;
                
                if (this.shouldObfuscateField(key)) {
                    obfuscatedFields++;
                }
                
                if (typeof value === 'object' && value !== null) {
                    countFields(value);
                }
            }
        };
        
        countFields(data);
        
        return {
            totalFields,
            obfuscatedFields,
            obfuscationRate: totalFields > 0 ? (obfuscatedFields / totalFields * 100).toFixed(2) + '%' : '0%'
        };
    }

    /**
     * 快速访问常用字段的方法
     */
    getQuickAccess(data) {
        if (!data) return {};
        
        const deobfuscatedData = this.deobfuscateData(data);
        const finder = new DataFinder(deobfuscatedData);
        
        return {
            drampId: finder.findValue("DRAMP ID"),
            peptideName: finder.findValue("Peptide Name"),
            sequence: finder.findValue("Sequence"),
            literature: finder.findValue("Literature"),
            bioActivity: finder.findValue("Biological Activity"),
            targetOrganism: finder.findValue("Target Organism"),
            function: finder.findValue("Function"),
            mass: finder.findValue("Mass"),
            pi: finder.findValue("PI"),
            formula: finder.findValue("Formula")
        };
    }

    /**
     * 高效数据查找器类
     */
    static DataFinder = class {
        constructor(data) {
            this.data = data;
            this.cache = new Map();
            this.fieldPaths = new Map();
            this.initializeFieldMap();
        }

        initializeFieldMap() {
            this.flattenData(this.data, []);
        }

        flattenData(obj, path) {
            if (obj === null || obj === undefined) return;

            if (Array.isArray(obj)) {
                obj.forEach((item, index) => {
                    this.flattenData(item, [...path, index]);
                });
            } else if (typeof obj === 'object') {
                Object.entries(obj).forEach(([key, value]) => {
                    const currentPath = [...path, key];
                    
                    if (!this.fieldPaths.has(key)) {
                        this.fieldPaths.set(key, []);
                    }
                    this.fieldPaths.get(key).push({
                        path: currentPath,
                        value: value
                    });

                    if (value && typeof value === 'object') {
                        this.flattenData(value, currentPath);
                    }
                });
            }
        }

        findValue(targetKey) {
            if (this.cache.has(targetKey)) {
                return this.cache.get(targetKey);
            }

            let result = null;

            if (this.fieldPaths.has(targetKey)) {
                const matches = this.fieldPaths.get(targetKey);
                if (matches.length > 0) {
                    result = matches[0].value;
                }
            }

            if (result === null) {
                const lowerKey = targetKey.toLowerCase();
                for (const [key, matches] of this.fieldPaths.entries()) {
                    if (key.toLowerCase() === lowerKey && matches.length > 0) {
                        result = matches[0].value;
                        break;
                    }
                }
            }

            this.cache.set(targetKey, result);
            return result;
        }
    };
}

// 创建全局实例
window.DataObfuscator = DataObfuscator;

// 自动初始化
if (typeof window !== 'undefined') {
    window.dataObfuscator = new DataObfuscator();
    console.log('🔒 Data Obfuscator initialized');
}

console.log('🔒 SPADE Data Obfuscation System Loaded'); 