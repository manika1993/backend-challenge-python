import datetime
from typing import Optional

from pydantic import BaseModel


class BookingBase(BaseModel):
    guest_name: str
    unit_id: str
    check_in_date: datetime.date
    number_of_nights: int
    check_out_date: Optional[datetime.date]

    class Config:
        orm_mode = True
