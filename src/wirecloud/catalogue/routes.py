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

import os
import markdown
from typing import Optional
from fastapi import APIRouter, Path, Query, Request, Response
from urllib.parse import urljoin
from urllib.request import pathname2url, url2pathname
import zipfile
import errno

import src.wirecloud.catalogue.utils as catalogue_utils
from src.wirecloud.commons.auth.utils import UserDep, UserDepNoCSRF
from src.wirecloud.commons.utils.template.schemas.macdschemas import Vendor, Name, Version
from src.wirecloud.commons.utils.http import (PermissionDenied, NotFound,
                                              produces, consumes, authentication_required, XHTMLResponse,
                                              force_trailing_slash, build_downloadfile_response,
                                              get_absolute_reverse_url, build_error_response)
from src.wirecloud.commons.utils.downloader import download_local_file
from src.wirecloud.commons.utils.html import clean_html, filter_changelog
from src.wirecloud.commons.utils.version import Version as VersionType
from src.wirecloud.commons.utils.wgt import WgtFile, InvalidContents
from src.wirecloud.commons.utils.template import TemplateParseException
from src.wirecloud.catalogue import docs
from src.wirecloud import docs as root_docs
from src.wirecloud.catalogue.schemas import (CatalogueResourceDataSummary, CatalogueResourceDataSummaryGroup,
                                             CatalogueResourceDeleteResults)
from src.wirecloud.catalogue.crud import (get_catalogue_resource_versions_for_user, get_catalogue_resource,
                                          get_all_catalogue_resource_versions, mark_resources_as_not_available)
from src.wirecloud.catalogue.utils import get_resource_group_data, get_resource_data
from src.wirecloud.platform.localcatalogue.utils import install_component
from src.wirecloud.database import DBDep
from src.wirecloud.translation import gettext as _

router = APIRouter()


@router.post(
    "/resources",
    summary=docs.create_resource_entry_summary,
    description=docs.create_resource_entry_description,
    response_class=Response,
    response_description=docs.create_resource_entry_response_description,
    status_code=201,
    responses={
        400: root_docs.generate_error_response_openapi_description(
            docs.create_resource_entry_bad_request_response_description,
            "The uploaded file is not a zip file"),
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.create_resource_entry_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.create_resource_entry_permission_denied_response_description,
            "You don't have persmissions to publish in name of example"),
        409: root_docs.generate_error_response_openapi_description(
            docs.create_resource_entry_conflict_response_description,
            "Resource already exists"),
        415: root_docs.generate_unsupported_media_type_response_openapi_description("Unsupported request content type"),
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": docs.create_resource_entry_request_schema_form
                },
                "application/octet-stream": {
                    "schema": docs.create_resource_entry_request_schema_binary
                }
            }
        }
    }
)
@consumes(["multipart/form-data", "application/octet-stream"])
@authentication_required()
async def create_resource(db: DBDep, request: Request, user: UserDep):
    if request.state.mimetype == 'multipart/form-data':
        # Get the file contents from the file 'file'
        form = await request.form(max_files=1000, max_fields=1000)

        public = form.get('public', 'true').strip().lower() == 'true'
        if 'file' not in form:
            return build_error_response(request, 400, _('Missing component file in the request'))

        downloaded_file = await form['file'].read()
    else:  # if request.mimetype == 'application/octet-stream'
        public = request.query_params.get('public', 'true').strip().lower() == 'true'
        downloaded_file = await request.body()

    try:
        file_contents = WgtFile(downloaded_file)
    except zipfile.BadZipfile:
        return build_error_response(request, 400, _('The uploaded file is not a zip file'))

    try:
        added, resource = await install_component(db, file_contents, executor_user=user, public=public,
                                                  users=[user], restricted=True)
        if not added:
            return build_error_response(request, 409, _('Resource already exists'))
    except OSError as e:
        if e.errno == errno.EACCES:
            return build_error_response(request, 500, _('Error writing the resource into the filesystem. Please, contact the server administrator.'))
        else:
            raise
    except TemplateParseException as e:
        msg = "Error parsing config.xml descriptor file"
        return build_error_response(request, 400, msg, details=str(e))
    except InvalidContents as e:
        details = e.details if hasattr(e, 'details') else None
        return build_error_response(request, 400, e.message, details=str(details))

    res = Response(status_code=201)
    res.headers['Location'] = resource.get_template_url()
    return res


