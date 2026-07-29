"""Shared fixtures for the tabular_permissions suite."""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from tabular_permissions.helpers import get_perm_name
from tabular_permissions.widgets import TabularPermissionsWidget


class ExtraPermissionsWidget(TabularPermissionsWidget):
    """
    Stands in for the downstream consumer of the get_extra_permissions() hook.

    The real consumer mixes this package's widget with a third party transfer widget that
    cannot be installed outside its own project, so what is reproduced here is the coupling
    itself: the overridden hook, a replaced base_template_name, a template_name that reaches
    the packaged table through an include, and the extra_permissions dict handed to the
    template. Everything this class touches is public API of the package.
    """

    base_template_name = "custom_models/base_widget_marker.html"
    template_name = "custom_models/extra_permissions_wrapper.html"

    def __init__(self, *args, **kwargs):
        self.extra_permissions = kwargs.pop('extra_permissions', {})
        super().__init__(*args, **kwargs)

    def get_extra_permissions(self, model, ct_id, codename_id_map):
        perms = []
        opts = model._meta
        for perm_name in self.extra_permissions:
            codename = get_perm_name(opts.model_name, perm_name)
            perms.append({
                'codename': codename,
                'verbose_name': self.extra_permissions[perm_name],
                'perm_name': perm_name,
                'c_perm_id': codename_id_map.get(f'{codename}_{ct_id}', False),
            })
        return perms

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['table']['extra_permissions'] = self.extra_permissions
        return context


def permission_id(model, action):
    """
    Return the auth_permission pk for a default-style action on a model.

    Only for actions that follow the "<action>_<model>" codename convention. Codenames
    declared in Meta.permissions are literal, so use codename_id() for those.
    """
    return codename_id(model, get_perm_name(model._meta.model_name, action))


def codename_id(model, codename):
    """Return the auth_permission pk for a literal codename, or None when absent."""
    ct = ContentType.objects.get_for_model(model)
    return Permission.objects.filter(content_type=ct, codename=codename).values_list(
        'id', flat=True).first()


def all_permission_choices():
    """Every permission as (pk, label) pairs, the shape a form field hands the widget."""
    return [(p.pk, str(p)) for p in Permission.objects.all().order_by('codename')]


def build_widget(widget_class=TabularPermissionsWidget, choices=None, **kwargs):
    """Instantiate a widget the way the admin form field does."""
    kwargs.setdefault('verbose_name', 'permissions')
    kwargs.setdefault('is_stacked', False)
    return widget_class(choices=all_permission_choices() if choices is None else choices,
                        **kwargs)
