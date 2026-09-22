"""geo-toolkit FastAPI 服务。

启动：uvicorn api.main:app --reload
文档：启动后访问 http://127.0.0.1:8000/docs
"""
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from geotk.coord_transform import (
    SYSTEMS,
    transform_coords,
    transform_point,
)
from geotk.geojson_io import transform_geojson

app = FastAPI(
    title="geo-toolkit API",
    version="0.1.0",
    description="WGS84 / GCJ02 / BD09 坐标转换与 GeoJSON 处理",
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # 不回显原始输入：非标准 JSON 的 NaN/Infinity 无法安全写回 JSON 响应。
    details = [{key: error[key] for key in ("loc", "msg", "type")}
               for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


class Point(BaseModel):
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)


class BatchRequest(BaseModel):
    points: List[Point] = Field(max_length=10000)
    src: str
    dst: str


class GeoJSONRequest(BaseModel):
    geojson: dict
    src: str
    dst: str


def _check_system(src: str, dst: str):
    if src not in SYSTEMS or dst not in SYSTEMS:
        raise HTTPException(status_code=400, detail=f"坐标系必须为 {SYSTEMS}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/transform")
def transform(src: str, dst: str,
              lng: float = Query(ge=-180, le=180, allow_inf_nan=False),
              lat: float = Query(ge=-90, le=90, allow_inf_nan=False)):
    _check_system(src, dst)
    x, y = transform_point(lng, lat, src, dst)
    return {"lng": x, "lat": y, "src": src, "dst": dst}


@app.post("/transform/batch")
def transform_batch(req: BatchRequest):
    _check_system(req.src, req.dst)
    pts = [[p.lng, p.lat] for p in req.points]
    return {"points": transform_coords(pts, req.src, req.dst)}


@app.post("/geojson/transform")
def transform_geojson_endpoint(req: GeoJSONRequest):
    _check_system(req.src, req.dst)
    try:
        return transform_geojson(req.geojson, req.src, req.dst)
    except (ValueError, TypeError, RecursionError) as exc:
        raise HTTPException(status_code=422, detail="GeoJSON 结构或坐标无效") from exc
