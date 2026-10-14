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
for _c in CITIES.values():
    _c.update(tz="Asia/Kolkata", country="India")

# world cities: name → (lat, lon, zoom, tz, country, north-India-crop-fires?)
_WORLD = {
    "London": (51.5074, -0.1278, 9.8, "Europe/London", "United Kingdom"),
    "Paris": (48.8566, 2.3522, 10.2, "Europe/Paris", "France"),
    "Berlin": (52.5200, 13.4050, 10, "Europe/Berlin", "Germany"),
    "New York": (40.7128, -74.0060, 9.8, "America/New_York", "United States"),
    "Los Angeles": (34.0522, -118.2437, 9.2, "America/Los_Angeles", "United States"),
    "Toronto": (43.6532, -79.3832, 10, "America/Toronto", "Canada"),
    "Mexico City": (19.4326, -99.1332, 9.8, "America/Mexico_City", "Mexico"),
    "São Paulo": (-23.5505, -46.6333, 9.6, "America/Sao_Paulo", "Brazil"),
    "Lahore": (31.5204, 74.3587, 10.2, "Asia/Karachi", "Pakistan"),
    "Karachi": (24.8607, 67.0011, 9.8, "Asia/Karachi", "Pakistan"),
    "Dhaka": (23.8103, 90.4125, 10.4, "Asia/Dhaka", "Bangladesh"),
    "Kathmandu": (27.7172, 85.3240, 11, "Asia/Kathmandu", "Nepal"),
    "Beijing": (39.9042, 116.4074, 9.6, "Asia/Shanghai", "China"),
    "Shanghai": (31.2304, 121.4737, 9.6, "Asia/Shanghai", "China"),
    "Bangkok": (13.7563, 100.5018, 10, "Asia/Bangkok", "Thailand"),
    "Jakarta": (-6.2088, 106.8456, 10, "Asia/Jakarta", "Indonesia"),
    "Singapore": (1.3521, 103.8198, 10.4, "Asia/Singapore", "Singapore"),
    "Tokyo": (35.6762, 139.6503, 9.6, "Asia/Tokyo", "Japan"),
    "Seoul": (37.5665, 126.9780, 10, "Asia/Seoul", "South Korea"),
    "Dubai": (25.2048, 55.2708, 9.8, "Asia/Dubai", "United Arab Emirates"),
    "Cairo": (30.0444, 31.2357, 10, "Africa/Cairo", "Egypt"),
    "Lagos": (6.5244, 3.3792, 10, "Africa/Lagos", "Nigeria"),
    "Sydney": (-33.8688, 151.2093, 9.6, "Australia/Sydney", "Australia"),
}
for _name, (_lat, _lon, _zoom, _tz, _country) in _WORLD.items():
    CITIES[_name] = {"center": {"lat": _lat, "lon": _lon}, "zoom": _zoom, "tz": _tz, "country": _country, "north": False,
                     "bounds": (_lat - 0.35, _lon - 0.45, _lat + 0.35, _lon + 0.45)}


def _city(city, rows):
    return {name: {"lat": lat, "lon": lon, "zone": zone, "city": city} for name, lat, lon, zone in rows}


def tz_of(loc: dict) -> str:
    return loc.get("tz") or CITIES.get(loc.get("city"), {}).get("tz", "Asia/Kolkata")


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


