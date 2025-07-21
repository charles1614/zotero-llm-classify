# Zotero LLM Classify

🚀 **An intelligent literature classification system for Zotero using Large Language Models**

This tool automatically classifies your Zotero literature collection using advanced LLM technology, featuring a two-stage hierarchical classification system with smart fallback mechanisms.

## ✨ Features

- **🎯 Two-Stage Classification**: Main category → Sub-category intelligent classification
- **🤖 GPT-4.1 Powered**: Uses advanced LLM for accurate classification decisions  
- **🔑 Collection Key Integration**: Direct Zotero collection_key usage prevents hallucinations
- **🔄 Smart Fallback**: Automatic name-to-key conversion when needed
- **⚡ High Concurrency**: Multi-process parallel execution (default 16 processes)
- **🚀 Intelligent Filtering**: Auto-skip literature that already has valid classifications
- **📊 Comprehensive Preview**: Detailed statistics before execution
- **📁 Structured Data Flow**: Timestamped output files in organized directory structure

## 🛠️ Quick Start

### Prerequisites

```bash
# Set environment variables
export ZOTERO_USER_ID='your_zotero_user_id'
export ZOTERO_API_KEY='your_zotero_api_key'
export OPENAI_API_KEY='your_openai_api_key'
export OPENAI_BASE_URL='your_openai_base_url'  # Optional
```

### Installation

```bash
git clone <repository-url>
cd zotero-llm-classify
pip install -r requirements.txt  # Install dependencies
```

### Usage - 4 Steps Pipeline

Execute the following scripts in sequence:

#### Step 1: Collect Literature Information
```bash
python 001_collect_literature_info.py
```
Collects literature metadata from Zotero and filters for true academic papers.

#### Step 2: Generate Classification Schema  
```bash
python 002_generate_classification_schema.py
```
Generates hierarchical classification schema with LLM-generated descriptions.

#### Step 3: Classify Literature
```bash
python 003_classify_literature.py
```
Performs two-stage intelligent classification using LLM with fallback mechanisms.

#### Step 4: Apply Classifications
```bash
python 004_apply_classification.py
```
Batch applies the classification results to your Zotero library.

## 📚 Documentation

- **[中文文档 / Chinese Documentation](./docs/README.md)** - 完整的中文使用指南
- **[Detailed Scripts Guide](./docs/README_scripts.md)** - Comprehensive documentation for each script
- **[Project Structure](./docs/PROJECT_STRUCTURE.md)** - File structure and data flow explanation
- **[CLI Tool](./cli.py)** - Interactive Zotero management interface

## 📊 Data Flow

```
Zotero Library → 001 → literature_info_*.xlsx
                 ↓
            002 → classification_schema_*.json  
                 ↓
            003 → classification_results_*.xlsx
                 ↓
            004 → application_results_*.xlsx → Zotero Library
```

## 🎯 Output Files

All output files are saved in the `data/` directory with timestamps:

- `literature_info_YYYYMMDD_HHMMSS.xlsx` - Literature metadata
- `classification_schema_YYYYMMDD_HHMMSS.json` - Classification schema with descriptions
- `classification_results_YYYYMMDD_HHMMSS.xlsx` - LLM classification results
- `application_results_YYYYMMDD_HHMMSS.xlsx` - Application results and statistics

## 🔧 Advanced Configuration

- **Concurrency**: Customize process count for classification and application
- **Batch Processing**: Process specific ranges of literature
- **Rate Limiting**: Configure API call delays for Zotero API
- **Smart Filtering**: Automatically skip already-classified literature

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For detailed usage instructions and troubleshooting, please refer to the [Chinese Documentation](./docs/README.md) or [Scripts Guide](./docs/README_scripts.md). 