#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero文献内容分析脚本
分析文献的具体内容，查看可获取的字段信息
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter

class ZoteroContentAnalyzer:
    """Zotero文献内容分析器"""
    
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
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """获取所有文献条目"""
        all_items = []
        start = 0
        limit = 100
        
        print("正在获取文献数据...")
        
        while True:
            try:
                url = f"{self.base_url}/users/{self.user_id}/items"
                params = {
                    'format': 'json',
                    'limit': limit,
                    'start': start,
                    'sort': 'dateModified',
                    'direction': 'desc'
                }
                
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                items = response.json()
                if not items:
                    break
                    
                all_items.extend(items)
                start += limit
                print(f"已获取 {len(all_items)} 条记录...")
                
            except Exception as e:
                print(f"获取文献失败: {e}")
                break
        
        print(f"总共获取到 {len(all_items)} 条记录")
        return all_items
    
    def analyze_field_availability(self, items: List[Dict[str, Any]]) -> None:
        """分析字段可用性"""
        
        # 过滤出文献条目（排除笔记和附件）
        literature_items = []
        for item in items:
            data = item['data']
            item_type = data.get('itemType', 'unknown')
            
            if item_type == 'note':
                continue
            elif item_type == 'attachment':
                # 只跳过有父条目的附件
                if data.get('parentItem'):
                    continue
            
            literature_items.append(item)
        
        print(f"\n文献条目总数: {len(literature_items)}")
        
        # 统计各字段的可用性
        field_stats = defaultdict(int)
        item_type_stats = Counter()
        
        # 关键字段列表
        key_fields = [
            'title', 'abstractNote', 'creators', 'date', 'publicationTitle',
            'volume', 'issue', 'pages', 'DOI', 'url', 'language', 'itemType',
            'tags', 'collections', 'extra', 'journalAbbreviation', 'ISSN',
            'publisher', 'place', 'edition', 'numPages', 'series', 'seriesNumber'
        ]
        
        print("\n字段可用性统计:")
        print("=" * 60)
        
        for item in literature_items:
            data = item['data']
            item_type = data.get('itemType', 'unknown')
            item_type_stats[item_type] += 1
            
            for field in key_fields:
                if field in data and data[field]:
                    # 特殊处理列表类型的字段
                    if field in ['creators', 'tags', 'collections']:
                        if isinstance(data[field], list) and len(data[field]) > 0:
                            field_stats[field] += 1
                    else:
                        field_stats[field] += 1
        
        # 显示字段统计
        total_items = len(literature_items)
        for field in key_fields:
            count = field_stats[field]
            percentage = (count / total_items) * 100 if total_items > 0 else 0
            print(f"{field:20} | {count:4d}/{total_items:4d} ({percentage:5.1f}%)")
        
        # 显示文献类型统计
        print(f"\n文献类型分布:")
        print("=" * 30)
        for item_type, count in item_type_stats.most_common():
            print(f"{item_type:20} | {count:4d}")
    
    def show_sample_items(self, items: List[Dict[str, Any]], num_samples: int = 5) -> None:
        """显示样本文献的详细信息"""
        
        # 过滤出文献条目
        literature_items = []
        for item in items:
            data = item['data']
            item_type = data.get('itemType', 'unknown')
            
            if item_type == 'note':
                continue
            elif item_type == 'attachment':
                if data.get('parentItem'):
                    continue
            
            literature_items.append(item)
        
        print(f"\n样本文献详情 (前{min(num_samples, len(literature_items))}篇):")
        print("=" * 80)
        
        for i, item in enumerate(literature_items[:num_samples]):
            data = item['data']
            print(f"\n【文献 {i+1}】")
            print("-" * 40)
            
            # 显示关键信息
            print(f"类型: {data.get('itemType', 'unknown')}")
            print(f"标题: {data.get('title', '无标题')}")
            
            # 作者信息
            creators = data.get('creators', [])
            if creators:
                authors = []
                for creator in creators:
                    if creator.get('firstName') and creator.get('lastName'):
                        authors.append(f"{creator['firstName']} {creator['lastName']}")
                    elif creator.get('name'):
                        authors.append(creator['name'])
                print(f"作者: {', '.join(authors)}")
            else:
                print("作者: 无")
            
            print(f"发表时间: {data.get('date', '无')}")
            print(f"期刊/会议: {data.get('publicationTitle', '无')}")
            print(f"DOI: {data.get('DOI', '无')}")
            print(f"URL: {data.get('url', '无')}")
            
            # 摘要（截取前200字符）
            abstract = data.get('abstractNote', '')
            if abstract:
                abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                print(f"摘要: {abstract_preview}")
            else:
                print("摘要: 无")
            
            # 标签
            tags = data.get('tags', [])
            if tags:
                tag_names = [tag.get('tag', '') for tag in tags if tag.get('tag')]
                print(f"标签: {', '.join(tag_names)}")
            else:
                print("标签: 无")
    
    def analyze_missing_collections_items(self, items: List[Dict[str, Any]]) -> None:
        """分析属于已删除集合的文献"""
        
        missing_collection_keys = ['9TGDQDAH', '6D76NGZ9']
        
        print(f"\n已删除集合的文献分析:")
        print("=" * 50)
        
        for missing_key in missing_collection_keys:
            print(f"\n集合 {missing_key} 的文献:")
            print("-" * 30)
            
            count = 0
            for item in items:
                data = item['data']
                item_type = data.get('itemType', 'unknown')
                
                # 跳过笔记和子附件
                if item_type == 'note':
                    continue
                elif item_type == 'attachment' and data.get('parentItem'):
                    continue
                
                collections = data.get('collections', [])
                if missing_key in collections:
                    count += 1
                    if count <= 3:  # 只显示前3个
                        title = data.get('title', '无标题')
                        item_type = data.get('itemType', 'unknown')
                        date = data.get('date', '无日期')
                        print(f"  {count}. [{item_type}] {title} ({date})")
            
            if count > 3:
                print(f"  ... 还有 {count - 3} 篇文献")
            
            print(f"  总计: {count} 篇")
    
    def run_analysis(self):
        """运行完整分析"""
        # 获取数据
        items = self.get_all_items()
        if not items:
            print("未找到任何条目")
            return
        
        # 分析字段可用性
        self.analyze_field_availability(items)
        
        # 显示样本文献
        self.show_sample_items(items)
        
        # 分析已删除集合的文献
        self.analyze_missing_collections_items(items)


def main():
    """主函数"""
    analyzer = ZoteroContentAnalyzer()
    if analyzer.user_id and analyzer.api_key:
        analyzer.run_analysis()
    else:
        print("请先设置环境变量:")
        print("export ZOTERO_USER_ID='your_user_id'")
        print("export ZOTERO_API_KEY='your_api_key'")


if __name__ == "__main__":
    main() 