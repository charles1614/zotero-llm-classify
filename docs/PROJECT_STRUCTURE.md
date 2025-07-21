# 项目结构说明

## 📁 目录结构

```
zotero-llm-classify/
├── 001_collect_literature_info.py      # 步骤1：收集文献信息
├── 002_generate_classification_schema.py # 步骤2：生成分类标准
├── 003_classify_literature.py          # 步骤3：执行文献分类
├── 004_apply_classification.py         # 步骤4：应用分类结果
├── README.md                           # 英文版项目说明
├── cli.py                              # 交互式Zotero管理工具
├── llm_client.py                       # LLM客户端模块
├── requirements.txt                    # Python依赖包列表
├── .gitignore                         # Git忽略文件
├── config/                            # 配置文件目录
│   ├── config_example.txt             # 配置示例
│   └── run.sh                         # 运行脚本
├── docs/                              # 文档目录
│   ├── README.md                      # 中文版详细说明
│   ├── README_scripts.md              # 脚本详细指南
│   └── PROJECT_STRUCTURE.md           # 项目结构说明
├── scripts/                           # 工具脚本目录
│   ├── analyze_all_items.py           # 文献分析工具
│   ├── analyze_content.py             # 内容分析工具
│   ├── analyze_hierarchy.py           # 层次分析工具
│   ├── analyze_library.py             # 库分析工具
│   └── main_simple.py                 # 简化版主程序
├── tests/                             # 测试文件目录
│   ├── test_auto_classify.py          # 自动分类测试
│   └── test_pdf_info.py               # PDF信息测试
└── data/                              # 数据输出目录（git忽略）
    ├── literature_info_*.xlsx         # 文献信息文件
    ├── classification_schema_*.json   # 分类标准文件
    ├── classification_results_*.xlsx  # 分类结果文件
    └── application_results_*.xlsx     # 应用结果文件
```

## 🚀 核心文件

### 主要处理脚本
- **001-004**：四步处理流程的主要脚本
- **cli.py**：交互式Zotero管理界面
- **llm_client.py**：LLM API客户端封装

### 文档文件
- **README.md**：英文版项目介绍
- **docs/README.md**：中文版详细说明
- **docs/README_scripts.md**：每个脚本的详细使用指南

### 配置和工具
- **config/**：配置文件和运行脚本
- **scripts/**：辅助工具和分析脚本
- **tests/**：测试文件

## 🔄 数据流

```
Zotero API → 001 → data/literature_info_*.xlsx
                ↓
             002 → data/classification_schema_*.json
                ↓
             003 → data/classification_results_*.xlsx
                ↓
             004 → data/application_results_*.xlsx → Zotero API
```

## 📋 使用顺序

1. 设置环境变量（Zotero + OpenAI API）
2. 按顺序执行 001 → 002 → 003 → 004
3. 检查 `data/` 目录下的输出文件
4. 可选：使用 `cli.py` 进行交互式管理 