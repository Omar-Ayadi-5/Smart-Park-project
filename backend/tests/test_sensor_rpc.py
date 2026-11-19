import json
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from app import db
from app.models import ParkingSpot, SensorDevice, SpotHistory


def test_postgres_sensor_mapping_is_scoped_idempotent_and_preserves_oos(app, accounts):
    if db.engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL integration runs in CI with a real service")
    db.session.execute(text((Path(__file__).resolve().parents[1]/'database/sensor_rpc.sql').read_text()))
    free=ParkingSpot.query.filter_by(status='FREE').one()
    device=SensorDevice(subject='00000000-0000-0000-0000-000000000001',spot_id=free.id)
    db.session.add(device);db.session.commit()
    db.session.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"),
        {'claims':json.dumps({'sub':device.subject})})
    assert db.session.execute(text('SELECT public.sync_spot(true)')).scalar()=='OCCUPIED'
    assert db.session.execute(text('SELECT public.sync_spot(true)')).scalar()=='OCCUPIED'
    assert SpotHistory.query.count()==1
    db.session.execute(text("UPDATE public.parking_spot SET status='OUT_OF_SERVICE' WHERE id=:id"),{'id':free.id})
    assert db.session.execute(text('SELECT public.sync_spot(false)')).scalar()=='OUT_OF_SERVICE'
    assert SpotHistory.query.count()==1
    db.session.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"),{'claims':'{"sub":"unregistered"}'})
    with pytest.raises(DBAPIError):db.session.execute(text('SELECT public.sync_spot(false)'))
    db.session.rollback()
