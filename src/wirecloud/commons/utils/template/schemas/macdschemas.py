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

# TODO Add docs of almost everything here (descriptions)

from pydantic import BaseModel, StringConstraints, Field, model_validator, field_serializer
from enum import Enum
from typing import Optional, Annotated, Union

from src.wirecloud.platform.wiring.schemas import WiringEndpoints, Wiring
from src.wirecloud.commons.utils.template.base import Contact, parse_contacts_info, TemplateParseException

from src.wirecloud.translation import gettext as _


IntegerStr = Annotated[str, StringConstraints(pattern=r'^\d+$')]
FloatStr = Annotated[str, StringConstraints(pattern=r'^\d+(\.\d+)?$')]
SizeStr = Annotated[str, StringConstraints(pattern=r'^\d+(\.\d+)?\s*(px|%)?$')]


class MACType(Enum):
    operator = 'operator'
    widget = 'widget'
    mashup = 'mashup'


Name = Annotated[str, StringConstraints(pattern=r'^[^/]+$')]
Vendor = Annotated[str, StringConstraints(pattern=r'^[^/]+$')]
Version = Annotated[str, StringConstraints(pattern=r'^(?:[1-9]\d*\.|0\.)*(?:[1-9]\d*|0)(?:(?:a|b|rc)[1-9]\d*)?(-dev.*)?$')]
MACVersion = Annotated[int, Field(ge=1, le=2)]


class MACDRequirement(BaseModel):
    type: str
    name: str


class MACDTranslationIndexUsage(BaseModel):
    type: str
    field: Optional[str] = None
    variable: Optional[str] = None
    option: Optional[int] = None


class MACDBase(BaseModel):
    type: MACType
    macversion: MACVersion = 1
    name: Name
    vendor: Vendor
    version: Version

    title: str = ""
    description: str = ""
    longdescription: str = ""
    email: str = ""
    homepage: str = ""
    doc: str = ""
    changelog: str = ""
    image: str = ""
    smartphoneimage: str = ""
    license: str = ""
    licenseurl: str = ""
    issuetracker: str = ""

    authors: list[Contact] = []
    contributors: list[Contact] = []

    requirements: list[MACDRequirement] = []

    default_lang: str = "en"
    translations: dict[str, dict[str, str]] = {}
    translation_index_usage: dict[str, list[MACDTranslationIndexUsage]] = {}

    wgt_files: Optional[list[str]] = None

    # Parse contacts if present
    @model_validator(mode='before')
    @classmethod
    def parse_contacts(cls, data):
        if isinstance(data, dict):
            if 'authors' in data and isinstance(data['authors'], (str, list, tuple)):
                data['authors'] = parse_contacts_info(data['authors'])
            if 'contributors' in data and isinstance(data['contributors'], (str, list, tuple)):
                data['contributors'] = parse_contacts_info(data['contributors'])
        return data

    # Serialize the type as a string
    @field_serializer("type")
    def serialize_type(self, value):
        return value.value

    def check_translations(self) -> None:
        if len(self.translations.keys()) == 0:
            return  # No translations

        missing_translations = []
        extra_translations = set()

        for index in self.translation_index_usage:
            if index not in self.translations[self.default_lang]:
                missing_translations.append(index)

        for __, translation in self.translations.items():
            for index in translation:
                if index not in self.translation_index_usage:
                    extra_translations.add(index)

        if self.default_lang not in self.translations:
            raise TemplateParseException(
                _("There isn't a translation element for the default translation language: (%(default_lang)s)") %
                {'default_lang': self.default_lang})

        if len(missing_translations) > 0:
            msg = _("The following translation indexes need a default value: %(indexes)s.")
            raise TemplateParseException(msg % {'indexes': ', '.join(missing_translations)})

        if len(extra_translations) > 0:
            msg = _("The following translation indexes are not used: %(indexes)s.")
            raise TemplateParseException(msg % {'indexes': ', '.join(extra_translations)})


class MACDPropertyBase(BaseModel):
    name: str
    type: str
    label: str = ""
    description: str = ""
    default: str = ""


class MACDPreferenceListOption(BaseModel):
    value: str
    label: str


