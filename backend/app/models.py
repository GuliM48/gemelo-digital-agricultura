import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# RBAC & USER MODELS
# ============================================================================


class UserRole(StrEnum):
    ADMINISTRATOR = "ADMINISTRATOR"
    AGRONOMIST = "AGRONOMIST"
    FARMER = "FARMER"
    DEVELOPER = "DEVELOPER"


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.FARMER)
    organization: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.FARMER)
    organization: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    organization: str | None = Field(default=None, max_length=255)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    fields: list[FarmField] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ============================================================================
# TEMPLATE ITEM MODELS (Preserved for compatibility)
# ============================================================================


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ============================================================================
# PRECISION AGRICULTURE DOMAIN MODELS
# ============================================================================


# ----------------------------------------------------------------------------
# 1. FarmField (Parcela / Lote Agrícola)
# ----------------------------------------------------------------------------
class FarmFieldBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    boundary_geojson: str | None = Field(default=None)
    area_ha: float = Field(gt=0)
    crop_type: str = Field(default="Zea mays L. (Maíz)", max_length=255)
    soil_type: str | None = Field(default="Fluvisol Mólico", max_length=255)
    elevation_mean_m: float = Field(default=1245.0)
    elevation_range_min_m: float = Field(default=1240.0)
    elevation_range_max_m: float = Field(default=1252.0)
    grid_resolution_m: float = Field(default=10.0, gt=0)
    grid_rows: int = Field(default=24, gt=0)
    grid_cols: int = Field(default=24, gt=0)


class FarmFieldCreate(FarmFieldBase):
    pass


class FarmFieldUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    boundary_geojson: str | None = None
    area_ha: float | None = Field(default=None, gt=0)
    crop_type: str | None = Field(default=None, max_length=255)
    soil_type: str | None = Field(default=None, max_length=255)
    elevation_mean_m: float | None = None
    elevation_range_min_m: float | None = None
    elevation_range_max_m: float | None = None
    grid_resolution_m: float | None = Field(default=None, gt=0)
    grid_rows: int | None = Field(default=None, gt=0)
    grid_cols: int | None = Field(default=None, gt=0)


class FarmField(FarmFieldBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="fields")
    seasons: list[Season] = Relationship(back_populates="field", cascade_delete=True)
    data_sources: list[DataSource] = Relationship(
        back_populates="field", cascade_delete=True
    )
    grid_cells: list[GridCell] = Relationship(
        back_populates="field", cascade_delete=True
    )
    provenance_records: list[ISOProvenanceRecord] = Relationship(
        back_populates="field", cascade_delete=True
    )


