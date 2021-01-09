# -*- coding: utf-8 -*-
"""Sphinx configuration."""
from __future__ import absolute_import, print_function, unicode_literals
from datetime import datetime


project = "mock-alchemy"
author = "Rajiv Sarvepalli"
copyright = f"{datetime.now().year}, {author}"
version = "0.1.0"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]
html_static_path = ["_static"]
copybutton_prompt_text = r">>> |\$ |\.\.\. "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = False

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": "https://github.com/rajivsarvepalli/mock-alchemy",
    "show_prev_next": False,
}

html_css_files = [
    "css/getting_started.css",
    "css/pandas.css",
]
