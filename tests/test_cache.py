"""Tests for the TTL cache implementation."""

import time
import pytest
from services.cache import TTLCache


def test_cache_set_and_get():
    """Test setting and getting values from the cache."""
    cache = TTLCache()
    
    # Set a value
    cache.set("test_key", "test_value", ttl_seconds=10)
    
    # Get the value
    result = cache.get("test_key")
    assert result == "test_value"


def test_cache_expiration():
    """Test that cache entries expire correctly."""
    cache = TTLCache()
    
    # Set a value with a short TTL
    cache.set("expiring_key", "expiring_value", ttl_seconds=1)
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Try to get the expired value
    result = cache.get("expiring_key")
    assert result is None


def test_cache_clear():
    """Test clearing all cache entries."""
    cache = TTLCache()
    
    # Set some values
    cache.set("key1", "value1", ttl_seconds=10)
    cache.set("key2", "value2", ttl_seconds=10)
    
    # Clear the cache
    cache.clear()
    
    # Try to get the cleared values
    result1 = cache.get("key1")
    result2 = cache.get("key2")
    
    assert result1 is None
    assert result2 is None


def test_cache_cleanup_expired():
    """Test cleaning up expired entries."""
    cache = TTLCache()
    
    # Set some values with different TTLs
    cache.set("permanent_key", "permanent_value", ttl_seconds=10)
    cache.set("expiring_key", "expiring_value", ttl_seconds=1)
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Clean up expired entries
    cache.cleanup_expired()
    
    # Check that permanent entry still exists and expiring entry is gone
    permanent_result = cache.get("permanent_key")
    expiring_result = cache.get("expiring_key")
    
    assert permanent_result == "permanent_value"
    assert expiring_result is None