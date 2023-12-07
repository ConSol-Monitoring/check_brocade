.PHONY: all clean test

all: check_brocade

check_brocade:
	mkdir build
	cp -av checkbrocade build/checkontap
	mv build/checkbrocade/cli.py build/__main__.py
	( cd build/; python -m zipapp -c --output ../check_brocade -p '/usr/bin/env python3' . )
	rm -rf build

dist: pyproject.toml
	python3 -m build
	chmod a+r dist/*

.PHONY: clean
clean:
	rm -rf build allinone check_brocade zip check_brocade.zip build check_brocade.egg-info dist

.PHONY: upload-test
upload-test: dist
	python3 -m twine upload --repository testpypi dist/*

.PHONY: upload-prod
upload-prod: dist
	python3 -m twine upload dist/*