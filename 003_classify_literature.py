#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
003 - Classify Literature
使用LLM对文献进行分类，支持多进程并发
"""

import os
import sys
import json
import pandas as pd
import multiprocessing as mp
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import glob
import time

# 导入已有的模块
from llm_client import LLMClient

# 全局LLM客户端配置（用于多进程）
OPENAI_API_KEY = None
OPENAI_BASE_URL = None

def init_worker():
    """工作进程初始化函数"""
    global OPENAI_API_KEY, OPENAI_BASE_URL
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')

def classify_single_literature(args):
    """分类单篇文献的工作函数（两阶段分类：主分类->子分类）"""
    literature_info, classification_schema, worker_id, classifier_instance = args
    
    try:
        # 在工作进程中创建LLM客户端
        llm = LLMClient(
            model_name="gpt-4.1",
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        
        # 构建所有分类的key映射
        all_collections_map = build_collections_key_map(classification_schema)
        
        # 第一阶段：选择主分类
        main_categories_prompt = build_main_classification_prompt(literature_info, classification_schema)
        
        main_response = llm.generate(
            prompt=main_categories_prompt,
            temperature=0.3,
            max_tokens=800
        )
        
        main_content = main_response.get('content', '').strip()
        
        try:
            main_result = json.loads(main_content)
            selected_main_keys = main_result.get('selected_main_categories', [])
            
            # 验证主分类key的有效性
            valid_main_keys = validate_collection_keys(selected_main_keys, classification_schema, 'main', 
                                                      classifier=classifier_instance)
            
            if not valid_main_keys:
                return {
                    'success': False,
                    'item_key': literature_info['item_key'],
                    'title': literature_info['title'],
                    'worker_id': worker_id,
                    'error': '未选择有效的主分类',
                    'main_response': main_content
                }
            
        except json.JSONDecodeError:
            return {
                'success': False,
                'item_key': literature_info['item_key'],
                'title': literature_info['title'],
                'worker_id': worker_id,
                'error': '主分类JSON解析失败',
                'main_response': main_content
            }
        
        # 第二阶段：为每个选定的主分类选择子分类
        final_collection_keys = []
        sub_responses = []
        
        for main_key in valid_main_keys:
            # 构建子分类选择提示词
            sub_prompt = build_sub_classification_prompt(literature_info, classification_schema, main_key)
            
            sub_response = llm.generate(
                prompt=sub_prompt,
                temperature=0.3,
                max_tokens=600
            )
            
            sub_content = sub_response.get('content', '').strip()
            sub_responses.append(sub_content)
            
            try:
                sub_result = json.loads(sub_content)
                selected_sub_keys = sub_result.get('selected_subcategories', [])
                
                # 验证子分类key的有效性
                valid_sub_keys = validate_collection_keys(selected_sub_keys, classification_schema, 'sub', 
                                                         main_key, classifier=classifier_instance)
                
                # 如果没有合适的子分类，就使用主分类本身
                if valid_sub_keys:
                    final_collection_keys.extend(valid_sub_keys)
                else:
                    final_collection_keys.append(main_key)
                    
            except json.JSONDecodeError:
                # 如果子分类解析失败，使用主分类
                final_collection_keys.append(main_key)
        
        # 去重
        final_collection_keys = list(set(final_collection_keys))
        
        # 将key转换为名称用于显示
        collection_names = [all_collections_map.get(key, key) for key in final_collection_keys]
        
        return {
            'success': True,
            'item_key': literature_info['item_key'],
            'title': literature_info['title'],
            'worker_id': worker_id,
            'recommended_collection_keys': final_collection_keys,
            'recommended_collections': collection_names,
            'main_analysis': main_result.get('analysis', ''),
            'main_response': main_content,
            'sub_responses': sub_responses
        }
        
    except Exception as e:
        return {
            'success': False,
            'item_key': literature_info['item_key'],
            'title': literature_info['title'],
            'worker_id': worker_id,
            'error': str(e),
            'main_response': '',
            'sub_responses': []
        }

def build_collections_key_map(classification_schema: Dict[str, Any]) -> Dict[str, str]:
    """构建分类key到名称的映射"""
    key_map = {}
    
    # 主分类
    main_categories = classification_schema.get('main_categories', {})
    for main_cat_name, main_cat_info in main_categories.items():
        key = main_cat_info.get('collection_key', '')
        if key:
            key_map[key] = main_cat_name
        
        # 子分类
        for sub_cat in main_cat_info.get('subcategories', []):
            sub_key = sub_cat.get('collection_key', '')
            if sub_key:
                key_map[sub_key] = sub_cat['name']
    
    # 独立分类
    independent_categories = classification_schema.get('independent_categories', {})
    for indep_cat_name, indep_cat_info in independent_categories.items():
        key = indep_cat_info.get('collection_key', '')
        if key:
            key_map[key] = indep_cat_name
    
    return key_map

def validate_collection_keys(keys: List[str], classification_schema: Dict[str, Any], 
                           category_type: str, main_key: str = None, classifier=None) -> List[str]:
    """验证分类key的有效性，支持名称到key的自动转换"""
    
    # 如果提供了classifier实例，尝试将名称转换为keys
    converted_keys = keys
    if classifier and hasattr(classifier, 'convert_names_to_keys'):
        converted_keys = classifier.convert_names_to_keys(keys)
    
    valid_keys = []
    
    if category_type == 'main':
        # 验证主分类key
        main_categories = classification_schema.get('main_categories', {})
        independent_categories = classification_schema.get('independent_categories', {})
        
        valid_main_keys = set()
        for main_cat_info in main_categories.values():
            if main_cat_info.get('collection_key'):
                valid_main_keys.add(main_cat_info['collection_key'])
        
        for indep_cat_info in independent_categories.values():
            if indep_cat_info.get('collection_key'):
                valid_main_keys.add(indep_cat_info['collection_key'])
        
        for key in converted_keys:
            if key in valid_main_keys:
                valid_keys.append(key)
    
    elif category_type == 'sub' and main_key:
        # 验证子分类key
        main_categories = classification_schema.get('main_categories', {})
        
        valid_sub_keys = set()
        for main_cat_info in main_categories.values():
            if main_cat_info.get('collection_key') == main_key:
                for sub_cat in main_cat_info.get('subcategories', []):
                    if sub_cat.get('collection_key'):
                        valid_sub_keys.add(sub_cat['collection_key'])
                break
        
        for key in converted_keys:
            if key in valid_sub_keys:
                valid_keys.append(key)
    
    return valid_keys

def build_main_classification_prompt(literature_info: Dict[str, Any], classification_schema: Dict[str, Any]) -> str:
    """构建主分类选择提示词"""
    
    # 构建文献信息
    literature_text = build_literature_text(literature_info)
    
    # 构建主分类列表
    main_categories_text = build_main_categories_text(classification_schema)
    
    prompt = f"""你是一个专业的学术文献分类专家。请为以下文献选择合适的主分类。

