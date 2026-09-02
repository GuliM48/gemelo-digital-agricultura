import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.main import app
from app.models import User, UserRole


@pytest.fixture(name="test_db")
def test_db_fixture() -> Generator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="admin_user")
def admin_user_fixture(test_db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@agritwin.org",
        hashed_password="hashedpassword123",
        full_name="Dr. Helena Vance",
        role=UserRole.ADMINISTRATOR,
        organization="USDA-ARS",
        is_active=True,
        is_superuser=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(name="farmer_user")
def farmer_user_fixture(test_db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="farmer@example.com",
        hashed_password="hashedpassword123",
        full_name="Thomas Miller",
        role=UserRole.FARMER,
        organization="Miller Prairie Agro",
        is_active=True,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_create_and_read_field_api(test_db: Session, admin_user: User) -> None:
    def override_get_db():
        yield test_db

    def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        # 1. Create Field
        field_data = {
            "name": "USDA BARC Field 01",
            "location": "Beltsville, MD",
            "latitude": 39.0274,
            "longitude": -76.8831,
            "area_ha": 52.4,
            "crop_type": "Zea mays L.",
            "soil_type": "Typic Fragiudults",
            "elevation_mean_m": 48.2,
            "elevation_range_min_m": 42.1,
            "elevation_range_max_m": 56.8,
            "grid_resolution_m": 10.0,
            "grid_rows": 24,
            "grid_cols": 24,
        }
        res = client.post(f"{settings.API_V1_STR}/fields/", json=field_data)
        assert res.status_code == 200
        field = res.json()
        assert field["name"] == "USDA BARC Field 01"
        assert field["area_ha"] == 52.4
        field_id = field["id"]

        # 2. Get Field List
        list_res = client.get(f"{settings.API_V1_STR}/fields/")
        assert list_res.status_code == 200
        data = list_res.json()
        assert data["count"] >= 1

        # 3. Create Season for Field
        season_data = {
            "name": "Campaña 2025/2026",
            "year": 2025,
            "target_yield_ton_ha": 12.0,
            "is_active": True,
            "field_id": field_id,
        }
        season_res = client.post(
            f"{settings.API_V1_STR}/fields/{field_id}/seasons",
            json=season_data,
        )
        assert season_res.status_code == 200
        assert season_res.json()["name"] == "Campaña 2025/2026"

        # 4. Get Seasons
        seasons_list = client.get(f"{settings.API_V1_STR}/fields/{field_id}/seasons")
        assert seasons_list.status_code == 200
        assert seasons_list.json()["count"] == 1

        # 5. Bulk Ingest Grid Cells
        cells_data = [
            {
                "field_id": field_id,
                "row": 0,
                "col": 0,
                "x": 0.0,
                "y": 0.0,
                "elevation": 48.2,
                "s2_ndvi": 0.84,
                "uav_ndvi": 0.86,
                "predicted_yield_kg_ha": 11400.0,
                "prediction_confidence": 0.96,
                "management_zone": 1,
            }
        ]
        cells_res = client.post(
            f"{settings.API_V1_STR}/fields/{field_id}/cells/bulk",
            json=cells_data,
        )
        assert cells_res.status_code == 200

        # 6. Read Grid Cells
        read_cells = client.get(f"{settings.API_V1_STR}/fields/{field_id}/cells")
        assert read_cells.status_code == 200
        cells_json = read_cells.json()
        assert cells_json["count"] == 1
        assert cells_json["data"][0]["s2_ndvi"] == 0.84

    app.dependency_overrides.clear()


def test_farmer_rbac_restriction(test_db: Session, farmer_user: User) -> None:
    def override_get_db():
        yield test_db

    def override_get_current_user():
        return farmer_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        # Farmer should NOT be allowed to create a field (restricted to ADMIN/AGRONOMIST/DEVELOPER)
        field_data = {
            "name": "Unauthorized Plot",
            "location": "Nowhere",
            "latitude": 0.0,
            "longitude": 0.0,
            "area_ha": 10.0,
            "crop_type": "Corn",
            "grid_resolution_m": 10.0,
            "grid_rows": 10,
            "grid_cols": 10,
        }
        res = client.post(f"{settings.API_V1_STR}/fields/", json=field_data)
        assert res.status_code == 403
        assert "not authorized" in res.json()["detail"]

    app.dependency_overrides.clear()
