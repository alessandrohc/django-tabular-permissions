from django.db import models


class ModelWithCustomPermissions(models.Model):
    """Fixture for the "other permissions" column, fed by Meta.permissions."""

    name = models.TextField()

    class Meta:
        permissions = [
            ("can_do_something", "Can do something"),
        ]


class ModelWithExtraDefaultPermissions(models.Model):
    """
    Fixture for a default_permissions action outside the four that get their own column.

    "publish" is not view/add/change/delete, so it has to surface in the other-permissions
    column. Without that it silently falls through to the leftover widget.
    """

    name = models.TextField()

    class Meta:
        default_permissions = ('add', 'change', 'delete', 'view', 'publish')


class ModelWithoutPermissions(models.Model):
    """
    Fixture for a model that produces no permission at all.

    With neither default_permissions nor Meta.permissions there is nothing to show, so the
    model must be left out of the table entirely.
    """

    name = models.TextField()

    class Meta:
        default_permissions = ()


class ModelWithPartialDefaultPermissions(models.Model):
    """
    Fixture for a model declaring only part of the default permissions.

    Exercises that default_permissions is respected: the add and delete columns must stay
    empty even when a matching auth_permission row exists.
    """

    name = models.TextField()

    class Meta:
        default_permissions = ('view', 'change')