**任务说明：**
这是分类的第一阶段：从所有主分类中选择最合适的分类。你可以选择多个主分类。

**文献信息：**
{literature_text}

**可选的主分类：**
{main_categories_text}

**分类原则：**
1. **精确匹配**：仔细分析文献内容，选择最匹配的主分类
2. **支持多选**：一篇文献可以同时属于多个主分类
3. **必须选择**：必须至少选择一个主分类
4. **只返回KEY**：只返回[KEY: ]中的collection_key，不要返回分类名称！

**回复格式（严格JSON）：**
{{
    "selected_main_categories": [
        "EXACT_COLLECTION_KEY1",
        "EXACT_COLLECTION_KEY2"
    ],
    "analysis": "分析说明：为什么选择这些主分类，请说明文献内容与所选主分类的匹配点"
}}

⚠️ 重要：只返回[KEY: ]中显示的确切collection_key，不要返回分类名称或其他文字！"""

    return prompt

def build_sub_classification_prompt(literature_info: Dict[str, Any], classification_schema: Dict[str, Any], main_key: str) -> str:
    """构建子分类选择提示词"""
    
    # 获取主分类信息
    main_cat_name, main_cat_info = get_main_category_by_key(classification_schema, main_key)
    
    # 构建子分类列表
    sub_categories_text = build_sub_categories_text(main_cat_info)
    
    prompt = f"""你是一个专业的学术文献分类专家。请为以下文献在指定主分类下选择合适的子分类。

**任务说明：**
这是分类的第二阶段：在主分类"{main_cat_name}"下选择最合适的子分类。你可以选择多个子分类，也可以不选择任何子分类（如果都不合适）。

