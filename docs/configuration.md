# Configuring Orchestra

This document explains the yaml format natively understood by Orchestra.

The configuration is actually preprocessed using [ytt](https://get-ytt.io/), 
allowing to factor repetitive parts, provide user options, and so on.

When invoked Orchestra will look for a `.orchestra` directory 
in the current directory or one or the parent ones (like git).
To start out it's enough to create a file in `.orchestra/configuration.yml`.

The `.orchestra` directory should be (or be placed inside) a git repository.
To use binary archives files under `.orchestra/binary_archives` should be 
managed by git-lfs. It is possible to use a different repository for 
that directory, e.g. using git submodules.

## Components and builds

Components must have at least one build. 
The main properties of a build are the configure and install scripts.
A component can have multiple builds, for instance for 
enabling different optimization levels. 

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
* `repository`: name of the repository to clone to get the project sources
* `default_build`: name of the default build. If not specified the first build in alphabetic order is picked.
* `add_to_path`: string prepended to $PATH. See the "Additional environment and PATH" section.
* `skip_post_install`: If true, Orchestra will skip the post install phase (RPATH adjustment, etc) 

### Build properties

**configure** (mandatory)
 
This script usually performs the following:
 
* downloads sources tarball to `$SOURCE_ARCHIVES` (if the component does not specify a repository)
* extracts sources to `$SOURCE_DIR` or `$BUILD_DIR` (if the component does not specify a repository)
    * `$BUILD_DIR` should be used for in-tree builds
* configuring the project (e.g. running `./configure`)

The script **must** create the directory `$BUILD_DIR`, as Orchestra considers the configure action
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
                    - component_a              # require the default build of `component_a`
                    - component_b@build_name   # require the build `build_name` of `component_b`
                    - component_c~build_name   # require any build of `component_c`, preferring `build_name`.
                build_dependencies:
                    - gcc_component            # Compiler is required only to build the component
```

## Environment variables and configurable paths
<a name="env-and-dirs"></a>

The following environment variables will be available to the shell scripts.
They are made available by inserting a prelude that performs `export VARIABLE="VALUE"`.
The value is purposefully not escaped, so that it can, for instance, expand other variables (`$OTHERVARIABLE`).
However, most variables need absolute paths if overridden.  

**ORCHESTRA_DOTDIR**

Orchestra configuration directory.

**ORCHESTRA_ROOT**

Orchestra root directory. 
Default value: `$ORCHESTRA_DOTDIR/../root`.
Overridable using the `paths.orchestra_root` setting by specifying an absolute path.

**SOURCE_ARCHIVES**

Directory containing cached source archives. 
Default value: `$ORCHESTRA_DOTDIR/source_archives`.
Overridable using the `paths.source_archives` setting by specifying an absolute path.

**BINARY_ARCHIVES**

Directory containing cached binary archives. 
Default value: `$ORCHESTRA_DOTDIR/binary_archives`.
Overridable using the `paths.binary_archives` setting by specifying an absolute path.

**SOURCES_DIR**

Directory where sources should be placed. Default value: `$ORCHESTRA_DOTDIR/../sources`.
Overridable using the `paths.sources_dir` setting by specifying an absolute path.
Not meant to be used directly, use `SOURCE_DIR`.

**BUILDS_DIR**

Directory where builds should be placed. Default value: `$ORCHESTRA_DOTDIR/../build`.
Overridable using the `paths.builds_dir` setting by specifying an absolute path.
Not meant to be used directly, use `BUILD_DIR`.

**SOURCE_DIR**

Per-component directory where sources should be placed. 
Value: `$SOURCES_DIR/<sanitized_component_name>/`. 

**BUILD_DIR**
Per-build directory where build artifacts should be placed.
Value: `$BUILDS_DIR/<sanitized_component_name>/<sanitized_build_name>`.

**TMP_ROOTS**

Directory containing the temporary roots, where the built components should be installed.
Default value: `$ORCHESTRA_DOTDIR/tmproot` by specifying an absolute path.
Overridable using the `paths.tmproot` setting.

**TMP_ROOT** and **DESTDIR**

Per-component temporary root directory where the built component should be installed.
Value: `$TMP_ROOTS/<sanitized_build_and_component_name>`.

The files installed to `TMP_ROOT` will be indexed 
and moved automatically by Orchestra to the "true" root.

`DESTDIR` is only set during the install phase.

## Additional environment and PATH

Additional environment variables can be exported by adding 
an element to the `environment` root key of the configuration.
The variables will be evaluated in order.

Example:
```yaml
components:
    ...
environment:
    - VARIABLE_NAME: value
    - ANOTHER_VARIABLE_NAME: "Expand another variable: $VARIABLE_NAME"
``` 

It is also possible to prepend components to the PATH variable, 
by specifying `add_to_path` in the root configuration or in a component:

```yaml
components:
    my_component:
        add_to_path: $ORCHESTRA_ROOT/opt/mycomponent/bin/
        ...
add_to_path: 
    - $ORCHESTRA_ROOT/bin
```

All `add_to_path` directives will be applied regardless of 
where they are specified, even if the component is not installed.

# Binary archives

# Repository cloning

Document how the remote is picked, etc.
