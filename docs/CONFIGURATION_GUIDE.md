# 配置指南 - Configuration Guide

## 概述

本项目使用统一的配置管理系统，所有配置都通过环境变量或`.env`文件进行管理，确保符合行业最佳实践。

## 配置结构

### 1. 应用配置 (Application Configuration)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `ENVIRONMENT` | `development` | 运行环境 (development, production, testing) | 全局 |
| `DEBUG` | `false` | 调试模式开关 | 日志输出 |
| `DATA_DIR` | `data` | 数据文件存储目录 | 所有脚本 |

### 2. LLM配置 (LLM Configuration)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `LLM_API_TYPE` | `gemini-direct` | LLM API类型 (openai-compatible, gemini-direct) | LLM客户端 |
| `LLM_API_KEY` | - | OpenAI兼容API密钥 | LLM请求 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI兼容API基础URL | LLM请求 |
| `LLM_MODEL` | `gemini-2.5-pro` | 使用的LLM模型名称 | LLM请求 |
| `GEMINI_API_KEY` | - | Gemini直接API密钥 | Gemini请求 |
| `GEMINI_API_ENDPOINT` | `https://generativelanguage.googleapis.com` | Gemini API端点 | Gemini请求 |
| `LLM_RPM_LIMIT` | `5` | 每分钟请求限制 | 速率控制 |
| `LLM_TIMEOUT` | `30.0` | 请求超时时间(秒) | 网络请求 |
| `LLM_CONNECT_TIMEOUT` | `10.0` | 连接超时时间(秒) | 网络连接 |

### 3. Zotero配置 (Zotero Configuration)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `ZOTERO_USER_ID` | - | Zotero用户ID (必需) | Zotero API |
| `ZOTERO_API_KEY` | - | Zotero API密钥 (必需) | Zotero API |
| `ZOTERO_BASE_URL` | `https://api.zotero.org` | Zotero API基础URL | Zotero API |

### 4. 文件配置 (File Configuration)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `LITERATURE_FILE` | `data/literature_info.xlsx` | 文献信息文件路径 | 005, 006脚本 |
| `SCHEMA_FILE` | `data/classification_schema.json` | 分类schema文件路径 | 005脚本 |
| `LLM_SCHEMA_FILE` | `data/llm_generated_schema.json` | LLM生成的schema文件路径 | 005脚本 |
| `FIXED_SCHEMA_FILE` | `data/fixed_schema.json` | 修复后的schema文件路径 | 005脚本 |

### 5. 处理配置 (Processing Configuration)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `DEFAULT_BATCH_SIZE` | `50` | 默认批量大小 | 006脚本批量处理 |
| `DEFAULT_TEST_ITEMS` | `10` | 默认测试项目数 | 测试模式 |
| `DEFAULT_DRY_RUN_ITEMS` | `50` | 默认干运行项目数 | 005脚本干运行 |
| `DEFAULT_MAX_ITEMS` | `100` | 默认最大处理项目数 | 005脚本 |
| `DEFAULT_LIMIT` | `100` | 默认API请求限制 | 008脚本分页 |

### 6. Token限制 (Token Limits)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `MAX_TOKENS_LIMIT` | `250000` | 最大token限制 | LLM请求验证 |
| `DEFAULT_OUTPUT_TOKENS` | `2000` | 默认输出token数 | LLM响应长度 |

### 7. 文本限制 (Text Limits)

| 环境变量 | 默认值 | 说明 | 影响范围 |
|---------|--------|------|----------|
| `TITLE_PREVIEW_LENGTH` | `50` | 标题预览长度 | 日志输出 |
| `DESCRIPTION_PREVIEW_LENGTH` | `100` | 描述预览长度 | 日志输出 |
| `ABSTRACT_LIMIT` | `500` | 摘要长度限制 | 008脚本摘要提取 |

## 配置影响详解

### 脚本级别影响

#### 001_collect_literature_info.py
- `ZOTERO_USER_ID`, `ZOTERO_API_KEY`, `ZOTERO_BASE_URL`: Zotero API访问
- `LITERATURE_FILE`: 输出文献信息文件路径
- `DEFAULT_LIMIT`: API分页请求大小
- `TITLE_PREVIEW_LENGTH`: 文献标题在日志中的显示长度

#### 004_apply_classification.py
- `LLM_API_TYPE`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`: LLM API配置
- `GEMINI_API_KEY`, `GEMINI_API_ENDPOINT`: Gemini API配置
- `LLM_RPM_LIMIT`, `LLM_TIMEOUT`, `LLM_CONNECT_TIMEOUT`: LLM请求控制
- `LITERATURE_FILE`: 输入文献信息文件
- `LLM_SCHEMA_FILE`: 输出LLM生成的schema文件
- `DEFAULT_TEST_ITEMS`: 测试模式处理的文献数量
- `MAX_TOKENS_LIMIT`, `DEFAULT_OUTPUT_TOKENS`: LLM token控制
- `TITLE_PREVIEW_LENGTH`, `DESCRIPTION_PREVIEW_LENGTH`: 日志显示长度

#### 005_refine_and_reclassify.py
- `LLM_API_TYPE`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`: LLM API配置
- `GEMINI_API_KEY`, `GEMINI_API_ENDPOINT`: Gemini API配置
- `LLM_RPM_LIMIT`, `LLM_TIMEOUT`, `LLM_CONNECT_TIMEOUT`: LLM请求控制
- `SCHEMA_FILE`: 输入分类schema文件
- `LLM_SCHEMA_FILE`: 输入LLM生成的schema文件
- `FIXED_SCHEMA_FILE`: 输出修复后的schema文件
- `DEFAULT_MAX_ITEMS`: 最大处理文献数量
- `DEFAULT_DRY_RUN_ITEMS`: 干运行时的文献数量
- `DEFAULT_TEST_ITEMS`: 测试模式的文献数量
- `MAX_TOKENS_LIMIT`, `DEFAULT_OUTPUT_TOKENS`: LLM token控制
- `TITLE_PREVIEW_LENGTH`, `DESCRIPTION_PREVIEW_LENGTH`: 日志显示长度

