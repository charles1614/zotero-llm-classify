#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
002 - Generate Classification Schema
生成分类标准，包含层级结构和LLM生成的描述
"""

import os
import sys
import json
import re
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm

# 导入已有的模块
from main import ZoteroManager
from llm_client import LLMClient

class ClassificationSchemaGenerator:
    """分类标准生成器"""
    
    # 分类黑名单：硬编码的不需要处理的分类名称
    BLACKLIST = ["readpaper"]
    
    def __init__(self, user_id: str = None, api_key: str = None):
        """初始化生成器"""
        self.zotero = ZoteroManager(user_id, api_key)
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 初始化LLM客户端
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if not openai_api_key:
            print("错误：请设置OPENAI_API_KEY环境变量")
            sys.exit(1)
            
        self.llm = LLMClient(
            model_name="gpt-4.1",
            api_key=openai_api_key,
            base_url=openai_base_url
        )
        
        # 获取现有分类
        self.existing_collections = {}
        self._load_existing_collections()
    
    def _load_existing_collections(self):
        """加载现有分类（支持分页）"""
        all_collections = []
        start = 0
        limit = 100
        
        print("📂 正在获取所有分类...")
        
        while True:
            try:
                # 使用分页获取所有分类
                url = f"{self.zotero.base_url}/users/{self.zotero.user_id}/collections"
                params = {
                    'limit': limit,
                    'start': start,
                    'format': 'json'
                }
                
                response = requests.get(url, headers=self.zotero.headers, params=params)
                response.raise_for_status()
                
                collections = response.json()
                if not collections:
                    break
                    
                all_collections.extend(collections)
                start += limit
                print(f"   已获取 {len(all_collections)} 个分类...")
                
            except Exception as e:
                print(f"获取分类失败: {e}")
                break
        
        # 构建分类映射（应用黑名单过滤）
        blacklisted_keys = set()  # 记录被黑名单过滤的分类key
        
        # 第一遍：找出直接在黑名单中的分类
        for collection in all_collections:
            collection_name = collection['data']['name']
            if collection_name in self.BLACKLIST:
                blacklisted_keys.add(collection['key'])
        
        # 第二遍：找出父分类在黑名单中的子分类
        for collection in all_collections:
            parent_key = collection['data'].get('parentCollection', '')
            if parent_key and parent_key in blacklisted_keys:
                blacklisted_keys.add(collection['key'])
        
        # 第三遍：构建最终的分类映射（排除黑名单）
        filtered_count = 0
        for collection in all_collections:
            collection_key = collection['key']
            collection_name = collection['data']['name']
            parent_key = collection['data'].get('parentCollection', '')
            
            if collection_key not in blacklisted_keys:
                self.existing_collections[collection_key] = {
                    'name': collection_name,
                    'parent': parent_key,
                    'key': collection_key
                }
            else:
                filtered_count += 1
        
        print(f"✅ 已加载 {len(self.existing_collections)} 个现有分类")
        if filtered_count > 0:
            print(f"🚫 已过滤 {filtered_count} 个黑名单分类")
            print(f"   黑名单: {', '.join(self.BLACKLIST)}")
        
        # 显示分类结构信息用于调试
        print(f"\n🔍 分类结构调试信息:")
        top_level_count = sum(1 for info in self.existing_collections.values() if not info['parent'])
        child_count = sum(1 for info in self.existing_collections.values() if info['parent'])
        print(f"   顶级分类: {top_level_count} 个")
        print(f"   子分类: {child_count} 个")
        
        # 显示前5个分类的结构
        print(f"\n📋 分类结构示例:")
        shown = 0
        for key, info in self.existing_collections.items():
            if shown >= 5:
                break
            parent_info = f" (父分类: {info['parent']})" if info['parent'] else " (顶级)"
            print(f"   - {info['name']}{parent_info}")
            shown += 1
    
    def _analyze_hierarchy(self) -> Dict[str, Any]:
        """分析分类层级结构（基于API的父子关系）"""
        main_categories = {}
        sub_categories = {}
        independent_categories = {}
        
        print("🔍 分析分类层级结构...")
        
        # 首先找出所有顶级分类（没有父分类的）
        for key, collection_info in self.existing_collections.items():
            name = collection_info['name']
            parent_key = collection_info['parent']
            
            if not parent_key:  # 顶级分类
                main_categories[name] = {
                    'name': name,
                    'subcategories': [],
                    'description': '',
                    'collection_key': key
                }
                print(f"✅ 顶级分类: {name}")
        
        # 然后处理子分类
        for key, collection_info in self.existing_collections.items():
            name = collection_info['name']
            parent_key = collection_info['parent']
            
            if parent_key:  # 有父分类
                # 找到父分类名称
                parent_name = None
                for parent_collection_info in self.existing_collections.values():
                    if parent_collection_info['key'] == parent_key:
                        parent_name = parent_collection_info['name']
                        break
                
                if parent_name and parent_name in main_categories:
                    # 添加为子分类
                    main_categories[parent_name]['subcategories'].append({
                        'name': name,
                        'description': '',
                        'collection_key': key
                    })
                    sub_categories[name] = parent_name
                    print(f"📋 子分类: {name} → {parent_name}")
                else:
                    # 父分类不在顶级分类中，可能是多级嵌套，暂时作为独立分类处理
                    independent_categories[name] = {
                        'name': name,
                        'description': '',
                        'collection_key': key,
                        'parent_key': parent_key
                    }
                    print(f"🔖 嵌套分类: {name} (父分类key: {parent_key})")
        
        # 如果没有找到任何顶级分类，把独立分类都当作主分类
        if not main_categories and independent_categories:
            print("⚠️  没有发现明确的层级结构，将所有分类视为独立分类")
        
        print(f"📊 层级分析结果:")
        print(f"   顶级分类: {len(main_categories)} 个")
        print(f"   子分类: {len(sub_categories)} 个") 
        print(f"   独立/嵌套分类: {len(independent_categories)} 个")
        
        return {
            'main_categories': main_categories,
            'sub_categories': sub_categories,
            'independent_categories': independent_categories
        }
    
    def _get_collection_key_by_name(self, name: str) -> str:
        """根据名称获取collection key"""
        for key, collection_info in self.existing_collections.items():
            if collection_info['name'] == name:
                return key
        return ''
    
    def _generate_description_prompt(self, category_name: str, category_type: str, parent_name: str = None, context_info: Dict[str, Any] = None) -> str:
        """生成描述提示词（包含上下文信息）"""
        context_info = context_info or {}
        
        if category_type == 'main':
            # 构建其他主分类的上下文信息
            other_main_categories = context_info.get('other_main_categories', [])
            other_categories_text = ""
            if other_main_categories:
                other_categories_text = f"""

