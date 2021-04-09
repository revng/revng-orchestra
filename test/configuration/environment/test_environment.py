from textwrap import dedent

from ...orchestra_shim import OrchestraShim

# Mapping from the name of a property in Configuration to the corresponding environment variable
configuration_property_name_to_environment = {
    "orchestra_dotdir": "ORCHESTRA_DOTDIR",
    "orchestra_root": "ORCHESTRA_ROOT",
    "source_archives": "SOURCE_ARCHIVES",
    "binary_archives_dir": "BINARY_ARCHIVES",
    "tmproot": "TMP_ROOTS",
    "sources_dir": "SOURCES_DIR",
    "builds_dir": "BUILDS_DIR",
}


def test_global_environment_paths(orchestra: OrchestraShim):
    """Checks that the global environment matches the paths accessible from Configuration properties"""
    config = orchestra.configuration
    env = config.global_env()

    for config_property_name, env_name in configuration_property_name_to_environment.items():
        assert env[env_name] == getattr(config, config_property_name)


def test_global_environment(orchestra: OrchestraShim):
    """Checks that the global environment contains the expected variables and values.
    This test does not check variables containing orchestra-defined paths, see other tests for those
    """
    config = orchestra.configuration
    env = config.global_env()

    # TODO: is there a better way to check these?
    expected_values = {
        "RPATH_PLACEHOLDER": "////////////////////////////////////////////////$ORCHESTRA_ROOT",
        "GIT_ASKPASS": "/bin/true",
    }
    for name, expected_value in expected_values.items():
        assert env.get(name) == expected_value


def test_user_can_override_environment_variables(orchestra: OrchestraShim):
    """Checks that the user configuration can set environment variables"""
    orchestra.set_environment_variable("ENV_VAR_A", "VAR_A_VALUE")
    env = orchestra.configuration.global_env()
    assert env["ENV_VAR_A"] == "VAR_A_VALUE"


def monkeypatch_action_script(action, new_script, monkeypatch_context):
    """Patches the script executed by `action`"""
    # HACK: since `script` is a class @property we can't change it at the instance level
    monkeypatch_context.setattr(action.__class__, "script", new_script)


def assert_script_succeeds_in_action_context(action, script, monkeypatch):
    """Runs the `script` in `action`'s context by monkeypatching the action to use it.
    Raises an exception if the script returns a nonzero exit code
    """
    with monkeypatch.context() as m:
        monkeypatch_action_script(action, script, m)
        action.run()


custom_variables_check_script = dedent(
    """        
    if [[ "$ENV_VAR_A" != "VAR_A_VALUE" ]] \
        || [[ "${ENV_VAR_B+defined}" == "defined" ]]
    then
        exit 1
    fi
    """
)


def assert_user_can_set_action_environment(action, orchestra: OrchestraShim, monkeypatch, script_suffix=""):
    """Asserts that the user can set environment variables passed to the script executed by `action`"""
    # Do not inline this, dedent breaks indentation if script_suffix contains newlines
    check_script = custom_variables_check_script + script_suffix
    with monkeypatch.context() as m:
        m.setenv("ENV_VAR_A", "ABC")
        m.setenv("ENV_VAR_B", "VAR_B_SHOULD_BECOME_UNSET")
        overlay1 = orchestra.set_environment_variable("ENV_VAR_A", "VAR_A_VALUE")
        overlay2 = orchestra.unset_environment_variable("ENV_VAR_B")

        # HACK: overriding variables at runtime requires updating the configuration referenced by the action
        m.setattr(action, "config", orchestra.configuration)

        assert_script_succeeds_in_action_context(action, check_script, m)

    # Cleanup
    orchestra.remove_overlay(overlay1)
    orchestra.remove_overlay(overlay2)


global_variables_check_script = dedent(
    """
    if [[ "$ORCHESTRA_DOTDIR" != "{config.orchestra_dotdir}" ]] \
        || [[ "$ORCHESTRA_ROOT" != "{config.orchestra_root}" ]] \
        || [[ "$SOURCE_ARCHIVES" != "{config.source_archives}" ]] \
        || [[ "$BINARY_ARCHIVES" != "{config.binary_archives_dir}" ]] \
        || [[ "$TMP_ROOTS" != "{config.tmproot}" ]] \
        || [[ "$SOURCES_DIR" != "{config.sources_dir}" ]] \
        || [[ "$BUILDS_DIR" != "{config.builds_dir}" ]]
    then
        exit 1
    fi
    """
)


