from algorithms.dijkstra import build_graph, dijkstra


def calculate_route(data, start, destination, mode):
    """
    Calculate a route for a selected mode.

    Returns:
        path
        total_weight
    """

    graph = build_graph(
        data,
        mode=mode
    )

    path, weight = dijkstra(
        graph,
        start,
        destination
    )

    return path, weight