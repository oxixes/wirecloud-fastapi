# -*- coding: utf-8 -*-

from wirecloud.platform.localcatalogue import docs, schemas


def test_localcatalogue_docs_constants():
    assert isinstance(docs.get_resource_collection_summary, str)
    assert isinstance(docs.create_resource_summary, str)
    assert isinstance(docs.get_resource_entry_summary, str)
    assert isinstance(docs.get_resource_description_summary, str)
    assert isinstance(docs.get_workspace_resource_collection_summary, str)
    assert isinstance(docs.create_resource_response_example, dict)
    assert isinstance(docs.delete_resource_entry_version_response_example, dict)


def test_localcatalogue_schemas_roundtrip():
    resource_create = schemas.ResourceCreateData(url="https://marketplace.example.org/widget.wgt")
    assert resource_create.url.endswith(".wgt")
    assert isinstance(resource_create.headers, dict)

    form_data = schemas.ResourceCreateFormData(
        force_create=True,
        public=False,
        users=["alice"],
        groups=["devs"],
        install_embedded_resources=True,
        file=b"zip-content",
    )
    assert form_data.force_create is True
    assert form_data.users == ["alice"]
    assert form_data.file == b"zip-content"
