# Zotero智能文献分类系统

🚀 **基于大语言模型的Zotero文献智能分类工具**

本工具使用先进的大语言模型技术，自动对您的Zotero文献库进行智能分类，具有两阶段层次分类系统和智能容错机制。

[🌐 **English Documentation**](../README.md) | [📖 **详细脚本指南**](./README_scripts.md)

## ✨ 核心特性

- **🎯 两阶段智能分类**：主分类 → 子分类的层次化分类流程
- **🤖 GPT-4.1驱动**：使用最先进的大语言模型确保分类准确性
- **🔑 Collection Key集成**：直接使用Zotero的collection_key，完全防止幻觉
- **🔄 智能容错机制**：当LLM返回分类名称时自动转换为collection_key
- **⚡ 高并发处理**：多进程并行执行（默认16进程）
- **🚀 智能筛选**：自动跳过已有有效分类的文献，提高效率
- **📊 全面预览**：执行前显示详细统计信息
- **📁 结构化数据流**：带时间戳的输出文件，井然有序

## 🛠️ 环境配置

### 必要的环境变量

```bash
# Zotero配置
export ZOTERO_USER_ID='你的Zotero用户ID'
export ZOTERO_API_KEY='你的Zotero API密钥'

# OpenAI配置  
export OPENAI_API_KEY='你的OpenAI API密钥'
export OPENAI_BASE_URL='你的OpenAI Base URL'  # 可选，如使用代理
```

### API密钥获取方式

1. **Zotero API密钥**：访问 [Zotero API Keys](https://www.zotero.org/settings/keys)
2. **OpenAI API密钥**：访问 [OpenAI API](https://platform.openai.com/api-keys)

### 安装依赖

```bash
git clone <仓库地址>
cd zotero-llm-classify
pip install -r requirements.txt  # 安装Python依赖包
```

## 🚀 四步执行流程

按顺序执行以下四个脚本：

### 步骤1：收集文献信息
```bash
python 001_collect_literature_info.py
```

**功能：**
- 从Zotero库中收集文献元数据
- 自动筛选真正的学术论文（conferencePaper, document, journalArticle, preprint）
- 排除附件、笔记等非论文条目
- 输出：`data/literature_info_YYYYMMDD_HHMMSS.xlsx`

### 步骤2：生成分类标准
```bash
python 002_generate_classification_schema.py
```

**功能：**
- 完整获取Zotero中所有分类（支持分页）
- 基于API构建真实的层次结构（主分类-子分类）
- 使用GPT-4.1为每个分类生成描述
- 智能上下文感知（为主分类提供其他主分类信息，为子分类提供同级分类信息）
- 分类黑名单过滤
- 输出：`data/classification_schema_YYYYMMDD_HHMMSS.json`

### 步骤3：执行文献分类
```bash
python 003_classify_literature.py
```

**功能：**
- 两阶段智能分类：先选主分类，再选子分类
- 智能筛选：只处理完全无分类的文献
- 智能容错：当LLM返回分类名称时自动转换为collection_key
- 高并发处理：16进程并行分类
- 严格验证：确保返回的key真实存在
- 输出：`data/classification_results_YYYYMMDD_HHMMSS.xlsx`

### 步骤4：应用分类结果  
```bash
python 004_apply_classification.py
```

**功能：**
- 智能预览：显示将要处理的文献数量和分类操作
- 直接应用：无需重新映射，直接使用collection_keys
- 批量处理：高效的API调用，支持速率限制
- 详细统计：成功/失败统计和错误分析
- 输出：`data/application_results_YYYYMMDD_HHMMSS.xlsx`

## 📊 数据流示意图

```
Zotero文献库 
    ↓
[001] 收集文献信息 → literature_info_*.xlsx
    ↓
[002] 生成分类标准 → classification_schema_*.json
    ↓  
[003] 智能分类 → classification_results_*.xlsx
    ↓
[004] 应用结果 → application_results_*.xlsx
    ↓
更新的Zotero文献库
```

## 🎯 输出文件说明

所有输出文件保存在`data/`目录下，带有时间戳：

| 文件 | 描述 |
|------|------|
| `literature_info_*.xlsx` | 文献元数据，已过滤为真正的学术论文 |
| `classification_schema_*.json` | 分类标准，包含层次结构和LLM生成的描述 |
| `classification_results_*.xlsx` | LLM分类结果，包含推荐的collection_keys |
| `application_results_*.xlsx` | 应用结果统计，包含成功/失败详情 |

## 🔧 高级配置

### 并发控制
```bash
# 自定义进程数
python 003_classify_literature.py 100 0 8  # 处理100篇，8个进程
python 004_apply_classification.py 50 10 4  # 从第10条开始，处理50条，4个进程
```

### 分批处理
```bash  
# 指定处理范围
python 003_classify_literature.py 50 0    # 处理前50篇
python 003_classify_literature.py 50 50   # 处理第51-100篇
```

### API速率限制
```bash
# 设置API调用延迟
python 004_apply_classification.py 100 0 4 0.2  # 延迟0.2秒
```

## 🔍 智能特性详解

### 两阶段分类系统
1. **第一阶段**：LLM从所有主分类中选择最匹配的分类
2. **智能转换**：如果LLM返回分类名称，系统自动转换为collection_key
3. **第二阶段**：对每个选定的主分类，LLM选择对应的子分类
4. **容错处理**：同样支持子分类名称到key的自动转换
5. **结果合并**：如果没有合适的子分类，则使用主分类本身

### 智能筛选机制
- **完全无分类**：0个有效分类 → 进行分类
- **已有分类**：≥1个有效分类 → 跳过分类
- **有效性验证**：只有在最新schema中存在的key才算有效分类

### 容错机制示例
```
LLM返回: "01Theory" → 自动转换为: "I65XEE54"
显示日志: 🔄 自动转换: '01Theory' → 'I65XEE54'
```

## 📚 相关文档

- [📖 详细脚本指南](./README_scripts.md) - 每个脚本的详细文档
- [📁 项目结构说明](./PROJECT_STRUCTURE.md) - 文件结构和数据流说明
- [🛠️ CLI工具](../cli.py) - 交互式Zotero管理界面
- [🌐 English Documentation](../README.md) - English version

## ❓ 常见问题

### Q: 如何获取Zotero用户ID？
A: 访问[Zotero API Keys](https://www.zotero.org/settings/keys)，您的用户ID显示在页面上。

### Q: 支持哪些文献类型？
A: 目前支持：`conferencePaper`、`document`、`journalArticle`、`preprint`。

### Q: 如何自定义分类黑名单？
A: 编辑`002_generate_classification_schema.py`中的`BLACKLIST`变量。

### Q: 分类失败怎么办？
A: 检查`classification_results_*.xlsx`中的错误信息，通常是API配置或网络问题。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 技术支持

如需技术支持，请参考[详细脚本指南](./README_scripts.md)或提交Issue。 