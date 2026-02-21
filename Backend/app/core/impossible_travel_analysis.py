import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime

# City to lat/lon lookup (add more as needed)
CITY_COORDS = {
    'Chennai': (13.0827, 80.2707),
    'Hyderabad': (17.3850, 78.4867),
    'Delhi': (28.6139, 77.2090),
    'Bangalore': (12.9716, 77.5946),
    'Mumbai': (19.0760, 72.8777),
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def flag_impossible_travel(df, speed_threshold_kmh=1000):
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['lat'] = df['ip_city'].map(lambda c: CITY_COORDS.get(c, (None, None))[0])
    df['lon'] = df['ip_city'].map(lambda c: CITY_COORDS.get(c, (None, None))[1])
    df = df.sort_values(['sender_upi', 'timestamp'])
    df['impossible_travel'] = False
    prev = {}
    for idx, row in df.iterrows():
        sender = row['sender_upi']
        lat, lon, t = row['lat'], row['lon'], row['timestamp']
        if sender in prev and lat is not None and lon is not None:
            plat, plon, pt = prev[sender]
            dt_hours = (t - pt).total_seconds() / 3600.0
            if dt_hours > 0:
                dist = haversine(lat, lon, plat, plon)
                speed = dist / dt_hours
                if speed > speed_threshold_kmh:
                    df.at[idx, 'impossible_travel'] = True
        prev[sender] = (lat, lon, t)
    return df

# Example usage:
# df = pd.read_csv('synthetic_upi_behavior_100.csv')
# df = flag_impossible_travel(df)
# print(df[df['impossible_travel']])
