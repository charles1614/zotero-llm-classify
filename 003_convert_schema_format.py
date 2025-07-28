#!/usr/bin/env python3
"""
004 - 分类计划格式转换工具
将LLM生成的分类计划（新格式）转换为Zotero应用脚本所需的格式（旧格式）
"""

import json
import argparse
import os
from datetime import datetime
from typing import Dict, Any, List


def convert_new_to_old_format(new_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    将新格式的schema转换为旧格式
    
    新格式特点：
    - 有metadata字段
    - subcategories是对象格式，键为子分类代码
    - 每个子分类有collection_key
    
    旧格式特点：
    - 有metadata字段，包含hierarchy_analysis
    - subcategories是数组格式
    - 每个子分类有collection_key
    """
    
    # 提取分类schema
    classification_schema = new_schema.get("classification_schema", {})
    main_categories = classification_schema.get("main_categories", {})
    
    # 构建hierarchy_analysis
    hierarchy_analysis = {
        "main_categories": [],
        "sub_categories_mapping": {}
    }
    
    # 转换main_categories
    converted_main_categories = {}
    
    for main_key, main_category in main_categories.items():
        # 添加到main_categories列表
        hierarchy_analysis["main_categories"].append(main_key)
        
        # 转换subcategories从对象格式到数组格式
        subcategories = main_category.get("subcategories", {})
        converted_subcategories = []
        
        for sub_key, sub_category in subcategories.items():
            # 添加到sub_categories_mapping
            hierarchy_analysis["sub_categories_mapping"][sub_key] = main_key
            
            # 转换为数组格式
            converted_subcategories.append({
                "name": sub_category.get("name", ""),
                "description": sub_category.get("description", ""),
                "collection_key": sub_category.get("collection_key", "")
            })
        
        # 构建转换后的main_category
        converted_main_categories[main_key] = {
            "name": main_category.get("name", ""),
            "description": main_category.get("description", ""),
            "collection_key": main_category.get("collection_key", ""),
            "subcategories": converted_subcategories
        }
    
    # 构建转换后的schema
    converted_schema = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_categories": len(hierarchy_analysis["sub_categories_mapping"]) + len(hierarchy_analysis["main_categories"]),
            "main_categories_count": len(hierarchy_analysis["main_categories"]),
            "sub_categories_count": len(hierarchy_analysis["sub_categories_mapping"]),
            "independent_categories_count": 0,
            "hierarchy_analysis": hierarchy_analysis
        },
        "classification_schema": {
            "main_categories": converted_main_categories
        }
    }
    
    return converted_schema


def convert_old_to_new_format(old_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    将旧格式的schema转换为新格式
    
    旧格式特点：
    - 有metadata字段，包含hierarchy_analysis
    - subcategories是数组格式
    - 每个子分类有collection_key
    
    新格式特点：
    - 有metadata字段
    - subcategories是对象格式，键为子分类代码
    - 每个子分类有collection_key
    """
    
    # 提取分类schema
    classification_schema = old_schema.get("classification_schema", {})
    main_categories = classification_schema.get("main_categories", {})
    
    # 转换main_categories
    converted_main_categories = {}
    
    for main_key, main_category in main_categories.items():
        # 转换subcategories从数组格式到对象格式
        subcategories = main_category.get("subcategories", [])
        converted_subcategories = {}
        
        for sub_category in subcategories:
            # 从hierarchy_analysis中找到对应的sub_key
            sub_key = None
            hierarchy_analysis = old_schema.get("metadata", {}).get("hierarchy_analysis", {})
            sub_categories_mapping = hierarchy_analysis.get("sub_categories_mapping", {})
            
            for key, parent in sub_categories_mapping.items():
                if parent == main_key:
                    # 检查这个子分类是否匹配当前项
                    # 这里需要根据name或description来匹配
                    if sub_category.get("name") in key or key in sub_category.get("name", ""):
                        sub_key = key
                        break
            
            # 如果没有找到匹配的key，使用name作为key
            if not sub_key:
                sub_key = sub_category.get("name", "").replace(" ", "_").upper()
            
            converted_subcategories[sub_key] = {
                "name": sub_category.get("name", ""),
                "description": sub_category.get("description", ""),
                "collection_key": sub_category.get("collection_key", "")
            }
        
        # 构建转换后的main_category
        converted_main_categories[main_key] = {
            "name": main_category.get("name", ""),
            "description": main_category.get("description", ""),
            "collection_key": main_category.get("collection_key", ""),
            "subcategories": converted_subcategories
        }
    
    # 构建转换后的schema
    converted_schema = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "status": "converted",
            "source_file": "converted_from_old_format",
            "total_collections_created": len(converted_main_categories)
        },
        "classification_schema": {
            "main_categories": converted_main_categories
        }
    }
    
    return converted_schema


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Schema格式转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 新格式转旧格式，自动生成文件名
  python 004_convert_schema_format.py --new-to-old --input data/schema_with_collection_keys_20250727_183928.json

  # 新格式转旧格式，指定输出文件名
  python 004_convert_schema_format.py --new-to-old --input data/schema_with_collection_keys_20250727_183928.json --output data/converted_old_format.json
  
  # 旧格式转新格式
  python 004_convert_schema_format.py --old-to-new --input data/schema_with_collection_keys_20250726_132555.json --output data/converted_new_format.json
  
  # 检测格式并自动转换
  python 004_convert_schema_format.py --auto --input data/schema.json
        """
    )
    
    # 创建互斥组
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--new-to-old', action='store_true', help='新格式转旧格式')
    mode_group.add_argument('--old-to-new', action='store_true', help='旧格式转新格式')
    mode_group.add_argument('--auto', action='store_true', help='自动检测格式并转换')
    
    # 文件路径参数
    parser.add_argument('--input', type=str, required=True, help='输入schema文件路径')
    parser.add_argument('--output', type=str, help='输出schema文件路径 (可选, 默认自动生成)')
    
    args = parser.parse_args()
    
    # 验证输入文件存在
    if not os.path.exists(args.input):
        parser.error(f"输入文件不存在: {args.input}")
    
    # 读取输入文件
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_schema = json.load(f)
    except Exception as e:
        parser.error(f"读取输入文件失败: {e}")
    
    # 确定转换方向
    converted_schema = None
    
    if args.auto:
        # 自动检测格式
        if "classification_schema" in input_schema:
            classification_schema = input_schema["classification_schema"]
            main_categories = classification_schema.get("main_categories", {})
            
            if main_categories:
                # 检查第一个main_category的subcategories格式
                first_main = list(main_categories.values())[0]
                subcategories = first_main.get("subcategories", {})
                
                if isinstance(subcategories, dict):
                    # 新格式：subcategories是对象
                    print("🔍 检测到新格式，转换为旧格式...")
                    converted_schema = convert_new_to_old_format(input_schema)
                elif isinstance(subcategories, list):
                    # 旧格式：subcategories是数组
                    print("🔍 检测到旧格式，转换为新格式...")
                    converted_schema = convert_old_to_new_format(input_schema)
                else:
                    parser.error("无法识别的schema格式")
            else:
                parser.error("无法识别的schema格式")
        else:
            parser.error("无法识别的schema格式")
    elif args.new_to_old:
        print("🔄 新格式转旧格式...")
        converted_schema = convert_new_to_old_format(input_schema)
    elif args.old_to_new:
        print("🔄 旧格式转新格式...")
        converted_schema = convert_old_to_new_format(input_schema)
    
    # 保存输出文件
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/converted_schema_{timestamp}.json"

    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_schema, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 转换完成！结果已保存到: {output_file}")
        
        # 显示统计信息
        if "classification_schema" in converted_schema:
            main_categories = converted_schema["classification_schema"].get("main_categories", {})
            total_subcategories = sum(len(main.get("subcategories", [])) for main in main_categories.values())
            
            print(f"📊 转换统计:")
            print(f"  - 主分类数量: {len(main_categories)}")
            print(f"  - 子分类数量: {total_subcategories}")
            print(f"  - 总分类数量: {len(main_categories) + total_subcategories}")

        print(f"💡 下一步操作:")
        print(f"  1. 检查转换后的schema文件: {output_file}")
        print(f"  2. 使用转换后的schema进行分类:")
        print(f"     python 004_reclassify_with_new_schema.py --plan --schema {output_file} --input <your_literature_file.xlsx>")
        
    except Exception as e:
        parser.error(f"保存输出文件失败: {e}")


if __name__ == "__main__":
    main() 