bl_info = {
    "name": "Import Fromsoft FLVER models",
    "description":
    "Import models from various Fromsoft games such as Dark Souls",
    "author": "Eliza Velasquez",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "category": "Import-Export",
    "location": "File > Import",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "",  # TODO: wiki url
    "tracker_url": "",  # TODO: tracker url
}

_submodules = {
    "importer",
    "flver",
    "reader",
}

# Reload submodules on addon reload
if "bpy" in locals():
    import importlib
    for submodule in _submodules:
        if submodule in locals():
            importlib.reload(locals()[submodule])

import bpy
from . import importer
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty


class FlverImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.flver"
    bl_label = "Fromsoft (.flver)"

    filter_glob = StringProperty(default="*.flver", options={"HIDDEN"})

    transpose_y_and_z = BoolProperty(
        name="Transpose Y and Z axes",
        description=("This will correct the orientation of the model. " +
                     "Rarely necessary to disable."),
        default=True)

    import_skeleton = BoolProperty(
        name="Import skeleton",
        description=("Disable to prevent the creation of an Armature " +
                     "and corresponding vertex groups."),
        default=True)

    connect_bones = BoolProperty(
        name="Connect bones",
        description=(
            "Disable to import disjointed bones rotated about their " +
            "original Euler angles. This may be potentially desireable "
            "for authoring derivative FLVER files."),
        default=True)

    def execute(self, context):
        importer.run(context=context,
                     path=self.filepath,
                     transpose_y_and_z=self.transpose_y_and_z,
                     import_skeleton=self.import_skeleton,
                     connect_bones=self.connect_bones)
        return {"FINISHED"}


def menu_import(self, context):
    self.layout.operator(FlverImporter.bl_idname)


def register():
    bpy.utils.register_class(FlverImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.utils.unregister_class(FlverImporter)
