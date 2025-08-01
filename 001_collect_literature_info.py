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
from tqdm import tqdm

# 导入配置系统
from config import (
    get_zotero_config, get_config,
    get_default_limit, get_abstract_limit
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiteratureCollector:
    """文献信息收集器"""
    
    def __init__(self, abstract_limit: int = None):
        """初始化收集器"""
        self.zotero_config = get_zotero_config()
        self.base_url = self.zotero_config.api_base_url
        self.user_id = self.zotero_config.user_id
        self.headers = self.zotero_config.headers
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 缓存集合信息
        self._collections_cache = None
        self._collections_cache_time = 0
        self._cache_ttl = 300  # 5分钟缓存
        
        # 摘要长度限制
        self.abstract_limit = abstract_limit or get_abstract_limit()
        
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

    def get_all_items(self, limit: int = None) -> List[Dict[str, Any]]:
        """获取所有文献项目（优化版本）"""
        all_items = []
        start = 0
        batch_size = min(limit or get_default_limit(), 100)  # 限制批量大小
        
        logger.info(f"📊 开始获取文献项目 (批量大小: {batch_size})...")
        
        with tqdm(desc="获取文献") as pbar:
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
                    pbar.update(len(items))
                    
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

    def _has_collection(self, item: Dict[str, Any]) -> bool:
        """判断项目是否有分类"""
        collections = item.get('data', {}).get('collections', [])
        return len(collections) > 0

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
            with tqdm(total=len(items), desc="提取详细信息") as pbar:
                for future in as_completed(future_to_item):
                    try:
                        details = future.result()
                        if details:
                            detailed_items.append(details)
                        pbar.update(1)
                            
                    except Exception as e:
                        item = future_to_item[future]
                        logger.warning(f"⚠️  处理项目失败 {item.get('key', 'unknown')}: {e}")
                        pbar.update(1)
        
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

    def collect_and_save(self, limit: int = None) -> str:
        """收集所有文献信息并保存到Excel文件"""
        start_time = time.time()
        logger.info("🚀 开始收集文献信息...")
        
        # 获取所有项目
        all_items = self.get_all_items(limit)
        self.total_items = len(all_items)
        
        # 筛选标准文献项目
        proper_items = [item for item in all_items if self._is_proper_item(item)]
        self.proper_items = len(proper_items)
        
        # 筛选有分类的文献
        classified_items = [item for item in proper_items if self._has_collection(item)]
        
        # 批量获取详细信息
        detailed_items = self._get_item_details_batch(classified_items)
        
        self.exported_items = len(detailed_items)
        
        elapsed_time = time.time() - start_time
        
        # 打印统计信息
        logger.info("📊 项目统计:")
        logger.info(f"   总项目数: {self.total_items}")
        logger.info(f"   标准文献数: {self.proper_items}")
        logger.info(f"   有分类的标准文献数: {len(classified_items)}")
        logger.info(f"   导出项目数: {self.exported_items}")
        logger.info(f"   处理时间: {elapsed_time:.2f}秒")
        
        if not detailed_items:
            logger.warning("⚠️  没有找到有分类的文献需要导出")
            return ""
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"literature_info_{timestamp}.xlsx"
        filepath = self.data_dir / filename
        
        # 保存到Excel
        try:
            df = pd.DataFrame(detailed_items)
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"💾 正在保存到 {filepath}...")
            return str(filepath)
        except Exception as e:
            logger.error(f"❌ 导出Excel文件失败: {e}")
            return ""

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="001 - 从Zotero收集文献信息并导出为Excel文件，用于后续分类",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python 001_collect_literature_info.py --limit 1000

注意事项:
  - 需要配置Zotero API环境变量
  - 只处理标准的Zotero文献类型
  - 只导出有分类的文献（即已手动分类或之前已分类的文献）
        """
    )
    
    # 可选参数
    parser.add_argument('--limit', type=int, help='限制检查的文献数量')
    parser.add_argument('--abstract-limit', type=int, help=f'摘要长度限制（默认: {get_abstract_limit()}字符）')
    
    args = parser.parse_args()
    
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
        collector = LiteratureCollector(abstract_limit=args.abstract_limit)
        
        # 收集并保存文献信息
        result_file = collector.collect_and_save(limit=args.limit)
        
        if result_file:
            print(f"\n✅ 收集完成！")
            print(f"📁 数据文件: {result_file}")
            print(f"\n💡 下一步操作:")
            print(f"  1. 检查生成的数据文件: {result_file}")
            print(f"  2. 生成分类Schema:")
            print(f"     python 002_generate_schema_and_create_collections.py --generate-schema --input {result_file}")
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