# Zotero LLM Classify

An intelligent literature classification system for Zotero using Large Language Models. This project is an enhancement of the original work, focusing on a more robust and modular architecture.

## Key Enhancements

*   **Modern Configuration**: Replaced shell scripts with a `pydantic-settings` based configuration system, using `.env` files for easier management.
*   **Modular Architecture**: Refactored the original scripts into a more modular and maintainable structure, with each script having a clear purpose.
*   **Flexible LLM Client**: The LLM client now supports multiple LLM APIs and includes a rate limiter.
*   **Improved Workflow**: The project now follows a clear and logical workflow, from data collection to classification and application.

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd zotero-llm-classify

# Install dependencies
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Create a .env file from the example
cp env.example .env

# Edit the .env file with your credentials
nano .env
```

### 3. Usage

The project follows a clear, step-by-step workflow. Run the scripts in the following order:

1.  **`001_collect_literature_info.py`**: Collects literature information from Zotero.
2.  **`002_generate_schema_and_create_collections.py`**: Generates a classification schema and creates collections in Zotero.
3.  **`003_convert_schema_format.py`**: Converts the schema to the format required by the classification script.
4.  **`004_reclassify_with_new_schema.py`**: Reclassifies your literature using the new schema.
5.  **`005_apply_classification_to_zotero.py`**: Applies the new classifications to your Zotero library.
6.  **`006_check_and_export_missing_proper_items.py`**: Checks for and exports any items that were missed during the classification process.

For detailed usage of each script, please refer to the help message of each script (e.g., `python 001_collect_literature_info.py --help`).

## Acknowledgements

This project is an enhancement of the original Zotero LLM Classify project. We are grateful to the original author for their foundational work.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.