import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def mat(name, rgb, metal=0.0, rough=0.4):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return m
bpy.ops.mesh.primitive_plane_add(size=20)
bpy.context.object.data.materials.append(mat("Piso", (0.8, 0.8, 0.82), rough=0.6))
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 1.2), rotation=(0, 0, math.radians(-20)))
o = bpy.context.object
o.modifiers.new("s", "SUBSURF").levels = 2
bpy.ops.object.shade_smooth()
o.data.materials.append(mat("Oro", (1.0, 0.7, 0.2), metal=1.0, rough=0.25))
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(2.2, 0.8, 0.6)); bpy.ops.object.shade_smooth()
bpy.context.object.data.materials.append(mat("Azul", (0.1, 0.25, 0.9)))
bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.2, 0.5, 0.5), rotation=(0, 0, 0.5))
bpy.context.object.data.materials.append(mat("Rojo", (0.9, 0.15, 0.1)))
bpy.ops.object.light_add(type="AREA", location=(4, -4, 6)); l = bpy.context.object
l.data.energy = 1500; l.data.size = 4; l.rotation_euler = (math.radians(45), 0, math.radians(45))
bpy.ops.object.camera_add(location=(0, -7.5, 3.2), rotation=(math.radians(72), 0, 0))
sc.camera = bpy.context.object
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.7, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 64
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.filepath = "/home/user/blender/demo_3d/render.png"
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath="/home/user/blender/demo_3d/escena.blend")
