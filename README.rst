
django-tabular-permissions
##########################
Display django permissions in a user friendly, translatable and customizable widget .

This is an independent fork maintained by `Alessandro Hecht <https://github.com/alessandrohc>`_
at `alessandrohc/django-tabular-permissions <https://github.com/alessandrohc/django-tabular-permissions>`_.
It is not published on PyPI — install it from the repository (see Installation below).
See `Credits`_ for the upstream authors.

Version
-------
3.1.1

Features:
---------
* Permissions and their relevant app and models names are displayed in the active language.
* Permissions are displayed in a table that contain the default model permissions **plus** any custom permissions.
* Supports view permission.
* Customize which apps, models to show in the permissions table. You can also set a exclude function for high-end customization.
* RTL ready, Bootstrap ready.
* Easy customize-able look.
* Python 3.10, 3.11, 3.12, 3.13. Django 4.2, 5.0, 5.1, 5.2.
* Default `FilteredSelectMultiple` widget will appear only if you have custom permissions that are not model related (ie directly created by code or hand)



Installation
------------
Install this fork straight from the repository::

    pip install git+https://github.com/alessandrohc/django-tabular-permissions.git@master

Pin a tag for a reproducible install::

    pip install git+https://github.com/alessandrohc/django-tabular-permissions.git@v3.1.1

.. note::
   ``pip install django-tabular-permissions`` pulls the **original** package from PyPI,
   not this fork.


and add "tabular_permissions" to your INSTALLED_APPS setting (at any place after `django.contrib.auth`) ::

    INSTALLED_APPS = [
        'django.contrib.auth',
         ....
        'tabular_permissions',
    ]

Finally, execute::

    python manage.py collectstatic


then navigate to User and/or Group change form to see `tabular_permissions` in action.

Configuration:
--------------
Tabular permissions possible configurations and their default::

    TABULAR_PERMISSIONS_CONFIG = {
        'template': 'tabular_permissions/admin/tabular_permissions.html',
        'extra_permissions': {},
        'exclude': {
            'override': False,
            'apps': [],
            'models': [],
            'function':'tabular_permissions.helpers.dummy_permissions_exclude'
        },
        'auto_implement': True,
        'use_for_concrete': False,
        'custom_permission_translation': 'tabular_permissions.helpers.custom_permissions_translator',
        'apps_customization_func': 'tabular_permissions.helpers.apps_customization_func',
        'custom_permissions_customization_func': 'tabular_permissions.helpers.custom_permissions_customization_func',
    }


`template`
  the template which contains the permissions table, you can always customize this template by extending or overriding.
  Notice that there is a `style` block which you can override to easily edit the css.

`extra_permissions`
  *(fork addition)* A dict of ``{permission_name: label}`` describing permissions that are
  not tied to a model's ``Meta.permissions`` but should still get a column in the table.

  The package itself only exposes the value as ``tabular_permissions.app_settings.EXTRA_PERMISSIONS``
  and ships a no-op hook — ``TabularPermissionsWidget.get_extra_permissions(model, ct_id, codename_id_map)``
  returns an empty tuple. To make the columns render, subclass the widget and override that hook,
  returning a list of dicts with ``codename``, ``verbose_name`` and ``c_perm_id`` keys.

  See ``plus_base.xpublique.xadmin_site.widgets.permission.TabularPermissionTransferWidget``
  in the instanet project for a working implementation.

`exclude`
  Control which apps, models to show in the permissions table.

  By default ``tabular_permissions`` exclude `sessions` , `contenttypes` and `admin` apps from showing their models in the permissions table. If you want to show them you can switch ``override`` to `False`.

  ``apps`` & ``models`` lists would contain the names of the apps and models you wish to exclude.

  ``function`` is a dotted path of a custom function which receive the model as a parameter to decide either to exclude it or not, default to a dummy function that always return False (ie do not exclude)

