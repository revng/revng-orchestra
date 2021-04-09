# Configuring orchestra

This document explains the yaml format natively understood by orchestra. The configuration must conform to the schema
that can be found in `support/`.

The configuration is preprocessed using the [ytt](https://carvel.dev/ytt/) yaml templating tool, which allows factoring
repetitive parts, provide user-configurable options, and so on.

When invoked, orchestra will look for a `.orchestra` directory in the current directory or one or the parent ones
(like git). To start out it's enough to create a `.yml` file in `.orchestra/config/`, e.g. `configuration.yml`.

The `.orchestra` directory should be (or be placed inside) a git repository. To use binary archives files under
`.orchestra/binary_archives` should be managed by git-lfs. It is possible to use a different repository for that
directory, e.g. using git submodules.

## Components and builds

Components must have at least one build. The main properties of a build are the configure and install scripts.
A component can have multiple builds, which can for instance enable different optimization levels.

This is an example of a simple component:

```yaml
simple_component:
  builds:
    simple_build:
      configure: |
        wget -O "$SOURCE_ARCHIVES/simpleproject.tar.gz" https://simpleproject.org/simpleproject.tar.gz
        mkdir -p "$SOURCE_DIR" && cd "$SOURCE_DIR"
        tar xzf "$SOURCE_ARCHIVES/simpleproject.tar.gz"
        mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"
        "$SOURCE_DIR/configure" --option-1 --option-2
      install: |
        cd "$BUILD_DIR"
        make
        make install
```

All builds must specify at least the `configure` and `install` scripts.
The scripts are run using `bash` and can use [environment variables from this list](#env-and-dirs)

### Component properties

A component can specify the following properties:

* `builds` (mandatory): a dictionary of builds
* `default_build`: name of the default build. If not specified the first build in alphabetic order is picked.
* `license`: license filename. Will be copied to the root when installing a component. orchestra will search for it in
  $SOURCE_DIR and $BUILD_DIR
* `binary_archives`: name of the binary archive repository where the archives for this component will be created
* `repository`: name of the repository to clone to get the project sources
* `build_from_source`: if true, orchestra will always build this component (even if the binary archives are available)
* `skip_post_install`: If true, orchestra will skip the post install phase (RPATH adjustment, etc)
* `add_to_path`: list of strings that will be prepended to $PATH. See the "Additional environment and PATH" section.

### Build properties

**configure** (mandatory)

This script usually performs the following:

* downloads sources tarball to `$SOURCE_ARCHIVES` (if the component does not specify a repository)
* extracts sources to `$SOURCE_DIR` or `$BUILD_DIR` (if the component does not specify a repository)
    * `$BUILD_DIR` should be used for in-tree builds
* configuring the project (e.g. running `./configure`)

The script **must** create the directory `$BUILD_DIR`, as orchestra considers the configure action
satisfied if it exists.

**install** (mandatory)

This script should build and install the component to `$TMP_ROOT`.

**dependencies** and **build_dependencies**

Dependencies are specified independently for each build.

Two types of dependencies exist: normal and build-only.
Normal dependencies are required both to build and to run the component,
while build-only dependencies are not required to run the component
and will not be installed if the component is installed from binary archives.

Dependencies can be specified using three syntax variations:

Example:
```yaml
components:
  my_component:
    builds:
      my_build:
        configure: ...
        install: ...
        dependencies:
          - component_a              # require any build of `component_a`, preferring the default build
          - component_c~build_name   # require any build of `component_c`, preferring `build_name`
          - component_b@build_name   # require the build `build_name` of `component_b`
        build_dependencies:
          - gcc_component            # Compiler is required only to build the component
```

**ndebug**

Boolean, defaults to true.
Used to replace `#ifdef`-like macros referencing `NDEBUG`.

## Environment variables and configurable paths
<a name="env-and-dirs"></a>

The following environment variables will be available to the shell scripts. Paths are guaranteed to be absolute unless
otherwise specified.

**ORCHESTRA_DOTDIR**

orchestra configuration directory.

**ORCHESTRA_ROOT**

orchestra root directory.
Default value: `$ORCHESTRA_DOTDIR/../root`. Overridable using `paths.orchestra_root`.

**SOURCE_ARCHIVES**

Directory containing cached source archives.
Default value: `$ORCHESTRA_DOTDIR/source_archives`. Overridable using `paths.source_archives`.

**BINARY_ARCHIVES**

Directory containing cached binary archives.
Default value: `$ORCHESTRA_DOTDIR/binary_archives`. Overridable using `paths.binary_archives`.

**SOURCES_DIR**

Directory where sources should be placed.
Default value: `$ORCHESTRA_DOTDIR/../sources`. Overridable using `paths.sources_dir`.
Not meant to be used directly, use `SOURCE_DIR`.

**BUILDS_DIR**

Directory where builds should be placed.
Default value: `$ORCHESTRA_DOTDIR/../build`. Overridable using `paths.builds_dir`.
Not meant to be used directly, use `BUILD_DIR`.

**SOURCE_DIR**

Per-component directory where sources should be placed.
Value: `$SOURCES_DIR/<sanitized_component_name>/`.

**BUILD_DIR**
Per-build directory where build artifacts should be placed.
Value: `$BUILDS_DIR/<sanitized_component_name>/<sanitized_build_name>`.

**TMP_ROOTS**

Directory containing the temporary roots, where the built components should be installed.
Default value: `$ORCHESTRA_DOTDIR/tmproot`. Overridable using `paths.tmproot`.

**TMP_ROOT** and **DESTDIR**

Per-component temporary root directory where the built component should be installed.
Value: `$TMP_ROOTS/<sanitized_build_and_component_name>`.

The files installed to `TMP_ROOT` will be indexed and moved automatically by orchestra to the "true" root.

`DESTDIR` is only set for the install script.

**RUN_TESTS**

This variable will be set to `1` when orchestra is invoked with the `--test` option, otherwise it will be set to `0`.
Install scripts should run the project testsuite when `RUN_TESTS == 1`.

## Overriding orchestra default paths

A `paths` property can be placed at the configuration top-level to override orchestra defaults. Example:
```yaml
components: ...
paths:
  orchestra_root: ~/data/orchestra_root
```

The section above documents which yaml property corresponds to which path.

`$VAR`, `${VAR}`, and `~` are expanded. Variable expansions can only reference orchestra builtin variables or
preexisting environment variables, not custom ones. Relative paths will be evaluated relative to $ORCHESTRA_DOTDIR.

## Setting/unsetting environment variables and PATH

Environment variables can be set/unset by adding an element to the `environment` root key of the configuration.
The variables will be evaluated in order, top to bottom.

Example:
```yaml
components:
    ...
environment:
    - VARIABLE_NAME: value
    - ANOTHER_VARIABLE_NAME: "Expand another variable: $VARIABLE_NAME"
    #! This variable will be unset. Its value must be an empty string or orchestra will throw an error
    - "-UNSET_THIS_VARIABLE": ""
```

It is also possible to prepend components to the PATH variable, by specifying `add_to_path` in the root configuration or
in a component:

```yaml
components:
    my_component:
        add_to_path:
          - $ORCHESTRA_ROOT/opt/mycomponent/bin/
        ...
add_to_path:
    - $ORCHESTRA_ROOT/bin
```

All `add_to_path` directives will always be applied regardless of where they are specified, even if the component is
not installed.

# Binary archives

TODO

# Repository cloning

TODO: Document how the remote is picked, etc.
