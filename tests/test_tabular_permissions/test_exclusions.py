"""
Coverage for the exclusion settings.

app_settings resolves TABULAR_PERMISSIONS_CONFIG at import time, so override_settings cannot
reach these values. The names are patched where widgets.py imported them, which is the same
object the code actually reads.
"""

from unittest import mock

from django import test
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from custom_models.models import ModelWithCustomPermissions

from .helpers import build_widget, permission_id


def rendered_models(ctx, app_label='custom_models'):
    app = ctx['apps_available'].get(app_label)
    return set(app['models']) if app else set()


class ExcludeAppsTest(test.TestCase):

    def test_excluded_app_gets_no_rows(self):
        with mock.patch('tabular_permissions.widgets.EXCLUDE_APPS', ['custom_models']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(rendered_models(ctx), set())

    def test_other_apps_are_untouched_by_the_exclusion(self):
        with mock.patch('tabular_permissions.widgets.EXCLUDE_APPS', ['custom_models']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertIn('auth', ctx['apps_available'])
        self.assertIn('user', ctx['apps_available']['auth']['models'])

    def test_excluded_app_permissions_are_not_offered_in_the_plain_widget_either(self):
        # The exclusion is about hiding the permission entirely, not about moving it from the
        # table to the leftover widget.
        with mock.patch('tabular_permissions.widgets.EXCLUDE_APPS', ['custom_models']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        excluded = permission_id(ModelWithCustomPermissions, 'view')
        self.assertNotIn(excluded, [pk for pk, _label in ctx['reminder_choices']])


class ExcludeModelsTest(test.TestCase):

    def test_excluded_model_gets_no_row(self):
        with mock.patch('tabular_permissions.widgets.EXCLUDE_MODELS',
                        ['modelwithcustompermissions']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertNotIn('modelwithcustompermissions', rendered_models(ctx))

    def test_sibling_models_in_the_same_app_survive(self):
        with mock.patch('tabular_permissions.widgets.EXCLUDE_MODELS',
                        ['modelwithcustompermissions']):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertIn('modelwithextradefaultpermissions', rendered_models(ctx))


class ExcludeFunctionTest(test.TestCase):

    def test_function_returning_true_removes_the_model(self):
        def exclude(model):
            return model._meta.model_name == 'modelwithcustompermissions'

        with mock.patch('tabular_permissions.widgets.EXCLUDE_FUNCTION', exclude):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertNotIn('modelwithcustompermissions', rendered_models(ctx))
        self.assertIn('modelwithextradefaultpermissions', rendered_models(ctx))

    def test_function_receives_the_model_class(self):
        seen = []

        def exclude(model):
            seen.append(model)
            return False

        with mock.patch('tabular_permissions.widgets.EXCLUDE_FUNCTION', exclude):
            build_widget().get_table_context('user_permissions', [], {})
        self.assertIn(ModelWithCustomPermissions, seen)

    def test_default_function_excludes_nothing(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertIn('modelwithcustompermissions', rendered_models(ctx))


class DefaultExcludedAppsTest(test.TestCase):
    """
    sessions, contenttypes and admin are hidden out of the box.

    An excluded app still gets an entry in apps_available, only with no models in it. The
    template iterates app.models, so nothing renders; these assertions target that observable
    outcome rather than the presence of the key.
    """

    def test_admin_app_contributes_no_rows_by_default(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(rendered_models(ctx, 'admin'), set())

    def test_contenttypes_app_contributes_no_rows_by_default(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(rendered_models(ctx, 'contenttypes'), set())

    def test_sessions_app_contributes_no_rows_by_default(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertEqual(rendered_models(ctx, 'sessions'), set())

    def test_default_exclusions_do_not_leak_into_the_plain_widget(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        log_entry_view = Permission.objects.filter(codename='view_logentry').values_list(
            'id', flat=True).first()
        self.assertNotIn(log_entry_view, [pk for pk, _label in ctx['reminder_choices']])


class UseForConcreteTest(test.TestCase):
    """use_for_concrete decides whether proxies resolve to their concrete content type."""

    def test_default_keeps_the_proxy_content_type(self):
        ctx = build_widget().get_table_context('user_permissions', [], {})
        entry = ctx['apps_available']['custom_models']['models']['modelwithcustompermissions']
        expected = ContentType.objects.get_for_model(ModelWithCustomPermissions,
                                                     for_concrete_model=False).pk
        codename_key = f'view_modelwithcustompermissions_{expected}'
        self.assertEqual(ctx['codename_id_map'].get(codename_key), entry['view_perm_id'])

    def test_concrete_lookup_still_produces_a_table(self):
        # RED: use_for_concrete=True crashes the widget. The code assigns
        # `opts = model._meta.concrete_model`, which is the model class rather than its
        # _meta, so opts.model_name raises AttributeError. It goes unnoticed because
        # opts.app_label happens to resolve to a field descriptor instead of failing, and
        # because the setting defaults to False.
        with mock.patch('tabular_permissions.widgets.USE_FOR_CONCRETE', True):
            ctx = build_widget().get_table_context('user_permissions', [], {})
        self.assertIn('modelwithcustompermissions', rendered_models(ctx))
