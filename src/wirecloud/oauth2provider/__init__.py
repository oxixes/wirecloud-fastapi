"""Public API for plugins offering user-authorized client connections."""
from wirecloud.oauth2provider.service import (
    OAuthPrincipal, OAuthResource, bearer_token, register_resource,
    resource_metadata_url, verify_access_token,
)
from wirecloud.oauth2provider.dependencies import require_access

__all__ = ["OAuthPrincipal", "OAuthResource", "bearer_token", "register_resource",
           "require_access", "resource_metadata_url", "verify_access_token"]
