"""Hamburguesa 3D a partir de las fotos de producto.

Cada ingrediente es un objeto independiente dentro de la colección "Hamburguesa".
Uso:
    blender -b --python hamburguesa.py
Variables de entorno:
    HB_CALIDAD = prueba | final      (resolución y muestras del render)
    HB_VISTAS  = armada,despiece     (qué renders hacer; vacío = ninguno)
    HB_OUT     = carpeta de salida
"""
import json
import math
import os
import random

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector, noise
from mathutils.bvhtree import BVHTree

BASE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(BASE, 'tex')
HDRI = os.path.join(BASE, 'hdri', 'brown_photostudio_02.hdr')
OUT = os.environ.get('HB_OUT', os.path.join(BASE, 'out'))
CALIDAD = os.environ.get('HB_CALIDAD', 'prueba')
VISTAS = [v for v in os.environ.get('HB_VISTAS', 'armada').split(',') if v]
os.makedirs(OUT, exist_ok=True)
COL = json.load(open(os.path.join(TEX, 'colores.json')))
TAU = 2 * math.pi
rnd = random.Random(1973)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def coleccion(nombre):
    c = bpy.data.collections.new(nombre)
    scene.collection.children.link(c)
    return c


C_HAMB = coleccion('Hamburguesa')
C_ESC = coleccion('Escenario')


# ---------------------------------------------------------------- utilidades
def n3(x, y, z, seed=0.0):
    return noise.noise(Vector((x + seed * 3.17, y - seed * 1.91, z + seed * 7.31)))


def f3(x, y, z, octavas=4, seed=0.0):
    return noise.fractal(Vector((x + seed * 3.17, y - seed * 1.91, z + seed * 7.31)), 1.0, 2.0, octavas) / 1.6


def malla(nombre, verts, caras, uvs=None, mat_idx=None, materiales=(), col=C_HAMB, suave=True):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in caras])
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.asarray(uvs, np.float32).ravel())
    for m in materiales:
        me.materials.append(m)
    if mat_idx is not None:
        me.polygons.foreach_set('material_index', np.asarray(mat_idx, np.int32))
    if suave:
        me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    return ob


def suavizar(ob):
    me = ob.data
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    me.update()


