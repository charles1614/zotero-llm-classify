#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
006 - 检查并导出未分类的标准文献项目
检查并导出未分类的标准文献项目

主要功能：
1. 检查Zotero中未分类的标准文献项目
2. 导出未分类文献的详细信息
3. 支持多种输出格式（JSON、Excel）
4. 过滤非标准文献类型
5. 高性能批量处理

注意：此脚本只处理标准的Zotero文献类型，不包括附件、笔记等
"""

import os
import sys
import json
import argparse
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 导入配置系统
from config import (
    get_zotero_config, get_config,
    get_default_limit, get_abstract_limit
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MissingItemsChecker:
    """未分类文献检查器"""
    
    def __init__(self, abstract_limit: int = None, schema_file: str = None):
        """初始化检查器"""
        self.zotero_config = get_zotero_config()
        self.base_url = self.zotero_config.api_base_url
        self.user_id = self.zotero_config.user_id
        self.headers = self.zotero_config.headers
        
        # 缓存集合信息
        self._collections_cache = None
        self._collections_cache_time = 0
        self._cache_ttl = 300  # 5分钟缓存
        
        # 摘要长度限制
        self.abstract_limit = abstract_limit or get_abstract_limit()
        
        # 加载schema文件
        self.schema_collection_keys = set()
        if schema_file:
            self._load_schema_collection_keys(schema_file)
        
        # 标准文献类型（排除附件、笔记等）
        self.proper_item_types = {
            'journalArticle', 'conferencePaper', 'book', 'bookSection', 
            'thesis', 'report', 'document', 'preprint', 'patent',
            'webpage', 'computerProgram', 'software', 'dataset',
            'presentation', 'videoRecording', 'audioRecording',
            'artwork', 'map', 'blogPost', 'forumPost', 'email',
            'letter', 'manuscript', 'encyclopediaArticle', 'dictionaryEntry',
            'newspaperArticle', 'magazineArticle', 'case', 'statute',
            'hearing', 'bill', 'treaty', 'regulation', 'standard'
        }
        
        # 统计信息
        self.total_items = 0
        self.proper_items = 0
        self.unfiled_items = 0
        self.exported_items = 0
        
    def _load_schema_collection_keys(self, schema_file: str):
        """加载schema文件中的collection_key"""
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            # 提取所有collection_key
            collection_keys = set()
            
            # 从主分类中提取
            main_categories = schema_data.get('classification_schema', {}).get('main_categories', {})
            for category in main_categories.values():
                if 'collection_key' in category:
                    collection_keys.add(category['collection_key'])
                
                # 从子分类中提取
                subcategories = category.get('subcategories', [])
                for subcategory in subcategories:
                    if 'collection_key' in subcategory:
                        collection_keys.add(subcategory['collection_key'])
            
            # 从独立分类中提取
            independent_categories = schema_data.get('classification_schema', {}).get('independent_categories', {})
            for category in independent_categories.values():
                if 'collection_key' in category:
                    collection_keys.add(category['collection_key'])
            
            self.schema_collection_keys = collection_keys
            logger.info(f"✅ 已加载schema文件，包含 {len(collection_keys)} 个分类集合")
            
        except Exception as e:
            logger.error(f"❌ 加载schema文件失败: {e}")
            self.schema_collection_keys = set()
    
    def _get_all_items(self, limit: int = None) -> List[Dict[str, Any]]:
        """获取所有文献项目（优化版本）"""
        all_items = []
        start = 0
        batch_size = min(limit or get_default_limit(), 100)  # 限制批量大小
        
        logger.info(f"📊 开始获取文献项目 (批量大小: {batch_size})...")
        
        while True:
            try:
                url = f"{self.base_url}/items"
                params = {
                    'start': start,
                    'limit': batch_size,
                    'format': 'json'
                }
            
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                items = response.json()
                if not items:
                    break
                
                all_items.extend(items)
                start += len(items)
                
                if len(all_items) % 500 == 0:
                    logger.info(f"📦 已获取 {len(all_items)} 个项目...")
                
                # 如果达到限制，停止
                if limit and len(all_items) >= limit:
                    all_items = all_items[:limit]
                    break
                    
                # 如果返回的项目数少于批量大小，说明已经获取完所有项目
                if len(items) < batch_size:
                    break
                
            except Exception as e:
                logger.error(f"❌ 获取文献项目失败: {e}")
                break
        
        logger.info(f"✅ 总共获取到 {len(all_items)} 个项目")
        return all_items
    
    def _get_all_collections(self) -> Dict[str, str]:
        """获取所有集合的key到name的映射（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._collections_cache is not None and 
            current_time - self._collections_cache_time < self._cache_ttl):
            return self._collections_cache
        
        try:
            url = f"{self.base_url}/collections"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            collections = response.json()
            collection_dict = {}
            
            for collection in collections:
                key = collection.get('key')
                name = collection.get('data', {}).get('name', '')
                if key and name:
                    collection_dict[key] = name
            
            # 更新缓存
            self._collections_cache = collection_dict
            self._collections_cache_time = current_time
            
            return collection_dict
            
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {e}")
            return {}
    
    def _is_proper_item(self, item: Dict[str, Any]) -> bool:
        """判断是否为标准文献项目"""
        item_type = item.get('data', {}).get('itemType', '')
        return item_type in self.proper_item_types
    
    def _needs_classification(self, item: Dict[str, Any]) -> bool:
        """判断项目是否需要分类"""
        collections = item.get('data', {}).get('collections', [])
        
        # 如果没有集合，需要分类
        if len(collections) == 0:
            return True
        
        # 如果没有加载schema文件，使用原来的逻辑
        if not self.schema_collection_keys:
            return False
        
        # 检查文献的集合是否在schema中
        for collection_key in collections:
            if collection_key in self.schema_collection_keys:
                # 如果文献在schema中的集合里，说明已分类
                return False
        
        # 如果文献的集合都不在schema中，说明未分类
        return True
    
    def _get_item_details_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量获取文献详细信息（并行处理）"""
        if not items:
            return []
        
        logger.info(f"🔍 开始批量获取 {len(items)} 个项目的详细信息...")
        
        # 使用线程池并行处理
        max_workers = min(10, len(items))  # 限制并发数
        detailed_items = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_item = {
                executor.submit(self._get_single_item_details, item): item 
                for item in items
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_item):
                try:
                    details = future.result()
                    if details:
                        detailed_items.append(details)
                    completed += 1
                    
                    if completed % 50 == 0:
                        logger.info(f"📋 已处理 {completed}/{len(items)} 个项目...")
                        
                except Exception as e:
                    item = future_to_item[future]
                    logger.warning(f"⚠️  处理项目失败 {item.get('key', 'unknown')}: {e}")
                    completed += 1
        
        logger.info(f"✅ 批量处理完成，成功获取 {len(detailed_items)} 个项目的详细信息")
        return detailed_items
    
    def _get_single_item_details(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取单个文献详细信息"""
        try:
            item_data = item.get('data', {})
            
            # 基本信息
            details = {
                'item_key': item.get('key', ''),
                'title': item_data.get('title', ''),
                'item_type': item_data.get('itemType', ''),
                'authors': self._extract_authors(item_data),
                'publication_title': item_data.get('publicationTitle', ''),
                'conference_name': item_data.get('conferenceName', ''),
                'date': item_data.get('date', ''),
                'doi': item_data.get('DOI', ''),
                'abstract': self._extract_abstract(item_data),
                'tags': self._extract_tags(item_data),
                'url': item_data.get('url', ''),
                'language': item_data.get('language', ''),
                'pages': item_data.get('pages', ''),
                'volume': item_data.get('volume', ''),
                'issue': item_data.get('issue', ''),
                'publisher': item_data.get('publisher', ''),
                'place': item_data.get('place', ''),
                'edition': item_data.get('edition', ''),
                'series': item_data.get('series', ''),
                'isbn': item_data.get('ISBN', ''),
                'issn': item_data.get('ISSN', ''),
                'call_number': item_data.get('callNumber', ''),
                'access_date': item_data.get('accessDate', ''),
                'rights': item_data.get('rights', ''),
                'extra': item_data.get('extra', ''),
                'collections': '',
                'collections_keys': '',
                'collections_count': 0,
                'notes': '',
                'attachments': '',
                'attachments_count': 0,
                'related_items': '',
                'related_items_count': 0,
                'created_date': item_data.get('dateAdded', ''),
                'modified_date': item_data.get('dateModified', ''),
                'last_modified_by': item_data.get('lastModifiedByUser', ''),
                'version': item.get('version', '')
            }
            
            # 获取集合信息
            collections = item_data.get('collections', [])
            if collections:
                details['collections_count'] = len(collections)
                details['collections_keys'] = '; '.join(collections)
                
                # 获取集合名称
                all_collections = self._get_all_collections()
                collection_names = []
                for collection_key in collections:
                    collection_name = all_collections.get(collection_key, '')
                    if collection_name:
                        collection_names.append(collection_name)
                details['collections'] = '; '.join(collection_names)
            
            # 获取附件信息
            attachments = item.get('attachments', [])
            if attachments:
                details['attachments_count'] = len(attachments)
                attachment_names = [att.get('data', {}).get('title', '') for att in attachments]
                details['attachments'] = '; '.join(attachment_names)
            
            # 获取相关项目信息
            related_items = item.get('relatedItems', [])
            if related_items:
                details['related_items_count'] = len(related_items)
                details['related_items'] = '; '.join(related_items)
            
            return details
            
        except Exception as e:
            logger.warning(f"⚠️  获取项目详情失败: {e}")
            return None
    
    def _extract_authors(self, item_data: Dict[str, Any]) -> str:
        """提取作者信息"""
        creators = item_data.get('creators', [])
        if not creators:
            return ''
        
        author_names = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                name = creator.get('name', '') or f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                if name:
                    author_names.append(name)
        
        return '; '.join(author_names)
    
    def _extract_abstract(self, item_data: Dict[str, Any]) -> str:
        """提取摘要信息"""
        # 尝试多个可能的摘要字段
        abstract = item_data.get('abstractNote', '')
        if not abstract:
            abstract = item_data.get('extra', '')
        if not abstract:
            # 从notes中查找摘要
            notes = item_data.get('notes', [])
            for note in notes:
                note_content = note.get('data', {}).get('note', '')
                if 'abstract' in note_content.lower() or '摘要' in note_content:
                    abstract = note_content
                    break
        
        # 限制摘要长度
        abstract_limit = self.abstract_limit
        if len(abstract) > abstract_limit:
            abstract = abstract[:abstract_limit] + '...'
        
        return abstract
    
    def _extract_tags(self, item_data: Dict[str, Any]) -> str:
        """提取标签信息"""
        tags = item_data.get('tags', [])
        if not tags:
            return ''
        
        tag_names = [tag.get('tag', '') for tag in tags if tag.get('tag')]
        return '; '.join(tag_names)
    
    def check_missing_items(self, limit: int = None) -> List[Dict[str, Any]]:
        """检查未分类的标准文献项目（优化版本）"""
        start_time = time.time()
        logger.info("🔍 开始检查未分类的标准文献项目...")
        
        # 获取所有项目
        all_items = self._get_all_items(limit)
        self.total_items = len(all_items)
        
        # 筛选标准文献项目
        proper_items = [item for item in all_items if self._is_proper_item(item)]
        self.proper_items = len(proper_items)
        
        # 筛选需要分类的项目（未分类和临时集合中的文献）
        unfiled_items = []
        for item in proper_items:
            if self._needs_classification(item):
                unfiled_items.append(item)
        
        self.unfiled_items = len(unfiled_items)
        
        # 批量获取详细信息
        detailed_items = self._get_item_details_batch(unfiled_items)
        
        self.exported_items = len(detailed_items)
        
        elapsed_time = time.time() - start_time
        
        # 打印统计信息
        logger.info("📊 项目统计:")
        logger.info(f"   总项目数: {self.total_items}")
        logger.info(f"   标准文献数: {self.proper_items}")
        logger.info(f"   需要分类的标准文献数: {self.unfiled_items}")
        logger.info(f"   导出项目数: {self.exported_items}")
        logger.info(f"   处理时间: {elapsed_time:.2f}秒")
        
        return detailed_items
    
    def export_items(self, items: List[Dict[str, Any]], output_format: str = 'excel') -> str:
        """导出未分类文献"""
        if not items:
            logger.warning("⚠️  没有未分类的文献需要导出")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == 'json':
            output_file = f"data/unfiled_proper_items_{timestamp}.json"
        
            export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                    'total_items': self.total_items,
                    'proper_items': self.proper_items,
                    'unfiled_items': self.unfiled_items,
                    'exported_items': self.exported_items
            },
            'literature_data': items
        }
        
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
        
                logger.info(f"✅ 未分类文献已导出到: {output_file}")
                return output_file
    
            except Exception as e:
                logger.error(f"❌ 导出JSON文件失败: {e}")
                return ""
        
        elif output_format.lower() == 'excel':
            output_file = f"data/unfiled_proper_items_{timestamp}.xlsx"
            
            try:
                df = pd.DataFrame(items)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                df.to_excel(output_file, index=False, engine='openpyxl')
                
                logger.info(f"✅ 未分类文献已导出到: {output_file}")
                return output_file
                
            except Exception as e:
                logger.error(f"❌ 导出Excel文件失败: {e}")
                return ""
        
        else:
            logger.error(f"❌ 不支持的输出格式: {output_format}")
            return ""


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="006 - 检查Zotero中未分类的标准文献项目，并导出为JSON或Excel文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 检查并导出未分类的文献（JSON格式）
  python 006_check_and_export_missing_proper_items.py --output-format json
  
  # 检查并导出未分类的文献（Excel格式）
  python 006_check_and_export_missing_proper_items.py --output-format excel
  
  # 使用schema文件判断分类状态
  python 006_check_and_export_missing_proper_items.py --schema data/schema_with_collection_keys.json --output-format excel
  
  # 限制检查数量
  python 006_check_and_export_missing_proper_items.py --limit 1000 --output-format json
  
  # 自定义摘要长度限制
  python 006_check_and_export_missing_proper_items.py --abstract-limit 5000 --output-format excel

