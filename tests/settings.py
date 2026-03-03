# tests/settings.py
# ---------------------------------------------------------------------------
# Shim: when wirecloud.settings does `from settings import *`, Python finds
# THIS file first (because tests/ is inserted before src/ in sys.path by
# conftest.py).  We simply re-export everything from settings_test so that
# the application uses lightweight test settings instead of the real ones.
# ---------------------------------------------------------------------------
from settings_test import *  # noqa: F401, F403
