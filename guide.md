# Wingz Project Guide

This guide is for studying the full project logic.
It does not replace the project README. README stays focused on setup and running.

## 1. Project Purpose

This project is a Django REST API for ride management (Uber-like domain) with:

- admin-only API access
- Ride, User, RideEvent CRUD APIs
- ride list filtering, pagination, and sorting
- performance-focused loading of recent ride events
- token authentication and Swagger documentation

## 2. Folder Map (What each folder is for)

- `wingz_api/`: Django project container (global settings, URL root, WSGI/ASGI).
- `rides/`: domain app (models, permissions, pagination, query helpers, tests).
- `rides/api/`: HTTP layer for this domain (viewsets, serializers, filters, API router).
- `.env`: runtime configuration (database, secret key, hosts, pagination size).
- `manage.py`: Django command entry point.
- `pyproject.toml`: package metadata and Python dependency constraints.

## 3. Request Lifecycle (End-to-End)

1. Command starts app via `manage.py`.
2. Django loads `wingz_api.settings`.
3. Incoming HTTP route is matched in `wingz_api/urls.py`.
4. `/api/` routes are delegated to `rides/urls.py` then `rides/api/urls.py`.
5. Matching ViewSet in `rides/api/views.py` handles action (`list`, `retrieve`, `create`, etc.).
6. ViewSet chooses serializer class based on action.
7. QuerySet is optimized with `select_related` and filtered `Prefetch` helpers.
8. Response is serialized and returned as JSON.

## 4. File-by-File Logic Walkthrough

## 4.1 `manage.py`

- Imports `os` and `sys` so Django settings can be configured before command execution.
- `main()` sets `DJANGO_SETTINGS_MODULE` to `wingz_api.settings`.
- It imports Django management executor.
- If Django import fails, it raises a clear virtual-environment error message.
- It forwards all CLI arguments (`sys.argv`) to Django.
- The `if __name__ == "__main__"` guard runs `main()` only when file is executed directly.

## 4.2 `pyproject.toml`

- `[build-system]` sets setuptools/wheel backend to build package.
- `[project]` contains package metadata and runtime dependencies.
- Django is pinned to `>=4.2,<5.0` to support MariaDB 10.4 compatibility.
- DRF, django-filter, django-environ, drf-spectacular are core framework dependencies.
- Optional extras support driver-level plug and play:
  - `postgres`
  - `mysql`
  - `oracle`
- Ruff config defines lint rules and style target.

## 4.3 `wingz_api/settings.py`

### Environment loading

- `BASE_DIR` points to project root.
- `environ.Env` defines typed env variables and defaults.
- `.env` is loaded from root.