# a few well-known neighbourhoods per world city (approximate centres)
_WORLD_LOCS = {
    "London": [("Westminster", 51.4975, -0.1357), ("Camden", 51.5390, -0.1426), ("Canary Wharf", 51.5054, -0.0235),
               ("Heathrow", 51.4700, -0.4543)],
    "Paris": [("Paris Centre", 48.8606, 2.3376), ("La Défense", 48.8919, 2.2380), ("Montmartre", 48.8867, 2.3431)],
    "Berlin": [("Mitte", 52.5200, 13.4049), ("Kreuzberg", 52.4986, 13.4030), ("Charlottenburg", 52.5163, 13.3041)],
    "New York": [("Midtown Manhattan", 40.7549, -73.9840), ("Brooklyn", 40.6782, -73.9442), ("Queens", 40.7282, -73.7949),
                 ("The Bronx", 40.8448, -73.8648)],
    "Los Angeles": [("Downtown LA", 34.0407, -118.2468), ("Santa Monica", 34.0195, -118.4912), ("Pasadena", 34.1478, -118.1445),
                    ("Long Beach", 33.7701, -118.1937)],
    "Toronto": [("Downtown Toronto", 43.6510, -79.3470), ("North York", 43.7615, -79.4111), ("Scarborough", 43.7764, -79.2318)],
    "Mexico City": [("Centro Histórico", 19.4326, -99.1332), ("Polanco", 19.4333, -99.1950), ("Coyoacán", 19.3467, -99.1617)],
    "São Paulo": [("Centro (São Paulo)", -23.5489, -46.6388), ("Pinheiros", -23.5674, -46.7019), ("Santo Amaro", -23.6543, -46.7096)],
    "Lahore": [("Gulberg", 31.5204, 74.3487), ("Lahore Old City", 31.5820, 74.3294), ("DHA Lahore", 31.4697, 74.4061)],
    "Karachi": [("Saddar", 24.8556, 67.0237), ("Clifton", 24.8138, 67.0300), ("Korangi", 24.8297, 67.1357)],
    "Dhaka": [("Gulshan", 23.7925, 90.4078), ("Old Dhaka", 23.7104, 90.4074), ("Mirpur", 23.8223, 90.3654)],
    "Kathmandu": [("Thamel", 27.7154, 85.3123), ("Lalitpur", 27.6644, 85.3188), ("Bhaktapur", 27.6710, 85.4298)],
    "Beijing": [("Dongcheng", 39.9288, 116.4164), ("Chaoyang", 39.9215, 116.4434), ("Haidian", 39.9593, 116.2981)],
    "Shanghai": [("Huangpu", 31.2317, 121.4846), ("Pudong", 31.2215, 121.5440), ("Xuhui", 31.1883, 121.4365)],
    "Bangkok": [("Sukhumvit", 13.7380, 100.5600), ("Silom", 13.7246, 100.5300), ("Chatuchak", 13.8283, 100.5597)],
    "Jakarta": [("Central Jakarta", -6.1865, 106.8341), ("South Jakarta", -6.2615, 106.8106), ("North Jakarta", -6.1384, 106.8630)],
    "Singapore": [("Marina Bay", 1.2834, 103.8607), ("Jurong", 1.3329, 103.7436), ("Tampines", 1.3496, 103.9568)],
    "Tokyo": [("Shinjuku", 35.6938, 139.7034), ("Shibuya", 35.6580, 139.7016), ("Tokyo Station", 35.6812, 139.7671)],
    "Seoul": [("Jongno", 37.5730, 126.9794), ("Gangnam", 37.4979, 127.0276), ("Mapo", 37.5663, 126.9019)],
    "Dubai": [("Downtown Dubai", 25.1972, 55.2744), ("Deira", 25.2711, 55.3075), ("Dubai Marina", 25.0805, 55.1403)],
    "Cairo": [("Downtown Cairo", 30.0444, 31.2357), ("Giza", 30.0131, 31.2089), ("Heliopolis", 30.0911, 31.3225)],
    "Lagos": [("Victoria Island", 6.4281, 3.4219), ("Ikeja", 6.6018, 3.3515), ("Lekki", 6.4698, 3.5852)],
    "Sydney": [("Sydney CBD", -33.8688, 151.2093), ("Parramatta", -33.8150, 151.0011), ("Bondi", -33.8915, 151.2767)],
}
for _wcity, _locs in _WORLD_LOCS.items():
    LOCATIONS.update(_city(_wcity, [(n, la, lo, _wcity) for n, la, lo in _locs]))


def city_locations(city):
    return {n: v for n, v in LOCATIONS.items() if v["city"] == city}


# kept for older imports
DELHI_CENTER = CITIES["Delhi NCR"]["center"]
DELHI_BOUNDS = CITIES["Delhi NCR"]["bounds"]
