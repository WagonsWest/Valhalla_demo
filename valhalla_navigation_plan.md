# Valhalla Navigation — Local Demo Plan

## Goal

Get a local A→B routing demo working with Valhalla on Tokyo/Kanto OSM data, running entirely on the local PC. This serves as a proof-of-concept before integrating navigation into the Wayzen app.

## Architecture

```
[OSM PBF Extract] → [Valhalla Docker Container] → [REST API on localhost:8002]
                                                         ↑
                                                   Flutter app / curl
```

## Prerequisites

- Docker Desktop installed and running on Windows
- ~2GB free disk space (PBF + routing tiles)
- ~4GB RAM available for tile building

## Phase 1: Valhalla Server Setup

### 1.1 Download Kanto Region OSM Extract

Source: Geofabrik — Kanto region (~300-400MB)

```
https://download.geofabrik.de/asia/japan/kanto-latest.osm.pbf
```

If Kanto is unavailable as a standalone extract, use the full Japan PBF (~1.5GB):
```
https://download.geofabrik.de/asia/japan-latest.osm.pbf
```

### 1.2 Run Valhalla via Docker

```bash
mkdir -p valhalla_data
cp kanto-latest.osm.pbf valhalla_data/

docker run -dt --name valhalla \
  -p 8002:8002 \
  -v ./valhalla_data:/custom_files \
  -e tile_urls=http://download.geofabrik.de/asia/japan/kanto-latest.osm.pbf \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
```

Alternatively, if you already downloaded the PBF:
```bash
docker run -dt --name valhalla \
  -p 8002:8002 \
  -v ./valhalla_data:/custom_files \
  -e use_tiles_ignore_pbf=False \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
```

First run will build routing tiles from the PBF — this takes 10-30 minutes depending on extract size.

### 1.3 Verify Server is Running

```bash
curl http://localhost:8002/status
```

## Phase 2: Test A→B Routing

### 2.1 Test Route: Tokyo Station → Shibuya Station

```bash
curl -s http://localhost:8002/route \
  --data '{
    "locations": [
      {"lat": 35.6812, "lon": 139.7671},
      {"lat": 35.6580, "lon": 139.7016}
    ],
    "costing": "auto",
    "directions_options": {"units": "km"}
  }' | python -m json.tool
```

### 2.2 Expected Response Structure

```json
{
  "trip": {
    "locations": [...],
    "legs": [{
      "maneuvers": [
        {
          "instruction": "Drive northeast on ...",
          "length": 0.5,
          "time": 30,
          "type": 1
        }
      ],
      "shape": "<encoded polyline>",
      "summary": {
        "length": 7.2,
        "time": 1200
      }
    }],
    "summary": {
      "length": 7.2,
      "time": 1200
    }
  }
}
```

### 2.3 Other Costing Modes to Test

- `"costing": "auto"` — car routing
- `"costing": "bicycle"` — bike routing
- `"costing": "pedestrian"` — walking
- `"costing": "motor_scooter"` — scooter

## Phase 3: Flutter Integration (Future — Wayzen App)

### 3.1 Add Endpoint

In `lib/config/endpoints.dart`:
```dart
static const String valhallaRoute = 'http://<server>:8002/route';
```

### 3.2 Routing Service

- Build request JSON with origin/destination coordinates and costing mode
- POST to Valhalla `/route` endpoint
- Parse response: decode polyline shape, extract maneuvers, distance, duration

### 3.3 Map Rendering

- Decode the encoded polyline from `trip.legs[].shape` (Valhalla uses encoded polyline6 format, 6 decimal precision)
- Draw as a polyline layer on the map
- Display turn-by-turn maneuvers

## Hosting Plan (Production)

- AWS EC2 `t3.medium` in `ap-northeast-1` (Tokyo) — same region as existing S3 bucket
- Japan-only OSM data: ~4-6GB routing tiles, fits comfortably in 4GB RAM
- Estimated cost: ~$32/month
- Periodic OSM data refresh via cron (monthly)

## Useful Valhalla API Endpoints

| Endpoint | Purpose |
|---|---|
| `/route` | A→B turn-by-turn routing |
| `/optimized_route` | Multi-stop route optimization |
| `/isochrone` | Reachability area from a point |
| `/locate` | Snap coordinates to nearest road |
| `/map_matching` | Snap GPS trace to road network |
| `/status` | Health check |

## Resources

- Valhalla Docker image: ghcr.io/gis-ops/docker-valhalla/valhalla
- Valhalla API docs: https://valhalla.github.io/valhalla/
- Geofabrik downloads: https://download.geofabrik.de/asia/japan.html
- Encoded polyline6 decoder needed for shape parsing