**整个分类体系中的其他主分类：**
{chr(10).join([f"- {cat}" for cat in other_main_categories])}

注意：你需要生成的描述应该与这些其他主分类有明确的区分度，避免重叠。"""

            prompt = f"""请为以下学术文献分类生成一个准确、简洁的描述说明。

**待描述分类：**
分类名称：{category_name}
分类类型：主分类{other_categories_text}

**要求：**
1. 描述应该明确说明这个分类主要收录什么类型的文献
2. 描述长度控制在2-3句话，100字以内
3. 描述应该具体且有区分度，与其他主分类明确区别，避免过于宽泛
4. 使用学术性语言，保持专业性
5. 如果分类名称包含数字编号，请忽略编号部分，只描述实际内容
6. 考虑整个分类体系的结构，确保描述的独特性

请直接返回描述文本，不需要其他格式。"""

        else:  # 子分类
            # 构建同级子分类的上下文信息
            sibling_subcategories = context_info.get('sibling_subcategories', [])
            siblings_text = ""
            if sibling_subcategories:
                siblings_text = f"""

**同属于{parent_name}的其他子分类：**
{chr(10).join([f"- {cat}" for cat in sibling_subcategories])}

注意：你需要生成的描述应该与这些同级子分类有明确的区分度，体现各自的特定性。"""

            prompt = f"""请为以下学术文献分类生成一个准确、简洁的描述说明。

