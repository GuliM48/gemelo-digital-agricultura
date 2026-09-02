import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app import crud
from app.models import (
    DataSourceCreate,
    FarmFieldCreate,
    GridCellCreate,
    ISOProvenanceRecordCreate,
    SeasonCreate,
    UserCreate,
    UserRole,
)


@pytest.fixture(name="db")
def db_fixture() -> Generator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_user_with_agronomic_role(db: Session) -> None:
    email = f"agronomist_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(
        email=email,
        password="secretpassword123",
        full_name="Carlos Mendez",
        role=UserRole.AGRONOMIST,
        organization="GeoCrop Advisory",
    )
    user = crud.create_user(session=db, user_create=user_in)

    assert user.email == email
    assert user.role == UserRole.AGRONOMIST
    assert user.organization == "GeoCrop Advisory"
    assert user.is_active is True


def test_create_farm_field_and_relationships(db: Session) -> None:
    email = f"farmer_{uuid.uuid4().hex[:8]}@example.com"
    user_in = UserCreate(
        email=email,
        password="secretpassword123",
        full_name="Thomas Miller",
        role=UserRole.FARMER,
        organization="Miller Agro Co.",
    )
    user = crud.create_user(session=db, user_create=user_in)

    # 1. Create FarmField
    field_in = FarmFieldCreate(
        name="Lote Experimental Norte",
        location="Sector 4 (39.027°N, -76.883°W)",
        latitude=39.0274,
        longitude=-76.8831,
        area_ha=52.4,
        crop_type="Zea mays L.",
        soil_type="Typic Fragiudults",
        elevation_mean_m=48.2,
        elevation_range_min_m=42.1,
        elevation_range_max_m=56.8,
        grid_resolution_m=10.0,
        grid_rows=24,
        grid_cols=24,
    )
    field = crud.create_farm_field(session=db, field_in=field_in, owner_id=user.id)

    assert field.id is not None
    assert field.name == "Lote Experimental Norte"
    assert field.owner_id == user.id
    assert field.area_ha == 52.4

    # 2. Create Season
    season_in = SeasonCreate(
        field_id=field.id,
        name="Campaña 2025",
        year=2025,
        sowing_date=datetime(2025, 4, 18, tzinfo=UTC),
        harvest_expected=datetime(2025, 9, 22, tzinfo=UTC),
        target_yield_ton_ha=11.8,
        is_active=True,
    )
    season = crud.create_season(session=db, season_in=season_in)
    assert season.id is not None
    assert season.field_id == field.id
    assert season.is_active is True

    # 3. Create ADAPT DataSource
    source_in = DataSourceCreate(
        field_id=field.id,
        source_name="Sentinel-2 L2A Harmonized",
        protocol="REST_RASTERIO",
        native_resolution="10m",
        target_resolution="10m Unified Grid (EPSG:4326)",
        reprojection="Bilinear Resample",
        status="ACTIVE",
        latency_ms=120,
        records_count=576,
        confidence_weight=0.92,
    )
    source = crud.create_data_source(session=db, source_in=source_in)
    assert source.id is not None
    assert source.protocol == "REST_RASTERIO"
    assert source.confidence_weight == 0.92

    # 4. Create GridCell Voxel
    cell_in = GridCellCreate(
        field_id=field.id,
        row=0,
        col=0,
        x=0.0,
        y=0.0,
        elevation=48.5,
        soil_organic_carbon_g_kg=24.5,
        soil_clay_percent=22.0,
        soil_sand_percent=45.0,
        soil_ph=6.8,
        soil_moisture_vol_percent=28.4,
        s2_ndvi=0.82,
        uav_ndvi=0.85,
        uav_canopy_height_m=1.95,
        ground_truth_yield_kg_ha=11200.0,
        apsim_simulated_yield_kg_ha=10900.0,
        xgboost_residual_kg_ha=250.0,
        predicted_yield_kg_ha=11150.0,
        prediction_confidence=0.95,
        management_zone=2,
    )
    cells = crud.create_grid_cells_bulk(session=db, cells_in=[cell_in])
    assert len(cells) == 1
    assert cells[0].s2_ndvi == 0.82
    assert cells[0].predicted_yield_kg_ha == 11150.0

    # 5. Create ISO 19115 Lineage Record
    prov_in = ISOProvenanceRecordCreate(
        field_id=field.id,
        user_id=user.id,
        user_email=user.email,
        action="TEST_ACTION: Multi-Modal Voxel Harmonization",
        source_dataset="Sentinel-2 + UAV + SoilGrids",
        iso_standard="ISO 19115-1:2014 Section 8.2",
        transformation_type="Nearest-Neighbor Resampling",
        lineage_hash="sha256:abc123test",
        status="VALIDATED",
    )
    record = crud.create_provenance_record(session=db, record_in=prov_in)
    assert record.id is not None
    assert record.status == "VALIDATED"
    assert record.lineage_hash == "sha256:abc123test"
