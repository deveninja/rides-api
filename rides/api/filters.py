from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from rides.models import Ride
from rides.query_helpers import distance_annotation


class RideFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    rider_email = filters.CharFilter(field_name="rider__email", lookup_expr="iexact")

    class Meta:
        model = Ride
        fields = ["status", "rider_email"]


class RideOrderingFilter(BaseFilterBackend):
    allowed_orderings = {"pickup_time", "-pickup_time", "distance", "-distance"}

    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get("ordering") or "pickup_time"
        if ordering not in self.allowed_orderings:
            return queryset

        if ordering.lstrip("-") == "distance":
            latitude = request.query_params.get("pickup_latitude")
            longitude = request.query_params.get("pickup_longitude")
            if latitude is None or longitude is None:
                raise ValidationError(
                    {
                        "ordering": "pickup_latitude and pickup_longitude are required when ordering by distance."
                    }
                )
            queryset = queryset.annotate(distance_km=distance_annotation(latitude, longitude))
            distance_order = "-distance_km" if ordering.startswith("-") else "distance_km"
            return queryset.order_by(distance_order, "id_ride")

        return queryset.order_by(ordering, "id_ride")
