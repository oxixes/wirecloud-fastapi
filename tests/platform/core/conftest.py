# -*- coding: utf-8 -*-

import sys
from types import SimpleNamespace


sys.modules.setdefault(
    "wirecloud.catalogue.search",
    SimpleNamespace(
        add_resource_to_index=None,
        delete_resource_from_index=None,
        rebuild_resource_index=None,
        search_resources=None,
    ),
)
