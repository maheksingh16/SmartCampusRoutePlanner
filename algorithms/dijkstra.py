import heapq
import pandas as pd


def build_graph(data, mode="distance"):
    """
    Build the campus graph.

    Modes:
    distance   = shortest physical distance
    fastest    = shortest travel time
    accessible = shortest distance using accessible roads only
    """

    # Accept either a DataFrame or a CSV file path
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        df = pd.read_csv(data)

    graph = {}

    for _, row in df.iterrows():

        source = str(row["source"])
        destination = str(row["destination"])

        distance = float(row["distance"])
        status = str(row["status"]).upper()

        speed = float(row["speed_kmh"])
        accessible = str(row["accessible"]).upper()

        # Make sure both locations exist
        graph.setdefault(source, [])
        graph.setdefault(destination, [])

        # Blocked roads cannot be used
        if status != "OPEN":
            continue

        # Accessible mode only uses accessible roads
        if mode == "accessible" and accessible != "YES":
            continue

        # Calculate the weight used by Dijkstra
        if mode == "fastest":

            # metres -> kilometres
            distance_km = distance / 1000

            # travel time in hours
            travel_time_hours = distance_km / speed

            # convert hours -> minutes
            weight = travel_time_hours * 60

        else:

            # distance and accessible modes
            weight = distance

        # Add both directions because campus roads
        # are currently treated as bidirectional
        graph[source].append(
            (destination, weight)
        )

        graph[destination].append(
            (source, weight)
        )

    return graph


def dijkstra(graph, start, end):
    """
    Find the lowest-weight path from start to end.
    """

    distances = {
        node: float("inf")
        for node in graph
    }

    previous = {
        node: None
        for node in graph
    }

    distances[start] = 0

    priority_queue = [
        (0, start)
    ]

    while priority_queue:

        current_distance, current_node = heapq.heappop(
            priority_queue
        )

        # Ignore outdated queue entries
        if current_distance > distances[current_node]:
            continue

        # Destination reached
        if current_node == end:
            break

        # Explore neighbours
        for neighbor, weight in graph[current_node]:

            new_distance = (
                    current_distance + weight
            )

            if new_distance < distances[neighbor]:

                distances[neighbor] = new_distance

                previous[neighbor] = current_node

                heapq.heappush(
                    priority_queue,
                    (new_distance, neighbor)
                )

    # No path exists
    if distances[end] == float("inf"):
        return [], float("inf")

    # Reconstruct path
    path = []

    current = end

    while current is not None:

        path.append(current)

        current = previous[current]

    path.reverse()

    return path, distances[end]