from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from rides.models import Ride, RideEvent, User


class RideApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="strong-password",
            first_name="Admin",
            last_name="User",
            role=User.RoleChoices.ADMIN,
            is_staff=True,
        )
        self.rider = User.objects.create_user(
            email="rider@example.com",
            password="strong-password",
            first_name="Rider",
            last_name="User",
            role=User.RoleChoices.RIDER,
        )
        self.driver = User.objects.create_user(
            email="driver@example.com",
            password="strong-password",
            first_name="Driver",
            last_name="User",
            role=User.RoleChoices.DRIVER,
        )
        self.other_rider = User.objects.create_user(
            email="other@example.com",
            password="strong-password",
            first_name="Other",
            last_name="Rider",
            role=User.RoleChoices.RIDER,
        )

        now = timezone.now()
        self.ride_one = Ride.objects.create(
            status="pickup",
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7306,
            dropoff_longitude=-73.9352,
            pickup_time=now - timedelta(hours=2),
        )
        self.ride_two = Ride.objects.create(
            status="en-route",
            rider=self.other_rider,
            driver=self.driver,
            pickup_latitude=40.7306,
            pickup_longitude=-73.9352,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
            pickup_time=now - timedelta(hours=1),
        )

        RideEvent.objects.create(
            ride=self.ride_one,
            description="Status changed to pickup",
            created_at=now - timedelta(hours=3),
        )
        RideEvent.objects.create(
            ride=self.ride_one,
            description="Status changed to dropoff",
            created_at=now - timedelta(hours=2, minutes=30),
        )
        RideEvent.objects.create(
            ride=self.ride_one,
            description="Driver assigned",
            created_at=now - timedelta(hours=30),
        )
        RideEvent.objects.create(
            ride=self.ride_two,
            description="Status changed to pickup",
            created_at=now - timedelta(hours=25),
        )
        RideEvent.objects.create(
            ride=self.ride_two,
            description="Status changed to dropoff",
            created_at=now - timedelta(hours=1, minutes=15),
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.admin_user)

    def test_list_is_admin_only(self):
        response = self.client.get(reverse("ride-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_filters_and_paginates_with_low_query_count(self):
        self.authenticate()
        url = reverse("ride-list")
        with self.assertNumQueries(3):
            response = self.client.get(url, {"status": "pickup", "rider_email": self.rider.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        payload = response.data["results"][0]
        self.assertEqual(payload["driver"]["email"], self.driver.email)
        self.assertEqual(payload["rider"]["email"], self.rider.email)
        self.assertEqual(len(payload["ride_events"]), 2)
        self.assertEqual(len(payload["todays_ride_events"]), 2)
        self.assertTrue(all(event["created_at"] for event in payload["todays_ride_events"]))

    def test_list_orders_by_distance(self):
        self.authenticate()
        response = self.client.get(
            reverse("ride-list"),
            {
                "ordering": "distance",
                "pickup_latitude": 40.7128,
                "pickup_longitude": -74.0060,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id_ride"], self.ride_one.id_ride)

    def test_distance_order_requires_coordinates(self):
        self.authenticate()
        response = self.client.get(reverse("ride-list"), {"ordering": "distance"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_returns_full_events(self):
        self.authenticate()
        response = self.client.get(reverse("ride-detail", args=[self.ride_one.id_ride]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["ride_events"]), 3)
        self.assertEqual(len(response.data["todays_ride_events"]), 2)

    def test_admin_can_list_users_and_ride_events(self):
        self.authenticate()

        user_response = self.client.get(reverse("user-list"))
        ride_event_response = self.client.get(reverse("ride-event-list"))

        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ride_event_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(user_response.data["results"]), 4)
        self.assertGreaterEqual(len(ride_event_response.data["results"]), 5)

    def test_admin_can_create_ride_with_pdf_field_names(self):
        self.authenticate()
        payload = {
            "status": "dropoff",
            "id_rider": self.rider.id_user,
            "id_driver": self.driver.id_user,
            "pickup_latitude": 34.0522,
            "pickup_longitude": -118.2437,
            "dropoff_latitude": 34.0622,
            "dropoff_longitude": -118.2537,
            "pickup_time": timezone.now().isoformat(),
        }

        response = self.client.post(reverse("ride-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ride.objects.count(), 3)
        self.assertEqual(Ride.objects.latest("id_ride").rider_id, self.rider.id_user)

    def test_admin_can_create_user_and_ride_event(self):
        self.authenticate()

        user_response = self.client.post(
            reverse("user-list"),
            {
                "role": User.RoleChoices.DRIVER,
                "first_name": "New",
                "last_name": "Driver",
                "email": "new-driver@example.com",
                "phone_number": "5550100",
                "password": "strong-password",
            },
            format="json",
        )
        self.assertEqual(user_response.status_code, status.HTTP_201_CREATED)

        ride_event_response = self.client.post(
            reverse("ride-event-list"),
            {
                "id_ride": self.ride_one.id_ride,
                "description": "Passenger notified",
                "created_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(ride_event_response.status_code, status.HTTP_201_CREATED)
