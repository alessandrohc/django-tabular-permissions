"""Unit coverage for the context TabularPermissionsWidget builds for its template."""

from unittest import mock

from django import test
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.forms.models import ModelChoiceIteratorValue

from custom_models.models import (
    ModelWithCustomPermissions,
    ModelWithExtraDefaultPermissions,
    ModelWithPartialDefaultPermissions,
)
from tabular_permissions.widgets import TabularPermissionsWidget, get_reminder_permissions_iterator

from .helpers import build_widget, codename_id, permission_id


class TableContextStructureTest(test.TestCase):
    """The context keys consumers read, and the shape of each one."""

    def setUp(self):
        self.widget = build_widget()
        self.ctx = self.widget.get_table_context('user_permissions', [], {})

    def test_context_exposes_the_packaged_table_template_path(self):
        # Consumers extend this path; it is the contract that lets them wrap the table.
        self.assertEqual(self.ctx['template_name'],
                         'tabular_permissions/admin/tabular_permissions.html')

    def test_context_carries_every_key_the_template_reads(self):
        expected = {
            'template_name', 'apps_available', 'user_permissions', 'codename_id_map',
            'input_name', 'custom_permissions_available', 'colspan',
            'django_supports_view_permissions', 'reminder_choices',
        }
        self.assertTrue(expected.issubset(set(self.ctx)),
                        msg=f'missing keys: {expected - set(self.ctx)}')

    def test_input_name_defaults_to_user_permissions(self):
        self.assertEqual(self.ctx['input_name'], 'user_permissions')

    def test_input_name_is_taken_from_the_constructor(self):
        widget = build_widget(input_name='permissions')
        ctx = widget.get_table_context('permissions', [], {})
        self.assertEqual(ctx['input_name'], 'permissions')

    def test_apps_available_is_keyed_by_app_label(self):
        self.assertIn('custom_models', self.ctx['apps_available'])
        self.assertEqual(self.ctx['apps_available']['custom_models']['label'], 'custom_models')

    def test_model_entry_carries_a_globally_unique_label(self):
        # The label feeds DOM ids. Being app qualified is what keeps ids unique across apps
        # that happen to share a model name.
        entry = self.ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        self.assertEqual(entry['label'], 'custom_models_modelwithcustompermissions')

    def test_every_rendered_model_label_is_unique(self):
        labels = [model['label']
                  for app in self.ctx['apps_available'].values()
                  for model in app['models'].values()]
        self.assertEqual(len(labels), len(set(labels)),
                         msg='duplicated model labels produce duplicated DOM ids')

    def test_user_permissions_holds_the_assigned_ids(self):
        perm = Permission.objects.first()
        ctx = build_widget().get_table_context('user_permissions', [perm.pk], {})
        self.assertIn(perm.pk, list(ctx['user_permissions']))

    def test_codename_id_map_is_keyed_by_codename_and_content_type(self):
        perm = Permission.objects.first()
        self.assertEqual(self.ctx['codename_id_map'][f'{perm.codename}_{perm.content_type_id}'],
                         perm.pk)


class DefaultPermissionsTest(test.TestCase):
    """Each of the four columns is filled only when default_permissions allows it."""

    def setUp(self):
        self.ctx = build_widget().get_table_context('user_permissions', [], {})
        self.models = self.ctx['apps_available']['custom_models']['models']

    def test_all_four_columns_are_filled_when_all_are_declared(self):
        entry = self.models['modelwithcustompermissions']
        for key in ('view_perm_id', 'add_perm_id', 'change_perm_id', 'delete_perm_id'):
            self.assertTrue(entry[key], msg=f'{key} should carry a permission id')

    def test_undeclared_default_permissions_leave_their_column_empty(self):
        entry = self.models['modelwithpartialdefaultpermissions']
        self.assertTrue(entry['view_perm_id'])
        self.assertTrue(entry['change_perm_id'])
        self.assertFalse(entry['add_perm_id'], msg='add is not in default_permissions')
        self.assertFalse(entry['delete_perm_id'], msg='delete is not in default_permissions')

    def test_stale_permission_row_does_not_refill_an_undeclared_column(self):
        # A row left in auth_permission by an older default_permissions must not resurrect
        # the column, otherwise the widget offers a permission the model disowned.
        ct = ContentType.objects.get_for_model(ModelWithPartialDefaultPermissions)
        Permission.objects.create(codename='add_modelwithpartialdefaultpermissions',
                                  name='stale add', content_type=ct)
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithpartialdefaultpermissions']
        self.assertFalse(entry['add_perm_id'])

    def test_model_without_any_permission_is_absent_from_the_table(self):
        self.assertNotIn('modelwithoutpermissions', self.models,
                         msg='a model with nothing to show must not get a row')


