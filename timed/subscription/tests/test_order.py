import pytest
from django.urls import reverse
from rest_framework import status

from timed.projects.factories import CustomerAssigneeFactory, ProjectFactory
from timed.subscription import factories


@pytest.mark.parametrize(
    "is_customer, is_accountant, is_superuser",
    [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (False, False, False),
        (False, False, False),
    ],
)
def test_order_list(auth_client, is_customer, is_accountant, is_superuser):
    """Test which user can see orders."""
    order = factories.OrderFactory.create()
    user = auth_client.user

    if is_customer:
        CustomerAssigneeFactory.create(
            customer=order.project.customer, user=user, is_customer=True
        )
    elif is_accountant:
        user.is_accountant = True
        user.save()
    elif is_superuser:
        user.is_superuser = True
        user.save()

    url = reverse("subscription-order-list")

    res = auth_client.get(url)
    assert res.status_code == status.HTTP_200_OK

    json = res.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["relationships"]["project"]["data"]["type"] == (
        "subscription-projects"
    )


@pytest.mark.parametrize(
    "is_customer, is_accountant, is_superuser, confirmed, expected",
    [
        (True, False, False, True, status.HTTP_403_FORBIDDEN),
        (True, False, False, False, status.HTTP_403_FORBIDDEN),
        (False, True, False, True, status.HTTP_403_FORBIDDEN),
        (False, True, False, False, status.HTTP_204_NO_CONTENT),
        (False, False, True, True, status.HTTP_403_FORBIDDEN),
        (False, False, True, False, status.HTTP_204_NO_CONTENT),
        (False, False, False, True, status.HTTP_403_FORBIDDEN),
        (False, False, False, False, status.HTTP_403_FORBIDDEN),
    ],
)
def test_order_delete(
    auth_client, is_customer, is_accountant, is_superuser, confirmed, expected
):
    """Test which user can delete orders, confirmed or not."""
    order = factories.OrderFactory()
    if confirmed:
        order.acknowledged = True
        order.save()

    user = auth_client.user

    if is_customer:
        CustomerAssigneeFactory.create(
            customer=order.project.customer, user=user, is_customer=True
        )
    elif is_accountant:
        user.is_accountant = True
        user.save()
    elif is_superuser:
        user.is_superuser = True
        user.save()

    url = reverse("subscription-order-detail", args=[order.id])

    res = auth_client.delete(url)
    assert res.status_code == expected


@pytest.mark.parametrize(
    "is_superuser, is_accountant, is_customer, status_code",
    [
        (True, False, False, status.HTTP_204_NO_CONTENT),
        (False, True, False, status.HTTP_204_NO_CONTENT),
        (False, False, True, status.HTTP_403_FORBIDDEN),
        (False, False, False, status.HTTP_403_FORBIDDEN),
    ],
)
def test_order_confirm(
    auth_client, is_superuser, is_accountant, is_customer, status_code
):
    """Test which user may confirm orders."""
    order = factories.OrderFactory.create()
    user = auth_client.user

    if is_superuser:
        user.is_superuser = True
        user.save()
    elif is_accountant:
        user.is_accountant = True
        user.save()
    elif is_customer:
        CustomerAssigneeFactory.create(
            user=user, is_customer=True, customer=order.project.customer
        )

    url = reverse("subscription-order-confirm", args=[order.id])

    res = auth_client.post(url)
    assert res.status_code == status_code

    if status_code == status.HTTP_204_NO_CONTENT:
        order.refresh_from_db()
        assert order.acknowledged
        assert order.confirmedby == auth_client.user


@pytest.mark.parametrize(
    "is_customer, is_accountant, is_superuser, acknowledged, expected",
    [
        (True, False, False, True, status.HTTP_400_BAD_REQUEST),
        (True, False, False, False, status.HTTP_201_CREATED),
        (False, True, False, True, status.HTTP_201_CREATED),
        (False, True, False, False, status.HTTP_201_CREATED),
        (False, False, True, True, status.HTTP_201_CREATED),
        (False, False, True, False, status.HTTP_201_CREATED),
        (False, False, False, True, status.HTTP_403_FORBIDDEN),
        (False, False, False, False, status.HTTP_403_FORBIDDEN),
    ],
)
def test_order_create(
    auth_client, is_customer, is_accountant, is_superuser, acknowledged, expected
):
    """Test which user may create orders.

    Additionally test if for creation of acknowledged/confirmed orders.
    """
    user = auth_client.user
    project = ProjectFactory.create()
    if is_customer:
        CustomerAssigneeFactory.create(
            user=user, is_customer=True, customer=project.customer
        )
    elif is_accountant:
        user.is_accountant = True
        user.save()
    elif is_superuser:
        user.is_superuser = True
        user.save()

    data = {
        "data": {
            "type": "subscription-orders",
            "id": None,
            "attributes": {
                "acknowledged": acknowledged,
                "duration": "00:30:00",
            },
            "relationships": {
                "project": {
                    "data": {"type": "subscription-projects", "id": project.id}
                },
            },
        }
    }

    url = reverse("subscription-order-list")

    response = auth_client.post(url, data)
    assert response.status_code == expected


@pytest.mark.parametrize(
    "is_customer, is_accountant, is_superuser, acknowledged, expected",
    [
        (True, False, False, True, status.HTTP_403_FORBIDDEN),
        (True, False, False, False, status.HTTP_403_FORBIDDEN),
        (False, True, False, True, status.HTTP_200_OK),
        (False, True, False, False, status.HTTP_200_OK),
        (False, False, True, True, status.HTTP_200_OK),
        (False, False, True, False, status.HTTP_200_OK),
        (False, False, False, True, status.HTTP_403_FORBIDDEN),
        (False, False, False, False, status.HTTP_403_FORBIDDEN),
    ],
)
def test_order_update(
    auth_client, is_customer, is_accountant, is_superuser, acknowledged, expected
):
    user = auth_client.user
    order = factories.OrderFactory.create()

    if acknowledged:
        order.acknowledged = True
        order.save()

    if is_customer:
        CustomerAssigneeFactory.create(
            user=user, is_customer=True, customer=order.project.customer
        )
    elif is_accountant:
        user.is_accountant = True
        user.save()
    elif is_superuser:
        user.is_superuser = True
        user.save()

    data = {
        "data": {
            "type": "subscription-orders",
            "id": order.id,
            "attributes": {
                "duration": "50:00:00",
                "acknowledged": True,
            },
        }
    }

    url = reverse("subscription-order-detail", args=[order.id])

    response = auth_client.patch(url, data)
    assert response.status_code == expected