#### 006_reclassify_with_new_schema.py
- `LLM_API_TYPE`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`: LLM API配置
- `GEMINI_API_KEY`, `GEMINI_API_ENDPOINT`: Gemini API配置
- `LLM_RPM_LIMIT`, `LLM_TIMEOUT`, `LLM_CONNECT_TIMEOUT`: LLM请求控制
- `FIXED_SCHEMA_FILE`: 输入修复后的schema文件
- `DEFAULT_BATCH_SIZE`: 批量处理的大小
- `DEFAULT_TEST_ITEMS`: 测试模式的文献数量
- `MAX_TOKENS_LIMIT`, `DEFAULT_OUTPUT_TOKENS`: LLM token控制
- `TITLE_PREVIEW_LENGTH`, `DESCRIPTION_PREVIEW_LENGTH`: 日志显示长度

#### 008_check_and_export_missing_proper_items.py
- `ZOTERO_USER_ID`, `ZOTERO_API_KEY`, `ZOTERO_BASE_URL`: Zotero API访问
- `DEFAULT_LIMIT`: API分页请求的大小
- `ABSTRACT_LIMIT`: 从Zotero notes提取摘要的最大长度
- `TITLE_PREVIEW_LENGTH`: 文献标题在日志中的显示长度

### 全局影响

#### 所有脚本
- `ENVIRONMENT`: 运行环境，影响日志级别和错误处理
- `DEBUG`: 调试模式，影响详细日志输出
- `DATA_DIR`: 数据目录，影响所有数据文件的存储位置

#### 所有LLM相关脚本
- `LLM_API_TYPE`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`: LLM API基础配置
- `GEMINI_API_KEY`, `GEMINI_API_ENDPOINT`: Gemini API配置
- `LLM_RPM_LIMIT`, `LLM_TIMEOUT`, `LLM_CONNECT_TIMEOUT`: LLM请求控制
- `MAX_TOKENS_LIMIT`, `DEFAULT_OUTPUT_TOKENS`: LLM token控制
- `TITLE_PREVIEW_LENGTH`, `DESCRIPTION_PREVIEW_LENGTH`: 日志显示长度

#### 所有Zotero相关脚本
- `ZOTERO_USER_ID`, `ZOTERO_API_KEY`, `ZOTERO_BASE_URL`: Zotero API访问

### 性能影响

#### 批量处理
- `DEFAULT_BATCH_SIZE`: 影响LLM请求的效率和成本
  - 较大值：减少API调用次数，但增加单次请求的token消耗
  - 较小值：增加API调用次数，但减少单次请求的token消耗

#### 速率限制
- `LLM_RPM_LIMIT`: 影响LLM API的请求频率
  - 较高值：处理速度更快，但可能触发API限制
  - 较低值：处理速度较慢，但更安全

#### Token管理
- `MAX_TOKENS_LIMIT`: 影响可处理的文献数量
  - 超过限制时会警告用户并建议减少文献数量
- `DEFAULT_OUTPUT_TOKENS`: 影响LLM响应的详细程度
  - 较大值：响应更详细，但成本更高
  - 较小值：响应较简洁，成本更低

### 用户体验影响

#### 日志输出
- `TITLE_PREVIEW_LENGTH`: 控制文献标题在日志中的显示长度
- `DESCRIPTION_PREVIEW_LENGTH`: 控制分类描述在日志中的显示长度
- 超过限制的文本会被截断并显示"..."

#### 测试模式
- `DEFAULT_TEST_ITEMS`: 控制测试模式处理的文献数量
- 较小的值可以快速验证功能，较大的值可以更全面地测试

## 配置最佳实践

### 1. 环境分离
- 开发环境：使用较小的限制值，便于调试
- 生产环境：使用较大的限制值，提高效率

### 2. 成本控制
- 根据LLM API的定价调整`DEFAULT_BATCH_SIZE`和`DEFAULT_OUTPUT_TOKENS`
- 监控`MAX_TOKENS_LIMIT`避免超出预算

### 3. 性能优化
- 根据网络状况调整超时设置
- 根据API限制调整速率限制

### 4. 调试友好
- 在开发阶段使用较小的`DEFAULT_TEST_ITEMS`
- 启用`DEBUG=true`获取详细日志

## 配置工具

### 1. 创建配置
```bash
python setup_config.py create
```

### 2. 交互式配置
```bash
python setup_config.py setup
```

### 3. 验证配置
```bash
python setup_config.py validate
```

### 4. 迁移旧配置
```bash
python migrate_config.py
```

## 注意事项

1. **必需配置**: `ZOTERO_USER_ID`和`ZOTERO_API_KEY`是必需的
2. **API密钥安全**: 不要在代码中硬编码API密钥
3. **环境变量优先级**: 环境变量会覆盖`.env`文件中的设置
4. **配置验证**: 使用`setup_config.py validate`验证配置的正确性
5. **备份配置**: 在修改配置前备份`.env`文件 