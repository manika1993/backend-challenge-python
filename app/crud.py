import datetime
from typing import Tuple

from sqlalchemy.orm import Session

from . import models, schemas


class UnableToBook(Exception):
    pass


def create_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    (is_possible, reason) = is_booking_possible(db=db, booking=booking)
    if not is_possible:
        raise UnableToBook(reason)
    db_booking = models.Booking(
        guest_name=booking.guest_name, unit_id=booking.unit_id,
        check_in_date=booking.check_in_date, number_of_nights=booking.number_of_nights,
        check_out_date=(booking.check_in_date + datetime.timedelta(booking.number_of_nights)))
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def is_booking_possible(db: Session, booking: schemas.BookingBase) -> Tuple[bool, str]:
    # check 1 : The Same guest cannot book the same unit multiple times
    is_same_guest_booking_same_unit = db.query(models.Booking) \
        .filter_by(guest_name=booking.guest_name, unit_id=booking.unit_id).first()

    if is_same_guest_booking_same_unit:
        return False, 'The given guest name cannot book the same unit multiple times'

    # check 2 : the same guest cannot be in multiple units at the same time
    is_same_guest_already_booked = db.query(models.Booking) \
        .filter_by(guest_name=booking.guest_name).first()
    if is_same_guest_already_booked:
        return False, 'The same guest cannot be in multiple units at the same time'

    # check 3 : Unit is available for the check-in date
    # Check-in date should be more than previous check-out date for the unit
    is_unit_available_on_check_in_date = db.query(models.Booking) \
        .filter(models.Booking.check_out_date > booking.check_in_date,
                models.Booking.unit_id == booking.unit_id).first()
    if is_unit_available_on_check_in_date:
        return False, 'For the given check-in date, the unit is already occupied'

    return True, 'OK'


def extend_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    (is_possible, reason) = is_extension_possible(db=db, booking=booking)
    if not is_possible:
        raise UnableToBook(reason)
    db_booking = db.query(models.Booking).filter_by(guest_name=booking.guest_name, unit_id=booking.unit_id).first()
    db_booking.number_of_nights += booking.number_of_nights
    db_booking.check_out_date += datetime.timedelta(booking.number_of_nights)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def is_extension_possible(db: Session, booking: schemas.BookingBase) -> Tuple[bool, str]:
    # check 1 : Previous check-out date and new check-in date must be equal
    is_date_continuous = db.query(models.Booking).filter(models.Booking.guest_name == booking.guest_name,
                                                         models.Booking.unit_id == booking.unit_id,
                                                         models.Booking.check_out_date == booking.check_in_date).first()

    if not is_date_continuous:
        return False, 'New check-in date is not equal to the previous check-out date'

    # check 2 : Unit is available for all extension dates
    is_unit_available_on_all_dates = db.query(models.Booking) \
        .filter(models.Booking.unit_id == booking.unit_id,
                models.Booking.check_in_date.between(booking.check_in_date,
                                                     booking.check_in_date +
                                                     datetime.timedelta(booking.number_of_nights))).first()

    if is_unit_available_on_all_dates:
        return False, 'For the given number of nights, the unit is already occupied'

    return True, 'OK'
