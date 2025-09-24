// -*- coding: utf-8 -*-

// Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

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

const get_scripts: (view: string) => string[] = (view: string): string[] => {
    const common = [
        'js/NGSI/NGSI.min.js',
        'js/NGSI/NGSIManager.js',
        'js/WirecloudAPI/NGSIAPI.js',
        'js/ObjectStorage/OpenStackManager.js',
        'js/ObjectStorage/ObjectStorageAPI.js'
    ]

    if (view === 'classic') {
        return [...common,
            'js/wirecloud/FiWare.js',
            'js/wirecloud/FiWare/BusinessAPIEcosystemView.js'
        ]
    } else {
        return common;
    }
};

export default {
    get_scripts: get_scripts,
    scripts_location: 'js'
}