Omnia Documentation
-------------------

The Omnia docs are hosted here: https://omnia-documentation.readthedocs.io/en/latest/index.html and are written in reStructuredText (`.rst`).

Building Docs
--------------

* Clone this project

* Install or update sphinx (See: https://pip.readthedocs.io/) ::

    pip install sphinx

or::

   pip install sphinx --upgrade


* Install ReadTheDocs theme::

   pip install sphinx_rtd_theme


* Build the Docs::

   cd omnia/docs
   make html


* View the documentation by pointing a browser to: `omnia/docs/build/html/index.html`