注意事项:
  - 需要配置Zotero API环境变量
  - 只处理标准的Zotero文献类型
  - 排除附件、笔记等非文献项目
  - 支持JSON和Excel两种输出格式
  - 使用--schema参数指定分类schema文件，根据schema中的collection_key判断文献是否已分类
  - 默认摘要长度限制为2000字符，可使用--abstract-limit自定义
        """
    )
    
    # 可选参数
    parser.add_argument('--limit', type=int, help='限制检查的文献数量')
    parser.add_argument('--output-format', type=str, choices=['json', 'excel'], default='excel', 
                       help='输出格式（默认: excel）')
    parser.add_argument('--abstract-limit', type=int, help=f'摘要长度限制（默认: {get_abstract_limit()}字符）')
    parser.add_argument('--schema', type=str, help='自定义schema文件路径，用于覆盖默认的schema_with_collection_keys.json')
    
    args = parser.parse_args()
    
    # 创建检查器
    checker = MissingItemsChecker(abstract_limit=args.abstract_limit, schema_file=args.schema)
    
    # 检查未分类文献
    unfiled_items = checker.check_missing_items(limit=args.limit)
    
    if not unfiled_items:
        print("✅ 没有发现未分类的标准文献项目")
        return 0
    
    # 导出结果
    output_file = checker.export_items(unfiled_items, args.output_format)
    
    if output_file:
        print(f"\n✅ 检查完成！")
        print(f"📊 统计信息:")
        print(f"   总项目数: {checker.total_items}")
        print(f"   标准文献数: {checker.proper_items}")
        print(f"   需要分类的标准文献数: {checker.unfiled_items}")
        print(f"   导出项目数: {checker.exported_items}")
        print(f"📁 导出文件: {output_file}")
        schema_file_for_next_step = args.schema if args.schema else "<请提供一个schema文件，例如: data/schema_with_collection_keys_YYYYMMDD_HHMMSS.json>"
        print(f"""
💡 下一步操作:
  1. 检查导出的未分类文献: {output_file}
  2. 使用004脚本进行分类:
     python 004_reclassify_with_new_schema.py --plan --schema {schema_file_for_next_step} --input {output_file}
""")
        return 0
    else:
        print("❌ 导出失败")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 