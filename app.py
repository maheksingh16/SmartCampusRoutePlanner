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
    "Find the best available campus route based on "
    "distance, travel time, or accessibility."
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
    width="stretch",
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
        ),

        "speed_kmh": st.column_config.NumberColumn(
            "Speed (km/h)",
            min_value=0.1
        ),

        "accessible": st.column_config.SelectboxColumn(
            "Accessible",
            options=["YES", "NO"],
            required=True
        )
    },
    disabled=[
        "source",
        "destination",
        "distance",
        "speed_kmh",
        "accessible"
    ],
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
            f'[label="{distance} m", color="gray"];\n'
        )

    else:

        dot += (
            f'"{source}" -- "{destination}" '
            f'[label="{distance} m - BLOCKED", '
            'color="red", style="dashed", fontcolor="red"];\n'
        )


dot += "}"

st.graphviz_chart(dot)


# -----------------------------
# Route Selection
# -----------------------------
st.subheader("📍 Choose Your Route")

route_mode = st.selectbox(
    "🧭 Route Mode",
    [
        "Shortest Distance",
        "Fastest Route",
        "Accessible Route"
    ]
)

start = st.selectbox(
    "Start Location",
    locations
)

destination = st.selectbox(
    "Destination",
    locations
)


# -----------------------------
# Find Route
# -----------------------------
if st.button("🔍 Find Route"):

    # -----------------------------
    # Convert route mode
    # -----------------------------
    if route_mode == "Shortest Distance":

        mode = "distance"

    elif route_mode == "Fastest Route":

        mode = "fastest"

    else:

        mode = "accessible"


    # -----------------------------
    # Validate locations
    # -----------------------------
    if start == destination:

        st.warning(
            "Start and destination cannot be the same."
        )

    else:

        # -----------------------------
        # Build current graph
        # -----------------------------
        graph = build_graph(
            edited_df,
            mode=mode
        )

        # -----------------------------
        # Find current route
        # -----------------------------
        path, weight = dijkstra(
            graph,
            start,
            destination
        )


        # -----------------------------
        # No route
        # -----------------------------
        if not path:

            if route_mode == "Accessible Route":

                st.error(
                    "No accessible route is available "
                    "between these locations."
                )

            else:

                st.error(
                    "No available route exists between "
                    "these locations."
                )


        # -----------------------------
        # Route found
        # -----------------------------
        else:

            # -----------------------------
            # Success message
            # -----------------------------
            if route_mode == "Shortest Distance":

                st.success(
                    "Shortest distance route found!"
                )

            elif route_mode == "Fastest Route":

                st.success(
                    "Fastest available route found!"
                )

            else:

                st.success(
                    "Accessible route found!"
                )


            # -----------------------------
            # Calculate Route Statistics
            # -----------------------------
            total_distance = 0.0
            total_time = 0.0


            for i in range(len(path) - 1):

                current = path[i]
                next_location = path[i + 1]


                for _, row in edited_df.iterrows():

                    is_same_road = (
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
                    )


                    if is_same_road:

                        segment_distance = float(
                            row["distance"]
                        )

                        speed = float(
                            row["speed_kmh"]
                        )

                        segment_time = (
                                               (segment_distance / 1000)
                                               / speed
                                       ) * 60


                        total_distance += (
                            segment_distance
                        )

                        total_time += (
                            segment_time
                        )

                        break


            # -----------------------------
            # Count blocked roads
            # -----------------------------
            blocked_count = int(
                (
                        edited_df["status"]
                        .astype(str)
                        .str.upper()
                        == "BLOCKED"
                ).sum()
            )


            # -----------------------------
            # Alternative Route Detection
            # -----------------------------
            baseline_df = edited_df.copy()

            # Temporarily make all roads OPEN
            baseline_df["status"] = "OPEN"


            baseline_graph = build_graph(
                baseline_df,
                mode=mode
            )


            baseline_path, baseline_weight = dijkstra(
                baseline_graph,
                start,
                destination
            )


            # -----------------------------
            # Detect route change
            # -----------------------------
            route_changed = (
                    baseline_path
                    and
                    baseline_path != path
            )


            if route_changed:

                st.warning(
                    "🚧 The preferred route is unavailable. "
                    "An alternative route has been selected."
                )


                st.write(
                    "**Normal route:** "
                    + " → ".join(baseline_path)
                )


                st.write(
                    "**Current route:** "
                    + " → ".join(path)
                )


                if mode == "fastest":

                    extra_time = (
                            total_time - baseline_weight
                    )

                    st.info(
                        f"⏱️ Additional travel time: "
                        f"{extra_time:.2f} minutes"
                    )

                else:

                    extra_distance = (
                            total_distance - baseline_weight
                    )

                    st.info(
                        f"📏 Additional distance: "
                        f"{extra_distance:.0f} metres"
                    )


            elif blocked_count > 0:

                st.info(
                    f"🚧 {blocked_count} blocked road(s) "
                    "are present in the campus network. "
                    "The selected route was not affected."
                )


            # -----------------------------
            # Route Summary Dashboard
            # -----------------------------
            st.subheader("📊 Route Summary")


            col1, col2, col3, col4 = st.columns(4)


            with col1:

                st.metric(
                    "📍 Stops",
                    len(path)
                )


            with col2:

                st.metric(
                    "📏 Distance",
                    f"{total_distance:.0f} m"
                )


            with col3:

                st.metric(
                    "⏱️ Travel Time",
                    f"{total_time:.2f} min"
                )


            with col4:

                st.metric(
                    "🧭 Mode",
                    route_mode
                )


            # -----------------------------
            # Selected Route Map
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


            # -----------------------------
            # Add Nodes
            # -----------------------------
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


            # -----------------------------
            # Add Roads
            # -----------------------------
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


                # Selected route
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
            # Route Steps
            # -----------------------------
            st.subheader(
                f"🚶 {route_mode}"
            )


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

                    is_same_road = (
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
                    )


                    if is_same_road:

                        segment_distance = float(
                            row["distance"]
                        )

                        speed = float(
                            row["speed_kmh"]
                        )

                        segment_time = (
                                               (segment_distance / 1000)
                                               / speed
                                       ) * 60


                        if route_mode == "Fastest Route":

                            st.write(
                                f"**{current} → {next_location}** "
                                f"— {segment_distance:.0f} m "
                                f"({segment_time:.2f} min)"
                            )

                        else:

                            st.write(
                                f"**{current} → {next_location}** "
                                f"— {segment_distance:.0f} m"
                            )

                        break


            # -----------------------------
            # Final Result
            # -----------------------------
            st.divider()


            if route_mode == "Fastest Route":

                st.metric(
                    "⏱️ Estimated Travel Time",
                    f"{total_time:.2f} minutes"
                )

                st.write(
                    f"Total route distance: "
                    f"**{total_distance:.0f} metres**"
                )

            else:

                st.metric(
                    "📏 Total Distance",
                    f"{total_distance:.0f} metres"
                )