def arbol(objs):
    """BVH con la geometría final (con modificadores) de varios objetos, para proyectar rayos."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    V, F, off = [], [], 0
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        mw = o.matrix_world
        V += [tuple(mw @ v.co) for v in me.vertices]
        F += [tuple(i + off for i in p.vertices) for p in me.polygons]
        off += len(me.vertices)
        oe.to_mesh_clear()
    return BVHTree.FromPolygons(V, F)


def z_abajo(tree, x, y, desde=0.5):
    hit = tree.ray_cast(Vector((x, y, desde)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else None


def remuestrear(pts, paso):
    out = [pts[0]]
    for (r0, z0), (r1, z1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(r1 - r0, z1 - z0)
        n = max(1, math.ceil(L / paso))
        for i in range(1, n + 1):
            t = i / n
            out.append((r0 + (r1 - r0) * t, z0 + (z1 - z0) * t))
    return out


def arco(cr, cz, rad, a0, a1, n=10):
    return [(cr + rad * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + rad * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def revolucion(nombre, piezas, nseg, desplazar, materiales, reps_u=4, rcap=0.05, paso=0.0012):
    """Superficie de revolución. piezas = [(puntos (r,z), 'cap'|'lado', indice_material)],
    desde el polo inferior hasta el polo superior. Las tapas llevan UV plana y los lados UV cilíndrica."""
    prof, preg = [], []
    for k, (pts, _tipo, _m) in enumerate(piezas):
        d = remuestrear(pts, paso)
        if prof:
            d = d[1:]
        prof += d
        preg += [k] * len(d)
    P = np.array(prof)
    n = len(P)
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0] = P[1] - P[0]
    T[-1] = P[-1] - P[-2]
    N = np.stack([T[:, 1], -T[:, 0]], 1)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    s = np.zeros(n)
    s[1:] = np.cumsum(np.linalg.norm(P[1:] - P[:-1], axis=1))
    # rango de longitud de arco de cada pieza
    rango = {}
    for k in range(len(piezas)):
        idx = [i for i in range(n) if preg[i] == k]
        i0 = max(0, idx[0] - 1)
        rango[k] = (s[i0], s[idx[-1]])

    verts, anillos = [], []
    for i in range(n):
        r, z = P[i]
        if r < 1e-7:
            nz = 1.0 if N[i][1] > 0 else -1.0
            verts.append(desplazar(0.0, 0.0, z, 0.0, 0.0, nz, 0.0, preg[i]))
            anillos.append([len(verts) - 1])
        else:
            idx = []
            for j in range(nseg):
                th = TAU * j / nseg
                c, sn = math.cos(th), math.sin(th)
                verts.append(desplazar(r * c, r * sn, z, N[i][0] * c, N[i][0] * sn, N[i][1], th, preg[i]))
                idx.append(len(verts) - 1)
            anillos.append(idx)

    caras, uvs, mats = [], [], []

    def uv_de(i, j, k):
        tipo = piezas[k][1]
        r = P[i][0]
        th = TAU * j / nseg
        if tipo == 'cap':
            return (0.5 + r * math.cos(th) / (2 * rcap), 0.5 + r * math.sin(th) / (2 * rcap))
        s0, s1 = rango[k]
        return (reps_u * j / nseg, min(1.0, max(0.0, (s[i] - s0) / max(1e-9, s1 - s0))))

    for i in range(n - 1):
        k = preg[i + 1]
        a, b = anillos[i], anillos[i + 1]
        for j in range(nseg):
            j1 = j + 1
            if len(a) == 1:
                caras.append((a[0], b[j1 % nseg], b[j]))
                esq = [(i, j + 0.5), (i + 1, j1), (i + 1, j)]
            elif len(b) == 1:
                caras.append((a[j], a[j1 % nseg], b[0]))
                esq = [(i, j), (i, j1), (i + 1, j + 0.5)]
            else:
                caras.append((a[j], a[j1 % nseg], b[j1 % nseg], b[j]))
                esq = [(i, j), (i, j1), (i + 1, j1), (i + 1, j)]
            uvs += [uv_de(ii, jj, k) for ii, jj in esq]
            mats.append(piezas[k][2])
    return malla(nombre, verts, caras, uvs, mats, materiales)


S_MB = 100.0  # las metabolas se calculan en centímetros (Blender limita su resolución mínima)


def metabolas(nombre, elementos, res=0.05, umbral=0.6, col=C_HAMB):
    mb = bpy.data.metaballs.new('MB_' + nombre)
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = umbral
    ob = bpy.data.objects.new('MB_' + nombre, mb)
    scene.collection.objects.link(ob)
    for e in elementos:
        el = mb.elements.new(type=e.get('tipo', 'BALL'))
        el.co = [c * S_MB for c in e['co']]
        el.radius = e['r'] * S_MB / 0.574
        el.stiffness = e.get('rigidez', 2.0)
        if el.type == 'ELLIPSOID':
            el.size_x, el.size_y, el.size_z = e['tam']
        if 'rot' in e:
            el.rotation = e['rot']
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(Matrix.Scale(1 / S_MB, 4))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    me.name = nombre
    o = bpy.data.objects.new(nombre, me)
    col.objects.link(o)
    suavizar(o)
    return o


def ruido_malla(ob, amp, escala, seed, octavas=3):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    nr = np.empty(n * 3, np.float32)
    me.vertex_normals.foreach_get('vector', nr)
    co, nr = co.reshape(-1, 3), nr.reshape(-1, 3)
    d = np.array([f3(x * escala, y * escala, z * escala, octavas, seed) for x, y, z in co], np.float32)
    co += nr * (amp * d)[:, None]
    me.vertices.foreach_set('co', co.ravel())
    me.update()


def rot_z(th):
    return Quaternion((0, 0, 1), th)


# ---------------------------------------------------------------- materiales
def link(nt, a, b):
    nt.links.new(a, b)


def principled(nombre, color=(0.8, 0.8, 0.8), rough=0.5):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    return m, nt, b


def sss(b, peso, radio, escala):
    b.inputs['Subsurface Weight'].default_value = peso
    b.inputs['Subsurface Radius'].default_value = radio
    b.inputs['Subsurface Scale'].default_value = escala


def nodo(nt, tipo, **props):
    n = nt.nodes.new(tipo)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def imagen(nt, archivo, colorspace='sRGB', ext='REPEAT', proy='FLAT', blend=0.0):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(os.path.join(TEX, archivo), check_existing=True)
    n.image.colorspace_settings.name = colorspace
    n.extension = ext
    n.projection = proy
    n.projection_blend = blend
    n.interpolation = 'Cubic'
    return n


def coords(nt, tipo='UV', escala=(1, 1, 1), loc=(0, 0, 0)):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = escala
    mp.inputs['Location'].default_value = loc
    link(nt, tc.outputs[tipo], mp.inputs['Vector'])
    return mp.outputs['Vector']


def mezcla(nt, a, b, fac=1.0, modo='MIX'):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = modo
    fin = [i for i in n.inputs if i.name == 'Factor' and i.type == 'VALUE'][0]
    ca, cb = [i for i in n.inputs if i.type == 'RGBA']
    for sock, val in ((ca, a), (cb, b)):
        if isinstance(val, (tuple, list)):
            sock.default_value = (*val, 1) if len(val) == 3 else val
        else:
            link(nt, val, sock)
    if isinstance(fac, (int, float)):
        fin.default_value = fac
    else:
        link(nt, fac, fin)
    return [o for o in n.outputs if o.type == 'RGBA'][0]


def rampa(nt, entrada, paradas):
    r = nt.nodes.new('ShaderNodeValToRGB')
    els = r.color_ramp.elements
    els[0].position, els[0].color = paradas[0][0], (*paradas[0][1], 1)
    els[1].position, els[1].color = paradas[-1][0], (*paradas[-1][1], 1)
    for pos, c in paradas[1:-1]:
        e = els.new(pos)
        e.color = (*c, 1)
    link(nt, entrada, r.inputs['Fac'])
    return r.outputs['Color']


def ruido(nt, vec, escala, detalle=4.0, rough=0.5, distorsion=0.0):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = escala
    n.inputs['Detail'].default_value = detalle
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = distorsion
    if vec is not None:
        link(nt, vec, n.inputs['Vector'])
    return n


def relieve(nt, altura, fuerza, dist, normal=None):
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = fuerza
    bp.inputs['Distance'].default_value = dist
    link(nt, altura, bp.inputs['Height'])
    if normal is not None:
        link(nt, normal, bp.inputs['Normal'])
    return bp.outputs['Normal']


def gris(nt, color):
    n = nt.nodes.new('ShaderNodeRGBToBW')
    link(nt, color, n.inputs[0])
    return n.outputs[0]


def mat_textura(nombre, archivo, rough=0.5, fuerza=0.3, dist=0.0008, ext='REPEAT', proy='FLAT',
                blend=0.0, tipo='UV', escala=(1, 1, 1), loc=(0, 0, 0), brillo=1.0):
    m, nt, b = principled(nombre, rough=rough)
    tex = imagen(nt, archivo, ext=ext, proy=proy, blend=blend)
    link(nt, coords(nt, tipo, escala, loc), tex.inputs['Vector'])
    col = tex.outputs['Color']
    if brillo != 1.0:
        col = mezcla(nt, col, (brillo, brillo, brillo), 1.0, 'MULTIPLY')
    link(nt, col, b.inputs['Base Color'])
    link(nt, relieve(nt, gris(nt, tex.outputs['Color']), fuerza, dist), b.inputs['Normal'])
    return m, nt, b, tex


# ================================================================ INGREDIENTES
# --- 1. Pan de abajo -------------------------------------------------------
R_PAN, H_PAN = 0.054, 0.026


def esc_pan_abajo(th, z=0.0):
    c, s = math.cos(th), math.sin(th)
    return 1 + 0.010 * n3(c * 1.3, s * 1.3, 0.0, 1) + 0.004 * n3(c * 4, s * 4, z * 30, 2)


def pan_abajo():
    R, h = R_PAN, H_PAN
    m_base, nt, b = principled('Pan_Abajo_Base', (0.42, 0.16, 0.04), 0.65)
    link(nt, relieve(nt, ruido(nt, None, 900).outputs['Fac'], 0.2, 0.0004), b.inputs['Normal'])
    m_lado, nt, b, tex = mat_textura('Pan_Abajo_Costado', 'pan_abajo_costado.jpg', rough=0.5,
                                     fuerza=0.35, dist=0.0006, ext='MIRROR')
    sss(b, 0.15, (1.0, 0.45, 0.2), 0.002)
    m_cara, nt, b, tex = mat_textura('Pan_Abajo_Miga_Tostada', 'pan_abajo_cara.jpg', rough=0.75,
                                     fuerza=0.7, dist=0.0012, ext='EXTEND')
    sss(b, 0.25, (1.0, 0.55, 0.25), 0.002)
    piezas = [
        ([(0, 0.0012), (R - 0.008, 0.0)], 'cap', 0),
        (arco(R - 0.008, 0.008, 0.008, -90, 0, 10)
         + [(R - 0.0012, 0.0105), (R + 0.0004, 0.0135), (R + 0.0004, 0.019)]
         + arco(R - 0.0028, h - 0.0032, 0.0032, 0, 90, 8), 'lado', 1),
        ([(R - 0.0028, h), (0, h)], 'cap', 2),
    ]

    def desp(x, y, z, nx, ny, nz, th, k):
        e = esc_pan_abajo(th, z)
        x, y = x * e, y * e
        d = 0.0
        if k == 2:
            d = 0.0006 * f3(x * 120, y * 120, 0.3, 3, 3) + 0.0008 * (1 - (x * x + y * y) / (R * R))
        elif k == 1:
            d = 0.0003 * f3(x * 150, y * 150, z * 150, 3, 4)
        return (x + nx * d, y + ny * d, z + nz * d)

    return revolucion('Pan_Abajo', piezas, 256, desp, [m_base, m_lado, m_cara], reps_u=6, rcap=R)


# --- 2. Salsa cremosa de la base ---------------------------------------------
def salsa_cremosa():
    R, h = R_PAN, H_PAN
    el = []
    # capa sobre la cara del pan
    for _ in range(46):
        rr = (R - 0.007) * math.sqrt(rnd.random())
        a = rnd.random() * TAU
        el.append(dict(tipo='ELLIPSOID', co=(rr * math.cos(a), rr * math.sin(a), h + 0.0010),
                       r=rnd.uniform(0.010, 0.015), tam=(1, 1, 0.26)))
    # rollo de salsa que se sale por el borde (aplastada por la carne), con caída ondulada
    for k in range(110):
        a = TAU * k / 110
        ca, sa = math.cos(a), math.sin(a)
        grosor = 0.0050 + 0.0016 * n3(ca * 2.0, sa * 2.0, 0.0, 71)
        caida = max(0.0, 0.0035 * n3(ca * 3.1, sa * 3.1, 0.4, 73) + 0.0012)
        rr = (R - 0.0010) * esc_pan_abajo(a)
        el.append(dict(tipo='ELLIPSOID', co=(rr * ca, rr * sa, h + 0.0008), r=grosor,
                       tam=(0.5, 1.0, 0.7), rot=rot_z(a)))
        if caida > 0.0015:
            rr2 = (R + 0.0005) * esc_pan_abajo(a, h - caida) + 0.0006
            el.append(dict(tipo='ELLIPSOID', co=(rr2 * ca, rr2 * sa, h - caida), r=grosor * 0.8,
                           tam=(0.42, 1.2, 0.9), rot=rot_z(a)))
    # algunos lóbulos más largos que chorrean y terminan en gota
    lobulos = [(-1.50, 0.011, 0.0058), (-1.95, 0.007, 0.0050), (-0.95, 0.005, 0.0046),
               (-2.55, 0.009, 0.0050), (0.6, 0.008, 0.0050), (2.2, 0.010, 0.0052)]
    for a0, largo, ancho in lobulos:
        a0 += rnd.uniform(-0.06, 0.06)
        largo *= rnd.uniform(0.85, 1.15)
        deriva = rnd.uniform(-0.03, 0.03)
        pasos = max(3, int(largo / 0.0011))
        for p in range(pasos + 1):
            t = p / pasos
            a = a0 + deriva * t
            z = h - 0.0015 - largo * t
            rr = (R + 0.0004) * esc_pan_abajo(a, z) + 0.0008
            ancho_t = ancho * (1.3 - 0.6 * t) if p < pasos else ancho * 0.9
            el.append(dict(tipo='ELLIPSOID', co=(rr * math.cos(a), rr * math.sin(a), z), r=ancho_t,
                           tam=(0.38, 1.25, 0.9), rot=rot_z(a)))
    ob = metabolas('Salsa_Cremosa', el, res=0.04)
    ruido_malla(ob, 0.00025, 220, 72, 2)
    m, nt, b = principled('Salsa_Cremosa', tuple(COL['salsa_cremosa']), 0.18)
    sss(b, 0.6, (1.0, 0.7, 0.4), 0.003)
    b.inputs['Coat Weight'].default_value = 0.3
    b.inputs['Coat Roughness'].default_value = 0.08
    # puntitos oscuros (pimienta/especias) que se ven en la foto
    vec = coords(nt, 'Object')
    vor = nodo(nt, 'ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 900
    vor.inputs['Randomness'].default_value = 1.0
    link(nt, vec, vor.inputs['Vector'])
    motas = rampa(nt, vor.outputs['Distance'], [(0.0, (0, 0, 0)), (0.10, (0, 0, 0)), (0.16, (1, 1, 1)), (1.0, (1, 1, 1))])
    var = ruido(nt, vec, 260, 3)
    pres = nodo(nt, 'ShaderNodeTexWhiteNoise')
    link(nt, vor.outputs['Position'], pres.inputs['Vector'])
    oscuro = mezcla(nt, (0.06, 0.03, 0.015), tuple(COL['salsa_cremosa']), motas, 'MIX')
    sel = rampa(nt, pres.outputs['Value'], [(0.0, (0, 0, 0)), (0.55, (0, 0, 0)), (0.56, (1, 1, 1)), (1.0, (1, 1, 1))])
    base = mezcla(nt, tuple(COL['salsa_cremosa']), (0.75, 0.45, 0.22), var.outputs['Fac'], 'MIX')
    color = mezcla(nt, base, oscuro, sel, 'MIX')
    link(nt, color, b.inputs['Base Color'])
    link(nt, relieve(nt, var.outputs['Fac'], 0.08, 0.0005), b.inputs['Normal'])
    ob.data.materials.append(m)
    return ob


# --- 3. Carne -------------------------------------------------------------------
R_CARNE, H_CARNE = 0.053, 0.023


def carne(z0):
    R, H = R_CARNE, H_CARNE
    m_lado, nt, b, tex = mat_textura('Carne_Costado', 'carne_costado.jpg', rough=0.40, fuerza=1.0,
                                     dist=0.0012, ext='MIRROR')
    sss(b, 0.08, (1.0, 0.25, 0.15), 0.002)
    b.inputs['Coat Weight'].default_value = 0.2
    b.inputs['Coat Roughness'].default_value = 0.25
    m_tapa, nt, b, tex = mat_textura('Carne_Costra', 'carne_arriba.jpg', rough=0.45, fuerza=0.8,
                                     dist=0.0012, ext='MIRROR', escala=(1.6, 2.2, 1))
    b.inputs['Coat Weight'].default_value = 0.2
    b.inputs['Coat Roughness'].default_value = 0.25
    piezas = [
        ([(0, 0.0008), (R - 0.007, 0.0)], 'cap', 0),
        (arco(R - 0.007, 0.007, 0.007, -90, 0, 10) + [(R + 0.001, 0.0105)]
         + arco(R - 0.007, H - 0.007, 0.007, 0, 90, 10), 'lado', 1),
        ([(R - 0.007, H), (0, H + 0.0012)], 'cap', 0),
    ]

    def desp(x, y, z, nx, ny, nz, th, k):
        c, s = math.cos(th), math.sin(th)
        e = 1 + 0.022 * n3(c * 1.1, s * 1.1, 0.5, 11) + 0.010 * n3(c * 3, s * 3, z * 40, 12)
        x, y = x * e, y * e
        d = 0.0016 * f3(x * 90, y * 90, z * 90, 4, 13) + 0.0006 * n3(x * 260, y * 260, z * 260, 14)
        if k == 2:
            d += 0.0012 * n3(x * 30, y * 30, 0, 15)
        return (x + nx * d, y + ny * d, z0 + z + nz * d)

    return revolucion('Carne', piezas, 256, desp, [m_tapa, m_lado], reps_u=6, rcap=R)


# --- 4. Queso parmesano crocante ----------------------------------------------
def queso_crocante(carne_ob):
    M = np.load(os.path.join(TEX, 'queso_crocante_mascara.npy'))
    D, n = 0.128, 330
    hh, ww = M.shape
    celda = np.zeros((n, n), bool)
    for i in range(n):
        for j in range(n):
            celda[i, j] = M[int((i + 0.5) / n * hh), int((j + 0.5) / n * ww)] > 0.5
    usados = np.zeros((n + 1, n + 1), bool)
    caras_ij = []
    for i in range(n):
        for j in range(n):
            if celda[i, j]:
                caras_ij.append((i, j))
                usados[i, j] = usados[i + 1, j] = usados[i + 1, j + 1] = usados[i, j + 1] = True
    tree = arbol([carne_ob])
    z_centro = z_abajo(tree, 0.0, 0.0)
    indice = -np.ones((n + 1, n + 1), int)
    verts, uv_v = [], []
    for i in range(n + 1):
        for j in range(n + 1):
            if not usados[i, j]:
                continue
            x, y = -D / 2 + j / n * D, D / 2 - i / n * D
            r = math.hypot(x, y)
            z = z_centro + 0.0012 + 0.0022 * n3(x * 45, y * 45, 0.0, 21) + 0.0005 * n3(x * 160, y * 160, 0, 22)
            exc = max(0.0, r - 0.044)
            z -= exc * 0.35 + 10 * exc * exc
            zc = z_abajo(tree, x, y)
            if zc is not None:
                z = max(z, zc + 0.0009)
            indice[i, j] = len(verts)
            verts.append((x, y, z))
            uv_v.append((j / n, 1 - i / n))
    caras = [(indice[i, j], indice[i + 1, j], indice[i + 1, j + 1], indice[i, j + 1]) for i, j in caras_ij]
    # suavizar el contorno para que el encaje no quede escalonado
    cuenta = {}
    for f in caras:
        for k in range(4):
            e = (min(f[k], f[(k + 1) % 4]), max(f[k], f[(k + 1) % 4]))
            cuenta[e] = cuenta.get(e, 0) + 1
    vecinos = {}
    for (va, vb), cnt in cuenta.items():
        if cnt == 1:
            vecinos.setdefault(va, []).append(vb)
            vecinos.setdefault(vb, []).append(va)
    V = np.array(verts)
    for _ in range(5):
        nuevo = V.copy()
        for v, ns in vecinos.items():
            nuevo[v, :2] = 0.5 * V[v, :2] + 0.5 * V[ns, :2].mean(0)
        V = nuevo
    verts = [tuple(v) for v in V]
    uvs = []
    for f in caras:
        uvs += [uv_v[v] for v in f]
    m, nt, b = principled('Queso_Crocante', tuple(COL['queso_crocante']), 0.42)
    tex = imagen(nt, 'queso_crocante.png', ext='CLIP')
    tex.image.alpha_mode = 'STRAIGHT'
    link(nt, coords(nt, 'UV'), tex.inputs['Vector'])
    hsv = nodo(nt, 'ShaderNodeHueSaturation')
    hsv.inputs['Saturation'].default_value = 1.15
    hsv.inputs['Value'].default_value = 0.92
    link(nt, tex.outputs['Color'], hsv.inputs['Color'])
    link(nt, hsv.outputs['Color'], b.inputs['Base Color'])
    link(nt, relieve(nt, gris(nt, tex.outputs['Color']), 0.9, 0.0007), b.inputs['Normal'])
    sss(b, 0.3, (1.0, 0.6, 0.15), 0.0015)
    ob = malla('Queso_Parmesano_Crocante', verts, caras, uvs, None, [m])
    so = ob.modifiers.new('Grosor', 'SOLIDIFY')
    so.thickness = 0.0013
    so.offset = 0.0
    return ob


# --- 5. Queso crema ---------------------------------------------------------------
def queso_crema(z_c):
    el = []
    k_total = 10
    for k in range(k_total):
        a = TAU * k / k_total + rnd.uniform(-0.15, 0.15)
        rr = rnd.uniform(0.036, 0.048)
        rv = rnd.uniform(0.0085, 0.0120)
        cx, cy = rr * math.cos(a), rr * math.sin(a)
        zc = z_c + 0.5 * rv
        el.append(dict(tipo='ELLIPSOID', co=(cx, cy, zc), r=rv, tam=(rnd.uniform(1.1, 1.35), 1.0, rnd.uniform(0.65, 0.8)),
                       rot=rot_z(a + math.pi / 2 + rnd.uniform(-0.4, 0.4)), rigidez=2.0))
        for _ in range(rnd.randint(2, 3)):
            sv = rnd.uniform(0.003, 0.0055)
            el.append(dict(tipo='ELLIPSOID', co=(cx + rnd.uniform(-0.006, 0.006), cy + rnd.uniform(-0.006, 0.006),
                                                 zc + rnd.uniform(0.001, 0.005)), r=sv, tam=(1.3, 1.0, 0.85),
                           rot=rot_z(rnd.random() * TAU), rigidez=2.0))
    for _ in range(6):
        rr = 0.02 * math.sqrt(rnd.random())
        a = rnd.random() * TAU
        el.append(dict(tipo='ELLIPSOID', co=(rr * math.cos(a), rr * math.sin(a), z_c + 0.002), r=rnd.uniform(0.011, 0.014),
                       tam=(1, 1, 0.42)))
    ob = metabolas('Queso_Crema', el, res=0.04)
    ruido_malla(ob, 0.0022, 90, 81, 4)
    ruido_malla(ob, 0.0006, 400, 82, 2)
    m, nt, b = principled('Queso_Crema', (0.84, 0.79, 0.67), 0.5)
    sss(b, 0.5, (1.0, 0.85, 0.6), 0.0025)
    b.inputs['Coat Weight'].default_value = 0.1
    b.inputs['Coat Roughness'].default_value = 0.25
    vec = coords(nt, 'Object')
    r1 = ruido(nt, vec, 160, 6, 0.65)
    r2 = ruido(nt, vec, 900, 3, 0.5)
    alt = mezcla(nt, r1.outputs['Color'], r2.outputs['Color'], 0.35, 'MIX')
    link(nt, relieve(nt, gris(nt, alt), 0.45, 0.0008), b.inputs['Normal'])
    link(nt, mezcla(nt, (0.84, 0.79, 0.67), (0.76, 0.69, 0.54), r1.outputs['Fac'], 'MIX'), b.inputs['Base Color'])
    ob.data.materials.append(m)
    return ob


# --- 6. Tocineta en trocitos ------------------------------------------------------
def tocineta(crema_ob):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    tv = np.array([v.co[:] for v in bm.verts])
    tf = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    tree = arbol([crema_ob])
    verts, caras = [], []
    for k in range(140):
        rr = 0.037 * math.sqrt(rnd.random())
        a = rnd.random() * TAU
        x, y = rr * math.cos(a), rr * math.sin(a)
        z = z_abajo(tree, x, y)
        if z is None:
            continue
        sx, sy, sz = rnd.uniform(0.0026, 0.0045), rnd.uniform(0.0018, 0.0032), rnd.uniform(0.0010, 0.0018)
        q = Quaternion(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized(),
                       rnd.uniform(0, TAU))
        rot = q.to_matrix()
        base = len(verts)
        sem = rnd.random() * 100
        for v in tv:
            irregular = 1 + 0.45 * n3(v[0] * 1.7, v[1] * 1.7, v[2] * 1.7, sem) + 0.2 * n3(v[0] * 4.5, v[1] * 4.5, v[2] * 4.5, sem + 3)
            p = Vector((v[0] * sx * irregular, v[1] * sy * irregular, v[2] * sz * irregular))
            p = rot @ p
            verts.append((x + p.x, y + p.y, z + p.z + sz * 0.3))
        caras += [[base + i for i in f] for f in tf]
    m, nt, b = principled('Tocineta', (0.30, 0.07, 0.03), 0.38)
    vec = coords(nt, 'Object')
    r1 = ruido(nt, vec, 700, 4, 0.55, 0.4)
    ond = nodo(nt, 'ShaderNodeTexWave')
    ond.inputs['Scale'].default_value = 350
    ond.inputs['Distortion'].default_value = 6
    link(nt, vec, ond.inputs['Vector'])
    col = rampa(nt, r1.outputs['Fac'], [(0.3, (0.035, 0.007, 0.003)), (0.5, (0.13, 0.03, 0.012)),
                                         (0.7, (0.25, 0.07, 0.03)), (0.9, (0.40, 0.16, 0.07))])
    r_grasa = ruido(nt, vec, 260, 3, 0.5)
    grasa = rampa(nt, r_grasa.outputs['Fac'], [(0.0, (0, 0, 0)), (0.62, (0, 0, 0)), (0.70, (0.6, 0.6, 0.6)), (1.0, (0.6, 0.6, 0.6))])
    link(nt, mezcla(nt, col, (0.50, 0.30, 0.16), grasa, 'MIX'), b.inputs['Base Color'])
    link(nt, relieve(nt, r1.outputs['Fac'], 0.6, 0.0004), b.inputs['Normal'])
    sss(b, 0.1, (1.0, 0.3, 0.2), 0.001)
    return malla('Tocineta', verts, caras, None, None, [m])


# --- 7. Salsa de frutos rojos --------------------------------------------------
def salsa_frutos_rojos(base_objs):
    tree = arbol(base_objs)
    el = []

    def sobre(x, y, extra):
        z = z_abajo(tree, x, y)
        return None if z is None else z + extra

    # charcos en el centro
    for _ in range(6):
        rr = 0.022 * math.sqrt(rnd.random())
        a = rnd.random() * TAU
        x, y = rr * math.cos(a), rr * math.sin(a)
        z = sobre(x, y, 0.0004)
        if z is not None:
            el.append(dict(tipo='ELLIPSOID', co=(x, y, z), r=rnd.uniform(0.006, 0.011), tam=(1, 0.8, 0.22),
                           rot=rot_z(rnd.random() * TAU)))
    # hilos hacia el borde (varios hacia la cámara) y chorreados
    direcciones = [-1.57, -1.25, -1.9, -0.85, -2.35, 0.3, 1.2, 2.2, 2.9, -1.0]
    for d0 in direcciones:
        a = d0 + rnd.uniform(-0.1, 0.1)
        x, y = rnd.uniform(-0.006, 0.006), rnd.uniform(-0.006, 0.006)
        z_prev = sobre(x, y, 0)
        grosor = rnd.uniform(0.0016, 0.0024)
        for _paso in range(200):
            a += rnd.uniform(-0.25, 0.25) * 0.35
            x += 0.0007 * math.cos(a)
            y += 0.0007 * math.sin(a)
            z = sobre(x, y, 0)
            if z is None or math.hypot(x, y) > 0.05:
                break
            if z_prev is not None and z < z_prev - 0.004:
                break
            el.append(dict(tipo='ELLIPSOID', co=(x, y, z + 0.0006), r=grosor, tam=(1, 1, 0.5)))
            z_prev = z
        # chorreado hacia abajo por el costado del queso
        if z_prev is None:
            continue
        largo = rnd.choice([rnd.uniform(0.003, 0.007), rnd.uniform(0.008, 0.019)])
        fi = math.atan2(y, x)
        pasos = int(largo / 0.0005) + 1
        ini = dict(tipo='ELLIPSOID', co=(x, y, z_prev + 0.0005), r=grosor * 1.5, tam=(1, 1, 0.4))
        el.append(ini)
        for p in range(pasos + 1):
            zz = z_prev - largo * p / pasos
            ori = Vector((0.09 * math.cos(fi), 0.09 * math.sin(fi), zz))
            hit = tree.ray_cast(ori, Vector((-math.cos(fi), -math.sin(fi), 0)))
            if hit[0] is None:
                break
            pnt = hit[0] + hit[1] * 0.0004
            t = p / pasos
            rv = grosor * (0.75 - 0.25 * t) if p < pasos else grosor * 0.95
            el.append(dict(tipo='ELLIPSOID', co=tuple(pnt), r=rv, tam=(0.35, 1.3, 1.0), rot=rot_z(fi)))
    ob = metabolas('Salsa_Frutos_Rojos', el, res=0.035)
    m, nt, b = principled('Salsa_Frutos_Rojos', (0.13, 0.004, 0.03), 0.05)
    b.inputs['Transmission Weight'].default_value = 0.25
    b.inputs['IOR'].default_value = 1.42
    b.inputs['Coat Weight'].default_value = 0.4
    b.inputs['Coat Roughness'].default_value = 0.03
    ob.data.materials.append(m)
    return ob


# --- 8. Lechuga ------------------------------------------------------------------
def lechuga(base_objs, semilla=int(os.environ.get('HB_SEMILLA_LECHUGA', '11'))):
    rnd = random.Random(semilla)  # azar propio: la lechuga no cambia si cambian otros ingredientes
    tree_base = arbol(base_objs)
    hojas = []
    m, nt, b = principled('Lechuga', (0.25, 0.45, 0.06), 0.38)
    b.inputs['Coat Weight'].default_value = 0.35
    b.inputs['Coat Roughness'].default_value = 0.12
    uvv = coords(nt, 'UV')
    sep = nodo(nt, 'ShaderNodeSeparateXYZ')
    link(nt, uvv, sep.inputs[0])
    # nervio central más claro (v cerca de 0.5) y base más amarilla (u pequeño)
    mr = nodo(nt, 'ShaderNodeMath', operation='SUBTRACT')
    link(nt, sep.outputs['Y'], mr.inputs[0])
    mr.inputs[1].default_value = 0.5
    ab = nodo(nt, 'ShaderNodeMath', operation='ABSOLUTE')
    link(nt, mr.outputs[0], ab.inputs[0])
    nerv = rampa(nt, ab.outputs[0], [(0.0, (1, 1, 1)), (0.03, (1, 1, 1)), (0.09, (0, 0, 0)), (1.0, (0, 0, 0))])
    base_amar = rampa(nt, sep.outputs['X'], [(0.0, (1, 1, 1)), (0.35, (0.2, 0.2, 0.2)), (1.0, (0, 0, 0))])
    vec = coords(nt, 'Object')
    # textura real de la hoja (foto IMG_0309), repetida en espejo a lo largo de cada hoja
    foto = imagen(nt, 'lechuga.jpg', ext='MIRROR')
    link(nt, coords(nt, 'UV', (0.85, 2.0, 1.0)), foto.inputs['Vector'])
    hsl = nodo(nt, 'ShaderNodeHueSaturation')
    hsl.inputs['Hue'].default_value = 0.49
    hsl.inputs['Saturation'].default_value = 1.1
    hsl.inputs['Value'].default_value = 1.45
    link(nt, foto.outputs['Color'], hsl.inputs['Color'])
    verde = hsl.outputs['Color']
    base_suave = mezcla(nt, (0, 0, 0), base_amar, 0.6, 'MIX')
    claro = mezcla(nt, verde, (0.50, 0.62, 0.20), base_suave, 'MIX')
    color = mezcla(nt, claro, (0.60, 0.68, 0.32), mezcla(nt, (0, 0, 0), nerv, 0.7, 'MIX'), 'MIX')
    link(nt, color, b.inputs['Base Color'])
    # venas laterales que salen del nervio central hacia el borde
    diag = nodo(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
    link(nt, ab.outputs[0], diag.inputs[0])
    diag.inputs[1].default_value = 0.8
    link(nt, sep.outputs['X'], diag.inputs[2])
    ond = nodo(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    ond.inputs['Scale'].default_value = 11
    ond.inputs['Distortion'].default_value = 3
    link(nt, diag.outputs[0], ond.inputs['Vector'])
    venas = rampa(nt, ond.outputs['Fac'], [(0.0, (0, 0, 0)), (0.08, (1, 1, 1)), (1.0, (1, 1, 1))])
    r2 = ruido(nt, vec, 650, 4, 0.6)
    alt = mezcla(nt, foto.outputs['Color'], r2.outputs['Color'], 0.25, 'MIX')
    link(nt, relieve(nt, gris(nt, alt), 0.3, 0.0005), b.inputs['Normal'])
    tr = nodo(nt, 'ShaderNodeBsdfTranslucent')
    link(nt, color, tr.inputs['Color'])
    mx = nodo(nt, 'ShaderNodeMixShader')
    mx.inputs['Fac'].default_value = 0.5
    salida = nt.nodes['Material Output']
    link(nt, b.outputs[0], mx.inputs[1])
    link(nt, tr.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], salida.inputs['Surface'])

    nu, nv = 110, 70
    # altura de apoyo: lo alto del queso crema (con tocineta y salsa)
    alturas = []
    for _ in range(600):
        rr = 0.045 * math.sqrt(rnd.random())
        a = rnd.random() * TAU
        zz = z_abajo(tree_base, rr * math.cos(a), rr * math.sin(a))
        if zz is not None:
            alturas.append(zz)
    z_apoyo = float(np.percentile(alturas, 80))
    angs = [i * TAU / 8 + rnd.uniform(-0.15, 0.15) for i in range(8)]
    puestas = []
    for hidx, fi in enumerate(angs):
        r0 = rnd.uniform(0.014, 0.022)
        L = rnd.uniform(0.050, 0.059)
        W = rnd.uniform(0.028, 0.034)
        sem = rnd.random() * 50
        ca, sa = math.cos(fi), math.sin(fi)
        tree = arbol(base_objs + puestas)
        X = np.zeros((nu + 1, nv + 1))
        Y = np.zeros_like(X)
        RUF = np.zeros_like(X)
        ZB = np.full_like(X, np.nan)
        UV = np.zeros((nu + 1, nv + 1, 2))
        for iu in range(nu + 1):
            u = iu / nu
            mitad = W * (math.sin(math.pi * min(1.0, u * 1.05)) ** 0.7) * (0.55 + 0.45 * u) + 0.002
            for iv in range(nv + 1):
                v = -1 + 2 * iv / nv
                al = r0 + u * L
                ac = v * mitad
                x = al * ca - ac * sa
                y = al * sa + ac * ca
                amp = 0.0085 * (abs(v) ** 1.4 * u ** 0.6 + 0.7 * u ** 3)
                ruf = 0.002 * (1 - v * v) * (1 - u)
                ruf += amp * n3(x * 95, y * 95, sem, 31) + 0.0008 * n3(x * 380, y * 380, sem, 32)
                ruf += 0.00045 * n3(x * 900, y * 900, sem, 33) * (0.4 + u)
                X[iu, iv], Y[iu, iv], RUF[iu, iv] = x, y, ruf
                UV[iu, iv] = (u, (v + 1) / 2)
                zb = z_abajo(tree, x, y)
                if zb is not None:
                    ZB[iu, iv] = zb
        # la hoja descansa casi plana sobre lo alto del queso y cae suave fuera del borde
        R_ = np.hypot(X, Y)
        exc = np.maximum(0.0, R_ - 0.049)
        Zs = z_apoyo + 0.0006 * hidx - 0.15 * exc - 6 * exc * exc
        Z = Zs + 0.0008 + RUF - RUF.min() * 0.25
        valido = ~np.isnan(ZB)
        Z = np.where(valido, np.maximum(Z, ZB + 0.0007), Z)
        verts, uvs, caras = [], [], []
        for iu in range(nu + 1):
            for iv in range(nv + 1):
                verts.append((X[iu, iv], Y[iu, iv], Z[iu, iv]))
        for iu in range(nu):
            for iv in range(nv):
                a = iu * (nv + 1) + iv
                f = (a, a + nv + 1, a + nv + 2, a + 1)
                caras.append(f)
                uvs += [tuple(UV[q // (nv + 1), q % (nv + 1)]) for q in f]
        ob = malla(f'Lechuga_Hoja_{hidx + 1}', verts, caras, uvs, None, [m])
        so = ob.modifiers.new('Grosor', 'SOLIDIFY')
        so.thickness = 0.0007
        puestas.append(ob)
    # unir las hojas en un solo objeto "Lechuga"
    for o in puestas:
        o.modifiers.remove(o.modifiers['Grosor'])
    with bpy.context.temp_override(active_object=puestas[0], selected_editable_objects=puestas,
                                   selected_objects=puestas):
        bpy.ops.object.join()
    ob = puestas[0]
    ob.name = 'Lechuga'
    ob.data.name = 'Lechuga'
    so = ob.modifiers.new('Grosor', 'SOLIDIFY')
    so.thickness = 0.0007
    return ob


# --- 9. Pan de arriba -----------------------------------------------------------
R_TAPA, H_TAPA = 0.0555, 0.050


def pan_arriba(zb):
    R, H = R_TAPA, H_TAPA
    m_cara, nt, b, tex = mat_textura('Pan_Arriba_Cara_Tostada', 'pan_arriba_cara.jpg', rough=0.7,
                                     fuerza=0.6, dist=0.001, ext='EXTEND')
    m_cort, nt, b = principled('Pan_Arriba_Corteza', tuple(COL['pan_arriba']), 0.36)
    tex = imagen(nt, 'pan_arriba_corteza.jpg', ext='MIRROR', proy='BOX', blend=0.35)
    link(nt, coords(nt, 'Object', (1 / 0.09, 1 / 0.09, 1 / 0.0365), (0.3, 0.1, 0)), tex.inputs['Vector'])
    oc = nodo(nt, 'ShaderNodeTexCoord')
    sp = nodo(nt, 'ShaderNodeSeparateXYZ')
    link(nt, oc.outputs['Object'], sp.inputs[0])
    gz = nodo(nt, 'ShaderNodeMapRange')
    gz.inputs['From Min'].default_value = zb
    gz.inputs['From Max'].default_value = zb + 0.045
    link(nt, sp.outputs['Z'], gz.inputs['Value'])
    grad = rampa(nt, gz.outputs['Result'], [(0.0, (1.35, 1.25, 1.1)), (0.18, (1.0, 1.0, 1.0)), (1.0, (0.78, 0.74, 0.74))])
    color = mezcla(nt, tex.outputs['Color'], grad, 1.0, 'MULTIPLY')
    hsv = nodo(nt, 'ShaderNodeHueSaturation')
    hsv.inputs['Saturation'].default_value = 1.15
    hsv.inputs['Value'].default_value = 0.82
    link(nt, color, hsv.inputs['Color'])
    color = hsv.outputs['Color']
    link(nt, color, b.inputs['Base Color'])
    link(nt, relieve(nt, gris(nt, tex.outputs['Color']), 0.35, 0.0007), b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.42
    b.inputs['Coat Weight'].default_value = 0.2
    b.inputs['Coat Roughness'].default_value = 0.28
    sss(b, 0.1, (1.0, 0.4, 0.2), 0.0015)
    m_sem, nt, b = principled('Semillas_Amapola', (0.015, 0.016, 0.02), 0.35)

    domo = []
    for i in range(61):
        t = (i / 60) * (math.pi / 2)
        domo.append((R * math.cos(t) ** 0.85, 0.004 + (H - 0.004) * math.sin(t) ** 0.85))
    piezas = [
        ([(0, 0.0), (R - 0.004, 0.0)], 'cap', 0),
        (arco(R - 0.004, 0.004, 0.004, -90, 0, 8) + domo[1:], 'lado', 1),
    ]

    def forma(x, y, z, nx, ny, nz, th, k):
        c, s = math.cos(th), math.sin(th)
        e = 1 + 0.012 * n3(c * 1.2, s * 1.2, 0.9, 41) + 0.004 * n3(c * 3, s * 3, z * 25, 42)
        x, y = x * e, y * e
        d = 0.0
        if k == 1:
            d = 0.0006 * f3(x * 70, y * 70, z * 70, 3, 43) + 0.0002 * n3(x * 300, y * 300, z * 300, 44)
        return (x + nx * d, y + ny * d, zb + z + nz * d)

    ob = revolucion('Pan_Arriba', piezas, 256, forma, [m_cara, m_cort], reps_u=4, rcap=R)
    # semillas de amapola (geometría real) sobre la parte alta del domo
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    tv = [v.co.copy() for v in bm.verts]
    tf = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    verts, caras = [], []
    for _ in range(420):
        t = math.asin(min(1.0, rnd.random() ** 0.55)) if rnd.random() < 0.85 else rnd.uniform(0.3, 1.2)
        t = min(t, math.pi / 2 - 0.02)
        th = rnd.random() * TAU
        r = R * math.cos(t) ** 0.85
        z = 0.004 + (H - 0.004) * math.sin(t) ** 0.85
        dr = -0.85 * R * math.cos(t) ** -0.15 * math.sin(t)
        dz = 0.85 * (H - 0.004) * math.sin(t) ** -0.15 * math.cos(t) if t > 1e-3 else 1.0
        nrm = Vector((dz * math.cos(th), dz * math.sin(th), -dr)).normalized()
        p = Vector(forma(r * math.cos(th), r * math.sin(th), z, nrm.x, nrm.y, nrm.z, th, 1))
        rot = nrm.to_track_quat('Z', 'X').to_matrix() @ Matrix.Rotation(rnd.random() * TAU, 3, 'Z')
        base = len(verts)
        for v in tv:
            q = rot @ Vector((v.x * 0.00055, v.y * 0.0004, v.z * 0.00025))
            verts.append(tuple(p + q + nrm * 0.0001))
        caras += [[base + i for i in f] for f in tf]
    sem = malla('Semillas', verts, caras, None, None, [m_sem])
    with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob, sem], selected_objects=[ob, sem]):
        bpy.ops.object.join()
    return ob


# --- 10. Palillo de madera ------------------------------------------------------
def palillo(z_base, z_tope):
    m, nt, b = principled('Madera_Palillo', (0.62, 0.43, 0.25), 0.55)
    vec = coords(nt, 'Object')
    ond = nodo(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z')
    ond.inputs['Scale'].default_value = 60
    ond.inputs['Distortion'].default_value = 4
    link(nt, vec, ond.inputs['Vector'])
    link(nt, mezcla(nt, (0.66, 0.47, 0.28), (0.52, 0.34, 0.18), ond.outputs['Fac'], 'MIX'), b.inputs['Base Color'])
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0016, radius2=0.0016, depth=z_tope - z_base)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, (z_base + z_tope) / 2))
    disco = bmesh.new()
    bmesh.ops.create_cone(disco, cap_ends=True, segments=48, radius1=0.011, radius2=0.011, depth=0.0025)
    bmesh.ops.rotate(disco, verts=disco.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(disco, verts=disco.verts, vec=(0, 0, z_tope + 0.0095))
    me = bpy.data.meshes.new('Palillo')
    bm.to_mesh(me)
    me2 = bpy.data.meshes.new('tmp')
    disco.to_mesh(me2)
    bm.free()
    disco.free()
    ob = bpy.data.objects.new('Palillo', me)
    C_HAMB.objects.link(ob)
    ob2 = bpy.data.objects.new('tmp', me2)
    C_HAMB.objects.link(ob2)
    with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob, ob2], selected_objects=[ob, ob2]):
        bpy.ops.object.join()
    ob.data.materials.append(m)
    bev = ob.modifiers.new('Bisel', 'BEVEL')
    bev.width = 0.0004
    bev.segments = 2
    return ob


# ================================================================ ARMADO
print('HB: pan de abajo')
o_pan_abajo = pan_abajo()
print('HB: salsa cremosa')
o_salsa = salsa_cremosa()
print('HB: carne')
o_carne = carne(H_PAN + 0.0016)
print('HB: queso crocante')
o_crocante = queso_crocante(o_carne)
t_croc = arbol([o_crocante])
z_c = z_abajo(t_croc, 0.0, 0.0) or (H_PAN + H_CARNE + 0.004)
print('HB: queso crema', z_c)
o_crema = queso_crema(z_c - 0.0005)
print('HB: tocineta')
o_toci = tocineta(o_crema)
print('HB: frutos rojos')
o_frutos = salsa_frutos_rojos([o_crema, o_toci, o_crocante])
print('HB: lechuga')
o_lechuga = lechuga([o_crema, o_toci, o_frutos])
vz = np.array([(o_lechuga.matrix_world @ v.co).z for v in o_lechuga.data.vertices
               if math.hypot(v.co.x, v.co.y) < 0.040])
z_tapa = float(np.percentile(vz, 85))
print('HB: pan de arriba', z_tapa)


def prensar(ob, z_max, radio):
    """Aplasta contra la base del pan de arriba lo que quede por encima (como al tapar la hamburguesa)."""
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    r = np.hypot(co[:, 0], co[:, 1])
    dentro = r < radio
    exceso = np.maximum(0.0, co[:, 2] - z_max)
    co[:, 2] = np.where(dentro, co[:, 2] - exceso * 0.92, co[:, 2])
    me.vertices.foreach_set('co', co.ravel())
    me.update()


prensar(o_lechuga, z_tapa - 0.0006, R_TAPA * 1.02)
prensar(o_crema, z_tapa - 0.0016, R_TAPA * 1.02)
prensar(o_frutos, z_tapa - 0.0014, R_TAPA * 1.02)
prensar(o_toci, z_tapa - 0.0016, R_TAPA * 1.02)
o_pan_arriba = pan_arriba(z_tapa)
o_palillo = palillo(z_c + 0.004, z_tapa + H_TAPA + 0.035)

INGREDIENTES = [o_pan_abajo, o_salsa, o_carne, o_crocante, o_crema, o_toci, o_frutos, o_lechuga,
                o_pan_arriba, o_palillo]

# ================================================================ ESCENARIO
print('HB: escenario')


def piedra():
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=1.0)
    a, bb, c = 0.105, 0.088, 0.048
    for v in bm.verts:
        x, y, z = v.co
        zf = math.copysign(abs(z) ** 0.55, z)
        p = Vector((x * a, y * bb, zf * c))
        d = 0.005 * f3(x * 1.2, y * 1.2, z * 1.2, 3, 51) + 0.0012 * f3(x * 9, y * 9, z * 9, 3, 52)
        v.co = p + v.normal * d
    me = bpy.data.meshes.new('Piedra')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('Piedra', me)
    C_ESC.objects.link(ob)
    suavizar(ob)
    m, nt, b = principled('Piedra', (0.22, 0.22, 0.21), 0.85)
    vec = coords(nt, 'Object')
    vor = nodo(nt, 'ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 650
    link(nt, vec, vor.inputs['Vector'])
    wn = nodo(nt, 'ShaderNodeTexWhiteNoise')
    link(nt, vor.outputs['Position'], wn.inputs['Vector'])
    motas = rampa(nt, wn.outputs['Value'], [(0.0, (0.03, 0.03, 0.03)), (0.3, (0.11, 0.11, 0.105)),
                                            (0.85, (0.16, 0.16, 0.15)), (0.97, (0.36, 0.36, 0.34))])
    r1 = ruido(nt, vec, 18, 5, 0.6)
    col = mezcla(nt, motas, (0.07, 0.07, 0.066), r1.outputs['Fac'], 'MIX')
    link(nt, col, b.inputs['Base Color'])
    poros = rampa(nt, vor.outputs['Distance'], [(0.0, (0, 0, 0)), (0.2, (1, 1, 1)), (1.0, (1, 1, 1))])
    link(nt, relieve(nt, gris(nt, poros), 0.5, 0.0006), b.inputs['Normal'])
    ob.data.materials.append(m)
    tope = z_abajo(arbol([ob]), 0.0, 0.0)
    ob.location.z = -0.0032 - tope
    return ob


def hoja_decorativa(piedra_ob):
    tree = arbol([piedra_ob])
    nu, nv = 140, 34
    L, W = 0.25, 0.056
    fi = math.radians(-22)
    cen = 0.45
    grid = {}
    for iu in range(nu + 1):
        u = iu / nu
        # base redondeada, más ancha al 35 %, punta aguda
        mitad = W * (math.sin(math.pi * min(1.0, u ** 0.85)) ** 0.75) * (1.0 - 0.25 * u) + 0.0005
        for iv in range(nv + 1):
            v = -1 + 2 * iv / nv
            al = (u - cen) * L
            ac = v * mitad
            x = al * math.cos(fi) - ac * math.sin(fi)
            y = al * math.sin(fi) + ac * math.cos(fi) + 0.008
            grid[iu, iv] = [x, y, z_abajo(tree, x, y), u, (v + 1) / 2, v]
    # fuera de la piedra la hoja sigue con una caída suave
    icen = int(cen * nu)
    for iv in range(nv + 1):
        for rango_u, paso in ((range(icen, nu + 1), 1), (range(icen, -1, -1), -1)):
            ultimo, fuera = None, 0.0
            for iu in rango_u:
                g = grid[iu, iv]
                if g[2] is not None and fuera == 0.0:
                    ultimo = g[2]
                else:
                    fuera += L / nu
                    g[2] = (ultimo if ultimo is not None else -0.01) - 0.12 * fuera - 1.5 * fuera * fuera
    verts, uvs_v = [], []
    for iu in range(nu + 1):
        for iv in range(nv + 1):
            x, y, z, uu, vv, v = grid[iu, iv]
            z = z + 0.0012 + 0.004 * abs(v) ** 1.6 + 0.0006 * n3(x * 60, y * 60, 0, 61)
            verts.append((x, y, min(z, -0.0012)))
            uvs_v.append((uu, vv))
    caras, uvs = [], []
    for iu in range(nu):
        for iv in range(nv):
            a = iu * (nv + 1) + iv
            f = (a, a + nv + 1, a + nv + 2, a + 1)
            caras.append(f)
            uvs += [uvs_v[q] for q in f]
    m, nt, b = principled('Hoja_Decorativa', (0.30, 0.38, 0.20), 0.45)
    uvv = coords(nt, 'UV')
    sep = nodo(nt, 'ShaderNodeSeparateXYZ')
    link(nt, uvv, sep.inputs[0])
    mr = nodo(nt, 'ShaderNodeMath', operation='SUBTRACT')
    link(nt, sep.outputs['Y'], mr.inputs[0])
    mr.inputs[1].default_value = 0.5
    ab = nodo(nt, 'ShaderNodeMath', operation='ABSOLUTE')
    link(nt, mr.outputs[0], ab.inputs[0])
    diag = nodo(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
    link(nt, ab.outputs[0], diag.inputs[0])
    diag.inputs[1].default_value = 0.35
    link(nt, sep.outputs['X'], diag.inputs[2])
    comb = nodo(nt, 'ShaderNodeCombineXYZ')
    link(nt, diag.outputs[0], comb.inputs[0])
    link(nt, ab.outputs[0], comb.inputs[1])
    ond = nodo(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    ond.inputs['Scale'].default_value = 26
    ond.inputs['Distortion'].default_value = 7
    ond.inputs['Detail'].default_value = 6
    link(nt, comb.outputs[0], ond.inputs['Vector'])
    rr = ruido(nt, uvv, 30, 6)
    mezc = mezcla(nt, ond.outputs['Color'], rr.outputs['Color'], 0.4, 'MIX')
    rayas = rampa(nt, gris(nt, mezc), [(0.0, (0, 0, 0)), (0.47, (0, 0, 0)), (0.53, (0.85, 0.85, 0.85)), (1.0, (0.85, 0.85, 0.85))])
    borde = rampa(nt, ab.outputs[0], [(0.0, (0, 0, 0)), (0.25, (0.3, 0.3, 0.3)), (0.5, (1, 1, 1))])
    fac = mezcla(nt, rayas, borde, 0.35, 'LIGHTEN')
    color = mezcla(nt, (0.32, 0.40, 0.25), (0.035, 0.12, 0.035), fac, 'MIX')
    link(nt, color, b.inputs['Base Color'])
    ob = malla('Hoja_Decorativa', verts, caras, uvs, None, [m], col=C_ESC)
    so = ob.modifiers.new('Grosor', 'SOLIDIFY')
    so.thickness = 0.0008
    return ob


def mesa():
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=2.5)
    me = bpy.data.meshes.new('Mesa_Fique')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('Mesa_Fique', me)
    C_ESC.objects.link(ob)
    ob.location.z = -0.092
    m, nt, b = principled('Fique', (0.32, 0.20, 0.11), 0.9)
    vec = coords(nt, 'Object')
    w1 = nodo(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    w1.inputs['Scale'].default_value = 330
    w1.inputs['Distortion'].default_value = 0.8
    w2 = nodo(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y')
    w2.inputs['Scale'].default_value = 330
    w2.inputs['Distortion'].default_value = 0.8
    link(nt, vec, w1.inputs['Vector'])
    link(nt, vec, w2.inputs['Vector'])
    tejido = mezcla(nt, w1.outputs['Color'], w2.outputs['Color'], 0.5, 'MULTIPLY')
    r1 = ruido(nt, vec, 40, 4)
    col = mezcla(nt, (0.36, 0.23, 0.13), (0.22, 0.13, 0.07), r1.outputs['Fac'], 'MIX')
    col = mezcla(nt, col, tejido, 0.35, 'MULTIPLY')
    link(nt, col, b.inputs['Base Color'])
    link(nt, relieve(nt, gris(nt, tejido), 0.6, 0.001), b.inputs['Normal'])
    b.inputs['Sheen Weight'].default_value = 0.4
    me.materials.append(m)
    return ob


o_piedra = piedra()
o_hoja = hoja_decorativa(o_piedra)
o_mesa = mesa()

# fondo cálido desenfocado (como las luces de la foto original)
def fondo():
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)
    me = bpy.data.meshes.new('Fondo')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('Fondo', me)
    C_ESC.objects.link(ob)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    ob.location = (0.0, 1.3, 0.25)
    ob.scale = (1.6, 1.0, 1.0)
    m = bpy.data.materials.new('Fondo')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nodo(nt, 'ShaderNodeEmission')
    vec = coords(nt, 'Object')
    r1 = ruido(nt, vec, 2.2, 2, 0.4)
    col = rampa(nt, r1.outputs['Fac'], [(0.32, (0.02, 0.005, 0.001)), (0.48, (0.18, 0.055, 0.012)),
                                         (0.6, (0.70, 0.30, 0.07)), (0.72, (1.0, 0.62, 0.25))])
    link(nt, col, em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.5
    link(nt, em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    me.materials.append(m)
    return ob


o_fondo = fondo()


def bokeh():
    m = bpy.data.materials.new('Luces_Fondo')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nodo(nt, 'ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.48, 0.16, 1)
    em.inputs['Strength'].default_value = 1.6
    link(nt, em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    import bmesh
    for k, (x, y, z, r) in enumerate([(-0.22, 1.0, 0.30, 0.035), (0.19, 1.1, 0.36, 0.045), (0.27, 0.9, 0.13, 0.03),
                                      (-0.29, 1.2, 0.06, 0.04), (0.03, 1.25, 0.43, 0.035), (-0.08, 1.15, 0.20, 0.025)]):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
        me = bpy.data.meshes.new(f'Luz_Fondo_{k}')
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m)
        ob = bpy.data.objects.new(f'Luz_Fondo_{k}', me)
        C_ESC.objects.link(ob)
        ob.location = (x, y, z)
        ob.visible_shadow = False


bokeh()

# ---------------------------------------------------------------- luces
def luz(nombre, loc, objetivo, energia, tam, color=(1, 1, 1), tam_y=None):
    ld = bpy.data.lights.new(nombre, 'AREA')
    ld.energy = energia
    ld.size = tam
    if tam_y:
        ld.shape = 'RECTANGLE'
        ld.size_y = tam_y
    ld.color = color
    ob = bpy.data.objects.new(nombre, ld)
    C_ESC.objects.link(ob)
    ob.location = loc
    d = Vector(objetivo) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


centro = (0, 0, 0.06)
luz('Luz_Principal', (-0.55, -0.55, 0.55), centro, 32, 0.6, (1.0, 0.93, 0.85))
luz('Luz_Relleno', (0.6, -0.5, 0.12), centro, 3.5, 0.8, (1.0, 0.95, 0.9))
luz('Luz_Contra_Calida', (0.35, 0.55, 0.30), centro, 40, 0.35, (1.0, 0.62, 0.32))
luz('Luz_Contra_Izq', (-0.45, 0.5, 0.2), centro, 14, 0.3, (1.0, 0.7, 0.45))

w = bpy.data.worlds.new('Mundo')
scene.world = w
w.use_nodes = True
wn = w.node_tree
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(HDRI)
link(wn, env.outputs['Color'], wn.nodes['Background'].inputs['Color'])
wn.nodes['Background'].inputs['Strength'].default_value = 0.25

# ---------------------------------------------------------------- cámaras
def camara(nombre, objetivo, dist, az, el, lente=100, fstop=5.6, foco_delta=-0.03):
    cd = bpy.data.cameras.new(nombre)
    cd.lens = lente
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.focus_distance = dist + foco_delta
    ob = bpy.data.objects.new(nombre, cd)
    C_ESC.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    t = Vector(objetivo)
    ob.location = t + Vector((dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a), dist * math.sin(e)))
    ob.rotation_euler = (t - ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


cam_armada = camara('Camara_Armada', (0, 0, 0.068), 0.70, -8, 7)
cam_despiece = camara('Camara_Despiece', (0, 0, 0.205), 1.75, -8, 13, fstop=8, foco_delta=-0.02)
cam_detalle = camara('Camara_Detalle', (0, 0, 0.052), 0.36, -4, 5, lente=100, fstop=8, foco_delta=-0.05)

# ---------------------------------------------------------------- animación de armado (despiece -> armada)
ALTURAS = {'Pan_Abajo': 0.0, 'Salsa_Cremosa': 0.03, 'Carne': 0.065, 'Queso_Parmesano_Crocante': 0.10,
           'Queso_Crema': 0.13, 'Tocineta': 0.16, 'Salsa_Frutos_Rojos': 0.185, 'Lechuga': 0.215,
           'Pan_Arriba': 0.255, 'Palillo': 0.30}
F_DESPIECE, F_ARMADA = 1, 72
scene.frame_start, scene.frame_end = F_DESPIECE, F_ARMADA + 24
for o in INGREDIENTES:
    o.location.z = ALTURAS[o.name]
    o.keyframe_insert('location', frame=F_DESPIECE)
    o.location.z = 0.0
    o.keyframe_insert('location', frame=F_ARMADA)
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'EASE_IN_OUT'
        except AttributeError:
            pass

# cámara de la animación: viaja de la toma del despiece a la toma armada
cd_an = bpy.data.cameras.new('Camara_Animacion')
cd_an.lens = 100
cd_an.sensor_width = 36
cd_an.dof.use_dof = True
cam_anim = bpy.data.objects.new('Camara_Animacion', cd_an)
C_ESC.objects.link(cam_anim)
cam_anim.rotation_mode = 'QUATERNION'
for frame, ref in ((F_DESPIECE, cam_despiece), (F_ARMADA, cam_armada)):
    cam_anim.location = ref.location
    cam_anim.rotation_quaternion = ref.rotation_euler.to_quaternion()
    cd_an.dof.focus_distance = ref.data.dof.focus_distance
    cd_an.dof.aperture_fstop = ref.data.dof.aperture_fstop
    cam_anim.keyframe_insert('location', frame=frame)
    cam_anim.keyframe_insert('rotation_quaternion', frame=frame)
    cd_an.dof.keyframe_insert('focus_distance', frame=frame)
    cd_an.dof.keyframe_insert('aperture_fstop', frame=frame)
scene.render.fps = 24

# ---------------------------------------------------------------- render
scene.render.engine = 'CYCLES'
cy = scene.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True
cy.use_denoising = True
try:
    cy.denoiser = 'OPENIMAGEDENOISE'
except Exception as ex:
    print('HB: denoiser', ex)
cy.max_bounces = 12
cy.transmission_bounces = 12
cy.transparent_max_bounces = 16
cy.diffuse_bounces = 4
cy.glossy_bounces = 6
cy.volume_bounces = 0
cy.caustics_reflective = False
cy.caustics_refractive = False
try:
    vt, lk = os.environ.get('HB_VT', 'AgX|AgX - Punchy').split('|')
    scene.view_settings.view_transform = vt
    scene.view_settings.look = lk
except Exception as ex:
    print('HB: color', ex)
scene.view_settings.exposure = 0.0
r = scene.render
r.resolution_x, r.resolution_y = 1080, 1350
if CALIDAD == 'final':
    cy.samples = 384
    cy.adaptive_threshold = 0.018
    r.resolution_percentage = 100
else:
    cy.samples = 40
    cy.adaptive_threshold = 0.05
    r.resolution_percentage = 50
r.image_settings.file_format = 'PNG'

blend = os.path.join(OUT, 'hamburguesa.blend')
scene.frame_set(F_ARMADA)
scene.camera = cam_armada
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
print('HB: guardado', blend)

for vista in VISTAS:
    if vista == 'armada':
        scene.frame_set(F_ARMADA)
        scene.camera = cam_armada
    elif vista == 'despiece':
        scene.frame_set(F_DESPIECE)
        scene.camera = cam_despiece
    elif vista == 'detalle':
        scene.frame_set(F_ARMADA)
        scene.camera = cam_detalle
    r.filepath = os.path.join(OUT, f'render_{vista}_{CALIDAD}{os.environ.get("HB_SUF", "")}.png')
    print('HB: render', vista)
    bpy.ops.render.render(write_still=True)
print('HB: listo')
