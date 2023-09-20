# Solution

This file explains the solution approach for the two tasks.

### 1. Fix the booking process:
The issue with the booking process lies in the unit availability conditions being checked.
The existing conditions do not include a check for the check-out date of the previous booking.
To fix this, an optional field `check_out_date` is added to the booking table. Check-out date is calculated by adding the number of nights to the check-in date.
In addition to the existing booking conditions, another condition is added such that _a booking is only possible if the input check-in date is greater than the previous check-out date._
This also fixes the failing test.

### 2. Implement a new feature to extend a booking: 
A `put` API is created to extend the booking. This API updates the existing booking to extend it, the number of nights and the check-out date values are updated. 
This API uses the same input and output schema as the create booking API. Some test are also added to for this API. 
The following edge cases/ conditions are checked:
1. Extending a booking is possible if the new check-in date is the same as the previous check-out date, i.e., extension is continuous. A user cannot skip a day/night to extend.
2. The unit must be available for extension, i.e., there should not be another booking for the unit starting from the input check-in date and upto the number of nights for extension.