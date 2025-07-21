# Zotero文献自动分类工具集

这是一个分步骤的Zotero文献自动分类工具集，将原来的大脚本拆分成4个独立的小脚本，便于分步执行和调试。

## 🎯 功能概述

- **001_collect_literature_info.py**: 收集文献信息
- **002_generate_classification_schema.py**: 生成分类标准
- **003_classify_literature.py**: 执行文献分类（支持多进程）
- **004_apply_classification.py**: 批量应用分类（支持多进程）

## 📋 环境要求

### Python依赖
```bash
pip install pandas openpyxl tqdm
```

### 环境变量
需要设置以下环境变量：

```bash
# Zotero API配置
export ZOTERO_USER_ID='你的Zotero用户ID'
export ZOTERO_API_KEY='你的Zotero API密钥'

# OpenAI API配置（用于002和003脚本）
export OPENAI_API_KEY='你的OpenAI API密钥'
export OPENAI_BASE_URL='你的OpenAI Base URL'  # 可选，默认为官方API
```

## 🚀 使用流程

### 步骤1：收集文献信息
```bash
python 001_collect_literature_info.py
```

**功能说明：**
- 从Zotero获取所有文献的详细信息
- 包括标题、作者、摘要、发表信息、DOI等
- 保存到`data/literature_info_YYYYMMDD_HHMMSS.xlsx`

**输出示例：**
```
📚 Zotero文献信息收集工具 - 001
✅ 总共获取到 1250 篇文献
📊 文献统计信息:
   总文献数: 1250
   文献类型分布:
     - journalArticle: 800 篇
     - conferencePaper: 300 篇
     - preprint: 100 篇
   有摘要的文献: 950 篇
   有DOI的文献: 900 篇
```

### 步骤2：生成分类标准
```bash
python 002_generate_classification_schema.py
```

**功能说明：**
- **📂 完整获取分类**：支持分页，获取所有Zotero分类（无数量限制）
- **🌳 真实层级结构**：基于API的parentCollection字段构建准确的父子关系
- **🤖 智能描述生成**：使用LLM为每个分类生成详细描述
- 保存到`data/classification_schema_YYYYMMDD_HHMMSS.json`

**重要改进：**
- ✅ **分页获取**：不再受限于单次API调用的数量限制
- ✅ **真实层级**：基于Zotero API的实际父子关系，而非名称猜测
- ✅ **智能过滤**：内置分类黑名单，自动过滤不需要的分类（如"readpaper"）
- ✅ **结构调试**：显示详细的分类结构信息便于验证
- ✅ **智能模型**：使用GPT-4.1模型提供更高质量的描述生成
- ✅ **上下文感知**：为分类描述提供完整的上下文信息
  - 主分类：了解所有其他主分类，确保区分度
  - 子分类：了解同级其他子分类，确保精确性
- ✅ **子分类约束**：子分类描述包含对主分类的依赖要求

**输出示例：**
```
🏗️ Zotero分类标准生成工具 - 002
📂 正在获取所有分类...
   已获取 25 个分类...
   已获取 47 个分类...
✅ 已加载 45 个现有分类
🚫 已过滤 2 个黑名单分类
   黑名单: readpaper

🔍 分类结构调试信息:
   顶级分类: 8 个
   子分类: 37 个

📋 分类结构示例:
   - Machine Learning (顶级)
   - Deep Learning → Machine Learning
   - NLP Fundamentals → Machine Learning
   - Computer Vision (顶级)

🔍 分析分类层级结构...
✅ 顶级分类: Machine Learning
✅ 顶级分类: Computer Vision
📋 子分类: Deep Learning → Machine Learning
📋 子分类: NLP Fundamentals → Machine Learning

📊 层级分析结果:
   顶级分类: 8 个
   子分类: 37 个
   独立/嵌套分类: 0 个

🤖 正在生成分类描述...
📝 生成主分类描述: Machine Learning
✅ 机器学习领域的理论、方法和技术相关的学术文献，包括算法开发、模型设计等核心研究。
```

### 步骤3：执行文献分类
```bash
# 基本用法（分类所有文献）
python 003_classify_literature.py

# 指定数量和起始位置
python 003_classify_literature.py [limit] [start] [max_workers]

# 示例：分类100篇文献，从第50篇开始，使用8个进程
python 003_classify_literature.py 100 50 8
```

**重大改进 - 两阶段智能分类：**
- 🎯 **两阶段流程**：先选择主分类，再选择子分类
- 🤖 **GPT-4.1模型**：使用更先进的模型提供更准确的分类
- 🔑 **Collection Key**：直接使用Zotero的collection_key，防止幻觉
- ✅ **严格验证**：确保LLM返回的分类key真实存在于schema中  
- 🔄 **智能Fallback**：当LLM返回分类名称时自动转换为collection_key
- ⚡ **高并发**：默认16个进程并发处理，显著提升效率
- 🚀 **智能筛选**：自动跳过已有1个或以上有效分类的文献

