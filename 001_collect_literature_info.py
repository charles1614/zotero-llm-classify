#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
001 - Collect Literature Information
收集Zotero文献信息并保存到Excel文件
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from tqdm import tqdm

# 导入已有的模块
from main import ZoteroManager

class LiteratureCollector:
    """文献信息收集器"""
    
    def __init__(self, user_id: str = None, api_key: str = None):
        """初始化收集器"""
        self.zotero = ZoteroManager(user_id, api_key)
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """获取所有文献项目"""
        all_items = []
        start = 0
        limit = 100
        
        print("📚 正在获取所有文献...")
        
        while True:
            try:
                items = self.zotero.get_items(limit=limit, start=start)
                if not items:
                    break
                    
                all_items.extend(items)
                start += limit
                print(f"   已获取 {len(all_items)} 篇文献...")
                
            except Exception as e:
                print(f"获取文献失败: {e}")
                break
        
        print(f"✅ 总共获取到 {len(all_items)} 篇文献")
        return all_items
    
    def extract_literature_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """提取文献详细信息"""
        data = item.get('data', {})
        
        # 基本信息
        item_key = data.get('key', '')
        title = data.get('title', '').strip()
        item_type = data.get('itemType', 'unknown')
        abstract = data.get('abstractNote', '').strip()
        url = data.get('url', '').strip()
        
        # 作者信息
        creators = data.get('creators', [])
        authors = []
        for creator in creators:
            if 'name' in creator:
                authors.append(creator['name'])
            elif 'firstName' in creator or 'lastName' in creator:
                first = creator.get('firstName', '')
                last = creator.get('lastName', '')
                if first and last:
                    authors.append(f"{first} {last}")
                elif last:
                    authors.append(last)
        
        authors_str = '; '.join(authors) if authors else ''
        
        # 出版信息
        publication_title = data.get('publicationTitle', '').strip()
        conference_name = data.get('conferenceName', '').strip()
        journal_abbreviation = data.get('journalAbbreviation', '').strip()
        publisher = data.get('publisher', '').strip()
        
        # 时间信息
        date = data.get('date', '').strip()
        
        # DOI和标识信息
        doi = data.get('DOI', '').strip()
        isbn = data.get('ISBN', '').strip()
        issn = data.get('ISSN', '').strip()
        
        # 标签
        tags = [tag.get('tag', '') for tag in data.get('tags', []) if tag.get('tag')]
        tags_str = '; '.join(tags) if tags else ''
        
        # 当前分类信息
        collections = data.get('collections', [])
        
        # 确保title存在
        if not title:
            title = '无标题'
        
        # 数据添加时间
        date_added = data.get('dateAdded', '')
        date_modified = data.get('dateModified', '')
        
        # 其他有用信息
        volume = data.get('volume', '').strip()
        issue = data.get('issue', '').strip()
        pages = data.get('pages', '').strip()
        
        return {
            'item_key': item_key,
            'title': title,
            'item_type': item_type,
            'authors': authors_str,
            'abstract': abstract,
            'publication_title': publication_title,
            'conference_name': conference_name,
            'journal_abbreviation': journal_abbreviation,
            'publisher': publisher,
            'date': date,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'doi': doi,
            'isbn': isbn,
            'issn': issn,
            'url': url,
            'tags': tags_str,
            'collections_count': len(collections),
            'collections_keys': '; '.join(collections) if collections else '',
            'date_added': date_added,
            'date_modified': date_modified,
            'abstract_length': len(abstract),
            'title_length': len(title),
            'has_doi': bool(doi),
            'has_abstract': bool(abstract),
            'has_tags': bool(tags),
        }
    
    def collect_and_save(self) -> str:
        """收集所有文献信息并保存到Excel文件"""
        print("🚀 开始收集文献信息...")
        
        # 获取所有文献
        all_items = self.get_all_items()
        if not all_items:
            print("❌ 没有找到文献")
            return ""
        
        # 定义真正的paper类型
        valid_paper_types = {'conferencePaper', 'document', 'journalArticle', 'preprint'}
        
        # 筛选出真正的paper
        paper_items = []
        type_counts = {}
        
        for item in all_items:
            item_type = item.get('data', {}).get('itemType', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            if item_type in valid_paper_types:
                paper_items.append(item)
        
        print(f"📊 文献类型统计:")
        for item_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            status = "✅" if item_type in valid_paper_types else "❌"
            print(f"   {status} {item_type}: {count} 篇")
        
        print(f"\n🎯 筛选结果:")
        print(f"   总条目数: {len(all_items)}")
        print(f"   真正paper数: {len(paper_items)}")
        print(f"   过滤掉: {len(all_items) - len(paper_items)} 条非paper条目")
        
        if not paper_items:
            print("❌ 没有找到有效的paper文献")
            return ""
        
        # 提取文献信息
        print("📊 正在提取paper详细信息...")
        literature_data = []
        
        for item in tqdm(paper_items, desc="提取信息", unit="篇"):
            try:
                info = self.extract_literature_info(item)
                literature_data.append(info)
            except Exception as e:
                print(f"提取文献信息失败: {e}")
                continue
        
        # 创建DataFrame
        df = pd.DataFrame(literature_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"literature_info_{timestamp}.xlsx"
        filepath = self.data_dir / filename
        
        # 保存到Excel
        print(f"💾 正在保存到 {filepath}...")
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        # 显示统计信息
        print(f"\n📊 Paper统计信息:")
        print(f"   有效paper数: {len(df)}")
        print(f"   paper类型分布:")
        type_counts = df['item_type'].value_counts()
        for item_type, count in type_counts.items():
            print(f"     ✅ {item_type}: {count} 篇")
        
        print(f"   有摘要的paper: {df['has_abstract'].sum()} 篇 ({df['has_abstract'].sum()/len(df)*100:.1f}%)")
        print(f"   有DOI的paper: {df['has_doi'].sum()} 篇 ({df['has_doi'].sum()/len(df)*100:.1f}%)")
        print(f"   有标签的paper: {df['has_tags'].sum()} 篇")
        print(f"   有分类的paper: {(df['collections_count'] > 0).sum()} 篇 ({(df['collections_count'] > 0).sum()/len(df)*100:.1f}%)")
        
        print(f"\n✅ 文献信息已保存到: {filepath}")
        return str(filepath)


def main():
    """主函数"""
    print("=" * 60)
    print("📚 Zotero文献信息收集工具 - 001")
    print("=" * 60)
    
    # 检查环境变量
    required_vars = ['ZOTERO_USER_ID', 'ZOTERO_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("\n请设置以下环境变量：")
        print("export ZOTERO_USER_ID='你的Zotero用户ID'")
        print("export ZOTERO_API_KEY='你的Zotero API密钥'")
        return 1
    
    try:
        # 创建收集器
        collector = LiteratureCollector()
        
        # 收集并保存文献信息
        result_file = collector.collect_and_save()
        
        if result_file:
            print(f"\n🎉 收集完成！")
            print(f"📁 数据文件: {result_file}")
            print(f"\n💡 下一步:")
            print(f"   运行: python 002_generate_classification_schema.py")
        else:
            print("❌ 收集失败")
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