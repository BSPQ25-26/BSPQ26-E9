# Configuration file for the Sphinx documentation builder.
project = 'Wallabot'
copyright = '2026, BSPQ26-E9'
author = 'BSPQ26-E9 Team'
release = '3.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'myst_parser',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '_generated']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']

html_theme_options = {
    'navigation_depth': 4,
    'sticky_navigation': True,
    'titles_only': False,
    'logo_only': False,
}

myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'tasklist',
]
