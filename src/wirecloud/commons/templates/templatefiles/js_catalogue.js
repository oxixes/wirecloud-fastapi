// -*- coding: utf-8 -*-
// Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

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

(function () {
    "use strict";

    let catalog = {};

    {{ js_catalogue|safe }}

    window.gettext = function (msgid) {
        return catalog[msgid] || msgid;
    }

    window.ngettext = function (msgid, msgid_plural, n) {
        const value = catalog[msgid];
        if (value) {
            return n === 1 ? value[0] : value[1];
        } else {
            return n === 1 ? msgid : msgid_plural;
        }
    }

    window.gettext_noop = function (msgid) {
        return msgid;
    }

    window.interpolate = function (fmt, obj, named) {
        if (named) {
            return fmt.replace(/%\(\w+\)s/g, function (match) {
                return String(obj[match.slice(2, -2)]);
            });
        } else {
            return fmt.replace(/%s/g, function (match) {
                return String(obj.shift());
            });
        }
    }
})();