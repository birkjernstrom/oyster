.PHONY: clean-pyc test lint

all:
	clean-pyc test

test:
	python tests/run.py


clean-pyc:
	echo 'Cleaning .pyc files'
	$(shell find * -name "*.pyc" | xargs rm -rf)

lint:
	-pyflakes sheldon/
