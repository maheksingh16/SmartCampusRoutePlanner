from typing import Literal

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithms.dijkstra import build_graph, dijkstra

from .database import Base, engine, get_db
from .models import Location, Road


# Create database tables
Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APPLICATION
# ============================================================
app = FastAPI(
    title="Smart Campus Route Planner API",
    description="Backend API for campus route planning",
    version="1.0.0"
)


# ============================================================
# REQUEST MODELS
# ============================================================
class RoadUpdate(BaseModel):
    status: str
    traffic: str


class RouteRequest(BaseModel):
    start: str
    destination: str
    mode: Literal[
        "distance",
        "fastest",
        "accessible"
    ] = "distance"


# ============================================================
# CONSTANTS
# ============================================================
TRAFFIC_MULTIPLIER = {
    "LOW": 1.0,
    "MEDIUM": 1.5,
    "HIGH": 2.5
}


# ============================================================
# HELPER: CALCULATE ROUTE STATISTICS
# ============================================================
def calculate_route_stats(path, roads_df):

    total_distance = 0.0
    total_time = 0.0

    for i in range(len(path) - 1):

        current = path[i]
        next_location = path[i + 1]

        matching_rows = roads_df[
            (
                    (roads_df["source"] == current)
                    &
                    (roads_df["destination"] == next_location)
            )
            |
            (
                    (roads_df["source"] == next_location)
                    &
                    (roads_df["destination"] == current)
            )
            ]

        if matching_rows.empty:
            continue

        row = matching_rows.iloc[0]

        distance = float(row["distance"])
        speed = float(row["speed_kmh"])
        traffic = str(row["traffic"]).upper()

        if speed <= 0:
            continue

        multiplier = TRAFFIC_MULTIPLIER.get(
            traffic,
            1.0
        )

        travel_time = (
                              (distance / 1000)
                              / speed
                      ) * 60

        travel_time *= multiplier

        total_distance += distance
        total_time += travel_time

    return total_distance, total_time


# ============================================================
# ROOT
# ============================================================
@app.get("/")
def root():

    return {
        "message": "Smart Campus Route Planner API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "database": "PostgreSQL"
    }


# ============================================================
# GET LOCATIONS
# ============================================================
@app.get("/locations")
def get_locations(
        db: Session = Depends(get_db)
):

    locations = db.execute(
        select(Location)
    ).scalars().all()

    return [
        {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "type": location.type
        }
        for location in locations
    ]


# ============================================================
# GET ROADS
# ============================================================
@app.get("/roads")
def get_roads(
        db: Session = Depends(get_db)
):

    roads = db.execute(
        select(Road)
    ).scalars().all()

    return [
        {
            "id": road.id,
            "source": road.source,
            "destination": road.destination,
            "distance": road.distance,
            "status": road.status,
            "speed_kmh": road.speed_kmh,
            "accessible": road.accessible,
            "traffic": road.traffic
        }
        for road in roads
    ]


# ============================================================
# UPDATE ROAD
# ============================================================
@app.put("/roads/{road_id}")
def update_road(
        road_id: int,
        road_update: RoadUpdate,
        db: Session = Depends(get_db)
):

    road = db.get(
        Road,
        road_id
    )

    if road is None:

        raise HTTPException(
            status_code=404,
            detail="Road not found"
        )

    status = road_update.status.upper().strip()
    traffic = road_update.traffic.upper().strip()

    if status not in {
        "OPEN",
        "BLOCKED"
    }:

        raise HTTPException(
            status_code=400,
            detail="Status must be OPEN or BLOCKED"
        )

    if traffic not in {
        "LOW",
        "MEDIUM",
        "HIGH"
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Traffic must be "
                "LOW, MEDIUM, or HIGH"
            )
        )

    road.status = status
    road.traffic = traffic

    db.commit()
    db.refresh(road)

    return {
        "message": "Road updated successfully",
        "road": {
            "id": road.id,
            "source": road.source,
            "destination": road.destination,
            "distance": road.distance,
            "status": road.status,
            "speed_kmh": road.speed_kmh,
            "accessible": road.accessible,
            "traffic": road.traffic
        }
    }


# ============================================================
# FIND ROUTE
# ============================================================
@app.post("/route")
def find_route(
        request: RouteRequest,
        db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Validate start and destination
    # --------------------------------------------------------
    if request.start == request.destination:

        raise HTTPException(
            status_code=400,
            detail=(
                "Start and destination "
                "cannot be the same."
            )
        )

    # --------------------------------------------------------
    # Get all locations
    # --------------------------------------------------------
    locations = db.execute(
        select(Location)
    ).scalars().all()

    location_names = {
        location.name
        for location in locations
    }

    if request.start not in location_names:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Start location "
                f"'{request.start}' not found."
            )
        )

    if request.destination not in location_names:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Destination "
                f"'{request.destination}' not found."
            )
        )

    # --------------------------------------------------------
    # Get roads from PostgreSQL
    # --------------------------------------------------------
    roads = db.execute(
        select(Road)
    ).scalars().all()

    if not roads:

        raise HTTPException(
            status_code=404,
            detail="No roads are available in the database."
        )

    # --------------------------------------------------------
    # Convert database roads to DataFrame
    #
    # Dijkstra already works with this structure.
    # --------------------------------------------------------
    roads_data = [
        {
            "source": road.source,
            "destination": road.destination,
            "distance": road.distance,
            "status": road.status,
            "speed_kmh": road.speed_kmh,
            "accessible": (
                "YES"
                if road.accessible
                else "NO"
            ),
            "traffic": road.traffic
        }
        for road in roads
    ]

    roads_df = pd.DataFrame(
        roads_data
    )

    # --------------------------------------------------------
    # Build graph
    # --------------------------------------------------------
    graph = build_graph(
        roads_df,
        mode=request.mode
    )

    # --------------------------------------------------------
    # Run Dijkstra
    # --------------------------------------------------------
    path, weight = dijkstra(
        graph,
        request.start,
        request.destination
    )

    # --------------------------------------------------------
    # No route
    # --------------------------------------------------------
    if not path:

        if request.mode == "accessible":

            raise HTTPException(
                status_code=404,
                detail=(
                    "No accessible route is available "
                    "between these locations."
                )
            )

        raise HTTPException(
            status_code=404,
            detail=(
                "No available route exists "
                "between these locations."
            )
        )

    # --------------------------------------------------------
    # Calculate final statistics
    # --------------------------------------------------------
    total_distance, total_time = (
        calculate_route_stats(
            path,
            roads_df
        )
    )

    # --------------------------------------------------------
    # Return route
    # --------------------------------------------------------
    return {
        "start": request.start,
        "destination": request.destination,
        "mode": request.mode,
        "route": path,
        "stops": len(path),
        "distance_m": round(
            total_distance,
            2
        ),
        "travel_time_min": round(
            total_time,
            2
        )
    }