# geo-toolkit：地理数据与路径算法学习演示

本项目用于学习 Python 地理数据处理、图算法、缓存与 HTTP 接口的基本结构。初稿由 AI 生成，随后经 AI 辅助审查、修复和回归测试整理。代码为独立学习示例，不包含“美颜世界／菠萝笔”等商业项目的原始源码。

## 实现的功能

- WGS84、GCJ02、BD09 的单点与批量近似转换。
- GeoJSON 结构的 Point、MultiPoint、LineString、MultiLineString、Polygon、MultiPolygon、GeometryCollection，以及 Feature、FeatureCollection 转换；保留属性与额外坐标维度。
- 内存路网的 Dijkstra 和 A*，支持有向边、非负自定义边权。
- 单进程、非线程安全的 LRU 缓存示例。
- FastAPI 的单点、批量及 GeoJSON 转换接口。
- 可选 GeoPandas 文件读取和 SHP 输出。

各模块使用本地示例数据演示，实际地图路网、实时路况、瓦片与地理编码服务尚未接入。

## 环境与运行

建议使用 Python 3.10 及以上版本，在项目根目录运行。坐标、GeoJSON、图算法与缓存的核心模块只使用标准库。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

只运行服务可安装 requirements.txt。启动后访问 http://127.0.0.1:8000/docs 查看接口；默认仅本机访问。

可选文件转换及相应测试：

```powershell
.\.venv\Scripts\python.exe -m pip install geopandas
.\.venv\Scripts\python.exe -m pytest -q
```

未安装 GeoPandas 时，文件转换测试会跳过。原有标准库测试也可单独执行：python tests/test_coord.py 和 python tests/test_pathfinding.py。

## Python 示例

```python
from geotk.coord_transform import transform_point, transform_coords
from geotk.geojson_io import load_geojson, transform_geojson, dump_geojson

print(transform_point(113.52, 22.27, "wgs84", "gcj02"))
print(transform_coords([[113.52, 22.27, 10]], "wgs84", "bd09"))

source = load_geojson("examples/sample.geojson")
converted = transform_geojson(source, "wgs84", "gcj02")
dump_geojson(converted, "out.geojson")

from geotk.pathfinding import RoadNetwork

net = RoadNetwork()
net.add_node("A", 113.52, 22.27)
net.add_node("B", 113.53, 22.27)
net.add_edge("A", "B")
path, cost = net.shortest_path("A", "B", method="astar")
print(path, cost)  # 默认边权为球面距离（米）

from geotk.cache import LRUCache

cache = LRUCache(capacity=128)
cache.put("example", {"value": 1})
print(cache.get("example"))
```

## HTTP 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| GET | /transform | 经度 lng、纬度 lat、源 src、目标 dst |
| POST | /transform/batch | points 数组、src、dst；最多 10000 点 |
| POST | /geojson/transform | geojson 对象、src、dst |

批量请求体示例：

```json
{"points":[{"lng":113.52,"lat":22.27}],"src":"wgs84","dst":"gcj02"}
```

坐标系名称必须为小写 wgs84 / gcj02 / bd09。无效坐标系返回 400，坐标或请求结构错误返回 422。

## 功能边界

1. **近似坐标转换**：这里的经验数值公式不是官方标准实现，不保证测绘精度。GCJ02 反算使用单步近似，没有全面的权威控制点验证。
2. **区域判断粗略**：以经度 (73.66, 135.05)、纬度 (3.86, 53.55) 的开区间矩形作为转换范围；范围外及边界原样返回。它不等于真实国界，边界附近还可能因偏移跨越阈值而无法准确往返。
3. **GeoJSON 语义**：输出 GCJ02/BD09 后仍保持 GeoJSON 的数据形状，但不符合 RFC 7946 使用 WGS84 的坐标语义，不能直接视为标准 GeoJSON 交换文件。调用者需记录实际坐标系。坐标转换会移除过期 bbox 和 crs；不进行完整几何拓扑、闭合环或自相交校验，也不增密边界。
4. **文件转换**：convert_file 仅接受明确标注 EPSG:4326 的 WGS84 输入，投影数据须预先重投影。GCJ02/BD09 仅输出不带 CRS 标记的 SHP，需自行记录坐标系；拒绝覆盖已有输出及同名 SHP 附件。SHP 字段名长度等格式限制仍由底层驱动决定。
5. **寻路**：默认权重是球面距离，自定义权重可表示一致单位的成本。存在低于球面距离的边权时，A* 自动使用零启发，以保持最短路径正确性；不承诺减少搜索。禁止负数、NaN、无穷边权；节点和邻接表不要直接修改。
6. **缓存和服务**：缓存没有 TTL、持久化、分布式或并发保证。服务没有鉴权、请求体总大小限制、总体 GeoJSON 点数限制、限流或压力验证，仅适合本机学习演示。不要将它直接作为公开生产服务部署。

## 测试说明

测试覆盖坐标输入与范围边界、嵌套 GeometryCollection、高度和属性保留、无效 GeoJSON、JSON 读写、A* 自定义权重、混合类型节点、非负权与不可达情况、LRU 淘汰和更新，以及 HTTP 成功和错误响应。

随机小图使用独立 Floyd–Warshall 计算结果校验 Dijkstra / A*。验证范围限于示例算法正确性与输入边界；测绘精度、真实路网和负载表现需另行评估。

## 目录

- geotk/：核心算法与可选文件转换
- api/：FastAPI 应用
- tests/：原始基础测试与新增回归测试
- examples/sample.geojson：示例输入
- requirements.txt：服务依赖
- requirements-dev.txt：测试依赖

## 许可证

尚未选择项目许可证。
