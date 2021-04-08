# Orchestra testsuite

## How to run the tests

Make sure you have installed the development requirements:
```
pip install -r dev_requirements.txt
```

You can run the whole testsuite with
```
python -m pytest test
```

Or select specific tests with the `-k` option
```
python -m pytest -k some_test_name test
```

## Custom helpers and fixtures

Some custom fixtures provide useful features:

- orchestra: this fixture provides an OrchestraShim object.
  It manages the configuration used by orchestra, creating a temporary copy and registering an upstream git repository.
  It has convenience properties pointing to various paths, methods for adding patches to the configuration, remotes,
  binary archives.
  It can simulate calling orchestra as if it was called on the cmdline by calling the OrchestraShim object:
  ```
  def test_something(orchestra: OrchestraShim):
      # equivalent to invoking `orchestra install -b some_component` on the cmdline
      orchestra("install", "-b", "some_compoent")
  ```

- test_data_mgr: provides a TestDataManager object.
  Use it to create copies of a folder from the test source directory to a tmpdir.

- git_repos_manager: provides a GitReposManager object.
  Use it to make temporary clones or empty repositories.

Some convenience helpers for doing common stuff (e.g. invoking various git commands) are available in the `utils` 
module.

## Test data

Before a test function is run, `pytest` instantiates the required fixtures.
The `orchestra` fixture will search for a `data/orchestra` directory starting from the directory containing the test 
module being executed and going up the filesystem hierarchy up to the `test` directory.

This allows you to have a specific configuration for the tests that require it, or to share the same configuration
where this is not needed.

## How to add a test

The easiest way is to copy an already existing test. File and function names must begin with `test_`.
Relative imports are recommended, so be sure to place your test in a proper module (having an `__init__.py` file in
its containing folder).
