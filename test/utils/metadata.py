def compare_metadata(actual_value, expected_value):
    """Compares the installed metadata against an expected value, ignoring attributes that have no importance for the
    testsuite"""
    # Test JSON metadata
    ignore_keys = [
        "install_time",
    ]
    # Exclude those keys from the comparison, but ensure they are defined
    for k in ignore_keys:
        del actual_value[k]

    return actual_value == expected_value
