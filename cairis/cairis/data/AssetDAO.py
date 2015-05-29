import numpy
from numpy.core.multiarray import array

import ARM
from Asset import Asset
from AssetEnvironmentProperties import AssetEnvironmentProperties
from AssetParameters import AssetParameters
from CairisHTTPError import ObjectNotFoundHTTPError, MalformedJSONHTTPError, ARMHTTPError, MissingParameterHTTPError, OverwriteNotAllowedHTTPError
from ValueType import ValueType
from ValueTypeParameters import ValueTypeParameters
import armid
from data.CairisDAO import CairisDAO
from kaosxdot import KaosXDotParser
from tools.JsonConverter import json_serialize, json_deserialize
from tools.ModelDefinitions import AssetEnvironmentPropertiesModel, SecurityAttribute, AssetModel
from tools.SessionValidator import check_required_keys, get_fonts
from AssetModel import AssetModel as GraphicalAssetModel

__author__ = 'Robin Quetin'


class AssetDAO(CairisDAO):
    def __init__(self, session_id):
        CairisDAO.__init__(self, session_id)
        self.prop_dict = {
            0: 'None',
            1: 'Low',
            2: 'Medium',
            3: 'High'
        }
        self.attr_dict = {
            'Confidentiality': armid.C_PROPERTY,
            'Integrity': armid.I_PROPERTY,
            'Availability': armid.AV_PROPERTY,
            'Accountability': armid.AC_PROPERTY,
            'Anonymity': armid.AN_PROPERTY,
            'Pseudonymity': armid.PAN_PROPERTY,
            'Unlinkability': armid.UNL_PROPERTY,
            'Unobservability': armid.UNO_PROPERTY
        }
        self.rev_attr_dict = {}
        self.rev_prop_dict = {}
        for key, value in self.attr_dict.items():
            self.rev_attr_dict[value] = key
        for key, value in self.prop_dict.items():
            self.rev_prop_dict[value] = key

    def get_assets(self, constraint_id=-1, simplify=True):
        try:
            assets = self.db_proxy.getAssets(constraint_id)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)

        if simplify:
            for key, value in assets.items():
                assets[key] = self.simplify(value)

        return assets

    def get_asset_names(self):
        try:
            asset_names = self.db_proxy.getDimensionNames('asset')
            return asset_names
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def get_asset_by_id(self, id, simplify=True):
        found_asset = None
        try:
            assets = self.db_proxy.getAssets()
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)

        idx = 0
        while found_asset is None and idx < len(assets):
            if assets.values()[idx].theId == id:
                found_asset = assets.values()[idx]
            idx += 1

        if found_asset is None:
            self.close()
            raise ObjectNotFoundHTTPError('The provided asset ID')

        if simplify:
            found_asset = self.simplify(found_asset)

        return found_asset

    def get_asset_by_name(self, name, simplify=True):
        found_asset = None
        try:
            assets = self.db_proxy.getAssets()
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)

        if assets is not None:
            found_asset = assets.get(name)

        if found_asset is None:
            self.close()
            raise ObjectNotFoundHTTPError('The provided asset name')

        if simplify:
            found_asset = self.simplify(found_asset)

        return found_asset

    def get_asset_props(self, name, simplify=True):
        asset = self.get_asset_by_name(name, simplify=False)
        props = asset.theEnvironmentProperties

        if simplify:
            props = self.convert_props(real_props=props)

        return props

    def add_asset(self, asset, asset_props=None):
        try:
            self.db_proxy.nameCheck(asset.theName, 'asset')
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

        assetParams = AssetParameters(
            assetName=asset.theName,
            shortCode=asset.theShortCode,
            assetDesc=asset.theDescription,
            assetSig=asset.theSignificance,
            assetType=asset.theType,
            cFlag=asset.isCritical,
            cRationale=asset.theCriticalRationale,
            tags=asset.theTags,
            ifs=asset.theInterfaces,
            cProperties=asset.theEnvironmentProperties
        )

        asset_id = self.db_proxy.addAsset(assetParams)
        return asset_id

    def update_asset(self, asset, name):
        old_asset = self.get_asset_by_name(name, simplify=False)
        id = old_asset.theId

        params = AssetParameters(
            assetName=asset.theName,
            shortCode=asset.theShortCode,
            assetDesc=asset.theDescription,
            assetSig=asset.theSignificance,
            assetType=asset.theType,
            cFlag=asset.isCritical,
            cRationale=asset.theCriticalRationale,
            tags=asset.theTags,
            ifs=asset.theInterfaces,
            cProperties=asset.theEnvironmentProperties
        )
        params.setId(id)

        try:
            self.db_proxy.updateAsset(params)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def update_asset_properties(self, props, name, existing_params=None):
        if existing_params is None:
            asset = self.get_asset_by_name(name, simplify=False)

            existing_params = AssetParameters(
                assetName=asset.theName,
                shortCode=asset.theShortCode,
                assetDesc=asset.theDescription,
                assetSig=asset.theSignificance,
                assetType=asset.theType,
                cFlag=asset.isCritical,
                cRationale=asset.theCriticalRationale,
                tags=asset.theTags,
                ifs=asset.theInterfaces,
                cProperties=[]
            )
            existing_params.setId(asset.theId)

        existing_params.theEnvironmentProperties = props

        try:
            self.db_proxy.updateAsset(existing_params)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def delete_asset(self, name=None, asset_id=-1):
        if name is not None:
            found_asset = self.get_asset_by_name(name)
        elif asset_id > -1:
            found_asset = self.get_asset_by_id(asset_id)
        else:
            self.close()
            raise MissingParameterHTTPError(param_names=['name'])

        if found_asset is None or not isinstance(found_asset, Asset):
            self.close()
            raise ObjectNotFoundHTTPError('The provided asset name')

        try:
            self.db_proxy.deleteAsset(found_asset.theId)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def get_asset_model(self, environment_name, with_concerns=True):
        fontName, fontSize, apFontName = get_fonts(session_id=self.session_id)
        try:
            associationDictionary = self.db_proxy.classModel(environment_name, hideConcerns=(with_concerns is False))
            associations = GraphicalAssetModel(associationDictionary.values(), environment_name, db_proxy=self.db_proxy, fontName=fontName, fontSize=fontSize)
            dot_code = associations.graph()
            return dot_code
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except Exception as ex:
            print(ex)

    # region Asset Types
    def get_asset_types(self, environment_name=''):
        try:
            asset_types = self.db_proxy.getValueTypes('asset_type', environment_name)
            return asset_types
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def get_asset_type_by_name(self, name, environment_name=''):
        found_type = None
        asset_types = self.get_asset_types(environment_name=environment_name)

        if asset_types is None or len(asset_types) < 1:
            self.close()
            raise ObjectNotFoundHTTPError('Asset types')

        idx = 0
        while found_type is None and idx < len(asset_types):
            if asset_types[idx].theName == name:
                found_type = asset_types[idx]
            idx += 1

        if found_type is None:
            self.close()
            raise ObjectNotFoundHTTPError('The provided asset type name')

        return found_type

    def add_asset_type(self, asset_type, environment_name=''):
        assert isinstance(asset_type, ValueType)
        type_exists = self.check_existing_asset_type(asset_type.theName, environment_name=environment_name)

        if type_exists:
            self.close()
            raise OverwriteNotAllowedHTTPError(obj_name='The asset type')

        params = ValueTypeParameters(
            vtName=asset_type.theName,
            vtDesc=asset_type.theDescription,
            vType='asset_type',
            envName=environment_name,
            vtScore=asset_type.theScore,
            vtRat=asset_type.theRationale
        )

        try:
            return self.db_proxy.addValueType(params)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def update_asset_type(self, asset_type, name, environment_name=''):
        assert isinstance(asset_type, ValueType)

        found_type = self.get_asset_type_by_name(name, environment_name)

        params = ValueTypeParameters(
            vtName=asset_type.theName,
            vtDesc=asset_type.theDescription,
            vType='asset_type',
            envName=environment_name,
            vtScore=asset_type.theScore,
            vtRat=asset_type.theRationale
        )
        params.setId(found_type.theId)

        try:
            self.db_proxy.updateValueType(params)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def delete_asset_type(self, name, environment_name=''):
        found_type = self.get_asset_type_by_name(name, environment_name)

        try:
            self.db_proxy.deleteAssetType(found_type.theId)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def check_existing_asset_type(self, name, environment_name):
        try:
            self.get_asset_type_by_name(name, environment_name)
            return True
        except ObjectNotFoundHTTPError:
            # Needs to reconnect after Error was raised
            self.db_proxy.reconnect(session_id=self.session_id)
            return False

    # endregion

    # region Asset values
    def get_asset_values(self, environment_name=''):
        try:
            asset_values = self.db_proxy.getValueTypes('asset_value', environment_name)
            return asset_values
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def get_asset_value_by_name(self, name, environment_name=''):
        found_value = None
        asset_values = self.get_asset_values(environment_name=environment_name)
        if asset_values is None or len(asset_values) < 1:
            self.close()
            raise ObjectNotFoundHTTPError('Asset values')
        idx = 0
        while found_value is None and idx < len(asset_values):
            if asset_values[idx].theName == name:
                found_value = asset_values[idx]
            idx += 1
        if found_value is None:
            self.close()
            raise ObjectNotFoundHTTPError('The provided asset value name')
        return found_value

    def update_asset_value(self, asset_value, name, environment_name=''):
        assert isinstance(asset_value, ValueType)
        found_value = self.get_asset_value_by_name(name, environment_name)
        params = ValueTypeParameters(
            vtName=asset_value.theName,
            vtDesc=asset_value.theDescription,
            vType='asset_value',
            envName=environment_name,
            vtScore=asset_value.theScore,
            vtRat=asset_value.theRationale
        )
        params.setId(found_value.theId)
        try:
            self.db_proxy.updateValueType(params)
        except ARM.DatabaseProxyException as ex:
            self.close()
            raise ARMHTTPError(ex)
        except ARM.ARMException as ex:
            self.close()
            raise ARMHTTPError(ex)

    def check_existing_asset_value(self, name, environment_name):
        try:
            self.get_asset_value_by_name(name, environment_name)
            return True
        except ObjectNotFoundHTTPError:
            return False

    # endregion

    def convert_props(self, real_props=None, fake_props=None):
        new_props = []
        if real_props is not None:
            if len(real_props) > 0:
                for real_prop in real_props:
                    assert isinstance(real_prop, AssetEnvironmentProperties)
                    for idx in range(0, len(real_prop.theAssociations)):
                        real_prop.theAssociations[idx] = list(real_prop.theAssociations[idx])
                    sec_props = real_prop.theProperties
                    rationales = real_prop.theRationale

                    if len(sec_props) == len(rationales):
                        new_sec_attrs = []
                        for idx in range(0, len(sec_props)):
                            try:
                                attr_name = self.rev_attr_dict[idx]
                                attr_value = self.prop_dict[sec_props[idx]]
                                new_sec_attr = SecurityAttribute(attr_name, attr_value, rationales[idx])
                                new_sec_attrs.append(new_sec_attr)
                            except LookupError:
                                self.logger.warning('Unable to find key in dictionary. Attribute is being skipped.')
                        real_prop.theProperties = new_sec_attrs
                        delattr(real_prop, 'theRationale')

                    new_props.append(real_prop)
        elif fake_props is not None:
            if len(fake_props) > 0:
                for fake_prop in fake_props:
                    check_required_keys(fake_prop, AssetEnvironmentPropertiesModel.required)
                    assert isinstance(fake_prop['theAssociations'], list)
                    for idx in range(0, len(fake_prop['theAssociations'])):
                        fake_prop['theAssociations'][idx] = tuple(fake_prop['theAssociations'][idx])
                    sec_attrs = fake_prop['theProperties']
                    new_syProps = array(8 * [0]).astype(numpy.int32)
                    new_rationale = ['None'] * 8

                    for sec_attr in sec_attrs:
                        attr_id = self.attr_dict[sec_attr['name']]
                        attr_value = self.rev_prop_dict[sec_attr['value']]
                        attr_rationale = sec_attr['rationale']
                        new_syProps[attr_id] = attr_value
                        new_rationale[attr_id] = attr_rationale

                    new_prop = AssetEnvironmentProperties(
                        environmentName=fake_prop['theEnvironmentName'],
                        syProperties=new_syProps,
                        pRationale=new_rationale,
                        associations=fake_prop['theAssociations']
                    )
                    new_props.append(new_prop)
        else:
            self.close()
            raise MissingParameterHTTPError(param_names=['real_props', 'fake_props'])

        return new_props

    def from_json(self, request, to_props=False):
        json = request.get_json(silent=True)
        if json is False or json is None:
            self.close()
            raise MalformedJSONHTTPError(data=request.get_data())

        json_dict = json['object']
        if to_props and isinstance(json_dict, list):
            props = self.convert_props(fake_props=json_dict)
            return props
        else:
            assert isinstance(json_dict, dict)
            check_required_keys(json_dict, AssetModel.required)
            json_dict['__python_obj__'] = Asset.__module__+'.'+Asset.__name__
            env_props = json_dict.pop('theEnvironmentProperties', [])
            env_props = self.convert_props(fake_props=env_props)
            json_dict.pop('theEnvironmentDictionary', None)
            json_dict.pop('theAssetPropertyDictionary', None)
            asset = json_serialize(json_dict)
            asset = json_deserialize(asset)

            if isinstance(asset, Asset):
                asset.theEnvironmentProperties = env_props
                return asset
            else:
                self.close()
                raise MalformedJSONHTTPError()

    def simplify(self, asset):
        """
        Simplifies the Asset object by removing the environment properties
        :param asset: The Asset to simplify
        :type asset: Asset
        :return: The simplified Asset
        :rtype: Asset
        """
        assert isinstance(asset, Asset)
        asset.theEnvironmentProperties = self.convert_props(real_props=asset.theEnvironmentProperties)
        asset.theEnvironmentDictionary = {}
        asset.theAssetPropertyDictionary = {}
        return asset
