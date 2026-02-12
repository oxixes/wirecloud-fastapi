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

/* globals StyledElements, Wirecloud */


(function (ns, se, utils) {

    "use strict";

    const ICON_MAPPING = {
        group: "users",
        organization: "building",
        user: "user"
    };

    const defaultOptions = {
        autocomplete: true
    };

    const searchForUserGroup = function searchForUserGroup(querytext) {
        return Wirecloud.io.makeRequest(Wirecloud.URLs.SEARCH_SERVICE, {
            parameters: {namespace: 'usergroup', q: querytext},
            method: 'GET',
            contentType: 'application/json',
            requestHeaders: {'Accept': 'application/json'}
        }).then((response) => {
            return JSON.parse(response.responseText).results;
        });
    };

    ns.UserGroupTypeahead = class UserGroupTypeahead extends se.Typeahead {

        constructor(options) {
            options = utils.merge({}, defaultOptions, options);

            super({
                autocomplete: options.autocomplete,
                lookup: searchForUserGroup,
                build: (typeahead, data) => {
                    // Usar username para usuarios, name para grupos/organizaciones
                    const identifier = data.type === "user" ? data.username : data.name;
                    return {
                        value: identifier,
                        title: data.fullname || identifier,
                        description: identifier,
                        iconClass: "fas fa-" + ICON_MAPPING[data.type],
                        context: data
                    };
                }
            });
        };

    }

})(Wirecloud.ui, StyledElements, StyledElements.Utils);
