"""Initial migration for PostgreSQL

Revision ID: 20251229_0c8e9b0a4f1d
Revises: 
Create Date: 2025-12-29 03:49:12.123456

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251229_0c8e9b0a4f1d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enums first
    compliance_status_enum = postgresql.ENUM('valid', 'expiring_soon', 'expired', name='compliance_status')
    compliance_status_enum.create(op.get_bind(), checkfirst=True)
    
    vehicle_types_enum = postgresql.ENUM('car', 'auto', 'bus', 'truck', 'bike', name='vehicle_types')
    vehicle_types_enum.create(op.get_bind(), checkfirst=True)
    
    station_load_enum = postgresql.ENUM('free', 'normal', 'busy', name='station_load_status')
    station_load_enum.create(op.get_bind(), checkfirst=True)
    
    fuel_availability_enum = postgresql.ENUM('available', 'limited', 'unavailable', name='fuel_availability_status')
    fuel_availability_enum.create(op.get_bind(), checkfirst=True)
    
    document_types_enum = postgresql.ENUM('rc', 'insurance', 'pollution', 'cng_certificate', 'other', name='document_types')
    document_types_enum.create(op.get_bind(), checkfirst=True)

    # Create tables
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('vehicle_owner', 'station_operator', 'admin', name='user_roles'), nullable=False),
        sa.Column('phone', sa.String(length=15), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    op.create_table('fuel_stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('pincode', sa.String(length=10), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('phone', sa.String(length=15), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_open', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, default=False),
        sa.Column('approval_date', sa.DateTime(), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('live_load', station_load_enum, nullable=False, default='normal'),
        sa.Column('fuel_availability', fuel_availability_enum, nullable=False, default='available'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now() on update now()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_number', sa.String(length=20), nullable=False),
        sa.Column('owner_name', sa.String(length=100), nullable=False),
        sa.Column('vehicle_type', vehicle_types_enum, nullable=False),
        sa.Column('cng_test_date', sa.Date(), nullable=True),
        sa.Column('cng_expiry_date', sa.Date(), nullable=True),
        sa.Column('compliance_status', compliance_status_enum, nullable=False, default='valid'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now() on update now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vehicle_number')
    )
    
    op.create_table('compliance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('checker_id', sa.Integer(), nullable=False),
        sa.Column('check_type', sa.Enum('manual', 'camera', 'qr', name='check_types'), nullable=False),
        sa.Column('compliance_status', compliance_status_enum, nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['checker_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['station_id'], ['fuel_stations.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=True),
        sa.Column('document_type', document_types_enum, nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.Enum('system', 'compliance', 'alert', 'reminder', name='notification_types'), nullable=False),
        sa.Column('priority', sa.Enum('low', 'normal', 'high', name='priority_levels'), nullable=False, default='normal'),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('qr_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('qr_code_path', sa.String(length=500), nullable=False),
        sa.Column('qr_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('station_ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['station_id'], ['fuel_stations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('station_employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, default='operator'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['station_id'], ['fuel_stations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_vehicle_number', 'vehicles', ['vehicle_number'])
    op.create_index('idx_compliance_status', 'vehicles', ['compliance_status'])
    op.create_index('idx_compliance_station_date', 'compliance_records', ['station_id', 'created_at'])
    op.create_index('idx_station_location', 'fuel_stations', ['latitude', 'longitude'])
    op.create_index('idx_notifications_user_read', 'notifications', ['user_id', 'is_read'])
    op.create_index('idx_documents_user_vehicle', 'documents', ['user_id', 'vehicle_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('station_employees')
    op.drop_table('station_ratings')
    op.drop_table('qr_codes')
    op.drop_table('notifications')
    op.drop_table('documents')
    op.drop_table('compliance_records')
    op.drop_table('vehicles')
    op.drop_table('fuel_stations')
    op.drop_table('users')
    
    # Drop enums
    compliance_status_enum = postgresql.ENUM(name='compliance_status')
    compliance_status_enum.drop(op.get_bind(), checkfirst=True)
    
    vehicle_types_enum = postgresql.ENUM(name='vehicle_types')
    vehicle_types_enum.drop(op.get_bind(), checkfirst=True)
    
    station_load_enum = postgresql.ENUM(name='station_load_status')
    station_load_enum.drop(op.get_bind(), checkfirst=True)
    
    fuel_availability_enum = postgresql.ENUM(name='fuel_availability_status')
    fuel_availability_enum.drop(op.get_bind(), checkfirst=True)
    
    document_types_enum = postgresql.ENUM(name='document_types')
    document_types_enum.drop(op.get_bind(), checkfirst=True)
    
    user_roles_enum = postgresql.ENUM(name='user_roles')
    user_roles_enum.drop(op.get_bind(), checkfirst=True)
    
    check_types_enum = postgresql.ENUM(name='check_types')
    check_types_enum.drop(op.get_bind(), checkfirst=True)
    
    notification_types_enum = postgresql.ENUM(name='notification_types')
    notification_types_enum.drop(op.get_bind(), checkfirst=True)
    
    priority_levels_enum = postgresql.ENUM(name='priority_levels')
    priority_levels_enum.drop(op.get_bind(), checkfirst=True)