import os

import bmesh
import bpy
from bpy.app.translations import pgettext
from mathutils import Matrix, Vector
from mathutils.noise import random

from . import reader


def create_armature(context, armature_name, collection, flver_data,
                    connect_bones, axes):
    armature = bpy.data.objects.new(armature_name,
                                    bpy.data.armatures.new(armature_name))
    collection.objects.link(armature)
    armature.show_in_front = True
    if connect_bones:
        armature.data.display_type = "STICK"
    else:
        armature.data.display_type = "WIRE"
    bpy.context.view_layer.objects.active = armature

    bpy.ops.object.mode_set(mode="EDIT", toggle=False)

    root_bones = []
    for flver_bone in flver_data.bones:
        bone = armature.data.edit_bones.new(flver_bone.name)
        if flver_bone.parent_index < 0:
            root_bones.append(bone)

    def transform_bone_and_siblings(bone_index, parent_matrix):
        while bone_index != -1:
            flver_bone = flver_data.bones[bone_index]
            bone = armature.data.edit_bones[bone_index]
            if flver_bone.parent_index >= 0:
                bone.parent = armature.data.edit_bones[flver_bone.parent_index]

            translation_vector = Vector(
                (flver_bone.translation[0], flver_bone.translation[1],
                 flver_bone.translation[2]))
            rotation_matrix = (
                Matrix.Rotation(flver_bone.rotation[1], 4, 'Y')
                @ Matrix.Rotation(flver_bone.rotation[2], 4, 'Z')
                @ Matrix.Rotation(flver_bone.rotation[0], 4, 'X'))

            head = parent_matrix @ translation_vector
            tail = head + rotation_matrix @ Vector((0, 0.05, 0))

            bone.head = (head[axes[0]], head[axes[1]], head[axes[2]])
            bone.tail = (tail[axes[0]], tail[axes[1]], tail[axes[2]])

            # Transform children and advance to next sibling
            transform_bone_and_siblings(
                flver_bone.child_index, parent_matrix
                @ Matrix.Translation(translation_vector) @ rotation_matrix)
            bone_index = flver_bone.next_sibling_index

    transform_bone_and_siblings(0, Matrix())

    def connect_bone(bone):
        children = bone.children
        if len(children) == 0:
            parent = bone.parent
            if parent is not None:
                direction = parent.tail - parent.head
                direction.normalize()
                length = (bone.tail - bone.head).magnitude
                bone.tail = bone.head + direction * length
            return
        if len(children) > 1:
            for child in children:
                connect_bone(child)
            return
        child = children[0]
        bone.tail = child.head
        child.use_connect = True
        connect_bone(child)

    if connect_bones:
        for bone in root_bones:
            connect_bone(bone)

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def run(context, path, transpose_y_and_z, import_skeleton, connect_bones):
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    flver_data = reader.read_flver(path)
    inflated_meshes = flver_data.inflate()

    collection = \
        bpy.context.view_layer.active_layer_collection.collection

    model_name = os.path.splitext(os.path.basename(path))[0]

    if transpose_y_and_z:
        axes = (0, 2, 1)
    else:
        axes = (0, 1, 2)

    # Create armature
    if import_skeleton:
        armature = create_armature(context=context,
                                   armature_name=model_name,
                                   collection=collection,
                                   flver_data=flver_data,
                                   connect_bones=connect_bones,
                                   axes=axes)

    # Create materials
    materials = []
    for flver_material in flver_data.materials:
        material = bpy.data.materials.new(flver_material.name)
        material.diffuse_color = (random(), random(), random(), 1.0)
        materials.append(material)

    for index, (flver_mesh, inflated_mesh) in enumerate(
            zip(flver_data.meshes, inflated_meshes)):
        if inflated_mesh is None:
            continue

        # Construct mesh
        material_name = flver_data.materials[flver_mesh.material_index].name
        verts = [
            Vector((v[axes[0]], v[axes[1]], v[axes[2]]))
            for v in inflated_mesh.vertices.positions
        ]
        mesh_name = f"{model_name}.{index}.{material_name}"
        mesh = bpy.data.meshes.new(name=mesh_name)
        mesh.from_pydata(verts, [], inflated_mesh.faces)

        # Create object
        obj = bpy.data.objects.new(mesh_name, mesh)
        collection.objects.link(obj)

        # Assign armature
        if import_skeleton:
            obj.modifiers.new(type="ARMATURE",
                              name=pgettext("Armature")).object = armature
            obj.parent = armature

        # Assign material
        obj.data.materials.append(materials[flver_mesh.material_index])

        # Create vertex groups for bones
        for bone_index in flver_mesh.bone_indices:
            obj.vertex_groups.new(name=flver_data.bones[bone_index].name)

        bm = bmesh.new()
        bm.from_mesh(mesh)

        uv_layer = bm.loops.layers.uv.new()
        for face in bm.faces:
            for loop in face.loops:
                u, v = inflated_mesh.vertices.uv[loop.vert.index]
                loop[uv_layer].uv = (u, 1.0 - v)
        if import_skeleton:
            weight_layer = bm.verts.layers.deform.new()
            for vert in bm.verts:
                weights = inflated_mesh.vertices.bone_weights[vert.index]
                indices = inflated_mesh.vertices.bone_indices[vert.index]
                for index, weight in zip(indices, weights):
                    if weight == 0.0:
                        continue
                    vert[weight_layer][index] = weight

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
