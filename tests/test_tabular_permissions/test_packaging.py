"""
Coverage for the distribution metadata.

These assertions describe the target state of the packaging work, so they fail until
pyproject.toml lands. They exist because the failure mode of bad packaging is silent: pip
happily installs on an unsupported interpreter, and a missing package-data pattern only shows
up as a TemplateDoesNotExist on someone else's deploy.
"""

import io
import re
from pathlib import Path

from django import test

try:  # tomllib is stdlib from 3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only on 3.10
    import tomli as tomllib

import tabular_permissions

ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT = ROOT / 'pyproject.toml'

# Lower bound of the declared support matrix.
MIN_PYTHON = (3, 10)
EXPECTED_VERSION = '3.1.0'


def load_pyproject():
    with PYPROJECT.open('rb') as handle:
        return tomllib.load(handle)


class PyprojectPresenceTest(test.SimpleTestCase):

    def test_pyproject_exists(self):
        self.assertTrue(PYPROJECT.is_file(),
                        msg='pyproject.toml is required to declare a PEP 517 build backend')

    def test_setup_py_is_gone(self):
        # Keeping both means two places to disagree about the support matrix.
        self.assertFalse((ROOT / 'setup.py').exists(),
                         msg='metadata should live in pyproject.toml alone')


class BuildSystemTest(test.SimpleTestCase):

    def setUp(self):
        if not PYPROJECT.is_file():
            self.skipTest('pyproject.toml not written yet')
        self.data = load_pyproject()

    def test_build_backend_is_declared(self):
        self.assertIn('build-backend', self.data.get('build-system', {}))

    def test_build_requirements_are_declared(self):
        self.assertTrue(self.data.get('build-system', {}).get('requires'))


class ProjectMetadataTest(test.SimpleTestCase):

    def setUp(self):
        if not PYPROJECT.is_file():
            self.skipTest('pyproject.toml not written yet')
        self.project = load_pyproject().get('project', {})

    def test_distribution_name_is_preserved(self):
        self.assertEqual(self.project.get('name'), 'django-tabular-permissions')

    def test_requires_python_is_declared(self):
        # Without this pip installs on interpreters the package cannot run on.
        self.assertIn('requires-python', self.project)

    def test_requires_python_floor_matches_the_support_matrix(self):
        floor = re.search(r'(\d+)\.(\d+)', self.project.get('requires-python', ''))
        self.assertIsNotNone(floor, msg='requires-python must name a minor version')
        self.assertEqual((int(floor.group(1)), int(floor.group(2))), MIN_PYTHON)

    def test_readme_is_declared_with_its_content_type(self):
        # A missing content type makes twine assume x-rst and warn.
        readme = self.project.get('readme')
        self.assertTrue(readme)
        if isinstance(readme, dict):
            self.assertIn('content-type', readme)
        else:
            self.assertTrue(str(readme).endswith('.rst'))

    def test_license_is_an_spdx_expression(self):
        license_value = self.project.get('license')
        if isinstance(license_value, dict):
            license_value = license_value.get('text', '')
        self.assertRegex(str(license_value), r'BSD-3-Clause',
                         msg='license classifiers are deprecated in favour of SPDX')

    def test_dependencies_declare_django(self):
        joined = ' '.join(self.project.get('dependencies', []))
        self.assertIn('Django', joined)


class VersionTest(test.SimpleTestCase):
    """One version, one place."""

    def test_package_exposes_the_release_version(self):
        self.assertEqual(tabular_permissions.__version__, EXPECTED_VERSION)

    def test_metadata_version_matches_the_package(self):
        if not PYPROJECT.is_file():
            self.skipTest('pyproject.toml not written yet')
        data = load_pyproject()
        project = data.get('project', {})
        if 'version' in project:
            self.assertEqual(project['version'], tabular_permissions.__version__)
        else:
            # A dynamic version has to point back at the package attribute.
            self.assertIn('version', project.get('dynamic', []),
                          msg='version must be declared either statically or as dynamic')


