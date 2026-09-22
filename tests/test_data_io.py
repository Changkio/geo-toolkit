"""可选 GIS 依赖；未安装时仅跳过本文件。"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point
from geotk.data_io import _reproject_geometry, convert_file


def test_shapely_point_height_and_empty():
    point = _reproject_geometry(Point(113, 22, 8), "wgs84", "gcj02")
    assert point.x != 113 and point.z == 8
    assert _reproject_geometry(Point(), "wgs84", "gcj02").is_empty


def test_projected_input_rejected(tmp_path):
    source = tmp_path / "projected.gpkg"
    gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1000, 1000)], crs=3857).to_file(source)
    with pytest.raises(ValueError, match="EPSG:4326"):
        convert_file(source, tmp_path / "out.shp", "wgs84", "gcj02")


def test_shapefile_does_not_mislabel_crs(tmp_path):
    source = tmp_path / "source.gpkg"
    output = tmp_path / "shifted.shp"
    gpd.GeoDataFrame({"id": [1]}, geometry=[Point(113, 22)], crs=4326).to_file(source)
    with pytest.warns(UserWarning, match="crs"):
        convert_file(source, output, "wgs84", "gcj02")
    result = gpd.read_file(output)
    assert result.crs is None
    assert result.geometry.iloc[0].x != 113
    with pytest.raises(ValueError, match="已存在"):
        convert_file(source, output, "wgs84", "gcj02")
