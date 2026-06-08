from __future__ import annotations

from itertools import count
import random
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from rides.models import Ride, RideEvent, User


FIRST_NAMES = [
    "Ava",
    "Noah",
    "Liam",
    "Emma",
    "Olivia",
    "Mason",
    "Sophia",
    "Isabella",
    "Lucas",
    "Mia",
    "Ethan",
    "Amelia",
    "Harper",
    "James",
    "Evelyn",
    "Benjamin",
    "Aria",
    "Elijah",
    "Charlotte",
    "Henry",
]

LAST_NAMES = [
    "Johnson",
    "Williams",
    "Brown",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Anderson",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
]

RIDE_STATUSES = ["en-route", "pickup", "dropoff"]
RIDE_EVENT_NOTES = [
    "Driver assigned",
    "Driver en route",
    "Passenger notified",
    "Traffic delay reported",
    "Rider confirmed",
    "Navigation updated",
]

CITY_CENTERS = [
    (40.7128, -74.0060),
    (34.0522, -118.2437),
    (37.7749, -122.4194),
    (41.8781, -87.6298),
    (47.6062, -122.3321),
]


@dataclass(frozen=True)
class SeedCounts:
    admins: int
    drivers: int
    riders: int
    supports: int
    rides: int


class Command(BaseCommand):
    help = "Seed realistic demo data for users, rides, and ride events."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--admins", type=int, default=1)
        parser.add_argument("--drivers", type=int, default=25)
        parser.add_argument("--riders", type=int, default=120)
        parser.add_argument("--supports", type=int, default=4)
        parser.add_argument("--rides", type=int, default=600)
        parser.add_argument("--password", type=str, default="seed-password")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing ride, ride event, and non-superuser user records before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(options["seed"])
        counts = SeedCounts(
            admins=max(1, options["admins"]),
            drivers=max(10, options["drivers"]),
            riders=max(20, options["riders"]),
            supports=max(1, options["supports"]),
            rides=max(10, options["rides"]),
        )
        password = options["password"]

        with transaction.atomic():
            if options["reset"]:
                self._reset_data()

            self.stdout.write("Starting admin creation")
            admins = self._ensure_admin_users(counts.admins, password)
            self.stdout.write("Starting driver creation")
            drivers = self._create_users(counts.drivers, User.RoleChoices.DRIVER, "driver", password)
            self.stdout.write("Starting rider creation")
            riders = self._create_users(counts.riders, User.RoleChoices.RIDER, "rider", password)
            self.stdout.write("Starting ride creation")
            self._create_users(counts.supports, User.RoleChoices.SUPPORT, "support", password)


            drivers = list(
                User.objects.filter(role=User.RoleChoices.DRIVER)
            )

            riders = list(
                User.objects.filter(role=User.RoleChoices.RIDER)
            )

            rides = self._create_rides(counts.rides, riders, drivers)
            events = self._create_ride_events(rides)
            RideEvent.objects.bulk_create(events, batch_size=1000)

        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))
        self.stdout.write(
            f"Admins: {len(admins)} | Drivers: {len(drivers)} | Riders: {len(riders)} | Rides: {len(rides)} | Events: {len(events)}"
        )
        self.stdout.write(f"Default seeded password: {password}")

    def _reset_data(self) -> None:
        RideEvent.objects.all().delete()
        Ride.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _ensure_admin_users(self, count: int, password: str) -> list[User]:
        admins = []
        for index in range(count):
            self.stdout.write("Before make_password")
            email = f"admin{index + 1}@seed.local"
            defaults = {
                "first_name": "Admin",
                "last_name": str(index + 1),
                "role": User.RoleChoices.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "phone_number": self._phone_number(),
                "password": make_password(password),
            }
            self.stdout.write("Before update_or_create")
            admin, created = User.objects.update_or_create(email=email, defaults=defaults)
            self.stdout.write("After update_or_create")
            if created:
                self.stdout.write(f"Created admin user {email}")
            admins.append(admin)
        return admins

    def _create_users(self, count: int, role: str, prefix: str, password: str) -> list[User]:
        if count == 0:
            return []

        users = []
        existing_emails = set(User.objects.values_list("email", flat=True))
        next_id = 1
        hashed_password = make_password(password)
        while len(users) < count:
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = f"{prefix}{next_id}.{first_name.lower()}.{last_name.lower()}@seed.local"
            next_id += 1
            if email in existing_emails:
                continue

            users.append(
                User(
                    email=email,
                    role=role,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=self._phone_number(),
                    is_active=True,
                    is_staff=(role == User.RoleChoices.ADMIN),
                    password=hashed_password,
                )
            )
            existing_emails.add(email)

        created = User.objects.bulk_create(users, batch_size=1000)
        return created

    def _create_rides(self, count: int, riders: list[User], drivers: list[User]) -> list[Ride]:
        now = timezone.now()
        rides = []
        for _ in range(count):
            rider = random.choice(riders)
            driver = random.choice(drivers)
            while driver.id_user == rider.id_user:
                driver = random.choice(drivers)

            pickup_lat, pickup_lon = self._coordinate_near_city()
            dropoff_lat, dropoff_lon = self._coordinate_near_city(base_lat=pickup_lat, base_lon=pickup_lon)
            pickup_time = now - timedelta(minutes=random.randint(5, 60 * 24 * 14))

            rides.append(
                Ride(
                    status=random.choice(RIDE_STATUSES),
                    rider=rider,
                    driver=driver,
                    pickup_latitude=pickup_lat,
                    pickup_longitude=pickup_lon,
                    dropoff_latitude=dropoff_lat,
                    dropoff_longitude=dropoff_lon,
                    pickup_time=pickup_time,
                )
            )

        Ride.objects.bulk_create(rides, batch_size=1000)
        return list(
            Ride.objects.order_by("-id_ride")[:count]
    )

    def _create_ride_events(self, rides: list[Ride]) -> list[RideEvent]:
        events: list[RideEvent] = []
        for ride in rides:
            pickup_marker = ride.pickup_time + timedelta(minutes=random.randint(0, 20))
            dropoff_marker = pickup_marker + timedelta(minutes=random.randint(10, 140))

            event_times = [
                ride.pickup_time - timedelta(minutes=random.randint(3, 20)),
                ride.pickup_time - timedelta(minutes=random.randint(1, 10)),
            ]
            event_descriptions = [
                random.choice(RIDE_EVENT_NOTES),
                "Status changed to pickup",
            ]

            if random.random() < 0.85:
                event_times.append(pickup_marker)
                event_descriptions.append(random.choice(RIDE_EVENT_NOTES))

            event_times.append(dropoff_marker)
            event_descriptions.append("Status changed to dropoff")

            if random.random() < 0.4:
                event_times.append(dropoff_marker + timedelta(minutes=random.randint(1, 12)))
                event_descriptions.append(random.choice(RIDE_EVENT_NOTES))

            zipped = sorted(zip(event_times, event_descriptions), key=lambda x: x[0])
            for created_at, description in zipped:
                events.append(
                    RideEvent(
                        ride=ride,
                        description=description,
                        created_at=created_at,
                    )
                )

        return events

    def _coordinate_near_city(self, base_lat: float | None = None, base_lon: float | None = None) -> tuple[float, float]:
        if base_lat is None or base_lon is None:
            base_lat, base_lon = random.choice(CITY_CENTERS)
        return (
            round(base_lat + random.uniform(-0.08, 0.08), 6),
            round(base_lon + random.uniform(-0.08, 0.08), 6),
        )

    def _phone_number(self) -> str:
        return f"+1{random.randint(2000000000, 9999999999)}"
