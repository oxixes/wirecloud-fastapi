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

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa

from wirecloud.keycloak import utils


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


async def test_decode_base64_url_handles_padding():
    encoded = _b64u(b"wirecloud")
    assert utils.decode_base64_url(encoded) == b"wirecloud"


async def test_format_jwks_key_rsa_ec_okp_and_oct():
    rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_numbers = rsa_private.public_key().public_numbers()
    rsa_key = {
        "kty": "RSA",
        "n": _b64u(rsa_numbers.n.to_bytes((rsa_numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64u(rsa_numbers.e.to_bytes((rsa_numbers.e.bit_length() + 7) // 8, "big")),
    }
    assert b"BEGIN PUBLIC KEY" in utils.format_jwks_key(rsa_key)

    ec_private = ec.generate_private_key(ec.SECP256R1())
    ec_numbers = ec_private.public_key().public_numbers()
    ec_key = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64u(ec_numbers.x.to_bytes((ec_numbers.x.bit_length() + 7) // 8, "big")),
        "y": _b64u(ec_numbers.y.to_bytes((ec_numbers.y.bit_length() + 7) // 8, "big")),
    }
    assert b"BEGIN PUBLIC KEY" in utils.format_jwks_key(ec_key)

    okp_public = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    okp_key = {"kty": "OKP", "crv": "Ed25519", "x": _b64u(okp_public)}
    assert b"BEGIN PUBLIC KEY" in utils.format_jwks_key(okp_key)

    oct_key = {"kty": "oct", "k": _b64u(b"secret-token")}
    assert utils.format_jwks_key(oct_key) == b"secret-token"


class _FlakyKtyDict(dict):
    def __init__(self):
        super().__init__({"kty": "RSA"})
        self.calls = 0

    def __getitem__(self, key):
        if key == "kty":
            self.calls += 1
            if self.calls == 1:
                return "RSA"
            return "UNRECOGNIZED"
        return super().__getitem__(key)


@pytest.mark.parametrize(
    "key_data,error",
    [
        ({}, "Only RSA keys are supported"),
        ({"kty": "RSA"}, "Invalid RSA key data"),
        ({"kty": "EC"}, "Invalid EC key data"),
        ({"kty": "EC", "crv": "P-999", "x": _b64u(b"x"), "y": _b64u(b"y")}, "Unsupported EC curve"),
        ({"kty": "OKP"}, "Invalid OKP key data"),
        ({"kty": "OKP", "crv": "X25519", "x": _b64u(b"x")}, "Unsupported OKP curve"),
        ({"kty": "oct"}, "Invalid oct key data"),
        (_FlakyKtyDict(), "Unsupported key type"),
    ],
)
async def test_format_jwks_key_error_paths(key_data, error):
    with pytest.raises(ValueError, match=error):
        utils.format_jwks_key(key_data)
