"""针对已发现正确性与输入边界缺陷的回归测试。"""
import copy
import itertools
import math
import random

import pytest

from geotk.cache import LRUCache
from geotk.coord_transform import SYSTEMS, transform_coords, transform_point
from geotk.geojson_io import dump_geojson, load_geojson, transform_geojson
from geotk.pathfinding import RoadNetwork, haversine_m


@pytest.mark.parametrize("src,dst", list(itertools.product(SYSTEMS, repeat=2)))
def test_rectangle_outside_unchanged_for_all_pairs(src, dst):
    for p in [(-74, 40.7), (73.66, 30), (135.05, 30), (100, 3.86), (100, 53.55)]:
        assert transform_point(*p, src, dst) == p


@pytest.mark.parametrize("point", [(181, 0), (0, 91), (float("nan"), 0),
                                  (0, float("inf")), (True, 20), ("113", 20)])
def test_invalid_points_rejected_even_for_identity(point):
    with pytest.raises(ValueError):
        transform_point(*point, "wgs84", "wgs84")


def test_invalid_identity_and_empty_batch_system():
    with pytest.raises(ValueError):
        transform_point(1, 2, "bogus", "bogus")
    with pytest.raises(ValueError):
        transform_coords([], "bogus", "wgs84")
    assert transform_coords([[113, 22, 8]], "wgs84", "gcj02")[0][2] == 8


def test_nested_geometry_collection_metadata_and_null():
    obj = {"type": "FeatureCollection", "bbox": [0, 0, 1, 1], "features": [
        {"type": "Feature", "properties": {"name": "地图"}, "geometry": {
            "type": "GeometryCollection", "bbox": [0, 0, 1, 1], "geometries": [
                {"type": "Point", "coordinates": [113, 22, 12]},
                {"type": "GeometryCollection", "geometries": [
                    {"type": "LineString", "coordinates": [[113, 22], [114, 23]]}]}]}},
        {"type": "Feature", "properties": {}, "geometry": None}]}
    original = copy.deepcopy(obj)
    out = transform_geojson(obj, "wgs84", "gcj02")
    assert obj == original
    assert "bbox" not in out
    geometry = out["features"][0]["geometry"]
    assert "bbox" not in geometry
    assert geometry["geometries"][0]["coordinates"] == [*transform_point(113, 22, "wgs84", "gcj02"), 12]
    assert out["features"][1]["geometry"] is None
    assert out["features"][0]["properties"] == {"name": "地图"}


@pytest.mark.parametrize("obj", [{}, {"type": "Point", "coordinates": [113]},
    {"type": "LineString", "coordinates": [113, 22]},
    {"type": "FeatureCollection", "features": [None]},
    {"type": "GeometryCollection", "geometries": [None]}])
def test_malformed_geometry_rejected(obj):
    with pytest.raises(ValueError):
        transform_geojson(obj, "wgs84", "gcj02")


def test_json_roundtrip_and_invalid_write_does_not_truncate(tmp_path):
    file = tmp_path / "中文.geojson"
    original = {"type": "Point", "coordinates": [113, 22]}
    dump_geojson(original, file)
    assert load_geojson(file) == original
    with pytest.raises(ValueError):
        dump_geojson({"bad": float("nan")}, file)
    assert load_geojson(file) == original


def test_astar_arbitrary_cost_regression():
    net = RoadNetwork()
    for node, lng in [("S", 0), ("A", 50), ("G", 0.01)]:
        net.add_node(node, lng, 0)
    net.add_edge("S", "G", weight=10, bidirectional=False)
    net.add_edge("S", "A", weight=1, bidirectional=False)
    net.add_edge("A", "G", weight=1, bidirectional=False)
    assert net.shortest_path("S", "G") == (["S", "A", "G"], 2)


def test_heap_ties_with_mixed_node_ids_and_zero_weight():
    net = RoadNetwork()
    for node in ["S", 1, ("x",), "G"]:
        net.add_node(node, 0, 0)
    net.add_edge("S", 1, weight=0)
    net.add_edge("S", ("x",), weight=0)
    net.add_edge(1, "G", weight=1)
    assert net.shortest_path("S", "G") == (["S", 1, "G"], 1)


@pytest.mark.parametrize("weight", [-1, float("nan"), float("inf"), True])
def test_invalid_edge_weights(weight):
    net = RoadNetwork()
    net.add_node("A", 0, 0)
    net.add_node("B", 1, 0)
    with pytest.raises(ValueError):
        net.add_edge("A", "B", weight=weight)


def test_graph_endpoints_and_antipodes():
    net = RoadNetwork()
    net.add_node("A", 0, 0)
    assert net.shortest_path("A", "A") == (["A"], 0)
    with pytest.raises(ValueError):
        net.shortest_path("A", "missing", "dijkstra")
    with pytest.raises(ValueError):
        net.add_node("A", 1, 0)
    assert math.isfinite(haversine_m((0, 0), (180, 0)))


def test_random_graphs_against_independent_floyd_warshall():
    rng = random.Random(1234)
    for _ in range(12):
        n = 7
        net = RoadNetwork()
        distances = [[0 if i == j else math.inf for j in range(n)] for i in range(n)]
        for i in range(n):
            net.add_node(i, rng.uniform(-100, 100), rng.uniform(-70, 70))
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < .3:
                    w = rng.randint(0, 30)
                    net.add_edge(i, j, weight=w, bidirectional=False)
                    distances[i][j] = w
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    distances[i][j] = min(distances[i][j], distances[i][k] + distances[k][j])
        for method in ("astar", "dijkstra"):
            for i in range(n):
                for j in range(n):
                    path, cost = net.shortest_path(i, j, method)
                    assert cost == distances[i][j]
                    if path is not None:
                        assert path[0] == i and path[-1] == j


@pytest.mark.parametrize("capacity", [0, -1, 1.5, True, float("nan")])
def test_invalid_cache_capacity(capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity)


def test_cache_update_recency_and_none_values():
    cache = LRUCache(2)
    cache.put("a", None)
    cache.put("b", 2)
    cache.put("a", 3)
    cache.put("c", 4)
    assert cache.get("b", "missing") == "missing"
    assert cache.get("a") == 3
    assert len(cache) == 2
