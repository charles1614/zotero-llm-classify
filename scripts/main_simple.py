#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero文献管理工具 - 简化版
专注于核心的文献分类管理功能
"""

import requests
import json
import os
from typing import List, Dict, Any, Optional
from collections import defaultdict


class ZoteroManager:
    """Zotero API管理类 - 简化版"""
    
    def __init__(self, user_id: Optional[str] = None, api_key: Optional[str] = None):
        """初始化Zotero管理器"""
        self.base_url = "https://api.zotero.org"
        self.user_id = user_id or os.getenv('ZOTERO_USER_ID') or ""
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY') or ""
        
        if not self.user_id or not self.api_key:
            print("错误：请设置ZOTERO_USER_ID和ZOTERO_API_KEY环境变量")
            return
            
        self.headers = {
            'Zotero-API-Version': '3',
            'Zotero-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        print(f"已连接到用户 {self.user_id} 的Zotero库")
    
    def get_items(self, limit: int = 50, start: int = 0) -> List[Dict[str, Any]]:
        """获取文献列表"""
        try:
            url = f"{self.base_url}/users/{self.user_id}/items"
            params = {
                'limit': min(limit, 100),
                'start': start,
                'format': 'json'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            items = response.json()
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"获取文献列表失败：{e}")
            return []
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """获取所有分类"""
        try:
            url = f"{self.base_url}/users/{self.user_id}/collections"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            collections = response.json()
            return collections
            
        except requests.exceptions.RequestException as e:
            print(f"获取分类列表失败：{e}")
            return []
    
    def display_collections_simple(self, collections: List[Dict[str, Any]]):
        """简单显示分类列表（层级结构）"""
        print(f"\n=== 分类列表 ===")
        
        # 建立父子关系映射
        parent_child_map = defaultdict(list)
        collection_map = {}
        root_collections = []
        
        for coll in collections:
            data = coll['data']
            key = data['key']
            name = data['name']
            parent_key = data.get('parentCollection')
            
            collection_map[key] = {'name': name, 'parent': parent_key}
            
            if parent_key:
                parent_child_map[parent_key].append(key)
            else:
                root_collections.append(key)
        
        def print_tree(key, level=0):
            """递归打印分类树"""
            if key not in collection_map:
                return
            
            name = collection_map[key]['name']
            indent = "  " * level
            if level > 0:
                indent += "└─ "
            
            # 找到原始索引
            original_index = next((i for i, c in enumerate(collections) if c['data']['key'] == key), -1)
            print(f"{original_index + 1:2d}. {indent}{name} (ID: {key})")
            
            # 打印子分类
            if key in parent_child_map:
                for child_key in sorted(parent_child_map[key], 
                                      key=lambda x: collection_map.get(x, {}).get('name', '')):
                    print_tree(child_key, level + 1)
        
        # 按名称排序根分类
        sorted_roots = sorted(root_collections, 
                            key=lambda x: collection_map.get(x, {}).get('name', ''))
        
        for root_key in sorted_roots:
            print_tree(root_key)
    
    def get_item_detail(self, item_key: str) -> Dict[str, Any]:
        """获取文献详细信息"""
        try:
            url = f"{self.base_url}/users/{self.user_id}/items/{item_key}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取文献详情失败：{e}")
            return {}
    
    def add_item_to_collection(self, item_key: str, collection_key: str) -> bool:
        """将文献添加到指定分类"""
        try:
            # 获取文献当前信息
            item = self.get_item_detail(item_key)
            if not item:
                return False
            
            current_collections = item.get('data', {}).get('collections', [])
            
            if collection_key in current_collections:
                print(f"文献已经在分类中")
                return True
            
            # 添加新分类
            updated_collections = current_collections + [collection_key]
            update_data = {"collections": updated_collections}
            
            # 更新文献
            url = f"{self.base_url}/users/{self.user_id}/items/{item_key}"
            headers = self.headers.copy()
            headers['If-Unmodified-Since-Version'] = str(item.get('version', 0))
            
            response = requests.patch(url, headers=headers, json=update_data)
            response.raise_for_status()
            
            print(f"✅ 成功将文献添加到分类")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 添加文献到分类失败：{e}")
            return False
    
    def quick_classify_first_item(self):
        """快速分类第一个文献"""
        print("\n=== 快速分类测试 ===")
        
        # 获取第一个文献
        items = self.get_items(limit=1)
        if not items:
            print("❌ 无法获取文献")
            return
        
        item = items[0]
        item_key = item['data']['key']
        title = item['data'].get('title', '无标题')
        
        print(f"选中文献: {title}")
        print(f"文献ID: {item_key}")
        
        # 获取分类
        collections = self.get_collections()
        if not collections:
            print("❌ 无法获取分类")
            return
        
        self.display_collections_simple(collections)
        
        # 用户选择分类
        choice = input(f"\n请选择分类序号 (1-{len(collections)}): ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(collections):
                collection_key = collections[choice_num - 1]['data']['key']
                collection_name = collections[choice_num - 1]['data']['name']
                
                print(f"将添加到分类: {collection_name}")
                confirm = input("确认执行吗？(y/N): ").strip().lower()
                
                if confirm == 'y':
                    success = self.add_item_to_collection(item_key, collection_key)
                    if success:
                        print(f"🎉 测试成功！文献已添加到 '{collection_name}'")
                else:
                    print("操作已取消")
            else:
                print("序号超出范围")
        except ValueError:
            print("请输入有效数字")
    
    def show_basic_stats(self):
        """显示基本统计"""
        print("\n=== 基本统计 ===")
        
        items = self.get_items(limit=100)
        collections = self.get_collections()
        
        print(f"文献总数: {len(items)} (显示前100条)")
        print(f"分类总数: {len(collections)}")
        
        # 统计分类情况
        no_collection = 0
        has_collection = 0
        
        for item in items:
            item_collections = item.get('data', {}).get('collections', [])
            if item_collections:
                has_collection += 1
            else:
                no_collection += 1
        
        print(f"已分类文献: {has_collection}")
        print(f"未分类文献: {no_collection}")
        print(f"分类率: {has_collection/len(items)*100:.1f}%")


def main():
    """主函数"""
    print("Zotero文献管理工具 - 简化版")
    print("=" * 40)
    
    # 检查环境变量
    user_id = os.getenv('ZOTERO_USER_ID')
    api_key = os.getenv('ZOTERO_API_KEY')
    
    if not user_id or not api_key:
        print("\n请先设置环境变量：")
        print("export ZOTERO_USER_ID='你的用户ID'")
        print("export ZOTERO_API_KEY='你的API密钥'")
        return
    
    zotero = ZoteroManager()
    
    try:
        while True:
            print(f"\n=== 主菜单 ===")
            print("1. 显示分类列表")
            print("2. 快速分类测试")
            print("3. 基本统计")
            print("4. 运行完整分析")
            print("0. 退出")
            
            choice = input("\n请选择操作 (0-4): ").strip()
            
            if choice == '0':
                print("再见！")
                break
            elif choice == '1':
                collections = zotero.get_collections()
                zotero.display_collections_simple(collections)
            elif choice == '2':
                zotero.quick_classify_first_item()
            elif choice == '3':
                zotero.show_basic_stats()
            elif choice == '4':
                print("\n启动完整分析...")
                print("请运行: python analyze_library.py")
            else:
                print("无效选择，请重试")
    
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"程序出错：{e}")


if __name__ == "__main__":
    main()
