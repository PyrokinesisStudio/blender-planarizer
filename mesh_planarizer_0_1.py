# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    'name': 'Planarizer',
    'author': "Mark Riedesel",
    'version': (0, 1, 0),
    'blender': (2, 66, 3),
    'location': "Editmode > D",
    'warning': "",
    'description': "Corrects non-planar quads",
    'category': 'Mesh'}

import bmesh
import mathutils
import bpy
import itertools
from bpy_extras import view3d_utils


def project_to_plane(point, va, vb):
    va.normalize()
    vb.normalize()
    norm = va.cross(vb)
    norm.normalize()

    adjust = mathutils.Vector()

    adjust = norm.dot(point)
    return norm.xyz * adjust


def fix_nonplanar_face(bm, vert_sel, context, event):
    ob = context.active_object
    region = context.region
    region_3d = context.space_data.region_3d

    # Find linked edges that are connected to faces
    edges = [edge for edge in vert_sel.link_edges if len(edge.link_faces) > 0]

    # Get all connected quads
    faces = [face for face in vert_sel.link_faces if len(face.verts) == 4]

    # Find optimal face to project the selected vertex to
    mouse_pos = mathutils.Vector([event.mouse_region_x, event.mouse_region_y])
    optimal_faces = []
    min_dist = False

    for face in faces:
        face_pos = face.calc_center_bounds()
        world_face_pos = ob.matrix_world * face_pos
        screen_face_pos = view3d_utils.location_3d_to_region_2d(region,
                                                                region_3d,
                                                                world_face_pos)

        dist = (mouse_pos - screen_face_pos).length
        if not min_dist or dist < min_dist[0]:
            min_dist = (dist, face)

    optimal_faces.append(min_dist)

    # Find edges that do not contain selected vertex
    face = optimal_faces[0][1]

    # Find the unselected vertices of the face
    face_verts = [v for v in face.verts if not v.select]

    # Find the edges of the face that don't contain the selected vertex
    face_edges = [edge for edge in face.edges if vert_sel not in edge.verts]

    # Find the middle vertex shared between the two edges
    middle_vert = None
    for v in face_verts:
        middle_vert = (v if v in face_edges[0].verts and
                       v in face_edges[1].verts else None)
        if middle_vert:
            break

    other_verts = []
    for edge in face_edges:
        v = [v for v in edge.verts if not v == middle_vert]
        other_verts.append(v[0])

    selected_vect = vert_sel.co - middle_vert.co
    plane_va = middle_vert.co - other_verts[0].co
    plane_vb = middle_vert.co - other_verts[1].co

    new_vertex = project_to_plane(selected_vect, plane_va, plane_vb)

    vert_sel.co.xyz = (vert_sel.co - new_vertex)

    # Update display
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')


class MeshPlanarizer(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "mesh.planarizer"
    bl_label = "Fix non-planar quad"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        bm = bmesh.from_edit_mesh(context.active_object.data)
        selected_verts = [v for v in bm.verts if v.select]

        fix_nonplanar_face(bm, selected_verts[0], context, event)
        return {'FINISHED'}


classes = [MeshPlanarizer]
addon_keymaps = []


def register():
    # add operator
    for c in classes:
        bpy.utils.register_class(c)

    # add keymap entry
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
        name='Mesh',
        space_type='EMPTY')
    kmi = km.keymap_items.new("mesh.planarizer", "D", "PRESS")
    addon_keymaps.append(km)


def unregister():
    # remove operator
    for c in classes:
        bpy.utils.unregister_class(c)

    # remove keymap
    for km in addon_keymaps:
        bpy.context.window_manager.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

if __name__ == '__main__':
    register()
