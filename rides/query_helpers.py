from datetime import timedelta

from django.db.models import F, FloatField, Prefetch, Value
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.utils import timezone

from rides.models import RideEvent

EARTH_RADIUS_KM = 6371.0088


def recent_events_prefetch(reference_time=None):
    cutoff = reference_time or timezone.now() - timedelta(hours=24)
    return Prefetch(
        "ride_events",
        queryset=RideEvent.objects.filter(created_at__gte=cutoff).order_by("created_at", "id_ride_event"),
        to_attr="todays_ride_events",
    )


def all_events_prefetch():
    return Prefetch(
        "ride_events",
        queryset=RideEvent.objects.all().order_by("created_at", "id_ride_event"),
        to_attr="prefetched_ride_events",
    )


def distance_annotation(latitude: float, longitude: float):
    latitude_value = Value(float(latitude))
    longitude_value = Value(float(longitude))
    latitude_radians = Radians(latitude_value)
    longitude_radians = Radians(longitude_value)
    ride_latitude = Radians(F("pickup_latitude"))
    ride_longitude = Radians(F("pickup_longitude"))

    cosine_formula = (
        Cos(latitude_radians) * Cos(ride_latitude) * Cos(ride_longitude - longitude_radians)
        + Sin(latitude_radians) * Sin(ride_latitude)
    )
    safe_cosine = Greatest(Value(-1.0), Least(Value(1.0), cosine_formula))
    return ExpressionWrapper(EARTH_RADIUS_KM * ACos(safe_cosine), output_field=FloatField())
