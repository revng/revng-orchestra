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

```
python -m pytest test
```

## Pre-commit hooks

Orchestra uses pre-commit to manage its pre-commit hooks. Do the following to set them up:

```
pip install pre-commit
pre-commit install
```
