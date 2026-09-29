from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_and_citizen_searches():
    assert client.get("/api/health").status_code == 200
    for payload in ({"query": "Rahul Sharma"}, {"query": "P1001"}, {"query": "PROP1001"}, {"query": "SUR-20000"}, {"query": "KHA-50000"}, {"query": "Ward 1 properties"}):
        response = client.post("/api/search", json=payload)
        assert response.status_code == 200
        assert "results" in response.json()


def test_public_property_map_and_suggestions():
    detail = client.get("/api/properties/P1001")
    assert detail.status_code == 200
    assert detail.json()["location_available"] is True
    assert detail.json()["geojson"]["type"] == "Feature"
    assert client.get("/api/search/suggestions?q=rah").status_code == 200
    viewport = client.get("/api/maps/viewport?north=23.55&south=23.50&east=77.84&west=77.78")
    assert viewport.status_code == 200
    assert viewport.json()["type"] == "FeatureCollection"
    assert client.get("/api/properties/nearby?latitude=23.525&longitude=77.808&radius=1000").status_code == 200


def test_read_only_citizen_surface_and_not_found():
    assert client.put("/api/properties/P1001", json={}).status_code in (401, 405, 422)
    assert client.get("/api/properties/DOES-NOT-EXIST").status_code == 404