@router.get(
    "/resource/{vendor}/{name}",
    summary=docs.get_resource_entry_group_summary,
    description=docs.get_resource_entry_group_description,
    response_model=CatalogueResourceDataSummaryGroup,
    response_model_exclude_none=True,
    response_description=docs.get_resource_entry_group_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_resource_entry_group_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_resource_entry_group_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_resource_entry_group_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_entry_group_validation_error_response_description)
    }
)
@produces(["application/json"])
async def get_resource_versions(db: DBDep,
                                user: UserDepNoCSRF,
                                request: Request,
                                vendor: Vendor = Path(description=docs.get_resource_entry_group_vendor_description,
                                                      pattern=r"^[^/]+$"),
                                name: Name = Path(description=docs.get_resource_entry_group_name_description,
                                                  pattern=r"^[^/]+$")):
    versions = await get_catalogue_resource_versions_for_user(db, vendor, name, user)

    if len(versions) == 0:
        raise NotFound()

    return await get_resource_group_data(db, versions, user, request)


@router.delete(
    "/resource/{vendor}/{name}",
    summary=docs.delete_resource_entry_group_summary,
    description=docs.delete_resource_entry_group_description,
    response_model=CatalogueResourceDeleteResults,
    response_description=docs.delete_resource_entry_group_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.delete_resource_entry_group_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_resource_entry_group_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_resource_entry_group_permission_denied_response_description,
            docs.delete_resource_entry_group_permission_denied_response_example_msg),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_resource_entry_group_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.delete_resource_entry_group_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.delete_resource_entry_group_validation_error_response_description)
    }
)
@produces(["application/json"])
@authentication_required()
async def delete_resource_versions(db: DBDep,
                                   user: UserDep,
                                   request: Request,
                                   vendor: Vendor = Path(description=docs.delete_resource_entry_group_vendor_description,
                                                         pattern=r"^[^/]+$"),
                                   name: Name = Path(description=docs.delete_resource_entry_group_name_description,
                                                     pattern=r"^[^/]+$")):
    resources = await get_all_catalogue_resource_versions(db, vendor, name)

    if len(resources) == 0:
        raise NotFound()
    elif not resources[0].is_removable_by(db, user, vendor=True):
        msg = _("user %(username)s is not the owner of the resource %(resource_id)s") % {
            'username': user.username, 'resource_id': '{}/{}'.format(vendor, name)}
        raise PermissionDenied(msg)

    # TODO Actually delete the resources
    await mark_resources_as_not_available(db, resources)
    await db.commit_transaction()

    return CatalogueResourceDeleteResults(affectedVersions=[resource.version for resource in resources])


