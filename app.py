import streamlit as st
import pandas as pd
import pydeck as pdk
import requests

from api_client import (
    get_locations,
    get_roads,
    update_road,
    find_route
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Smart Campus Route Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# PROFESSIONAL UI STYLING
# ============================================================
st.markdown(
    """
    <style>
        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,0.18);
            border-radius: 14px;
            padding: 0.8rem;
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 700;
            min-height: 2.7rem;
        }

        div[data-testid="stExpander"] {
            border-radius: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================
if "route_history" not in st.session_state:
    st.session_state.route_history = []


# ============================================================
# CONSTANTS
# ============================================================
TRAFFIC_MULTIPLIER = {
    "LOW": 1.0,
    "MEDIUM": 1.5,
    "HIGH": 2.5
}

FACILITY_LABELS = {
    "LIBRARY": "📚 Library",
    "CANTEEN": "🍴 Canteen",
    "LAB": "💻 Computer Lab",
    "AUDITORIUM": "🎭 Auditorium",
    "GATE": "🚪 Gate",
    "ADMIN": "🏢 Admin Block",
    "DEPARTMENT": "🏫 Department"
}


# ============================================================
# HELPERS
# ============================================================
def format_facility_type(facility_type):
    return FACILITY_LABELS.get(
        facility_type,
        facility_type.title()
    )


def calculate_route_stats(path, data):
    total_distance = 0.0
    total_time = 0.0

    for i in range(len(path) - 1):
        current = path[i]
        next_location = path[i + 1]

        matching_rows = data[
            (
                    (data["source"] == current)
                    &
                    (data["destination"] == next_location)
            )
            |
            (
                    (data["source"] == next_location)
                    &
                    (data["destination"] == current)
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

        segment_time = (
                               (distance / 1000)
                               / speed
                       ) * 60

        segment_time *= multiplier

        total_distance += distance
        total_time += segment_time

    return total_distance, total_time


def build_network_graph(data):
    dot = """
graph Campus {
    rankdir=LR;
    bgcolor="transparent";

    node [
        shape=box,
        style="rounded,filled",
        fillcolor="lightblue",
        fontname="Arial",
        fontsize=11
    ];

    edge [
        fontname="Arial",
        fontsize=9,
        fontcolor="gray"
    ];
"""

    network_locations = sorted(
        set(data["source"]).union(
            set(data["destination"])
        )
    )

    for location in network_locations:
        dot += f'"{location}";\n'

    for _, row in data.iterrows():
        source = row["source"]
        destination = row["destination"]
        distance = row["distance"]
        status = str(row["status"]).upper()
        traffic = str(row["traffic"]).upper()

        if status == "OPEN":
            dot += (
                f'"{source}" -- "{destination}" '
                f'[label="{distance} m | {traffic}"];\n'
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
    return dot


def build_selected_route_graph(
        data,
        path,
        start,
        destination
):
    route_edges = set()

    for i in range(len(path) - 1):
        route_edges.add(
            tuple(
                sorted(
                    [path[i], path[i + 1]]
                )
            )
        )

    dot = """
graph Campus {
    rankdir=LR;
    bgcolor="transparent";

    node [
        shape=box,
        style="rounded,filled",
        fillcolor="lightblue",
        fontname="Arial",
        fontsize=11
    ];

    edge [
        color="gray",
        fontname="Arial",
        fontsize=9
    ];
"""

    network_locations = sorted(
        set(data["source"]).union(
            set(data["destination"])
        )
    )

    for location in network_locations:
        if location == start:
            dot += (
                f'"{location}" '
                '[fillcolor="lightgreen"];\n'
            )
        elif location == destination:
            dot += (
                f'"{location}" '
                '[fillcolor="lightcoral"];\n'
            )
        else:
            dot += f'"{location}";\n'

    for _, row in data.iterrows():
        source = row["source"]
        destination_name = row["destination"]
        distance = row["distance"]
        status = str(row["status"]).upper()

        edge = tuple(
            sorted(
                [
                    source,
                    destination_name
                ]
            )
        )

        if edge in route_edges:
            dot += (
                f'"{source}" -- '
                f'"{destination_name}" '
                f'[label="{distance} m", '
                'color="red", '
                'penwidth=4, '
                'fontcolor="red"];\n'
            )

        elif status == "BLOCKED":
            dot += (
                f'"{source}" -- '
                f'"{destination_name}" '
                '[label="BLOCKED", '
                'color="red", '
                'style="dashed", '
                'fontcolor="red"];\n'
            )

        else:
            dot += (
                f'"{source}" -- '
                f'"{destination_name}" '
                f'[label="{distance} m"];\n'
            )

    dot += "}"
    return dot


def show_route_map(path, locations_df):
    route_locations = locations_df[
        locations_df["location"].isin(path)
    ].copy()

    if route_locations.empty:
        st.warning(
            "No coordinates found for this route."
        )
        return

    route_locations["route_order"] = (
        route_locations["location"].apply(
            lambda location: path.index(location)
        )
    )

    route_locations = (
        route_locations
        .sort_values("route_order")
    )

    route_coordinates = [
        [
            float(row["longitude"]),
            float(row["latitude"])
        ]
        for _, row in route_locations.iterrows()
    ]

    campus_points = locations_df.copy()

    location_layer = pdk.Layer(
        "ScatterplotLayer",
        data=campus_points,
        get_position="[longitude, latitude]",
        get_radius=35,
        pickable=True,
        auto_highlight=True
    )

    label_layer = pdk.Layer(
        "TextLayer",
        data=campus_points,
        get_position="[longitude, latitude]",
        get_text="location",
        get_size=15,
        get_pixel_offset="[0, -28]",
        pickable=False
    )

    route_layer = pdk.Layer(
        "PathLayer",
        data=pd.DataFrame(
            {
                "path": [
                    route_coordinates
                ]
            }
        ),
        get_path="path",
        get_width=8,
        pickable=True
    )

    campus_map = pdk.Deck(
        map_style=None,

        initial_view_state=pdk.ViewState(
            latitude=float(
                route_locations["latitude"].mean()
            ),
            longitude=float(
                route_locations["longitude"].mean()
            ),
            zoom=16,
            pitch=0
        ),

        layers=[
            location_layer,
            label_layer,
            route_layer
        ],

        tooltip={
            "text": "{location}"
        }
    )

    st.pydeck_chart(
        campus_map,
        width="stretch"
    )


def convert_roads_to_dataframe(roads):
    roads_df = pd.DataFrame(roads)

    if roads_df.empty:
        return roads_df

    roads_df["accessible"] = roads_df[
        "accessible"
    ].apply(
        lambda value: "YES"
        if value
        else "NO"
    )

    return roads_df


def save_changed_roads(
        original_df,
        edited_df
):
    changes = 0

    for _, edited_row in edited_df.iterrows():
        original_rows = original_df[
            original_df["id"]
            == edited_row["id"]
            ]

        if original_rows.empty:
            continue

        original_row = original_rows.iloc[0]

        status_changed = (
                str(original_row["status"]).upper()
                !=
                str(edited_row["status"]).upper()
        )

        traffic_changed = (
                str(original_row["traffic"]).upper()
                !=
                str(edited_row["traffic"]).upper()
        )

        if status_changed or traffic_changed:
            update_road(
                int(edited_row["id"]),
                str(edited_row["status"]),
                str(edited_row["traffic"])
            )

            changes += 1

    return changes


def get_locations_list(locations_df):
    return sorted(
        locations_df["location"].tolist()
    )


def add_route_to_history(
        start,
        destination,
        route_mode,
        result
):
    record = {
        "start": start,
        "destination": destination,
        "mode": route_mode,
        "path": result["route"].copy(),
        "distance": result["distance_m"],
        "time": result["travel_time_min"]
    }

    if (
            not st.session_state.route_history
            or
            st.session_state.route_history[0]
            != record
    ):
        st.session_state.route_history.insert(
            0,
            record
        )

    st.session_state.route_history = (
        st.session_state.route_history[:5]
    )


def show_error_from_request(error, fallback):
    if isinstance(error, requests.HTTPError):
        try:
            detail = error.response.json().get(
                "detail",
                fallback
            )
        except Exception:
            detail = fallback

        st.error(detail)

    else:
        st.error(fallback)


# ============================================================
# LOAD DATA FROM BACKEND
# ============================================================
try:
    locations_response = get_locations()
    roads_response = get_roads()

except requests.RequestException as error:
    st.error(
        "FastAPI backend is currently unavailable."
    )
    st.code(str(error))
    st.info(
        "Start the backend with: "
        "python -m uvicorn backend.main:app --reload"
    )
    st.stop()


locations_df = pd.DataFrame(
    locations_response
).rename(
    columns={
        "name": "location"
    }
)

db_roads_df = convert_roads_to_dataframe(
    roads_response
)

if locations_df.empty or db_roads_df.empty:
    st.error(
        "The backend returned incomplete campus data."
    )
    st.stop()


locations = get_locations_list(
    locations_df
)


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("🗺️ Campus Planner")
    st.caption("Campus navigation dashboard")

    st.divider()

    open_roads = int(
        (
                db_roads_df["status"]
                .astype(str)
                .str.upper()
                == "OPEN"
        ).sum()
    )

    blocked_roads = int(
        (
                db_roads_df["status"]
                .astype(str)
                .str.upper()
                == "BLOCKED"
        ).sum()
    )

    facilities = int(
        locations_df[
            locations_df["type"]
            .astype(str)
            .str.upper()
            != "GATE"
            ].shape[0]
    )

    st.metric(
        "🟢 Open Roads",
        open_roads
    )

    st.metric(
        "🚧 Blocked Roads",
        blocked_roads
    )

    st.metric(
        "📍 Locations",
        len(locations)
    )

    st.metric(
        "🏫 Facilities",
        facilities
    )

    st.divider()

    st.markdown(
        "**System**"
    )

    st.caption(
        "Frontend: Streamlit"
    )

    st.caption(
        "Backend: FastAPI"
    )

    st.caption(
        "Database: PostgreSQL"
    )

    st.caption(
        "Algorithm: Dijkstra"
    )

    st.divider()

    st.markdown(
        "**Traffic Model**"
    )

    st.write("🟢 LOW × 1.0")
    st.write("🟡 MEDIUM × 1.5")
    st.write("🔴 HIGH × 2.5")


# ============================================================
# HERO
# ============================================================
st.title("🗺️ Smart Campus Route Planner")
st.caption(
    "Intelligent campus navigation using Dijkstra's algorithm, "
    "traffic conditions, road availability, accessibility, "
    "FastAPI and PostgreSQL."
)


# ============================================================
# TOP DASHBOARD
# ============================================================
summary1, summary2, summary3, summary4 = st.columns(4)

with summary1:
    st.metric(
        "📍 Campus Locations",
        len(locations)
    )

with summary2:
    st.metric(
        "🛣️ Total Roads",
        len(db_roads_df)
    )

with summary3:
    st.metric(
        "🚧 Blocked Roads",
        blocked_roads
    )

with summary4:
    st.metric(
        "🏫 Facilities",
        facilities
    )


# ============================================================
# MAIN TABS
# ============================================================
route_tab, facility_tab, network_tab, road_tab, history_tab = st.tabs(
    [
        "📍 Route Planner",
        "🏫 Facility Finder",
        "🗺️ Campus Network",
        "🚧 Road Control",
        "🕘 History"
    ]
)


# ============================================================
# ROUTE PLANNER
# ============================================================
with route_tab:

    st.subheader("📍 Plan Your Route")
    st.caption(
        "Choose a routing objective, select locations, and calculate the best available path."
    )

    col1, col2, col3 = st.columns(
        [1, 1.2, 1.2]
    )

    with col1:
        route_mode = st.selectbox(
            "🧭 Route Mode",
            [
                "Shortest Distance",
                "Fastest Route",
                "Accessible Route"
            ],
            key="main_route_mode"
        )

    with col2:
        start = st.selectbox(
            "🟢 Start Location",
            locations,
            key="main_start"
        )

    with col3:
        destination = st.selectbox(
            "🔴 Destination",
            locations,
            key="main_destination"
        )

    action1, action2 = st.columns(2)

    find_clicked = action1.button(
        "🔍 Find Route",
        type="primary",
        width="stretch"
    )

    compare_clicked = action2.button(
        "🔄 Compare All Routes",
        width="stretch"
    )


    # --------------------------------------------------------
    # ROUTE COMPARISON
    # --------------------------------------------------------
    if compare_clicked:

        if start == destination:
            st.warning(
                "Start and destination cannot be the same."
            )

        else:

            mode_mapping = {
                "Shortest Distance": "distance",
                "Fastest Route": "fastest",
                "Accessible Route": "accessible"
            }

            comparison_rows = []

            try:

                for display_name, api_mode in (
                        mode_mapping.items()
                ):

                    result = find_route(
                        start,
                        destination,
                        api_mode
                    )

                    comparison_rows.append(
                        {
                            "Mode": display_name,
                            "Stops": result["stops"],
                            "Distance (m)": result["distance_m"],
                            "Travel Time (min)": result["travel_time_min"],
                            "Route": " → ".join(
                                result["route"]
                            )
                        }
                    )

                st.subheader("📊 Route Comparison")

                st.dataframe(
                    pd.DataFrame(comparison_rows),
                    hide_index=True,
                    width="stretch"
                )

            except requests.RequestException as error:

                show_error_from_request(
                    error,
                    "Unable to compare routes."
                )


    # --------------------------------------------------------
    # FIND ROUTE
    # --------------------------------------------------------
    if find_clicked:

        if start == destination:

            st.warning(
                "Start and destination cannot be the same."
            )

        else:

            mode_mapping = {
                "Shortest Distance": "distance",
                "Fastest Route": "fastest",
                "Accessible Route": "accessible"
            }

            api_mode = mode_mapping[
                route_mode
            ]

            try:

                result = find_route(
                    start,
                    destination,
                    api_mode
                )

                path = result["route"]
                total_distance = result["distance_m"]
                total_time = result["travel_time_min"]

                add_route_to_history(
                    start,
                    destination,
                    route_mode,
                    result
                )


                # ------------------------------------------------
                # RESULT BANNER
                # ------------------------------------------------
                st.success(
                    f"✅ {route_mode} calculated successfully."
                )


                # ------------------------------------------------
                # SUMMARY
                # ------------------------------------------------
                st.subheader("📊 Route Summary")

                result1, result2, result3, result4 = st.columns(4)

                with result1:
                    st.metric(
                        "📍 Stops",
                        result["stops"]
                    )

                with result2:
                    st.metric(
                        "📏 Distance",
                        f"{total_distance:.0f} m"
                    )

                with result3:
                    st.metric(
                        "⏱️ Travel Time",
                        f"{total_time:.2f} min"
                    )

                with result4:
                    st.metric(
                        "🧭 Mode",
                        route_mode
                    )


                # ------------------------------------------------
                # ROUTE PATH
                # ------------------------------------------------
                st.subheader("🛣️ Selected Route")

                route_text = " → ".join(path)

                st.info(route_text)


                # ------------------------------------------------
                # TWO-COLUMN RESULT AREA
                # ------------------------------------------------
                map_col, steps_col = st.columns(
                    [1.7, 1]
                )

                with map_col:

                    st.subheader("🌍 Campus Map")

                    show_route_map(
                        path,
                        locations_df
                    )

                with steps_col:

                    st.subheader("🚶 Route Steps")

                    for i, location in enumerate(path):

                        if i == 0:
                            with st.container(border=True):
                                st.write("🟢 **START**")
                                st.write(location)

                        elif i == len(path) - 1:
                            with st.container(border=True):
                                st.write("🔴 **DESTINATION**")
                                st.write(location)

                        else:
                            with st.container(border=True):
                                st.write(f"⬇️ {location}")

                # ------------------------------------------------
                # NETWORK VIEW
                # ------------------------------------------------
                with st.expander(
                        "🗺️ View Route on Campus Network",
                        expanded=False
                ):

                    st.graphviz_chart(
                        build_selected_route_graph(
                            db_roads_df,
                            path,
                            start,
                            destination
                        ),
                        width="stretch"
                    )


                # ------------------------------------------------
                # ROUTE DETAILS
                # ------------------------------------------------
                with st.expander(
                        "📋 View Route Details",
                        expanded=True
                ):

                    for i in range(
                            len(path) - 1
                    ):

                        current = path[i]
                        next_location = path[i + 1]

                        matching_rows = db_roads_df[
                            (
                                    (
                                            db_roads_df["source"]
                                            == current
                                    )
                                    &
                                    (
                                            db_roads_df["destination"]
                                            == next_location
                                    )
                            )
                            |
                            (
                                    (
                                            db_roads_df["source"]
                                            == next_location
                                    )
                                    &
                                    (
                                            db_roads_df["destination"]
                                            == current
                                    )
                            )
                            ]

                        if matching_rows.empty:
                            continue

                        row = matching_rows.iloc[0]

                        distance = float(
                            row["distance"]
                        )

                        traffic = str(
                            row["traffic"]
                        ).upper()

                        details = (
                            f"**{current} → {next_location}** "
                            f"— {distance:.0f} m "
                            f"| 🚦 {traffic}"
                        )

                        if route_mode == "Fastest Route":

                            speed = float(
                                row["speed_kmh"]
                            )

                            if speed > 0:

                                multiplier = (
                                    TRAFFIC_MULTIPLIER.get(
                                        traffic,
                                        1.0
                                    )
                                )

                                segment_time = (
                                                       (distance / 1000)
                                                       / speed
                                               ) * 60 * multiplier

                                details += (
                                    f" | ⏱️ "
                                    f"{segment_time:.2f} min"
                                )

                        st.write(details)


                # ------------------------------------------------
                # DOWNLOAD REPORT
                # ------------------------------------------------
                with st.expander(
                        "📄 Download Route Report",
                        expanded=False
                ):

                    report_lines = [
                        "SMART CAMPUS ROUTE REPORT",
                        "==========================",
                        f"Start: {start}",
                        f"Destination: {destination}",
                        f"Route Mode: {route_mode}",
                        "",
                        "Route:",
                        " → ".join(path),
                        "",
                        f"Total Distance: "
                        f"{total_distance:.0f} metres",
                        f"Estimated Travel Time: "
                        f"{total_time:.2f} minutes"
                    ]

                    report_text = "\n".join(
                        report_lines
                    )

                    st.download_button(
                        "⬇️ Download Route Report",
                        data=report_text,
                        file_name=(
                            "smart_campus_route_report.txt"
                        ),
                        mime="text/plain",
                        width="stretch"
                    )


            except requests.RequestException as error:

                show_error_from_request(
                    error,
                    "Unable to calculate the selected route."
                )


# ============================================================
# FACILITY FINDER
# ============================================================
with facility_tab:

    st.subheader("🏫 Nearest Campus Facility")
    st.caption(
        "Find the closest reachable library, canteen, lab, auditorium or other mapped facility."
    )

    facility_col1, facility_col2 = st.columns(2)

    with facility_col1:

        facility_start = st.selectbox(
            "📍 Starting Location",
            locations,
            key="facility_start"
        )

    with facility_col2:

        facility_types = sorted(
            locations_df["type"]
            .astype(str)
            .str.upper()
            .unique()
        )

        facility_type = st.selectbox(
            "🏫 Facility Type",
            facility_types,
            format_func=format_facility_type,
            key="facility_type"
        )

    facility_mode_name = st.selectbox(
        "🧭 Route Mode",
        [
            "Shortest Distance",
            "Fastest Route",
            "Accessible Route"
        ],
        key="facility_route_mode"
    )

    facility_clicked = st.button(
        "🏫 Find Nearest Facility",
        type="primary",
        width="stretch"
    )


    if facility_clicked:

        facility_candidates = (
            locations_df[
                locations_df["type"]
                .astype(str)
                .str.upper()
                == facility_type
                ]["location"]
                .tolist()
        )

        facility_candidates = [
            facility
            for facility in facility_candidates
            if facility != facility_start
        ]

        if not facility_candidates:

            st.warning(
                "No other facility of this type is available."
            )

        else:

            mode_mapping = {
                "Shortest Distance": "distance",
                "Fastest Route": "fastest",
                "Accessible Route": "accessible"
            }

            facility_mode = mode_mapping[
                facility_mode_name
            ]

            facility_results = []

            try:

                for facility in facility_candidates:

                    try:

                        result = find_route(
                            facility_start,
                            facility,
                            facility_mode
                        )

                        facility_results.append(
                            result
                        )

                    except requests.HTTPError:

                        continue


                if not facility_results:

                    st.error(
                        "No reachable facility of the "
                        "selected type is available."
                    )

                else:

                    if facility_mode == "fastest":

                        nearest = min(
                            facility_results,
                            key=lambda item:
                            item["travel_time_min"]
                        )

                    else:

                        nearest = min(
                            facility_results,
                            key=lambda item:
                            item["distance_m"]
                        )

                    nearest_name = nearest[
                        "destination"
                    ]

                    nearest_path = nearest[
                        "route"
                    ]

                    nearest_distance = nearest[
                        "distance_m"
                    ]

                    nearest_time = nearest[
                        "travel_time_min"
                    ]

                    st.success(
                        f"✅ Nearest "
                        f"{format_facility_type(facility_type)}: "
                        f"**{nearest_name}**"
                    )

                    facility_result1, facility_result2, facility_result3 = (
                        st.columns(3)
                    )

                    with facility_result1:

                        st.metric(
                            "🏫 Facility",
                            nearest_name
                        )

                    with facility_result2:

                        st.metric(
                            "📏 Distance",
                            f"{nearest_distance:.0f} m"
                        )

                    with facility_result3:

                        st.metric(
                            "⏱️ Travel Time",
                            f"{nearest_time:.2f} min"
                        )

                    st.subheader("🛣️ Route")

                    st.info(" → ".join(nearest_path))

                    map_col, table_col = st.columns(
                        [1.5, 1]
                    )

                    with map_col:

                        show_route_map(
                            nearest_path,
                            locations_df
                        )

                    with table_col:

                        facility_table = pd.DataFrame(
                            [
                                {
                                    "Facility": item[
                                        "destination"
                                    ],
                                    "Distance (m)": item[
                                        "distance_m"
                                    ],
                                    "Time (min)": item[
                                        "travel_time_min"
                                    ],
                                    "Route": " → ".join(
                                        item["route"]
                                    )
                                }
                                for item in facility_results
                            ]
                        )

                        st.dataframe(
                            facility_table,
                            hide_index=True,
                            width="stretch"
                        )


            except requests.RequestException as error:

                show_error_from_request(
                    error,
                    "Unable to find a facility."
                )


# ============================================================
# CAMPUS NETWORK
# ============================================================
with network_tab:

    st.subheader("🗺️ Campus Road Network")
    st.caption("Live road status and traffic information from PostgreSQL.")

    st.graphviz_chart(
        build_network_graph(
            db_roads_df
        ),
        width="stretch"
    )

    network_col1, network_col2, network_col3 = st.columns(3)

    with network_col1:
        st.metric(
            "🛣️ Roads",
            len(db_roads_df)
        )

    with network_col2:
        st.metric(
            "🟢 Open",
            open_roads
        )

    with network_col3:
        st.metric(
            "🚧 Blocked",
            blocked_roads
        )


# ============================================================
# ROAD CONTROL
# ============================================================
with road_tab:

    st.subheader("🚧 Road Status & Traffic Control")
    st.caption(
        "Update live campus road conditions. Changes are stored in PostgreSQL through the FastAPI backend."
    )

    edited_df = st.data_editor(
        db_roads_df,
        hide_index=True,
        width="stretch",

        column_config={

            "id": st.column_config.NumberColumn(
                "ID"
            ),

            "source": "Source",

            "destination": "Destination",

            "distance": st.column_config.NumberColumn(
                "Distance (m)"
            ),

            "status": st.column_config.SelectboxColumn(
                "Status",
                options=[
                    "OPEN",
                    "BLOCKED"
                ],
                required=True
            ),

            "speed_kmh": st.column_config.NumberColumn(
                "Speed (km/h)"
            ),

            "accessible": st.column_config.SelectboxColumn(
                "Accessible",
                options=[
                    "YES",
                    "NO"
                ]
            ),

            "traffic": st.column_config.SelectboxColumn(
                "Traffic",
                options=[
                    "LOW",
                    "MEDIUM",
                    "HIGH"
                ],
                required=True
            )
        },

        disabled=[
            "id",
            "source",
            "destination",
            "distance",
            "speed_kmh",
            "accessible"
        ],

        key="road_editor"
    )

    save_col, refresh_col = st.columns(2)

    with save_col:

        if st.button(
                "💾 Save Changes",
                type="primary",
                width="stretch"
        ):

            try:

                changes = save_changed_roads(
                    db_roads_df,
                    edited_df
                )

                if changes:
                    st.success(
                        f"{changes} road(s) updated in PostgreSQL."
                    )
                else:
                    st.info(
                        "No changes detected."
                    )

            except requests.RequestException as error:

                show_error_from_request(
                    error,
                    "Unable to save road changes."
                )

    with refresh_col:

        if st.button(
                "🔄 Refresh Database Data",
                width="stretch"
        ):
            st.rerun()


# ============================================================
# ROUTE HISTORY
# ============================================================
with history_tab:

    st.subheader("🕘 Recent Route History")
    st.caption(
        "The latest five successful route searches in this session."
    )

    if not st.session_state.route_history:

        st.info(
            "No routes searched yet."
        )

    else:

        for index, record in enumerate(
                st.session_state.route_history
        ):

            with st.container(border=True):

                history_col1, history_col2, history_col3, history_col4 = (
                    st.columns(
                        [2.2, 1.2, 1, 1]
                    )
                )

                with history_col1:

                    st.write(
                        f"📍 **{record['start']} → "
                        f"{record['destination']}**"
                    )

                    st.caption(
                        " → ".join(
                            record["path"]
                        )
                    )

                with history_col2:

                    st.write(
                        f"🧭 {record['mode']}"
                    )

                with history_col3:

                    st.write(
                        f"📏 {record['distance']:.0f} m"
                    )

                with history_col4:

                    st.write(
                        f"⏱️ {record['time']:.2f} min"
                    )


    if st.session_state.route_history:

        st.divider()

        if st.button(
                "🗑️ Clear Route History"
        ):

            st.session_state.route_history = []

            st.rerun()


# ============================================================
# FOOTER
# ============================================================
st.divider()

st.caption(
    "Smart Campus Route Planner • "
    "Streamlit + FastAPI + PostgreSQL + Dijkstra"
)
