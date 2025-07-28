#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Migration - 配置迁移工具
从旧的setup_env.sh迁移到新的配置系统
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Optional


def check_setup_env_exists() -> bool:
    """检查setup_env.sh是否存在"""
    return Path("setup_env.sh").exists()


def load_old_environment() -> Dict[str, str]:
    """加载旧的环境变量"""
    env_vars = {}
    
    if not check_setup_env_exists():
        print("❌ 找不到setup_env.sh文件")
        return env_vars
    
    print("📖 读取setup_env.sh文件...")
    
    try:
        # 直接读取setup_env.sh文件内容
        with open("setup_env.sh", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析环境变量
        for line in content.split('\n'):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#') or line.startswith('echo'):
                continue
            
            # 解析export语句
            if line.startswith('export '):
                # 移除export前缀
                var_line = line[7:].strip()
                if '=' in var_line:
                    key, value = var_line.split('=', 1)
                    # 移除引号
                    value = value.strip("'\"")
                    env_vars[key] = value
        
        print(f"✅ 成功读取 {len(env_vars)} 个环境变量")
        
    except Exception as e:
        print(f"❌ 读取setup_env.sh失败: {e}")
    
    return env_vars


def map_old_to_new_config(old_env: Dict[str, str]) -> Dict[str, str]:
    """将旧的环境变量映射到新的配置"""
    mapping = {
        # LLM配置
        'LLM_API_TYPE': 'LLM_API_TYPE',
        'OPENAI_API_KEY': 'LLM_API_KEY',
        'OPENAI_BASE_URL': 'LLM_BASE_URL',
        'LLM_MODEL': 'LLM_MODEL',
        'GEMINI_API_KEY': 'GEMINI_API_KEY',
        'GEMINI_API_ENDPOINT': 'GEMINI_API_ENDPOINT',
        'LLM_RATE_LIMIT_RPM': 'LLM_RPM_LIMIT',
        
        # Zotero配置
        'ZOTERO_USER_ID': 'ZOTERO_USER_ID',
        'ZOTERO_API_KEY': 'ZOTERO_API_KEY',
        'ZOTERO_BASE_URL': 'ZOTERO_BASE_URL',
    }
    
    new_config = {}
    
    for old_key, new_key in mapping.items():
        if old_key in old_env:
            new_config[new_key] = old_env[old_key]
    
    return new_config


def create_env_file_from_old_config(config: Dict[str, str]) -> bool:
    """从旧配置创建.env文件"""
    env_file = Path(".env")
    example_file = Path("env.example")
    
    if not example_file.exists():
        print("❌ 找不到env.example文件")
        return False
    
    # 读取示例文件
    with open(example_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换配置值
    for key, value in config.items():
        # 查找并替换配置行
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                break
        content = '\n'.join(lines)
    
    # 写入.env文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已创建.env文件")
    return True


def backup_setup_env() -> bool:
    """备份setup_env.sh文件"""
    if not check_setup_env_exists():
        return True
    
    backup_file = Path("setup_env.sh.backup")
    if backup_file.exists():
        response = input("⚠️  备份文件已存在，是否覆盖？(y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            return False
    
    try:
        import shutil
        shutil.copy2("setup_env.sh", "setup_env.sh.backup")
        print("✅ 已备份setup_env.sh为setup_env.sh.backup")
        return True
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False


def show_migration_summary(old_env: Dict[str, str], new_config: Dict[str, str]):
    """显示迁移摘要"""
    print("\n📊 迁移摘要:")
    print("=" * 50)
    
    print(f"📖 从setup_env.sh读取的变量: {len(old_env)}")
    print(f"🔄 映射到新配置的变量: {len(new_config)}")
    
    if new_config:
        print("\n✅ 成功映射的配置:")
        for key, value in new_config.items():
            # 隐藏敏感信息
            if 'KEY' in key or 'SECRET' in key:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"   {key}: {display_value}")
    
    unmapped = set(old_env.keys()) - set(new_config.keys())
    if unmapped:
        print(f"\n⚠️  未映射的变量 ({len(unmapped)}):")
        for key in sorted(unmapped):
            print(f"   {key}")
    
    print("\n💡 迁移后的使用方式:")
    print("   1. 不再需要运行: source setup_env.sh")
    print("   2. 直接运行脚本即可: python 005_generate_schema_and_create_collections.py")
    print("   3. 如需修改配置，编辑.env文件")


def main():
    """主函数"""
    print("🔄 配置迁移工具")
    print("=" * 50)
    print("从setup_env.sh迁移到新的.env配置系统")
    print()
    
    # 检查setup_env.sh是否存在
    if not check_setup_env_exists():
        print("❌ 找不到setup_env.sh文件")
        print("💡 如果没有旧的配置文件，请运行:")
        print("   python setup_config.py create")
        return 1
    
    # 备份原文件
    if not backup_setup_env():
        return 1
    
    # 加载旧配置
    old_env = load_old_environment()
    if not old_env:
        print("❌ 无法加载旧配置")
        return 1
    
    # 映射配置
    new_config = map_old_to_new_config(old_env)
    
    # 显示迁移摘要
    show_migration_summary(old_env, new_config)
    
    # 确认迁移
    print("\n" + "=" * 50)
    response = input("是否继续迁移？(y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 已取消迁移")
        return 0
    
    # 创建.env文件
    if create_env_file_from_old_config(new_config):
        print("\n✅ 迁移完成！")
        print("\n📝 后续步骤:")
        print("   1. 验证配置: python setup_config.py validate")
        print("   2. 测试脚本: python 005_generate_schema_and_create_collections.py --help")
        print("   3. 如需修改配置，编辑.env文件")
        print("   4. 确认一切正常后，可以删除setup_env.sh.backup")
        return 0
    else:
        print("❌ 迁移失败")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 