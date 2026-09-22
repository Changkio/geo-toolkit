"""可选矢量文件转换：仅接受标注为 EPSG:4326 的 WGS84 输入。

GCJ02/BD09 不是标准 EPSG CRS，输出不携带错误的 WGS84 CRS 标记。
"""
from pathlib import Path

from .coord_transform import transform_point, validate_systems


def _reproject_geometry(geom, src, dst):
    from shapely.ops import transform as shapely_transform

    if geom is None or geom.is_empty:
        return geom

    def func(x, y, z=None):
        if hasattr(x, "__iter__"):
            pairs = [transform_point(a, b, src, dst) for a, b in zip(x, y)]
            tx, ty = zip(*pairs)
        else:
            tx, ty = transform_point(x, y, src, dst)
        return (tx, ty) if z is None else (tx, ty, z)

    return shapely_transform(func, geom)


def convert_file(input_path: str, output_path: str, src: str, dst: str) -> None:
    validate_systems(src, dst)
    if src != "wgs84":
        raise ValueError("文件转换仅支持 WGS84 输入；GCJ02/BD09 请使用显式坐标转换接口")
    if Path(input_path).resolve() == Path(output_path).resolve():
        raise ValueError("请使用不同的输出路径，避免覆盖原始数据")
    if dst != "wgs84" and Path(output_path).suffix.lower() != ".shp":
        raise ValueError("偏移坐标文件仅支持输出为无 CRS 的 SHP；避免驱动自动标记为 WGS84")
    if Path(output_path).exists() or (Path(output_path).suffix.lower() == ".shp" and any(Path(output_path).parent.glob(Path(output_path).stem + ".*"))):
        raise ValueError("输出文件或同名 SHP 附件已存在，请选择新路径")
    try:
        import geopandas
    except ImportError as exc:
        raise ImportError("文件转换需要可选依赖：pip install geopandas") from exc
    gdf = geopandas.read_file(input_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        raise ValueError("输入必须明确标注 EPSG:4326；投影坐标请先使用 GIS 工具重投影")
    gdf = gdf.copy()
    gdf["geometry"] = gdf["geometry"].apply(lambda g: _reproject_geometry(g, src, dst))
    if dst != "wgs84":
        # 不应将偏移坐标标记为 WGS84；调用方需另行记录实际坐标系。
        gdf = gdf.set_crs(None, allow_override=True)
    gdf.to_file(output_path, encoding="utf-8")
