from app.core.config import get_settings


def test_tests_use_my_blog_test_database():
    assert get_settings().database_url.endswith("/my_blog_test")
