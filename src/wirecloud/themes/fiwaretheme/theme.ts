// -*- coding: utf-8 -*-

// Copyright (c) 2016 CoNWeT Lab., Universidad Politécnica de Madrid

// This file is part of Wirecloud.

// Wirecloud is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Wirecloud is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

const parent: string | null = "defaulttheme";

const get_platform_css = (view: string): string[] => {
    return ["css/window_menu.css"];
};

export default {
    parent: parent,
    get_css: get_platform_css,
    get_scripts: (_: string): string[] => []
};