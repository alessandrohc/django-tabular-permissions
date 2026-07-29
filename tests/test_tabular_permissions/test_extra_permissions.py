"""
Coverage for the extension points a consumer subclass depends on.

The downstream consumer of this package subclasses the widget, overrides
get_extra_permissions(), swaps base_template_name for its own widget template and points
template_name at a wrapper that reaches the packaged table through an include. That coupling
is reproduced by ExtraPermissionsWidget without pulling in the third party transfer widget,
which is not installable outside its own project. Every assertion here is about public API:
break one and the consumer's permission screen breaks with it.
"""

from django import test
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from pyquery import PyQuery as pq

from custom_models.models import ModelWithCustomPermissions
from tabular_permissions.app_settings import EXTRA_PERMISSIONS
from tabular_permissions.helpers import get_perm_name
from tabular_permissions.widgets import TabularPermissionsWidget

from .helpers import ExtraPermissionsWidget, build_widget

EXTRA = {'see_menu': 'See menu'}


def create_extra_permissions(action='see_menu'):
    """Create the permission rows a consumer declares outside Meta.permissions."""
    created = {}
    for model in (ModelWithCustomPermissions,):
        ct = ContentType.objects.get_for_model(model)
        codename = get_perm_name(model._meta.model_name, action)
        created[model] = Permission.objects.create(codename=codename, name=f'Can {action}',
                                                   content_type=ct)
    return created


class HookDefaultTest(test.TestCase):
    """The packaged widget ships the hook as a no-op."""

    def test_base_widget_returns_no_extra_permissions(self):
        widget = TabularPermissionsWidget()
        self.assertEqual(
            widget.get_extra_permissions(ModelWithCustomPermissions, 1, {}), ())

    def test_model_entry_still_carries_the_extra_permissions_key(self):
        # The template iterates it unconditionally, so the key has to exist even when empty.
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        self.assertEqual(list(entry['extra_permissions']), [])

    def test_extra_permissions_setting_is_exported(self):
        # The consumer imports this name directly from app_settings.
        self.assertIsInstance(EXTRA_PERMISSIONS, dict)


class HookOverrideTest(test.TestCase):

    def setUp(self):
        self.created = create_extra_permissions()
        self.widget = build_widget(ExtraPermissionsWidget, extra_permissions=EXTRA)
        self.ctx = self.widget.get_table_context('user_permissions', [], {})
        self.entry = self.ctx['apps_available']['custom_models']['models'][
            'modelwithcustompermissions']

    def test_hook_output_reaches_the_model_entry(self):
        codenames = [perm['codename'] for perm in self.entry['extra_permissions']]
        self.assertIn('see_menu_modelwithcustompermissions', codenames)

    def test_hook_receives_the_codename_id_map(self):
        # The consumer resolves its own permission ids out of the map it is handed.
        expected = self.created[ModelWithCustomPermissions].pk
        found = {perm['codename']: perm['c_perm_id']
                 for perm in self.entry['extra_permissions']}
        self.assertEqual(found['see_menu_modelwithcustompermissions'], expected)

    def test_hook_receives_the_content_type_id(self):
        seen = {}
        widget = build_widget(ExtraPermissionsWidget, extra_permissions=EXTRA)
        original = widget.get_extra_permissions

        def spy(model, ct_id, codename_id_map):
            seen[model] = ct_id
            return original(model, ct_id, codename_id_map)

        widget.get_extra_permissions = spy
        widget.get_table_context('user_permissions', [], {})
        self.assertEqual(seen[ModelWithCustomPermissions],
                         ContentType.objects.get_for_model(ModelWithCustomPermissions).pk)

    def test_missing_permission_row_yields_a_false_id(self):
        # A declared extra permission with no row in the database renders as an empty cell
        # rather than blowing up.
        self.created[ModelWithCustomPermissions].delete()
        ctx = build_widget(ExtraPermissionsWidget,
                           extra_permissions=EXTRA).get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        found = {perm['codename']: perm['c_perm_id'] for perm in entry['extra_permissions']}
        self.assertFalse(found['see_menu_modelwithcustompermissions'])

    def test_extra_permission_is_not_offered_as_a_leftover(self):
        # It has a cell in the table, so it must not also show up in the plain widget.
        extra_id = self.created[ModelWithCustomPermissions].pk
        self.assertNotIn(extra_id, [pk for pk, _label in self.ctx['reminder_choices']])

    def test_extra_permission_counts_as_managed(self):
        self.assertIn(self.created[ModelWithCustomPermissions].pk, self.widget.managed_perms)

    def test_extra_permission_alone_is_enough_to_render_a_row(self):
        # A model with no default permission and no Meta.permissions still earns a row when
        # the hook contributes something for it.
        ct = ContentType.objects.get_for_model(ModelWithCustomPermissions)
        Permission.objects.filter(content_type=ct).exclude(
            codename='see_menu_modelwithcustompermissions').delete()
        ctx = build_widget(ExtraPermissionsWidget,
                           extra_permissions=EXTRA).get_table_context('user_permissions', [], {})
        self.assertIn('modelwithcustompermissions',
                      ctx['apps_available']['custom_models']['models'])