**分类流程：**
1. **第一阶段**：LLM分析文献内容，从所有主分类中选择合适的分类
2. **智能转换**：如果LLM返回分类名称，系统自动转换为collection_key
3. **第二阶段**：对每个选定的主分类，LLM选择对应的子分类
4. **Fallback处理**：同样支持子分类名称到key的自动转换
5. **结果合并**：如果没有合适的子分类，则使用主分类本身

**多进程特性：**
- 默认使用 min(CPU核心数, 16) 个进程
- 支持自定义进程数
- tqdm进度条显示两阶段分类进度

**智能Fallback机制：**
系统会自动处理LLM返回分类名称而非collection_key的情况：
- 自动建立分类名称到collection_key的映射表
- 当检测到无效key时，尝试按名称查找对应的key
- 支持主分类和子分类的自动转换
- 显示转换日志：`🔄 自动转换: '01Theory' → 'ABC123'`

**输出示例：**
```
🤖 Zotero文献智能分类工具 - 003
🔧 将使用 16 个进程进行并发分类
📁 加载文献信息: data/literature_info_20241201_143022.xlsx
✅ 已加载 365 篇文献信息（已过滤非paper类型）
📁 加载分类标准: data/classification_schema_20241201_143155.json
✅ 已加载分类标准: 8 个主分类, 37 个独立分类
🔍 筛选需要分类的文献...
✅ 已加载 45 个有效分类key
📊 分析现有分类情况...
   无有效分类: 180 篇
   1个有效分类: 120 篇
   2个或以上有效分类: 65 篇

📊 筛选结果:
   总文献数: 365
   待分类文献数: 180 篇
   已跳过（有效分类>=1）: 185 篇
   🔄 自动转换: '05LongContext' → 'SM7DUXE4'
   🔄 自动转换: '04Benchmark' → 'FHM95M9I'
两阶段分类进度: 100%|██████████| 180/180 [02:15<00:00, 1.33篇/s]

📊 两阶段分类结果统计:
   ✅ 成功分类: 175 篇
   ❌ 分类失败: 5 篇
   📂 平均推荐分类数: 2.3
   🔄 平均子分类响应数: 1.8
   🔑 使用的分类key总数: 25

📂 热门推荐分类:
     - Machine Learning: 45 篇
     - Deep Learning: 38 篇
     - Natural Language Processing: 32 篇
```

### 步骤4：批量应用分类
```bash
# 基本用法（应用所有分类结果）
python 004_apply_classification.py

# 指定参数
python 004_apply_classification.py [limit] [start] [max_workers] [rate_limit_delay]

# 示例：应用50条结果，从第10条开始，使用2个进程，延迟0.2秒
python 004_apply_classification.py 50 10 2 0.2
```

**功能说明：**
- 读取步骤3的分类结果（包含collection_keys）
- **直接应用**：无需重新映射，直接使用collection_keys应用分类
- **智能预览**：执行前显示详细的应用统计预览
- 使用多进程并发调用Zotero API应用分类
- 包含API速率限制保护
- 保存到`data/application_results_YYYYMMDD_HHMMSS.xlsx`

**预览功能：**
- 📊 显示总共多少篇文献需要分类
- 🏷️ 统计总共多少个分类操作
- 🔑 展示即将应用的collection_keys分布
- 📍 明确显示处理范围

**安全特性：**
- 执行前需要用户确认
- 支持自定义API调用延迟
- 详细的错误日志和统计信息

**输出示例：**
```
🔗 Zotero分类应用工具 - 004
🔧 将使用 4 个进程进行并发应用
⏱️ API速率限制延迟: 0.1秒
已连接到用户 xxxxx 的Zotero库

🔍 正在分析分类结果...
📁 加载分类结果: data/classification_results_20250721_095703.xlsx
✅ 已加载 5 条分类结果
🔍 筛选需要应用的分类结果...
📊 筛选结果:
   总结果数: 5
   成功分类数: 5
   有推荐分类keys数: 5

📊 即将执行的分类应用预览:
   📁 总分类结果: 5 条
   ✅ 可应用结果: 5 条
   🎯 本次处理: 5 篇文献
   🏷️ 总分类操作: 9 个
   📍 处理范围: 第 1 到第 5 条

🔑 即将应用的分类keys（Top 10）:
     - I65XEE54: 3 篇
     - GVC5JRGU: 1 篇
     - 5LWWS9NA: 1 篇

⚠️ 确认要开始应用分类到Zotero吗？(y/N): y
应用进度: 100%|██████████| 5/5 [00:15<00:00, 0.32条/s]
📊 应用结果统计:
   ✅ 成功应用: 5 篇
   ❌ 应用失败: 0 篇
   📂 总共应用分类: 9 个
```

