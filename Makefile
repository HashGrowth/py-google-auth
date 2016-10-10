init:
	pip install -r requirements.txt

test:
	py.test tests

coverage:
	py.test --verbose --cov-report term --cov=py_google_auth tests

ci: init
	py.test --junitxml=junit.xml

publish:
	python setup.py sdist
	python setup.py bdist_wheel
	twine upload -r pypitest dist/*
	rm -rf build dist .egg py_google_auth.egg-info