class MACDPreference(MACDPropertyBase):
    readonly: bool = False
    required: bool = True
    secure: bool = False
    multiuser: bool = False
    value: Optional[str] = None
    options: Optional[list[MACDPreferenceListOption]] = None
    language: Optional[str] = None  # Used when the type is 'code', and refers to a programming language (e.g. 'javascript')

    # multiuser must be False, set it in the after validator
    @model_validator(mode='after')
    def set_multiuser(self):
        self.multiuser = False
        return self

    # If the preference is a list, there must be options
    @model_validator(mode='after')
    def check_options(self):
        if self.type == 'list' and self.options is None:
            raise ValueError('List preferences must have options')
        return self


class MACDMashupPreference(MACDPropertyBase):
    readonly: bool = False
    required: bool = True
    value: Optional[str] = None


class MACDProperty(MACDPropertyBase):
    secure: bool = False
    multiuser: bool = False


class MACDWidgetOperatorVairables(BaseModel):
    all: dict[str, Union[MACDPreference, MACDProperty]] = {}
    preferences: dict[str, MACDPreference] = {}
    properties: dict[str, MACDProperty] = {}


# Only used in operators and widgets, but not in mashups
class MACDWidgetOperatorBase(MACDBase):
    preferences: list[MACDPreference] = []
    properties: list[MACDProperty] = []
    entrypoint: Optional[str] = None
    js_files: list[str] = []
    wiring: WiringEndpoints = WiringEndpoints()

    variables: MACDWidgetOperatorVairables = MACDWidgetOperatorVairables()

    # On validation make the variables empty. They can only be set after the object is created
    # in get_resource_processed_info
    @model_validator(mode='after')
    def set_variables(self):
        self.variables = MACDWidgetOperatorVairables()
        return self


class MACDWidgetContentsBase(BaseModel):
    src: str
    contenttype: str = 'text/html'
    charset: str = 'utf-8'


class MACDWidgetContents(MACDWidgetContentsBase):
    cacheable: bool = True
    useplatformstyle: bool = False


class MACDWidgetContentsAlternative(MACDWidgetContentsBase):
    scope: str


class MACDWidget(MACDWidgetOperatorBase):
    contents: MACDWidgetContents
    altcontents: list[MACDWidgetContentsAlternative] = []
    widget_width: SizeStr
    widget_height: SizeStr

    @model_validator(mode='after')
    def check_type(self):
        if self.type != MACType.widget:
            raise ValueError('Invalid type for widget')
        return self

    # Check that no js_files are defined if macversion is 1
    @model_validator(mode='after')
    def check_js_files(self):
        if self.macversion == 1 and self.js_files:
            raise ValueError('JS scripts are not allowed in the config of macversion 1 widgets')
        return self


class MACDOperator(MACDWidgetOperatorBase):
    @model_validator(mode='after')
    def check_type(self):
        if self.type != MACType.operator:
            raise ValueError('Invalid type for operator')
        return self


class MACDMashupResourcePropertyBase(BaseModel):
    readonly: bool = False
    value: Optional[str] = None


class MACDMashupResourceProperty(MACDMashupResourcePropertyBase):
    pass


class MACDMashupResourcePreference(MACDMashupResourcePropertyBase):
    hidden: bool = False


class MACDMashupResourcePosition(BaseModel):
    anchor: str = "top-left"
    relx: bool = True
    rely: bool = True
    x: FloatStr
    y: FloatStr
    z: IntegerStr


class MACDMashupResourceRendering(BaseModel):
    fulldragboard: bool = False
    minimized: bool = False
    relwidth: bool = True
    relheight: bool = True
    titlevisible: bool = True
    width: FloatStr
    height: FloatStr


class MACDMashupResourceScreenSize(BaseModel):
    id: int = Field(ge=0)
    moreOrEqual: int = Field(ge=0)
    lessOrEqual: int = Field(ge=-1)
    rendering: MACDMashupResourceRendering
    position: MACDMashupResourcePosition


