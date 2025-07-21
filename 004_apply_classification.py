#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
004 - Apply Classification
批量应用分类结果到Zotero，支持多进程并发
"""

import os
import sys
import json
import pandas as pd
import multiprocessing as mp
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import glob
import time
import threading
import queue

# 导入已有的模块
from main import ZoteroManager

# 全局Zotero配置（用于多进程）
ZOTERO_USER_ID = None
ZOTERO_API_KEY = None

# 全局锁用于防止API限制
api_lock = threading.Lock()

def init_worker():
    """工作进程初始化函数"""
    global ZOTERO_USER_ID, ZOTERO_API_KEY
    ZOTERO_USER_ID = os.getenv('ZOTERO_USER_ID')
    ZOTERO_API_KEY = os.getenv('ZOTERO_API_KEY')

def apply_single_classification(args):
    """应用单篇文献分类的工作函数"""
    classification_row, worker_id, rate_limit_delay = args
    
    try:
        # 在工作进程中创建Zotero客户端
        zotero = ZoteroManager(ZOTERO_USER_ID, ZOTERO_API_KEY)
        
        # 解析推荐分类keys
        item_key = classification_row['item_key']
        recommended_collection_keys_str = classification_row.get('recommended_collection_keys', '')
        
        if not recommended_collection_keys_str or pd.isna(recommended_collection_keys_str):
            return {
                'success': False,
                'item_key': item_key,
                'title': classification_row.get('title', ''),
                'worker_id': worker_id,
                'error': '没有推荐分类keys',
                'applied_collections': []
            }
        
        # 分割推荐分类keys
        recommended_collection_keys = [key.strip() for key in recommended_collection_keys_str.split(';') if key.strip()]
        
        if not recommended_collection_keys:
            return {
                'success': False,
                'item_key': item_key,
                'title': classification_row.get('title', ''),
                'worker_id': worker_id,
                'error': '推荐分类keys为空',
                'applied_collections': []
            }
        
        # 应用分类
        applied_collections = []
        failed_collections = []
        
        for collection_key in recommended_collection_keys:
            
            # 添加速率限制延迟
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
            
            # 尝试添加到分类
            try:
                success = zotero.add_item_to_collection(item_key, collection_key)
                if success:
                    applied_collections.append(collection_key)
                else:
                    failed_collections.append(f"{collection_key}(API失败)")
                    
            except Exception as e:
                failed_collections.append(f"{collection_key}(异常: {str(e)})")
        
        return {
            'success': len(applied_collections) > 0,
            'item_key': item_key,
            'title': classification_row.get('title', ''),
            'worker_id': worker_id,
            'applied_collections': applied_collections,
            'failed_collections': failed_collections,
            'error': '; '.join(failed_collections) if failed_collections else ''
        }
        
    except Exception as e:
        return {
            'success': False,
            'item_key': classification_row.get('item_key', ''),
            'title': classification_row.get('title', ''),
            'worker_id': worker_id,
            'error': f'处理异常: {str(e)}',
            'applied_collections': [],
            'failed_collections': []
        }

class ClassificationApplier:
    """分类应用器"""
    
    def __init__(self, max_workers: int = None, rate_limit_delay: float = 0.1):
        """初始化应用器"""
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 设置进程数
        if max_workers is None:
            # API调用比CPU密集任务需要更少的进程
            self.max_workers = min(mp.cpu_count() // 2, 4)  # 最多4个进程
        else:
            self.max_workers = max_workers
        
        # API速率限制延迟（秒）
        self.rate_limit_delay = rate_limit_delay
        
        print(f"🔧 将使用 {self.max_workers} 个进程进行并发应用")
        print(f"⏱️ API速率限制延迟: {self.rate_limit_delay}秒")
        
        # 检查环境变量
        global ZOTERO_USER_ID, ZOTERO_API_KEY
        ZOTERO_USER_ID = os.getenv('ZOTERO_USER_ID')
        ZOTERO_API_KEY = os.getenv('ZOTERO_API_KEY')
        
        if not ZOTERO_USER_ID or not ZOTERO_API_KEY:
            print("错误：请设置ZOTERO_USER_ID和ZOTERO_API_KEY环境变量")
            sys.exit(1)
        
        # 创建Zotero客户端
        self.zotero = ZoteroManager(ZOTERO_USER_ID, ZOTERO_API_KEY)
    

    def load_latest_classification_results(self) -> Optional[pd.DataFrame]:
        """加载最新的分类结果"""
        pattern = str(self.data_dir / "classification_results_*.xlsx")
        files = glob.glob(pattern)
        
        if not files:
            print("❌ 未找到分类结果文件，请先运行 003_classify_literature.py")
            return None
        
        # 选择最新的文件
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 加载分类结果: {latest_file}")
        
        try:
            df = pd.read_excel(latest_file, engine='openpyxl')
            print(f"✅ 已加载 {len(df)} 条分类结果")
            return df
        except Exception as e:
            print(f"❌ 加载分类结果失败: {e}")
            return None
    
    def filter_results_for_application(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选需要应用的分类结果"""
        print("🔍 筛选需要应用的分类结果...")
        
        # 筛选成功分类且有推荐分类keys的结果
        filtered_df = df[
            (df['classification_success'] == True) &
            (df['recommended_collection_keys'].notna()) &
            (df['recommended_collection_keys'] != '') &
            (df['recommended_count'] > 0)
        ].copy()
        
        print(f"📊 筛选结果:")
        print(f"   总结果数: {len(df)}")
        print(f"   成功分类数: {len(df[df['classification_success'] == True])}")
        print(f"   有推荐分类keys数: {len(filtered_df)}")
        
        if len(filtered_df) > 0:
            print(f"   平均推荐分类数: {filtered_df['recommended_count'].mean():.1f}")
            
            # 统计推荐分类
            all_recommended = []
            for recommendations in filtered_df['recommended_collections']:
                if recommendations:
                    all_recommended.extend([cat.strip() for cat in recommendations.split(';')])
            
            if all_recommended:
                from collections import Counter
                category_counts = Counter(all_recommended)
                print(f"\n📂 即将应用的分类统计:")
                for category, count in category_counts.most_common(10):
                    print(f"     - {category}: {count} 篇")
        
        return filtered_df
    
    def apply_classifications_batch(self, results_df: pd.DataFrame, 
                                  limit: Optional[int] = None, start: int = 0) -> List[Dict[str, Any]]:
        """批量应用分类"""
        
        # 确定处理范围
        total_count = len(results_df)
        if limit is None:
            limit = total_count
        
        end_index = min(start + limit, total_count)
        selected_df = results_df.iloc[start:end_index]
        
        print(f"🚀 开始应用分类:")
        print(f"   处理范围: 第 {start+1} 到第 {end_index} 条结果")
        print(f"   总数: {len(selected_df)} 条")
        print(f"   并发进程: {self.max_workers} 个")
        
        # 准备任务数据
        tasks = []
        for idx, row in selected_df.iterrows():
            tasks.append((row, idx % self.max_workers, self.rate_limit_delay))
        
        # 多进程执行
        results = []
        
        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=init_worker
        ) as executor:
            
            # 提交所有任务
            future_to_task = {
                executor.submit(apply_single_classification, task): i 
                for i, task in enumerate(tasks)
            }
            
            # 收集结果
            with tqdm(total=len(tasks), desc="应用进度", unit="条") as pbar:
                for future in as_completed(future_to_task):
                    try:
                        result = future.result()
                        results.append(result)
                        pbar.update(1)
                        
                        # 显示进度信息
                        if result['success']:
                            applied_count = len(result.get('applied_collections', []))
                            if applied_count > 0:
                                pbar.set_postfix_str(f"最新: {result['title'][:20]}... → {applied_count}个分类")
                        
                    except Exception as e:
                        task_idx = future_to_task[future]
                        task_info = tasks[task_idx]
                        results.append({
                            'success': False,
                            'item_key': task_info[0].get('item_key', ''),
                            'title': task_info[0].get('title', ''),
                            'worker_id': task_info[2],
                            'error': f'任务执行失败: {str(e)}',
                            'applied_collections': [],
                            'failed_collections': []
                        })
                        pbar.update(1)
        
        return results
    
    def save_application_results(self, results: List[Dict[str, Any]], 
                               original_df: pd.DataFrame) -> str:
        """保存应用结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"application_results_{timestamp}.xlsx"
        filepath = self.data_dir / filename
        
        print(f"💾 正在保存应用结果到 {filepath}...")
        
        # 构建结果DataFrame
        result_data = []
        
        for result in results:
            item_key = result['item_key']
            
            # 从原始分类结果中获取完整信息
            original_row = original_df[original_df['item_key'] == item_key]
            if not original_row.empty:
                original_info = original_row.iloc[0].to_dict()
            else:
                original_info = {}
            
            # 构建结果行
            result_row = {
                'item_key': item_key,
                'title': result['title'],
                'item_type': original_info.get('item_type', ''),
                'authors': original_info.get('authors', ''),
                'recommended_collections': original_info.get('recommended_collections', ''),
                'recommended_count': original_info.get('recommended_count', 0),
                'application_success': result['success'],
                'applied_collections': '; '.join(result.get('applied_collections', [])),
                'applied_count': len(result.get('applied_collections', [])),
                'failed_collections': '; '.join(result.get('failed_collections', [])),
                'failed_count': len(result.get('failed_collections', [])),
                'error_message': result.get('error', ''),
                'worker_id': result.get('worker_id', ''),
                'analysis': original_info.get('analysis', '')
            }
            
            result_data.append(result_row)
        
        # 保存到Excel
        result_df = pd.DataFrame(result_data)
        result_df.to_excel(filepath, index=False, engine='openpyxl')
        
        # 显示统计信息
        successful_results = result_df[result_df['application_success'] == True]
        failed_results = result_df[result_df['application_success'] == False]
        
        print(f"\n📊 应用结果统计:")
        print(f"   ✅ 成功应用: {len(successful_results)} 篇")
        print(f"   ❌ 应用失败: {len(failed_results)} 篇")
        
        if len(successful_results) > 0:
            total_applied = successful_results['applied_count'].sum()
            print(f"   📂 总共应用分类: {total_applied} 个")
            print(f"   📂 平均每篇分类数: {successful_results['applied_count'].mean():.1f}")
            
            # 统计应用的分类
            all_applied = []
            for applications in successful_results['applied_collections']:
                if applications:
                    all_applied.extend([cat.strip() for cat in applications.split(';')])
            
            if all_applied:
                from collections import Counter
                category_counts = Counter(all_applied)
                print(f"\n📂 已应用分类统计:")
                for category, count in category_counts.most_common(10):
                    print(f"     - {category}: {count} 篇")
        
        if len(failed_results) > 0:
            print(f"\n❌ 失败原因统计:")
            error_counts = failed_results['error_message'].value_counts()
            for error, count in error_counts.head(5).items():
                print(f"     - {error}: {count} 篇")
        
        print(f"\n✅ 应用结果已保存到: {filepath}")
        return str(filepath)
    
    def apply_and_save(self, limit: Optional[int] = None, start: int = 0) -> str:
        """执行应用并保存结果"""
        print("🚀 开始分类应用任务...")
        
        # 加载分类结果
        results_df = self.load_latest_classification_results()
        if results_df is None:
            return ""
        
        # 筛选需要应用的结果
        filtered_df = self.filter_results_for_application(results_df)
        if len(filtered_df) == 0:
            print("✅ 没有需要应用的分类结果")
            return ""
        
        # 执行应用
        application_results = self.apply_classifications_batch(filtered_df, limit, start)
        
        # 保存结果
        result_file = self.save_application_results(application_results, results_df)
        
        return result_file


def main():
    """主函数"""
    print("=" * 60)
    print("🔗 Zotero分类应用工具 - 004")
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
    
    # 解析命令行参数
    limit = None
    start = 0
    max_workers = None
    rate_limit_delay = 0.1
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("❌ 无效的限制数量参数")
            return 1
    
    if len(sys.argv) > 2:
        try:
            start = int(sys.argv[2])
        except ValueError:
            print("❌ 无效的起始位置参数")
            return 1
    
    if len(sys.argv) > 3:
        try:
            max_workers = int(sys.argv[3])
        except ValueError:
            print("❌ 无效的进程数参数")
            return 1
    
    if len(sys.argv) > 4:
        try:
            rate_limit_delay = float(sys.argv[4])
        except ValueError:
            print("❌ 无效的延迟参数")
            return 1
    
    try:
        # 创建应用器
        applier = ClassificationApplier(max_workers=max_workers, rate_limit_delay=rate_limit_delay)
        
        # 获取预览信息
        print("\n🔍 正在分析分类结果...")
        
        # 加载分类结果
        results_df = applier.load_latest_classification_results()
        if results_df is None:
            print("❌ 无法加载分类结果")
            return 1
        
        # 筛选需要应用的结果
        filtered_df = applier.filter_results_for_application(results_df)
        if len(filtered_df) == 0:
            print("✅ 没有需要应用的分类结果")
            return 0
        
        # 计算实际处理范围
        total_count = len(filtered_df)
        if limit is None:
            actual_limit = total_count
            end_index = total_count
        else:
            actual_limit = min(limit, total_count - start)
            end_index = min(start + limit, total_count)
        
        if start >= total_count:
            print(f"❌ 起始位置 ({start+1}) 超出总数量 ({total_count})")
            return 1
        
        # 获取实际要处理的数据
        process_df = filtered_df.iloc[start:end_index]
        
        # 统计即将应用的分类信息
        total_classifications = 0
        classification_stats = {}
        
        for _, row in process_df.iterrows():
            recommended_collection_keys_str = row.get('recommended_collection_keys', '')
            if recommended_collection_keys_str and not pd.isna(recommended_collection_keys_str):
                recommended_collection_keys = [key.strip() for key in recommended_collection_keys_str.split(';') if key.strip()]
                total_classifications += len(recommended_collection_keys)
                
                for key in recommended_collection_keys:
                    classification_stats[key] = classification_stats.get(key, 0) + 1
        
        # 显示预览信息
        print(f"\n📊 即将执行的分类应用预览:")
        print(f"   📁 总分类结果: {len(results_df)} 条")
        print(f"   ✅ 可应用结果: {total_count} 条")
        print(f"   🎯 本次处理: {len(process_df)} 篇文献")
        print(f"   🏷️ 总分类操作: {total_classifications} 个")
        print(f"   📍 处理范围: 第 {start+1} 到第 {end_index} 条")
        
        if classification_stats:
            print(f"\n🔑 即将应用的分类keys（Top 10）:")
            from collections import Counter
            sorted_stats = Counter(classification_stats).most_common(10)
            for collection_key, count in sorted_stats:
                print(f"     - {collection_key}: {count} 篇")
        
        # 确认操作
        confirm = input(f"\n⚠️ 确认要开始应用分类到Zotero吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 操作已取消")
            return 0
        
        # 直接使用已筛选的数据进行处理，避免重复加载
        application_results = applier.apply_classifications_batch(process_df, None, 0)
        result_file = applier.save_application_results(application_results, results_df)
        
        if result_file:
            print(f"\n🎉 分类应用完成！")
            print(f"📁 结果文件: {result_file}")
            print(f"\n💡 注意事项:")
            print(f"   - 请检查Zotero中的分类是否正确应用")
            print(f"   - 如有问题可以根据结果文件进行调整")
        else:
            print("❌ 应用失败")
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