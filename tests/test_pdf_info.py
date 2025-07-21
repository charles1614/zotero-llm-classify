#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：检查PDF文件在Zotero中的可用信息
"""

import os
import json
from main import ZoteroManager

def test_pdf_info():
    """测试PDF文件信息"""
    print("🔍 PDF文件信息测试")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('ZOTERO_USER_ID') or not os.getenv('ZOTERO_API_KEY'):
        print("❌ 请设置ZOTERO_USER_ID和ZOTERO_API_KEY环境变量")
        return
    
    try:
        # 创建Zotero管理器
        zotero = ZoteroManager()
        
        # 获取所有文献
        print("📚 正在获取文献列表...")
        all_items = []
        start = 0
        limit = 100
        
        while True:
            items = zotero.get_items(limit=limit, start=start)
            if not items:
                break
            all_items.extend(items)
            start += limit
            print(f"已获取 {len(all_items)} 项...")
        
        print(f"总共获取了 {len(all_items)} 项")
        
        # 筛选PDF文件（重点：只关注独立PDF）
        all_pdf_items = []
        independent_pdf_items = []  # 🎯 这才是我们要分类的
        attachment_items = []
        
        for item in all_items:
            data = item['data']
            item_type = data.get('itemType', '')
            
            if item_type == 'attachment':
                attachment_items.append(item)
                
                # 检查是否是PDF
                filename = data.get('filename', '')
                content_type = data.get('contentType', '')
                
                if (filename.lower().endswith('.pdf') or 
                    'pdf' in content_type.lower()):
                    all_pdf_items.append(item)
                    
                    # 🎯 按照auto_classify.py逻辑：只有独立PDF才需要分类
                    if not data.get('parentItem'):
                        independent_pdf_items.append(item)
        
        print(f"\n📎 找到 {len(attachment_items)} 个附件")
        print(f"📄 其中 {len(all_pdf_items)} 个是PDF文件")
        print(f"🎯 其中 {len(independent_pdf_items)} 个是独立PDF（需要分类的）")
        
        if not independent_pdf_items:
            print("❌ 没有找到独立PDF文件")
            if all_pdf_items:
                print("ℹ️ 所有PDF都有父项目，不需要分类")
            return
        
        # 🎯 重点分析独立PDF文件
        print(f"\n🔬 分析前 {min(5, len(independent_pdf_items))} 个独立PDF文件的信息：")
        print("=" * 60)
        
        for i, item in enumerate(independent_pdf_items[:5]):
            data = item['data']
            print(f"\n📄 PDF文件 {i+1}:")
            print("-" * 30)
            
            # 显示所有可用字段
            for key, value in data.items():
                if value:  # 只显示非空值
                    if isinstance(value, str) and len(value) > 100:
                        print(f"{key}: {value[:100]}...")
                    else:
                        print(f"{key}: {value}")
            
            print(f"\n🔍 关键信息分析:")
            title = data.get('title', '')
            filename = data.get('filename', '')
            parent_item = data.get('parentItem', '')
            content_type = data.get('contentType', '')
            url = data.get('url', '')
            
            print(f"  - 有标题: {'✅' if title else '❌'} {title[:50] if title else ''}")
            print(f"  - 有文件名: {'✅' if filename else '❌'} {filename}")
            print(f"  - 有父项目: {'✅' if parent_item else '❌'} {parent_item}")
            print(f"  - 内容类型: {content_type}")
            print(f"  - 有URL: {'✅' if url else '❌'}")
            print(f"  - 有摘要: {'✅' if data.get('abstractNote') else '❌'}")
            print(f"  - 有作者: {'✅' if data.get('creators') else '❌'}")
            print(f"  - 有标签: {'✅' if data.get('tags') else '❌'}")
            
            # 检查是否是独立PDF
            is_independent = not parent_item
            print(f"  - 独立PDF: {'✅' if is_independent else '❌'}")
            
            # 如果有父项目，获取父项目信息
            if parent_item:
                try:
                    parent = zotero.get_item_detail(parent_item)
                    if parent:
                        parent_data = parent.get('data', {})
                        parent_title = parent_data.get('title', '')
                        print(f"  - 父项目标题: {parent_title[:50] if parent_title else '无'}")
                except:
                    print(f"  - 父项目: 无法获取详情")
        
        # 🎯 独立PDF统计分析（这些才需要分类）
        print(f"\n📊 独立PDF统计分析（需要分类的）:")
        print("=" * 30)
        
        pdfs_with_title = []
        pdfs_with_filename_only = []
        pdfs_with_no_info = []
        
        for item in independent_pdf_items:
            data = item['data']
            title = data.get('title', '')
            filename = data.get('filename', '')
            
            if title and title != 'PDF':  # 排除默认标题
                pdfs_with_title.append(item)
            elif filename:
                pdfs_with_filename_only.append(item)
            else:
                pdfs_with_no_info.append(item)
        
        print(f"📈 总独立PDF: {len(independent_pdf_items)} 个")
        print(f"📈 有完整标题: {len(pdfs_with_title)} 个")
        print(f"📈 只有文件名: {len(pdfs_with_filename_only)} 个")
        print(f"📈 信息不足: {len(pdfs_with_no_info)} 个")
        
        # 额外统计所有PDF的分布
        total_dependent = len(all_pdf_items) - len(independent_pdf_items)
        print(f"\nℹ️ 总体PDF分布:")
        print(f"   - 独立PDF（需分类）: {len(independent_pdf_items)} 个")
        print(f"   - 依附PDF（跳过）: {total_dependent} 个")
        
        # 🎯 详细分析可分类的独立PDF
        if independent_pdf_items:
            print(f"\n🎯 可分类独立PDF详细分析（前3个）:")
            for i, item in enumerate(independent_pdf_items[:3]):
                data = item['data']
                print(f"\n独立PDF {i+1}:")
                title = data.get('title', '')
                filename = data.get('filename', '')
                
                if title:
                    print(f"  标题: {title}")
                elif filename:
                    # 尝试从文件名提取信息
                    clean_name = filename.replace('.pdf', '').replace('.PDF', '').replace('_', ' ').replace('-', ' ')
                    print(f"  文件名: {filename}")
                    print(f"  清理后: {clean_name}")
                    
                    # 检查文件名是否包含有用信息
                    if any(keyword in clean_name.lower() for keyword in 
                           ['attention', 'transformer', 'bert', 'gpt', 'llm', 'neural', 'deep', 'learning']):
                        print(f"  🎯 可能的AI/ML相关文献")
                
                # 显示完整数据结构（用于调试）
                print(f"  完整数据结构:")
                print(json.dumps(data, indent=4, ensure_ascii=False)[:500] + "...")
        
        print(f"\n✅ 测试完成！")
        
        # 分类能力总结
        classifiable_count = len(pdfs_with_title) + len(pdfs_with_filename_only)
        total_independent = len(independent_pdf_items)
        
        print(f"\n📋 分类能力总结:")
        print(f"   - 独立PDF总数: {total_independent} 个")
        print(f"   - 可分类PDF: {classifiable_count} 个 ({classifiable_count/total_independent*100:.1f}%)" if total_independent > 0 else "   - 可分类PDF: 0 个")
        print(f"   - 有完整信息: {len(pdfs_with_title)} 个")
        print(f"   - 仅文件名信息: {len(pdfs_with_filename_only)} 个")
        print(f"   - 信息不足: {len(pdfs_with_no_info)} 个")
        
        if classifiable_count > 0:
            print(f"\n🎉 结论：有 {classifiable_count} 个独立PDF可以用于自动分类！")
        else:
            print(f"\n❌ 结论：独立PDF信息不足，无法进行自动分类")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_info() 