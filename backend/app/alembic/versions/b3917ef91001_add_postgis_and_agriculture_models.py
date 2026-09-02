"""Add PostGIS extension and precision agriculture domain models

Revision ID: b3917ef91001
Revises: fe56fa70289e
Create Date: 2026-09-02 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b3917ef91001'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Add RBAC & Organization columns to User
    op.add_column(
        'user',
        sa.Column('role', sa.String(length=50), nullable=False, server_default='FARMER')
    )
    op.add_column(
        'user',
        sa.Column('organization', sa.String(length=255), nullable=True)
    )

    # 3. Create FarmField table
    op.create_table(
        'farmfield',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('boundary_geojson', sa.Text(), nullable=True),
        sa.Column('area_ha', sa.Float(), nullable=False),
        sa.Column('crop_type', sa.String(length=255), nullable=False),
        sa.Column('soil_type', sa.String(length=255), nullable=True),
        sa.Column('elevation_mean_m', sa.Float(), nullable=False),
        sa.Column('elevation_range_min_m', sa.Float(), nullable=False),
        sa.Column('elevation_range_max_m', sa.Float(), nullable=False),
        sa.Column('grid_resolution_m', sa.Float(), nullable=False),
        sa.Column('grid_rows', sa.Integer(), nullable=False),
        sa.Column('grid_cols', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Create Season table
    op.create_table(
        'season',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('field_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('sowing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('harvest_expected', sa.DateTime(timezone=True), nullable=True),
        sa.Column('target_yield_ton_ha', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['field_id'], ['farmfield.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_season_field_id', 'season', ['field_id'], unique=False)

    # 5. Create DataSource (ADAPT Plugin) table
    op.create_table(
        'datasource',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('field_id', sa.UUID(), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('protocol', sa.String(length=50), nullable=False),
        sa.Column('native_resolution', sa.String(length=100), nullable=False),
        sa.Column('target_resolution', sa.String(length=100), nullable=False),
        sa.Column('reprojection', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('last_ingested_iso', sa.DateTime(timezone=True), nullable=True),
        sa.Column('records_count', sa.Integer(), nullable=False),
        sa.Column('confidence_weight', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['field_id'], ['farmfield.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_datasource_field_id', 'datasource', ['field_id'], unique=False)

    # 6. Create GridCell table
    op.create_table(
        'gridcell',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('field_id', sa.UUID(), nullable=False),
        sa.Column('row', sa.Integer(), nullable=False),
        sa.Column('col', sa.Integer(), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('elevation', sa.Float(), nullable=False),
        # Soil
        sa.Column('soil_organic_carbon_g_kg', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_clay_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_sand_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_ph', sa.Float(), nullable=False, server_default='7.0'),
        sa.Column('soil_moisture_vol_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_depth_0_15_cm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_depth_15_30_cm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_depth_30_60_cm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('soil_depth_60_100_cm', sa.Float(), nullable=False, server_default='0.0'),
        # Sentinel-2
        sa.Column('s2_b2_blue', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_b3_green', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_b4_red', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_b8_nir', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_b11_swir', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_ndvi', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_ndre', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('s2_evi', sa.Float(), nullable=False, server_default='0.0'),
        # UAV
        sa.Column('uav_rgb_hex', sa.String(length=20), nullable=False, server_default='#4d8c2f'),
        sa.Column('uav_ndvi', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('uav_canopy_height_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('uav_thermal_c', sa.Float(), nullable=False, server_default='0.0'),
        # Farm Management
        sa.Column('seed_density_k_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('nitrogen_applied_kg_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('irrigation_mm', sa.Float(), nullable=False, server_default='0.0'),
        # Predictions & Ground Truth
        sa.Column('ground_truth_yield_kg_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('apsim_simulated_yield_kg_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('xgboost_residual_kg_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('predicted_yield_kg_ha', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('prediction_confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('management_zone', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['field_id'], ['farmfield.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_gridcell_field_id', 'gridcell', ['field_id'], unique=False)
    op.create_index('ix_gridcell_field_row_col', 'gridcell', ['field_id', 'row', 'col'], unique=True)

    # 7. Create ISOProvenanceRecord table
    op.create_table(
        'isoprovenancerecord',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('field_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('source_dataset', sa.String(length=255), nullable=False),
        sa.Column('iso_standard', sa.String(length=255), nullable=False),
        sa.Column('transformation_type', sa.String(length=255), nullable=False),
        sa.Column('lineage_hash', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['field_id'], ['farmfield.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_isoprovenancerecord_field_id', 'isoprovenancerecord', ['field_id'], unique=False)


def downgrade():
    op.drop_index('ix_isoprovenancerecord_field_id', table_name='isoprovenancerecord')
    op.drop_table('isoprovenancerecord')

    op.drop_index('ix_gridcell_field_row_col', table_name='gridcell')
    op.drop_index('ix_gridcell_field_id', table_name='gridcell')
    op.drop_table('gridcell')

    op.drop_index('ix_datasource_field_id', table_name='datasource')
    op.drop_table('datasource')

    op.drop_index('ix_season_field_id', table_name='season')
    op.drop_table('season')

    op.drop_table('farmfield')

    op.drop_column('user', 'organization')
    op.drop_column('user', 'role')
