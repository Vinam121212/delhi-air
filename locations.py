"""Delhi localities tracked by the dashboard (roughly matching CPCB/DPCC monitoring sites)."""

LOCATIONS = {
    "Anand Vihar":      {"lat": 28.6469, "lon": 77.3160, "zone": "East"},
    "ITO":              {"lat": 28.6289, "lon": 77.2410, "zone": "Central"},
    "Connaught Place":  {"lat": 28.6315, "lon": 77.2167, "zone": "Central"},
    "Chandni Chowk":    {"lat": 28.6562, "lon": 77.2300, "zone": "Central"},
    "Lodhi Road":       {"lat": 28.5918, "lon": 77.2273, "zone": "South"},
    "RK Puram":         {"lat": 28.5633, "lon": 77.1869, "zone": "South"},
    "Okhla Phase-2":    {"lat": 28.5308, "lon": 77.2713, "zone": "South"},
    "Nehru Nagar":      {"lat": 28.5679, "lon": 77.2507, "zone": "South"},
    "Saket":            {"lat": 28.5245, "lon": 77.2066, "zone": "South"},
    "Vasant Kunj":      {"lat": 28.5293, "lon": 77.1530, "zone": "South-West"},
    "Dwarka Sector 8":  {"lat": 28.5710, "lon": 77.0719, "zone": "South-West"},
    "IGI Airport (T3)": {"lat": 28.5562, "lon": 77.1000, "zone": "South-West"},
    "Najafgarh":        {"lat": 28.6090, "lon": 76.9798, "zone": "South-West"},
    "Punjabi Bagh":     {"lat": 28.6740, "lon": 77.1310, "zone": "West"},
    "Mundka":           {"lat": 28.6823, "lon": 77.0303, "zone": "West"},
    "Karol Bagh":       {"lat": 28.6519, "lon": 77.1909, "zone": "Central"},
    "Ashok Vihar":      {"lat": 28.6950, "lon": 77.1818, "zone": "North"},
    "Rohini":           {"lat": 28.7325, "lon": 77.1197, "zone": "North-West"},
    "Jahangirpuri":     {"lat": 28.7328, "lon": 77.1707, "zone": "North"},
    "Bawana":           {"lat": 28.7762, "lon": 77.0511, "zone": "North-West"},
    "Narela":           {"lat": 28.8227, "lon": 77.1020, "zone": "North"},
    "Wazirpur":         {"lat": 28.6999, "lon": 77.1655, "zone": "North"},
    "Patparganj":       {"lat": 28.6238, "lon": 77.2872, "zone": "East"},
    "Shahdara":         {"lat": 28.6731, "lon": 77.2898, "zone": "East"},
    "Vivek Vihar":      {"lat": 28.6723, "lon": 77.3152, "zone": "East"},
}

DELHI_CENTER = {"lat": 28.6139, "lon": 77.2090}
# lat_min, lon_min, lat_max, lon_max — used for the WAQI station map
DELHI_BOUNDS = (28.40, 76.84, 28.89, 77.35)
