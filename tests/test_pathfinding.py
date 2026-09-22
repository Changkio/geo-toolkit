"""路径规划与 LRU 缓存测试，可直接运行：python tests/test_pathfinding.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from geotk.pathfinding import RoadNetwork, haversine_m
from geotk.cache import LRUCache


def build_network():
    net = RoadNetwork()
    # 近路：A -> B -> C
    net.add_node("A", 113.52, 22.27)
    net.add_node("B", 113.53, 22.27)
    net.add_node("C", 113.53, 22.28)
    # 远绕行点 D
    net.add_node("D", 113.50, 22.25)
    net.add_edge("A", "B")
    net.add_edge("B", "C")
    net.add_edge("A", "D")
    net.add_edge("D", "C")
    return net


def test_shortest_path():
    net = build_network()
    expected_cost = haversine_m((113.52, 22.27), (113.53, 22.27)) + haversine_m(
        (113.53, 22.27), (113.53, 22.28)
    )
    for method in ("dijkstra", "astar"):
        path, cost = net.shortest_path("A", "C", method)
        assert path == ["A", "B", "C"]
        assert abs(cost - expected_cost) < 1.0


def test_unreachable():
    net = RoadNetwork()
    net.add_node("X", 0, 0)
    net.add_node("Y", 1, 1)
    path, cost = net.shortest_path("X", "Y")
    assert path is None


def test_lru_cache():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)          # 淘汰 b
    assert c.get("b") is None and c.get("c") == 3
    assert len(c) == 2


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("ALL TESTS PASSED")
