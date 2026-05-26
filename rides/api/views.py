from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import CharField, Serializer

from rides.api.filters import RideFilter, RideOrderingFilter
from rides.api.serializers import (
    RideDetailSerializer,
    RideEventReadSerializer,
    RideEventWriteSerializer,
    RideListSerializer,
    RideWriteSerializer,
    UserReadSerializer,
    UserWriteSerializer,
)
from rides.models import Ride, RideEvent, User
from rides.permissions import IsAdminRole
from rides.query_helpers import all_events_prefetch, recent_events_prefetch


class EmailAuthTokenSerializer(Serializer):
    email = CharField()
    password = CharField(style={"input_type": "password"}, write_only=True)


class EmailAuthTokenResponseSerializer(Serializer):
    token = CharField()


class EmailAuthTokenView(ObtainAuthToken):
    serializer_class = EmailAuthTokenSerializer

    @extend_schema(request=EmailAuthTokenSerializer, responses=EmailAuthTokenResponseSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"non_field_errors": ["Unable to log in with provided credentials."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class AdminOnlyModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]


class UserViewSet(AdminOnlyModelViewSet):
    queryset = User.objects.all().order_by("id_user")

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserReadSerializer
        return UserWriteSerializer


class RideEventViewSet(AdminOnlyModelViewSet):
    queryset = RideEvent.objects.select_related("ride").all().order_by("created_at", "id_ride_event")

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return RideEventReadSerializer
        return RideEventWriteSerializer


class RideViewSet(AdminOnlyModelViewSet):
    queryset = Ride.objects.all()
    filter_backends = [DjangoFilterBackend, RideOrderingFilter]
    filterset_class = RideFilter

    def get_serializer_class(self):
        if self.action == "list":
            return RideListSerializer
        if self.action == "retrieve":
            return RideDetailSerializer
        return RideWriteSerializer

    def get_queryset(self):
        queryset = Ride.objects.select_related("rider", "driver")
        if self.action == "list":
            return queryset.prefetch_related(recent_events_prefetch())
        if self.action == "retrieve":
            return queryset.prefetch_related(all_events_prefetch(), recent_events_prefetch())
        return queryset
