"""SageWorksCache is a wrapper around Cache and RedisCache that allows us to
use RedisCache if it's available, and fall back to Cache if it's not.
"""

from sageworks.utils.cache import Cache
from sageworks.utils.redis_cache import RedisCache

import logging

log = logging.getLogger("sageworks")


class SageWorksCache:
    def __init__(self, expire=None, prefix="", postfix=""):
        """SageWorksCache Initialization
        Args:
            expire: the number of seconds to keep items in the cache
            prefix: the prefix to use for all keys
            postfix: the postfix to use for all keys
        """
        self.medium_data = 5 * 1024  # 5KB
        self.large_data = 20 * 1024  # 20KB
        if RedisCache().check():
            self._actual_cache = RedisCache(expire=expire, prefix=prefix, postfix=postfix)
        else:
            # If Redis isn't available, fall back to an In-Memory Cache
            log.critical("Redis connect failed, using In-Memory Cache...")
            self._actual_cache = Cache(expire=expire, prefix=prefix, postfix=postfix)

    def set(self, key, value):
        # Check the size of the value
        if len(value) > self.large_data:
            log.warning(f"Large cache value: ({key}: {len(value)})")
        elif len(value) > self.medium_data:
            log.important(f"Medium cache value: ({key}: {len(value)})")
        self._actual_cache.set(key, value)

    def get(self, key):
        # Check the size of the value
        value = self._actual_cache.get(key)
        if value and len(value) > self.large_data:
            log.warning(f"Large cache value: ({key}: {len(value)})")
        elif value and len(value) > self.medium_data:
            log.important(f"Medium cache value: ({key}: {len(value)})")
        return value

    def delete(self, key):
        self._actual_cache.delete(key)

    def list_keys(self):
        return self._actual_cache.list_keys()

    def list_subkeys(self, key):
        return self._actual_cache.list_subkeys(key)

    def check(self):
        return RedisCache().check()

    def clear(self):
        return self._actual_cache.clear()


if __name__ == "__main__":
    """Exercise the SageWorks Cache class"""

    # Create the SageWorks Cache
    my_cache = SageWorksCache(prefix="test")
    assert my_cache.check()

    # Delete anything in the test database
    my_cache.clear()

    # Test storage
    my_cache.set("foo", "bar")
    assert my_cache.get("foo") == "bar"
    for key in my_cache.list_keys():
        print(key)
    my_cache.clear()

    # Test prefix/postfix
    my_cache = SageWorksCache(prefix="pre", postfix="post")
    my_cache.set("foo", "bar")
    assert my_cache.get("foo") == "bar"
    my_cache.list_keys()
    for key in my_cache.list_keys():
        print(key)
    my_cache.clear()

    # Test medium and large data
    my_cache = SageWorksCache(prefix="test")
    my_cache.set("foo", "a" * 1024)
    my_cache.set("bar", "a" * 1024 * 6)
    my_cache.set("baz", "a" * 1024 * 30)
    my_cache.get("foo")
    my_cache.get("bar")
    my_cache.get("baz")
    my_cache.clear()
