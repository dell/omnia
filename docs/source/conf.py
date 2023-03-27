# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import contextlib
import datetime
import io
import os
import subprocess


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Omnia'
copyright = '2023, Dell Technologies'
author = 'dellhpc/omnia'
release = '1.4.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_static_path = ['_static']

root_doc = 'index'

# -- Custom directives to generate documentation -----------------------------
# ref: https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html
#
# We define custom directives to help us generate documentation using Python on
# demand when referenced from our documentation files.
#

# Create a temp instance of JupyterHub for use by two separate directive classes
# to get the output from using the "--generate-config" and "--help-all" CLI
# flags respectively.
#



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'bizstyle'
html_logo = "images/omnia-logo-transparent.png"
html_title = 'Omnia'
#html_style = 'css/override.css'

html_theme_options = {
    'logo_only': True,
    "rightsidebar": False
}

html_sidebars = {
   '**': ['globaltoc.html', 'sourcelink.html', 'searchbox.html']
}





