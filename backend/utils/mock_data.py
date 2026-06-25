"""Mock flight and hotel data for the POC"""

def get_flights():
    return [
        {"flight_no": "6E-204", "airline": "IndiGo", "origin": "BLR", "destination": "DEL",
         "departure": "06:15", "arrival": "09:05", "duration": "2h 50m",
         "price": 4820, "class": "Economy", "seats_left": 12, "stops": 0},
        {"flight_no": "AI-501", "airline": "Air India", "origin": "BLR", "destination": "DEL",
         "departure": "08:30", "arrival": "11:25", "duration": "2h 55m",
         "price": 5340, "class": "Economy", "seats_left": 4, "stops": 0},
        {"flight_no": "UK-834", "airline": "Vistara", "origin": "BLR", "destination": "DEL",
         "departure": "11:00", "arrival": "13:55", "duration": "2h 55m",
         "price": 5900, "class": "Economy", "seats_left": 8, "stops": 0},
        {"flight_no": "6E-312", "airline": "IndiGo", "origin": "BLR", "destination": "BOM",
         "departure": "07:00", "arrival": "08:45", "duration": "1h 45m",
         "price": 3200, "class": "Economy", "seats_left": 15, "stops": 0},
        {"flight_no": "AI-665", "airline": "Air India", "origin": "BLR", "destination": "BOM",
         "departure": "14:20", "arrival": "16:10", "duration": "1h 50m",
         "price": 3750, "class": "Economy", "seats_left": 6, "stops": 0},
        {"flight_no": "6E-451", "airline": "IndiGo", "origin": "DEL", "destination": "BLR",
         "departure": "16:30", "arrival": "19:20", "duration": "2h 50m",
         "price": 4650, "class": "Economy", "seats_left": 9, "stops": 0},
        {"flight_no": "SG-212", "airline": "SpiceJet", "origin": "DEL", "destination": "BLR",
         "departure": "19:45", "arrival": "22:40", "duration": "2h 55m",
         "price": 3980, "class": "Economy", "seats_left": 20, "stops": 0},
    ]


def get_hotels():
    return [
        {"name": "Marriott Whitefield", "city": "Bengaluru", "tier": "Tier-1",
         "price_per_night": 5800, "rating": 4.5, "distance_from_center": "18km",
         "amenities": ["WiFi", "Gym", "Restaurant", "Airport Shuttle"],
         "policy_compliant": True},
        {"name": "ITC Gardenia", "city": "Bengaluru", "tier": "Tier-1",
         "price_per_night": 6000, "rating": 4.7, "distance_from_center": "5km",
         "amenities": ["WiFi", "Pool", "Spa", "Restaurant"],
         "policy_compliant": True},
        {"name": "Lemon Tree Premier", "city": "Bengaluru", "tier": "Tier-1",
         "price_per_night": 4200, "rating": 4.1, "distance_from_center": "8km",
         "amenities": ["WiFi", "Restaurant"],
         "policy_compliant": True},
        {"name": "Taj Mahal Palace", "city": "Mumbai", "tier": "Tier-1",
         "price_per_night": 9500, "rating": 4.9, "distance_from_center": "2km",
         "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Bar"],
         "policy_compliant": False, "policy_note": "Exceeds ₹6000/night limit"},
        {"name": "Novotel Mumbai", "city": "Mumbai", "tier": "Tier-1",
         "price_per_night": 5500, "rating": 4.3, "distance_from_center": "6km",
         "amenities": ["WiFi", "Gym", "Restaurant"],
         "policy_compliant": True},
        {"name": "Courtyard by Marriott", "city": "Delhi", "tier": "Tier-1",
         "price_per_night": 5200, "rating": 4.2, "distance_from_center": "10km",
         "amenities": ["WiFi", "Gym", "Restaurant", "Airport Shuttle"],
         "policy_compliant": True},
    ]


def get_sample_expense_reports():
    return [
        {"id": "EXP-001", "merchant": "Café Coffee Day", "amount": 340,
         "category": "meals", "date": "2025-01-10", "status": "approved"},
        {"id": "EXP-002", "merchant": "Ola Cabs", "amount": 680,
         "category": "transport", "date": "2025-01-10", "status": "approved"},
        {"id": "EXP-003", "merchant": "ITC Gardenia", "amount": 6000,
         "category": "accommodation", "date": "2025-01-11", "status": "pending"},
    ]
