"""Renderiza la animación de armado (cuadros 1 a 96) desde hamburguesa.blend.
Uso: blender -b out/hamburguesa.blend --python animacion.py
Variables: HB_PORC (porcentaje de resolución, 60 por defecto), HB_MUESTRAS (48 por defecto)."""
import os

import bpy

OUT = os.environ.get('HB_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'))
scene = bpy.context.scene
scene.camera = bpy.data.objects['Camara_Animacion']
r = scene.render
r.resolution_x, r.resolution_y = 1080, 1350
r.resolution_percentage = int(os.environ.get('HB_PORC', '60'))
scene.cycles.samples = int(os.environ.get('HB_MUESTRAS', '48'))
scene.cycles.adaptive_threshold = 0.03
r.fps = 24
scene.frame_start, scene.frame_end = 1, 96
r.image_settings.file_format = 'PNG'
r.filepath = os.path.join(OUT, 'anim', 'f_')
bpy.ops.render.render(animation=True)
print('HB: animacion lista')