class CustomPermissionsTest(test.TestCase):
    """Meta.permissions and the extra default_permissions actions share one column."""

    def test_meta_permissions_land_in_custom_permissions(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        codenames = [codename for codename, _verbose, _pk in entry['custom_permissions']]
        self.assertIn('can_do_something', codenames)

    def test_custom_permissions_carry_their_permission_id(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        # Codenames from Meta.permissions are literal, not "<action>_<model>".
        expected = codename_id(ModelWithCustomPermissions, 'can_do_something')
        found = {codename: pk for codename, _verbose, pk in entry['custom_permissions']}
        self.assertEqual(found['can_do_something'], expected)

    def test_default_permissions_action_without_a_column_becomes_a_custom_permission(self):
        # "publish" has no column of its own, so it belongs in the other-permissions cell.
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithextradefaultpermissions']
        codenames = [codename for codename, _verbose, _pk in entry['custom_permissions']]
        self.assertIn('publish_modelwithextradefaultpermissions', codenames)

    def test_the_four_column_actions_never_duplicate_into_custom_permissions(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithextradefaultpermissions']
        codenames = [codename for codename, _verbose, _pk in entry['custom_permissions']]
        for action in ('view', 'add', 'change', 'delete'):
            self.assertNotIn(f'{action}_modelwithextradefaultpermissions', codenames)

    def test_custom_permissions_available_flags_the_extra_column(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertTrue(ctx['custom_permissions_available'])

    def test_translation_hook_receives_each_custom_permission(self):
        with mock.patch('tabular_permissions.widgets.TRANSLATION_FUNC') as translate:
            translate.side_effect = lambda codename, verbose, ct_id: f'translated:{codename}'
            ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        verbose_names = [verbose for _codename, verbose, _pk in entry['custom_permissions']]
        self.assertIn('translated:can_do_something', verbose_names)


class ReminderPermissionsTest(test.TestCase):
    """Permissions the table cannot show must stay reachable through the plain widget."""

    def test_original_widget_stays_hidden_when_the_table_covers_everything(self):
        widget = build_widget()
        widget.get_table_context('user_permissions', [], {})
        self.assertTrue(widget.hide_original)

    def test_orphan_permission_reveals_the_original_widget(self):
        # A permission with no model behind it cannot get a row, so the plain widget is the
        # only way left to assign it.
        ct = ContentType.objects.get_for_model(Permission)
        Permission.objects.create(codename='handmade_permission', name='handmade',
                                  content_type=ct)
        widget = build_widget()
        widget.get_table_context('user_permissions', [], {})
        self.assertFalse(widget.hide_original)

    def test_orphan_permission_is_offered_as_a_reminder_choice(self):
        ct = ContentType.objects.get_for_model(Permission)
        orphan = Permission.objects.create(codename='handmade_permission', name='handmade',
                                           content_type=ct)
        widget = build_widget()
        ctx = widget.get_table_context('user_permissions', [], {})
        self.assertIn(orphan.pk, [pk for pk, _label in ctx['reminder_choices']])

    def test_permission_shown_in_the_table_is_not_repeated_as_a_reminder(self):
        widget = build_widget()
        ctx = widget.get_table_context('user_permissions', [], {})
        managed = permission_id(ModelWithCustomPermissions, 'can_do_something')
        self.assertNotIn(managed, [pk for pk, _label in ctx['reminder_choices']])

    def test_managed_perms_collects_every_id_the_table_owns(self):
        widget = build_widget()
        widget.get_table_context('user_permissions', [], {})
        self.assertIn(permission_id(ModelWithCustomPermissions, 'view'), widget.managed_perms)

    def test_extra_default_permission_is_not_left_over(self):
        # It shows up in the custom column, so it must not also appear in the plain widget.
        widget = build_widget()
        ctx = widget.get_table_context('user_permissions', [], {})
        publish = permission_id(ModelWithExtraDefaultPermissions, 'publish')
        self.assertNotIn(publish, [pk for pk, _label in ctx['reminder_choices']])

    def test_customization_hook_can_filter_the_reminder_choices(self):
        with mock.patch('tabular_permissions.widgets.CUSTOM_PERMISSIONS_CUSTOMIZATION_FUNC',
                        return_value=[]):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(ctx['reminder_choices'], [])

    def test_repeated_context_builds_keep_the_original_choices(self):
        # get_table_context narrows self.choices to the leftovers, so a widget rendered twice
        # would otherwise compute the second pass from an already filtered list.
        ct = ContentType.objects.get_for_model(Permission)
        Permission.objects.create(codename='handmade_permission', name='handmade',
                                  content_type=ct)
        widget = build_widget()
        first = widget.get_table_context('user_permissions', [], {})
        second = widget.get_table_context('user_permissions', [], {})
        self.assertEqual(list(first['reminder_choices']), list(second['reminder_choices']))


class ReminderIteratorTest(test.SimpleTestCase):
    """The helper that pairs leftover permission ids back with their choices."""

    def test_only_choices_present_in_the_reminder_map_survive(self):
        choices = [(1, 'one'), (2, 'two'), (3, 'three')]
        result = get_reminder_permissions_iterator(choices, {'a_1': 1, 'c_3': 3})
        self.assertEqual(result, [(1, 'one'), (3, 'three')])

    def test_empty_reminder_map_yields_nothing(self):
        self.assertEqual(get_reminder_permissions_iterator([(1, 'one')], {}), [])

    def test_choice_order_is_preserved(self):
        choices = [(3, 'three'), (1, 'one'), (2, 'two')]
        result = get_reminder_permissions_iterator(choices, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual([pk for pk, _label in result], [3, 1, 2])

    def test_model_choice_iterator_value_is_matched(self):
        # This is the value type a ModelMultipleChoiceField actually yields. Membership is
        # tested against a set of plain ids, which only works because the wrapper hashes and
        # compares as the value it wraps.
        wrapped = ModelChoiceIteratorValue(2, object())
        result = get_reminder_permissions_iterator([(wrapped, 'two')], {'a': 2})
        self.assertEqual(len(result), 1)

    def test_model_choice_iterator_value_outside_the_map_is_dropped(self):
        wrapped = ModelChoiceIteratorValue(99, object())
        self.assertEqual(get_reminder_permissions_iterator([(wrapped, 'x')], {'a': 2}), [])


class ColspanTest(test.TestCase):
    """The separator row spans the whole table, so colspan tracks the column count."""

    def test_colspan_counts_the_custom_permission_column(self):
        # app + model + view + add + change + delete + custom = 7
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertTrue(ctx['custom_permissions_available'])
        self.assertEqual(ctx['colspan'], 7)

    def test_colspan_drops_the_custom_column_when_no_model_declares_one(self):
        # RED: custom_permissions_available is set before the exclusion is applied, so an
        # excluded app still turns the column on. The result is a phantom "other permissions"
        # header with nothing but empty cells under it, and a colspan one too wide.
        with mock.patch('tabular_permissions.widgets.EXCLUDE_APPS', ['custom_models']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertFalse(ctx['custom_permissions_available'])
        self.assertEqual(ctx['colspan'], 6)

    def test_view_permission_column_is_always_announced(self):
        # Every supported Django release ships the view permission.
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertTrue(ctx['django_supports_view_permissions'])


class AppsCustomizationHookTest(test.TestCase):
    """The apps_customization_func hook gets the last word on the table contents."""

    def test_hook_output_replaces_apps_available(self):
        with mock.patch('tabular_permissions.widgets.APPS_CUSTOMIZATION_FUNC',
                        return_value={'sentinel': {}}):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(ctx['apps_available'], {'sentinel': {}})

    def test_hook_receives_the_assembled_apps(self):
        with mock.patch('tabular_permissions.widgets.APPS_CUSTOMIZATION_FUNC',
                        side_effect=lambda apps: apps) as hook:
            build_widget().get_table_context('user_permissions', [], {})
        self.assertIn('custom_models', hook.call_args[0][0])


class WidgetConstructionTest(test.SimpleTestCase):
    """The constructor keeps the keyword signature consumers rely on."""

    def test_defaults_leave_the_widget_usable(self):
        widget = TabularPermissionsWidget()
        self.assertEqual(widget.input_name, 'user_permissions')
        self.assertTrue(widget.hide_original)
        self.assertEqual(widget.managed_perms, [])
        self.assertIsNone(widget.org_choices)

    def test_verbose_name_and_stacking_reach_the_parent_widget(self):
        widget = TabularPermissionsWidget(verbose_name='permissions', is_stacked=True)
        self.assertEqual(widget.verbose_name, 'permissions')
        self.assertTrue(widget.is_stacked)

    def test_attrs_and_choices_are_accepted_positionally(self):
        widget = TabularPermissionsWidget({'class': 'x'}, [(1, 'one')])
        self.assertEqual(widget.attrs['class'], 'x')
        self.assertEqual(list(widget.choices), [(1, 'one')])

    def test_javascript_asset_is_declared(self):
        self.assertIn('tabular_permissions/tabular_permissions.js',
                      TabularPermissionsWidget().media._js)
