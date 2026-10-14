"""Cities and localities tracked by AQIfyMe (roughly matching CPCB / state-board monitoring sites)."""

# center / zoom drive the maps; bounds = (lat_min, lon_min, lat_max, lon_max) for the live-station query;
# north = crop-fire smoke from Punjab/Haryana is relevant
CITIES = {
    "Delhi NCR":  {"center": {"lat": 28.6139, "lon": 77.2090}, "zoom": 9.3, "bounds": (28.25, 76.84, 28.95, 77.60), "north": True},
    "Mumbai":     {"center": {"lat": 19.0760, "lon": 72.8777}, "zoom": 10, "bounds": (18.85, 72.70, 19.35, 73.15), "north": False},
    "Bengaluru":  {"center": {"lat": 12.9716, "lon": 77.5946}, "zoom": 10, "bounds": (12.75, 77.35, 13.20, 77.85), "north": False},
    "Kolkata":    {"center": {"lat": 22.5726, "lon": 88.3639}, "zoom": 10.5, "bounds": (22.40, 88.20, 22.75, 88.55), "north": False},
    "Chennai":    {"center": {"lat": 13.0827, "lon": 80.2707}, "zoom": 10.3, "bounds": (12.85, 80.05, 13.30, 80.40), "north": False},
    "Hyderabad":  {"center": {"lat": 17.3850, "lon": 78.4867}, "zoom": 10.3, "bounds": (17.20, 78.25, 17.60, 78.70), "north": False},
    "Pune":       {"center": {"lat": 18.5204, "lon": 73.8567}, "zoom": 10.5, "bounds": (18.40, 73.65, 18.70, 74.05), "north": False},
    "Lucknow":    {"center": {"lat": 26.8467, "lon": 80.9462}, "zoom": 10.8, "bounds": (26.70, 80.80, 27.00, 81.10), "north": True},
    "Chandigarh": {"center": {"lat": 30.7333, "lon": 76.7794}, "zoom": 11.2, "bounds": (30.62, 76.65, 30.85, 76.90), "north": True},
    "Patna":      {"center": {"lat": 25.5941, "lon": 85.1376}, "zoom": 11, "bounds": (25.50, 84.95, 25.70, 85.30), "north": True},
}
DEFAULT_CITY = "Delhi NCR"


def _city(city, rows):
    return {name: {"lat": lat, "lon": lon, "zone": zone, "city": city} for name, lat, lon, zone in rows}


