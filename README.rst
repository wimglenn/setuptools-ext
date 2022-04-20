|pypi|_ |pyversions|_ |actions|_ |codecov|_ |womm|_

.. |pypi| image:: https://img.shields.io/pypi/v/setuptools-ext.svg
.. _pypi: https://pypi.org/project/setuptools-ext

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/setuptools-ext.svg
.. _pyversions:

.. |actions| image:: https://github.com/wimglenn/setuptools-ext/actions/workflows/tests.yml/badge.svg
.. _actions: https://github.com/wimglenn/setuptools-ext/actions/workflows/tests.yml/

.. |codecov| image:: https://codecov.io/gh/wimglenn/setuptools-ext/branch/master/graph/badge.svg
.. _codecov: https://codecov.io/gh/wimglenn/setuptools-ext

.. |womm| image:: https://cdn.rawgit.com/nikku/works-on-my-machine/v0.2.0/badge.svg
.. _womm: https://github.com/nikku/works-on-my-machine

setuptools-ext
==============

This is a `PEP 517 Build backend interface`_ supporting fields in the `Core metadata specifications`_ which are otherwise difficult to provide using existing tools.
Specifically, it allows declaring those fields marked with an "—" in the rightmost column of the table below by specifying them in a ``[tool.setuptools-ext]`` section of ``pyproject.toml``.
The backend otherwise functions identically to ``setuptools.build_meta``, and is in fact a drop-in replacement for the default setuptools build backend.

Setuptools_ lacks a way to specify some fields, despite their validity in Python package metadata according to the spec.
`PEP 621 – Storing project metadata in pyproject.toml`_ appears to have punted on some of the fields too.

+-----------------------------------+-------------------------------+---------------------------------+
| Field                             | setup.py keyword              | pyproject.toml name             |
+===================================+===============================+=================================+
| Name                              | name                          | name                            |
+-----------------------------------+-------------------------------+---------------------------------+
| Version                           | version                       | version                         |
+-----------------------------------+-------------------------------+---------------------------------+
| Dynamic (multiple use)            | —                             | dynamic                         |
+-----------------------------------+-------------------------------+---------------------------------+
| Platform (multiple use)           | platforms                     | —                               |
+-----------------------------------+-------------------------------+---------------------------------+
| Supported-Platform (multiple use) | —                             | —                               |
+-----------------------------------+-------------------------------+---------------------------------+
| Summary                           | description                   | description                     |
+-----------------------------------+-------------------------------+---------------------------------+
| Description                       | long_description              | readme                          |
+-----------------------------------+-------------------------------+---------------------------------+
| Description-Content-Type          | long_description_content_type | readme                          |
+-----------------------------------+-------------------------------+---------------------------------+
| Keywords                          | keywords                      | keywords                        |
+-----------------------------------+-------------------------------+---------------------------------+
| Home-page                         | url                           | [project.urls]                  |
+-----------------------------------+-------------------------------+---------------------------------+
| Download-URL                      | download_url                  | —                               |
+-----------------------------------+-------------------------------+---------------------------------+
| Author                            | author                        | authors                         |
+-----------------------------------+-------------------------------+---------------------------------+
| Author-email                      | author_email                  | authors                         |
+-----------------------------------+-------------------------------+---------------------------------+
| Maintainer                        | maintainer                    | maintainers                     |
+-----------------------------------+-------------------------------+---------------------------------+
| Maintainer-email                  | maintainer_email              | maintainers                     |
+-----------------------------------+-------------------------------+---------------------------------+
| License                           | license / license_files       | license                         |
+-----------------------------------+-------------------------------+---------------------------------+
| Classifier (multiple use)         | classifiers                   | classifiers                     |
+-----------------------------------+-------------------------------+---------------------------------+
| Requires-Dist (multiple use)      | install_requires              | dependencies                    |
+-----------------------------------+-------------------------------+---------------------------------+
| Requires-Python                   | python_requires               | requires-python                 |
+-----------------------------------+-------------------------------+---------------------------------+
| Requires-External (multiple use)  | —                             | —                               |
+-----------------------------------+-------------------------------+---------------------------------+
| Project-URL (multiple-use)        | project_urls                  | [project.urls]                  |
+-----------------------------------+-------------------------------+---------------------------------+
| Provides-Extra (multiple use)     | extras_require                | [project.optional-dependencies] |
+-----------------------------------+-------------------------------+---------------------------------+
| Provides-Dist (multiple use)      | —                             | —                               |
+-----------------------------------+-------------------------------+---------------------------------+
| Obsoletes-Dist (multiple use)     | —                             | —                               |
+-----------------------------------+-------------------------------+---------------------------------+

Reference links for the info above:

- Setuptools `keywords <https://setuptools.pypa.io/en/latest/references/keywords.html>`_ and |more_keywords|_
- `Declaring project metadata`_ in ``pyproject.toml``

Usage
-----

To offer a simple example, if you want to add a ``Supported-Platform`` and the ``Requires-External`` field three times, producing these lines in the ``.dist-info/METADATA`` file:

.. code-block::

   Supported-Platform: RedHat 8.3
   Requires-External: C
   Requires-External: libpng (>=1.5)
   Requires-External: make; sys_platform != "win32"

You would configure the tool like this in ``pyproject.toml``, specifying a build dependency on ``setuptools-ext`` and then adding the fields in a ``[tool.setuptools-ext]`` section:

.. code-block:: toml

   [build-system]
   requires = ["setuptools-ext"]
   build-backend = "setuptools_ext"

   ...

   [tool.setuptools-ext]
   supported-platform = [
       "RedHat 8.3",
   ]
   requires-external = [
       "C",
       "libpng (>=1.5)",
       'make; sys_platform != "win32"'
   ]

The metadata fields may then be consumed by automated tooling for building RPM packages with system dependencies, for example.

*Note:* This package does not `add new keyword arguments`_ to ``setup.py`` (that's out of scope for a PEP 517 build backend).

.. |more_keywords| replace:: New and Changed ``setup()`` Keywords

.. _PEP 517 Build backend interface: https://peps.python.org/pep-0517/#build-backend-interface
.. _Setuptools: https://setuptools.pypa.io/
.. _Core metadata specifications: https://packaging.python.org/en/latest/specifications/core-metadata/
.. _PEP 621 – Storing project metadata in pyproject.toml: https://peps.python.org/pep-0621/
.. _more_keywords: https://setuptools.pypa.io/en/latest/userguide/keywords.html
.. _Declaring project metadata: https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
.. _add new keyword arguments: https://setuptools.pypa.io/en/latest/userguide/extension.html#adding-setup-arguments