class ClassifiersTest(test.SimpleTestCase):

    def setUp(self):
        if not PYPROJECT.is_file():
            self.skipTest('pyproject.toml not written yet')
        self.classifiers = load_pyproject().get('project', {}).get('classifiers', [])

    def test_no_python_2_classifier(self):
        self.assertNotIn('Programming Language :: Python :: 2.7', self.classifiers)

    def test_no_classifier_below_the_declared_floor(self):
        declared = []
        for classifier in self.classifiers:
            match = re.fullmatch(r'Programming Language :: Python :: (\d+)\.(\d+)', classifier)
            if match:
                declared.append((int(match.group(1)), int(match.group(2))))
        self.assertTrue(declared, msg='no Python minor version classifier declared')
        self.assertGreaterEqual(min(declared), MIN_PYTHON)

    def test_license_classifier_is_dropped(self):
        # setuptools deprecated these in favour of the SPDX expression.
        license_classifiers = [c for c in self.classifiers if c.startswith('License ::')]
        self.assertEqual(license_classifiers, [])

    def test_target_django_versions_are_classified(self):
        for version in ('4.2', '5.2'):
            self.assertIn(f'Framework :: Django :: {version}', self.classifiers)

    def test_no_django_classifier_below_the_supported_floor(self):
        declared = []
        for classifier in self.classifiers:
            match = re.fullmatch(r'Framework :: Django :: (\d+)\.(\d+)', classifier)
            if match:
                declared.append((int(match.group(1)), int(match.group(2))))
        self.assertTrue(declared, msg='no Django version classifier declared')
        self.assertGreaterEqual(min(declared), (4, 2))


class PackageDataTest(test.SimpleTestCase):
    """Templates, static files and catalogues have to ship with the wheel."""

    def setUp(self):
        if not PYPROJECT.is_file():
            self.skipTest('pyproject.toml not written yet')
        self.data = load_pyproject()

    def test_the_package_itself_is_declared(self):
        setuptools_conf = self.data.get('tool', {}).get('setuptools', {})
        packages = setuptools_conf.get('packages')
        if isinstance(packages, dict):
            # find directives resolve at build time; the include filter must name the package.
            include = packages.get('find', {}).get('include', [])
            self.assertTrue(any('tabular_permissions' in entry for entry in include))
        else:
            self.assertIn('tabular_permissions', packages or [])

    def test_non_python_files_are_declared_as_package_data(self):
        patterns = self.data.get('tool', {}).get('setuptools', {}).get(
            'package-data', {}).get('tabular_permissions', [])
        joined = ' '.join(patterns)
        for needed in ('templates', 'static', 'locale'):
            self.assertIn(needed, joined,
                          msg=f'{needed} must be declared or it will not ship')


class LongDescriptionTest(test.SimpleTestCase):
    """
    The readme has to render, because it is the long_description.

    Broken markup does not fail the build: it fails ``twine check``, and on PyPI it would
    render as nothing. Checking it here means an editing slip is caught before a push.
    """

    def test_readme_renders_as_restructuredtext(self):
        readme = ROOT / 'README.rst'
        self.assertTrue(readme.is_file())
        try:
            from readme_renderer.rst import render
        except ModuleNotFoundError:  # pragma: no cover
            self.skipTest('readme_renderer not installed')

        # render() returns None on broken markup and writes the docutils diagnostics to the
        # stream, so the stream is what carries a usable message.
        diagnostics = io.StringIO()
        rendered = render(readme.read_text(encoding='utf-8'), stream=diagnostics)
        self.assertIsNotNone(
            rendered, msg=f'README.rst does not render:\n{diagnostics.getvalue()}')


class ManifestTest(test.SimpleTestCase):
    """Every file MANIFEST.in includes has to actually exist."""

    def test_included_files_exist(self):
        manifest = ROOT / 'MANIFEST.in'
        if not manifest.is_file():
            self.skipTest('MANIFEST.in not used')
        missing = []
        for line in manifest.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] == 'include' and not (ROOT / parts[1]).exists():
                missing.append(parts[1])
        self.assertEqual(missing, [],
                         msg=f'MANIFEST.in points at files that do not exist: {missing}')
