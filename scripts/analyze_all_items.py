#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析Zotero中所有条目的类型分布
"""

import os
import json
import requests
from typing import List, Dict, Any
from collections import defaultdict

class ZoteroItemAnalyzer:
    """Zotero条目详细分析器"""
    
    def __init__(self, user_id: str = None, api_key: str = None):
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
        """获取所有条目"""
        all_items = []
        start = 0
        limit = 100
        
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
                
            except Exception as e:
                print(f"获取条目失败: {e}")
                break
        
        return all_items
    
    def analyze_all_items(self, items: List[Dict[str, Any]]) -> None:
        """详细分析所有条目"""
        print("=" * 60)
        print("Zotero 库详细分析报告")
        print("=" * 60)
        
        # 统计各种类型
        item_type_stats = defaultdict(int)
        attachment_stats = defaultdict(int)
        literature_stats = defaultdict(int)
        note_stats = defaultdict(int)
        
        # 详细分类
        literature_items = []
        attachment_items = []
        note_items = []
        other_items = []
        
        for item in items:
            data = item['data']
            item_type = data.get('itemType', 'unknown')
            
            # 统计所有类型
            item_type_stats[item_type] += 1
            
            if item_type == 'note':
                note_items.append(item)
                note_stats['total'] += 1
            elif item_type == 'attachment':
                attachment_items.append(item)
                if data.get('parentItem'):
                    attachment_stats['with_parent'] += 1
                else:
                    attachment_stats['independent'] += 1
                    # 独立附件作为文献处理
                    literature_items.append(item)
                    literature_stats['independent_attachments'] += 1
            else:
                # 其他类型作为文献
                literature_items.append(item)
                literature_stats[item_type] += 1
        
        # 输出总体统计
        print(f"\n📊 总体统计:")
        print(f"总条目数: {len(items)}")
        print(f"文献条目数: {len(literature_items)}")
        print(f"附件条目数: {len(attachment_items)}")
        print(f"笔记条目数: {len(note_items)}")
        
        # 输出条目类型分布
        print(f"\n📋 条目类型详细分布:")
        print("-" * 40)
        for item_type, count in sorted(item_type_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"{item_type}: {count}")
        
        # 输出文献类型分布
        print(f"\n📚 文献类型分布 (共{len(literature_items)}个):")
        print("-" * 40)
        for lit_type, count in sorted(literature_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"{lit_type}: {count}")
        
        # 输出附件类型分布
        print(f"\n📎 附件类型分布 (共{len(attachment_items)}个):")
        print("-" * 40)
        print(f"有父条目的附件: {attachment_stats['with_parent']}")
        print(f"独立附件 (作为文献): {attachment_stats['independent']}")
        
        # 输出笔记统计
        print(f"\n📝 笔记统计:")
        print("-" * 40)
        print(f"笔记总数: {note_stats['total']}")
        
        # 解释为什么app显示不同
        print(f"\n💡 显示差异说明:")
        print("-" * 40)
        print(f"1. 脚本统计总条目: {len(items)}")
        print(f"2. 脚本统计文献: {len(literature_items)}")
        print(f"3. App可能只显示主要文献类型，不包括独立附件")
        print(f"4. App显示: ~200多个 (可能不包括 {attachment_stats['independent']} 个独立附件)")
        print(f"5. 其他 {len(items) - len(literature_items)} 个条目包括:")
        print(f"   - {attachment_stats['with_parent']} 个附件 (PDF、图片等)")
        print(f"   - {note_stats['total']} 个笔记")
        
        return {
            'total_items': len(items),
            'literature_items': len(literature_items),
            'attachment_items': len(attachment_items),
            'note_items': len(note_items),
            'item_type_stats': dict(item_type_stats),
            'literature_stats': dict(literature_stats),
            'attachment_stats': dict(attachment_stats)
        }
    
    def run_analysis(self):
        """运行分析"""
        items = self.get_all_items()
        if not items:
            print("未找到任何条目")
            return
        
        return self.analyze_all_items(items)


def main():
    """主函数"""
    analyzer = ZoteroItemAnalyzer()
    if analyzer.user_id and analyzer.api_key:
        result = analyzer.run_analysis()
        
        # 保存详细结果到JSON
        if result:
            with open('zotero_detailed_analysis.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 详细分析结果已保存到: zotero_detailed_analysis.json")
    else:
        print("请先设置环境变量:")
        print("export ZOTERO_USER_ID='your_user_id'")
        print("export ZOTERO_API_KEY='your_api_key'")


if __name__ == "__main__":
    main() 