class ConsumerTemplateChainTest(test.TestCase):
    """wrapper template -> include -> extends widget.table.template_name."""

    def setUp(self):
        self.created = create_extra_permissions()
        self.widget = build_widget(ExtraPermissionsWidget, extra_permissions=EXTRA)
        self.html = self.widget.render('user_permissions', [], {'id': 'id_user_permissions'})
        self.doc = pq(self.html)

    def test_wrapper_template_is_used(self):
        self.assertEqual(len(self.doc.find('#wrapper-marker')), 1)

    def test_packaged_table_is_reached_through_the_context_key(self):
        # This is the whole point of exposing template_name in the context.
        self.assertEqual(len(self.doc.find('#tabular_permissions')), 1)

    def test_extra_permission_header_block_is_filled(self):
        headers = [th.get('data-permission')
                   for th in self.doc.find('th.extra-permission-header')]
        self.assertEqual(headers, ['see_menu'])

    def test_extra_permission_row_block_is_filled(self):
        cell = self.doc.find('td.extra-permission-cell.see_menu')
        self.assertTrue(len(cell) > 0)

    def test_extra_permission_checkbox_carries_the_permission_id(self):
        expected = self.created[ModelWithCustomPermissions].pk
        box = self.doc.find(f'input.extra[data-perm-id="{expected}"]')
        self.assertEqual(len(box), 1)

    def test_extra_permission_checkbox_id_is_app_qualified(self):
        selector = '#id_custom_models_modelwithcustompermissions_see_menu_modelwithcustompermissions'
        self.assertEqual(len(self.doc.find(selector)), 1)

    def test_assigned_extra_permission_renders_checked(self):
        perm = self.created[ModelWithCustomPermissions]
        widget = build_widget(ExtraPermissionsWidget, extra_permissions=EXTRA)
        doc = pq(widget.render('user_permissions', [perm.pk], {'id': 'id_user_permissions'}))
        self.assertEqual(doc.find(f'input.extra[data-perm-id="{perm.pk}"]').attr('checked'),
                         'checked')

    def test_base_template_name_override_is_honoured(self):
        # The consumer replaces the plain select with its own widget template.
        self.assertEqual(len(self.doc.find('#base-template-marker')), 1)

    def test_default_select_template_is_not_rendered_when_overridden(self):
        self.assertEqual(len(self.doc.find('select[name=user_permissions]')), 0)


class PackagedBaseTemplateTest(test.TestCase):
    """Without an override the packaged table renders the plain select."""

    def test_default_base_template_renders_a_select(self):
        widget = build_widget()
        doc = pq(widget.render('user_permissions', [], {'id': 'id_user_permissions'}))
        self.assertEqual(len(doc.find('select[name=user_permissions]')), 1)

    def test_base_template_name_is_exposed_to_the_template(self):
        widget = build_widget()
        context = widget.get_context('user_permissions', [], {})
        self.assertEqual(context['widget']['base_template_name'],
                         'django/forms/widgets/select.html')

    def test_table_context_is_nested_under_the_widget(self):
        widget = build_widget()
        context = widget.get_context('user_permissions', [], {})
        self.assertIn('table', context['widget'])
        self.assertIn('apps_available', context['widget']['table'])