class FarmFieldPublic(FarmFieldBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class FarmFieldsPublic(SQLModel):
    data: list[FarmFieldPublic]
    count: int


# ----------------------------------------------------------------------------
# 2. Season (Campaña / Temporada Agrícola)
# ----------------------------------------------------------------------------
class SeasonBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    year: int = Field(ge=2000, le=2100)
    sowing_date: datetime | None = None
    harvest_expected: datetime | None = None
    target_yield_ton_ha: float | None = Field(default=None, ge=0)
    is_active: bool = True


class SeasonCreate(SeasonBase):
    field_id: uuid.UUID


class SeasonUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    year: int | None = Field(default=None, ge=2000, le=2100)
    sowing_date: datetime | None = None
    harvest_expected: datetime | None = None
    target_yield_ton_ha: float | None = None
    is_active: bool | None = None


class Season(SeasonBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    field_id: uuid.UUID = Field(
        foreign_key="farmfield.id", nullable=False, ondelete="CASCADE", index=True
    )
    field: FarmField | None = Relationship(back_populates="seasons")


class SeasonPublic(SeasonBase):
    id: uuid.UUID
    field_id: uuid.UUID
    created_at: datetime | None = None


class SeasonsPublic(SQLModel):
    data: list[SeasonPublic]
    count: int


# ----------------------------------------------------------------------------
# 3. DataSource / ADAPTPlugin (Adaptadores OGC / AgGateway ADAPT)
# ----------------------------------------------------------------------------
class DataSourceBase(SQLModel):
    source_name: str = Field(min_length=1, max_length=255)
    protocol: str = Field(default="ADAPT_PLUGIN", max_length=50)
    native_resolution: str = Field(default="10m", max_length=100)
    target_resolution: str = Field(
        default="10m Unified Grid (EPSG:4326)", max_length=100
    )
    reprojection: str = Field(default="EPSG:4326 WGS84", max_length=100)
    status: str = Field(default="ACTIVE", max_length=50)
    latency_ms: int = Field(default=45, ge=0)
    last_ingested_iso: datetime | None = None
    records_count: int = Field(default=0, ge=0)
    confidence_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class DataSourceCreate(DataSourceBase):
    field_id: uuid.UUID | None = None


class DataSourceUpdate(SQLModel):
    source_name: str | None = None
    protocol: str | None = None
    native_resolution: str | None = None
    target_resolution: str | None = None
    reprojection: str | None = None
    status: str | None = None
    latency_ms: int | None = None
    last_ingested_iso: datetime | None = None
    records_count: int | None = None
    confidence_weight: float | None = None


class DataSource(DataSourceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    field_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="farmfield.id",
        nullable=True,
        ondelete="CASCADE",
        index=True,
    )
    field: FarmField | None = Relationship(back_populates="data_sources")


class DataSourcePublic(DataSourceBase):
    id: uuid.UUID
    field_id: uuid.UUID | None = None
    created_at: datetime | None = None


class DataSourcesPublic(SQLModel):
    data: list[DataSourcePublic]
    count: int


# ----------------------------------------------------------------------------
# 4. GridCell (Celdas Fusión Multi-Modal / Vóxeles 3D)
# ----------------------------------------------------------------------------
class GridCellBase(SQLModel):
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    x: float
    y: float
    elevation: float
    # Suelo (SoilGrids 2.0 downscaled a 10m)
    soil_organic_carbon_g_kg: float = Field(default=0.0)
    soil_clay_percent: float = Field(default=0.0)
    soil_sand_percent: float = Field(default=0.0)
    soil_ph: float = Field(default=7.0)
    soil_moisture_vol_percent: float = Field(default=0.0)
    soil_depth_0_15_cm: float = Field(default=0.0)
    soil_depth_15_30_cm: float = Field(default=0.0)
    soil_depth_30_60_cm: float = Field(default=0.0)
    soil_depth_60_100_cm: float = Field(default=0.0)
    # Satélite Sentinel-2 L2A (10m)
    s2_b2_blue: float = Field(default=0.0)
    s2_b3_green: float = Field(default=0.0)
    s2_b4_red: float = Field(default=0.0)
    s2_b8_nir: float = Field(default=0.0)
    s2_b11_swir: float = Field(default=0.0)
    s2_ndvi: float = Field(default=0.0)
    s2_ndre: float = Field(default=0.0)
    s2_evi: float = Field(default=0.0)
    # UAV Dron OpenDroneMap (Alta resolución)
    uav_rgb_hex: str = Field(default="#4d8c2f", max_length=20)
    uav_ndvi: float = Field(default=0.0)
    uav_canopy_height_m: float = Field(default=0.0)
    uav_thermal_c: float = Field(default=0.0)
    # Manejo Agronómico (OpenFarm / ERP)
    seed_density_k_ha: float = Field(default=0.0)
    nitrogen_applied_kg_ha: float = Field(default=0.0)
    irrigation_mm: float = Field(default=0.0)
    # Modelo Híbrido (APSIM + XGBoost) y Ground Truth
    ground_truth_yield_kg_ha: float = Field(default=0.0)
    apsim_simulated_yield_kg_ha: float = Field(default=0.0)
    xgboost_residual_kg_ha: float = Field(default=0.0)
    predicted_yield_kg_ha: float = Field(default=0.0)
    prediction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    management_zone: int = Field(default=1, ge=1, le=4)


class GridCellCreate(GridCellBase):
    field_id: uuid.UUID


class GridCell(GridCellBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    field_id: uuid.UUID = Field(
        foreign_key="farmfield.id", nullable=False, ondelete="CASCADE", index=True
    )
    field: FarmField | None = Relationship(back_populates="grid_cells")


class GridCellPublic(GridCellBase):
    id: uuid.UUID
    field_id: uuid.UUID


class GridCellsPublic(SQLModel):
    data: list[GridCellPublic]
    count: int


# ----------------------------------------------------------------------------
# 5. ISOProvenanceRecord (Trazabilidad y Linaje ISO 19115-1:2014)
# ----------------------------------------------------------------------------
class ISOProvenanceRecordBase(SQLModel):
    timestamp: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    user_email: str = Field(max_length=255)
    action: str = Field(max_length=255)
    source_dataset: str = Field(max_length=255)
    iso_standard: str = Field(
        default="ISO 19115-1:2014 Section 8.2 (Lineage)", max_length=255
    )
    transformation_type: str = Field(max_length=255)
    lineage_hash: str = Field(max_length=128)
    status: str = Field(default="VALIDATED", max_length=50)


class ISOProvenanceRecordCreate(ISOProvenanceRecordBase):
    field_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class ISOProvenanceRecord(ISOProvenanceRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    field_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="farmfield.id",
        nullable=True,
        ondelete="CASCADE",
        index=True,
    )
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", nullable=True, ondelete="SET NULL"
    )
    field: FarmField | None = Relationship(back_populates="provenance_records")


class ISOProvenanceRecordPublic(ISOProvenanceRecordBase):
    id: uuid.UUID
    field_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class ISOProvenanceRecordsPublic(SQLModel):
    data: list[ISOProvenanceRecordPublic]
    count: int


# ============================================================================
# GENERIC & AUTH PAYLOADS
# ============================================================================


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
