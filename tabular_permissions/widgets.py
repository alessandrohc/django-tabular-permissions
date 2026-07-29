from collections import OrderedDict
from itertools import chain

from django import VERSION
from django.apps import apps
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str
from .app_settings import (
    EXCLUDE_FUNCTION, EXCLUDE_APPS,
    EXCLUDE_MODELS, USE_FOR_CONCRETE,
    TRANSLATION_FUNC, APPS_CUSTOMIZATION_FUNC,
    CUSTOM_PERMISSIONS_CUSTOMIZATION_FUNC,
    TEMPLATE)
from .helpers import get_perm_name


def get_reminder_permissions_iterator(choices, reminder_perms):
    reminder_perms_list = reminder_perms.values()
    l = []
    for c in choices:
        if c[0] in reminder_perms_list:
            l.append(c)
    return l


class TabularPermissionsWidget(FilteredSelectMultiple):
    # Template that renders the widget
    base_template_name = "django/forms/widgets/select.html"
    # Template that renders the table and includes the widget
    template_name = TEMPLATE

    def __init__(self, attrs=None, choices=(), verbose_name=None, is_stacked=False, input_name='user_permissions'):
        super().__init__(verbose_name, is_stacked, attrs, choices)
        self.managed_perms = []
        self.input_name = input_name  # in case of UserAdmin, it's 'user_permissions', GroupAdmin it's 'permissions'
        self.hide_original = True
        self.org_choices = None

    def get_extra_permissions(self, model, ct_id, codename_id_map):
        """
        :param model:
        :param ct_id:
        :param codename_id_map:
        :return: dict {
            'codename': codename,
            'verbose_name': verbose_name,
            'c_perm_id': c_perm_id
        }
        """
        return ()

    def get_table_context(self, name, value, attrs):
        choices = self.choices if self.org_choices is None else self.org_choices
        apps_available = OrderedDict()  # []  # main container to send to template
        user_permissions = Permission.objects.filter(id__in=value or []).values_list('id', flat=True)
        all_perms = Permission.objects.all().values('id', 'codename', 'content_type_id').order_by('codename')
        excluded_perms = set()
        codename_id_map = {}
        for p in all_perms:
            codename_id_map[f"{p['codename']}_{p['content_type_id']}"] = p['id']

        # reminder_perms used to detect if the tabular permissions covers all permissions,
        # if true, we don't need to make the default widget visible.
        reminder_perms = codename_id_map.copy()

        # a global flag to either show or hide the other permission column in the table
        custom_permissions_available = False

        cache_content_type = {}
        for ct in ContentType.objects.all():
            model = ct.model_class()
            if model:
                opts = model._meta
                if USE_FOR_CONCRETE:
                    opts = model._meta.concrete_model

                cache_key = (opts.app_label, opts.model_name)
                cache_content_type[cache_key] = ct

        for app in apps.get_app_configs():
            app_dict = {'verbose_name': force_str(app.verbose_name),
                        'label': app.label,
                        'models': OrderedDict()}

            for model_name in app.models:
                model_custom_permissions = []
                model_custom_permissions_ids = []

                model = app.models[model_name]
                opts = model._meta
                if USE_FOR_CONCRETE:
                    opts = model._meta.concrete_model
                cache_key = (opts.app_label, opts.model_name)

                ct_obj = cache_content_type.get(cache_key)
                if not ct_obj:
                    ct_obj = ContentType.objects.get_for_model(model, for_concrete_model=USE_FOR_CONCRETE)

                ct_id = ct_obj.pk

                view_perm_name = get_perm_name(model_name, 'view')
                add_perm_name = get_perm_name(model_name, 'add')
                change_perm_name = get_perm_name(model_name, 'change')
                delete_perm_name = get_perm_name(model_name, 'delete')

                view_perm_id = (codename_id_map.get(f'{view_perm_name}_{ct_id}', False)
                                if 'view' in opts.default_permissions else False)
                add_perm_id = (codename_id_map.get(f'{add_perm_name}_{ct_id}', False)
                               if 'add' in opts.default_permissions else False)
                change_perm_id = (codename_id_map.get(f'{change_perm_name}_{ct_id}', False)
                                  if 'change' in opts.default_permissions else False)
                delete_perm_id = (codename_id_map.get(f'{delete_perm_name}_{ct_id}', False)
                                  if 'delete' in opts.default_permissions else False)

                # default_permissions may declare actions beyond the four that get their own
                # column. Those are surfaced in the "other permissions" column; without this
                # they would silently fall through to the leftover widget.
                extra_default_permissions = []
                for action in opts.default_permissions:
                    if action in {'view', 'add', 'change', 'delete'}:
                        continue
                    extra_default_permissions.append(
                        (
                            get_permission_codename(action, opts),
                            'Can %s %s' % (action, opts.verbose_name_raw),
                        )
                    )

                if opts.permissions or extra_default_permissions:
                    custom_permissions_available = True
                    for codename, perm_name in chain(opts.permissions, extra_default_permissions):
                        c_perm_id = codename_id_map.get(f'{codename}_{ct_id}', False)
                        verbose_name = TRANSLATION_FUNC(codename, perm_name, ct_id)
                        model_custom_permissions.append(
                            (codename, verbose_name, c_perm_id)
                        )
                        model_custom_permissions_ids.append(c_perm_id)

                extra_permissions = self.get_extra_permissions(model, ct_id, codename_id_map)

                if (view_perm_id or add_perm_id or change_perm_id or delete_perm_id
                        or model_custom_permissions or extra_permissions):

                    excluded_perm_ids = [view_perm_id, add_perm_id, change_perm_id, delete_perm_id]
                    excluded_perm_ids.extend(model_custom_permissions_ids)
                    excluded_perm_ids.extend([perm['c_perm_id'] for perm in extra_permissions])
                    excluded_perms.update(excluded_perm_ids)

                    reminder_perms.pop(f'{view_perm_name}_{ct_id}', False)
                    reminder_perms.pop(f'{add_perm_name}_{ct_id}', False)
                    reminder_perms.pop(f'{change_perm_name}_{ct_id}', False)
                    reminder_perms.pop(f'{delete_perm_name}_{ct_id}', False)

                    for c, v, _id in model_custom_permissions:
                        reminder_perms.pop(f'{c}_{ct_id}', False)

                    for perm in extra_permissions:
                        reminder_perms.pop(f"{perm['codename']}_{ct_id}", False)

                    # Because the logic of exclusion should/would work on both the tabular_permissin widget
                    # and the normal widget
                    # ie bydefautlwe exclude the session, admin log permissions and we dont want that on either widgets
                    if app.label in EXCLUDE_APPS or model_name in EXCLUDE_MODELS or EXCLUDE_FUNCTION(model):
                        continue

                    app_dict['models'][model_name] = {
                        'model_name': model_name,
                        'model': model,
                        'label': force_str(model._meta.label_lower.replace('.', '_')),
                        'verbose_name_plural': force_str(opts.verbose_name_plural),
                        'verbose_name': force_str(opts.verbose_name),
                        'view_perm_id': view_perm_id,
                        'view_perm_name': view_perm_name,
                        'add_perm_id': add_perm_id,
                        'add_perm_name': add_perm_name,
                        'change_perm_id': change_perm_id,
                        'change_perm_name': change_perm_name,
                        'delete_perm_id': delete_perm_id,
                        'delete_perm_name': delete_perm_name,
                        'custom_permissions': model_custom_permissions,
                        'extra_permissions': extra_permissions
                    }

            if app.models:
                apps_available[app.label] = app_dict
        if VERSION >= (2, 1, 0) and custom_permissions_available:
            colspan = 7
        elif VERSION >= (2, 1, 0) or custom_permissions_available:
            colspan = 6
        else:
            colspan = 5

        apps_available = APPS_CUSTOMIZATION_FUNC(apps_available)

        self.managed_perms = excluded_perms
        if reminder_perms:
            self.hide_original = False

        reminder_choices = get_reminder_permissions_iterator(choices, reminder_perms)
        # filter the left over permission
        reminder_choices = CUSTOM_PERMISSIONS_CUSTOMIZATION_FUNC(reminder_choices)

        ctx = {
            'template_name': "tabular_permissions/admin/tabular_permissions.html",
            'apps_available': apps_available,
            'user_permissions': user_permissions,
            'codename_id_map': codename_id_map,
            'input_name': self.input_name,
            'custom_permissions_available': custom_permissions_available,
            'colspan': colspan,
            'django_supports_view_permissions': VERSION >= (2, 1, 0),
            'reminder_choices': reminder_choices
        }
        if self.org_choices is None:
            self.org_choices = self.choices
        self.choices = reminder_choices
        return ctx

    def get_context(self, name, value, attrs):
        ctx = self.get_table_context(name, value, attrs)
        context = super().get_context(name, value, attrs)
        context['widget']['base_template_name'] = self.base_template_name
        context['widget']['table'] = ctx
        return context

    class Media:
        js = ('tabular_permissions/tabular_permissions.js',)
