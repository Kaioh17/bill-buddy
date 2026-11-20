import json
import logging

from app.core.logging import mask_email, setup_logging


def _our_handlers():
    return [h for h in logging.getLogger().handlers if getattr(h, "_billbuddy", False)]


def test_setup_is_idempotent():
    setup_logging("dev", "DEBUG")
    setup_logging("dev", "DEBUG")
    assert len(_our_handlers()) == 1


def test_dev_format_is_readable_with_extras(capsys):
    setup_logging("dev", "DEBUG")
    logging.getLogger("t").info("signup_ok", extra={"user_id": "u1"})
    err = capsys.readouterr().err
    assert "INFO" in err and "signup_ok" in err and "user_id=u1" in err
    assert not err.lstrip().startswith("{")


def test_prod_format_is_json(capsys):
    setup_logging("prod", "INFO")
    logging.getLogger("t").info("signup_ok", extra={"user_id": "u1"})
    line = capsys.readouterr().err.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["message"] == "signup_ok"
    assert data["user_id"] == "u1"
    assert "time" in data


def test_prod_json_includes_traceback(capsys):
    setup_logging("prod", "INFO")
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logging.getLogger("t").exception("boom")
    data = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert "ZeroDivisionError" in data["exc"]


def test_prod_hides_debug(capsys):
    setup_logging("prod", "INFO")
    logging.getLogger("t").debug("secret detail")
    assert "secret detail" not in capsys.readouterr().err


def test_mask_email():
    assert mask_email("ada@example.com") == "a***@example.com"
    assert mask_email("nonsense") == "***"
