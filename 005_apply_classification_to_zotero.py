#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
005 - 将LLM分类计划应用到Zotero
安全地将分类结果应用到Zotero

主要功能：
1. 加载分类计划文件
2. 安全地更新Zotero文献的集合
3. 支持测试模式和批量处理
4. 只添加新分类，不删除现有分类

注意：此脚本只添加新的集合关联，不会删除现有的分类
"""

import os
import sys
import json
import argparse
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from tqdm import tqdm

# 导入配置系统
from config import (
    get_zotero_config, get_config,
    get_default_test_items, get_title_preview_length
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClassificationApplier:
    """分类应用器"""
    
    def __init__(self):
        """初始化应用器"""
        self.zotero_config = get_zotero_config()
        self.base_url = self.zotero_config.api_base_url
        self.user_id = self.zotero_config.user_id
        self.headers = self.zotero_config.headers
        
        # 统计信息
        self.total_items = 0
        self.processed_items = 0
        self.successful_applications = 0
        self.failed_applications = 0
    
    def _load_classification_plan(self, plan_file: str) -> Dict[str, Any]:
        """加载分类计划文件"""
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
            logger.info(f"✅ 成功加载分类计划: {plan_file}")
            return plan_data
        except Exception as e:
            logger.error(f"❌ 加载分类计划失败: {e}")
            return {}
    
    def _get_item_collections(self, item_key: str) -> List[str]:
        """获取文献当前的集合"""
        try:
            url = f"{self.base_url}/items/{item_key}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            item_data = response.json()
            collections = item_data.get('data', {}).get('collections', [])
            return collections
                
        except Exception as e:
            logger.warning(f"获取文献 {item_key} 的集合失败: {e}")
            return []
    
    def _get_item_version(self, item_key: str) -> Optional[str]:
        """获取文献的版本号"""
        try:
            url = f"{self.base_url}/items/{item_key}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            item_data = response.json()
            return item_data.get('version')
                
        except Exception as e:
            logger.warning(f"获取文献 {item_key} 的版本失败: {e}")
            return None
    
    def _validate_collection(self, collection_key: str) -> bool:
        """验证集合是否存在"""
        try:
            url = f"{self.base_url}/collections/{collection_key}"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_valid_collections(self, collection_keys: List[str]) -> List[str]:
        """过滤出有效的集合"""
        valid_collections = []
        for key in collection_keys:
            if self._validate_collection(key):
                valid_collections.append(key)
            else:
                logger.warning(f"⚠️  集合 {key} 不存在，已跳过")
        return valid_collections

    def _add_item_to_collections(self, item_key: str, collection_keys: List[str]) -> bool:
        """将文献添加到指定的集合"""
        try:
            # 验证推荐集合的有效性
            valid_collections = self._get_valid_collections(collection_keys)
            if not valid_collections:
                logger.error(f"文献 {item_key} 的所有推荐集合都无效")
                return False
            
            # 获取当前集合
            current_collections = self._get_item_collections(item_key)
            logger.info(f"📋 文献 {item_key} 当前集合: {current_collections}")
            
            # 验证当前集合的有效性，但保留所有当前集合（即使无效）
            valid_current_collections = []
            invalid_current_collections = []
            for coll in current_collections:
                if self._validate_collection(coll):
                    valid_current_collections.append(coll)
                else:
                    invalid_current_collections.append(coll)
                    logger.warning(f"⚠️  当前集合 {coll} 不存在，但会保留在更新中")
            
            # 获取版本号
            version = self._get_item_version(item_key)
            if not version:
                logger.error(f"无法获取文献 {item_key} 的版本号")
                return False
            
            # 合并集合（保留所有当前集合，添加新的推荐集合）
            all_collections = list(set(current_collections + valid_collections))
            logger.info(f"📋 合并后的集合: {all_collections}")
            logger.info(f"📋 新增集合: {[c for c in valid_collections if c not in current_collections]}")
            
            # 获取完整的文献数据
            url = f"{self.base_url}/items/{item_key}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            item_data = response.json()
            
            # 更新集合字段（在data子对象中）
            item_data['data']['collections'] = all_collections
            
            # 更新文献
            headers = self.headers.copy()
            headers['If-Unmodified-Since-Version'] = str(version)
            
            response = requests.put(url, headers=headers, json=item_data)
            response.raise_for_status()
            
            new_collections = [c for c in valid_collections if c not in current_collections]
            logger.info(f"✅ 成功更新文献 {item_key}: 添加 {len(new_collections)} 个新集合")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 412:
                logger.error(f"文献 {item_key} 版本冲突，需要重新获取")
            else:
                logger.error(f"更新文献 {item_key} 失败: HTTP {e.response.status_code}")
                logger.error(f"请求URL: {url}")
                logger.error(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"更新文献 {item_key} 失败: {e}")
            return False
    
    def apply_classification(self, plan_file: str, max_items: int = None, test_mode: bool = False) -> bool:
        """应用分类计划"""
        # 加载分类计划
        plan_data = self._load_classification_plan(plan_file)
        if not plan_data:
            return False
        
        classifications = plan_data.get('classifications', [])
        if not classifications:
            logger.error("❌ 分类计划中没有找到分类数据")
            return False
        
        # 筛选成功的分类
        successful_classifications = [
            c for c in classifications 
            if c.get('classification_success', False) and c.get('recommended_collections')
        ]
        
        if not successful_classifications:
            logger.error("❌ 没有找到成功的分类结果")
            return False
        
        # 限制处理数量
        if max_items:
            successful_classifications = successful_classifications[:max_items]
        
        # 测试模式：从末尾开始处理少量数据
        if test_mode:
            test_count = get_default_test_items()
            successful_classifications = successful_classifications[-test_count:]
            logger.info(f"🧪 测试模式：处理最后 {len(successful_classifications)} 篇文献")
        
        self.total_items = len(successful_classifications)
        logger.info(f"📊 开始应用分类: {self.total_items} 篇文献")
        
        # 显示预览
        title_preview_length = get_title_preview_length()
        logger.info("📋 即将应用的分类预览:")
        for i, classification in enumerate(successful_classifications[:5]):
            title = classification.get('title', '')[:title_preview_length]
            collections = classification.get('recommended_collections', [])
            logger.info(f"  {i+1}. {title} -> {collections}")
        
        if len(successful_classifications) > 5:
            logger.info(f"  ... 还有 {len(successful_classifications) - 5} 篇文献")
        
        # 用户确认
        if not test_mode:
            confirm = input(f"\n⚠️  确认要应用分类到 {self.total_items} 篇文献吗？(y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("操作已取消")
                return False
        
        # 应用分类
        logger.info("🚀 开始应用分类...")
        
        for classification in tqdm(successful_classifications, desc="应用进度"):
            item_key = classification.get('item_key', '')
            collection_keys = classification.get('recommended_collections', [])
            
            if not item_key or not collection_keys:
                self.failed_applications += 1
                continue
            
            success = self._add_item_to_collections(item_key, collection_keys)
            if success:
                self.successful_applications += 1
            else:
                self.failed_applications += 1
            
            self.processed_items += 1
            
            # 避免API限制
            time.sleep(0.1)
        
        # 输出统计
        logger.info("📊 应用完成统计:")
        logger.info(f"   总文献数: {self.total_items}")
        logger.info(f"   成功应用: {self.successful_applications}")
        logger.info(f"   应用失败: {self.failed_applications}")
        
        if self.total_items > 0:
            success_rate = self.successful_applications / self.total_items * 100
            logger.info(f"   成功率: {success_rate:.1f}%")
        
        return self.successful_applications > 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="007 - 安全地将分类结果应用到Zotero",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试模式应用
  python 007_apply_classification_to_zotero.py --plan data/classification_plan.json --test
  
  # 全量应用
  python 007_apply_classification_to_zotero.py --plan data/classification_plan.json
  
  # 限制处理数量
  python 007_apply_classification_to_zotero.py --plan data/classification_plan.json --max-items 100

注意事项:
  - 需要配置Zotero API环境变量
  - 建议先使用--test模式测试
  - 只添加新分类，不会删除现有分类
  - 操作不可逆，请谨慎执行
        """
    )
    
    # 文件路径参数（强制要求）
    parser.add_argument('--plan', type=str, required=True, help='分类计划文件路径（JSON格式）')
    
    # 可选参数
    parser.add_argument('--test', action='store_true', help='测试模式（处理少量数据）')
    parser.add_argument('--max-items', type=int, help='最大处理文献数量')
    
    args = parser.parse_args()
    
    # 验证文件存在
    if not os.path.exists(args.plan):
        parser.error(f"分类计划文件不存在: {args.plan}")
            
    # 创建应用器
    applier = ClassificationApplier()
    
    # 执行应用
    success = applier.apply_classification(
        plan_file=args.plan,
        max_items=args.max_items,
        test_mode=args.test
    )
    
    if success:
        print(f"\n✅ 分类应用完成！")
        print(f"📊 成功应用: {applier.successful_applications} 篇文献")
        print(f"📊 应用失败: {applier.failed_applications} 篇文献")
        print(f"\n💡 下一步操作:")
        print(f"  1. 检查Zotero中文献的分类情况")
        print(f"  2. 检查是否有未分类的文献:")
        print(f"     python 006_check_and_export_missing_proper_items.py --output-format excel")
        return 0
    else:
        print("❌ 分类应用失败")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 