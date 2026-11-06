"""
Lámpara colgante de cuerda torcida (forma de platillo / doble cono)
===================================================================

Genera en Blender una lámpara colgante forrada con cuerda de algodón torcida
de 3 cabos, inspirada en las lámparas de fibra natural tipo "platillo".

Medidas por defecto
    - Ancho (diámetro en el centro) .......... 80 cm
    - Alto total (de aro a aro) .............. 50 cm
    - Centro (parte más ancha) ............... a 25 cm (justo en la mitad)
    - Doble aro en el centro ................. 2 aros forrados, separados 2 cm
    - Bocas superior e inferior .............. Ø 25 cm

Cómo usarlo
    1. Blender 4.2 o superior -> pestaña "Scripting" -> "Open" -> este archivo
       -> "Run Script" (o Alt+P).
    2. Desde la terminal (sin abrir Blender):
           blender -b -P lampara_cuerda.py -- --guardar lampara.blend
           blender -b -P lampara_cuerda.py -- --render render.png --muestras 128
       Opciones: --vista producto|frente  --res 1080  --muestras 128

Todas las medidas se cambian en la sección PARÁMETROS. Ejecutar el script de
nuevo borra la lámpara anterior y la vuelve a crear.
"""

import argparse
import math
import random
import sys

import bpy
from mathutils import Vector


# =============================================================================
# PARÁMETROS
# =============================================================================

# --- Forma (centímetros) -----------------------------------------------------
ANCHO_CM = 80.0            # Diámetro exterior en el centro (parte más ancha).
ALTO_CM = 50.0             # Alto total, del borde del aro de arriba al de abajo.
ALTURA_ECUADOR_CM = 25.0   # Altura del centro (mitad entre los dos aros del centro),
                           # medida desde abajo.
SEPARACION_AROS_CENTRO_CM = 2.0  # Distancia entre los dos aros del centro (de eje a
                                 # eje del alambre). Con 2 cm los dos aros forrados
                                 # quedan casi pegados, con una línea fina entre ellos.
DIAM_BOCA_SUP_CM = 25.0    # Diámetro del aro metálico superior.
DIAM_BOCA_INF_CM = 25.0    # Diámetro del aro metálico inferior.
ABOMBADO_CM = 0.8          # Curvatura hacia afuera de cada cono (0 = cono recto).
ALTO_ARO_CM = 1.5          # Alto de las bandas metálicas de arriba y abajo.

# --- Cuerda --------------------------------------------------------------------
DIAM_CUERDA_MM = 6.0       # Grosor de la cuerda.
PASO_TORSION_MM = 20.0     # Largo de una vuelta completa de los 3 cabos.
NUM_HEBRAS = 288           # Hebras por cono, arriba y abajo (se redondea a múltiplo de 6).
COLOR_CUERDA = "#7E5E3C"   # Café/caramelo tomado de la foto del rollo.
VARIACION_HEBRAS = 0.35    # Irregularidad natural de las hebras (0 = perfectas).
GIRO_HEBRAS_GRADOS = 0.0   # > 0 hace que las hebras bajen en espiral.

# --- Estructura metálica --------------------------------------------------------
DIAM_ALAMBRE_MM = 5.0      # Alambre de los aros y costillas.
ESPESOR_ARO_MM = 2.5       # Espesor de las bandas metálicas visibles.
NUM_COSTILLAS = 8          # Costillas verticales del armazón (debajo de la cuerda).
LARGO_CABLE_CM = 80.0      # Cable desde la lámpara hasta el techo.
POTENCIA_BOMBILLO_W = 25.0

# --- Calidad --------------------------------------------------------------------
PASO_MUESTREO_MM = 1.5     # Distancia entre puntos de cada hebra (menor = más fino).
PUNTOS_PERFIL = 18         # Puntos de la sección de la cuerda (múltiplo de 6).

# --- Escena -------------------------------------------------------------------
CREAR_ESCENA = True        # Cámara, luces y pared listas para renderizar.
SEMILLA = 7

NOMBRE = "Lampara_Cuerda"
NOMBRE_ESCENA = "Lampara_Escena"


# =============================================================================
# Utilidades
# =============================================================================

def cm(v):
    return v / 100.0


def mm(v):
    return v / 1000.0