LOCATIONS = {
    **_city("Delhi NCR", [
        ("Anand Vihar", 28.6469, 77.3160, "East Delhi"), ("ITO", 28.6289, 77.2410, "Central Delhi"),
        ("Connaught Place", 28.6315, 77.2167, "Central Delhi"), ("Chandni Chowk", 28.6562, 77.2300, "Central Delhi"),
        ("Lodhi Road", 28.5918, 77.2273, "South Delhi"), ("RK Puram", 28.5633, 77.1869, "South Delhi"),
        ("Okhla Phase-2", 28.5308, 77.2713, "South Delhi"), ("Nehru Nagar", 28.5679, 77.2507, "South Delhi"),
        ("Saket", 28.5245, 77.2066, "South Delhi"), ("Vasant Kunj", 28.5293, 77.1530, "South-West Delhi"),
        ("Dwarka Sector 8", 28.5710, 77.0719, "South-West Delhi"), ("IGI Airport (T3)", 28.5562, 77.1000, "South-West Delhi"),
        ("Najafgarh", 28.6090, 76.9798, "South-West Delhi"), ("Punjabi Bagh", 28.6740, 77.1310, "West Delhi"),
        ("Mundka", 28.6823, 77.0303, "West Delhi"), ("Karol Bagh", 28.6519, 77.1909, "Central Delhi"),
        ("Ashok Vihar", 28.6950, 77.1818, "North Delhi"), ("Rohini", 28.7325, 77.1197, "North-West Delhi"),
        ("Jahangirpuri", 28.7328, 77.1707, "North Delhi"), ("Bawana", 28.7762, 77.0511, "North-West Delhi"),
        ("Narela", 28.8227, 77.1020, "North Delhi"), ("Wazirpur", 28.6999, 77.1655, "North Delhi"),
        ("Patparganj", 28.6238, 77.2872, "East Delhi"), ("Shahdara", 28.6731, 77.2898, "East Delhi"),
        ("Vivek Vihar", 28.6723, 77.3152, "East Delhi"),
        ("Noida Sector 62", 28.6270, 77.3726, "Noida"), ("Noida Sector 125", 28.5447, 77.3255, "Noida"),
        ("Greater Noida", 28.4744, 77.5040, "Noida"),
        ("Gurugram Vikas Sadan", 28.4502, 77.0263, "Gurugram"), ("Gurugram Sector 51", 28.4229, 77.0670, "Gurugram"),
        ("Gurugram Cyber City", 28.4950, 77.0890, "Gurugram"),
        ("Ghaziabad Vasundhara", 28.6603, 77.3573, "Ghaziabad"), ("Indirapuram", 28.6411, 77.3712, "Ghaziabad"),
        ("Loni", 28.7570, 77.2860, "Ghaziabad"),
        ("Faridabad Sector 16A", 28.4089, 77.3178, "Faridabad"), ("Ballabgarh", 28.3394, 77.3260, "Faridabad"),
    ]),
    **_city("Mumbai", [
        ("Colaba", 18.9067, 72.8147, "South Mumbai"), ("Bandra", 19.0596, 72.8295, "Western suburbs"),
        ("Andheri", 19.1136, 72.8697, "Western suburbs"), ("Borivali", 19.2307, 72.8567, "Western suburbs"),
        ("Powai", 19.1176, 72.9060, "Eastern suburbs"), ("Chembur", 19.0522, 72.9005, "Eastern suburbs"),
        ("Navi Mumbai (Vashi)", 19.0771, 72.9986, "Navi Mumbai"),
    ]),
    **_city("Bengaluru", [
        ("Koramangala", 12.9352, 77.6245, "South-East"), ("Jayanagar", 12.9250, 77.5938, "South"),
        ("Electronic City", 12.8452, 77.6602, "South-East"), ("Whitefield", 12.9698, 77.7500, "East"),
        ("Hebbal", 13.0358, 77.5970, "North"), ("Peenya", 13.0285, 77.5197, "North-West"),
    ]),
    **_city("Kolkata", [
        ("Park Street", 22.5535, 88.3520, "Central"), ("Salt Lake", 22.5800, 88.4116, "East"),
        ("Ballygunge", 22.5276, 88.3653, "South"), ("Jadavpur", 22.4955, 88.3709, "South"),
        ("Howrah", 22.5958, 88.2636, "West bank"),
    ]),
    **_city("Chennai", [
        ("T Nagar", 13.0418, 80.2341, "Central"), ("Anna Nagar", 13.0850, 80.2101, "West"),
        ("Adyar", 13.0012, 80.2565, "South"), ("Velachery", 12.9815, 80.2180, "South"),
        ("Manali (Chennai)", 13.1667, 80.2667, "North"),
    ]),
    **_city("Hyderabad", [
        ("Charminar", 17.3616, 78.4747, "Old City"), ("Banjara Hills", 17.4126, 78.4482, "Central"),
        ("Secunderabad", 17.4399, 78.4983, "North"), ("Hitec City", 17.4435, 78.3772, "West"),
        ("Gachibowli", 17.4401, 78.3489, "West"),
    ]),
    **_city("Pune", [
        ("Shivajinagar", 18.5308, 73.8475, "Central"), ("Kothrud", 18.5074, 73.8077, "West"),
        ("Hinjewadi", 18.5913, 73.7389, "West"), ("Hadapsar", 18.5089, 73.9260, "East"),
    ]),
    **_city("Lucknow", [
        ("Hazratganj", 26.8500, 80.9462, "Central"), ("Gomti Nagar", 26.8560, 81.0040, "East"),
        ("Aliganj", 26.8930, 80.9420, "North"), ("Talkatora", 26.8340, 80.8920, "West"),
    ]),
    **_city("Chandigarh", [
        ("Chandigarh Sector 17", 30.7398, 76.7827, "Central"), ("Chandigarh Sector 25", 30.7550, 76.7630, "West"),
        ("Mohali", 30.7046, 76.7179, "Tricity"), ("Panchkula", 30.6942, 76.8606, "Tricity"),
    ]),
    **_city("Patna", [
        ("Gandhi Maidan", 25.6196, 85.1440, "Central"), ("Danapur", 25.6200, 85.0400, "West"),
        ("Patna City", 25.5960, 85.2290, "East"),
    ]),
}


def city_locations(city):
    return {n: v for n, v in LOCATIONS.items() if v["city"] == city}


# kept for older imports
DELHI_CENTER = CITIES["Delhi NCR"]["center"]
DELHI_BOUNDS = CITIES["Delhi NCR"]["bounds"]
