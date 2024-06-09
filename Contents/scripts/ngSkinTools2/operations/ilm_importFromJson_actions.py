"""
DESCRIPTION:
    This file is an additional function menu in the NGSkin Tool window. It has two menus:
    1. Retrieving data joints that have already been exported.
    2. Binding the geo selected with the joints data and then running the imported layer window.

USAGE:
    1. Run the "Select all the joint list" then all the joints in the scene will be selected according to the .json data.
    2. - Select the geo without the skin weight.
       - Run the "Binding skin and import layer.."
       - The geo will be bound to the joints in the scene according to the .json data.
       - Import layer window will be run automatically.

AUTHOR:
    Adien Dendra - adendra@ilm.com

"""
from PySide2 import QtWidgets
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om


from ngSkinTools2 import api
from ngSkinTools2.ui.options import PersistentValue
from ngSkinTools2.api import plugin
from ngSkinTools2.api.import_export import FileFormatWrapper

filter_normal_json = 'JSON files(*.json)'
filter_compressed = 'Compressed JSON(*.json.gz)'
file_dialog_filters = ";;".join([filter_normal_json, filter_compressed])

format_map = {
    filter_normal_json: api.FileFormat.JSON,
    filter_compressed: api.FileFormat.CompressedJSON,
}

default_filter = PersistentValue("default_import_filter", default_value=api.FileFormat.JSON)

def ilm_data_list(file_name, selected_format):

    with FileFormatWrapper(file_name, format=format_map[selected_format], read_mode=True) as f:
        data = plugin.ngst2tools(
            tool="importJsonFile",
            file=f.plain_file,
        )

    # query the joint data
    data_values = (data.values())
    jointsSelectList = []
    for values in data_values:
        jointsSelectList = [(item['path']) for item in values]

    newList = []
    for object in jointsSelectList:
        if cmds.objExists(object):
            newList.append(object)
        else:
            objectName = object.split("|")
            cmds.warning("'{}'{}".format(objectName[-1], " doesn't exist in the scene, skip!"))

    if not newList:
        raise IndexError('Nothing object is matched between the data and the scene!')

    return newList


def ilm_importJointList(parent, file_dialog_func=None):
    from ngSkinTools2.ui import actions

    def default_file_dialog_func():
        file_name, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            parent, "Select all the joint list", filter=file_dialog_filters, selectedFilter=default_filter.get()
        )
        if file_name:
            default_filter.set(selected_filter)
        return file_name, selected_filter

    if file_dialog_func is None:
        file_dialog_func = default_file_dialog_func

    def import_callback():
        file_name, selected_format = file_dialog_func()
        if not file_name:
            return

        # listing the data
        list_data = ilm_data_list(file_name, selected_format)
        cmds.select(list_data, r=True)

        # show the list info
        list_name = [item.split("|")[-1] for item in list_data]
        om.MGlobal.displayInfo('{}{}'.format('Object selected list >>> ', list_name))

    result = actions.define_action(parent, "Select all the joint list", callback=import_callback,
                                   tooltip="Load previously joints exported weights")

    return result

def ilm_bindSkinAndImportLayer(parent, file_dialog_func=None):
    from ngSkinTools2.ui import actions
    from ngSkinTools2.ui.transferDialog import LayersTransfer, UiModel, open

    def default_file_dialog_func():
        file_name, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            parent, "Bind skin and import layer", filter=file_dialog_filters, selectedFilter=default_filter.get()
        )
        if file_name:
            default_filter.set(selected_filter)

        return file_name, selected_filter

    if file_dialog_func is None:
        file_dialog_func = default_file_dialog_func


    def import_callback_bindSkin():
        # condition if mesh select or not
        if len (cmds.ls(sl=True)) != 1:
            raise ValueError('Please select one object geo!')

        # filter object mesh selection
        object_mesh = cmds.ls(sl=True, dag=True, type="mesh", long=True)
        if not object_mesh:
            raise ValueError('Please select a geo object!')

        # target object to be skinned
        geo =[]
        new_list = cmds.listRelatives(object_mesh, ap=True, f=True)
        [geo.append(i) for i in new_list if i not in geo]

        # condition objet has a skin weight
        target_geo = mel.eval('findRelatedSkinCluster ' + geo[0])
        if target_geo:
            raise ValueError('The object geo already has a skin weight!')

        # take the joint data list
        file_name, selected_format = file_dialog_func()
        if not file_name:
            return

        # listing the data
        list_data = ilm_data_list(file_name, selected_format)

        # bind skin joint to geo selected
        update_skinWeight_name = cmds.skinCluster(list_data, geo[0], mi=5, omi=False, rui=False, tsb=True)

        def transfer_dialog(transfer):
            model = UiModel()
            model.transfer = transfer
            open(parent, model)

        # data layer weight
        t = LayersTransfer()
        t.load_source_from_file(file_name, format=format_map[selected_format])
        t.target = update_skinWeight_name[0]
        t.customize_callback = transfer_dialog
        t.execute()

    result = actions.define_action(parent, "Binding skin and import layer..", callback=import_callback_bindSkin, tooltip="Load previously layers exported weights")

    return result
