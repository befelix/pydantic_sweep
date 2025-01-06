# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= --jobs 2 -b html
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build/html

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
build: Makefile
	@$(SPHINXBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

auto:
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O) --ignore autoapi

clean: Makefile
	@rm -rf "$(BUILDDIR)" autoapi jupyter_execute _build $(O)