auto_implement
  By default, just by including `tabular_permissions` in your installed_apps, the ``django.contrib.admin.UserAdmin`` (and ``GroupAdmin``) are "patched" to include the tabular_permissions widget.
  If you have a custom UserAdmin, then set this option to False and make sure you either:

  1. Inherit from ``tabular_permissions.admin.TabularPermissionsUserAdmin`` and ``tabular_permissions.admin.TabularPermissionsGroupAdmin`` for User & Group ModelAdmin.
  2. Or for a more direct and compact way, inherit your ModelAdmin from ``tabular_permissions.admin.UserTabularPermissionsMixin`` and ``tabular_permissions.admin.GroupTabularPermissionsMixin`` (comes before admin.ModelAdmin in the mro),
  3. Set the user_permissions widget to ``tabular_permissions.widgets.TabularPermissionsWidget`` and remember to send a 3rd argument 'permissions' for Group Model Admin.
     See ``tabular_permissions.admin`` for information.

use_for_concrete
  Default: False (new in version 2.8)

  There was an inconsistency with proxy models permissions (Django ticket `11154 <https://code.djangoproject.com/ticket/11154>`_) which got fixed in Django 2.1
  In case you're on an django <2.1 and you have proxy models and you created their permissions by hand (via this `gist <https://gist.github.com/magopian/7543724>`_ maybe), then turn off this option in order to correctly assign your newly created permissions.
  For django > 2.1, leave it as is you should be good.

custom_permission_translation
  A dotted path function to translate the custom permission.
  This function gets passed the permissions `codename`, `verbose_name` and its relevant `content_type_id`.
  The function will try to translate the permission verbose_name.

apps_customization_func
  A dotted path function to control the whole permissions objects passed to the widget.
  Sometimes you use custom menu where apps and models are ordered in a more "user friendly" manner and not necessarily
  in the "actual programmatic" apps & models order.
  You can use this option to get a hold of the whole ordered dict and shuffle its content around moving
  models from one app to the other and do all kind of crazy stuff to get just the right table of permissions.

custom_permissions_customization_func
  A dotted path function to control the "extra" permissions which will be displayed on the default django widget.
  Suppose a model is removed, or an app is commented out of `INSTALLED_APPS`; its permissions are still in the
  permissions table, and it will be picked up.
  Use this function to manipulate and order those permissions and return them .
  The permissions are passed a list of tuples , like this ``[(perm_id, perm_name), (perm_id, perm_name), ...]``

JavaScript:
-----------
Located at 'static/tabular_permissions/tabular_permissions.js', it have 2 responsibilities:

1. Upon form submit, the checked permissions in the table are dynamically appended to the form default permission input so the backend can carry on its functionality normally and correctly.
2. Add handlers for column and row `select-all` checkboxes.


Compatibility:
--------------
This version supports Python 3.10 to 3.13 and Django 4.2 to 5.2. The combinations are
exercised on every push; Django 4.2 and 5.0 do not support Python 3.13, so those two pairs
are excluded from the matrix.

For older interpreters or Django releases, use a 3.0.x tag.

Demo:
-----

To run the demo project in the repo on your local you need

1. Clone the repo;
2. Create a virtualenv
3. `pip install -e .`
4. `python manage.py migrate`
5. `python manage.py runserver`


Tests
-----

To run the tests, you need to install the test requirements::

    cd tests
    pip install -r requirements.txt

Then run::

    python runtests.py

A single module, class or test can be targeted by passing it as an argument::

    python runtests.py tests.test_tabular_permissions.test_widget_render

With Coverage ::

        coverage run --source=../tabular_permissions runtests.py
        coverage report -m
        coverage html

What the suite does not cover
.............................

The behaviour implemented in ``tabular_permissions.js`` is not exercised: the select-all
checkboxes and the submit handler that copies the table state into the plain widget both need
a real browser. The suite covers everything the server produces, including the ids, classes
and data attributes the script keys off, so a rename that would break the script fails a test.
The clicking itself does not.


.. _Credits:

Credits
-------

This fork stands on the work of others:

* `Ramez Ashraf <https://github.com/RamezIssac>`_ — original author of
  ``django-tabular-permissions`` and copyright holder (see LICENSE).
* `alexsilva <https://github.com/alexsilva>`_ — the bulk of this fork's changes
  (extra permissions, column selection, pt-BR locale, multiple-widget fixes).
* `Alessandro Hecht <https://github.com/alessandrohc>`_ — current maintainer.

Licensed under the BSD License, unchanged from upstream.
