"""
Lámpara roseta – estructura metálica
====================================

Genera en Blender la estructura de la lámpara (aro exterior, disco central,
48 curvas y, opcional, 24 meridianos) y la PIEZA ÚNICA ("curvita") que se
repite.

Cómo usar
---------
  blender --factory-startup -b -P generar_lampara.py -- <carpeta_salida>

o bien abrir Blender > Scripting > abrir este archivo > Run Script.

Todas las medidas están en milímetros (la escena usa 1 unidad = 1 mm).
Cambie los PARÁMETROS y vuelva a correr el script para otro tamaño.

Geometría
---------
El domo es un casquete esférico. Cada "pétalo" es el corte de esa esfera con
un plano que pasa por el centro de arriba, así que cada curva es un ARCO DE
CÍRCULO PLANO de radio constante. El aro corta cada pétalo en dos mitades:
esas mitades son las 48 curvas, todas idénticas (las que giran a la izquierda
son la misma pieza volteada). Para el herrero: una sola pieza, doblada a un
radio fijo, repetida 48 veces.
"""

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

# =====================================================================
# PARÁMETROS (mm)
# =====================================================================
DIAMETRO_ARO = 900.0       # diámetro al que llegan las varillas (eje del aro)
ALTURA_DOMO = 250.0        # altura del domo: del plano del aro al centro de arriba
N_PETALOS = 24             # pétalos; cada uno da 2 curvas -> 48 curvas
SALTO_V = 4                # en el aro, cada curva se junta (en "V") con la de un
                           # pétalo SALTO_V posiciones más allá. 4 -> llega a 30°
RADIO_FIN_CENTRO = 70.0    # radio (en planta) donde terminan las curvas en el centro
DIAM_VARILLA = 6.0         # varilla redonda maciza
ARO_ANCHO = 20.0           # aro exterior: ancho radial (pletina)
ARO_ESPESOR = 5.0          # aro exterior: espesor
DISCO_DIAM = 170.0         # disco central donde se sueldan las curvas
DISCO_ESPESOR = 5.0
MERIDIANOS = True          # 24 varillas rectas (en planta) del centro al aro,
MER_PASA_ARO = True        # los meridianos entran por una ranura del aro y bajan
                           # hasta su cara de abajo (se sueldan arriba y abajo)
                           # donde la lámpara original lleva las tiras de luz

SEG_ARCO = 97              # puntos por arco (suavidad; error < 0.02 mm)

# Medidas desde la línea de comandos (opcional), p. ej.:
#   blender -b -P generar_lampara.py -- d80 --D 800 --H 220
_ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _opcion(nombre, valor):
    if "--" + nombre in _ARGS:
        return float(_ARGS[_ARGS.index("--" + nombre) + 1])
    return valor


DIAMETRO_ARO = _opcion("D", DIAMETRO_ARO)
ALTURA_DOMO = _opcion("H", ALTURA_DOMO)
N_PETALOS = int(_opcion("petalos", N_PETALOS))
RADIO_FIN_CENTRO = _opcion("rh", RADIO_FIN_CENTRO)
DIAM_VARILLA = _opcion("varilla", DIAM_VARILLA)
DISCO_DIAM = _opcion("disco", DISCO_DIAM)

# =====================================================================
# GEOMETRÍA
# =====================================================================
a = DIAMETRO_ARO / 2.0
H = ALTURA_DOMO
Rs = (a * a + H * H) / (2.0 * H)       # radio de la esfera del domo
zc = H - Rs                            # z del centro de la esfera (aro en z=0)
paso = 2.0 * math.pi / N_PETALOS
alpha = SALTO_V * paso / 2.0           # ángulo (en planta) donde la curva toca el aro
th_rim = math.asin(a / Rs)
th_hub = math.asin(RADIO_FIN_CENTRO / Rs)
P = Vector((0.0, 0.0, Rs))             # polo (centro de arriba), coords de esfera


def petal(thq):
    """Círculo del pétalo: pasa por el polo P y por Q (ángulo polar thq, azimut 0)."""
    Q = Rs * Vector((math.sin(thq), 0.0, math.cos(thq)))
    C = (P + Q) / 2.0
    rho = (P - Q).length / 2.0
    u = (P - C) / rho
    v = Vector((0.0, 1.0, 0.0))
    return C, rho, u, v


def petal_point(thq, s):
    C, rho, u, v = petal(thq)
    return C + rho * (math.cos(s) * u + math.sin(s) * v)


