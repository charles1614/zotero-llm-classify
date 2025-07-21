#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero分类层级关系分析脚本
分析并展示分类的父子关系结构
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from collections import defaultdict

class ZoteroHierarchyAnalyzer:
    """Zotero分类层级分析器"""
    
    def __init__(self, user_id: Optional[str] = None, api_key: Optional[str] = None):
        """初始化分析器"""
        self.base_url = "https://api.zotero.org"
        self.user_id = user_id or os.getenv('ZOTERO_USER_ID') or ""
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY') or ""
        
        if not self.user_id or not self.api_key:
            print("错误：请设置 ZOTERO_USER_ID 和 ZOTERO_API_KEY 环境变量")
            return
            
        self.headers = {
            'Zotero-API-Version': '3',
            'Zotero-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def get_all_collections(self) -> List[Dict[str, Any]]:
        """获取所有分类，包含层级信息"""
        try:
            url = f"{self.base_url}/users/{self.user_id}/collections"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            collections = response.json()
            return collections
        except Exception as e:
            print(f"获取分类失败: {e}")
            return []
    
    def analyze_hierarchy(self):
        """分析并展示分类层级结构"""
        collections = self.get_all_collections()
        if not collections:
            print("无法获取分类信息")
            return
        
        print(f"总分类数量: {len(collections)}")
        print("\n" + "="*60)
        print("分类层级结构分析")
        print("="*60)
        
        # 构建分类映射
        collection_map = {}
        parent_child_map = defaultdict(list)
        root_collections = []
        
        for collection in collections:
            key = collection['key']
            data = collection['data']
            name = data['name']
            parent_collection = data.get('parentCollection')
            
            collection_map[key] = {
                'name': name,
                'parent': parent_collection,
                'data': data
            }
            
            if parent_collection:
                parent_child_map[parent_collection].append(key)
            else:
                root_collections.append(key)
        
        # 显示层级结构
        print(f"\n🌳 分类层级结构:")
        print("-" * 40)
        
        def print_hierarchy(collection_key: str, level: int = 0):
            """递归打印层级结构"""
            indent = "  " * level
            if collection_key in collection_map:
                name = collection_map[collection_key]['name']
                print(f"{indent}{name} ({collection_key})")
                
                # 打印子分类
                children = parent_child_map.get(collection_key, [])
                for child_key in sorted(children, key=lambda k: collection_map[k]['name']):
                    print_hierarchy(child_key, level + 1)
        
        # 打印根分类及其子分类
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            print_hierarchy(root_key)
        
        # 统计信息
        print(f"\n📊 层级统计:")
        print("-" * 30)
        print(f"根分类数量: {len(root_collections)}")
        
        total_children = sum(len(children) for children in parent_child_map.values())
        print(f"子分类数量: {total_children}")
        print(f"独立分类数量: {len(collections) - total_children}")
        
        # 显示每个根分类的子分类数量
        print(f"\n📂 各根分类的子分类数量:")
        print("-" * 35)
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            root_name = collection_map[root_key]['name']
            child_count = len(parent_child_map.get(root_key, []))
            print(f"{root_name}: {child_count} 个子分类")
        
        # 生成层级字典（用于代码）
        hierarchy_dict = self._generate_hierarchy_dict(collection_map, parent_child_map, root_collections)
        
        print(f"\n💻 生成的层级字典（用于代码）:")
        print("-" * 40)
        print("COLLECTION_HIERARCHY = {")
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            root_name = collection_map[root_key]['name']
            children = parent_child_map.get(root_key, [])
            if children:
                child_names = [collection_map[child]['name'] for child in children]
                child_names_str = ", ".join([f"'{name}'" for name in sorted(child_names)])
                print(f"    '{root_name}': [{child_names_str}],")
            else:
                print(f"    '{root_name}': [],")
        print("}")
        
        return hierarchy_dict, collection_map, parent_child_map
    
    def _generate_hierarchy_dict(self, collection_map, parent_child_map, root_collections):
        """生成层级字典"""
        hierarchy = {}
        
        for root_key in root_collections:
            root_name = collection_map[root_key]['name']
            children = parent_child_map.get(root_key, [])
            child_names = [collection_map[child]['name'] for child in children]
            hierarchy[root_name] = sorted(child_names)
        
        return hierarchy
    
    def export_hierarchy_config(self, filename: str = "collection_hierarchy.py"):
        """导出层级配置到Python文件"""
        hierarchy_dict, collection_map, parent_child_map = self.analyze_hierarchy()
        
        # 生成配置文件内容
        config_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero分类层级配置
自动生成，包含分类的层级关系和描述信息
"""

# 分类层级关系 (父分类 -> [子分类列表])
COLLECTION_HIERARCHY = {
'''
        
        root_collections = [k for k in collection_map.keys() if not collection_map[k]['parent']]
        
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            root_name = collection_map[root_key]['name']
            children = [k for k in collection_map.keys() if collection_map[k]['parent'] == root_key]
            if children:
                child_names = [collection_map[child]['name'] for child in children]
                child_names_str = ", ".join([f"'{name}'" for name in sorted(child_names)])
                config_content += f"    '{root_name}': [{child_names_str}],\n"
            else:
                config_content += f"    '{root_name}': [],\n"
        
        config_content += '''}

# 分类描述信息 (请手动填写每个分类的用途说明)
COLLECTION_DESCRIPTIONS = {
    # === 根分类描述 ===
'''
        
        # 添加根分类描述模板
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            root_name = collection_map[root_key]['name']
            config_content += f"    '{root_name}': '请填写{root_name}分类的描述',\n"
        
        config_content += '''    
    # === 子分类描述 ===
'''
        
        # 添加子分类描述模板
        for root_key in sorted(root_collections, key=lambda k: collection_map[k]['name']):
            children = [k for k in collection_map.keys() if collection_map[k]['parent'] == root_key]
            if children:
                for child_key in sorted(children, key=lambda k: collection_map[k]['name']):
                    child_name = collection_map[child_key]['name']
                    config_content += f"    '{child_name}': '请填写{child_name}分类的描述',\n"
        
        config_content += '''}

def get_parent_category(subcategory: str) -> str:
    """获取子分类的父分类"""
    for parent, children in COLLECTION_HIERARCHY.items():
        if subcategory in children:
            return parent
    return subcategory  # 如果不是子分类，返回自身

def get_all_subcategories(parent_category: str) -> list:
    """获取父分类的所有子分类"""
    return COLLECTION_HIERARCHY.get(parent_category, [])

def is_parent_category(category: str) -> bool:
    """判断是否为父分类"""
    return category in COLLECTION_HIERARCHY and len(COLLECTION_HIERARCHY[category]) > 0

def is_subcategory(category: str) -> bool:
    """判断是否为子分类"""
    for parent, children in COLLECTION_HIERARCHY.items():
        if category in children:
            return True
    return False

def get_category_description(category: str) -> str:
    """获取分类描述"""
    return COLLECTION_DESCRIPTIONS.get(category, f"未提供{category}的描述")

def validate_category_combination(categories: list) -> dict:
    """验证分类组合是否合理"""
    result = {
        'valid': True,
        'warnings': [],
        'suggestions': []
    }
    
    parent_categories = set()
    subcategories = set()
    
    for category in categories:
        if is_parent_category(category):
            parent_categories.add(category)
        elif is_subcategory(category):
            subcategories.add(category)
            parent = get_parent_category(category)
            parent_categories.add(parent)
    
    # 检查是否同时包含父分类和其子分类
    for category in categories:
        if is_parent_category(category):
            children_in_list = [c for c in categories if c in get_all_subcategories(category)]
            if children_in_list:
                result['warnings'].append(
                    f"同时包含父分类'{category}'和其子分类{children_in_list}，建议只使用子分类"
                )
    
    return result
'''
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"\n✅ 层级配置已导出到: {filename}")
        print("请编辑该文件，手动填写每个分类的描述信息！")


def main():
    """主函数"""
    analyzer = ZoteroHierarchyAnalyzer()
    if analyzer.user_id and analyzer.api_key:
        analyzer.export_hierarchy_config()
    else:
        print("请设置环境变量:")
        print("export ZOTERO_USER_ID='your_user_id'")
        print("export ZOTERO_API_KEY='your_api_key'")


if __name__ == "__main__":
    main() 