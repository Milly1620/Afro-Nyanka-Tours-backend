def test_health(client):
    assert client.get("/health").json() == {"status": "healthy"}


def test_list_tours_empty(client):
    response = client.get("/api/tours/")
    assert response.status_code == 200
    assert response.json() == []