def hex_a_lineal(h, factor=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(min(1.0, lin(c) * factor) for c in srgb) + (1.0,)


def poner_entrada(nodo, nombres, valor):
    """Asigna una entrada de nodo probando varios nombres (cambian entre versiones)."""
    for n in nombres:
        if n in nodo.inputs:
            nodo.inputs[n].default_value = valor
            return True
    return False


def borrar_coleccion(nombre):
    col = bpy.data.collections.get(nombre)
    if col is None:
        return
    for ob in list(col.all_objects):
        datos = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if datos is not None and datos.users == 0:
            for tipo, almacen in ((bpy.types.Mesh, bpy.data.meshes),
                                  (bpy.types.Curve, bpy.data.curves),
                                  (bpy.types.Light, bpy.data.lights),
                                  (bpy.types.Camera, bpy.data.cameras)):
                if isinstance(datos, tipo):
                    almacen.remove(datos)
                    break
    for sub in list(col.children_recursive):
        bpy.data.collections.remove(sub)
    bpy.data.collections.remove(col)


def quitar_escena_por_defecto():
    """Quita el cubo, la luz y la cámara de la escena inicial de Blender."""
    for nombre, tipo in (("Cube", "MESH"), ("Light", "LIGHT"), ("Camera", "CAMERA")):
        ob = bpy.data.objects.get(nombre)
        if ob is not None and ob.type == tipo:
            bpy.data.objects.remove(ob, do_unlink=True)


def nueva_coleccion(nombre, padre=None):
    col = bpy.data.collections.new(nombre)
    (padre or bpy.context.scene.collection).children.link(col)
    return col


def suavizar_malla(me, angulo=40.0):
    if hasattr(me, "shade_smooth"):
        me.shade_smooth()
        if hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(angulo))
    else:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        if hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(angulo)


def curva(nombre, col, padre, splines, tilts=None, ciclica=False, material=None,
          bevel_obj=None, radio=0.0, resolucion_bisel=3, dimensiones="3D"):
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = dimensiones
    if dimensiones == "3D":
        cu.twist_mode = "MINIMUM"
        cu.fill_mode = "FULL"
    else:
        cu.fill_mode = "NONE"
    cu.use_fill_caps = True
    if bevel_obj is not None:
        cu.bevel_mode = "OBJECT"
        cu.bevel_object = bevel_obj
    elif radio > 0:
        cu.bevel_mode = "ROUND"
        cu.bevel_depth = radio
        cu.bevel_resolution = resolucion_bisel
    for k, pts in enumerate(splines):
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        sp.points.foreach_set("co", [c for p in pts for c in (p[0], p[1], p[2], 1.0)])
        if tilts is not None:
            sp.points.foreach_set("tilt", tilts[k])
        sp.use_cyclic_u = ciclica
        sp.use_smooth = True
    if material is not None:
        cu.materials.append(material)
    ob = bpy.data.objects.new(nombre, cu)
    col.objects.link(ob)
    ob.parent = padre
    return ob


def cilindro(nombre, col, padre, radio, alto, centro, material, segmentos=48):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segmentos,
                          radius1=radio, radius2=radio, depth=alto)
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    suavizar_malla(me)
    me.materials.append(material)
    ob = bpy.data.objects.new(nombre, me)
    ob.location = centro
    col.objects.link(ob)
    ob.parent = padre
    return ob


def esfera(nombre, col, padre, radio, centro, material):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=radio)
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    suavizar_malla(me, 180.0)
    me.materials.append(material)
    ob = bpy.data.objects.new(nombre, me)
    ob.location = centro
    col.objects.link(ob)
    ob.parent = padre
    return ob


def apuntar(ob, objetivo):
    direccion = Vector(objetivo) - ob.location
    ob.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()


# =============================================================================
# Materiales
# =============================================================================

def material_base(nombre):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    salida = nt.nodes.new("ShaderNodeOutputMaterial")
    salida.location = (600, 0)
    return m, nt, salida


