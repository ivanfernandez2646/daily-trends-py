import pytest

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.users.domain.value_objects import (
    UserEmail,
    UserPassword,
    UserPasswordHash,
)


def test_user_email_is_trimmed_and_lowercased() -> None:
    assert UserEmail("  Admin@Example.com ").value == "admin@example.com"


@pytest.mark.parametrize(
    "value",
    [
        "admin.example.com",
        "admin@@example.com",
        "ad@min@example.com",
        "@example.com",
        "admin@example",
        "admin@example..com",
        "admin@.example.com",
        "admin@example.com.",
        "",
        "   ",
    ],
)
def test_user_email_rejects_an_invalid_value_showing_it_as_received(value: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        UserEmail(value)

    assert str(error.value) == f"<UserEmail> does not allow the value <{value}>"


def test_user_email_rejects_a_value_that_is_not_a_string() -> None:
    with pytest.raises(InvalidArgumentError) as error:
        UserEmail(42)  # pyright: ignore[reportArgumentType]

    assert str(error.value) == "<UserEmail> does not allow the value <42>"


def test_user_password_accepts_twelve_characters() -> None:
    assert UserPassword("a" * 12).value == "a" * 12


def test_user_password_rejects_fewer_than_twelve_characters_without_showing_them() -> None:
    with pytest.raises(InvalidArgumentError) as error:
        UserPassword("shortsecret")

    assert str(error.value) == "<UserPassword> must have at least 12 characters"
    assert "shortsecret" not in str(error.value)


@pytest.mark.parametrize(
    "secret",
    [UserPassword("a-long-enough-secret"), UserPasswordHash("a-long-enough-secret")],
)
def test_secrets_never_show_their_value_in_their_repr(
    secret: UserPassword | UserPasswordHash,
) -> None:
    assert "a-long-enough-secret" not in repr(secret)
