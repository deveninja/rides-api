from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.RoleChoices.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class RoleChoices(models.TextChoices):
        ADMIN = "admin", "Admin"
        DRIVER = "driver", "Driver"
        RIDER = "rider", "Rider"
        SUPPORT = "support", "Support"

    id_user = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=32, choices=RoleChoices.choices, default=RoleChoices.RIDER)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "user"
        ordering = ["id_user"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"


class Ride(models.Model):
    id_ride = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=32)
    rider = models.ForeignKey(User, on_delete=models.PROTECT, related_name="rides_as_rider", db_column="id_rider")
    driver = models.ForeignKey(User, on_delete=models.PROTECT, related_name="rides_as_driver", db_column="id_driver")
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        ordering = ["pickup_time", "id_ride"]
        indexes = [
            models.Index(fields=["status", "pickup_time"]),
            models.Index(fields=["pickup_time"]),
            models.Index(fields=["rider", "pickup_time"]),
            models.Index(fields=["driver", "pickup_time"]),
        ]

    def __str__(self) -> str:
        return f"Ride {self.id_ride} ({self.status})"


class RideEvent(models.Model):
    id_ride_event = models.BigAutoField(primary_key=True)
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="ride_events", db_column="id_ride")
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride_event"
        ordering = ["created_at", "id_ride_event"]
        indexes = [
            models.Index(fields=["ride", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"RideEvent {self.id_ride_event} for ride {self.ride_id}"
