from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
from django.contrib.auth.admin import Group, GroupAdmin as DjGroupAdmin, UserAdmin as DjUserAdmin
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from tabular_permissions.widgets import TabularPermissionsWidget
from . import app_settings

User = get_user_model()


class UserTabularPermissionsMixin:
    """
    Swaps the user_permissions widget for the tabular one on any UserAdmin.

    Mix it in ahead of the ModelAdmin so this formfield_for_manytomany wins. The default help
    text goes away with the widget, since it describes the ctrl-click multiple select that is
    no longer what the user sees.
    """

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == 'user_permissions':
            field.widget = TabularPermissionsWidget(verbose_name=db_field.verbose_name,
                                                    is_stacked=db_field.name in self.filter_vertical)
            field.help_text = ''
        return field


class GroupTabularPermissionsMixin:
    """
    Same as the user mixin, for the GroupAdmin permissions field.

    The field is named differently on Group, so input_name is passed explicitly: it is what
    tells the javascript which select to copy the checked permissions into.
    """

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == 'permissions':
            field.widget = TabularPermissionsWidget(verbose_name=db_field.verbose_name,
                                                    is_stacked=db_field.name in self.filter_vertical,
                                                    input_name='permissions')
            field.help_text = ''
        return field


# Build on whatever ModelAdmin is already registered, so a project with its own UserAdmin
# keeps it. KeyError is the only expected outcome here: the model is simply not registered
# yet, which happens when this app is loaded before the one that registers it.
try:
    UserAdminModel = admin.site._registry[User].__class__
except KeyError:
    UserAdminModel = DjUserAdmin

try:
    GroupAdminModel = admin.site._registry[Group].__class__
except KeyError:
    GroupAdminModel = DjGroupAdmin


class TabularPermissionsUserAdmin(UserTabularPermissionsMixin, UserAdminModel):
    pass


class TabularPermissionsGroupAdmin(GroupTabularPermissionsMixin, GroupAdminModel):
    pass


if app_settings.AUTO_IMPLEMENT:
    try:
        admin.site.unregister(User)
        admin.site.register(User, TabularPermissionsUserAdmin)
        admin.site.unregister(Group)
        admin.site.register(Group, TabularPermissionsGroupAdmin)

    except (AlreadyRegistered, NotRegistered) as exc:
        # Only the registration errors are translated into a configuration hint. Chaining the
        # cause matters: a bare except swallowed unrelated failures raised while building the
        # admin classes and reported them as an ordering problem, hiding the real traceback.
        raise ImproperlyConfigured(
            'Please make sure that django.contrib.auth (Or the app containing your custom User model) '
            'comes before tabular_permissions in INSTALLED_APPS; Or set AUTO_IMPLEMENT to False in your settings.'
        ) from exc