def bisect(f, lo, hi, it=200):
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        if f(mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def s_rim(thq):
    # parámetro s donde el pétalo cruza el plano del aro (z = 0)
    return bisect(lambda s: petal_point(thq, s).z + zc > 0.0, 0.0, math.pi)


def rim_azimuth(thq):
    p = petal_point(thq, s_rim(thq))
    return math.atan2(p.y, p.x)


thq = bisect(lambda t: rim_azimuth(t) < alpha, th_rim + 1e-9, math.pi * 0.95)
C, rho, u, v = petal(thq)
s1 = s_rim(thq)
s0 = bisect(lambda s: math.hypot(*petal_point(thq, s).xy) < RADIO_FIN_CENTRO, 0.0, s1)
THETA = s1 - s0                         # ángulo del arco de la pieza
sm = 0.5 * (s0 + s1)
C_world = C + Vector((0.0, 0.0, zc))    # centro del círculo de doblez (mundo)

largo = rho * THETA
cuerda = 2.0 * rho * math.sin(THETA / 2.0)
flecha = rho * (1.0 - math.cos(THETA / 2.0))
p_hub = petal_point(thq, s0) + Vector((0, 0, zc))
p_rim = petal_point(thq, s1) + Vector((0, 0, zc))
p_mid = petal_point(thq, sm) + Vector((0, 0, zc))
normal_plano = u.cross(v)
inclin_plano = math.degrees(math.acos(abs(normal_plano.z)))

# fin del meridiano: en la cara de arriba del aro (z = 0) o, si pasa por la
# ranura, en la cara de abajo (z = -ARO_ESPESOR), siguiendo la misma esfera
th_mer_fin = math.acos((-ARO_ESPESOR - zc) / Rs) if MER_PASA_ARO else th_rim
mer_ang = th_mer_fin - th_hub
mer_largo = Rs * mer_ang
# los meridianos van entre las "V" del aro
mer_offset = paso / 2.0 if SALTO_V % 2 == 0 else 0.0

r_rod = DIAM_VARILLA / 2.0


def z_esfera(r):
    return zc + math.sqrt(Rs * Rs - r * r)


DATOS = {
    "unidades": "mm",
    "diametro_aro_eje": DIAMETRO_ARO,
    "diametro_exterior_total": DIAMETRO_ARO + ARO_ANCHO,
    "altura_domo_eje": ALTURA_DOMO,
    "radio_esfera_domo": Rs,
    "n_petalos": N_PETALOS,
    "n_curvas": 2 * N_PETALOS,
    "salto_v": SALTO_V,
    "angulo_llegada_aro_deg": math.degrees(alpha),
    "diam_varilla": DIAM_VARILLA,
    "curva": {
        "radio_doblez_eje": rho,
        "radio_interior": rho - r_rod,
        "radio_exterior": rho + r_rod,
        "angulo_arco_deg": math.degrees(THETA),
        "largo_desarrollado_eje": largo,
        "cuerda": cuerda,
        "flecha": flecha,
        "extremo_centro_xyz": list(p_hub),
        "extremo_aro_xyz": list(p_rim),
        "punto_medio_xyz": list(p_mid),
        "centro_doblez_xyz": list(C_world),
        "inclinacion_plano_vs_horizontal_deg": inclin_plano,
        "extremo_centro_r_ang_z": [math.hypot(p_hub.x, p_hub.y),
                                   math.degrees(math.atan2(p_hub.y, p_hub.x)), p_hub.z],
        "extremo_aro_r_ang_z": [math.hypot(p_rim.x, p_rim.y),
                                math.degrees(math.atan2(p_rim.y, p_rim.x)), p_rim.z],
        "punto_medio_r_ang_z": [math.hypot(p_mid.x, p_mid.y),
                                math.degrees(math.atan2(p_mid.y, p_mid.x)), p_mid.z],
    },
    "meridiano": {
        "incluido": MERIDIANOS,
        "cantidad": N_PETALOS,
        "radio_doblez_eje": Rs,
        "angulo_arco_deg": math.degrees(mer_ang),
        "largo_desarrollado_eje": mer_largo,
        "cuerda": 2 * Rs * math.sin(mer_ang / 2),
        "angulo_primer_meridiano_deg": math.degrees(mer_offset),
        "pasa_por_el_aro": MER_PASA_ARO,
        "llegada_al_aro_deg": math.degrees(th_rim),
    },
    "aro": {"ancho": ARO_ANCHO, "espesor": ARO_ESPESOR,
            "diam_interior": DIAMETRO_ARO - ARO_ANCHO,
            "diam_exterior": DIAMETRO_ARO + ARO_ANCHO,
            "largo_desarrollado_eje": math.pi * DIAMETRO_ARO},
    "disco": {"diametro": DISCO_DIAM, "espesor": DISCO_ESPESOR},
}

# =====================================================================
# ESCENA
# =====================================================================
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
HACER_RENDERS = "--sin-renders" not in argv

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for coll in list(bpy.data.collections):
    bpy.data.collections.remove(coll)
for c in list(bpy.data.curves):
    bpy.data.curves.remove(c)

sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = "MILLIMETERS"


def new_coll(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or sc.collection).children.link(col)
    return col


def mat(name, color, metallic=0.7, rough=0.4, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    m.diffuse_color = (*color, 1.0)
    return m


M_CURVA = mat("Metal_curvas", (0.78, 0.62, 0.42), 0.35, 0.45)
M_MER = mat("Metal_meridianos", (0.90, 0.82, 0.68), 0.3, 0.45)
M_ARO = mat("Metal_aro", (0.74, 0.60, 0.42), 0.35, 0.45)
M_DISCO = mat("Metal_disco", (0.72, 0.58, 0.40), 0.35, 0.45)
M_TXT = mat("Texto_cotas", (0.05, 0.05, 0.06), 0.0, 0.8)
M_COTA = mat("Lineas_cotas", (0.75, 0.10, 0.08), 0.0, 0.6)


def curve_data(name, pts, radius, closed=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_cyclic_u = closed
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    return cu


def link(name, data, col, matrix=None, material=None):
    ob = bpy.data.objects.new(name, data)
    col.objects.link(ob)
    if matrix is not None:
        ob.matrix_world = matrix
    if material and not ob.data.materials:
        ob.data.materials.append(material)
    return ob


# ---------- datos compartidos: la PIEZA (arco plano en su plano XY) ----------
# El origen local es el CENTRO DEL DOBLEZ. Extremo del centro en t=-THETA/2,
# extremo del aro en t=+THETA/2.
pts_curva = []
for i in range(SEG_ARCO):
    t = -THETA / 2 + THETA * i / (SEG_ARCO - 1)
    pts_curva.append((rho * math.cos(t), rho * math.sin(t), 0.0))
CURVA = curve_data("PIEZA_curva", pts_curva, r_rod)
CURVA.materials.append(M_CURVA)

pts_mer = []
for i in range(SEG_ARCO):
    th = th_hub + mer_ang * i / (SEG_ARCO - 1)
    pts_mer.append((Rs * math.sin(th), Rs * math.cos(th), 0.0))
MERID = curve_data("PIEZA_meridiano", pts_mer, r_rod)
MERID.materials.append(M_MER)

# ---------- colecciones ----------
C_PIEZA = new_coll("1_PIEZA_UNICA_curva_x%d" % (2 * N_PETALOS))
C_LAMP = new_coll("2_LAMPARA_COMPLETA")
C_CURVAS = new_coll("Curvas_x%d" % (2 * N_PETALOS), C_LAMP)
C_MER = new_coll("Meridianos_x%d (opcional)" % N_PETALOS, C_LAMP)
C_ARO = new_coll("Aro_exterior", C_LAMP)
C_DISCO = new_coll("Disco_central", C_LAMP)

# ---------- 48 curvas: copias enlazadas de la MISMA pieza ----------
for k in range(N_PETALOS):
    Rz = Matrix.Rotation(k * paso, 3, "Z")
    for lado, w in (("A", v), ("B", -v)):
        e1 = math.cos(sm) * u + math.sin(sm) * w
        e2 = -math.sin(sm) * u + math.cos(sm) * w
        n = e1.cross(e2)
        R = Matrix((e1, e2, n)).transposed()
        Cw = C + Vector((0, 0, zc))
        Cw = Vector((Cw.x, Cw.y * (1 if lado == "A" else -1), Cw.z))
        M = Matrix.Translation(Rz @ Cw) @ (Rz @ R).to_4x4()
        link("Curva_%02d%s" % (k + 1, lado), CURVA, C_CURVAS, M)

# ---------- meridianos ----------
if MERIDIANOS:
    base = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0))).transposed()
    for k in range(N_PETALOS):
        Rz = Matrix.Rotation(mer_offset + k * paso, 3, "Z")
        M = Matrix.Translation((0, 0, zc)) @ (Rz @ base).to_4x4()
        link("Meridiano_%02d" % (k + 1), MERID, C_MER, M)
