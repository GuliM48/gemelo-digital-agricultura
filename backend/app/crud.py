import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    DataSource,
    DataSourceCreate,
    FarmField,
    FarmFieldCreate,
    FarmFieldUpdate,
    GridCell,
    GridCellCreate,
    ISOProvenanceRecord,
    ISOProvenanceRecordCreate,
    Item,
    ItemCreate,
    Season,
    SeasonCreate,
    User,
    UserCreate,
    UserUpdate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ============================================================================
# PRECISION AGRICULTURE DOMAIN CRUD
# ============================================================================


def create_farm_field(
    *, session: Session, field_in: FarmFieldCreate, owner_id: uuid.UUID
) -> FarmField:
    db_field = FarmField.model_validate(field_in, update={"owner_id": owner_id})
    session.add(db_field)
    session.commit()
    session.refresh(db_field)
    return db_field


def get_farm_field(*, session: Session, field_id: uuid.UUID) -> FarmField | None:
    return session.get(FarmField, field_id)


def get_farm_fields(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: uuid.UUID | None = None,
) -> list[FarmField]:
    statement = select(FarmField)
    if owner_id:
        statement = statement.where(FarmField.owner_id == owner_id)
    statement = statement.offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_farm_field(
    *, session: Session, db_field: FarmField, field_in: FarmFieldUpdate
) -> FarmField:
    field_data = field_in.model_dump(exclude_unset=True)
    db_field.sqlmodel_update(field_data)
    session.add(db_field)
    session.commit()
    session.refresh(db_field)
    return db_field


def create_season(*, session: Session, season_in: SeasonCreate) -> Season:
    db_season = Season.model_validate(season_in)
    session.add(db_season)
    session.commit()
    session.refresh(db_season)
    return db_season


def get_seasons_by_field(*, session: Session, field_id: uuid.UUID) -> list[Season]:
    statement = select(Season).where(Season.field_id == field_id)
    return list(session.exec(statement).all())


def create_data_source(*, session: Session, source_in: DataSourceCreate) -> DataSource:
    db_source = DataSource.model_validate(source_in)
    session.add(db_source)
    session.commit()
    session.refresh(db_source)
    return db_source


def get_data_sources(
    *, session: Session, field_id: uuid.UUID | None = None
) -> list[DataSource]:
    statement = select(DataSource)
    if field_id:
        statement = statement.where(
            (DataSource.field_id == field_id) | (DataSource.field_id.is_(None))  # type: ignore
        )
    return list(session.exec(statement).all())


def create_grid_cells_bulk(
    *, session: Session, cells_in: list[GridCellCreate]
) -> list[GridCell]:
    db_cells = [GridCell.model_validate(cell) for cell in cells_in]
    session.add_all(db_cells)
    session.commit()
    return db_cells


def get_grid_cells_by_field(*, session: Session, field_id: uuid.UUID) -> list[GridCell]:
    statement = (
        select(GridCell)
        .where(GridCell.field_id == field_id)
        .order_by(GridCell.row, GridCell.col)  # type: ignore
    )
    return list(session.exec(statement).all())


def create_provenance_record(
    *, session: Session, record_in: ISOProvenanceRecordCreate
) -> ISOProvenanceRecord:
    db_record = ISOProvenanceRecord.model_validate(record_in)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)
    return db_record


def get_provenance_records(
    *, session: Session, field_id: uuid.UUID | None = None, limit: int = 50
) -> list[ISOProvenanceRecord]:
    statement = select(ISOProvenanceRecord)
    if field_id:
        statement = statement.where(
            (ISOProvenanceRecord.field_id == field_id)
            | (ISOProvenanceRecord.field_id.is_(None))  # type: ignore
        )
    statement = statement.order_by(ISOProvenanceRecord.timestamp.desc()).limit(limit)  # type: ignore
    return list(session.exec(statement).all())