def material_cuerda():
    m, nt, salida = material_base("Cuerda_Algodon")
    color = hex_a_lineal(COLOR_CUERDA)
    m.diffuse_color = color

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-900, 0)

    ruido_color = nt.nodes.new("ShaderNodeTexNoise")
    ruido_color.location = (-650, 200)
    poner_entrada(ruido_color, ["Scale"], 22.0)
    poner_entrada(ruido_color, ["Detail"], 3.0)
    nt.links.new(coord.outputs["Object"], ruido_color.inputs["Vector"])

    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.location = (-420, 200)
    rampa.color_ramp.elements[0].position = 0.3
    rampa.color_ramp.elements[0].color = hex_a_lineal(COLOR_CUERDA, 0.78)
    rampa.color_ramp.elements[1].position = 0.7
    rampa.color_ramp.elements[1].color = hex_a_lineal(COLOR_CUERDA, 1.15)
    nt.links.new(ruido_color.outputs["Fac"], rampa.inputs["Fac"])

    ruido_fibra = nt.nodes.new("ShaderNodeTexNoise")
    ruido_fibra.location = (-650, -200)
    poner_entrada(ruido_fibra, ["Scale"], 1400.0)
    poner_entrada(ruido_fibra, ["Detail"], 2.0)
    nt.links.new(coord.outputs["Object"], ruido_fibra.inputs["Vector"])

    relieve = nt.nodes.new("ShaderNodeBump")
    relieve.location = (-420, -200)
    poner_entrada(relieve, ["Strength"], 0.3)
    poner_entrada(relieve, ["Distance"], 0.0003)
    nt.links.new(ruido_fibra.outputs["Fac"], relieve.inputs["Height"])

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (-150, 100)
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(relieve.outputs["Normal"], bsdf.inputs["Normal"])
    poner_entrada(bsdf, ["Roughness"], 0.88)
    poner_entrada(bsdf, ["Specular IOR Level", "Specular"], 0.3)
    poner_entrada(bsdf, ["Sheen Weight", "Sheen"], 0.45)
    poner_entrada(bsdf, ["Sheen Roughness"], 0.4)

    # Un poco de luz atraviesa el algodón: brilla cálido cuando el bombillo está prendido.
    translucido = nt.nodes.new("ShaderNodeBsdfTranslucent")
    translucido.location = (-150, -250)
    translucido.inputs["Color"].default_value = hex_a_lineal(COLOR_CUERDA, 1.4)
    nt.links.new(relieve.outputs["Normal"], translucido.inputs["Normal"])

    mezcla = nt.nodes.new("ShaderNodeMixShader")
    mezcla.location = (300, 0)
    mezcla.inputs["Fac"].default_value = 0.15
    nt.links.new(bsdf.outputs[0], mezcla.inputs[1])
    nt.links.new(translucido.outputs[0], mezcla.inputs[2])
    nt.links.new(mezcla.outputs[0], salida.inputs["Surface"])
    return m


def material_simple(nombre, color, metalico, rugosidad, brillo_tela=0.0):
    m, nt, salida = material_base(nombre)
    m.diffuse_color = color
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    poner_entrada(bsdf, ["Metallic"], metalico)
    poner_entrada(bsdf, ["Roughness"], rugosidad)
    if brillo_tela:
        poner_entrada(bsdf, ["Sheen Weight", "Sheen"], brillo_tela)
    nt.links.new(bsdf.outputs[0], salida.inputs["Surface"])
    return m


def material_bombillo():
    m, nt, salida = material_base("Bombillo")
    m.diffuse_color = (1.0, 0.75, 0.45, 1.0)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.68, 0.38, 1.0)
    em.inputs["Strength"].default_value = 2.5
    nt.links.new(em.outputs[0], salida.inputs["Surface"])
    return m


def material_pared():
    m, nt, salida = material_base("Pared_Estuco")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    poner_entrada(ruido, ["Scale"], 6.0)
    poner_entrada(ruido, ["Detail"], 8.0)
    poner_entrada(ruido, ["Roughness"], 0.6)
    nt.links.new(coord.outputs["Object"], ruido.inputs["Vector"])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = hex_a_lineal("#A88A68")
    rampa.color_ramp.elements[1].color = hex_a_lineal("#C4A988")
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    relieve = nt.nodes.new("ShaderNodeBump")
    poner_entrada(relieve, ["Strength"], 0.12)
    nt.links.new(ruido.outputs["Fac"], relieve.inputs["Height"])
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    poner_entrada(bsdf, ["Roughness"], 0.95)
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(relieve.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], salida.inputs["Surface"])
    return m


