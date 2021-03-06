The ElectrumSV documentation
============================

This directory contains two different projects, the ElectrumSV web site and the standalone
documentation.

The web site
------------

This uses the `Pelican static site generator <https://blog.getpelican.com/>`_ to produce
a fully updated deployment of the ElectrumSV web site.

Before you can generate the documentation you need to install the dependencies.

Windows::

    cd docs\website
    py -3.7 -m pip install pelican

MacOS/Linux::

    cd docs/website
    python3.7 -m pip install pelican

To develop the documentation with the aid of a web browser, you can generate it in-place after
making local changes. The built documentation should not be checked in.

Windows::

    cd docs\website
    pelican -s pelicanconf.py

MacOS/Linux::

    cd docs/website
    pelican -s pelicanconf.py

The generated web site will be available in the ``output`` sub-directory. You can
navigate here and open ``index.html``.

The standalone documentation
----------------------------

This uses the `Sphinx documentation generator <https://www.sphinx-doc.org/en/master/>`_ in
combination with the `Read the docs theme <https://sphinx-rtd-theme.readthedocs.io/en/stable/>`_
to produce HTML-based documentation.

Before you can generate the documentation you need to install the dependencies.

Windows::

    cd docs\standalone
    py -3.7 -m pip install -r requirements.txt

MacOS/Linux::

    cd docs/standalone
    python3.7 -m pip install -r requirements.txt

To develop the documentation with the aid of a web browser, you can generate it in-place after
making local changes. The built documentation should not be checked in.

Windows::

    cd docs\standalone
    make html

MacOS/Linux::

    cd docs/standalone
    make html

The generated documentation will be available in the ``_build\html`` sub-directory. You can
navigate here and open ``index.html``.
