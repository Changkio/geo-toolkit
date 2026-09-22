"""真实 ASGI 请求覆盖正常接口与无效输入响应。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_and_transform_endpoints():
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/transform", params={"lng": 113, "lat": 22, "src": "wgs84", "dst": "gcj02"})
    assert response.status_code == 200 and response.json()["lng"] != 113
    response = client.post("/transform/batch", json={"points": [{"lng": 113, "lat": 22}], "src": "wgs84", "dst": "gcj02"})
    assert response.status_code == 200 and len(response.json()["points"]) == 1


@pytest.mark.parametrize("lng,lat", [(181, 22), (113, 91), ("nan", 22), ("inf", 22)])
def test_api_invalid_coordinates(lng, lat):
    assert client.get("/transform", params={"lng": lng, "lat": lat, "src": "wgs84", "dst": "gcj02"}).status_code == 422


def test_api_invalid_system_and_geometry():
    assert client.get("/transform", params={"lng": 113, "lat": 22, "src": "bad", "dst": "bad"}).status_code == 400
    for geojson in [{}, {"type": "Point", "coordinates": [113]}, {"type": "Point", "coordinates": [181, 22]}]:
        response = client.post("/geojson/transform", json={"geojson": geojson, "src": "wgs84", "dst": "gcj02"})
        assert response.status_code == 422


def test_api_geometry_collection():
    response = client.post("/geojson/transform", json={"geojson": {
        "type": "GeometryCollection", "geometries": [{"type": "Point", "coordinates": [113, 22]}]},
        "src": "wgs84", "dst": "gcj02"})
    assert response.status_code == 200
    assert response.json()["geometries"][0]["coordinates"] != [113, 22]


def test_batch_size_and_coordinate_limits():
    assert client.post("/transform/batch", json={"points": [{"lng": 200, "lat": 0}], "src": "wgs84", "dst": "gcj02"}).status_code == 422
    assert client.post("/transform/batch", json={"points": [{"lng": 0, "lat": 0}] * 10001, "src": "wgs84", "dst": "gcj02"}).status_code == 422


def test_nonfinite_json_input_has_json_error_response():
    for value in ("NaN", "Infinity", "-Infinity"):
        payload = '{"points":[{"lng":' + value + ',"lat":0}],"src":"wgs84","dst":"gcj02"}'
        response = client.post("/transform/batch", content=payload, headers={"content-type": "application/json"})
        assert response.status_code == 422
        assert "detail" in response.json()