else:
    C_MER.hide_render = True
    C_MER.hide_viewport = True


# ---------- aro exterior (pletina, cara de arriba en z=0) ----------
def ring_mesh(name, r_in, r_out, z0, z1, seg=360):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        ang = 2 * math.pi * i / seg
        c, s = math.cos(ang), math.sin(ang)
        rings.append([bm.verts.new((r * c, r * s, z)) for r, z in
                      ((r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1))])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(4):
            bm.faces.new((A[j], A[(j + 1) % 4], B[(j + 1) % 4], B[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


aro = link("Aro_exterior", ring_mesh("Aro_exterior", a - ARO_ANCHO / 2, a + ARO_ANCHO / 2,
                                      -ARO_ESPESOR, 0.0), C_ARO, material=M_ARO)

# ---------- disco central ----------
me = bpy.data.meshes.new("Disco_central")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=128,
                      radius1=DISCO_DIAM / 2, radius2=DISCO_DIAM / 2, depth=DISCO_ESPESOR)
bm.to_mesh(me)
bm.free()
z_disco_top = z_esfera((RADIO_FIN_CENTRO + DISCO_DIAM / 2) / 2) - r_rod
disco = link("Disco_central", me, C_DISCO,
             Matrix.Translation((0, 0, z_disco_top - DISCO_ESPESOR / 2)), M_DISCO)

# ---------- PIEZA ÚNICA acostada en el piso, al lado de la lámpara ----------
# Se gira para que la cuerda quede horizontal y la panza hacia abajo.
X0 = a + 380.0
M_pieza = Matrix.Translation((X0, -rho + flecha / 2 - 40, 0.0)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
pieza = link("PIEZA_curva_unica", CURVA, C_PIEZA, M_pieza)


def pieza_xy(t):
    return M_pieza @ Vector((rho * math.cos(t), rho * math.sin(t), 0.0))


def texto(body, loc, size=16.0, col=C_PIEZA, align="CENTER", name=None, rot=0.0):
    cu = bpy.data.curves.new(name or "txt", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = link(name or "Texto", cu, col, material=M_TXT)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot)
    return ob


def linea(name, pts, col=C_PIEZA, r=0.8, material=M_COTA):
    cu = curve_data(name, pts, r)
    cu.materials.append(material)
    return link(name, cu, col)


c_pieza = M_pieza @ Vector((0, 0, 0))
e_hub = pieza_xy(-THETA / 2)
e_rim = pieza_xy(THETA / 2)
e_mid = pieza_xy(0.0)
linea("Cota_cuerda", [e_hub + Vector((0, 0, 0)), e_rim])
linea("Cota_radio_1", [c_pieza, e_hub], r=0.5)
linea("Cota_radio_2", [c_pieza, e_rim], r=0.5)
linea("Cota_flecha", [(e_hub + e_rim) / 2, e_mid], r=0.5)
texto("PIEZA ÚNICA – hacer %d" % (2 * N_PETALOS), e_mid + Vector((0, 70, 0)), 22, name="T_titulo")
texto("Varilla Ø%.0f mm – arco plano" % DIAM_VARILLA, e_mid + Vector((0, 42, 0)), 14, name="T_varilla")
texto("R = %.1f mm (al eje)" % rho, (c_pieza + e_hub) / 2 + Vector((95, -10, 0)), 14, name="T_radio")
texto("Ángulo = %.1f°" % math.degrees(THETA), c_pieza + Vector((0, 40, 0)), 14, name="T_angulo")
texto("Cuerda = %.1f mm" % cuerda, (e_hub + e_rim) / 2 + Vector((0, -16, 0)), 14, name="T_cuerda")
texto("Flecha = %.1f mm" % flecha, (e_hub + e_rim) / 2 + Vector((70, flecha / 2, 0)), 12, name="T_flecha")
texto("Largo desarrollado = %.1f mm" % largo, e_mid + Vector((0, 18, 0)), 14, name="T_largo")
texto("extremo CENTRO", e_hub + Vector((0, -30, 0)), 12, name="T_ext_centro")
texto("extremo ARO", e_rim + Vector((0, -30, 0)), 12, name="T_ext_aro")
texto("centro del doblez", c_pieza + Vector((0, -18, 0)), 11, name="T_centro")

# ---------- vista del 3D Viewport ----------
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == "VIEW_3D":
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.clip_start = 1.0
                    sp.clip_end = 100000.0
                    r3d = sp.region_3d
                    r3d.view_location = (X0 / 2, -100, 100)
                    r3d.view_distance = 2600
                    sp.shading.type = "SOLID"
                    sp.shading.color_type = "MATERIAL"

# ---------- datos ----------
with open(os.path.join(OUT, "datos_pieza.json"), "w", encoding="utf-8") as f:
    json.dump(DATOS, f, indent=2, ensure_ascii=False)
c01 = bpy.data.objects["Curva_01A"].matrix_world
GEO = {
    "paso_deg": math.degrees(paso),
    "mer_offset_deg": math.degrees(mer_offset),
    "radio_fin_centro": RADIO_FIN_CENTRO,
    "a": a,
    "curva_01A_mundo": [list(c01 @ Vector(p)) for p in pts_curva],
    "curva_local": [list(p) for p in pts_curva],
}
with open(os.path.join(OUT, "geometria.json"), "w", encoding="utf-8") as f:
    json.dump(GEO, f)

# ---------- exportar STL / OBJ ----------
dg = bpy.context.evaluated_depsgraph_get()


def exportar(objs, path, fmt="STL"):
    tmp = new_coll("_tmp_export")
    temps = []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        t = bpy.data.objects.new(ob.name, me)
        t.matrix_world = ob.matrix_world
        tmp.objects.link(t)
        temps.append(t)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for t in temps:
        t.select_set(True)
    if fmt == "STL":
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              ascii_format=False, apply_modifiers=True)
    else:
        bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True,
                              export_materials=False, forward_axis="Y", up_axis="Z")
    for t in temps:
        me = t.data
        bpy.data.objects.remove(t, do_unlink=True)
        bpy.data.meshes.remove(me)
    bpy.data.collections.remove(tmp)


# pieza suelta exportada en su sistema local (centro del doblez en el origen)
pieza.matrix_world = Matrix.Identity(4)
exportar([pieza], os.path.join(OUT, "curva_unica.stl"))
pieza.matrix_world = M_pieza

lamp_objs = list(C_CURVAS.objects) + list(C_ARO.objects) + list(C_DISCO.objects)
if MERIDIANOS:
    lamp_objs += list(C_MER.objects)
exportar(lamp_objs, os.path.join(OUT, "lampara_completa.stl"))
exportar(lamp_objs, os.path.join(OUT, "lampara_completa.obj"), "OBJ")

# ---------- renders ----------
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.resolution_x = 1400
sc.render.resolution_y = 1050
sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX"

world = sc.world or bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.82, 0.83, 0.86, 1.0)
bg.inputs["Strength"].default_value = 0.9

