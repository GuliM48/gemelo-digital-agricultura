import hashlib
from datetime import UTC, datetime

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    DataSourceCreate,
    FarmField,
    FarmFieldCreate,
    ISOProvenanceRecordCreate,
    SeasonCreate,
    User,
    UserCreate,
    UserRole,
)

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


def init_db(session: Session) -> None:
    # 1. Initialize First Superuser with ADMINISTRATOR Role
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            full_name="Dr. Helena Vance (Lead Researcher)",
            role=UserRole.ADMINISTRATOR,
            organization="USDA-ARS & Precision Ag Consortium",
        )
        user = crud.create_user(session=session, user_create=user_in)

    # 2. Initialize Demo Farm Field (USDA BARC Research Field 01)
    existing_field = session.exec(select(FarmField)).first()
    if not existing_field and user:
        demo_field_in = FarmFieldCreate(
            name="USDA BARC Research Field 01",
            location="Beltsville, MD, USA (39.027°N, -76.883°W)",
            latitude=39.0274,
            longitude=-76.8831,
            area_ha=52.4,
            crop_type="Zea mays L. (Corn / Maize Pioneer P1197AM)",
            soil_type="Typic Fragiudults (Silt Loam & Sandy Clay)",
            elevation_mean_m=48.2,
            elevation_range_min_m=42.1,
            elevation_range_max_m=56.8,
            grid_resolution_m=10.0,
            grid_rows=24,
            grid_cols=24,
            boundary_geojson="""{
                "type": "Polygon",
                "coordinates": [[
                    [-76.8850, 39.0255],
                    [-76.8812, 39.0255],
                    [-76.8812, 39.0293],
                    [-76.8850, 39.0293],
                    [-76.8850, 39.0255]
                ]]
            }""",
        )
        field = crud.create_farm_field(
            session=session, field_in=demo_field_in, owner_id=user.id
        )

        # 3. Initialize Active Season
        season_in = SeasonCreate(
            field_id=field.id,
            name="Campaña 2025/2026 - Maíz Primario",
            year=2025,
            sowing_date=datetime(2025, 4, 18, tzinfo=UTC),
            harvest_expected=datetime(2025, 9, 22, tzinfo=UTC),
            target_yield_ton_ha=12.5,
            is_active=True,
        )
        crud.create_season(session=session, season_in=season_in)

        # 4. Initialize Core ADAPT Plugins / Data Sources
        plugins_data = [
            DataSourceCreate(
                field_id=field.id,
                source_name="Sentinel-2 L2A Harmonized Multispectral (Copernicus)",
                protocol="REST_RASTERIO",
                native_resolution="10m - 20m - 60m (13 bands)",
                target_resolution="10m Unified Grid (EPSG:4326)",
                reprojection="Bilinear Resample + Cloud Mask QA60",
                status="ACTIVE",
                latency_ms=142,
                last_ingested_iso=datetime.now(UTC),
                records_count=576,
                confidence_weight=0.88,
            ),
            DataSourceCreate(
                field_id=field.id,
                source_name="OpenDroneMap UAV Aerial Survey (MicaSense RedEdge)",
                protocol="ADAPT_PLUGIN",
                native_resolution="4.8 cm GSD",
                target_resolution="10m (Spatial Aggregation: mean, std, p90)",
                reprojection="AgGateway ADAPT Spatial Raster Upscaler",
                status="ACTIVE",
                latency_ms=380,
                last_ingested_iso=datetime.now(UTC),
                records_count=576,
                confidence_weight=0.96,
            ),
            DataSourceCreate(
                field_id=field.id,
                source_name="ISRIC SoilGrids 2.0 (Global 250m Covariable Database)",
                protocol="ADAPT_PLUGIN",
                native_resolution="250 m",
                target_resolution="10m (Spatial Regression Kriging + S2 Covariates)",
                reprojection="EPSG:4326 downscale via Random Forest Covariates",
                status="ACTIVE",
                latency_ms=95,
                last_ingested_iso=datetime.now(UTC),
                records_count=576,
                confidence_weight=0.82,
            ),
            DataSourceCreate(
                field_id=field.id,
                source_name="OpenFarm / CGIAR Ag-Management (ISO 11783 TaskController)",
                protocol="ISO_XML",
                native_resolution="Tractor Section Control (2.5m Swath)",
                target_resolution="10m Voxel Prescription Layer",
                reprojection="AgGateway ADAPT CropType & Prescription Importer",
                status="ACTIVE",
                latency_ms=48,
                last_ingested_iso=datetime.now(UTC),
                records_count=576,
                confidence_weight=0.99,
            ),
            DataSourceCreate(
                field_id=field.id,
                source_name="Decagon / Meter Soil Profile Probes (OGC SensorThings API)",
                protocol="OGC_STA",
                native_resolution="Point Sensor Depths: 10, 25, 50, 90 cm",
                target_resolution="10m Kriging Surface Mesh (EPSG:4326)",
                reprojection="OGC STA Observation Harmonizer",
                status="ACTIVE",
                latency_ms=62,
                last_ingested_iso=datetime.now(UTC),
                records_count=576,
                confidence_weight=0.91,
            ),
        ]
        for plugin in plugins_data:
            crud.create_data_source(session=session, source_in=plugin)

        # 5. Initialize ISO 19115 Lineage / Provenance Log
        lineage_hash = hashlib.sha256(
            f"{field.id}-init-provenance".encode()
        ).hexdigest()[:16]
        provenance_in = ISOProvenanceRecordCreate(
            field_id=field.id,
            user_id=user.id,
            user_email=user.email,
            action="INITIAL_SEED: Harmonized 10m Multi-Modal Digital Twin Baseline",
            source_dataset="Sentinel-2 + UAV OpenDroneMap + SoilGrids 2.0 + OpenFarm",
            iso_standard="ISO 19115-1:2014 Section 8.2 (Lineage)",
            transformation_type="Spatial Resampling & ADAPT Schema Normalization (EPSG:4326)",
            lineage_hash=f"sha256:{lineage_hash}",
            status="VALIDATED",
        )
        crud.create_provenance_record(session=session, record_in=provenance_in)
