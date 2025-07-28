#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Setup - 配置设置工具
帮助用户快速设置环境配置
"""

import os
import sys
from pathlib import Path
from typing import Optional


def create_env_file() -> bool:
    """创建.env文件"""
    env_file = Path(".env")
    example_file = Path("env.example")
    
    if env_file.exists():
        print("⚠️  .env文件已存在")
        response = input("是否覆盖？(y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            return False
    
    if not example_file.exists():
        print("❌ 找不到env.example文件")
        return False
    
    # 复制示例文件
    with open(example_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已创建.env文件")
    return True


def interactive_setup() -> bool:
    """交互式配置设置"""
    print("🔧 交互式配置设置")
    print("=" * 50)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 请先创建.env文件")
        return False
    
    # 读取现有配置
    config = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
    
    # LLM配置
    print("\n🤖 LLM配置:")
    print("-" * 30)
    
    # API类型
    api_type = input(f"LLM API类型 (openai-compatible/gemini-direct) [{config.get('LLM_API_TYPE', 'openai-compatible')}]: ").strip()
    if api_type:
        config['LLM_API_TYPE'] = api_type
    elif 'LLM_API_TYPE' not in config:
        config['LLM_API_TYPE'] = 'openai-compatible'
    
    # API密钥
    if config['LLM_API_TYPE'] == 'gemini-direct':
        gemini_key = input(f"Gemini API密钥 [{config.get('GEMINI_API_KEY', '')}]: ").strip()
        if gemini_key:
            config['GEMINI_API_KEY'] = gemini_key
    else:
        openai_key = input(f"OpenAI API密钥 [{config.get('LLM_API_KEY', '')}]: ").strip()
        if openai_key:
            config['LLM_API_KEY'] = openai_key
    
    # 模型
    model = input(f"模型名称 [{config.get('LLM_MODEL', 'gemini-2.5-pro')}]: ").strip()
    if model:
        config['LLM_MODEL'] = model
    elif 'LLM_MODEL' not in config:
        config['LLM_MODEL'] = 'gemini-2.5-pro'
    
    # Zotero配置
    print("\n📚 Zotero配置:")
    print("-" * 30)
    
    user_id = input(f"Zotero用户ID [{config.get('ZOTERO_USER_ID', '')}]: ").strip()
    if user_id:
        config['ZOTERO_USER_ID'] = user_id
    
    api_key = input(f"Zotero API密钥 [{config.get('ZOTERO_API_KEY', '')}]: ").strip()
    if api_key:
        config['ZOTERO_API_KEY'] = api_key
    
    # 环境配置
    print("\n⚙️  环境配置:")
    print("-" * 30)
    
    environment = input(f"运行环境 (development/production) [{config.get('ENVIRONMENT', 'development')}]: ").strip()
    if environment:
        config['ENVIRONMENT'] = environment
    elif 'ENVIRONMENT' not in config:
        config['ENVIRONMENT'] = 'development'
    
    debug = input(f"调试模式 (true/false) [{config.get('DEBUG', 'false')}]: ").strip()
    if debug:
        config['DEBUG'] = debug
    elif 'DEBUG' not in config:
        config['DEBUG'] = 'false'
    
    # 保存配置
    print("\n💾 保存配置...")
    
    # 读取原始文件内容
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 更新配置值
    updated_lines = []
    for line in lines:
        if line.strip() and not line.startswith('#') and '=' in line:
            key = line.split('=', 1)[0]
            if key in config:
                updated_lines.append(f"{key}={config[key]}\n")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # 写入更新后的配置
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print("✅ 配置已保存")
    return True


def validate_config() -> bool:
    """验证配置"""
    print("🔍 验证配置...")
    
    try:
        from config import get_config
        config = get_config()
        
        print("✅ 配置验证通过")
        print(f"   环境: {config.environment}")
        print(f"   调试模式: {config.debug}")
        print(f"   LLM API类型: {config.llm.api_type}")
        print(f"   LLM模型: {config.llm.model}")
        print(f"   Zotero用户ID: {config.zotero.user_id}")
        
        return True
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False


def show_help():
    """显示帮助信息"""
    print("""
🔧 配置设置工具

使用方法:
  python setup_config.py [命令]

命令:
  create    创建.env文件
  setup     交互式配置设置
  validate  验证配置
  help      显示此帮助信息

示例:
  python setup_config.py create    # 创建.env文件
  python setup_config.py setup     # 交互式配置
  python setup_config.py validate  # 验证配置
""")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        success = create_env_file()
        return 0 if success else 1
    elif command == "setup":
        success = interactive_setup()
        return 0 if success else 1
    elif command == "validate":
        success = validate_config()
        return 0 if success else 1
    elif command in ["help", "-h", "--help"]:
        show_help()
        return 0
    else:
        print(f"❌ 未知命令: {command}")
        show_help()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 