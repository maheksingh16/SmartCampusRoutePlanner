# Smart Campus Route Planner

Smart Campus Route Planner is a small-scope full-stack campus navigation system that helps users find suitable routes between campus locations using Dijkstra's shortest-path algorithm.

The system considers road distance, traffic conditions, blocked roads, travel speed, and accessibility while calculating routes.

---

## Features

### Campus Route Planning
The system provides three routing modes:

- Shortest Distance
- Fastest Route
- Accessible Route

### Dynamic Road Conditions
- Roads can be marked as OPEN or BLOCKED
- Traffic can be updated as LOW, MEDIUM, or HIGH
- Updated road conditions are stored in PostgreSQL
- Route calculation automatically considers the latest road conditions

### Nearest Facility Finder
Users can find the nearest reachable campus facility such as:

- Library
- Canteen
- Computer Lab
- Auditorium
- Department
- Admin Block
- Gate

### Route Comparison
Users can compare different routing modes using:

- Route
- Number of stops
- Distance
- Estimated travel time

### Campus Map
The application displays campus locations and the selected route using an interactive map.

### Route History
The system keeps the latest five successful route searches during the current session.

### Route Report
Users can download route information as a text report.

---

## System Architecture

User
    |
    v
Streamlit Frontend
    |
    v
API Client
    |
    v
FastAPI Backend
    |
    +-------------------+
    |                   |
    v                   v
Dijkstra Algorithm   PostgreSQL Database
                        |
                +-------+-------+
                |               |
                v               v
            Locations          Roads

---

## Technology Stack

Frontend:
Streamlit

Backend:
FastAPI

Database:
PostgreSQL

ORM:
SQLAlchemy

Algorithm:
Dijkstra's Shortest Path Algorithm

Data Processing:
Pandas

Map Visualization:
PyDeck

API Communication:
Python Requests

API Documentation:
FastAPI Swagger UI

Programming Language:
Python

---

## Project Structure

SmartCampusRoutePlanner/
|
+-- backend/
|   +-- __init__.py
|   +-- database.py
|   +-- main.py
|   +-- models.py
|   +-- seed.py
|
+-- algorithms/
|   +-- dijkstra.py
|   +-- route_comparison.py
|
+-- data/
|   +-- campus_locations.csv
|   +-- campus_routes.csv
|
+-- api_client.py
+-- app.py
+-- pyproject.toml
+-- README.md

---

## How the Routing Works

The campus is represented as a graph.

Each campus location is treated as a node.

Each road connecting two locations is treated as an edge.

The edge weight depends on the selected routing mode.

### Shortest Distance

The system uses physical road distance as the edge weight.

### Fastest Route

The system calculates travel time using road distance and speed.

Traffic conditions are also considered.

Traffic multipliers:

LOW = 1.0

MEDIUM = 1.5

HIGH = 2.5

### Accessible Route

Only roads marked as accessible are considered.

### Blocked Roads

Blocked roads are excluded from the routing graph.

When a road is blocked, Dijkstra can find another available path through the campus network.

---

## Database

PostgreSQL is used as the main database for the application.

The database contains two main tables.

### Locations Table

Fields:

id

name

latitude

longitude

type

### Roads Table

Fields:

id

source

destination

distance

status

speed_kmh

accessible

traffic

---

## Backend API

The FastAPI backend provides the following main endpoints.

GET /

GET /health

GET /locations

GET /roads

PUT /roads/{road_id}

POST /route

The API can be tested using FastAPI Swagger UI.

Local Swagger URL:

http://127.0.0.1:8000/docs

---

## Application Flow

1. The user selects a start location and destination.
2. The user selects a routing mode.
3. Streamlit sends the request to the FastAPI backend.
4. FastAPI retrieves current road information from PostgreSQL.
5. The routing graph is created from the database data.
6. Dijkstra's algorithm calculates the route.
7. FastAPI returns the route, distance, stops, and estimated travel time.
8. Streamlit displays the result on the dashboard and map.

---

## Dynamic Routing Example

Suppose the road between:

Admin Block -> Library

is marked as BLOCKED.

The backend removes that road from the available routing graph.

The system then calculates an alternative path using the remaining available roads.

This allows the application to demonstrate dynamic campus navigation.

---

## Nearest Facility

The nearest facility feature works through the same campus road network.

Instead of simply checking straight-line distance, the system calculates reachable routes through campus roads and identifies the nearest available facility according to the selected routing mode.

---

## Local Setup

### 1. Clone the Repository

git clone https://github.com/maheksingh16/SmartCampusRoutePlanner.git

cd SmartCampusRoutePlanner

### 2. Create Virtual Environment

python -m venv .venv

### 3. Activate Virtual Environment

Windows PowerShell:

.venv\Scripts\Activate.ps1

### 4. Install Dependencies

python -m pip install streamlit pandas pydeck requests fastapi uvicorn sqlalchemy "psycopg[binary]"

### 5. Create PostgreSQL Database

Create a PostgreSQL database named:

smart_campus_db

### 6. Configure Database

Update the PostgreSQL username and password in:

backend/database.py

### 7. Seed the Database

python -m backend.seed

This imports the initial campus locations and roads into PostgreSQL.

### 8. Start FastAPI Backend

python -m uvicorn backend.main:app --reload

Backend:

http://127.0.0.1:8000

Swagger:

http://127.0.0.1:8000/docs

### 9. Start Streamlit Frontend

Open another terminal and run:

python -m streamlit run app.py

Frontend:

http://localhost:8501

---

## Example

Example route:

Start Location:
Admin Block

Destination:
Auditorium

Mode:
Shortest Distance

Example route:

Admin Block
    ->
CSE Department
    ->
Computer Lab
    ->
Auditorium

The system displays:

- Number of stops
- Total distance
- Estimated travel time
- Route details
- Campus map
- Route network

---

## Project Scope

This project is intentionally designed as a small-scope full-stack campus navigation system.

The project focuses on four main areas:

Graph Algorithms

Backend API Development

Database Management

Interactive Frontend

The goal is to demonstrate how a shortest-path algorithm can be integrated into a real application with a backend and persistent database.

---

## Future Improvements

Possible future improvements include:

- Real campus GPS coordinates for individual buildings
- Real-time traffic updates
- Live user location
- Mobile application
- Authentication and role-based access
- Admin dashboard
- Larger campus road network
- Deployment of backend and database to a cloud environment

---

## Author

Mahek Singh

GitHub:

https://github.com/maheksingh16

Repository:

https://github.com/maheksingh16/SmartCampusRoutePlanner

---

## Project Status

Core system completed with:

- Streamlit frontend
- FastAPI backend
- PostgreSQL database
- Dijkstra route calculation
- Traffic-aware routing
- Blocked-road handling
- Accessible routing
- Nearest facility finder
- Route comparison
- Interactive campus map
- Route history
- Route report
