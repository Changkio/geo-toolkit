"""WGS84 / GCJ02(火星坐标) / BD09(百度) 坐标互转。

学习用途的近似数值实现，并非官方标准或测绘精度保证。
以矩形范围粗略判断转换区域；范围外坐标原样返回。
"""
import math
from numbers import Real

PI = math.pi
A = 6378245.0  # 长半轴
EE = 0.00669342162296594323  # 偏心率平方
X_PI = PI * 3000.0 / 180.0

WGS84, GCJ02, BD09 = "wgs84", "gcj02", "bd09"
SYSTEMS = (WGS84, GCJ02, BD09)


def validate_systems(src, dst):
    if src not in SYSTEMS or dst not in SYSTEMS:
        raise ValueError(f"坐标系必须为 {SYSTEMS}")


def validate_point(lng, lat):
    for value, limit, name in ((lng, 180, "经度"), (lat, 90, "纬度")):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name}必须为数值")
        if not math.isfinite(value) or not -limit <= value <= limit:
            raise ValueError(f"{name}必须为 [-{limit}, {limit}] 内的有限数")


def _out_of_china(lng, lat):
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng, lat):
    validate_point(lng, lat)
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * PI
    magic = math.sin(rad_lat)
    magic = 1.0 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1.0 - EE)) / (magic * sqrt_magic) * PI)
    dlng = (dlng * 180.0) / (A / sqrt_magic * math.cos(rad_lat) * PI)
    return lng + dlng, lat + dlat


def gcj02_to_wgs84(lng, lat):
    """单步近似反算；误差随位置变化，不作精度保证。"""
    validate_point(lng, lat)
    if _out_of_china(lng, lat):
        return lng, lat
    glng, glat = wgs84_to_gcj02(lng, lat)
    return lng * 2.0 - glng, lat * 2.0 - glat


def gcj02_to_bd09(lng, lat):
    validate_point(lng, lat)
    if _out_of_china(lng, lat):
        return lng, lat
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * X_PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * X_PI)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd09_to_gcj02(bd_lng, bd_lat):
    validate_point(bd_lng, bd_lat)
    if _out_of_china(bd_lng, bd_lat):
        return bd_lng, bd_lat
    x = bd_lng - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    return z * math.cos(theta), z * math.sin(theta)


def wgs84_to_bd09(lng, lat):
    return gcj02_to_bd09(*wgs84_to_gcj02(lng, lat))


def bd09_to_wgs84(bd_lng, bd_lat):
    return gcj02_to_wgs84(*bd09_to_gcj02(bd_lng, bd_lat))


_CONVERTERS = {
    (WGS84, GCJ02): wgs84_to_gcj02,
    (GCJ02, WGS84): gcj02_to_wgs84,
    (GCJ02, BD09): gcj02_to_bd09,
    (BD09, GCJ02): bd09_to_gcj02,
    (WGS84, BD09): wgs84_to_bd09,
    (BD09, WGS84): bd09_to_wgs84,
}


def transform_point(lng, lat, src, dst):
    validate_systems(src, dst)
    validate_point(lng, lat)
    if src == dst:
        return lng, lat
    conv = _CONVERTERS.get((src, dst))
    if conv is None:
        raise ValueError(f"不支持的坐标转换: {src} -> {dst}")
    return conv(lng, lat)


def transform_coords(points, src, dst):
    """批量转换 [[lng, lat, ...], ...]，保留额外维度。"""
    validate_systems(src, dst)
    result = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            raise ValueError("每个坐标必须至少包含经度和纬度")
        result.append([*transform_point(p[0], p[1], src, dst), *p[2:]])
    return result
