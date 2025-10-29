"""
Cache manager for LLM responses and generated content
Provides simple file-based caching with invalidation support
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict


class CacheManager:
    """Simple file-based cache for LLM responses"""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, content: str) -> str:
        """Generate cache key from content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get path for cache file"""
        return self.cache_dir / f"{key}.json"
    
    def get(self, prompt: str) -> Optional[Any]:
        """
        Get cached response for a prompt
        
        Args:
            prompt: The prompt/key to look up
            
        Returns:
            Cached data if found, None otherwise
        """
        cache_key = self._get_cache_key(prompt)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read cache file: {e}")
                return None
        
        return None
    
    def set(self, prompt: str, data: Any):
        """
        Cache a response
        
        Args:
            prompt: The prompt/key
            data: Data to cache (must be JSON-serializable)
        """
        cache_key = self._get_cache_key(prompt)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write cache file: {e}")
    
    def invalidate(self, prompt: str):
        """
        Remove cached data for a prompt
        
        Args:
            prompt: The prompt/key to invalidate
        """
        cache_key = self._get_cache_key(prompt)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            cache_path.unlink()
    
    def clear_all(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        print(f"✅ Cleared all cache files from {self.cache_dir}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        return {
            "total_files": len(cache_files),
            "cache_dir": str(self.cache_dir)
        }


# Global cache instance
_global_cache = None

def get_cache(cache_dir: str = ".cache") -> CacheManager:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(cache_dir)
    return _global_cache
