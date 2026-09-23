import os
from pathlib import Path
import shutil

# Mock is explicit and confined to automated tests.
TEST_DB = Path("tests/.test_meeting_protocol.db")
TEST_UPLOADS = Path("tests/.tmp_uploads")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEST_UPLOADS)
os.environ["MOCK_MODE"] = "true"


def pytest_sessionstart(session):
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOADS, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus):
    try:
        from app.core.database import engine
        engine.dispose()
    except ImportError:
        pass
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOADS, ignore_errors=True)
