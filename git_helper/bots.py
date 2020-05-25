#  !/usr/bin/env python
#   -*- coding: utf-8 -*-
#
#  bots.py
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
import shutil

# 3rd party
from domdf_python_tools.paths import maybe_make

# this package
from .templates import template_dir
from .utils import clean_writer

__all__ = ["make_dependabot", "make_auto_assign_action", "make_stale_bot"]


def make_stale_bot(repo_path, templates):
	"""
	Add configuration for ``stale`` to the desired repo

	https://probot.github.io/apps/stale/

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	dot_github = repo_path / ".github"
	maybe_make(dot_github)
	shutil.copy2(template_dir / "stale_bot.yaml", dot_github / "stale.yml")


def make_auto_assign_action(repo_path, templates):
	"""
	Add configuration for ``auto-assign`` to the desired repo

	https://github.com/kentaro-m/auto-assign

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	dot_github = repo_path / ".github"
	maybe_make(dot_github / "workflow", parents=True)

	with (dot_github / "workflow" / "assign.yml").open("w") as fp:
		clean_writer("""# This file is managed by `git_helper`. Don't edit it directly

name: 'Auto Assign'
on: pull_request

jobs:
  add-reviews:
    runs-on: ubuntu-latest
    steps:
      - uses: kentaro-m/auto-assign-action@v1.1.0
        with:
          repo-token: "${{ secrets.GITHUB_TOKEN }}"
""", fp)

	with (dot_github / "auto_assign.yml").open("w") as fp:
		clean_writer(f"""# This file is managed by `git_helper`. Don't edit it directly

# Set to true to add reviewers to pull requests
addReviewers: true

# Set to true to add assignees to pull requests
addAssignees: true

# A list of reviewers to be added to pull requests (GitHub user name)
reviewers:
  - {templates.globals['username']}

# A number of reviewers added to the pull request
# Set 0 to add all the reviewers (default: 0)
numberOfReviewers: 0

# A list of assignees, overrides reviewers if set
# assignees:
#   - assigneeA

# A number of assignees to add to the pull request
# Set to 0 to add all of the assignees.
# Uses numberOfReviewers if unset.
# numberOfAssignees: 2

# A list of keywords to be skipped the process that add reviewers if pull requests include it
# skipKeywords:
#   - wip

# more settings at https://github.com/marketplace/actions/auto-assign-action
""", fp)


def make_dependabot(repo_path, templates):
	"""
	Add configuration for ``dependabot`` to the desired repo

	https://dependabot.com/

	:param repo_path: Path to the repository root
	:type repo_path: pathlib.Path
	:param templates:
	:type templates: jinja2.Environment
	"""

	dependabot_dir = repo_path / ".dependabot"
	maybe_make(dependabot_dir)

	with (dependabot_dir / "config.yml").open("w") as fp:
		clean_writer(f"""# This file is managed by `git_helper`. Don't edit it directly

version: 1
update_configs:
  - package_manager: "python"
    directory: "/"
    update_schedule: "weekly"
    default_reviewers:
      - "{templates.globals['username']}"
""", fp)
