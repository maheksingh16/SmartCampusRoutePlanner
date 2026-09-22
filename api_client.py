import requests


API_BASE_URL = "http://127.0.0.1:8000"


def get_locations():
    response = requests.get(
        f"{API_BASE_URL}/locations",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def get_roads():
    response = requests.get(
        f"{API_BASE_URL}/roads",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def update_road(
        road_id,
        status,
        traffic
):
    response = requests.put(
        f"{API_BASE_URL}/roads/{road_id}",
        json={
            "status": status,
            "traffic": traffic
        },
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def find_route(
        start,
        destination,
        mode
):
    response = requests.post(
        f"{API_BASE_URL}/route",
        json={
            "start": start,
            "destination": destination,
            "mode": mode
        },
        timeout=5
    )

    response.raise_for_status()

    return response.json()