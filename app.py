import streamlit as st
import pandas as pd

from algorithms.dijkstra import build_graph, dijkstra


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Smart Campus Route Planner",
    page_icon="🗺️",
    layout="centered"
)


# -----------------------------
# Load campus data
# -----------------------------
DATA_FILE = "data/campus_routes.csv"

df = pd.read_csv(DATA_FILE)


# -----------------------------
# Title
# -----------------------------
st.title("🗺️ Smart Campus Route Planner")

st.write(
    "Find the shortest route between two campus locations "
    "while avoiding blocked roads."
)


# -----------------------------
# Road Status Control
# -----------------------------
st.subheader("🚧 Road Status Control")

st.write(
    "Change a road to BLOCKED to simulate a campus road "
    "being unavailable."
)

edited_df = st.data_editor(
    df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "source": "Source",
        "destination": "Destination",
        "distance": st.column_config.NumberColumn(
            "Distance (m)",
            min_value=0
        ),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["OPEN", "BLOCKED"],
            required=True
        )
    },
    disabled=["source", "destination", "distance"],
    key="road_status_editor"
)


# -----------------------------
# Save Road Status
# -----------------------------
if st.button("💾 Save Road Status"):

    edited_df.to_csv(
        DATA_FILE,
        index=False
    )

    st.success(
        "Road status saved successfully!"
    )


# -----------------------------
# Build graph from edited data
# -----------------------------
graph = build_graph(edited_df)


# -----------------------------
# Get all locations
# -----------------------------
locations = sorted(
    set(edited_df["source"]).union(
        set(edited_df["destination"])
    )
)


# -----------------------------
# Campus Map
# -----------------------------
st.subheader("🏫 Campus Map")

dot = """
graph Campus {
    rankdir=LR;
    bgcolor="transparent";

    node [
        shape=box,
        style="rounded,filled",
        fillcolor="lightblue"
    ];

    edge [
        fontcolor="gray"
    ];
"""


# Add nodes
for location in locations:
    dot += f'"{location}";\n'


# Add roads
for _, row in edited_df.iterrows():

    source = row["source"]
    destination = row["destination"]
    distance = row["distance"]
    status = str(row["status"]).upper()

    if status == "OPEN":

        dot += (
            f'"{source}" -- "{destination}" '
            f'[label="{distance} m", '
            'color="gray"];\n'
        )

    else:

        dot += (
            f'"{source}" -- "{destination}" '
            f'[label="{distance} m - BLOCKED", '
            'color="red", '
            'style="dashed", '
            'fontcolor="red"];\n'
        )

dot += "}"

st.graphviz_chart(dot)


# -----------------------------
# Route Selection
# -----------------------------
st.subheader("📍 Choose Your Route")

start = st.selectbox(
    "Start Location",
    locations
)

destination = st.selectbox(
    "Destination",
    locations
)


# -----------------------------
# Find Shortest Route
# -----------------------------
if st.button("🔍 Find Shortest Route"):

    if start == destination:

        st.warning(
            "Start and destination cannot be the same."
        )

    else:

        path, distance = dijkstra(
            graph,
            start,
            destination
        )

        # -----------------------------
        # No route
        # -----------------------------
        if not path:

            st.error(
                "No available route exists between "
                "these locations."
            )

        # -----------------------------
        # Route found
        # -----------------------------
        else:

            st.success(
                "Shortest available route found!"
            )


            # -----------------------------
            # Highlight Selected Route
            # -----------------------------
            st.subheader("🗺️ Selected Route")

            route_edges = set()

            for i in range(len(path) - 1):

                edge = tuple(
                    sorted(
                        [path[i], path[i + 1]]
                    )
                )

                route_edges.add(edge)


            highlighted_dot = """
graph Campus {
    rankdir=LR;
    bgcolor="transparent";

    node [
        shape=box,
        style="rounded,filled",
        fillcolor="lightblue"
    ];

    edge [
        color="gray",
        fontcolor="gray"
    ];
"""


            # Add nodes
            for location in locations:

                if location == start:

                    highlighted_dot += (
                        f'"{location}" '
                        '[fillcolor="lightgreen"];\n'
                    )

                elif location == destination:

                    highlighted_dot += (
                        f'"{location}" '
                        '[fillcolor="lightcoral"];\n'
                    )

                else:

                    highlighted_dot += (
                        f'"{location}";\n'
                    )


            # Add roads
            for _, row in edited_df.iterrows():

                source = row["source"]
                destination_name = row["destination"]
                distance_value = row["distance"]
                status = str(row["status"]).upper()

                edge = tuple(
                    sorted(
                        [source, destination_name]
                    )
                )

                # Highlight selected route
                if edge in route_edges:

                    highlighted_dot += (
                        f'"{source}" -- '
                        f'"{destination_name}" '
                        f'[label="{distance_value} m", '
                        'color="red", '
                        'penwidth=4, '
                        'fontcolor="red"];\n'
                    )

                # Blocked road
                elif status == "BLOCKED":

                    highlighted_dot += (
                        f'"{source}" -- '
                        f'"{destination_name}" '
                        '[label="BLOCKED", '
                        'color="red", '
                        'style="dashed", '
                        'fontcolor="red"];\n'
                    )

                # Normal road
                else:

                    highlighted_dot += (
                        f'"{source}" -- '
                        f'"{destination_name}" '
                        f'[label="{distance_value} m"];\n'
                    )


            highlighted_dot += "}"

            st.graphviz_chart(
                highlighted_dot
            )


            # -----------------------------
            # Shortest Route
            # -----------------------------
            st.subheader("🚶 Shortest Route")

            for i, location in enumerate(path):

                if i == 0:

                    st.write(
                        f"🟢 **START:** {location}"
                    )

                elif i == len(path) - 1:

                    st.write(
                        f"🔴 **DESTINATION:** {location}"
                    )

                else:

                    st.write(
                        f"⬇️ {location}"
                    )


            # -----------------------------
            # Route Details
            # -----------------------------
            st.subheader("📋 Route Details")

            for i in range(len(path) - 1):

                current = path[i]
                next_location = path[i + 1]

                for _, row in edited_df.iterrows():

                    if (
                            (
                                    row["source"] == current
                                    and
                                    row["destination"] == next_location
                            )
                            or
                            (
                                    row["source"] == next_location
                                    and
                                    row["destination"] == current
                            )
                    ):

                        segment_distance = row["distance"]

                        st.write(
                            f"**{current} → {next_location}** "
                            f"— {segment_distance} m"
                        )

                        break


            # -----------------------------
            # Total Distance
            # -----------------------------
            st.divider()

            st.metric(
                "📏 Total Distance",
                f"{distance} metres"
            )