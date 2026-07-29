"""
Rendering coverage for the User and Group admin screens.

This module replaces the Selenium suite that used to live here, commented out. Those tests
drove a real browser to assert the behaviour of the select-all checkboxes and of the submit
handler that copies the table state into the plain widget. That behaviour lives in
tabular_permissions.js and cannot be reached without a browser, so what is covered here is
everything the server is responsible for: that the table renders, that the checkboxes carry
the ids and the data attributes the script keys off, and that the assigned permissions come
back checked. The click behaviour itself stays uncovered, and is called out in the README.
"""

from django import test
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from pyquery import PyQuery as pq

from custom_models.models import ModelWithCustomPermissions

from .helpers import permission_id

User = get_user_model()


class AdminRenderTestCase(test.TestCase):
    """Shared login for the admin screens that host the widget."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username='super', password='secret',
                                                 email='super@example.com')

    def setUp(self):
        self.client.force_login(self.user)

    def get_doc(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return pq(response.content)

    def user_change_doc(self):
        return self.get_doc(reverse('admin:auth_user_change', args=(self.user.pk,)))

    def group_add_doc(self):
        return self.get_doc(reverse('admin:auth_group_add'))


class TableRenderTest(AdminRenderTestCase):

    def test_table_renders_on_the_user_change_form(self):
        self.assertEqual(len(self.user_change_doc().find('#tabular_permissions')), 1)

    def test_table_renders_on_the_group_add_form(self):
        self.assertEqual(len(self.group_add_doc().find('#tabular_permissions')), 1)

    def test_user_form_announces_the_user_permissions_input(self):
        doc = self.user_change_doc()
        self.assertEqual(doc.find('#tabular_permissions').attr('data-input-name'),
                         'user_permissions')

    def test_group_form_announces_the_permissions_input(self):
        doc = self.group_add_doc()
        self.assertEqual(doc.find('#tabular_permissions').attr('data-input-name'),
                         'permissions')

    def test_original_multiple_select_is_rendered_alongside_the_table(self):
        # The table posts through the plain widget, so it has to be in the DOM.
        self.assertEqual(len(self.user_change_doc().find('[name=user_permissions]')), 1)

    def test_javascript_asset_is_loaded_on_the_form(self):
        response = self.client.get(reverse('admin:auth_user_change', args=(self.user.pk,)))
        self.assertContains(response, 'tabular_permissions/tabular_permissions.js')


class CheckboxContractTest(AdminRenderTestCase):
    """The script keys off these ids, classes and data attributes."""

    def test_permission_checkbox_carries_its_permission_id(self):
        doc = self.user_change_doc()
        expected = permission_id(ModelWithCustomPermissions, 'view')
        box = doc.find('#id_custom_models_modelwithcustompermissions'
                       '_view_modelwithcustompermissions')
        self.assertEqual(box.attr('data-perm-id'), str(expected))

    def test_checkbox_ids_are_app_qualified(self):
        doc = self.user_change_doc()
        self.assertEqual(len(doc.find('#id_auth_user_add_user')), 1)

    def test_no_checkbox_id_collapses_to_an_empty_label(self):
        # Before the model label reached the context every id looked like "id__add_user",
        # which produced duplicates across apps.
        doc = self.user_change_doc()
        collapsed = [box.get('id') for box in doc.find('input[type=checkbox]')
                     if (box.get('id') or '').startswith('id__')]
        self.assertEqual(collapsed, [], msg=f'ids with an empty model label: {collapsed}')

    def test_checkbox_ids_are_unique_across_the_document(self):
        doc = self.user_change_doc()
        ids = [box.get('id') for box in doc.find('input[type=checkbox]') if box.get('id')]
        duplicated = {value for value in ids if ids.count(value) > 1}
        self.assertEqual(duplicated, set(), msg=f'duplicated DOM ids: {duplicated}')

    def test_row_select_all_names_the_model_it_drives(self):
        doc = self.user_change_doc()
        names = {box.get('data-model-name') for box in doc.find('.select-all.select-row')}
        self.assertIn('modelwithcustompermissions', names)

    def test_column_select_all_names_the_permission_it_drives(self):
        doc = self.user_change_doc()
        permissions = {box.get('data-permission') for box in doc.find('.select-all.select-column')}
        self.assertEqual({'view', 'add', 'change', 'delete'}, permissions)

    def test_permission_checkbox_is_tagged_with_its_model(self):
        doc = self.user_change_doc()
        self.assertTrue(len(doc.find('input.model-modelwithcustompermissions')) > 0)


class AssignedPermissionsTest(AdminRenderTestCase):

    def test_assigned_permission_renders_checked(self):
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='view_modelwithcustompermissions')
        self.user.user_permissions.add(perm)
        doc = self.user_change_doc()
        box = doc.find(f'input[data-perm-id="{perm.pk}"]')
        self.assertEqual(box.attr('checked'), 'checked')

    def test_unassigned_permission_renders_unchecked(self):
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='delete_modelwithcustompermissions')
        doc = self.user_change_doc()
        box = doc.find(f'input[data-perm-id="{perm.pk}"]')
        self.assertIsNone(box.attr('checked'))

    def test_group_permissions_render_checked_on_the_group_form(self):
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='change_modelwithcustompermissions')
        group = Group.objects.create(name='editors')
        group.permissions.add(perm)
        doc = self.get_doc(reverse('admin:auth_group_change', args=(group.pk,)))
        self.assertEqual(doc.find(f'input[data-perm-id="{perm.pk}"]').attr('checked'),
                         'checked')


class CustomPermissionColumnTest(AdminRenderTestCase):

    def test_custom_permission_renders_with_an_app_qualified_id(self):
        doc = self.user_change_doc()
        selector = '#id_custom_models_modelwithcustompermissions_can_do_something'
        self.assertEqual(len(doc.find(selector)), 1)

    def test_extra_default_permission_renders_in_the_custom_column(self):
        doc = self.user_change_doc()
        selector = ('#id_custom_models_modelwithextradefaultpermissions_'
                    'publish_modelwithextradefaultpermissions')
        self.assertEqual(len(doc.find(selector)), 1)

    def test_other_permissions_header_is_present(self):
        doc = self.user_change_doc()
        headers = [th.text_content().strip().lower() for th in doc.find('th.tabular_perms_header')]
        self.assertTrue(any('other permissions' in header for header in headers))


class LeftoverPermissionsTest(AdminRenderTestCase):

    def test_orphan_permission_is_listed_in_the_plain_widget(self):
        orphan = Permission.objects.create(
            codename='handmade_permission', name='handmade',
            content_type=ContentType.objects.get_for_model(Permission))
        doc = self.user_change_doc()
        options = [option.get('value')
                   for option in doc.find('[name=user_permissions] option')]
        self.assertIn(str(orphan.pk), options)

    def test_permission_owned_by_the_table_is_not_listed_in_the_plain_widget(self):
        managed = permission_id(ModelWithCustomPermissions, 'view')
        doc = self.user_change_doc()
        options = [option.get('value')
                   for option in doc.find('[name=user_permissions] option')]
        self.assertNotIn(str(managed), options)


class SaveThroughAdminTest(AdminRenderTestCase):
    """
    The table posts through the plain widget, so a POST carrying permission ids has to persist
    them. This is the server side half of what the commented Selenium test used to assert.
    """

    def test_posted_permissions_are_persisted_on_the_group(self):
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='add_modelwithcustompermissions')
        response = self.client.post(reverse('admin:auth_group_add'),
                                    {'name': 'editors', 'permissions': [perm.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Group.objects.get(name='editors').permissions.all()), [perm])

    def test_posting_no_permission_clears_the_group(self):
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='add_modelwithcustompermissions')
        group = Group.objects.create(name='editors')
        group.permissions.add(perm)
        response = self.client.post(reverse('admin:auth_group_change', args=(group.pk,)),
                                    {'name': 'editors', 'permissions': []})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(group.permissions.all()), [])

    def test_permission_managed_by_the_table_is_accepted_on_post(self):
        # The widget narrows its own choices to the leftovers, but the form field validates
        # against the full queryset, so a table managed id must still be accepted.
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(ModelWithCustomPermissions),
            codename='can_do_something')
        response = self.client.post(reverse('admin:auth_group_add'),
                                    {'name': 'publishers', 'permissions': [perm.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertIn(perm, Group.objects.get(name='publishers').permissions.all())
