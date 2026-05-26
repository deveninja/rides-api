from rest_framework import serializers

from rides.models import Ride, RideEvent, User


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id_user",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
        ]


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id_user",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
        ]
        read_only_fields = ["id_user"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RideEventReadSerializer(serializers.ModelSerializer):
    id_ride = serializers.IntegerField(source="ride_id", read_only=True)

    class Meta:
        model = RideEvent
        fields = ["id_ride_event", "id_ride", "description", "created_at"]


class RideEventWriteSerializer(serializers.ModelSerializer):
    id_ride = serializers.PrimaryKeyRelatedField(source="ride", queryset=Ride.objects.all())

    class Meta:
        model = RideEvent
        fields = ["id_ride_event", "id_ride", "description", "created_at"]
        read_only_fields = ["id_ride_event"]


class RideReadBaseSerializer(serializers.ModelSerializer):
    id_rider = serializers.IntegerField(source="rider_id", read_only=True)
    id_driver = serializers.IntegerField(source="driver_id", read_only=True)
    rider = UserReadSerializer(read_only=True)
    driver = UserReadSerializer(read_only=True)
    ride_events = RideEventReadSerializer(many=True, read_only=True, source="todays_ride_events")
    todays_ride_events = RideEventReadSerializer(many=True, read_only=True)

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "rider",
            "driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
            "ride_events",
            "todays_ride_events",
        ]


class RideListSerializer(RideReadBaseSerializer):
    class Meta(RideReadBaseSerializer.Meta):
        fields = RideReadBaseSerializer.Meta.fields


class RideDetailSerializer(RideReadBaseSerializer):
    ride_events = serializers.SerializerMethodField()

    class Meta(RideReadBaseSerializer.Meta):
        fields = RideReadBaseSerializer.Meta.fields

    def get_ride_events(self, obj):
        prefetched = getattr(obj, "prefetched_ride_events", obj.ride_events.all())
        return RideEventReadSerializer(prefetched, many=True).data


class RideWriteSerializer(serializers.ModelSerializer):
    id_rider = serializers.PrimaryKeyRelatedField(source="rider", queryset=User.objects.all())
    id_driver = serializers.PrimaryKeyRelatedField(source="driver", queryset=User.objects.all())

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        ]
        read_only_fields = ["id_ride"]

    def validate(self, attrs):
        rider = attrs.get("rider") or getattr(self.instance, "rider", None)
        driver = attrs.get("driver") or getattr(self.instance, "driver", None)
        if rider and driver and rider.pk == driver.pk:
            raise serializers.ValidationError("Rider and driver must be different users.")
        return attrs
