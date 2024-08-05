# -*- coding: utf-8 -*-

# Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of Wirecloud.

# Wirecloud is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Wirecloud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

"""
from io import BytesIO

from lxml import etree

from src.wirecloud.commons.utils.http import get_absolute_static_url, get_current_domain
from src.wirecloud.platform.plugins import get_operator_api_extensions
"""

from typing import Union, Callable
from src.wirecloud.platform.wiring.schemas import Wiring, WiringVisualDescription, WiringComponents, WiringBehaviour, \
    WiringConnectionEndpoint, WiringType, WiringConnection, WiringVisualDescriptionConnection


def remove_widget_from_wiring_status(id: str, status: Wiring) -> Wiring:
    def has_model_widget(connection: WiringConnection) -> bool:
        def check_endpoint(endpoint: WiringConnectionEndpoint) -> bool:
            return endpoint.type == WiringType.widget and ("%s" % endpoint.id) == id

        return check_endpoint(connection.source) or check_endpoint(connection.target)

    def has_view_widget(connection: WiringVisualDescriptionConnection) -> bool:
        def check_endpoint(endpoint: str) -> bool:
            c_type, c_id, e_name = tuple(endpoint.split('/'))
            return c_type == 'widget' and c_id == id

        return check_endpoint(connection.sourcename) or check_endpoint(connection.targetname)

    def remove_references(description: Union[Wiring, WiringVisualDescription, WiringBehaviour],
                          has_widget: Union[Callable[[WiringConnection], bool],
                                            Callable[[WiringVisualDescriptionConnection], bool]]) -> None:
        if hasattr(description, 'components') and id in description.components.widget:
            del description.components.widget[id]

        for connection in [c for c in description.connections if has_widget(c)]:
            description.connections.remove(connection)

    remove_references(status, has_model_widget)

    remove_references(status.visualdescription, has_view_widget)

    for behaviour in status.visualdescription.behaviours:
        remove_references(behaviour, has_view_widget)

    return status


# TODO
"""
def get_operator_cache_key(operator: Operator, domain: str, mode: str) -> str:
    return '_operator_xhtml/%s/%s/%s?mode=%s' % (operator.cache_version, domain, operator.id, mode)


# TODO Cache operator_api_files
def get_operator_api_files(request):
    from wirecloud.platform.core.plugins import get_version_hash

    key = 'operator_api_files/%s?v=%s' % (get_current_domain(request), get_version_hash())
    operator_api_files = cache.get(key)

    if operator_api_files is None or settings.DEBUG is True:
        code = '''{% load compress %}{% load static from staticfiles %}{% compress js %}
        <script type="text/javascript" src="{% static "js/WirecloudAPI/WirecloudAPIBootstrap.js" %}"></script>
        <script type="text/javascript" src="{% static "js/WirecloudAPI/WirecloudOperatorAPI.js" %}"></script>
        <script type="text/javascript" src="{% static "js/WirecloudAPI/WirecloudAPICommon.js" %}"></script>
        {% endcompress %}'''

        result = Template(code).render(Context())
        doc = etree.parse(BytesIO(('<files>' + result + '</files>').encode('utf-8')), etree.XMLParser())

        files = [script.get('src') for script in doc.getroot()]
        operator_api_files = tuple([get_absolute_static_url(file, request=request, versioned=True) for file in files])
        cache.set(key, operator_api_files)

    return list(operator_api_files)


def generate_xhtml_operator_code(js_files, base_url, request, requirements, mode):

    api_closure_url = get_absolute_static_url('js/WirecloudAPI/WirecloudAPIClosure.js', request=request, versioned=True)
    extra_api_js_files = [get_absolute_static_url(url, request=request, versioned=True) for url in get_operator_api_extensions(mode, requirements)]
    api_js = get_operator_api_files(request) + extra_api_js_files + [api_closure_url]

    template = loader.get_template('wirecloud/operator_xhtml.html')
    context = {'base_url': base_url, 'js_files': api_js + js_files}

    xhtml = template.render(context)

    return xhtml
"""


def get_endpoint_name(endpoint: WiringConnectionEndpoint):
    return "%s/%s/%s" % (endpoint.type, endpoint.id, endpoint.endpoint)


def rename_component_type(component_type: str) -> WiringType:
    if component_type in ['widget', 'operator']:
        return WiringType(component_type)
    else:
        raise ValueError("Invalid component type")


def get_behaviour_skeleton() -> WiringBehaviour:
    return WiringBehaviour(
        title="",
        description="",
        components=WiringComponents(widget={}, operator={}),
        connections=[]
    )


def get_wiring_skeleton() -> Wiring:
    return Wiring(
        version="2.0",
        connections=[],
        operators={},
        visualdescription=WiringVisualDescription(
            behaviours=[],
            components=WiringComponents(widget={}, operator={}),
            connections=[]
        )
    )


def is_empty_wiring(visual_info: WiringVisualDescription) -> bool:
    return len(visual_info.connections) == 0 and len(visual_info.components.operator) == 0 and len(
        visual_info.components.widget) == 0
