# What is Orchestra?

Orchestra is a meta build system. 
Its job is to automate the repetitive tasks required to build a complex 
software project with many dependencies.

## How does it work?

TODO - write about:
* fundamental concepts (components, builds, dependencies) 
* actions (clone, configure, install)
* binary archives
* "root portability" (rpath, etc)
* usage examples
* integration with git

## Configuring Orchestra

See the documentation in `/docs`.

## Usage

TODO - document Orchestra usage

## Installing

```bash
python setup.py bdist_wheel
pip install --user dist/orchestra*.whl
```

## Development setup

Creating a dedicated virtualenv is highly suggested

```bash
python3 -m venv virtualenv
. ./virtualenv/bin/activate
python setup.py develop
```
