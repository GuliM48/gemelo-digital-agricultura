import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    require_roles,
)
from app.models import (
    DataSourcesPublic,
    FarmField,
    FarmFieldCreate,
    FarmFieldPublic,
    FarmFieldsPublic,
    FarmFieldUpdate,
    GridCellCreate,
    GridCellsPublic,
    ISOProvenanceRecordsPublic,
    Message,
    SeasonCreate,
    SeasonPublic,
    SeasonsPublic,
    UserRole,
)

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("/", response_model=FarmFieldsPublic)
def read_fields(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve farm fields.
    Admins and Agronomists can see all fields; Farmers see only their assigned fields.
    """
    if current_user.is_superuser or current_user.role in (
        UserRole.ADMINISTRATOR,
        UserRole.AGRONOMIST,
        UserRole.DEVELOPER,
    ):
        count_statement = select(func.count()).select_from(FarmField)
        count = session.exec(count_statement).one()
        statement = select(FarmField).offset(skip).limit(limit)
        fields = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(FarmField)
            .where(FarmField.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(FarmField)
            .where(FarmField.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        fields = session.exec(statement).all()

    return FarmFieldsPublic(data=list(fields), count=count)


@router.post(
    "/",
    response_model=FarmFieldPublic,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMINISTRATOR, UserRole.AGRONOMIST, UserRole.DEVELOPER
            )
        )
    ],
)
def create_field(
    *, session: SessionDep, current_user: CurrentUser, field_in: FarmFieldCreate
) -> Any:
    """
    Create a new farm field / experimental plot.
    Restricted to ADMINISTRATOR, AGRONOMIST, or DEVELOPER.
    """
    field = crud.create_farm_field(
        session=session, field_in=field_in, owner_id=current_user.id
    )
    return field


@router.get("/{field_id}", response_model=FarmFieldPublic)
def read_field(
    *, session: SessionDep, current_user: CurrentUser, field_id: uuid.UUID
) -> Any:
    """
    Get a specific farm field by ID.
    """
    field = session.get(FarmField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Farm field not found")
    if (
        not current_user.is_superuser
        and current_user.role == UserRole.FARMER
        and field.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return field


@router.put(
    "/{field_id}",
    response_model=FarmFieldPublic,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMINISTRATOR, UserRole.AGRONOMIST, UserRole.DEVELOPER
            )
        )
    ],
)
def update_field(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    field_id: uuid.UUID,
    field_in: FarmFieldUpdate,
) -> Any:
    """
    Update field properties and boundaries.
    """
    field = session.get(FarmField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Farm field not found")
    if (
        not current_user.is_superuser
        and current_user.role != UserRole.ADMINISTRATOR
        and field.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this field"
        )
    field = crud.update_farm_field(session=session, db_field=field, field_in=field_in)
    return field


# ----------------------------------------------------------------------------
# SEASONS
# ----------------------------------------------------------------------------
@router.get("/{field_id}/seasons", response_model=SeasonsPublic)
def read_seasons(*, session: SessionDep, field_id: uuid.UUID) -> Any:
    """
    Get all seasons/campaigns associated with a field.
    """
    field = session.get(FarmField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Farm field not found")
    seasons = crud.get_seasons_by_field(session=session, field_id=field_id)
    return SeasonsPublic(data=seasons, count=len(seasons))


@router.post(
    "/{field_id}/seasons",
    response_model=SeasonPublic,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMINISTRATOR, UserRole.AGRONOMIST, UserRole.DEVELOPER
            )
        )
    ],
)
def create_season(
    *, session: SessionDep, field_id: uuid.UUID, season_in: SeasonCreate
) -> Any:
    """
    Register a new agricultural season for this field.
    """
    season_in.field_id = field_id
    season = crud.create_season(session=session, season_in=season_in)
    return season


# ----------------------------------------------------------------------------
# DATA SOURCES & ADAPT PLUGINS
# ----------------------------------------------------------------------------
@router.get("/{field_id}/data-sources", response_model=DataSourcesPublic)
def read_data_sources(*, session: SessionDep, field_id: uuid.UUID) -> Any:
    """
    Get active data sources and ADAPT plugins for this field.
    """
    sources = crud.get_data_sources(session=session, field_id=field_id)
    return DataSourcesPublic(data=sources, count=len(sources))


# ----------------------------------------------------------------------------
# GRID CELLS / 3D DIGITAL TWIN VOXELS
# ----------------------------------------------------------------------------
@router.get("/{field_id}/cells", response_model=GridCellsPublic)
def read_grid_cells(*, session: SessionDep, field_id: uuid.UUID) -> Any:
    """
    Get fused multi-modal grid cells for 3D digital twin terrain and voxel rendering.
    """
    cells = crud.get_grid_cells_by_field(session=session, field_id=field_id)
    return GridCellsPublic(data=cells, count=len(cells))


@router.post(
    "/{field_id}/cells/bulk",
    response_model=Message,
    dependencies=[Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.DEVELOPER))],
)
def bulk_insert_cells(
    *, session: SessionDep, field_id: uuid.UUID, cells_in: list[GridCellCreate]
) -> Any:
    """
    Bulk insert or replace voxel grid cells resulting from data fusion pipeline.
    """
    for cell in cells_in:
        cell.field_id = field_id
    crud.create_grid_cells_bulk(session=session, cells_in=cells_in)
    return Message(message=f"Successfully ingested {len(cells_in)} fused grid cells")


# ----------------------------------------------------------------------------
# ISO 19115 PROVENANCE & LINEAGE
# ----------------------------------------------------------------------------
@router.get("/{field_id}/provenance", response_model=ISOProvenanceRecordsPublic)
def read_provenance_records(
    *, session: SessionDep, field_id: uuid.UUID, limit: int = 50
) -> Any:
    """
    Get ISO 19115 lineage and data transformation audit records.
    """
    records = crud.get_provenance_records(
        session=session, field_id=field_id, limit=limit
    )
    return ISOProvenanceRecordsPublic(data=records, count=len(records))
