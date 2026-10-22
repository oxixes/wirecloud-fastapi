from __future__ import annotations

import os
import runpy
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

        project_root = Path(__file__).resolve().parent
        self.announce("Running frontend build: npm run build", level=2)
        npm = "npm.cmd" if os.name == "nt" else "npm"

        try:
            subprocess.check_call([npm, "run", "build"], cwd=str(project_root), env=os.environ.copy())
        except FileNotFoundError as exc:
            raise RuntimeError("npm is required to build Wirecloud frontend assets") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"npm run build failed with exit code {exc.returncode}") from exc

        _NPM_BUILD_DONE = True


class build_py(_FrontendBuildMixin, _build_py):
    def _compile_translations(self) -> None:
        project_root = Path(__file__).resolve().parent
        source = project_root / "src"
        compiler = runpy.run_path(str(source / "wirecloud" / "commons" / "utils" / "translation.py"))
        count = 0
        for po_file in sorted(source.glob("**/locale/*/LC_MESSAGES/*.po")):
            mo_file = (Path(self.build_lib) / po_file.relative_to(source)).with_suffix(".mo")
            compiler["compile_catalog"](po_file, mo_file)
            count += 1
        self.announce(f"Compiled {count} translation catalogs", level=2)

    def run(self):
        self._run_frontend_build()
        super().run()
        self._compile_translations()


class sdist(_FrontendBuildMixin, _sdist):
    def run(self):
        self._run_frontend_build()
        super().run()


setup(cmdclass={"build_py": build_py, "sdist": sdist})
