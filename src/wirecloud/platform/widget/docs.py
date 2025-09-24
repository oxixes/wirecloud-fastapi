#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.
#
#  This file is part of Wirecloud.
#
#  Wirecloud is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wirecloud is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

#GET /{vendor}/{name}/{version}/html
get_widget_html_summary = "Get the HTML code of a widget"
get_widget_html_description = "Get the HTML code of a widget. The HTML code is processed"
get_widget_html_response_description = "The HTML code of the widget."
get_widget_html_not_modified_response_description = "The widget has not been modified since the last request."
get_widget_html_not_found_response_description = "Widget not found."
get_widget_html_bad_gateway_response_description = "Widget code was not encoded using the specified charset."
get_widget_html_vendor_description = "The vendor of the widget."
get_widget_html_name_description = "The name of the widget."
get_widget_html_version_description = "The version of the widget."
get_widget_html_mode_description = "The mode in which the widget will be rendered."
get_widget_html_theme_description = "The theme to be used to render the widget."

# GET /{vendor}/{name}/{version}/docs/{file_path:path}
get_widget_file_summary = "Get a file from a widget or operator package"
get_widget_file_description = " Get a file from a widget or operator package. The file can be any file included in the widget package, including the entry point file (if it is a widget). The entry point file is the one that will be used to render the widget in the platform."
get_widget_file_response_description = "The file requested from the widget package."
get_widget_file_found_response_description = "The file has been found and the response will be a redirect to the file."
get_widget_file_not_modified_response_description = "The file has not been modified since the last request."
get_widget_file_not_found_response_description = "Page not found."
get_widget_file_vendor_description = "The vendor of the widget."
get_widget_file_name_description = "The name of the widget."
get_widget_file_version_description = "The version of the widget."
get_widget_file_path_description = "The path of the file to be retrieved from the widget package."
get_widget_file_entrypoint_description = "If true, the entry point file of the widget will be returned."
get_widget_file_mode_description = "The mode in which the widget will be rendered."
get_widget_file_theme_description = "The theme to be used to render the widget."

# GET /missing_widget
get_missing_widget_html_summary = "Get the missing widget HTML"
get_missing_widget_html_description = "Gets the HTML for the missing widget."
get_missing_widget_html_response_description = "The HTML for the missing widget."
get_missing_widget_html_theme_description = "The theme to be used to render the missing widget."
