"""坐标转换与 GeoJSON 测试，可直接运行：python tests/test_coord.py"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from geotk.coord_transform import (  # noqa: E402
    bd09_to_gcj02,
    gcj02_to_bd09,
    gcj02_to_wgs84,
    wgs84_to_gcj02,
)
from geotk.geojson_io import load_geojson, transform_geojson  # noqa: E402


def haversine_m(a, b):
    R = 6371000.0
    p1 = (math.radians(a[1]), math.radians(a[0]))
    p2 = (math.radians(b[1]), math.radians(b[0]))
    dphi = p2[0] - p1[0]
    dlmb = p2[1] - p1[1]
    h = math.sin(dphi / 2) ** 2 + math.cos(p1[0]) * math.cos(p2[0]) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def test_overseas_unchanged():
    lng, lat = wgs84_to_gcj02(-74.0, 40.7)  # 纽约，境外
    assert abs(lng + 74.0) < 1e-9 and abs(lat - 40.7) < 1e-9


def test_wgs_gcj_roundtrip():
    p = (113.52, 22.27)  # 珠海
    g = wgs84_to_gcj02(*p)
    assert g != p  # 境内确实发生偏移
    back = gcj02_to_wgs84(*g)
    assert haversine_m(p, back) < 5.0  # 回环误差 < 5m


def test_gcj_bd_roundtrip():
    g = (113.53, 22.28)
    b = gcj02_to_bd09(*g)
    back = bd09_to_gcj02(*b)
    assert haversine_m(g, back) < 2.0


def test_geojson_transform():
    sample = os.path.join(ROOT, "examples", "sample.geojson")
    obj = load_geojson(sample)
    out = transform_geojson(obj, "wgs84", "gcj02")
    p0 = obj["features"][0]["geometry"]["coordinates"]
    q0 = out["features"][0]["geometry"]["coordinates"]
    assert p0 != q0
    # 属性保留
    assert out["features"][0]["properties"]["name"] == "point_a"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("ALL TESTS PASSED")
