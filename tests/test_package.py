import my_project


def test_version_is_defined():
    assert isinstance(my_project.__version__, str)
    assert my_project.__version__
