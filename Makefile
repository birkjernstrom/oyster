.PHONY: clean-pyc test lint

all:
	clean-pyc test

test:
	python tests.py


clean-pyc:
	echo 'Cleaning .pyc files'
	$(shell find * -name "*.pyc" | xargs rm -rf)

lint:
	-pyflakes src/