# =============================================================================
# Geometría
# =============================================================================

def perfil_cuerda(col, padre, radio, puntos):
    """Sección de una cuerda de 3 cabos: unión de tres círculos superpuestos.

    Al girar esta sección a lo largo de la hebra (tilt) se forma la torsión.
    """
    rp = radio / 1.7       # radio de cada cabo
    dc = 0.7 * rp          # distancia del centro de cada cabo al eje
    pts = []
    for k in range(puntos):
        th = 2.0 * math.pi * k / puntos
        r = 0.0
        for i in range(3):
            d = th - 2.0 * math.pi * i / 3.0
            s, c = dc * math.sin(d), dc * math.cos(d)
            disc = rp * rp - s * s
            if disc >= 0.0:
                r = max(r, c + math.sqrt(disc))
        pts.append((r * math.cos(th), r * math.sin(th), 0.0))
    ob = curva("Perfil_Cuerda", col, padre, [pts], ciclica=True, dimensiones="2D")
    ob.hide_render = True
    return ob


def muestrear_tramo(A, B, abombado, paso):
    """Puntos (t, r, z, normal_r, normal_z) de un tramo del perfil, de A a B.

    La normal apunta hacia afuera de la lámpara.
    """
    dx, dz = B[0] - A[0], B[1] - A[1]
    largo = math.hypot(dx, dz)
    nr0, nz0 = -dz / largo, dx / largo
    n = max(8, int(math.ceil(largo / paso)))
    salida = []
    for j in range(n + 1):
        t = j / n
        b = abombado * math.sin(math.pi * t)
        db = abombado * math.pi * math.cos(math.pi * t)
        r = A[0] + dx * t + nr0 * b
        z = A[1] + dz * t + nz0 * b
        tr, tz = dx + nr0 * db, dz + nz0 * db
        tl = math.hypot(tr, tz)
        salida.append((t, r, z, -tz / tl, tr / tl))
    return salida


def levante_capa(separacion, d):
    """Altura entre capas para que hebras vecinas no se crucen.

    Cubre siempre sqrt(d² - separación²) y llega a cero suavemente, sin dejar
    una línea marcada donde la cuerda pasa de 3 capas a 1.
    """
    k = 1.4 * d
    if separacion >= k:
        return 0.0
    return k * (1.0 - (separacion / k) ** 2) ** 2


def hebras(muestras, n, desfase, giro, rng, d, a, paso_torsion):
    """Hebras de cuerda sobre un tramo del armazón.

    Cerca de las bocas no caben todas lado a lado: se reparten en 3 capas
    (alturas 0, 1 y 2 en rotación) y se asientan en una sola capa hacia el
    centro, donde hay espacio.
    """
    splines, tilts, largo_total = [], [], 0.0
    for i in range(n):
        th0 = 2.0 * math.pi * (i + desfase) / n
        capa = i % 3
        fase = rng.uniform(0.0, 2.0 * math.pi / 3.0)
        amp = rng.uniform(-1.0, 1.0)
        frec = rng.uniform(0.6, 1.6)
        ph = rng.uniform(0.0, 2.0 * math.pi)
        pts, tl = [], []
        recorrido, previo = 0.0, None
        for (t, r, z, nr, nz) in muestras:
            separacion = 2.0 * math.pi * (r + nr * a) / n
            levante = capa * levante_capa(separacion, d)
            off = a + levante
            rc, zc = r + nr * off, z + nz * off
            holgura = max(0.0, separacion - d)
            desvio = (VARIACION_HEBRAS * 0.5 * holgura * math.sin(math.pi * t)
                      * (0.6 * amp + 0.4 * math.sin(2.0 * math.pi * frec * t + ph)))
            th = th0 + desvio / rc + giro * t
            p = (rc * math.cos(th), rc * math.sin(th), zc)
            if previo is not None:
                recorrido += math.dist(p, previo)
            previo = p
            pts.append(p)
            tl.append(fase + 2.0 * math.pi * recorrido / paso_torsion)
        splines.append(pts)
        tilts.append(tl)
        largo_total += recorrido
    return splines, tilts, largo_total


