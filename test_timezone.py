import requests
from datetime import datetime
import pytz

# Test the API with IST timezone
ist = pytz.timezone('Asia/Kolkata')
current_time_ist = datetime.now(ist)
current_time_str = current_time_ist.isoformat()

print(f"Current time (IST): {current_time_str}")
print(f"Current time (readable): {current_time_ist.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")

# Call the API
response = requests.get(f"http://localhost:8000/api/state?current_time={current_time_str}")
data = response.json()

print("\nMedications:")
for med in data.get("medications", []):
    print(f"\nName: {med['name']}")
    print(f"Timings: {med['timings']}")
    print(f"Next dose (ISO): {med.get('next_dose_at')}")
    
    if med.get('next_dose_at'):
        next_dose = datetime.fromisoformat(med['next_dose_at'])
        print(f"Next dose (readable): {next_dose.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
