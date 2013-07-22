.PHONY: clean-pyc test lint docs clean-docs website

all:
	clean-pyc test

test:
	python tests.py

clean-pyc:
	echo 'Cleaning .pyc files'
	$(shell find * -name "*.pyc" | xargs rm -rf)

lint:
	-pyflakes src/

docs:
	$(MAKE) -C docs html

clean-docs:
	$(MAKE) -C docs clean

website:
	$(MAKE) clean-docs
	$(MAKE) docs
	rm -rf website/documentation/*
	cp -r docs/_build/html/* website/documentation/
	sphinxtogithub website/documentation
	python scripts/generate_website.py