## 📁 数据文件结构

所有数据文件保存在`data/`目录下，带有时间戳：

```
data/
├── literature_info_20241201_143022.xlsx         # 文献信息
├── classification_schema_20241201_143155.json   # 分类标准
├── classification_results_20241201_144530.xlsx  # 分类结果
└── application_results_20241201_145210.xlsx     # 应用结果
```

## ⚙️ 高级配置

### 并发配置
- **003脚本**：默认使用 min(CPU核心数, 8) 个进程进行LLM调用
- **004脚本**：默认使用 min(CPU核心数//2, 4) 个进程进行API调用

### API限制配置
- **LLM调用**：无特殊限制，依赖服务商配置
- **Zotero API**：默认0.1秒延迟，可根据需要调整

### 自定义参数
```bash
# 003脚本参数
python 003_classify_literature.py [limit] [start] [max_workers]

# 004脚本参数  
python 004_apply_classification.py [limit] [start] [max_workers] [rate_limit_delay]
```

### 分类黑名单配置
在`002_generate_classification_schema.py`中可以修改黑名单：

```python
# 分类黑名单：硬编码的不需要处理的分类名称
BLACKLIST = ["readpaper", "other_unwanted_category"]
```

**黑名单功能：**
- 自动过滤指定名称的分类
- 同时过滤这些分类的所有子分类
- 不生成描述，不存储到最终结果中
- 在输出中显示过滤统计信息

## 🔧 故障排除

### 常见问题

1. **环境变量未设置**
   ```bash
   ❌ 缺少环境变量: ZOTERO_USER_ID, ZOTERO_API_KEY
   ```
   解决：设置所需的环境变量

2. **找不到前置文件**
   ```bash
   ❌ 未找到文献信息文件，请先运行 001_collect_literature_info.py
   ```
   解决：按顺序执行脚本

3. **API调用失败**
   ```bash
   ❌ 应用失败: collection_name(API失败)
   ```
   解决：检查网络连接和API密钥，适当增加延迟时间

### 性能优化

1. **调整进程数**：根据机器性能和API限制调整
2. **增加延迟**：如果遇到API限制错误，增加`rate_limit_delay`
3. **分批处理**：大量文献可以分批处理，使用limit和start参数

## 📊 输出文件说明

### 文献信息文件 (literature_info_*.xlsx)
- `item_key`: Zotero文献唯一标识
- `title`: 文献标题
- `authors`: 作者列表
- `abstract`: 摘要
- `publication_title`: 期刊名称
- `date`: 发表日期
- `doi`: DOI标识
- 等详细字段...

### 分类标准文件 (classification_schema_*.json)
```json
{
  "metadata": {
    "generated_at": "2024-12-01T14:31:55",
    "total_categories": 25,
    "main_categories_count": 15
  },
  "classification_schema": {
    "main_categories": {
      "01Theory": {
        "name": "01Theory",
        "description": "理论基础相关文献...",
        "subcategories": [...]
      }
    }
  }
}
```

### 分类结果文件 (classification_results_*.xlsx)
- `item_key`: 文献标识
- `title`: 文献标题
- `classification_success`: 分类是否成功
- `recommended_collections`: 推荐分类列表
- `analysis`: LLM分析说明
- `error_message`: 错误信息（如有）

### 应用结果文件 (application_results_*.xlsx)
- `item_key`: 文献标识
- `application_success`: 应用是否成功
- `applied_collections`: 成功应用的分类
- `failed_collections`: 失败的分类
- `error_message`: 错误信息

## 🎨 自定义和扩展

### 修改分类标准
1. 运行002脚本生成初始分类标准
2. 手动编辑JSON文件中的`description`字段
3. 调整分类层级结构
4. 运行003脚本使用修改后的标准

### 调整分类逻辑
在`003_classify_literature.py`的`build_classification_prompt`函数中：
- 修改提示词模板
- 调整分类原则
- 添加特殊规则

### 批量处理策略
```bash
# 分批处理大量文献
python 003_classify_literature.py 100 0    # 处理前100篇
python 003_classify_literature.py 100 100  # 处理第101-200篇
python 003_classify_literature.py 100 200  # 处理第201-300篇
```

## 📞 支持

如有问题，请检查：
1. 环境变量设置
2. 网络连接
3. API密钥有效性
4. 文件权限
5. 磁盘空间

使用`--help`或查看脚本源码获取更多详细信息。 