class MACDMashupResource(BaseModel):
    id: IntegerStr
    name: Name
    vendor: Vendor
    version: Version
    title: str = ""
    layout: int = 0
    readonly: bool = False
    properties: dict[str, MACDMashupResourceProperty] = {}
    preferences: dict[str, MACDMashupResourcePreference] = {}
    screenSizes: list[MACDMashupResourceScreenSize] = []

    # Fix old format that didn't have screen sizes
    @model_validator(mode='before')
    @classmethod
    def fix_old_format(cls, data):
        if isinstance(data, dict) and 'screenSizes' not in data and ('rendering' in data or 'position' in data):
            if not isinstance(data.get('rendering', {}), dict) or not isinstance(data.get('position', {}), dict):
                return data

            screen_sizes = [
                {
                    'moreOrEqual': 0,
                    'lessOrEqual': -1,
                    'id': 0,
                    'rendering': data.get('rendering', {}),
                    'position': data.get('position', {})
                }
            ]

            layout = screen_sizes[0]['rendering'].get('layout', 0)
            data['layout'] = int(layout)
            if 'layout' in screen_sizes[0]['rendering']:
                del screen_sizes[0]['rendering']['layout']

            if 'rendering' in data:
                del data['rendering']

            if 'position' in data:
                del data['position']

            data['screenSizes'] = screen_sizes
        return data

    # Set default for rely based on layout
    @model_validator(mode='before')
    @classmethod
    def set_default_rely(cls, data):
        if isinstance(data, dict) and 'screenSizes' in data and isinstance(data['screenSizes'], list):
            for screen_size in data['screenSizes']:
                if (isinstance(screen_size, dict) and 'position' in screen_size and
                        isinstance(screen_size['position'], dict) and 'rely' not in screen_size['position']):
                    screen_size['position']['rely'] = screen_size['layout'] != 1
        return data


class MACDTab(BaseModel):
    name: str
    title: str = ""
    preferences: dict[str, str] = {}
    resources: list[MACDMashupResource] = []


class MACDMashupEmbedded(BaseModel):
    name: Name
    vendor: Vendor
    version: Version
    src: str


class MACDMashupWiring(Wiring, WiringEndpoints):
    pass


class MACDMashup(MACDBase):
    preferences: dict[str, str] = {}
    params: list[MACDMashupPreference] = []
    tabs: list[MACDTab] = []
    embedmacs: bool = False
    embedded: list[MACDMashupEmbedded] = []
    wiring: MACDMashupWiring = MACDMashupWiring()

    @model_validator(mode='after')
    def check_type(self):
        if self.type != MACType.mashup:
            raise ValueError('Invalid type for mashup')
        return self

    def is_valid_screen_sizes(self) -> bool:
        for tab in self.tabs:
            for resource in tab.resources:
                # Screen sizes must cover the whole range of screen sizes ([0, +inf)) without gaps or overlaps
                if len(resource.screenSizes) == 0:
                    return False

                screen_sizes_copy = resource.screenSizes.copy()
                screen_sizes_copy.sort(key=lambda x: x.moreOrEqual)

                if screen_sizes_copy[0].moreOrEqual != 0:
                    return False

                for i in range(1, len(screen_sizes_copy)):
                    if screen_sizes_copy[i].moreOrEqual != screen_sizes_copy[i - 1].lessOrEqual + 1:
                        return False

                if screen_sizes_copy[-1].lessOrEqual != -1:
                    return False

        return True


class MACDParametrizationOptionsSource(Enum):
    custom = 'custom'
    default = 'default'
    current = 'current'


class MACDParametrizationOptionsStatus(Enum):
    readonly = 'readonly'
    hidden = 'hidden'
    normal = 'normal'


class MACDParametrizationOptions(BaseModel, use_enum_values=True):
    source: MACDParametrizationOptionsSource = MACDParametrizationOptionsSource.current
    status: MACDParametrizationOptionsStatus = MACDParametrizationOptionsStatus.normal
    value: str


class MACDParametrization(BaseModel):
    iwidgets: dict[IntegerStr, dict[str, MACDParametrizationOptions]] = {}
    ioperators: dict[IntegerStr, dict[str, MACDParametrizationOptions]] = {}


class MACDMashupWithParametrization(MACDMashup):
    readOnlyWidgets: bool = False
    parametrization: MACDParametrization = MACDParametrization()
    readOnlyConnectables: bool = False


MACD = Union[MACDWidget, MACDOperator, MACDMashup]
