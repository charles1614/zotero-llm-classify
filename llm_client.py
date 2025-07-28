#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Client - 统一的LLM客户端
支持多种LLM API，包括OpenAI兼容接口和Gemini直接接口
"""

import os
import time
import json
import hashlib
import httpx
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pathlib import Path
from collections import deque
from openai import OpenAI
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    from google import genai
except ImportError:
    genai = None

# 导入配置
from config import get_llm_config

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimiter:
    """简单的速率限制器，基于滑动窗口"""
    
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
    
    def can_proceed(self) -> bool:
        """检查是否可以继续请求"""
        now = time.time()
        
        # 移除窗口外的请求
        while self.requests and now - self.requests[0] > self.window_seconds:
            self.requests.popleft()
        
        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            return False
        
        return True
    
    def record_request(self):
        """记录一个请求"""
        now = time.time()
        self.requests.append(now)
    
    def wait_if_needed(self):
        """如果需要，等待直到可以继续请求"""
        while not self.can_proceed():
            # 计算需要等待的时间
            if self.requests:
                oldest_request = self.requests[0]
                wait_time = self.window_seconds - (time.time() - oldest_request)
                if wait_time > 0:
                    logger.info(f"⏳ 速率限制: 等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)
            else:
                break
        
        self.record_request()

class LLMClient:
    """统一的LLM客户端接口，带缓存机制"""
    
    def __init__(self, model_name: str = None, api_key: str = None, base_url: str = None):
        # 获取配置
        config = get_llm_config()
        
        self.model_name = model_name or config.model
        self.api_key = api_key or config.api_key
        
        # 根据API类型选择正确的base_url
        if config.api_type == 'gemini-direct':
            self.base_url = base_url or config.gemini_base_url
        else:
            self.base_url = base_url or config.base_url
        
        # 初始化缓存目录
        self.cache_dir = Path("./.cache/llm_responses")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置超时参数
        timeout_config = httpx.Timeout(config.timeout, connect=config.connect_timeout)
        
        # 初始化速率限制器
        self.rate_limiter = None
        
        # 设置速率限制
        if config.rpm_limit > 0:
            self.rate_limiter = RateLimiter(max_requests=config.rpm_limit, window_seconds=60)
            logger.info(f"🔒 为 {self.model_name} 启用速率限制: {config.rpm_limit} RPM")
        
        if "claude" in self.model_name.lower():
            self.client_type = "anthropic"
            # Claude需要特殊处理，使用OpenAI兼容的接口
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_config)
        elif "gemini" in self.model_name.lower():
            self.client_type = "gemini"
            # 检查是否是官方Gemini API
            if "generativelanguage.googleapis.com" in self.base_url:
                # 官方Gemini API - 使用google.generativeai库
                self.client = genai.Client(api_key=config.gemini_api_key)
                self.gemini_base_url = self.base_url
                self.gemini_api_key = config.gemini_api_key
            else:
                # 代理API - 使用OpenAI兼容接口
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_config)
                self.gemini_base_url = self.base_url
                self.gemini_api_key = config.gemini_api_key
        else:
            self.client_type = "openai"
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_config)
    
    def _generate_cache_key(self, prompt: str, system_prompt: Optional[str] = None, 
                           max_tokens: int = 4096, temperature: float = 0.7, 
                           tools: Optional[List[Dict]] = None) -> str:
        """生成缓存键值"""
        # 创建一个包含所有参数的字典
        cache_data = {
            "model": self.model_name,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tools
        }
        
        # 使用JSON序列化并计算MD5哈希
        cache_string = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        cache_hash = hashlib.md5(cache_string.encode('utf-8')).hexdigest()
        return cache_hash
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取回复"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    logger.warning(f"🔄 使用缓存回复 (model: {self.model_name}, cache: {cache_key[:8]}...)")
                    return cache_data.get("response")
            except Exception as e:
                logger.warning(f"读取缓存失败: {str(e)}")
        return None
    
    def _save_cached_response(self, cache_key: str, prompt: str, system_prompt: Optional[str], 
                             response: Dict[str, Any], max_tokens: int, temperature: float,
                             tools: Optional[List[Dict]] = None) -> None:
        """保存回复到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            cache_data = {
                "model": self.model_name,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"💾 缓存已保存 (model: {self.model_name}, cache: {cache_key[:8]}...)")
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                 max_tokens: int = 4096, temperature: float = 0.7,
                 tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """生成回复，带缓存机制"""
        
        # 生成缓存键
        cache_key = self._generate_cache_key(prompt, system_prompt, max_tokens, temperature, tools)
        
        # 尝试从缓存获取
        cached_response = self._get_cached_response(cache_key)
        if cached_response is not None:
            return cached_response
        
        # 缓存未命中，调用API
        try:
            # 应用速率限制（如果需要）
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()
            
            logger.warning(f"🌐 调用API (model: {self.model_name}, cache: {cache_key[:8]}...)")
            
            if self.client_type == "gemini":
                # 检查是否是官方Gemini API
                if "generativelanguage.googleapis.com" in self.gemini_base_url:
                    # 官方Gemini API
                    response = self._call_official_gemini_api(prompt, system_prompt, max_tokens, temperature)
                    result = {
                        "content": response.get("content", ""),
                        "tool_calls": []
                    }
                else:
                    # 代理API - OpenAI兼容接口
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    
                    # 构建API调用参数
                    api_params = {
                        "model": self.model_name,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                    
                    # 如果提供了工具，添加工具调用支持
                    if tools:
                        api_params["tools"] = tools
                        api_params["tool_choice"] = "auto"
                    
                    response = self.client.chat.completions.create(**api_params)
                    
                    # OpenAI兼容接口响应格式
                    message = response.choices[0].message
                    result = {
                        "content": message.content,
                        "tool_calls": []
                    }
                    
                    # 检查是否有工具调用
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            result["tool_calls"].append({
                                "id": tool_call.id,
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            })
            else:
                # OpenAI兼容接口
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # 构建API调用参数
                api_params = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # 如果提供了工具，添加工具调用支持
                if tools:
                    api_params["tools"] = tools
                    api_params["tool_choice"] = "auto"
                
                response = self.client.chat.completions.create(**api_params)
                
                # OpenAI兼容接口响应格式
                message = response.choices[0].message
                result = {
                    "content": message.content,
                    "tool_calls": []
                }
                
                # 检查是否有工具调用
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
            
            # 保存到缓存
            self._save_cached_response(cache_key, prompt, system_prompt, result, max_tokens, temperature, tools)
            
            return result
                
        except Exception as e:
            # 根据客户端类型提供更准确的错误信息
            if self.client_type == "gemini":
                if self.client is None:
                    logger.error(f"Gemini API调用失败 (model: {self.model_name}): {str(e)}")
                else:
                    logger.error(f"Gemini兼容接口调用失败 (model: {self.model_name}): {str(e)}")
            elif self.client_type == "anthropic":
                logger.error(f"Claude API调用失败 (model: {self.model_name}): {str(e)}")
            else:
                logger.error(f"OpenAI API调用失败 (model: {self.model_name}): {str(e)}")
            raise
    
    def _call_official_gemini_api(self, prompt: str, system_prompt: Optional[str] = None, 
                                 max_tokens: int = 4096, temperature: float = 0.7) -> Dict[str, Any]:
        """调用官方Gemini API使用google.generativeai库"""
        try:
            # 构建完整的提示词
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\n{prompt}"
            
            # 使用genai.Client()调用API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            # 提取文本内容
            if response.text:
                return {
                    "content": response.text
                }
            else:
                return {
                    "content": ""
                }
                
        except Exception as e:
            logger.error(f"官方Gemini API调用失败 (model: {self.model_name}): {str(e)}")
            logger.error(f"错误类型: {type(e).__name__}")
            raise
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None,
                     max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """向后兼容的文本生成方法"""  
        result = self.generate(prompt, system_prompt, max_tokens, temperature)
        return result.get("content", "")