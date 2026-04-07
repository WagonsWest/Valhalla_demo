# Valhalla Navigation Demo

Local A-to-B routing demo using [Valhalla](https://valhalla.github.io/valhalla/) on Kanto (Tokyo region) OpenStreetMap data. This serves as a proof-of-concept before integrating navigation into the Wayzen app.

## Architecture

```
[OSM PBF Extract] --> [Valhalla Docker Container] --> [REST API on localhost:8002]
                                                            |
                                                    [Web UI / curl / Flutter]
```

No custom server code is needed. The [gis-ops/docker-valhalla](https://github.com/gis-ops/docker-valhalla) image handles tile building and API serving out of the box.

## Prerequisites

- **Docker Desktop** installed and running
- **Python 3** (for the dev server)
- ~2 GB free disk space (PBF + routing tiles)
- ~4 GB RAM available during tile building

## Quick Start

### 1. Download OSM data

Download the Kanto region extract from [Geofabrik](https://download.geofabrik.de/asia/japan.html) and place the `.osm.pbf` file in this directory.

### 2. Start Valhalla

```bash
mkdir -p valhalla_data
cp *.osm.pbf valhalla_data/

docker run -dt --name valhalla \
  -p 8002:8002 \
  -v /absolute/path/to/valhalla_data:/custom_files \
  -e use_tiles_ignore_pbf=False \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
```

> **Windows note:** Use an absolute path for the volume mount (e.g. `d:/Wayzen/valhalla_demo/Valhalla_demo/valhalla_data`). Relative paths and `$(pwd)` may not work on Docker for Windows.

First run builds routing tiles from the PBF file. This takes **~25 minutes** for the Kanto extract (441 MB). Subsequent starts are instant since tiles are cached.

Monitor progress with:
```bash
docker logs -f valhalla
```

### 3. Verify the server

```bash
curl http://localhost:8002/status
```

You should see a JSON response with `"version": "3.5.1"` and a list of available actions.

### 4. Start the web UI

```bash
python server.py
```

Open **http://localhost:3000** in your browser. The Python server serves the static files and proxies API calls to Valhalla (to avoid CORS issues).

Click the map to set an origin and destination, choose a transport mode, and hit **Get Route**.

## Test with curl

```bash
# Tokyo Station -> Shibuya Station (car)
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

### Costing modes

| Mode | `costing` value | Example result (Tokyo Sta. to Shibuya) |
|------|-----------------|----------------------------------------|
| Car | `auto` | 7.8 km, ~8 min |
| Bicycle | `bicycle` | 7.8 km, ~29 min |
| Walking | `pedestrian` | 7.4 km, ~90 min |
| Scooter | `motor_scooter` | 7.8 km, ~8 min |

## Available API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/route` | A-to-B turn-by-turn routing |
| `/optimized_route` | Multi-stop route optimization |
| `/isochrone` | Reachability area from a point |
| `/locate` | Snap coordinates to nearest road |
| `/map_matching` | Snap GPS trace to road network |
| `/status` | Health check |

## Docker Management

```bash
docker stop valhalla      # stop the server
docker start valhalla     # restart (uses cached tiles, starts fast)
docker logs valhalla      # view build/server logs
docker rm -f valhalla     # remove container entirely
```

## Project Files

| File | Purpose |
|------|---------|
| `index.html` | Web UI with Leaflet.js map, route visualization, and turn-by-turn display |
| `server.py` | Python dev server that serves static files and proxies API calls to Valhalla |
| `valhalla_data/` | Mounted into Docker; contains the PBF, generated tiles, and `valhalla.json` config |
| `valhalla_navigation_plan.md` | Original planning document |

## Technical Notes

- Valhalla uses **encoded polyline6** format (6 decimal precision), not Google's polyline5. Client code must decode accordingly.
- Street names in the Kanto region are returned in Japanese (Unicode). The API handles this correctly.
- The auto-generated `valhalla_data/valhalla.json` controls server configuration (costing defaults, tile paths, etc.).
- Tile build peaks at ~99% CPU and ~1 GB RAM. Once running, the server idles at <1% CPU and ~285 MB RAM.

---

## Wayzen Integration Plan

This demo validates that Valhalla works for routing in the Kanto region. The next step is integrating it into the Wayzen Flutter app.

### Server Deployment

- **Target:** AWS EC2 `t3.medium` in `ap-northeast-1` (Tokyo), same region as the existing S3 bucket
- **Data:** Japan-only OSM extract, producing ~4-6 GB of routing tiles (fits in 4 GB RAM)
- **Estimated cost:** ~$32/month
- **Data refresh:** Monthly cron job to download fresh OSM data and rebuild tiles

The same Docker image and setup used in this demo can be deployed directly to EC2.

### Flutter Code Required

The Valhalla server requires no custom code. All integration work is on the Flutter client side:

1. **Endpoint configuration** -- Add the Valhalla server URL to `lib/config/endpoints.dart`
2. **Routing service** -- Build request JSON with origin/destination coordinates and costing mode, POST to the `/route` endpoint, parse the response
3. **Polyline6 decoder** -- Valhalla returns route shapes as encoded polyline6 (6 decimal precision). A custom decoder or compatible package is needed since most Flutter polyline packages assume Google's 5-decimal format
4. **Map rendering** -- Decode the polyline and draw it as a layer on the map widget
5. **Turn-by-turn UI** -- Display maneuver instructions from the response, including distance and duration for each step

### API Response Structure

The `/route` response contains everything needed for navigation:

```json
{
  "trip": {
    "legs": [{
      "shape": "<encoded polyline6>",
      "maneuvers": [
        {
          "instruction": "Turn left onto Route 246.",
          "length": 0.5,
          "time": 30,
          "type": 15
        }
      ],
      "summary": {
        "length": 7.8,
        "time": 474
      }
    }]
  }
}
```

### Additional Valhalla Features for Future Use

| Feature | Endpoint | Use Case |
|---------|----------|----------|
| Multi-stop optimization | `/optimized_route` | Delivery/errand routing |
| Reachability areas | `/isochrone` | "What's within 10 min drive?" |
| GPS trace matching | `/map_matching` | Snap recorded trips to roads |
| Coordinate snapping | `/locate` | Find nearest road to a point |

## Resources

- [Valhalla API docs](https://valhalla.github.io/valhalla/)
- [Docker image (gis-ops)](https://github.com/gis-ops/docker-valhalla)
- [Geofabrik downloads (Japan)](https://download.geofabrik.de/asia/japan.html)
