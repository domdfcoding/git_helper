#  !/usr/bin/env python
#   -*- coding: utf-8 -*-
#
#  core.py
"""
Core functionality of ``git_helper``.
"""
#
#  Copyright © 2020 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

# stdlib
import os.path
import pathlib
from typing import Callable, List, Sequence, Tuple, Union

# 3rd party
import jinja2
from domdf_python_tools.paths import maybe_make

# this package
from .bots import make_auto_assign_action, make_dependabot, make_imgbot, make_stale_bot
from .ci_cd import (
	make_copy_pypi_2_github,
	make_github_ci,
	make_github_docs_test,
	make_github_octocheese, make_make_conda_recipe,
	make_travis,
	make_travis_deploy_conda,
	)
from .docs import (
	copy_docs_styling,
	ensure_doc_requirements,
	make_404_page,
	make_conf,
	make_docs_building_rst,
	make_docs_source_rst,
	make_rtfd,
	rewrite_docs_index
)
from .gitignore import make_gitignore
from .linting import lint_belligerent_list, lint_fix_list, lint_warn_list, make_lint_roller, make_pylintrc, code_only_warning
from .packaging import make_manifest, make_pkginfo, make_setup
from .readme import rewrite_readme
from .templates import template_dir
from .testing import ensure_tests_requirements, make_isort, make_tox, make_yapf
from .utils import clean_writer
from domdf_python_tools.utils import enquote_value
from .yaml_parser import parse_yaml

__all__ = [
		"GitHelper",
		"ensure_bumpversion",
		"make_issue_templates",
		"make_contributing_md",
		"files",
		]


class GitHelper:
	"""
	Git Helper: Manage configuration files with ease.

	:param target_repo: The path to the root of the repository to manage files for.
	"""

	def __init__(self, target_repo: Union[str, pathlib.Path, os.PathLike]):
		self.target_repo = pathlib.Path(target_repo)
		self.templates = jinja2.Environment(
				loader=jinja2.FileSystemLoader(str(template_dir)),
				undefined=jinja2.StrictUndefined,
				)
		self.load_settings()

	def load_settings(self) -> None:
		"""
		Load settings from the ``git_helper.yml`` file in the repository.
		"""

		config_vars = parse_yaml(self.target_repo)
		self.templates.globals.update(config_vars)
		self.templates.globals["lint_fix_list"] = lint_fix_list
		self.templates.globals["lint_belligerent_list"] = lint_belligerent_list
		self.templates.globals["lint_warn_list"] = lint_warn_list
		self.templates.globals["code_only_warning"] = code_only_warning
		self.templates.globals["enquote_value"] = enquote_value
		self.templates.globals["len"] = len

	@property
	def exclude_files(self) -> List[str]:
		"""
		:return: a list of excluded files that should **NOT** be managed by Git Helper.
		"""

		return self.templates.globals["exclude_files"]

	@property
	def repo_name(self) -> str:
		"""
		:return: the name of the repository being managed.
		:rtype: str
		"""
		return self.templates.globals["repo_name"]

	def run(self) -> List[str]:
		"""
		Run Git Helper for the repository and update all managed files.

		:return: A list of files managed by Git Helper, regardless of whether they were added,
			removed or modified.
		"""

		if not self.templates.globals["preserve_custom_theme"] and self.templates.globals["enable_docs"] :
			all_managed_files = copy_docs_styling(self.target_repo, self.templates)
		else:
			all_managed_files = []

		# TODO: this isn't respecting "enable_docs"
		for function_, exclude_name, other_requirements in files:
			if exclude_name not in self.exclude_files and all([
					self.templates.globals[req] for req in other_requirements
					]):
				output_filenames = function_(self.target_repo, self.templates)

				for filename in output_filenames:
					all_managed_files.append(str(filename))

		all_managed_files.append("git_helper.yml")

		return all_managed_files


