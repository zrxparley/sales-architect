"""
LLM 响应缓存模块
使用文件哈希缓存 LLM 响应，减少重复 API 调用
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class LLMCache:
    """LLM 响应缓存管理器"""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录，默认 ~/.sa-cache
        """
        self.cache_dir = cache_dir or Path.home() / ".sa-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"

    def _get_cache_key(self, messages: list, model: str, temperature: float) -> str:
        """
        生成缓存键（基于消息内容、模型和参数的哈希）

        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数

        Returns:
            缓存键字符串
        """
        # 将消息、模型和温度参数序列化为字符串
        cache_data = {
            "messages": messages,
            "model": model,
            "temperature": temperature
        }
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)

        # 生成 SHA256 哈希
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, messages: list, model: str, temperature: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        从缓存获取响应

        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数

        Returns:
            缓存的响应数据，如果不存在或已过期则返回 None
        """
        cache_key = self._get_cache_key(messages, model, temperature)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 检查是否过期（默认7天）
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(days=7):
                # 删除过期缓存
                cache_path.unlink()
                self._update_metadata(cache_key, remove=True)
                return None

            # 更新访问次数
            self._update_metadata(cache_key, update_access=True)

            return cache_data.get('response')

        except (json.JSONDecodeError, KeyError, ValueError):
            # 缓存文件损坏，删除并返回 None
            if cache_path.exists():
                cache_path.unlink()
                self._update_metadata(cache_key, remove=True)
            return None

    def set(self, messages: list, model: str, temperature: float, response: Dict[str, Any]) -> None:
        """
        保存响应到缓存

        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数
            response: LLM 响应数据
        """
        cache_key = self._get_cache_key(messages, model, temperature)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'temperature': temperature,
            'response': response,
            'message_count': len(messages)
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            self._update_metadata(cache_key, add=True)

        except (IOError, OSError) as e:
            print(f"⚠️ 缓存写入失败: {e}")

    def _load_metadata(self) -> Dict[str, Any]:
        """加载缓存元数据"""
        if not self.metadata_file.exists():
            return {"entries": {}, "total_size": 0}

        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"entries": {}, "total_size": 0}

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """保存缓存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as e:
            print(f"⚠️ 元数据保存失败: {e}")

    def _update_metadata(self, cache_key: str, add: bool = False,
                         update_access: bool = False, remove: bool = False) -> None:
        """
        更新缓存元数据

        Args:
            cache_key: 缓存键
            add: 是否添加新条目
            update_access: 是否更新访问时间
            remove: 是否移除条目
        """
        metadata = self._load_metadata()

        if remove and cache_key in metadata['entries']:
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                size = cache_path.stat().st_size
                metadata['total_size'] = max(0, metadata['total_size'] - size)
            del metadata['entries'][cache_key]

        elif add and cache_key not in metadata['entries']:
            cache_path = self._get_cache_path(cache_key)
            size = cache_path.stat().st_size if cache_path.exists() else 0
            metadata['entries'][cache_key] = {
                'created': datetime.now().isoformat(),
                'last_access': datetime.now().isoformat(),
                'access_count': 1,
                'size': size
            }
            metadata['total_size'] += size

        elif update_access and cache_key in metadata['entries']:
            metadata['entries'][cache_key]['last_access'] = datetime.now().isoformat()
            metadata['entries'][cache_key]['access_count'] += 1

        self._save_metadata(metadata)

    def clear(self) -> int:
        """
        清空所有缓存

        Returns:
            删除的缓存文件数量
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name != "metadata.json":
                try:
                    cache_file.unlink()
                    count += 1
                except OSError:
                    pass

        # 重置元数据
        self._save_metadata({"entries": {}, "total_size": 0})

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        metadata = self._load_metadata()

        # 计算实际文件大小
        total_size = 0
        file_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name != "metadata.json":
                total_size += cache_file.stat().st_size
                file_count += 1

        return {
            "cache_dir": str(self.cache_dir),
            "total_entries": len(metadata['entries']),
            "actual_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_entry": self._get_oldest_entry(metadata),
            "most_accessed": self._get_most_accessed(metadata)
        }

    def _get_oldest_entry(self, metadata: Dict[str, Any]) -> Optional[str]:
        """获取最旧的缓存条目"""
        if not metadata['entries']:
            return None

        oldest_key = min(
            metadata['entries'].keys(),
            key=lambda k: metadata['entries'][k]['created']
        )
        return metadata['entries'][oldest_key]['created']

    def _get_most_accessed(self, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取访问次数最多的缓存条目"""
        if not metadata['entries']:
            return None

        most_key = max(
            metadata['entries'].keys(),
            key=lambda k: metadata['entries'][k]['access_count']
        )

        entry = metadata['entries'][most_key]
        return {
            "access_count": entry['access_count'],
            "created": entry['created'],
            "last_access": entry['last_access']
        }


# 全局缓存实例
_cache_instance: Optional[LLMCache] = None


def get_cache() -> LLMCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache()
    return _cache_instance


def is_cache_enabled() -> bool:
    """检查缓存是否启用（通过环境变量控制）"""
    return os.environ.get('SA_CACHE_ENABLED', '1') == '1'