@router.get(
    '/resource/{vendor}/{name}/{version}',
    summary=docs.get_resource_entry_summary,
    description=docs.get_resource_entry_description,
    response_model=CatalogueResourceDataSummary,
    response_model_exclude_none=True,
    response_description=docs.get_resource_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.get_resource_entry_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_resource_entry_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_resource_entry_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_entry_validation_error_response_description)
    }
)
@produces(["application/json"])
async def get_resource_version(db: DBDep,
                               user: UserDepNoCSRF,
                               request: Request,
                               vendor: Vendor = Path(description=docs.get_resource_entry_vendor_description,
                                                     pattern=r"^[^/]+$"),
                               name: Name = Path(description=docs.get_resource_entry_name_description,
                                                 pattern=r"^[^/]+$"),
                               version: Version = Path(description=docs.get_resource_entry_version_description,
                                                       pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$")):
    # FIXME No access permissions are checked. The original code does not check permissions either. Check this.
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        raise NotFound()

    return await get_resource_data(db, resource, user, request)


@router.delete(
    '/resource/{vendor}/{name}/{version}',
    summary=docs.delete_resource_entry_summary,
    description=docs.delete_resource_entry_description,
    response_model=CatalogueResourceDeleteResults,
    response_description=docs.delete_resource_entry_response_description,
    responses={
        200: {"content": {"application/json": {"example": docs.delete_resource_entry_response_example}}},
        401: root_docs.generate_auth_required_response_openapi_description(
            docs.delete_resource_entry_auth_required_response_description),
        403: root_docs.generate_permission_denied_response_openapi_description(
            docs.delete_resource_entry_permission_denied_response_description,
            docs.delete_resource_entry_permission_denied_response_example_msg),
        404: root_docs.generate_not_found_response_openapi_description(
            docs.delete_resource_entry_not_found_response_description),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.delete_resource_entry_not_acceptable_response_description, ["application/json"]),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.delete_resource_entry_validation_error_response_description)
    }
)
@produces(["application/json"])
@authentication_required()
async def delete_resource_version(db: DBDep,
                                  user: UserDep,
                                  request: Request,
                                  vendor: Vendor = Path(description=docs.delete_resource_entry_vendor_description,
                                                        pattern=r"^[^/]+$"),
                                  name: Name = Path(description=docs.delete_resource_entry_name_description,
                                                    pattern=r"^[^/]+$"),
                                  version: Version = Path(description=docs.delete_resource_entry_version_description,
                                                        pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$")):
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        raise NotFound()
    elif not await resource.is_removable_by(db, user, vendor=True):
        msg = _("user %(username)s is not the owner of the resource %(resource_id)s") % {
            'username': user.username, 'resource_id': '{}/{}/{}'.format(vendor, name, version)}
        raise PermissionDenied(msg)

    # TODO Actually delete the resources
    await mark_resources_as_not_available(db, [resource])
    await db.commit_transaction()

    return CatalogueResourceDeleteResults(affectedVersions=[resource.version])


@router.get(
    "/resource/{vendor}/{name}/{version}/changelog",
    summary=docs.get_resource_changelog_summary,
    description=docs.get_resource_changelog_description,
    response_description=docs.get_resource_changelog_response_description,
    response_class=XHTMLResponse,
    responses={
        200: {"content": {"application/xhtml+xml": {"example": docs.get_resource_changelog_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_resource_changelog_not_found_response_description, include_schema=False),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_resource_changelog_not_acceptable_response_description, ["application/xhtml+xml"],
            include_schema=False),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_changelog_validation_error_response_description, include_schema=False)
    }
)
@produces(["application/xhtml+xml"])
async def get_resource_changelog(db: DBDep,
                                 request: Request,
                                 vendor: Vendor = Path(description=docs.get_resource_changelog_vendor_description,
                                                       pattern=r"^[^/]+$"),
                                 name: Name = Path(description=docs.get_resource_changelog_name_description,
                                                   pattern=r"^[^/]+$"),
                                 version: Version = Path(description=docs.get_resource_changelog_version_description,
                                                       pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$"),
                                 from_version: Optional[Version] = Query(None,
                                                                         description=docs.get_resource_changelog_from_version_description,
                                                                         pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$",
                                                                         alias='from')):
    # FIXME No access permissions are checked. The original code does not check permissions either. Check this.
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        raise NotFound()

    resource_info = resource.get_processed_info(process_urls=False)
    if resource_info.changelog == "":
        raise NotFound()

    doc_relative_path = url2pathname(resource_info.changelog)
    doc_base_url = force_trailing_slash(urljoin(resource.get_template_url(request=request, for_base=True),
                                                pathname2url(os.path.dirname(doc_relative_path))))
    doc_path = os.path.join(catalogue_utils.wgt_deployer.get_base_dir(vendor, name, version), doc_relative_path)

    (doc_filename_root, doc_filename_ext) = os.path.splitext(doc_path)
    # TODO Use user language instead of 'en'
    localized_doc_path = doc_filename_root + '.' + 'en' + doc_filename_ext

    try:
        doc_code = download_local_file(localized_doc_path).decode('utf-8')
    except Exception:
        try:
            doc_code = download_local_file(doc_path).decode('utf-8')
        except Exception:
            msg = _('Error opening the changelog file')
            doc_code = '<div class="margin-top: 10px"><p>%s</p></div>' % msg

    doc_pre_html = markdown.markdown(doc_code, output_format='xhtml',
                                     extensions=['markdown.extensions.codehilite', 'markdown.extensions.fenced_code'])

    if from_version is not None:
        doc_pre_html = filter_changelog(doc_pre_html, VersionType(from_version))
        if doc_pre_html.strip() == '':
            raise NotFound()

    doc = clean_html(doc_pre_html, base_url=doc_base_url)

    return Response(
        content=doc,
        media_type="application/xhtml+xml; charset=UTF-8"
    )


@router.get(
    "/resource/{vendor}/{name}/{version}/userguide",
    summary=docs.get_resource_userguide_summary,
    description=docs.get_resource_userguide_description,
    response_description=docs.get_resource_userguide_response_description,
    response_class=XHTMLResponse,
    responses={
        200: {"content": {"application/xhtml+xml": {"example": docs.get_resource_userguide_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_resource_userguide_not_found_response_description, include_schema=False),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_resource_userguide_not_acceptable_response_description, ["application/xhtml+xml"],
            include_schema=False),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_userguide_validation_error_response_description, include_schema=False)
    }
)
@produces(["application/xhtml+xml"])
async def get_resource_user_guide(db: DBDep,
                                  request: Request,
                                  vendor: Vendor = Path(description=docs.get_resource_userguide_vendor_description,
                                                        pattern=r"^[^/]+$"),
                                  name: Name = Path(description=docs.get_resource_userguide_name_description,
                                                    pattern=r"^[^/]+$"),
                                  version: Version = Path(description=docs.get_resource_userguide_version_description,
                                                        pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$")):
    # FIXME No access permissions are checked. The original code does not check permissions either. Check this.
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        raise NotFound()

    resource_info = resource.get_processed_info(process_urls=False)
    if resource_info.doc == "":
        raise NotFound()

    doc_base_url = None
    if resource_info.doc.startswith(('http://', 'https://')):
        doc_code = _('You can find the userguide of this component in this external <a target="_blank" href="%s">link</a>') % \
                   resource_info.doc
        doc_code = '<div style="margin-top: 10px"><p>%s</p></div>' % doc_code
    else:
        doc_relative_path = url2pathname(resource_info.doc)
        doc_base_url = force_trailing_slash(urljoin(resource.get_template_url(request=request, for_base=True),
                                                    pathname2url(os.path.dirname(doc_relative_path))))
        doc_path = os.path.join(catalogue_utils.wgt_deployer.get_base_dir(vendor, name, version), doc_relative_path)

        (doc_filename_root, doc_filename_ext) = os.path.splitext(doc_path)
        # TODO Use user language instead of 'en'
        localized_doc_path = doc_filename_root + '.' + 'en' + doc_filename_ext

        try:
            doc_code = download_local_file(localized_doc_path).decode('utf-8')
        except Exception:
            try:
                doc_code = download_local_file(doc_path).decode('utf-8')
            except Exception:
                msg = _('Error opening the userguide file')
                doc_code = '<div class="margin-top: 10px"><p>%s</p></div>' % msg

    doc_pre_html = markdown.markdown(doc_code, output_format='xhtml',
                                     extensions=['markdown.extensions.codehilite', 'markdown.extensions.fenced_code'])
    doc = clean_html(doc_pre_html, base_url=doc_base_url)

    return Response(
        content=doc,
        media_type="application/xhtml+xml; charset=UTF-8"
    )


@router.get(
    "/resource/{vendor}/{name}/{version}/{file_path:path}",
    summary=docs.get_resource_file_summary,
    description=docs.get_resource_file_description,
    response_description=docs.get_resource_file_response_description,
    response_class=Response,
    responses={
        200: {"content": {"application/octet-stream": {"example": docs.get_resource_file_response_example}}},
        404: root_docs.generate_not_found_response_openapi_description(
            docs.get_resource_file_not_found_response_description, include_schema=False),
        406: root_docs.generate_not_acceptable_response_openapi_description(
            docs.get_resource_file_not_acceptable_response_description, ["application/octet-stream"],
            include_schema=False),
        422: root_docs.generate_validation_error_response_openapi_description(
            docs.get_resource_file_validation_error_response_description, include_schema=False)
    }
)
@produces(["application/octet-stream"])
async def get_resource_file(db: DBDep,
                            request: Request,
                            vendor: Vendor = Path(description=docs.get_resource_file_vendor_description,
                                                  pattern=r"^[^/]+$"),
                            name: Name = Path(description=docs.get_resource_file_name_description,
                                                pattern=r"^[^/]+$"),
                            version: Version = Path(description=docs.get_resource_file_version_description,
                                                    pattern=r"^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$"),
                            file_path: str = Path(description=docs.get_resource_file_file_path_description)):
    # FIXME No access permissions are checked. The original code does not check permissions either. Check this.
    resource = await get_catalogue_resource(db, vendor, name, version)

    if resource is None:
        raise NotFound()

    base_dir = catalogue_utils.wgt_deployer.get_base_dir(vendor, name, version)
    response = build_downloadfile_response(request, file_path, base_dir)

    if response.status_code == 302:
        response.headers['Location'] = get_absolute_reverse_url('wirecloud_catalogue.media', request,
                                                                vendor=vendor, name=name, version=version,
                                                                file_path=response.headers['Location'])

    return response