def assert_action_has_correct_global_environment(action, orchestra: OrchestraShim, monkeypatch, script_suffix=""):
    """Asserts that the global environment variables are passed correctly to the script executed by the action"""
    config = orchestra.configuration
    check_script = global_variables_check_script + script_suffix
    assert_script_succeeds_in_action_context(action, check_script.format(config=config), monkeypatch)


def test_clone_environment(orchestra: OrchestraShim, monkeypatch):
    """Checks that the clone script gets executed in the expected environment.
    This means:
     - checking that the user can set and unset custom variables
     - checking that orchestra global variables have the expected value
     - checking that the clone-specific variables have the expected value
    """
    config = orchestra.configuration
    action = config.components["component_A"].clone

    assert_user_can_set_action_environment(action, orchestra, monkeypatch)
    assert_action_has_correct_global_environment(action, orchestra, monkeypatch)

    # Check clone-specific variables
    check_script = dedent(
        rf"""
        if [[ "$SOURCE_DIR" != "{action.source_dir}" ]]; then
            exit 1
        fi
        """
    )
    assert_script_succeeds_in_action_context(action, check_script, monkeypatch)


def test_configure_environment(orchestra: OrchestraShim, monkeypatch):
    """Checks that the configure script gets executed in the expected environment.
    This means:
     - checking that the user can set and unset custom variables
     - checking that orchestra global variables have the expected value
     - checking that the configure-specific variables have the expected value
    """
    config = orchestra.configuration
    action = config.components["component_A"].default_build.configure

    configure_script_suffix = 'mkdir -p "$BUILD_DIR"'

    assert_user_can_set_action_environment(action, orchestra, monkeypatch, script_suffix=configure_script_suffix)
    assert_action_has_correct_global_environment(action, orchestra, monkeypatch, script_suffix=configure_script_suffix)

    # Check configure-specific variables
    check_script = dedent(
        rf"""
        # Checks if ENV_VAR_B is undefined
        if [[ "$SOURCE_DIR" != "{action.source_dir}" ]] \
            || [[ "$BUILD_DIR" != "{action.build_dir}" ]] \
            || [[ "$TMP_ROOT" != "{action.tmp_root}" ]]
        then
            exit 1
        fi
        """
    )
    check_script += configure_script_suffix
    assert_script_succeeds_in_action_context(action, check_script, monkeypatch)


def test_install_environment(orchestra: OrchestraShim, monkeypatch):
    """Checks that the install script gets executed in the expected environment.
    This means:
     - checking that the user can set and unset custom variables
     - checking that orchestra global variables have the expected value
     - checking that the install-specific variables have the expected value
    """
    config = orchestra.configuration
    action = config.components["component_A"].default_build.install
    action.allow_build = True

    assert_user_can_set_action_environment(action, orchestra, monkeypatch)
    assert_action_has_correct_global_environment(action, orchestra, monkeypatch)

    # Check configure-specific variables
    check_script = dedent(
        rf"""
        # Checks if ENV_VAR_B is undefined
        if [[ "$SOURCE_DIR" != "{action.source_dir}" ]] \
            || [[ "$BUILD_DIR" != "{action.build_dir}" ]] \
            || [[ "$TMP_ROOT" != "{action.tmp_root}" ]] \
            || [[ "$DESTDIR" != "{action.tmp_root}" ]]
        then
            exit 1
        fi
        """
    )
    assert_script_succeeds_in_action_context(action, check_script, monkeypatch)


def test_shell_environment(orchestra: OrchestraShim, monkeypatch):
    """Checks that the scripts executed by `orchestra shell` have the expected environment"""
    config = orchestra.configuration

    # Check global variables have expected value
    orchestra("shell", "bash", "-c", global_variables_check_script.format(config=config))

    # Check the user config can set/unset variables
    with monkeypatch.context() as m:
        m.setenv("ENV_VAR_A", "ABC")
        m.setenv("ENV_VAR_B", "VAR_B_SHOULD_BECOME_UNSET")
        overlay1 = orchestra.set_environment_variable("ENV_VAR_A", "VAR_A_VALUE")
        overlay2 = orchestra.unset_environment_variable("ENV_VAR_B")
        orchestra("shell", "bash", "-c", custom_variables_check_script)

        # Cleanup
        orchestra.remove_overlay(overlay1)
        orchestra.remove_overlay(overlay2)
