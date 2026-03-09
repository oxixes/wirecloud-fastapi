# -*- coding: utf-8 -*-

from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from wirecloud.commons.utils import wgt


def _zip_bytes(entries):
    fp = BytesIO()
    with zipfile.ZipFile(fp, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return fp.getvalue()


def test_invalid_contents_and_create_folder(tmp_path):
    exc = wgt.InvalidContents("bad")
    assert str(exc) == "bad"

    folder = tmp_path / "a" / "b"
    wgt._create_folder(str(folder))
    assert folder.is_dir()
    wgt._create_folder(str(folder))
    assert folder.is_dir()


def test_wgtfile_init_read_and_template():
    data = _zip_bytes({"config.xml": "<xml/>", "a/b.txt": "x"})
    wf = wgt.WgtFile(data)
    assert "config.xml" in wf.namelist()
    assert wf.get_underlying_file() is not None
    assert wf.read("a\\b.txt") == b"x"
    assert wf.get_template() == b"<xml/>"
    wf.close()

    missing = wgt.WgtFile(_zip_bytes({"x.txt": "x"}))
    with pytest.raises(wgt.InvalidContents):
        missing.get_template()
    missing.close()

    with pytest.raises(ValueError):
        wgt.WgtFile(_zip_bytes({"../evil.txt": "x"}))
    with pytest.raises(ValueError):
        wgt.WgtFile(_zip_bytes({"/abs.txt": "x"}))
    # Branch where input is already a file-like object (not bytes)
    wf_file_like = wgt.WgtFile(BytesIO(data))
    assert "config.xml" in wf_file_like.namelist()
    wf_file_like.close()


def test_extract_file_localized_dir_and_extract(tmp_path):
    data = _zip_bytes(
        {
            "config.xml": "<xml/>",
            "docs/readme.md": "hello",
            "docs/sub/info.txt": "world",
            "i18n/label.md": "x",
            "i18n/label.es.md": "x",
            "i18n/label.pt-BR.md": "x",
            "dir/": "",
        }
    )
    wf = wgt.WgtFile(data)

    out_file = tmp_path / "single" / "readme.md"
    wf.extract_file("docs/readme.md", str(out_file))
    assert out_file.read_text() == "hello"

    out_loc = tmp_path / "localized"
    wf.extract_localized_files("i18n/label.md", str(out_loc))
    assert (out_loc / "label.md").exists()
    assert (out_loc / "label.es.md").exists()
    assert (out_loc / "label.pt-BR.md").exists()

    out_dir = tmp_path / "docs"
    wf.extract_dir("docs", str(out_dir))
    assert (out_dir / "readme.md").exists()
    assert (out_dir / "sub" / "info.txt").exists()

    with pytest.raises(KeyError):
        wf.extract_dir("missing", str(tmp_path / "missing"))

    out_all = tmp_path / "all"
    wf.extract(str(out_all))
    assert (out_all / "config.xml").exists()
    assert (out_all / "docs" / "sub" / "info.txt").exists()
    wf.close()


def test_extract_dir_and_extract_existing_paths_branches(tmp_path):
    data = _zip_bytes(
        {
            "config.xml": "<xml/>",
            "docs/sub/": "",
            "docs/sub/nested/": "",
            "docs/sub/file.txt": "x",
            "top/sub/": "",
            "top/sub/file.txt": "y",
        }
    )
    wf = wgt.WgtFile(data)

    out_dir = tmp_path / "docs"
    out_dir.mkdir(parents=True)
    wf.extract_dir("docs/", str(out_dir))
    assert (out_dir / "sub" / "file.txt").exists()

    out_all = tmp_path / "all"
    out_all.mkdir()
    (out_all / "top").mkdir()
    (out_all / "top" / "sub").mkdir()
    wf.extract(str(out_all))
    assert (out_all / "top" / "sub" / "file.txt").exists()
    wf.close()


def test_update_config_and_deployer(tmp_path, monkeypatch):
    data = _zip_bytes({"config.xml": "<xml/>", "f.txt": "x"})
    wf = wgt.WgtFile(data)
    wf.update_config("<new/>")
    assert wf.get_template() == b"<new/>"
    wf.update_config(b"<new2/>")
    assert wf.get_template() == b"<new2/>"

    class _FakeTemplate:
        def __init__(self, _data):
            self.base = None

        def get_resource_vendor(self):
            return "acme"

        def get_resource_name(self):
            return "widget"

        def get_resource_version(self):
            return "1.0.0"

        def set_base(self, value):
            self.base = value

    monkeypatch.setattr(wgt, "TemplateParser", _FakeTemplate)
    deployer = wgt.WgtDeployer(str(tmp_path / "deploy"))
    parser = deployer.deploy(wf)
    assert parser.base.endswith("acme/widget/1.0.0/")
    assert deployer.root_dir.endswith("deploy")

    base_dir = Path(deployer.get_base_dir("acme", "widget", "1.0.0"))
    assert base_dir.is_dir()
    assert (base_dir / "config.xml").exists()
    deployer.undeploy("acme", "widget", "1.0.0")
    assert not base_dir.exists()
    deployer.undeploy("acme", "widget", "1.0.0")
