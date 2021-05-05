# Development setup

## Installing

Creating a dedicated virtualenv is highly suggested

```bash
python3 -m venv virtualenv
. ./virtualenv/bin/activate
```

Install required dependencies
```
pip install -r requirements.txt
pip install -r dev_requirements.txt
```

Install orchestra in development mode, so local modifications will be immediately effective without reinstalling.

```
python setup.py develop
```

## Testing

### Prerequisites

To run the testsuite you need to either install orchestra (see previous section) or install its dependencies:

```
apt install tree python3-pygraphviz
```

You will also need the following dependencies:
```
apt install build-essential cmake make autoconf git git-lfs
```

### Running the testsuite

```
python -m pytest test
```

## Pre-commit hooks

Orchestra uses pre-commit to manage its pre-commit hooks. Do the following to set them up:

```
pip install pre-commit
pre-commit install
```
