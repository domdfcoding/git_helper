from .utils import clean_writer, ensure_requirements


def ensure_doc_requirements(repo_path, templates):
	"""
	Ensure ``doc-source/requirements.txt`` contains the required entries.

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	# TODO: preserve extras [] options

	target_requirements = {
			("extras_require", None),
			("sphinx", "3.0.3"),
			("sphinx_rtd_theme", "0.4.3"),
			("sphinxcontrib-httpdomain", "1.7.0"),
			("sphinxemoji", "0.1.5"),
			("sphinx-autodoc-typehints", "1.10.3"),
			}

	test_req_file = repo_path / "doc-source" / "requirements.txt"

	ensure_requirements(target_requirements, test_req_file)


def make_rtfd(repo_path, templates):
	"""
	Add configuration for ``ReadTheDocs``
	https://readthedocs.org/

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	with (repo_path / ".readthedocs.yml").open("w") as fp:
		clean_writer(f"""# This file is managed by `git_helper`. Don't edit it directly

# .readthedocs.yml
# Read the Docs configuration file
# See https://docs.readthedocs.io/en/stable/config-file/v2.html for details

# Required
version: 2

# Build documentation in the docs/ directory with Sphinx
sphinx:
  builder: html
  configuration: doc-source/conf.py

# Optionally build your docs in additional formats such as PDF and ePub
formats: all

# Optionally set the version of Python and requirements required to build your docs
python:
  version: {templates.globals["python_deploy_version"]}
  install:
    - requirements: requirements.txt
    - requirements: doc-source/requirements.txt
""", fp)
		for file in templates.globals["additional_requirements_files"]:
			clean_writer(f"    - requirements: { file }", fp)


def make_conf(repo_path, templates):
	"""
	Add ``conf.py`` configuration file for ``Sphinx``

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	conf = templates.get_template("conf.py")

	username = templates.globals["username"]
	repo_name = templates.globals["repo_name"]

	if templates.globals["sphinx_html_theme"] == "sphinx_rtd_theme":
		for key, val in {
				"display_github": True,  # Integrate GitHub
				"github_user": username,  # Username
				"github_repo": repo_name,  # Repo name
				"github_version": "master",  # Version
				"conf_py_path": "/",  # Path in the checkout to the docs root
				}:
			if key not in templates.globals["html_context"]:
				templates.globals["html_context"][key] = val

		for key, val in {
				# 'logo': 'logo.png',
				'logo_only': False,  # True will show just the logo
				}:
			if key not in templates.globals["html_theme_options"]:
				templates.globals["html_theme_options"][key] = val

	elif templates.globals["sphinx_html_theme"] == "alabaster":
		# See https://github.com/bitprophet/alabaster/blob/master/alabaster/theme.conf
		# and https://alabaster.readthedocs.io/en/latest/customization.html
		for key, val in {
				# 'logo': 'logo.png',
				"page_width": "1200px",
				"logo_name": "true",
				"github_user": username,  # Username
				"github_repo": repo_name,  # Repo name
				"description": templates.globals["short_desc"],
				"github_banner": "true",
				"github_type": "star",
				"travis_button": "true",
				"badge_branch": "master",
				"fixed_sidebar": "false",
				}:
			if key not in templates.globals["html_theme_options"]:
				templates.globals["html_theme_options"][key] = val

	with (repo_path / "doc-source" / "conf.py").open("w") as fp:
		clean_writer(conf.render(), fp)
		clean_writer("\n", fp)


def copy_docs_styling(repo_path, templates):
	"""
	Copy custom styling for documentation to the desired repository

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	dest__static_dir = repo_path / "doc-source/_static"
	dest__templates_dir = repo_path / "doc-source/_templates"

	for directory in [dest__static_dir, dest__templates_dir]:
		if not directory.is_dir():
			directory.mkdir(parents=True)

	with (dest__static_dir / "style.css").open("w") as fp:
		clean_writer("""/* This file is managed by `git_helper`. Don't edit it directly */

.wy-nav-content {max-width: 900px !important;}

li p:last-child { margin-bottom: 12px !important;}
""", fp)

	with (dest__templates_dir / "layout.html").open("w") as fp:
		clean_writer("""<!--- This file is managed by `git_helper`. Don't edit it directly --->
{% extends "!layout.html" %}
{% block extrahead %}
	<link href="{{ pathto("_static/style.css", True) }}" rel="stylesheet" type="text/css">
{% endblock %}
""", fp)
