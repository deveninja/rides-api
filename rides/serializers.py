from rides.api.serializers import (
    RideDetailSerializer,
    RideEventReadSerializer,
    RideEventWriteSerializer,
    RideListSerializer,
    RideWriteSerializer,
    UserReadSerializer,
    UserWriteSerializer,
)

UserSerializer = UserReadSerializer
RideEventSerializer = RideEventReadSerializer

__all__ = [
    "RideDetailSerializer",
    "RideEventReadSerializer",
    "RideEventSerializer",
    "RideEventWriteSerializer",
    "RideListSerializer",
    "RideWriteSerializer",
    "UserReadSerializer",
    "UserSerializer",
    "UserWriteSerializer",
]
