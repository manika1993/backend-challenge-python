import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

GUEST_A_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_A_UNIT_2: dict = {
    'unit_id': '2', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_B_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestB', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}


@pytest.fixture()
def test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.freeze_time('2023-05-21')
def test_create_fresh_booking(test_db):
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text
    response.raise_for_status()

    # Guests want to book same unit again
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The given guest name cannot book the same unit multiple times'


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_different_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # Guest wants to book another unit
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_2
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The same guest cannot be in multiple units at the same time'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied
    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given check-in date, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking_different_date(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied
    response = client.post(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestB',  # different guest
            # check_in date of GUEST A + 1, the unit is already booked on this date
            'check_in_date': (datetime.date.today() + datetime.timedelta(1)).strftime('%Y-%m-%d'),
            'number_of_nights': 5
        }
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given check-in date, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_guest_same_unit_booking_extension(test_db):
    # Create first booking for GuestA
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestA trying to extend a booking
    response = client.put(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestA',  # same guest
            # new check_in date of GUEST A is the previous check-out date
            'check_in_date': (datetime.datetime.strptime(GUEST_A_UNIT_1['check_in_date'], '%Y-%m-%d') +
                              datetime.timedelta(GUEST_A_UNIT_1['number_of_nights'])).strftime('%Y-%m-%d'),
            'number_of_nights': 5
        }
    )

    response.raise_for_status()
    assert response.status_code == 200, response.text


@pytest.mark.freeze_time('2023-05-21')
def test_guest_same_unit_booking_extension_different_date(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestA trying to extend a booking with a different date than the current check-out date
    response = client.put(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestA',  # same guest
            # new check_in date of GUEST A is different (2 days ahead) from the previous check-out date
            'check_in_date': (datetime.date.today() +
                              datetime.timedelta(GUEST_A_UNIT_1['number_of_nights'] + 2)).strftime('%Y-%m-%d'),
            'number_of_nights': 5
        }
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'New check-in date is not equal to the previous check-out date'


@pytest.mark.freeze_time('2023-05-21')
def test_guest_same_unit_booking_extension_different_guest(test_db):
    # Create first booking for GuestA
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # Create a booking for GuestB for the same unit after GuestA
    check_out_date_guest_a = (datetime.datetime.strptime(GUEST_A_UNIT_1['check_in_date'], '%Y-%m-%d') +
                              datetime.timedelta(GUEST_A_UNIT_1['number_of_nights'])).strftime('%Y-%m-%d')
    GUEST_B_UNIT_1['check_in_date'] = check_out_date_guest_a
    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestA trying to extend a booking but the unit is booked by another guest
    response = client.put(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestA',  # same guest
            # new check_in date of GUEST A is the previous check-out date
            'check_in_date': check_out_date_guest_a,
            'number_of_nights': 5
        }
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given number of nights, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_guest_same_unit_booking_extension_different_guest_different_dates(test_db):
    # Create first booking for GuestA
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # Create a booking for GuestB for the same unit after GuestA
    check_out_date_guest_a = (datetime.datetime.strptime(GUEST_A_UNIT_1['check_in_date'], '%Y-%m-%d') +
                              datetime.timedelta(GUEST_A_UNIT_1['number_of_nights'])).strftime('%Y-%m-%d')
    GUEST_B_UNIT_1['check_in_date'] = (datetime.datetime.strptime(check_out_date_guest_a, '%Y-%m-%d') +
                                       datetime.timedelta(2)).strftime('%Y-%m-%d')
    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestA trying to extend a booking but the unit is booked by another guest
    response = client.put(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestA',  # same guest
            # new check_in date of GUEST A is the previous check-out date
            'check_in_date': check_out_date_guest_a,
            'number_of_nights': 5
        }
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given number of nights, the unit is already occupied'
