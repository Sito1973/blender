import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix
OUT = sys.argv[sys.argv.index("--") + 1]
dat = json.load(open('/home/user/blender/lampara_roseta/datos_pieza.json'))
rho = dat['curva']['radio_doblez_eje']
sc = bpy.context.scene
# ocultar pieza suelta, textos y meridianos
for c in bpy.data.collections:
    if c.name.startswith('1_PIEZA') or c.name.startswith('Meridianos'):
        c.hide_render = True
src = bpy.data.objects['Curva_01A']
src.hide_render = True
# copia resaltada de la curva 01A
cu = src.data.copy()
hl = bpy.data.objects.new('Curva_resaltada', cu)
sc.collection.objects.link(hl)
hl.matrix_world = src.matrix_world.copy()
m = bpy.data.materials.new('Naranja'); m.use_nodes = True
b = m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (1.0, 0.35, 0.08, 1); b.inputs['Roughness'].default_value = 0.35
b.inputs['Emission Color'].default_value = (1.0, 0.3, 0.05, 1); b.inputs['Emission Strength'].default_value = 0.6
cu.materials.clear(); cu.materials.append(m)
cu.bevel_depth = 5.0  # un poco más gruesa para que se vea
# disco del plano (círculo completo de la curva)
me = bpy.data.meshes.new('Plano'); bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, radius=rho, segments=160)
bm.to_mesh(me); bm.free()
disc = bpy.data.objects.new('Plano_curva', me); sc.collection.objects.link(disc)
disc.matrix_world = src.matrix_world.copy()
pm = bpy.data.materials.new('Plano'); pm.use_nodes = True
pb = pm.node_tree.nodes['Principled BSDF']
pb.inputs['Base Color'].default_value = (0.35, 0.6, 1.0, 1); pb.inputs['Alpha'].default_value = 0.22; pb.inputs['Roughness'].default_value = 0.8
pb.inputs['Emission Color'].default_value = (0.3, 0.55, 1.0, 1); pb.inputs['Emission Strength'].default_value = 0.25
me.materials.append(pm)
# borde del círculo completo (línea fina)
ring = bpy.data.curves.new('Borde', 'CURVE'); ring.dimensions = '3D'
sp = ring.splines.new('POLY'); n = 160; sp.points.add(n - 1)
for i in range(n):
    t = 2 * math.pi * i / n; sp.points[i].co = (rho * math.cos(t), rho * math.sin(t), 0, 1)
sp.use_cyclic_u = True; ring.bevel_depth = 1.2
rm = bpy.data.materials.new('Borde'); rm.use_nodes = True
rm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.45, 0.7, 1.0, 1)
ring.materials.append(rm)
ro = bpy.data.objects.new('Borde_plano', ring); sc.collection.objects.link(ro); ro.matrix_world = src.matrix_world.copy()
# render
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 900
sc.render.film_transparent = False
bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.035, 0.035, 0.04, 1)
# vectores del plano
M = src.matrix_world
nrm = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
mid = M @ Vector((rho, 0, 0))
strike = nrm.cross(Vector((0, 0, 1))).normalized()   # horizontal y dentro del plano
def cam(name, loc, target, ortho=None, lens=40, up=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 1; cd.clip_end = 100000
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob); ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob
views = []
# 1) desde abajo: parece espiral (sin el plano)
views.append(('1_abajo', cam('C1', (0.01, 0.01, -1250), (0, 0, 0), lens=35), False))
# 2) 3/4 con el plano inclinado
views.append(('2_plano', cam('C2', (900, -1150, 380), (120, 60, 110), lens=38), True))
# 3) de canto, mirando a lo largo de la línea horizontal del plano: la curva se ve recta e inclinada
views.append(('3_canto', cam('C3', tuple(mid + strike * 3000), tuple(mid), ortho=700), True))
for name, ob, show_plane in views:
    disc.hide_render = ro.hide_render = not show_plane
    sc.camera = ob
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
print('INCL', dat['curva']['inclinacion_plano_vs_horizontal_deg'])
