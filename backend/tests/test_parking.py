from app import db
from app.models import ParkingSpot, SpotHistory, AdminUser


def test_public_dashboard_has_no_account_data(client, accounts):
    response=client.get('/api/parking/dashboard')
    assert response.status_code == 200
    assert response.json['availableSpots']==1
    assert response.json['occupiedSpots']==1
    assert response.json['outOfServiceSpots']==1
    assert 'email' not in response.get_data(as_text=True)
    assert 'password' not in response.get_data(as_text=True)


def test_toggle_records_actor_and_preserves_occupied_spot(client, login, accounts):
    headers=login()
    free=ParkingSpot.query.filter_by(status='FREE').one()
    occupied=ParkingSpot.query.filter_by(status='OCCUPIED').one()
    assert client.patch(f'/api/admin/spot/{free.id}/toggle-oos',headers=headers).json['status']=='OUT_OF_SERVICE'
    history=SpotHistory.query.one()
    assert history.changed_by_admin_id==accounts['admin'].id and history.old_status=='FREE'
    assert client.patch(f'/api/admin/spot/{occupied.id}/toggle-oos',headers=headers).status_code==400
    assert SpotHistory.query.count()==1
    assert client.patch(f'/api/admin/spot/{free.id}/toggle-oos',headers=headers).json['status']=='FREE'


def test_dashboard_empty_and_populated(client, login, accounts):
    response=client.get('/api/admin/dashboard',headers=login())
    assert response.status_code==200
    assert response.json['totalSpots']==3
    assert response.json['occupancyRate']==33
    assert len(response.json['dailyTraffic'])==24
    assert len(response.json['weeklyTrend'])==7


def test_seed_is_repeatable_and_has_no_default_admin(app):
    runner=app.test_cli_runner()
    assert runner.invoke(args=['seed-demo']).exit_code==0
    assert ParkingSpot.query.count()==24
    assert runner.invoke(args=['seed-demo']).exit_code==0
    assert ParkingSpot.query.count()==24 and AdminUser.query.count()==0


def test_bootstrap_admin_is_explicit_and_repeat_safe(app):
    runner=app.test_cli_runner()
    args=['create-admin','--email','owner@example.com','--username','owner','--password','Test-password-42!']
    assert runner.invoke(args=args).exit_code==0
    assert runner.invoke(args=args).exit_code!=0
    assert AdminUser.query.one().is_approved


def test_regular_admin_cannot_delete_other_accounts(client, login, accounts):
    target=accounts['pending'].id
    assert client.delete(f'/api/admin/delete-admin/{target}',headers=login()).status_code==403
    assert db.session.get(AdminUser,target) is not None


def test_deleting_actor_preserves_history(client, login, accounts):
    headers=login()
    free=ParkingSpot.query.filter_by(status='FREE').one()
    assert client.patch(f'/api/admin/spot/{free.id}/toggle-oos',headers=headers).status_code==200
    assert client.delete('/api/admin/delete-account',headers=headers).status_code==200
    event=SpotHistory.query.one()
    assert event.spot_id==free.id and event.changed_by_admin_id is None


def test_device_provisioning_does_not_overwrite_mapping(app, accounts):
    from app.models import SensorDevice
    runner=app.test_cli_runner()
    args=['provision-device','--subject','00000000-0000-0000-0000-000000000001','--spot-code','A1']
    assert runner.invoke(args=args).exit_code==0
    assert runner.invoke(args=args).exit_code==0
    assert runner.invoke(args=args[:-1]+['A2']).exit_code!=0
    assert SensorDevice.query.count()==1
