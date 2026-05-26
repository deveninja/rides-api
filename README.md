# Wingz Ride API

A production-oriented Django REST Framework project for the Wingz assessment. It exposes a rides API with admin-only access, optimized related-object loading, filtering, pagination, and distance-based ordering.

## What is included

- Django REST Framework viewsets for `Ride`, `User`, and `RideEvent`
- Custom user model with `role` support
- Admin-only API access control
- Ride list endpoint with pagination
- Filtering by ride status and rider email
- Ordering by pickup time or distance from a supplied pickup coordinate
- `todays_ride_events` on each ride, loaded with a filtered prefetch so the full ride-event table is never pulled into memory
- Database configuration that works from `.env` and supports `DATABASE_URL` plus direct backend settings
- Tests that cover access control, filtering, ordering, pagination, and query count behavior

## Project layout

- [wingz_api/settings.py](wingz_api/settings.py) for environment-driven settings
- [rides/models.py](rides/models.py) for the data model and custom user implementation
- [rides/api/views.py](rides/api/views.py) for API viewsets and token authentication
- [rides/api/serializers.py](rides/api/serializers.py) for read and write serializers
- [rides/api/filters.py](rides/api/filters.py) for filtering and ordering logic
- [rides/query_helpers.py](rides/query_helpers.py) for queryset optimizations
- [rides/tests.py](rides/tests.py) for requirement-focused API coverage

This structure keeps the domain model in `rides/models.py`, performance helpers in `rides/query_helpers.py`, and HTTP concerns under `rides/api/`, which makes the app easier to extend when new rider, driver, dispatch, or pricing features are added.

## Local setup

1. Create and activate a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -e .
```

If you need a specific database backend, install the matching optional extra:

```bash
pip install -e .[postgres]
pip install -e .[mysql]
pip install -e .[oracle]
```

3. Copy `.env.example` to `.env` and adjust values.
4. Run migrations:

```bash
python manage.py migrate
```

5. Create an admin-role user:

```bash
python manage.py createsuperuser
```

6. Run the API:

```bash
python manage.py runserver
```

7. Run the tests:

```bash
python manage.py test
```

## Swagger UI

Once the app is running, open these endpoints in your browser:

- [API docs](http://127.0.0.1:8000/api/docs/)
- [OpenAPI schema](http://127.0.0.1:8000/api/schema/)

If you are using token auth, click the Swagger `Authorize` button and provide your token as `Token <your-token>`.

## Environment variables

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode flag
- `ALLOWED_HOSTS`: Comma-separated host list
- `CSRF_TRUSTED_ORIGINS`: Comma-separated trusted origins
- `DATABASE_URL`: Full database URL, for example `postgres://user:pass@host:5432/name`
- `DATABASE_ENGINE`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`: Direct DB settings fallback when `DATABASE_URL` is not set
- `PAGE_SIZE`: Page size for ride list pagination

## API notes

### Authentication and access control

The API is restricted to authenticated users whose `role` is `admin`. Unauthenticated requests receive `401 Unauthorized`, and authenticated non-admin users receive `403 Forbidden`.

You can authenticate in one of two ways:

1. Use the browsable API session login at `GET /api-auth/login/`.
2. Obtain a token at `POST /api/token-auth/` with JSON or form data containing `email` set to the admin email and `password` set to the password, then send `Authorization: Token <token>`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/token-auth/ \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"your-password"}'
```

### Ride list endpoint

`GET /api/rides/`

Query parameters:

- `status`: Filter by ride status
- `rider_email`: Filter by rider email
- `ordering`: `pickup_time`, `-pickup_time`, `distance`, or `-distance`
- `pickup_latitude` and `pickup_longitude`: Required when ordering by distance
- `page`: Standard page number pagination

The list response includes nested rider and driver objects plus recent ride events exposed as both `ride_events` and `todays_ride_events`. The detail response includes the full ride-event history in `ride_events` and the recent subset in `todays_ride_events`.

