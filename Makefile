.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr pip-wheel-metadata
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	rm -fr Pipfile.lock

.PHONY: clean-docs
clean-docs:
	rm -fr site/

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.DS_Store' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	rm -fr .tox/
	rm -f .coverage
	find . -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	find . -name 'log.txt' -exec rm -fr {} +
	find . -name 'log.*.txt' -exec rm -fr {} +

.PHONY: lint
lint:
	black packages
	isort packages
	flake8 packages
	darglint packages

.PHONY: pylint
pylint:
	pylint -j4 packages

.PHONY: static
static:
	mypy packages --disallow-untyped-defs

v := $(shell pip -V | grep virtualenvs)

.PHONY: new_env
new_env: clean
	if [ ! -z "$(which svn)" ];\
	then\
		echo "The development setup requires SVN, exit";\
		exit 1;\
	fi;\
	if [ -z "$v" ];\
	then\
		pipenv --rm;\
		pipenv --python 3.8;\
		pipenv install --dev --skip-lock;\
		svn export https://github.com/valory-xyz/open-aea.git/trunk/packages/open_aea packages/open_aea;\
		echo "Enter virtual environment with all development dependencies now: 'pipenv shell'.";\
	else\
		echo "In a virtual environment! Exit first: 'exit'.";\
	fi
