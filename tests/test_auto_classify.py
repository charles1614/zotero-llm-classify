#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试自动分类功能
"""

import os
from auto_classify import ZoteroAutoClassifier

def quick_test():
    """快速测试分类功能"""
    print("🧪 Zotero自动分类功能测试")
    print("=" * 40)
    
    # 检查环境变量
    required_vars = ['ZOTERO_USER_ID', 'ZOTERO_API_KEY', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        return
    
    try:
        # 创建分类器
        classifier = ZoteroAutoClassifier()
        
        # 只测试单篇分类
        print("\n🔍 测试单篇文献分类...")
        
        # 获取需要分类的文献
        all_items = classifier._get_all_literature_items()
        items_to_classify = classifier._filter_items_for_classification(all_items, verbose=False)
        
        if not items_to_classify:
            print("✅ 没有需要分类的文献")
            return
        
        # 测试第一篇文献
        first_item = items_to_classify[0]
        paper_info = classifier._extract_paper_info(first_item)
        
        print(f"\n📄 测试文献: {paper_info['title'][:50]}...")
        print(f"📝 类型: {paper_info['item_type']}")
        
        # 调用分类
        result = classifier.classify_paper(first_item)
        
        if result['success']:
            classification = result['classification']
            
            print(f"\n✅ 分类成功!")
            
            # 显示推荐分类
            recommended = classification.get('recommended_collections', [])
            if recommended:
                print(f"\n🎯 推荐分类:")
                for rec in recommended:
                    print(f"   - {rec['name']} (置信度: {rec.get('confidence', 0):.2f})")
                    print(f"     理由: {rec.get('reason', '无')}")
            
            # 显示建议新分类
            suggested = classification.get('suggested_new_collections', [])
            if suggested:
                print(f"\n💡 建议新分类:")
                for sug in suggested:
                    print(f"   - {sug['name']} (置信度: {sug.get('confidence', 0):.2f})")
                    print(f"     理由: {sug.get('reason', '无')}")
            
            # 显示分析
            analysis = classification.get('analysis', '')
            if analysis:
                print(f"\n📊 分析: {analysis}")
            
            print(f"\n🎉 测试完成！分类功能正常工作。")
            
        else:
            print(f"❌ 分类失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test() 