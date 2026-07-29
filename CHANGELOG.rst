----------
CHANGELOG
----------
 v 3.1.0 (29 July 2026)
  Packaging
  - Added ``pyproject.toml`` with a PEP 517 build backend and removed ``setup.py``. The
    metadata lives in one place and the version is read from ``tabular_permissions.__version__``,
    which previously disagreed with the one declared for the distribution.
  - Declared ``requires-python >= 3.10`` and ``Django>=4.2,<6.0``. Without them pip installed
    on interpreters the package cannot run on.
  - Declared the readme content type, replaced the deprecated license classifier with the
    ``BSD-3-Clause`` SPDX expression, and declared the templates, static files and locale
    catalogues as package data.

  Compatibility
  - Support asserted for Python 3.10 to 3.13 and Django 4.2 to 5.2, exercised by a CI matrix
    over the fourteen supported combinations. Django 4.2 and 5.0 do not support Python 3.13.
  - Removed the Python 2 residue and the dead ``Django < 2.1`` version gates.

  Fixes
  - ``use_for_concrete = True`` raised ``AttributeError`` instead of rendering, because
    ``concrete_model`` is a model class and its options come from ``_meta``.
  - Excluding an app no longer leaves an empty "other permissions" column behind, along with a
    colspan one cell too wide.
  - Registration errors are no longer caught by a bare ``except`` that reported every failure
    as an ``INSTALLED_APPS`` ordering problem. Only the registration exceptions are translated,
    and the original cause is chained.
  - The leftover permission lookup no longer scans a list per choice, which made it quadratic
    in the number of permissions.

  Tests
  - The two remaining tests and the six commented out Selenium ones were replaced by a suite
    covering the template context, the rendering of both admin screens, the exclusion settings,
    the ``get_extra_permissions()`` hook and the distribution metadata. What the suite cannot
    reach without a browser is stated in the README.

 v 3.0.0 (25 September 2024)
  First release of the independent fork, carrying work that had been kept on top of upstream
  without ever being recorded here.
  - The widget renders through ``get_context()`` and ``template_name`` rather than overriding
    ``render()``. This is what makes the table extensible: ``template_name`` wraps the packaged
    table and ``base_template_name`` replaces the underlying select.
  - Added the ``extra_permissions`` setting and the ``get_extra_permissions()`` hook, for
    permissions that are not declared in ``Meta.permissions``.
  - The select-all handlers are bound per table and driven by ``data-permission``, so extra
    permission columns work as well; column and row states are synced on load.
  - Content types are resolved in a single query instead of one per model.
  - A widget rendered more than once keeps its original choices.
  - Added the pt_BR locale and the metadata that makes the table searchable.

 v 2.9.3 (19 April 2024)
  - Fix: Submit event handler in FilteredSelectMultiple removes selected options from tabular_permissions #27 (@DemidovEvg)
  - Fix error caused by non-existent model.label #26 (@SteMazzO)
  - fix: reminder_perms not work with extra default_permissions #29 (@DemidovEvg)


 v 2.9.2 (24 July 2023)
  - Update readme to show how to run tests
  - update demo project to use Django latest releases
  - Enhance the tests to cover more.

 v 2.9.1 (7 June 2022)
  - Django 4 Upgrade. (@youssriaboelseod)

 v 2.9 (11 December 2021)
  - Respect model default permission (Case of stalled permission in database due to removed default permissions)

 v 2.8 (15 September 2020)
  - Changed default of use_for_concrete

 v 2.7 (16 August 2020)
  - Assert Django 3.1 Support.
  - Adds Django 3.1 to travis matrix.

 v 2.6 (3 April 2020)
  - Better aim at working with Custom User/Group ModelAdmin out-of-box (Thanks @abahnihi )

 v 2.5 (1 February 2020)
  - Hinted `collectstatic` in installation docs (#14)
  - Fixes possible non unique HTML ID. (#13)

 v 2.4 (19 December 2019)
  - Added `custom_permissions_customization_func` to control the extra permissions not displayed on main permissions table.

 v 2.3 (25 July 2019)
  - Added native javascript event to wait for the full page load to start (Thanks @Filipe-Souza)

 v 2.2 (8 October 2018)
  - Adds view permission supporting Django 2.1

 v 2.1 (16 July 2018)
  - Adds `apps_customization_func` option to allow a full apps customization control. (Thanks to KuwaitNet)

 v 2.0.2 (July 1 2018)
  - Include locale in manifest
  - fix a problem with exclude settings & use plural instead of singular in exclude apps and models settings,
  - Fix RTL checkbox alignment issue


 v 2.0 (June 30 2018)

  - Major breaking release.
  - Added logic to support model custom permissions in an extra column instead of the original widget.
  - Original widget appear only to totally custom permissions created by code.
  - Added demo_project and renewed screen shots


 1.1.1 (Nov 21 2017)

 - Added `model-` prefix for model name css class to prevent conflict *(ie model_name called table)*

 1.1 (Sep 9 2017)

  - Added support for Django 1.11

 1.0.9 (Mar 11 2016)
  - Minor improvement
  - use Django's `import_string` instead of own hacky function to load the exclude function



 1.0.8 (Feb 1 2016)

  - Added option for dealing with proxy models permissions,
  - Fixes Django version check,

 1.0.7 (Dec 24 2015)
  - Fixed Issue#2.
  - Logic enhancement.


* 1.0.4 (Dec 14 2015)

  made TABULAR_PERMISSIONS_EXCLUDE model and app list case insensitive;
  Handle case where excluded model that does not implement the default permissions;
  Fixes around setup.py

 1.0.3
  Fix RTL, move to 'All' instead of 'Select all' , natively translated by django

 1.0.2
  Added 'Select All' for rows.

 1.0.1
  Added tests, travis CI

 1.0.0 (Dec 9 2015)
  initial concept proof
