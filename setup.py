from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

_NPM_BUILD_DONE = False


class _FrontendBuildMixin:
    def _run_frontend_build(self) -> None:
        global _NPM_BUILD_DONE

        if _NPM_BUILD_DONE:
            return

        if os.environ.get("WIRECLOUD_SKIP_NPM_BUILD") == "1":
            self.announce("Skipping frontend build because WIRECLOUD_SKIP_NPM_BUILD=1", level=2)
            _NPM_BUILD_DONE = True
            return

        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("npm is required to build Wirecloud frontend assets")

        project_root = Path(__file__).resolve().parent
        self.announce("Running frontend build: npm run build", level=2)

        try:
            subprocess.check_call([npm, "run", "build"], cwd=str(project_root), env=os.environ.copy())
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"npm run build failed with exit code {exc.returncode}") from exc

        _NPM_BUILD_DONE = True


class build_py(_FrontendBuildMixin, _build_py):
    def run(self):
        self._run_frontend_build()
        super().run()


class sdist(_FrontendBuildMixin, _sdist):
    def run(self):
        self._run_frontend_build()
        super().run()


setup(cmdclass={"build_py": build_py, "sdist": sdist})