C_LUZ = new_coll("Luces_y_camaras")


def sol(name, rot, energy):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = energy
    ld.angle = math.radians(8)
    ob = link(name, ld, C_LUZ)
    ob.rotation_euler = rot
    return ob


sol("Sol_arriba", (math.radians(35), 0, math.radians(30)), 3.5)
sol("Sol_abajo", (math.radians(150), 0, math.radians(-60)), 3.0)
sol("Sol_abajo_2", (math.radians(200), 0, math.radians(70)), 1.5)


def camara(name, loc, target, lens=35.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 1.0
    cd.clip_end = 100000.0
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = link(name, cd, C_LUZ)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


cams = {
    "render_3_4.png": camara("Cam_3_4", (820, -900, -520), (0, 0, 95), 35),
    "render_desde_abajo.png": camara("Cam_abajo", (0.01, 0.01, -1250), (0, 0, 0), 35),
    "render_lateral.png": camara("Cam_lateral", (0, -3000, 125), (0, 0, 125), ortho=1000),
    "render_pieza.png": camara("Cam_pieza", (X0, (c_pieza.y + e_mid.y + 70) / 2, 2000),
                               (X0, (c_pieza.y + e_mid.y + 70) / 2, 0), ortho=720),
}
for ob in cams.values():
    if ob.name == "Cam_abajo":
        ob.rotation_euler = (math.radians(180), 0, 0)

sc.camera = cams["render_3_4.png"]

if HACER_RENDERS:
    for fn, cam in cams.items():
        sc.camera = cam
        solo_pieza = fn == "render_pieza.png"
        C_LAMP.hide_render = solo_pieza
        C_PIEZA.hide_render = not solo_pieza
        sc.render.resolution_x, sc.render.resolution_y = (1600, 1100) if solo_pieza else (1400, 1050)
        bg.inputs["Color"].default_value = (0.86, 0.86, 0.88, 1.0) if solo_pieza else (0.035, 0.035, 0.04, 1.0)
        bg.inputs["Strength"].default_value = 1.0
        sc.render.filepath = os.path.join(OUT, fn)
        bpy.ops.render.render(write_still=True)
    C_LAMP.hide_render = False
    C_PIEZA.hide_render = False
    sc.camera = cams["render_3_4.png"]
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1050

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lampara_roseta.blend"), compress=True)
print("LISTO:", OUT)
print(json.dumps(DATOS["curva"], indent=1))
