"""Coverage for the admin wiring: the mixins and the auto_implement registration."""

from django import test
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tabular_permissions import app_settings
from tabular_permissions.admin import (
    GroupTabularPermissionsMixin,
    TabularPermissionsGroupAdmin,
    TabularPermissionsUserAdmin,
    UserTabularPermissionsMixin,
)
from tabular_permissions.widgets import TabularPermissionsWidget

User = get_user_model()


class AutoImplementTest(test.SimpleTestCase):
    """With auto_implement on, User and Group are re-registered with the tabular admins."""

    def test_auto_implement_is_enabled_by_default(self):
        self.assertTrue(app_settings.AUTO_IMPLEMENT)

    def test_user_admin_is_the_tabular_one(self):
        self.assertIsInstance(admin.site._registry[User], TabularPermissionsUserAdmin)

    def test_group_admin_is_the_tabular_one(self):
        self.assertIsInstance(admin.site._registry[Group], TabularPermissionsGroupAdmin)

    def test_user_admin_keeps_the_mixin_in_front(self):
        # The mixin has to win over the base ModelAdmin for formfield_for_manytomany.
        mro = TabularPermissionsUserAdmin.__mro__
        self.assertLess(mro.index(UserTabularPermissionsMixin), mro.index(admin.ModelAdmin))

    def test_group_admin_keeps_the_mixin_in_front(self):
        mro = TabularPermissionsGroupAdmin.__mro__
        self.assertLess(mro.index(GroupTabularPermissionsMixin), mro.index(admin.ModelAdmin))


class UserAdminFormFieldTest(test.TestCase):

    def setUp(self):
        self.model_admin = admin.site._registry[User]

    def get_field(self, name):
        db_field = User._meta.get_field(name)
        return self.model_admin.formfield_for_manytomany(db_field, request=None)

    def test_user_permissions_gets_the_tabular_widget(self):
        self.assertIsInstance(self.get_field('user_permissions').widget,
                              TabularPermissionsWidget)

    def test_user_permissions_widget_targets_the_right_input(self):
        self.assertEqual(self.get_field('user_permissions').widget.input_name,
                         'user_permissions')

    def test_help_text_is_cleared_for_the_tabular_widget(self):
        # The default help text describes the ctrl-click select, which no longer applies.
        self.assertEqual(self.get_field('user_permissions').help_text, '')

    def test_groups_field_keeps_its_own_widget(self):
        self.assertNotIsInstance(self.get_field('groups').widget, TabularPermissionsWidget)

    def test_groups_field_keeps_its_help_text(self):
        self.assertNotEqual(self.get_field('groups').help_text, '')


class GroupAdminFormFieldTest(test.TestCase):

    def setUp(self):
        self.model_admin = admin.site._registry[Group]

    def get_field(self, name):
        return self.model_admin.formfield_for_manytomany(Group._meta.get_field(name),
                                                         request=None)

    def test_permissions_gets_the_tabular_widget(self):
        self.assertIsInstance(self.get_field('permissions').widget, TabularPermissionsWidget)

    def test_permissions_widget_targets_the_permissions_input(self):
        self.assertEqual(self.get_field('permissions').widget.input_name, 'permissions')

    def test_help_text_is_cleared_for_the_tabular_widget(self):
        self.assertEqual(self.get_field('permissions').help_text, '')