def espiral_ecuador(rc, ze, a, d, paso_torsion, sentido=1):
    """Cuerda enrollada en espiral alrededor de un aro del centro.

    sentido = 1 o -1 cambia la dirección del enrollado (los dos aros del
    centro van en sentidos opuestos, como en espiga).
    """
    vueltas = max(3, round(2.0 * math.pi * rc / d))
    por_vuelta = 24
    n = vueltas * por_vuelta
    pts = []
    for k in range(n):
        phi = 2.0 * math.pi * k / n
        psi = sentido * 2.0 * math.pi * vueltas * k / n
        rr = rc + a * math.cos(psi)
        pts.append((rr * math.cos(phi), rr * math.sin(phi), ze + a * math.sin(psi)))
    largo = sum(math.dist(pts[k], pts[(k + 1) % n]) for k in range(n))
    # Torsión ajustada para que cierre sin salto (la sección se repite cada 1/3 de vuelta).
    giros = max(1.0, round(3.0 * largo / paso_torsion) / 3.0)
    tl, recorrido = [], 0.0
    for k in range(n):
        tl.append(2.0 * math.pi * giros * recorrido / largo)
        recorrido += math.dist(pts[k], pts[(k + 1) % n])
    return pts, tl, largo


def circulo(radio, z, n=160):
    return [(radio * math.cos(2 * math.pi * k / n), radio * math.sin(2 * math.pi * k / n), z)
            for k in range(n)]


def banda(nombre, col, padre, radio, z_centro, alto, espesor, material):
    ob = curva(nombre, col, padre, [circulo(radio, 0.0)], ciclica=True,
               material=material, dimensiones="2D")
    cu = ob.data
    cu.extrude = max(0.0, alto / 2.0 - espesor / 2.0)
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = espesor / 2.0
    cu.bevel_resolution = 3
    ob.location = (0.0, 0.0, z_centro)
    return ob