### Requirement coverage

- Functionality: CRUD endpoints exist for `Ride`, `User`, and `RideEvent`, with the list endpoint on `Ride` supporting pagination, filtering, and sorting.
- Code quality: serializers, filters, views, and query helpers are split by responsibility so future features can be added without bloating a single module.
- Error handling: invalid distance ordering requests return `400 Bad Request`, invalid credentials return `400`, anonymous requests return `401`, and authenticated non-admin requests return `403`.
- Performance: the ride list uses `select_related` plus a filtered `Prefetch` for `todays_ride_events`, and the test suite verifies the list can still execute in 3 queries including pagination count.

## SQL report

The assessment also asks for a raw SQL report that groups trips longer than one hour by month and driver. The exact query depends on your SQL dialect, but the logic is:

- Join rides to ride events twice, once for pickup and once for dropoff
- Compute the timestamp difference between the two events
- Group by driver and month
- Filter to durations greater than one hour

Example MySQL/MariaDB version (matches this project environment):

```sql
WITH trip_events AS (
    SELECT
        r.id_ride,
        r.id_driver,
        MIN(CASE WHEN re.description = 'Status changed to pickup' THEN re.created_at END) AS pickup_at,
        MIN(CASE WHEN re.description = 'Status changed to dropoff' THEN re.created_at END) AS dropoff_at
    FROM ride AS r
    JOIN ride_event AS re ON re.id_ride = r.id_ride
    WHERE re.description IN ('Status changed to pickup', 'Status changed to dropoff')
    GROUP BY r.id_ride, r.id_driver
)
SELECT
    DATE_FORMAT(te.dropoff_at, '%Y-%m') AS month,
    CONCAT(u.first_name, ' ', LEFT(u.last_name, 1)) AS driver,
    COUNT(*) AS trip_count
FROM trip_events AS te
JOIN user AS u ON u.id_user = te.id_driver
WHERE te.pickup_at IS NOT NULL
  AND te.dropoff_at IS NOT NULL
  AND te.dropoff_at > te.pickup_at
  AND TIMESTAMPDIFF(MINUTE, te.pickup_at, te.dropoff_at) > 60
GROUP BY month, driver
ORDER BY month, driver;
```

Equivalent PostgreSQL version:

```sql
WITH trip_events AS (
    SELECT
        r.id_ride,
        r.id_driver,
        MIN(re.created_at) FILTER (
            WHERE re.description = 'Status changed to pickup'
        ) AS pickup_at,
        MIN(re.created_at) FILTER (
            WHERE re.description = 'Status changed to dropoff'
        ) AS dropoff_at
    FROM ride AS r
    JOIN ride_event AS re ON re.id_ride = r.id_ride
    WHERE re.description IN ('Status changed to pickup', 'Status changed to dropoff')
    GROUP BY r.id_ride, r.id_driver
)
SELECT
    TO_CHAR(DATE_TRUNC('month', te.dropoff_at), 'YYYY-MM') AS month,
    CONCAT(u.first_name, ' ', LEFT(u.last_name, 1)) AS driver,
    COUNT(*) AS trip_count
FROM trip_events AS te
JOIN "user" AS u ON u.id_user = te.id_driver
WHERE te.pickup_at IS NOT NULL
  AND te.dropoff_at IS NOT NULL
  AND te.dropoff_at > te.pickup_at
  AND te.dropoff_at - te.pickup_at > INTERVAL '1 hour'
GROUP BY month, driver
ORDER BY month, driver;
```

## Design decisions

- The ride list uses `select_related` for rider and driver, and a filtered `Prefetch` with `to_attr` for recent events, which keeps the query count small and avoids loading the full ride-event table.
- Distance ordering is computed in the database so pagination still works after ordering.
- The database layer is configured from `.env` and supports direct backend settings or a single `DATABASE_URL` for portability.
