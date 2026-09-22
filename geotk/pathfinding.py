"""路网建模与最短路径：Dijkstra 与 A*。

节点带经纬度，边权重默认为两点球面距离（米），也可手动指定（如实时路况权重）。
A* 在全部边权不低于球面距离时使用距离启发；否则退化为 Dijkstra。
"""
import heapq
import math
from itertools import count
from numbers import Real

from .coord_transform import validate_point

EARTH_R = 6371000.0


def haversine_m(a, b):
    """a, b 为 (lng, lat)，返回球面距离（米）。"""
    validate_point(*a)
    validate_point(*b)
    p1 = (math.radians(a[1]), math.radians(a[0]))
    p2 = (math.radians(b[1]), math.radians(b[0]))
    dphi = p2[0] - p1[0]
    dlmb = p2[1] - p1[1]
    h = math.sin(dphi / 2) ** 2 + math.cos(p1[0]) * math.cos(p2[0]) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(min(1.0, max(0.0, h))))


class RoadNetwork:
    def __init__(self):
        self.nodes = {}   # id -> (lng, lat)
        self.adj = {}     # id -> [(neighbor, weight)]
        self._distance_heuristic_safe = True

    def add_node(self, node_id, lng, lat):
        validate_point(lng, lat)
        if node_id in self.nodes and self.nodes[node_id] != (lng, lat):
            raise ValueError("不能修改已有节点坐标；请新建路网以重新计算边权")
        self.nodes[node_id] = (lng, lat)
        self.adj.setdefault(node_id, [])

    def add_edge(self, u, v, bidirectional=True, weight=None):
        if u not in self.nodes or v not in self.nodes:
            raise ValueError("边的端点必须先 add_node")
        distance = haversine_m(self.nodes[u], self.nodes[v])
        if weight is None:
            weight = distance
        if isinstance(weight, bool) or not isinstance(weight, Real) or not math.isfinite(weight) or weight < 0:
            raise ValueError("边权必须为非负有限数")
        if weight < distance:
            self._distance_heuristic_safe = False
        self.adj[u].append((v, weight))
        if bidirectional:
            self.adj[v].append((u, weight))

    def shortest_path(self, start, goal, method="astar"):
        """返回 (路径节点列表, 总权重)；默认权重单位为米，不可达返回 (None, inf)。"""
        if start not in self.nodes or goal not in self.nodes:
            raise ValueError("起点和终点必须存在")
        if method not in ("dijkstra", "astar"):
            raise ValueError("method 必须为 dijkstra 或 astar")
        if method == "dijkstra" or not self._distance_heuristic_safe:
            heuristic = lambda n: 0.0
        elif method == "astar":
            heuristic = lambda n: haversine_m(self.nodes[n], self.nodes[goal])
        else:
            raise ValueError("method 必须为 dijkstra 或 astar")

        inf = float("inf")
        dist = {start: 0.0}
        came = {}
        serial = count()
        pq = [(heuristic(start), 0.0, next(serial), start)]

        while pq:
            _, g, _, u = heapq.heappop(pq)
            if g > dist.get(u, inf):
                continue
            if u == goal:
                path = [goal]
                while path[-1] != start:
                    path.append(came[path[-1]])
                return path[::-1], g
            for v, w in self.adj[u]:
                ng = g + w
                if ng < dist.get(v, inf):
                    dist[v] = ng
                    came[v] = u
                    heapq.heappush(pq, (ng + heuristic(v), ng, next(serial), v))
        return None, inf
