import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMClient:
    """统一的LLM客户端接口，带缓存机制"""
    
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.model_name = model_name
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.base_url = os.environ.get("OPENAI_BASE_URL")
        
        # 初始化缓存目录
        self.cache_dir = Path("./.cache/llm_responses")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if "claude" in model_name.lower():
            self.client_type = "anthropic"
            # Claude需要特殊处理，使用OpenAI兼容的接口
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client_type = "openai"
            self.client = OpenAI(api_key=api_key, base_url=base_url)
    
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
            # 统一使用OpenAI接口格式（Claude也使用OpenAI兼容接口）
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
            
            logger.warning(f"🌐 调用API (model: {self.model_name}, cache: {cache_key[:8]}...)")
            response = self.client.chat.completions.create(**api_params)
            
            # 解析响应
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
            logger.error(f"Error generating response with {self.model_name}: {str(e)}")
            raise
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None,
                     max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """向后兼容的文本生成方法"""  
        result = self.generate(prompt, system_prompt, max_tokens, temperature)
        return result.get("content", "")