**待描述分类：**
分类名称：{category_name}
分类类型：子分类
所属主分类：{parent_name}{siblings_text}

**要求：**
1. 描述必须以"首先要属于{parent_name}分类"开头
2. 然后明确说明这个子分类在主分类中的具体范围和特点
3. 描述长度控制在2-3句话，120字以内
4. 描述应该具体且有区分度，与同级其他子分类明确区分
5. 使用学术性语言，保持专业性
6. 强调这个子分类的特定性，避免与主分类或其他子分类重叠
7. 考虑同级子分类的划分方式，确保描述的精确性

示例格式：
"首先要属于{parent_name}分类。[具体说明这个子分类的特定范围和要求]"

请直接返回描述文本，不需要其他格式。"""

        return prompt
    
    def _generate_description(self, category_name: str, category_type: str, parent_name: str = None, context_info: Dict[str, Any] = None) -> str:
        """使用LLM生成分类描述（包含上下文信息）"""
        prompt = self._generate_description_prompt(category_name, category_type, parent_name, context_info)
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=250  # 增加token数量以适应更复杂的prompt
            )
            
            description = response.get('content', '').strip()
            return description
            
        except Exception as e:
            print(f"生成描述失败 {category_name}: {e}")
            if category_type == 'main':
                return f"主分类：{category_name}相关的学术文献"
            else:
                return f"首先要属于{parent_name}分类。{category_name}相关的专门文献。"
    
    def generate_schema(self) -> Dict[str, Any]:
        """生成完整的分类标准"""
        print("🏗️ 开始生成分类标准...")
        
        # 分析层级结构
        hierarchy = self._analyze_hierarchy()
        
        # 为每个分类生成描述
        print("\n🤖 正在生成分类描述...")
        
        # 处理主分类
        main_categories = hierarchy['main_categories']
        all_main_category_names = list(main_categories.keys())
        
        for main_cat_name, main_cat_info in tqdm(main_categories.items(), desc="主分类描述", unit="个"):
            print(f"\n📝 生成主分类描述: {main_cat_name}")
            
            # 构建主分类的上下文信息（其他主分类）
            other_main_categories = [name for name in all_main_category_names if name != main_cat_name]
            main_context = {
                'other_main_categories': other_main_categories
            }
            
            description = self._generate_description(main_cat_name, 'main', context_info=main_context)
            main_cat_info['description'] = description
            print(f"✅ {description}")
            
            # 处理子分类
            subcategories = main_cat_info['subcategories']
            for sub_cat_info in subcategories:
                sub_cat_name = sub_cat_info['name']
                print(f"\n📝 生成子分类描述: {sub_cat_name}")
                
                # 构建子分类的上下文信息（同级其他子分类）
                sibling_subcategories = [sub['name'] for sub in subcategories if sub['name'] != sub_cat_name]
                sub_context = {
                    'sibling_subcategories': sibling_subcategories
                }
                
                sub_description = self._generate_description(sub_cat_name, 'sub', main_cat_name, sub_context)
                sub_cat_info['description'] = sub_description
                print(f"✅ {sub_description}")
        
        # 处理独立分类
        independent_categories = hierarchy['independent_categories']
        all_independent_names = list(independent_categories.keys())
        
        for indep_cat_name, indep_cat_info in tqdm(independent_categories.items(), desc="独立分类描述", unit="个"):
            print(f"\n📝 生成独立分类描述: {indep_cat_name}")
            
            # 构建独立分类的上下文信息（其他独立分类 + 主分类）
            other_independent_categories = [name for name in all_independent_names if name != indep_cat_name]
            all_other_categories = other_independent_categories + all_main_category_names
            indep_context = {
                'other_main_categories': all_other_categories
            }
            
            description = self._generate_description(indep_cat_name, 'main', context_info=indep_context)
            indep_cat_info['description'] = description
            print(f"✅ {description}")
        
        # 构建最终的schema
        schema = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_categories': len(self.existing_collections),
                'main_categories_count': len(main_categories),
                'sub_categories_count': len(hierarchy['sub_categories']),
                'independent_categories_count': len(independent_categories),
                'hierarchy_analysis': {
                    'main_categories': list(main_categories.keys()),
                    'sub_categories_mapping': hierarchy['sub_categories']
                }
            },
            'classification_schema': {
                'main_categories': main_categories,
                'independent_categories': independent_categories
            }
        }
        
        return schema
    
    def save_schema(self, schema: Dict[str, Any]) -> str:
        """保存分类标准到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"classification_schema_{timestamp}.json"
        filepath = self.data_dir / filename
        
        print(f"💾 正在保存分类标准到 {filepath}...")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def generate_and_save(self) -> str:
        """生成并保存分类标准"""
        print("🚀 开始生成分类标准...")
        
        # 生成分类标准
        schema = self.generate_schema()
        
        # 保存到文件
        result_file = self.save_schema(schema)
        
        # 显示统计信息
        metadata = schema['metadata']
        main_cats = schema['classification_schema']['main_categories']
        indep_cats = schema['classification_schema']['independent_categories']
        
        print(f"\n📊 分类标准统计:")
        print(f"   总分类数: {metadata['total_categories']}")
        print(f"   主分类数: {metadata['main_categories_count']}")
        print(f"   子分类数: {metadata['sub_categories_count']}")
        print(f"   独立分类数: {metadata['independent_categories_count']}")
        
        print(f"\n📂 主分类列表:")
        for main_cat_name, main_cat_info in main_cats.items():
            print(f"   - {main_cat_name}")
            print(f"     描述: {main_cat_info['description']}")
            if main_cat_info['subcategories']:
                print(f"     子分类: {len(main_cat_info['subcategories'])} 个")
        
        if indep_cats:
            print(f"\n🔖 独立分类列表:")
            for indep_cat_name, indep_cat_info in indep_cats.items():
                print(f"   - {indep_cat_name}")
                print(f"     描述: {indep_cat_info['description']}")
        
        print(f"\n✅ 分类标准已保存到: {result_file}")
        print(f"\n💡 注意事项:")
        print(f"   - 生成的描述可以根据需要手动修改")
        print(f"   - 子分类描述都包含了对主分类的依赖要求")
        print(f"   - 可以直接编辑JSON文件来调整分类层级和描述")
        
        return result_file


def main():
    """主函数"""
    print("=" * 60)
    print("🏗️ Zotero分类标准生成工具 - 002")
    print("=" * 60)
    
    # 检查环境变量
    required_vars = ['ZOTERO_USER_ID', 'ZOTERO_API_KEY', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("\n请设置以下环境变量：")
        print("export ZOTERO_USER_ID='你的Zotero用户ID'")
        print("export ZOTERO_API_KEY='你的Zotero API密钥'")
        print("export OPENAI_API_KEY='你的OpenAI API密钥'")
        print("export OPENAI_BASE_URL='你的OpenAI Base URL' (可选)")
        return 1
    
    try:
        # 创建生成器
        generator = ClassificationSchemaGenerator()
        
        # 生成并保存分类标准
        result_file = generator.generate_and_save()
        
        if result_file:
            print(f"\n🎉 分类标准生成完成！")
            print(f"📁 标准文件: {result_file}")
            print(f"\n💡 下一步:")
            print(f"   1. 检查并编辑分类标准文件（如需要）")
            print(f"   2. 运行: python 003_classify_literature.py")
        else:
            print("❌ 生成失败")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        return 1
    except Exception as e:
        print(f"程序出错：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 