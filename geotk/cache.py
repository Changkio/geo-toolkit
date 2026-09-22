"""LRU 缓存：可用于缓存热点瓦片、地理编码或路径规划结果。

get/put O(1)，容量满时淘汰最近最少使用的条目。
"""


class _Node:
    __slots__ = ("key", "val", "prev", "next")

    def __init__(self, key, val):
        self.key = key
        self.val = val
        self.prev = None
        self.next = None


class LRUCache:
    def __init__(self, capacity=128):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity 必须为正整数")
        self.cap = capacity
        self.map = {}
        self.head = _Node(None, None)
        self.tail = _Node(None, None)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_front(self, node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key, default=None):
        node = self.map.get(key)
        if node is None:
            return default
        self._remove(node)
        self._add_front(node)
        return node.val

    def put(self, key, val):
        node = self.map.get(key)
        if node:
            node.val = val
            self._remove(node)
            self._add_front(node)
            return
        if len(self.map) == self.cap:
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]
        node = _Node(key, val)
        self._add_front(node)
        self.map[key] = node

    def __len__(self):
        return len(self.map)
