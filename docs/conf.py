# Configuration file for the Sphinx documentation builder.
# Full list of options: https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
project = "ISO-DART"
copyright = "2024, Lawrence Livermore National Laboratory"
author = "Pedro Sotorrio, Thomas Edmunds, Amelia Musselman, Chih-Che Sun"
version = "2.0.0"
release = "2.0.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Auto-generate docs from docstrings
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "sphinx.ext.viewcode",  # Add links to highlighted source code
    "sphinx.ext.intersphinx",  # Link to other project's documentation
    "sphinx.ext.autosummary",  # Generate autodoc summaries
    "sphinx.ext.todo",  # Support for todo items
    "sphinx.ext.coverage",  # Documentation coverage checker
    "sphinx.ext.githubpages",  # Create .nojekyll file for GitHub Pages
    "myst_parser",  # Markdown support
    "sphinx_design",  # Design elements (grids, cards, tabs)
    "sphinx_copybutton",  # Add copy button to code blocks
]

# MyST (Markdown) configuration
myst_enable_extensions = [
    "colon_fence",  # ::: fence syntax
    "deflist",  # Definition lists
    "tasklist",  # Task lists
    "fieldlist",  # Field lists
    "attrs_inline",  # Inline attributes
    "attrs_block",  # Block attributes
]

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Autosummary settings
autosummary_generate = True

# Template settings
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]

# The master document
master_doc = "index"

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Theme options for sphinx_rtd_theme
html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "style_nav_header_background": "#2980B9",
    # Toc options
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Custom CSS
html_css_files = [
    "custom.css",
]

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ["_static"]

# Custom sidebar templates
html_sidebars = {
    "**": [
        "globaltoc.html",
        "relations.html",
        "sourcelink.html",
        "searchbox.html",
    ]
}

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = '_static/logo.png'

# The name of an image file (within the static path) to use as favicon
# html_favicon = '_static/favicon.ico'

# If true, "Created using Sphinx" is shown in the HTML footer
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer
html_show_copyright = True

# Output file base name for HTML help builder
htmlhelp_basename = "ISODARTdoc"

# -- Options for LaTeX output ------------------------------------------------
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
    "preamble": "",
    "figure_align": "htbp",
}

# Grouping the document tree into LaTeX files
latex_documents = [
    (
        master_doc,
        "ISODART.tex",
        "ISO-DART Documentation",
        "Lawrence Livermore National Laboratory",
        "manual",
    ),
]

# -- Options for manual page output ------------------------------------------
man_pages = [(master_doc, "isodart", "ISO-DART Documentation", [author], 1)]

# -- Options for Texinfo output ----------------------------------------------
texinfo_documents = [
    (
        master_doc,
        "ISODART",
        "ISO-DART Documentation",
        author,
        "ISODART",
        "Independent System Operator Data Automated Request Tool.",
        "Miscellaneous",
    ),
]

# -- Options for Epub output -------------------------------------------------
epub_title = project
epub_exclude_files = ["search.html"]

# -- Extension configuration -------------------------------------------------

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Todo configuration
todo_include_todos = True


# -- Custom setup ------------------------------------------------------------
def setup(app):
    """Custom Sphinx setup."""
    # Add custom CSS
    app.add_css_file("custom.css")
