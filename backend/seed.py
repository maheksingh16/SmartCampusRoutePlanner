import pandas as pd
from sqlalchemy import delete

from .database import SessionLocal
from .models import Location, Road


ROUTES_FILE = "data/campus_routes.csv"
LOCATIONS_FILE = "data/campus_locations.csv"


def seed_database():

    locations_df = pd.read_csv(
        LOCATIONS_FILE
    )

    roads_df = pd.read_csv(
        ROUTES_FILE
    )

    db = SessionLocal()

    try:

        # Clear existing data
        db.execute(delete(Road))
        db.execute(delete(Location))

        # -----------------------------
        # Insert locations
        # -----------------------------
        for _, row in locations_df.iterrows():

            location = Location(
                name=str(row["location"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                type=str(row["type"]).upper()
            )

            db.add(location)

        # -----------------------------
        # Insert roads
        # -----------------------------
        for _, row in roads_df.iterrows():

            accessible_value = (
                    str(row["accessible"])
                    .strip()
                    .upper()
                    == "YES"
            )

            road = Road(
                source=str(row["source"]),
                destination=str(row["destination"]),
                distance=float(row["distance"]),
                status=str(row["status"]).upper(),
                speed_kmh=float(row["speed_kmh"]),
                accessible=accessible_value,
                traffic=str(row["traffic"]).upper()
            )

            db.add(road)

        db.commit()

        print("Database seeded successfully!")
        print(
            f"Locations inserted: {len(locations_df)}"
        )
        print(
            f"Roads inserted: {len(roads_df)}"
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_database()