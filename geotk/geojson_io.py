"""GeoJSON 形状的坐标转换；保留属性与高度，不执行完整拓扑验证。"""
import copy
import json
import math
from numbers import Real

from .coord_transform import transform_point, validate_systems

_DEPTH = {"Point": 0, "MultiPoint": 1, "LineString": 1,
          "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}


def _walk(coords, depth, src, dst):
    if not isinstance(coords, (list, tuple)):
        raise ValueError("coordinates 必须为数组")
    if depth:
        return [_walk(c, depth - 1, src, dst) for c in coords]
    if len(coords) < 2:
        raise ValueError("坐标至少需要经度和纬度")
    for value in coords:
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError("坐标必须为有限数值")
    return [*transform_point(coords[0], coords[1], src, dst), *coords[2:]]


def _convert(obj, src, dst):
    if not isinstance(obj, dict):
        raise ValueError("GeoJSON 对象必须为字典")
    kind = obj.get("type")
    if kind == "FeatureCollection":
        items = obj.get("features")
        if not isinstance(items, list):
            raise ValueError("FeatureCollection 必须包含 features 数组")
        for feature in items:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError("features 中只能包含 Feature")
            _convert(feature, src, dst)
    elif kind == "Feature":
        if "geometry" not in obj:
            raise ValueError("Feature 必须包含 geometry，可为 null")
        if obj["geometry"] is not None:
            _geometry(obj["geometry"], src, dst)
    else:
        _geometry(obj, src, dst)
    if src != dst:
        # 旧边界框与旧 CRS 会错误描述转换后的坐标，移除过期值。
        obj.pop("bbox", None)
        obj.pop("crs", None)


def _geometry(geometry, src, dst):
    if not isinstance(geometry, dict):
        raise ValueError("geometry 必须为对象")
    kind = geometry.get("type")
    if kind == "GeometryCollection":
        items = geometry.get("geometries")
        if not isinstance(items, list):
            raise ValueError("GeometryCollection 必须包含 geometries 数组")
        for item in items:
            _geometry(item, src, dst)
    elif kind in _DEPTH:
        geometry["coordinates"] = _walk(geometry.get("coordinates"), _DEPTH[kind], src, dst)
    else:
        raise ValueError(f"不支持的几何类型: {kind}")
    if src != dst:
        geometry.pop("bbox", None)
        geometry.pop("crs", None)


def transform_geojson(geojson: dict, src: str, dst: str) -> dict:
    """返回新对象。GCJ02/BD09 输出不是严格 RFC 7946 的 WGS84 GeoJSON。"""
    validate_systems(src, dst)
    obj = copy.deepcopy(geojson)
    _convert(obj, src, dst)
    return obj


def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_geojson(geojson: dict, path: str) -> None:
    # 先序列化，输入含非有限值时不会截断已有文件。
    text = json.dumps(geojson, ensure_ascii=False, indent=2, allow_nan=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
