import re
with open('c:/Users/gouth/OneDrive/Desktop/TRANSOVA/truck_booking_system/bookings/views.py', 'r') as f:
    content = f.read()
    # Find driver_reject_job function
    match = re.search(r'def driver_reject_job.*?return redirect', content, re.DOTALL)
    if match:
        print(match.group())