def medir(objetos):
    """Caja envolvente real (con el grosor de la cuerda) de varios objetos."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    mn = np.full(3, np.inf)
    mx = np.full(3, -np.inf)
    for ob in objetos:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        if not len(co):
            continue
        co = co.reshape(-1, 3) @ np.array(ev.matrix_world.to_3x3()).T + np.array(ev.matrix_world.translation)
        mn = np.minimum(mn, co.min(axis=0))
        mx = np.maximum(mx, co.max(axis=0))
    return Vector(mn), Vector(mx)


def construir_lampara():
    rng = random.Random(SEMILLA)
    if CREAR_ESCENA:
        quitar_escena_por_defecto()
    borrar_coleccion(NOMBRE)

    col = nueva_coleccion(NOMBRE)
    raiz = bpy.data.objects.new(NOMBRE, None)
    raiz.empty_display_type = "PLAIN_AXES"
    raiz.empty_display_size = 0.1
    col.objects.link(raiz)

    # --- Medidas en metros ---------------------------------------------------
    W, H, ZE = cm(ANCHO_CM), cm(ALTO_CM), cm(ALTURA_ECUADOR_CM)
    d = mm(DIAM_CUERDA_MM)
    rr = d / 2.0
    wr = mm(DIAM_ALAMBRE_MM) / 2.0
    bh = cm(ALTO_ARO_CM)
    bt = mm(ESPESOR_ARO_MM)
    abombado = cm(ABOMBADO_CM)
    paso = mm(PASO_MUESTREO_MM)
    paso_torsion = mm(PASO_TORSION_MM)
    giro = math.radians(GIRO_HEBRAS_GRADOS)
    n = max(6, 6 * round(NUM_HEBRAS / 6))      # múltiplo de 6, para rotar las capas

    a = wr + rr                                # centro del alambre -> centro de la cuerda
    rc = W / 2.0 - a - rr                      # aros del centro (la cuerda llega a ANCHO_CM)
    sep_centro = cm(SEPARACION_AROS_CENTRO_CM)
    z_centro_sup = ZE + sep_centro / 2.0       # aro del centro de arriba
    z_centro_inf = ZE - sep_centro / 2.0       # aro del centro de abajo
    z_banda_sup = H - bh / 2.0
    z_banda_inf = bh / 2.0
    r_banda_sup = cm(DIAM_BOCA_SUP_CM) / 2.0
    r_banda_inf = cm(DIAM_BOCA_INF_CM) / 2.0

    def aro_interno(r_banda, z_banda, z_centro, signo):
        """Aro del armazón escondido detrás de la banda metálica."""
        r, z = r_banda - 0.012, z_banda - signo * 0.008
        for _ in range(4):
            dx, dz = (rc - r, z_centro - z) if signo > 0 else (r - rc, z - z_centro)
            largo = math.hypot(dx, dz)
            nr, nz = -dz / largo, dx / largo
            sep = 2.0 * math.pi * (r + nr * a) / n
            levante = 2.0 * levante_capa(sep, d)
            r = r_banda - bt / 2.0 - 0.0005 - rr - nr * (a + levante)
            z = z_banda - nz * (a + levante)
        return (r, z)

    A = aro_interno(r_banda_sup, z_banda_sup, z_centro_sup, +1)
    B_sup = (rc, z_centro_sup)
    B_inf = (rc, z_centro_inf)
    F = aro_interno(r_banda_inf, z_banda_inf, z_centro_inf, -1)

    # Cono de arriba: del aro superior al aro del centro de arriba.
    # Cono de abajo: del aro del centro de abajo al aro inferior.
    tramo_sup = muestrear_tramo(A, B_sup, abombado, paso)
    tramo_inf = muestrear_tramo(B_inf, F, abombado, paso)

    # --- Materiales ----------------------------------------------------------
    m_cuerda = material_cuerda()
    m_cobre = material_simple("Metal_Cobre", hex_a_lineal("#9A6640"), 1.0, 0.38)
    m_negro = material_simple("Metal_Negro", hex_a_lineal("#1E1B18"), 0.85, 0.45)
    m_cable = material_simple("Cable_Tela", hex_a_lineal("#141414"), 0.0, 0.6, 0.3)
    m_bombillo = material_bombillo()

    # --- Cuerda --------------------------------------------------------------
    perfil = perfil_cuerda(col, raiz, rr, max(6, PUNTOS_PERFIL - PUNTOS_PERFIL % 6))

    s_sup, t_sup, l_sup = hebras(tramo_sup, n, 0.0, giro, rng, d, a, paso_torsion)
    s_inf, t_inf, l_inf = hebras(tramo_inf, n, 0.5, giro, rng, d, a, paso_torsion)
    cuerda_sup = curva("Cuerda_Cono_Superior", col, raiz, s_sup, t_sup,
                       material=m_cuerda, bevel_obj=perfil)
    cuerda_inf = curva("Cuerda_Cono_Inferior", col, raiz, s_inf, t_inf,
                       material=m_cuerda, bevel_obj=perfil)

    # Doble aro del centro: cada aro va forrado con cuerda enrollada en espiral.
    pts_es, tl_es, l_es = espiral_ecuador(rc, z_centro_sup, a, d, paso_torsion, 1)
    pts_ei, tl_ei, l_ei = espiral_ecuador(rc, z_centro_inf, a, d, paso_torsion, -1)
    cuerda_centro = curva("Cuerda_Aros_Centro", col, raiz, [pts_es, pts_ei],
                          [tl_es, tl_ei], ciclica=True, material=m_cuerda,
                          bevel_obj=perfil)
    l_e = l_es + l_ei

    # --- Armazón metálico ----------------------------------------------------
    banda_sup = banda("Aro_Superior", col, raiz, r_banda_sup, z_banda_sup, bh, bt, m_cobre)
    banda_inf = banda("Aro_Inferior", col, raiz, r_banda_inf, z_banda_inf, bh, bt, m_cobre)
    curva("Alambres_Centro", col, raiz, [circulo(rc, z_centro_sup), circulo(rc, z_centro_inf)],
          ciclica=True, material=m_negro, radio=wr)
    curva("Alambre_Aro_Sup", col, raiz, [circulo(A[0], A[1])], ciclica=True,
          material=m_negro, radio=wr)
    curva("Alambre_Aro_Inf", col, raiz, [circulo(F[0], F[1])], ciclica=True,
          material=m_negro, radio=wr)
    perfil_rz = []
    for tramo in (tramo_sup, tramo_inf):
        puntos = [(r, z) for (_, r, z, _, _) in tramo]
        perfil_rz += puntos[::4] + ([puntos[-1]] if (len(puntos) - 1) % 4 else [])
    costillas = []
    for k in range(NUM_COSTILLAS):
        ang = 2.0 * math.pi * (k + 0.25) / max(1, NUM_COSTILLAS)
        costillas.append([(r * math.cos(ang), r * math.sin(ang), z) for (r, z) in perfil_rz])
    if costillas:
        curva("Costillas", col, raiz, costillas, material=m_negro, radio=wr)

    # Araña de 3 brazos que sostiene el portabombillo.
    r_collar = 0.014
    brazos = []
    for k in range(3):
        ang = 2.0 * math.pi * k / 3.0 + math.pi / 2.0
        r_fin = r_banda_sup - bt / 2.0
        brazos.append([(r_collar * math.cos(ang), r_collar * math.sin(ang), z_banda_sup),
                       (r_fin * math.cos(ang), r_fin * math.sin(ang), z_banda_sup)])
    curva("Arana", col, raiz, brazos, material=m_negro, radio=0.002)
    cilindro("Collar", col, raiz, r_collar, 0.02, (0, 0, z_banda_sup), m_negro)

    # Portabombillo, bombillo y cable.
    z_socket = H - 0.10
    cilindro("Portabombillo", col, raiz, 0.02, 0.055, (0, 0, z_socket - 0.0275), m_negro)
    radio_bombillo = 0.0475
    z_bombillo = z_socket - 0.055 - 0.04
    esfera("Bombillo", col, raiz, radio_bombillo, (0, 0, z_bombillo), m_bombillo)
    z_techo = H + cm(LARGO_CABLE_CM)
    curva("Cable", col, raiz, [[(0, 0, z_socket), (0, 0, z_techo)]],
          material=m_cable, radio=0.0035)
    cilindro("Floron_Techo", col, raiz, 0.06, 0.025, (0, 0, z_techo + 0.0125), m_negro)

    luz = bpy.data.lights.new("Luz_Bombillo", "POINT")
    luz.energy = POTENCIA_BOMBILLO_W
    luz.color = (1.0, 0.66, 0.36)
    if hasattr(luz, "shadow_soft_size"):
        luz.shadow_soft_size = radio_bombillo
    ob_luz = bpy.data.objects.new("Luz_Bombillo", luz)
    ob_luz.location = (0, 0, z_bombillo)
    col.objects.link(ob_luz)
    ob_luz.parent = raiz

    perfil.hide_set(True)

    # --- Resumen ---------------------------------------------------------------
    pantalla = [cuerda_sup, cuerda_inf, cuerda_centro, banda_sup, banda_inf]
    mn, mx = medir(pantalla)
    medidas = {
        "ancho_cm": round((mx.x - mn.x) * 100, 1),
        "fondo_cm": round((mx.y - mn.y) * 100, 1),
        "alto_cm": round((mx.z - mn.z) * 100, 1),
        "centro_cm": round(ZE * 100, 1),
        "separacion_aros_centro_cm": round(sep_centro * 100, 1),
        "hebras_por_cono": n,
        "cuerda_m": round(l_sup + l_inf + l_e, 1),
    }
    print("\n=== Lámpara de cuerda generada ===")
    print(f"  Ancho: {medidas['ancho_cm']} cm   Alto: {medidas['alto_cm']} cm   "
          f"Centro a {medidas['centro_cm']} cm")
    print(f"  Doble aro en el centro, separados {medidas['separacion_aros_centro_cm']} cm "
          f"(a {round(z_centro_inf * 100, 1)} y {round(z_centro_sup * 100, 1)} cm de altura)")
    print(f"  Hebras por cono: {n}   Cuerda de {DIAM_CUERDA_MM:g} mm aprox.: "
          f"{medidas['cuerda_m']} m (sin contar amarres ni desperdicio)\n")
    return raiz, medidas


# =============================================================================
# Escena (cámara, luces, pared)
# =============================================================================

def construir_escena():
    scene = bpy.context.scene
    borrar_coleccion(NOMBRE_ESCENA)
    col = nueva_coleccion(NOMBRE_ESCENA)

    us = scene.unit_settings
    us.system = "METRIC"
    us.length_unit = "CENTIMETERS"

    H = cm(ALTO_CM)
    centro = (0.0, 0.0, H * 0.5)

    # Pared de fondo.
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3.0)
    me = bpy.data.meshes.new("Pared")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material_pared())
    pared = bpy.data.objects.new("Pared", me)
    pared.location = (0.0, 1.0, H * 0.5)
    pared.rotation_euler = (math.radians(90), 0.0, 0.0)
    col.objects.link(pared)

    # Cámara principal (ligeramente por encima del centro, como en la foto).
    cam_d = bpy.data.cameras.new("Camara_Lampara")
    cam_d.lens = 50
    cam = bpy.data.objects.new("Camara_Lampara", cam_d)
    cam.location = (0.35, -1.55, H + 0.12)
    col.objects.link(cam)
    apuntar(cam, (0.0, 0.0, H * 0.48))
    scene.camera = cam

    # Cámara de frente, ortográfica, para ver las medidas.
    camf_d = bpy.data.cameras.new("Camara_Frente")
    camf_d.type = "ORTHO"
    camf_d.ortho_scale = cm(ANCHO_CM) * 1.5
    camf = bpy.data.objects.new("Camara_Frente", camf_d)
    camf.location = (0.0, -3.0, H * 0.54)
    camf.rotation_euler = (math.radians(90), 0.0, 0.0)
    col.objects.link(camf)

    def luz_area(nombre, energia, tam, pos, color):
        ld = bpy.data.lights.new(nombre, "AREA")
        ld.energy = energia
        ld.size = tam
        ld.color = color
        ob = bpy.data.objects.new(nombre, ld)
        ob.location = pos
        col.objects.link(ob)
        apuntar(ob, centro)
        return ob

    luz_area("Luz_Principal", 120.0, 1.2, (-1.5, -1.2, 1.5), (1.0, 0.85, 0.68))
    luz_area("Luz_Relleno", 25.0, 2.0, (1.8, -1.4, 0.3), (0.95, 0.9, 0.85))

    mundo = scene.world or bpy.data.worlds.new("Mundo")
    scene.world = mundo
    if bpy.app.version < (5, 0, 0):
        mundo.use_nodes = True
    fondo = mundo.node_tree.nodes.get("Background")
    if fondo is None:
        fondo = mundo.node_tree.nodes.new("ShaderNodeBackground")
        salida = mundo.node_tree.nodes.get("World Output") or \
            mundo.node_tree.nodes.new("ShaderNodeOutputWorld")
        mundo.node_tree.links.new(fondo.outputs[0], salida.inputs["Surface"])
    fondo.inputs["Color"].default_value = (0.035, 0.028, 0.022, 1.0)
    fondo.inputs["Strength"].default_value = 1.0

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x = 1080
    r.resolution_y = 1080
    r.resolution_percentage = 100
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return col


def vista_frente():
    """Cámara de frente con fondo claro (para revisar medidas)."""
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["Camara_Frente"]
    bpy.data.objects["Pared"].hide_render = True
    for nombre in ("Luz_Principal", "Luz_Relleno"):
        bpy.data.objects[nombre].data.energy *= 0.6
    fondo = scene.world.node_tree.nodes["Background"]
    fondo.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900


# =============================================================================
# Principal
# =============================================================================

def argumentos():
    if "--" not in sys.argv:
        return None
    p = argparse.ArgumentParser(prog="lampara_cuerda.py")
    p.add_argument("--guardar", help="Ruta del .blend a guardar")
    p.add_argument("--render", help="Ruta de la imagen a renderizar")
    p.add_argument("--vista", choices=("producto", "frente"), default="producto")
    p.add_argument("--muestras", type=int)
    p.add_argument("--res", type=int, help="Resolución (lado mayor en píxeles)")
    return p.parse_args(sys.argv[sys.argv.index("--") + 1:])


def main():
    args = argumentos()
    _, medidas = construir_lampara()
    if CREAR_ESCENA:
        construir_escena()
    if args is None:
        return medidas
    scene = bpy.context.scene
    if args.guardar:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args.guardar))
    if args.render:
        if args.vista == "frente":
            vista_frente()
        if args.muestras:
            scene.cycles.samples = args.muestras
        if args.res:
            r = scene.render
            escala = args.res / max(r.resolution_x, r.resolution_y)
            r.resolution_x = round(r.resolution_x * escala)
            r.resolution_y = round(r.resolution_y * escala)
        scene.render.filepath = bpy.path.abspath(args.render)
        bpy.ops.render.render(write_still=True)
    return medidas


if __name__ == "__main__":
    main()