def ensure_bumpversion(repo_path: pathlib.Path, templates: jinja2.Environment) -> List[str]:
	"""
	Add configuration for ``bumpversion`` to the desired repo
	https://pypi.org/project/bumpversion/

	:param repo_path: Path to the repository root.
	:param templates:
	:type templates: jinja2.Environment
	"""

	bumpversion_file = repo_path / ".bumpversion.cfg"

	if not bumpversion_file.is_file():
		with bumpversion_file.open("w") as fp:
			fp.write(
					f"""\
[bumpversion]
current_version = {templates.globals["version"]}
commit = True
tag = True

"""
					)

	bumpversion_contents = bumpversion_file.read_text()

	if not bumpversion_contents.endswith("\n\n"):
		with bumpversion_file.open("a") as fp:
			fp.write("\n")

	required_lines = [
			"[bumpversion:file:git_helper.yml]",
			"[bumpversion:file:__pkginfo__.py]",
			"[bumpversion:file:README.rst]",
			]

	if templates.globals["enable_docs"]:
		required_lines.append("[bumpversion:file:doc-source/index.rst]")


	if templates.globals["py_modules"]:
		for modname in templates.globals["py_modules"]:
			required_lines.append(f"[bumpversion:file:{templates.globals['source_dir']}{modname}.py]")
	else:
		required_lines.append(f"[bumpversion:file:{templates.globals['source_dir']}{templates.globals['import_name']}/__init__.py]")

	for line in required_lines:
		if line not in bumpversion_contents:
			with bumpversion_file.open("a") as fp:
				fp.write(line)
				fp.write("\n\n")

	return [".bumpversion.cfg"]


def make_issue_templates(repo_path: pathlib.Path, templates: jinja2.Environment) -> List[str]:
	"""
	Add issue templates for GitHub to the desired repo

	:param repo_path: Path to the repository root.
	:param templates:
	:type templates: jinja2.Environment
	"""

	bug_report = templates.get_template("bug_report.md")
	feature_request = templates.get_template("feature_request.md")

	issue_template_dir = repo_path / ".github" / "ISSUE_TEMPLATE"
	maybe_make(issue_template_dir, parents=True)

	with (issue_template_dir / "bug_report.md").open("w") as fp:
		clean_writer(bug_report.render(), fp)

	with (issue_template_dir / "feature_request.md").open("w") as fp:
		clean_writer(feature_request.render(), fp)

	return [
			os.path.join(".github", "ISSUE_TEMPLATE", "bug_report.md"),
			os.path.join(".github", "ISSUE_TEMPLATE", "feature_request.md"),
			]


def make_contributing_md(repo_path: pathlib.Path, templates: jinja2.Environment) -> List[str]:
	"""
	Add CONTRIBUTING.md to the desired repo

	:param repo_path: Path to the repository root.
	:param templates:
	:type templates: jinja2.Environment
	"""

	contributing = templates.get_template("CONTRIBUTING.md")

	with (repo_path / "CONTRIBUTING.md").open("w") as fp:
		clean_writer(contributing.render(), fp)

	return [os.path.join("CONTRIBUTING.md")]


files: List[Tuple[Callable, str, Sequence[str]]] = [
		(make_copy_pypi_2_github, "copy_pypi_2_github", ["enable_releases"]),
		(make_lint_roller, "lint_roller", []),
		(make_stale_bot, "stale_bot", []),
		(make_auto_assign_action, "auto_assign", []),
		(rewrite_readme, "readme", []),
		(rewrite_docs_index, "index.rst", ["enable_docs"]),
		(ensure_doc_requirements, "doc_requirements", ["enable_docs"]),
		(make_pylintrc, "pylintrc", []),
		(make_manifest, "manifest", []),
		(make_setup, "setup", []),
		(make_pkginfo, "pkginfo", []),
		(make_conf, "conf", ["enable_docs"]),
		(make_gitignore, "gitignore", []),
		(make_rtfd, "rtfd", ["enable_docs"]),
		(make_travis, "travis", []),
		(make_github_ci, "actions", []),
		(make_tox, "tox", []),
		(make_yapf, "yapf", []),
		(ensure_tests_requirements, "test_requirements", ["enable_tests"]),
		(make_dependabot, "dependabot", []),
		(make_imgbot, "imgbot", []),
		(make_github_octocheese, "octocheese", []),
		(make_travis_deploy_conda, "travis_deploy_conda", ["enable_conda"]),
		(make_make_conda_recipe, "make_conda_recipe", ["enable_conda"]),
		(ensure_bumpversion, "bumpversion", []),
		(make_issue_templates, "issue_templates", []),
		(make_404_page, "404", ["enable_docs"]),
		(make_docs_source_rst, "Source_rst", ["enable_docs"]),
		(make_github_docs_test, "docs_action", ["enable_docs"]),
		(make_docs_building_rst, "Building_rst", ["enable_docs"]),
		(make_contributing_md, "contributing", []),
		(make_isort, "isort", []),  # Must always run last
		]
