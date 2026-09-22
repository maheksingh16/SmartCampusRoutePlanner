import heapq
import pandas as pd


def build_graph(data):
    """
    Build a graph from either:
    - a CSV file path
    - a pandas DataFrame
    """

    # If DataFrame is provided
    if isinstance(data, pd.DataFrame):
        df = data.copy()

    # If CSV file path is provided
    else:
        df = pd.read_csv(data)

    graph = {}

    for _, row in df.iterrows():

        source = row["source"]
        destination = row["destination"]
        distance = float(row["distance"])
        status = str(row["status"]).upper()

        # Add locations to graph
        graph.setdefault(source, [])
        graph.setdefault(destination, [])

        # Only OPEN roads are usable
        if status == "OPEN":

            graph[source].append(
                (destination, distance)
            )

            graph[destination].append(
                (source, distance)
            )

    return graph


def dijkstra(graph, start, end):

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

            new_distance = current_distance + weight

            if new_distance < distances[neighbor]:

                distances[neighbor] = new_distance

                previous[neighbor] = current_node

                heapq.heappush(
                    priority_queue,
                    (new_distance, neighbor)
                )

    # No route exists
    if distances[end] == float("inf"):
        return [], float("inf")

    # Reconstruct shortest path
    path = []

    current = end

    while current is not None:

        path.append(current)

        current = previous[current]

    path.reverse()

    return path, distances[end]