**文献信息：**
{build_literature_text(literature_info)}

**主分类：{main_cat_name}**
描述：{main_cat_info.get('description', '')}

**可选的子分类：**
{sub_categories_text}

**分类原则：**
1. **精确匹配**：选择与文献内容最匹配的子分类
2. **支持多选**：可以选择多个相关的子分类
3. **可以不选**：如果没有合适的子分类，返回空数组
4. **只返回KEY**：只返回[KEY: ]中的collection_key，不要返回分类名称！

**回复格式（严格JSON）：**
{{
    "selected_subcategories": [
        "EXACT_SUBCATEGORY_KEY1",
        "EXACT_SUBCATEGORY_KEY2"
    ],
    "analysis": "分析说明：为什么选择这些子分类，或为什么不选择任何子分类"
}}

⚠️ 重要：只返回[KEY: ]中显示的确切collection_key，不要返回分类名称或其他文字！"""

    return prompt

def build_main_categories_text(classification_schema: Dict[str, Any]) -> str:
    """构建主分类列表文本"""
    categories_lines = []
    
    # 主分类
    main_categories = classification_schema.get('main_categories', {})
    for main_cat_name, main_cat_info in main_categories.items():
        key = main_cat_info.get('collection_key', '')
        description = main_cat_info.get('description', '')
        categories_lines.append(f"- **[KEY: {key}]** {main_cat_name}")
        categories_lines.append(f"  描述: {description}")
        categories_lines.append("")
    
    # 独立分类也作为主分类
    independent_categories = classification_schema.get('independent_categories', {})
    for indep_cat_name, indep_cat_info in independent_categories.items():
        key = indep_cat_info.get('collection_key', '')
        description = indep_cat_info.get('description', '')
        categories_lines.append(f"- **[KEY: {key}]** {indep_cat_name}")
        categories_lines.append(f"  描述: {description}")
        categories_lines.append("")
    
    return "\n".join(categories_lines)

def build_sub_categories_text(main_cat_info: Dict[str, Any]) -> str:
    """构建子分类列表文本"""
    subcategories = main_cat_info.get('subcategories', [])
    
    if not subcategories:
        return "该主分类下没有子分类。"
    
    categories_lines = []
    for sub_cat in subcategories:
        name = sub_cat.get('name', '')
        key = sub_cat.get('collection_key', '')
        description = sub_cat.get('description', '')
        categories_lines.append(f"- **[KEY: {key}]** {name}")
        categories_lines.append(f"  描述: {description}")
        categories_lines.append("")
    
    return "\n".join(categories_lines)

def get_main_category_by_key(classification_schema: Dict[str, Any], main_key: str) -> tuple:
    """根据key获取主分类信息"""
    # 在主分类中查找
    main_categories = classification_schema.get('main_categories', {})
    for main_cat_name, main_cat_info in main_categories.items():
        if main_cat_info.get('collection_key') == main_key:
            return main_cat_name, main_cat_info
    
    # 在独立分类中查找
    independent_categories = classification_schema.get('independent_categories', {})
    for indep_cat_name, indep_cat_info in independent_categories.items():
        if indep_cat_info.get('collection_key') == main_key:
            return indep_cat_name, indep_cat_info
    
    return f"Unknown({main_key})", {}

def build_literature_text(literature_info: Dict[str, Any]) -> str:
    """构建文献信息文本"""
    info_lines = []
    
    # 基本信息
    info_lines.append(f"📄 标题: {literature_info.get('title', '无标题')}")
    info_lines.append(f"📋 类型: {literature_info.get('item_type', 'unknown')}")
    
    # 作者
    authors = literature_info.get('authors', '')
    if authors:
        info_lines.append(f"👤 作者: {authors}")
    
    # 发表信息
    pub_title = literature_info.get('publication_title', '')
    conf_name = literature_info.get('conference_name', '')
    if pub_title:
        info_lines.append(f"📖 期刊: {pub_title}")
    if conf_name:
        info_lines.append(f"🏛️ 会议: {conf_name}")
    
    # 时间
    date = literature_info.get('date', '')
    if date:
        info_lines.append(f"📅 时间: {date}")
    
    # DOI
    doi = literature_info.get('doi', '')
    if doi:
        info_lines.append(f"🔗 DOI: {doi}")
    
    # 摘要
    abstract = literature_info.get('abstract', '')
    if abstract:
        if hasattr(abstract, '__len__'):
            abstract_preview = abstract[:500] + '...' if len(abstract) > 500 else abstract
        else:
            abstract_preview = str(abstract)
        info_lines.append(f"📝 摘要: {abstract_preview}")
    
    # 标签
    tags = literature_info.get('tags', '')
    if tags:
        info_lines.append(f"🏷️ 标签: {tags}")
    
    # 当前分类状态
    collections_count = literature_info.get('collections_count', 0)
    if collections_count > 0:
        info_lines.append(f"📂 当前分类数: {collections_count}")
    else:
        info_lines.append("📂 当前分类: 无")
    
    return "\n".join(info_lines)

class LiteratureClassifier:
    """文献分类器"""
    
    def __init__(self, max_workers: int = None):
        """初始化分类器"""
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 设置进程数
        if max_workers is None:
            self.max_workers = min(mp.cpu_count(), 16)  # 默认16个进程
        else:
            self.max_workers = max_workers
        
        print(f"🔧 将使用 {self.max_workers} 个进程进行并发分类")
        
        # 检查环境变量
        global OPENAI_API_KEY, OPENAI_BASE_URL
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if not OPENAI_API_KEY:
            print("错误：请设置OPENAI_API_KEY环境变量")
            sys.exit(1)
        
        # 缓存有效的collection keys和名称映射
        self.valid_collection_keys = None
        self.name_to_key_map = None
    
    def load_valid_collection_keys(self, schema: Dict[str, Any]) -> set:
        """从schema中加载所有有效的collection keys和名称映射"""
        if self.valid_collection_keys is not None:
            return self.valid_collection_keys
            
        valid_keys = set()
        name_to_key = {}
        
        # 从主分类中获取keys
        main_categories = schema.get('classification_schema', {}).get('main_categories', {})
        for main_cat_name, main_cat_info in main_categories.items():
            key = main_cat_info.get('collection_key', '')
            if key:
                valid_keys.add(key)
                name_to_key[main_cat_name] = key
            
            # 从子分类中获取keys
            for sub_cat in main_cat_info.get('subcategories', []):
                sub_key = sub_cat.get('collection_key', '')
                sub_name = sub_cat.get('name', '')
                if sub_key:
                    valid_keys.add(sub_key)
                    if sub_name:
                        name_to_key[sub_name] = sub_key
        
        # 从独立分类中获取keys
        independent_categories = schema.get('classification_schema', {}).get('independent_categories', {})
        for indep_cat_name, indep_cat_info in independent_categories.items():
            key = indep_cat_info.get('collection_key', '')
            if key:
                valid_keys.add(key)
                name_to_key[indep_cat_name] = key
        
        self.valid_collection_keys = valid_keys
        self.name_to_key_map = name_to_key
        
        print(f"✅ 已加载 {len(valid_keys)} 个有效分类key")
        print(f"✅ 已建立 {len(name_to_key)} 个名称->key映射")
        
        # 显示前几个有效key样本
        if valid_keys:
            sample_keys = list(valid_keys)[:5]
            print(f"   样本key: {sample_keys}")
        
        # 显示前几个名称映射样本
        if name_to_key:
            sample_mappings = list(name_to_key.items())[:3]
            print(f"   样本映射: {sample_mappings}")
        
        return valid_keys
    
    def convert_names_to_keys(self, items: List[str]) -> List[str]:
        """尝试将分类名称转换为collection keys"""
        if not self.name_to_key_map:
            return items
        
        converted_keys = []
        for item in items:
            # 首先检查是否已经是有效的key
            if item in self.valid_collection_keys:
                converted_keys.append(item)
            # 如果不是key，尝试通过名称映射查找
            elif item in self.name_to_key_map:
                converted_key = self.name_to_key_map[item]
                converted_keys.append(converted_key)
                print(f"   🔄 自动转换: '{item}' → '{converted_key}'")
            else:
                # 既不是有效key也不是已知名称，保持原值
                converted_keys.append(item)
        
        return converted_keys
    
    def count_valid_collections(self, collection_keys_str: str) -> int:
        """计算有效的collection keys数量"""
        if not collection_keys_str or pd.isna(collection_keys_str):
            return 0
            
        if not self.valid_collection_keys:
            return 0
        
        # 分割collection keys字符串（支持多种分隔符）
        str_data = str(collection_keys_str)
        if ';' in str_data:
            keys = [key.strip() for key in str_data.split(';') if key.strip()]
        elif ',' in str_data:
            keys = [key.strip() for key in str_data.split(',') if key.strip()]
        else:
            keys = [str_data.strip()] if str_data.strip() else []
        
        # 计算有效keys数量
        valid_count = 0
        for key in keys:
            if key in self.valid_collection_keys:
                valid_count += 1
        
        # 调试信息（仅在有keys时输出）
        if keys and hasattr(self, '_debug_count') and self._debug_count < 3:
            print(f"   🔍 调试样本: '{collection_keys_str}' → {keys} → 有效数量: {valid_count}")
            self._debug_count += 1
        
        return valid_count
    
    def load_latest_literature_info(self) -> Optional[pd.DataFrame]:
        """加载最新的文献信息"""
        pattern = str(self.data_dir / "literature_info_*.xlsx")
        files = glob.glob(pattern)
        
        if not files:
            print("❌ 未找到文献信息文件，请先运行 001_collect_literature_info.py")
            return None
        
        # 选择最新的文件
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 加载文献信息: {latest_file}")
        
        try:
            df = pd.read_excel(latest_file, engine='openpyxl')
            print(f"✅ 已加载 {len(df)} 篇文献信息")
            return df
        except Exception as e:
            print(f"❌ 加载文献信息失败: {e}")
            return None
    
    def load_latest_classification_schema(self) -> Optional[Dict[str, Any]]:
        """加载最新的分类标准"""
        pattern = str(self.data_dir / "classification_schema_*.json")
        files = glob.glob(pattern)
        
        if not files:
            print("❌ 未找到分类标准文件，请先运行 002_generate_classification_schema.py")
            return None
        
        # 选择最新的文件
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 加载分类标准: {latest_file}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            main_count = len(schema.get('classification_schema', {}).get('main_categories', {}))
            indep_count = len(schema.get('classification_schema', {}).get('independent_categories', {}))
            print(f"✅ 已加载分类标准: {main_count} 个主分类, {indep_count} 个独立分类")
            
            return schema
        except Exception as e:
            print(f"❌ 加载分类标准失败: {e}")
            return None
    
    def filter_literature_for_classification(self, df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
        """筛选需要分类的文献"""
        print("🔍 筛选需要分类的文献...")
        
        # 先加载有效的collection keys
        self.load_valid_collection_keys(schema)
        self._debug_count = 0  # 重置调试计数器
        
        # 检查DataFrame中的字段名
        print("🔍 检查数据字段...")
        print(f"   DataFrame字段: {list(df.columns)}")
        
        # 查找正确的collection keys字段名
        possible_fields = ['collections_keys', 'collection_keys', 'collections', 'collection_names']
        collection_field = None
        for field in possible_fields:
            if field in df.columns:
                collection_field = field
                break
        
        if not collection_field:
            print("⚠️ 未找到collection相关字段，将所有文献视为需要分类")
            valid_counts = pd.Series([0] * len(df))
        else:
            print(f"   使用字段: {collection_field}")
            
            # 分析几个样本数据
            sample_data = df[collection_field].head(3).tolist()
            print(f"   样本数据: {sample_data}")
            
            # 分析现有分类情况
            print("📊 分析现有分类情况...")
            valid_counts = df.apply(lambda row: self.count_valid_collections(row.get(collection_field, '')), axis=1)
        
        no_valid_classifications = (valid_counts == 0).sum()
        one_valid_classification = (valid_counts == 1).sum()  
        two_or_more_valid_classifications = (valid_counts >= 2).sum()
        
        print(f"   无有效分类: {no_valid_classifications} 篇")
        print(f"   1个有效分类: {one_valid_classification} 篇") 
        print(f"   2个或以上有效分类: {two_or_more_valid_classifications} 篇")
        
        # 过滤条件
        if collection_field:
            filtered_df = df[
                # 排除没有标题的
                (df['title'].notna() & (df['title'] != '') & (df['title'] != '无标题')) &
                # 只处理完全没有有效分类的文献
                (valid_counts == 0)
            ].copy()
        else:
            # 如果没有collection字段，只按标题筛选
            filtered_df = df[
                (df['title'].notna() & (df['title'] != '') & (df['title'] != '无标题'))
            ].copy()
        
        print(f"\n📊 筛选结果:")
        print(f"   总文献数: {len(df)}")
        print(f"   待分类文献数: {len(filtered_df)}")
        
        if collection_field:
            skipped_count = one_valid_classification + two_or_more_valid_classifications
            print(f"   已跳过（有效分类>=1）: {skipped_count} 篇")
        else:
            print(f"   无collection字段，仅按标题筛选")
        
        if len(filtered_df) > 0:
            print(f"\n📚 待分类文献类型分布:")
            type_counts = filtered_df['item_type'].value_counts().head(5)
            for item_type, count in type_counts.items():
                print(f"     - {item_type}: {count} 篇")
        
        return filtered_df
    
    def classify_literature_batch(self, literature_df: pd.DataFrame, schema: Dict[str, Any], 
                                 limit: Optional[int] = None, start: int = 0) -> List[Dict[str, Any]]:
        """批量分类文献"""
        
        # 确定处理范围
        total_count = len(literature_df)
        if limit is None:
            limit = total_count
        
        end_index = min(start + limit, total_count)
        selected_df = literature_df.iloc[start:end_index]
        
        print(f"🚀 开始分类文献:")
        print(f"   处理范围: 第 {start+1} 到第 {end_index} 篇")
        print(f"   总数: {len(selected_df)} 篇")
        print(f"   并发进程: {self.max_workers} 个")
        
        # 准备任务数据
        tasks = []
        for idx, row in selected_df.iterrows():
            literature_info = row.to_dict()
            tasks.append((literature_info, schema['classification_schema'], idx % self.max_workers, self))
        
        # 多进程执行
        results = []
        
        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=init_worker
        ) as executor:
            
            # 提交所有任务
            future_to_task = {
                executor.submit(classify_single_literature, task): i 
                for i, task in enumerate(tasks)
            }
            
            # 收集结果
            with tqdm(total=len(tasks), desc="两阶段分类进度", unit="篇") as pbar:
                for future in as_completed(future_to_task):
                    try:
                        result = future.result()
                        results.append(result)
                        pbar.update(1)
                        
                        # 显示进度信息
                        if result['success']:
                            recommended = result.get('recommended_collections', [])
                            if recommended:
                                pbar.set_postfix_str(f"最新: {result['title'][:15]}... → {len(recommended)}个分类")
                        else:
                            pbar.set_postfix_str(f"失败: {result.get('error', 'Unknown')}")
                        
                    except Exception as e:
                        task_idx = future_to_task[future]
                        task_info = tasks[task_idx]
                        results.append({
                            'success': False,
                            'item_key': task_info[0].get('item_key', ''),
                            'title': task_info[0].get('title', ''),
                            'worker_id': task_info[2],
                            'error': f'任务执行失败: {str(e)}',
                            'main_response': '',
                            'sub_responses': []
                        })
                        pbar.update(1)
        
        return results
    
    def save_classification_results(self, results: List[Dict[str, Any]], 
                                  literature_df: pd.DataFrame) -> str:
        """保存分类结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"classification_results_{timestamp}.xlsx"
        filepath = self.data_dir / filename
        
        print(f"💾 正在保存分类结果到 {filepath}...")
        
        # 构建结果DataFrame
        result_data = []
        
        for result in results:
            item_key = result['item_key']
            
            # 从原始文献信息中获取完整信息
            literature_row = literature_df[literature_df['item_key'] == item_key]
            if not literature_row.empty:
                lit_info = literature_row.iloc[0].to_dict()
            else:
                lit_info = {}
            
            # 构建结果行
            result_row = {
                'item_key': item_key,
                'title': result['title'],
                'item_type': lit_info.get('item_type', ''),
                'authors': lit_info.get('authors', ''),
                'publication_title': lit_info.get('publication_title', ''),
                'date': lit_info.get('date', ''),
                'doi': lit_info.get('doi', ''),
                'abstract': lit_info.get('abstract', ''),
                'current_collections_count': lit_info.get('collections_count', 0),
                'classification_success': result['success'],
                'recommended_collection_keys': '; '.join(result.get('recommended_collection_keys', [])) if result['success'] else '',
                'recommended_collections': '; '.join(result.get('recommended_collections', [])) if result['success'] else '',
                'recommended_count': len(result.get('recommended_collections', [])) if result['success'] and result.get('recommended_collections') else 0,
                'main_analysis': result.get('main_analysis', ''),
                'error_message': result.get('error', ''),
                'worker_id': result.get('worker_id', ''),
                'main_response': result.get('main_response', ''),
                'sub_responses_count': len(result.get('sub_responses', [])) if result['success'] and result.get('sub_responses') else 0
            }
            
            result_data.append(result_row)
        
        # 保存到Excel
        result_df = pd.DataFrame(result_data)
        result_df.to_excel(filepath, index=False, engine='openpyxl')
        
        # 显示统计信息
        successful_results = result_df[result_df['classification_success'] == True]
        failed_results = result_df[result_df['classification_success'] == False]
        
        print(f"\n📊 两阶段分类结果统计:")
        print(f"   ✅ 成功分类: {len(successful_results)} 篇")
        print(f"   ❌ 分类失败: {len(failed_results)} 篇")
        
        if len(successful_results) > 0:
            print(f"   📂 平均推荐分类数: {successful_results['recommended_count'].mean():.1f}")
            print(f"   🔄 平均子分类响应数: {successful_results['sub_responses_count'].mean():.1f}")
            
            # 统计推荐分类
            all_recommended_keys = []
            all_recommended_names = []
            for keys, names in zip(successful_results['recommended_collection_keys'], 
                                 successful_results['recommended_collections']):
                if keys:
                    all_recommended_keys.extend([key.strip() for key in keys.split(';')])
                if names:
                    all_recommended_names.extend([name.strip() for name in names.split(';')])
            
            if all_recommended_names:
                from collections import Counter
                category_counts = Counter(all_recommended_names)
                print(f"\n📂 热门推荐分类:")
                for category, count in category_counts.most_common(10):
                    print(f"     - {category}: {count} 篇")
            
            print(f"\n🔑 使用的分类key总数: {len(set(all_recommended_keys))}")
        
        if len(failed_results) > 0:
            print(f"\n❌ 失败原因统计:")
            error_counts = failed_results['error_message'].value_counts()
            for error, count in error_counts.head(5).items():
                print(f"     - {error}: {count} 篇")
        
        print(f"\n✅ 分类结果已保存到: {filepath}")
        return str(filepath)
    
    def classify_and_save(self, limit: Optional[int] = None, start: int = 0) -> str:
        """执行分类并保存结果"""
        print("🚀 开始文献分类任务...")
        
        # 加载数据
        literature_df = self.load_latest_literature_info()
        if literature_df is None:
            return ""
        
        schema = self.load_latest_classification_schema()
        if schema is None:
            return ""
        
        # 筛选需要分类的文献
        filtered_df = self.filter_literature_for_classification(literature_df, schema)
        if len(filtered_df) == 0:
            print("✅ 没有需要分类的文献")
            return ""
        
        # 执行分类
        results = self.classify_literature_batch(filtered_df, schema, limit, start)
        
        # 保存结果
        result_file = self.save_classification_results(results, literature_df)
        
        return result_file


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 Zotero文献智能分类工具 - 003")
    print("=" * 60)
    
    # 检查环境变量
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("\n请设置以下环境变量：")
        print("export OPENAI_API_KEY='你的OpenAI API密钥'")
        print("export OPENAI_BASE_URL='你的OpenAI Base URL' (可选)")
        return 1
    
    # 解析命令行参数
    limit = None
    start = 0
    max_workers = None
    
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
    
    try:
        # 创建分类器
        classifier = LiteratureClassifier(max_workers=max_workers)
        
        # 执行分类
        if limit is not None:
            print(f"📋 将分类 {limit} 篇文献，从第 {start+1} 篇开始")
        else:
            print(f"📋 将分类所有文献，从第 {start+1} 篇开始")
        
        result_file = classifier.classify_and_save(limit=limit, start=start)
        
        if result_file:
            print(f"\n🎉 分类完成！")
            print(f"📁 结果文件: {result_file}")
            print(f"\n💡 下一步:")
            print(f"   1. 检查分类结果文件")
            print(f"   2. 运行: python 004_apply_classification.py")
        else:
            print("❌ 分类失败")
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