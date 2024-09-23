# -*- coding: utf-8 -*-

# Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

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

# Proxy endpoint
proxy_request_summary = "Make a request to a given URL using the WireCloud proxy"
proxy_request_description = ("Make a request to a given URL using the WireCloud proxy. "
                             "This endpoint is useful to avoid CORS issues when making requests to external services."
                             "The proxy can only be used in certain situations, like when the request is made from a WireCloud widget."
                             "The proxy is not available for all requests and it is not a general purpose proxy.")
proxy_request_response_description = "The response from the requested URL"
proxy_request_permission_denied_description = "The proxy cannot be used to access the requested URL or the request comes from an untrusted source"
proxy_request_validation_error_description = "The request data is invalid"
proxy_request_bad_gateway_description = "The proxy cannot access the requested URL"
proxy_request_gateway_timeout_description = "The server took too long to respond"
proxy_request_protocol_description = "The protocol to use for the request (http or https)"
proxy_request_domain_description = "The domain to use for the request"
proxy_request_path_description = "The path to use for the request"