#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Management - 统一配置管理
使用 pydantic-settings 进行类型安全的配置管理

支持：
1. 环境变量配置
2. .env 文件配置
3. 多环境配置
4. 配置验证
5. 默认值管理
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM配置"""
    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)
    
    # API类型
    api_type: str = Field(default="openai-compatible", description="LLM API类型")
    
    # OpenAI兼容配置
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")
    model: str = Field(default="gemini-2.5-pro", description="模型名称")
    
    # Gemini直接配置
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY", description="Gemini API密钥")
    gemini_base_url: str = Field(default="https://generativelanguage.googleapis.com", alias="GEMINI_API_ENDPOINT", description="Gemini API端点")
    
    # 速率限制
    rpm_limit: int = Field(default=5, description="每分钟请求限制")
    timeout: float = Field(default=30.0, description="请求超时时间")
    connect_timeout: float = Field(default=10.0, description="连接超时时间")
    
    def model_post_init(self, __context) -> None:
        """模型初始化后验证"""
        if self.api_type == 'gemini-direct' and not self.gemini_api_key:
            raise ValueError("Gemini直接模式需要设置GEMINI_API_KEY")
        elif self.api_type == 'openai-compatible' and not self.api_key:
            raise ValueError("OpenAI兼容模式需要设置LLM_API_KEY")


class ZoteroConfig(BaseSettings):
    """Zotero配置"""
    model_config = SettingsConfigDict(env_prefix="ZOTERO_", case_sensitive=False)
    
    user_id: str = Field(description="Zotero用户ID")
    api_key: str = Field(description="Zotero API密钥")
    base_url: str = Field(default="https://api.zotero.org", description="Zotero API基础URL")
    
    @property
    def api_base_url(self) -> str:
        """获取完整的API基础URL"""
        return f"{self.base_url}/users/{self.user_id}"
    
    @property
    def headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            'Zotero-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }


class AppConfig(BaseSettings):
    """应用配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 环境
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    
    # 数据目录
    data_dir: str = Field(default="data", description="数据目录")
    
    # 文件配置
    literature_file: str = Field(default="data/literature_info.xlsx", description="文献信息文件路径")
    schema_file: str = Field(default="data/classification_schema.json", description="分类schema文件路径")
    llm_schema_file: str = Field(default="data/llm_generated_schema.json", description="LLM生成的schema文件路径")
    fixed_schema_file: str = Field(default="data/fixed_schema.json", description="修复后的schema文件路径")
    
    # 处理配置
    default_batch_size: int = Field(default=50, description="默认批量大小")
    default_test_items: int = Field(default=10, description="默认测试项目数")
    default_dry_run_items: int = Field(default=50, description="默认干运行项目数")
    default_max_items: int = Field(default=100, description="默认最大处理项目数")
    default_limit: int = Field(default=100, description="默认API请求限制")
    
    # Token限制
    max_tokens_limit: int = Field(default=250000, description="最大token限制")
    default_output_tokens: int = Field(default=2000, description="默认输出token数")
    
    # 文本限制 - 用于控制日志输出和显示文本的长度
    title_preview_length: int = Field(default=50, description="文献标题在日志中的显示长度，超过此长度会截断并显示'...'")
    description_preview_length: int = Field(default=100, description="分类描述在日志中的显示长度，超过此长度会截断并显示'...'")
    abstract_limit: int = Field(default=2000, description="从Zotero notes中提取摘要时的最大长度限制，超过此长度会截断")
    
    # LLM配置
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    
    # Zotero配置
    zotero: ZoteroConfig = Field(default_factory=ZoteroConfig, description="Zotero配置")
    
    @field_validator('data_dir')
    @classmethod
    def create_data_dir(cls, v):
        """确保数据目录存在"""
        Path(v).mkdir(exist_ok=True)
        return v
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"
    
    def get_literature_file_path(self) -> Path:
        """获取文献文件路径"""
        return Path(self.data_dir) / Path(self.literature_file).name
    
    def get_schema_file_path(self) -> Path:
        """获取schema文件路径"""
        return Path(self.data_dir) / Path(self.schema_file).name


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """重新加载配置"""
    global _config
    _config = AppConfig()
    return _config


# 便捷访问函数
def get_llm_config() -> LLMConfig:
    """获取LLM配置"""
    return get_config().llm


def get_zotero_config() -> ZoteroConfig:
    """获取Zotero配置"""
    return get_config().zotero


def get_data_dir() -> Path:
    """获取数据目录"""
    return Path(get_config().data_dir)


def get_literature_file() -> Path:
    """获取文献文件路径"""
    return get_config().get_literature_file_path()


def get_schema_file() -> Path:
    """获取schema文件路径"""
    return get_config().get_schema_file_path()

def get_default_batch_size() -> int:
    """获取默认批量大小"""
    return get_config().default_batch_size

def get_default_test_items() -> int:
    """获取默认测试项目数"""
    return get_config().default_test_items

def get_default_dry_run_items() -> int:
    """获取默认干运行项目数"""
    return get_config().default_dry_run_items

def get_default_max_items() -> int:
    """获取默认最大处理项目数"""
    return get_config().default_max_items

def get_default_limit() -> int:
    """获取默认API请求限制"""
    return get_config().default_limit

def get_max_tokens_limit() -> int:
    """获取最大token限制"""
    return get_config().max_tokens_limit

def get_default_output_tokens() -> int:
    """获取默认输出token数"""
    return get_config().default_output_tokens

def get_title_preview_length() -> int:
    """获取标题预览长度"""
    return get_config().title_preview_length

def get_description_preview_length() -> int:
    """获取描述预览长度"""
    return get_config().description_preview_length

def get_abstract_limit() -> int:
    """获取摘要长度限制"""
    return get_config().abstract_limit 