### Security and host config

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` are read from env.

### Installed apps

- Django core apps.
- DRF (`rest_framework`), filters (`django_filters`), schema docs (`drf_spectacular`), token auth (`rest_framework.authtoken`), and domain app (`rides`).

### Database selection logic

- If `DATABASE_URL` exists, it is used directly.
- Otherwise, engine/name/user/password/host/port fallback settings are used.
- This allows flexible DB switching with minimal changes.

### Auth and i18n

- `AUTH_USER_MODEL = "rides.User"` sets custom user model.
- Password validators are standard Django validators.
- UTC timezone and i18n defaults are enabled.

### DRF config

- Auth classes: Token, Session, Basic.
- Default permission: authenticated user required.
- Default pagination class: `RidePagination`.
- Default schema class: drf-spectacular.

### Swagger/OpenAPI config

- `SPECTACULAR_SETTINGS` sets API title/description/version.
- `SECURITY` declares token auth as default documented scheme.

## 4.4 `wingz_api/urls.py`

Top-level route registration:

- `/admin/` -> Django admin site.
- `/api-auth/` -> browsable API session login/logout.
- `/api/token-auth/` -> custom email+password token endpoint.
- `/api/schema/` -> OpenAPI schema.
- `/api/docs/` -> Swagger UI.
- `/api/` -> domain API routes from rides app.

## 4.5 `rides/models.py`

### `UserManager`

- `create_user`: validates email, normalizes it, hashes password, saves user.
- `create_superuser`: sets admin defaults (`role=admin`, staff, superuser).

### `User` model

- Custom auth model using email as login identifier.
- Fields include role, name, email, phone, status flags.
- `USERNAME_FIELD = "email"` integrates with Django authentication.
- Uses table name `user` and ordering by primary key.

### `Ride` model

- Core ride entity with status, rider FK, driver FK, coordinates, pickup time.
- Uses explicit DB column names (`id_rider`, `id_driver`) to match assessment schema.
- Includes indexes for common filters/sorts:
  - status + pickup_time
  - pickup_time
  - rider + pickup_time
  - driver + pickup_time

### `RideEvent` model

- Event stream linked to a ride (description + timestamp).
- Indexed by ride+created_at and by created_at for scalability.

## 4.6 `rides/permissions.py`

- `IsAdminRole` checks:
  - user exists
  - user is authenticated
  - user role equals `admin`
- This is combined with `IsAuthenticated` in viewsets.

## 4.7 `rides/pagination.py`

- `RidePagination` extends DRF page-number pagination.
- Default page size comes from settings (`PAGE_SIZE`).
- Client can pass `page_size`, capped at 100.

## 4.8 `rides/query_helpers.py`

### `recent_events_prefetch`

- Builds a filtered prefetch to fetch only events in last 24 hours.
- Stores results on each ride as `todays_ride_events`.
- Prevents loading full event history for list endpoint.

### `all_events_prefetch`

- Prefetches complete event history as `prefetched_ride_events`.
- Used for detail endpoint where full event list is needed.

### `distance_annotation`

- Computes SQL expression for ride distance from query point using great-circle formula.
- Uses DB functions (`Radians`, `Cos`, `Sin`, `ACos`) for DB-side sorting.
- clamps cosine to [-1, 1] to avoid floating-point domain errors.

## 4.9 `rides/api/filters.py`

### `RideFilter`

- `status`: case-insensitive match.
- `rider_email`: case-insensitive match via relationship.

### `RideOrderingFilter`

- Allows only: pickup_time asc/desc, distance asc/desc.
- For distance ordering, requires `pickup_latitude` and `pickup_longitude` query params.
- Applies DB annotation then orders by computed distance and `id_ride` for stable sort.

## 4.10 `rides/api/serializers.py`

### User serializers

- `UserReadSerializer`: safe output fields.
- `UserWriteSerializer`: includes optional write-only password.
- `create()` uses `create_user()` so passwords are hashed.
- `update()` updates model fields and re-hashes password when provided.

### RideEvent serializers

- `RideEventReadSerializer`: returns `id_ride` as integer via `ride_id` source.
- `RideEventWriteSerializer`: accepts `id_ride` and resolves it to FK relation.

### Ride serializers

- `RideReadBaseSerializer`:
  - includes `id_rider` and `id_driver` numeric IDs
  - includes nested rider and driver data
  - includes recent event fields
- `RideListSerializer`: list output shape.
- `RideDetailSerializer`:
  - overrides `ride_events` to return full event history when prefetched
- `RideWriteSerializer`:
  - accepts `id_rider` and `id_driver` as input keys
  - validates rider and driver are not the same user

## 4.11 `rides/api/views.py`

### Token auth view

- `EmailAuthTokenSerializer` reads `email` + write-only password.
- `EmailAuthTokenView`:
  - validates payload
  - authenticates user with email/password
  - returns existing or new auth token
  - returns 400 with readable error if credentials are invalid

### Base admin viewset

- `AdminOnlyModelViewSet` enforces `IsAuthenticated` + `IsAdminRole`.

### CRUD endpoints

- `UserViewSet`: admin CRUD on users, read/write serializer split.
- `RideEventViewSet`: admin CRUD on events with `select_related("ride")`.
- `RideViewSet`:
  - list/retrieve/create/update/delete for rides
  - filter backends for query params
  - serializer split by action
  - optimized queryset strategy:
    - list: `select_related` + `recent_events_prefetch`
    - retrieve: `select_related` + `all_events_prefetch` + `recent_events_prefetch`

## 4.12 `rides/api/urls.py`

Router registers three resources:

- `/api/rides/`
- `/api/users/`
- `/api/ride-events/`

DRF router auto-creates list/detail route names and patterns.

## 4.13 `rides/tests.py`

Covers core behavior:

- unauthorized access blocked
- low query count for ride list (3 incl. pagination count)
- filters and distance ordering work
- distance ordering validation errors handled
- detail endpoint includes full events + today subset
- user and ride-event list/create endpoints work
- ride creation accepts assessment field names (`id_rider`, `id_driver`)

## 5. Performance Design (Why this is fast)

- Avoid N+1 user lookups with `select_related("rider", "driver")`.
- Avoid loading full event history on ride list with filtered prefetch to `todays_ride_events`.
- Distance sorting is done in SQL annotation, not Python loops.
- Stable ordering uses secondary key `id_ride`.

## 6. Setup and Run (Study Mode)

1. Create venv and activate.
2. Install dependencies:

```bash
pip install -e .
```

3. Configure `.env` (SQLite or MySQL/MariaDB).
4. Apply migrations:

```bash
python manage.py migrate
```

5. Create admin user:

```bash
python manage.py createsuperuser
```

6. Run server:

```bash
python manage.py runserver
```

7. Open docs:

- http://127.0.0.1:8000/api/docs/
- http://127.0.0.1:8000/api/schema/

## 7. How to Extend Safely

When adding features (pricing, dispatch, geofencing, driver availability), keep this rule:

- domain changes in `rides/models.py`
- query optimization in `rides/query_helpers.py`
- API contracts in `rides/api/serializers.py`
- endpoint behavior in `rides/api/views.py`
- request filtering in `rides/api/filters.py`
- route exposure in `rides/api/urls.py`
- behavior guarantees in `rides/tests.py`

This separation keeps each module focused and easier to test.

## 8. Troubleshooting Notes

- If migration fails due to MariaDB version with Django 5+, use Django 4.2 LTS or upgrade MariaDB to 10.5+.
- If Django admin crashes on Python 3.14 while using Django 4.2, the issue is runtime compatibility rather than project code. Use Python 3.11 to 3.13 for this repository, or upgrade the database server so the project can move back to a newer Django release.
- If token auth fails, POST to `/api/token-auth/` with `email` and `password`.
- If Swagger auth seems stale, hard-refresh `/api/docs/`.
- If distance ordering fails, pass both `pickup_latitude` and `pickup_longitude`.
