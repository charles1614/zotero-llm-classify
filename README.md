# Zotero LLM Classify

基于LLM的Zotero文献智能分类系统，使用大语言模型分析文献内容并自动创建分类体系。

## 🚀 快速开始

### 1. 环境配置

#### 新用户（推荐）
```bash
# 1. 创建配置文件
python setup_config.py create

# 2. 交互式配置
python setup_config.py setup

# 3. 验证配置
python setup_config.py validate
```

#### 从旧配置迁移
```bash
# 从setup_env.sh迁移到新配置系统
python migrate_config.py
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 运行脚本
```bash
# 生成分类体系并创建集合
python 005_generate_schema_and_create_collections.py --test

# 对文献进行重新分类
python 006_reclassify_with_new_schema.py --plan

# 应用分类到Zotero
python 007_apply_classification_to_zotero.py data/classification_plan.json --test
```

## 📋 脚本说明

### 核心脚本
- **005_generate_schema_and_create_collections.py**: 使用LLM生成分类体系并创建Zotero集合
- **006_reclassify_with_new_schema.py**: 使用新分类体系对文献进行智能分类
- **007_apply_classification_to_zotero.py**: 安全地将分类结果应用到Zotero
- **008_check_and_export_missing_proper_items.py**: 检查并导出未分类的文献

### 配置工具
- **setup_config.py**: 配置管理工具
- **migrate_config.py**: 从旧配置迁移到新系统
- **config.py**: 统一配置管理模块

## ⚙️ 配置系统

### 环境变量配置
项目使用现代化的配置管理系统，支持：

1. **`.env`文件配置**：主要配置方式
2. **环境变量**：支持系统环境变量
3. **类型安全**：使用pydantic进行配置验证
4. **多环境支持**：开发、测试、生产环境

### 配置示例
```bash
# 复制配置模板
cp env.example .env

# 编辑配置文件
nano .env
```

### 主要配置项
```bash
# LLM配置
LLM_API_TYPE=openai-compatible
LLM_API_KEY=your_api_key_here
LLM_MODEL=gemini-2.5-pro

# Zotero配置
ZOTERO_USER_ID=your_user_id
ZOTERO_API_KEY=your_api_key

# 环境配置
ENVIRONMENT=development
DEBUG=false
```

## 🔧 配置工具使用

### 创建配置文件
```bash
python setup_config.py create
```

### 交互式配置
```bash
python setup_config.py setup
```

### 验证配置
```bash
python setup_config.py validate
```

### 查看帮助
```bash
python setup_config.py help
```

## 📁 项目结构

```
zotero-llm-classify/
├── config.py                    # 统一配置管理
├── setup_config.py              # 配置设置工具
├── migrate_config.py            # 配置迁移工具
├── env.example                  # 环境变量示例
├── requirements.txt             # 依赖包
├── 005_generate_schema_and_create_collections.py
├── 006_reclassify_with_new_schema.py
├── 007_apply_classification_to_zotero.py
├── 008_check_and_export_missing_proper_items.py
├── llm_client.py               # LLM客户端
├── cli.py                      # 命令行工具
└── data/                       # 数据目录
```

## 🛠️ 开发指南

### 配置管理最佳实践

1. **使用配置常量**：避免硬编码值
2. **类型安全**：使用pydantic进行配置验证
3. **环境分离**：开发、测试、生产环境配置分离
4. **敏感信息保护**：API密钥等敏感信息使用环境变量

### 添加新配置项

1. 在`config.py`中添加配置类
2. 在`env.example`中添加示例
3. 在`setup_config.py`中添加交互式配置
4. 更新文档

## 🔒 安全注意事项

1. **不要提交`.env`文件**：包含敏感信息
2. **使用环境变量**：生产环境使用系统环境变量
3. **定期轮换密钥**：定期更新API密钥
4. **最小权限原则**：只授予必要的API权限

## 📝 更新日志

### v2.0.0 - 现代化配置系统
- ✅ 引入pydantic-settings进行类型安全配置管理
- ✅ 支持.env文件配置
- ✅ 提供配置迁移工具
- ✅ 消除硬编码问题
- ✅ 改进配置验证和错误处理

### v1.x.x - 原始版本
- 使用setup_env.sh进行环境配置
- 硬编码配置值
- 基础功能实现

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## �� 许可证

MIT License 