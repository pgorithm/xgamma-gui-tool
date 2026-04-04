"""Single source for the application version string.

Git/source trees use "dev". Release DEB builds replace this value via CI
(see .github/workflows/build-deb.yml) so the About dialog matches the package.
"""

__version__ = "dev"
