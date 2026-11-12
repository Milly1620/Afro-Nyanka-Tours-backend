import pytest
from fastapi.routing import APIRoute

from src.api.routes import analytics

ANALYTICS = [
    (method, f"/api/analytics{route.path}")
    for route in analytics.router.routes
    if isinstance(route, APIRoute)
    for method in route.methods
]

PROTECTED = [
    ("POST", "/api/tours/"),
    ("POST", "/api/tours/locations/"),
    ("PATCH", "/api/tours/tours/popular/1"),
    ("POST", "/api/tours/1/upload-main-image"),
    ("POST", "/api/tours/1/upload-gallery-images"),
    ("DELETE", "/api/tours/1/remove-gallery-image"),
    ("POST", "/api/tours/1/add-location"),
    ("DELETE", "/api/tours/1/remove-location"),
    ("PATCH", "/api/tours/1/update-location-order"),
    ("PATCH", "/api/tours/1/reorder-locations"),
    ("GET", "/api/bookings/"),
    ("GET", "/api/bookings/1"),
    ("GET", "/api/bookings/1/summary"),
    ("POST", "/api/bookings/test-email"),
    ("POST", "/api/contact/test"),
] + ANALYTICS


def test_analytics_routes_discovered():
    assert len(ANALYTICS) >= 12


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_routes_require_admin(client, admin_headers, method, path):
    assert client.request(method, path).status_code == 401
    assert client.request(method, path, headers=admin_headers).status_code != 401


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/api/tours/", None),
        ("GET", "/api/tours/locations/", None),
        ("GET", "/api/tours/tours/countries", None),
        ("POST", "/api/bookings/", {}),
        ("POST", "/api/contact/", {}),
    ],
)
def test_public_routes_stay_open(client, method, path, body):
    assert client.request(method, path, json=body).status_code != 401


def test_cors_origins_setting(monkeypatch):
    from src.core.config import Settings

    s = Settings(_env_file=None, DATABASE_URL="x", debug=True, cors_origins="https://a.com, https://b.com")
    assert s.cors_origin_list == ["https://a.com", "https://b.com"]
    assert Settings(_env_file=None, DATABASE_URL="x", debug=True).cors_origin_list == ["*"]
