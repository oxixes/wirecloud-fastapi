# -*- coding: utf-8 -*-
# Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

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

import base64
from typing import Union
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
from cryptography.hazmat.backends import default_backend


def decode_base64_url(data: str) -> bytes:
    data += '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data)


def format_jwks_key(key_data: dict[str, Union[str, list[str]]]) -> bytes:
    if 'kty' not in key_data or key_data['kty'] not in ['RSA', 'EC', 'OKP', 'oct']:
        raise ValueError('Only RSA keys are supported')

    if key_data['kty'] == 'RSA':
        if 'n' not in key_data or 'e' not in key_data:
            raise ValueError('Invalid RSA key data')
        modulus = decode_base64_url(key_data['n'])
        exponent = decode_base64_url(key_data['e'])
        n = int.from_bytes(modulus, 'big')
        e = int.from_bytes(exponent, 'big')
        public_numbers = rsa.RSAPublicNumbers(e, n)
        public_key_b = public_numbers.public_key(default_backend())
        public_key = public_key_b.public_bytes(encoding=serialization.Encoding.PEM,
                                               format=serialization.PublicFormat.SubjectPublicKeyInfo)
    elif key_data['kty'] == 'EC':
        if 'crv' not in key_data or 'x' not in key_data or 'y' not in key_data:
            raise ValueError('Invalid EC key data')

        x = decode_base64_url(key_data['x'])
        y = decode_base64_url(key_data['y'])
        curve_map = {
            'P-256': ec.SECP256R1(),
            'P-384': ec.SECP384R1(),
            'P-521': ec.SECP521R1(),
        }

        if key_data['crv'] not in curve_map:
            raise ValueError('Unsupported EC curve')

        curve = curve_map[key_data['crv']]
        public_numbers = ec.EllipticCurvePublicNumbers(int.from_bytes(x, 'big'), int.from_bytes(y, 'big'), curve)
        public_key_b = public_numbers.public_key(default_backend())
        public_key = public_key_b.public_bytes(encoding=serialization.Encoding.PEM,
                                               format=serialization.PublicFormat.SubjectPublicKeyInfo)
    elif key_data['kty'] == 'OKP':
        if 'crv' not in key_data or 'x' not in key_data:
            raise ValueError('Invalid OKP key data')

        x = decode_base64_url(key_data['x'])

        if key_data['crv'] == 'Ed25519':
            public_key_b = ed25519.Ed25519PublicKey.from_public_bytes(x)
            public_key = public_key_b.public_bytes(encoding=serialization.Encoding.PEM,
                                                   format=serialization.PublicFormat.SubjectPublicKeyInfo)
        else:
            raise ValueError('Unsupported OKP curve')
    elif key_data['kty'] == 'oct':
        if 'k' not in key_data:
            raise ValueError('Invalid oct key data')
        public_key = decode_base64_url(key_data['k'])
    else:
        raise ValueError('Unsupported key type')

    return public_key



