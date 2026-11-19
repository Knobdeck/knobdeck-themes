"""Forge's art: a rusted iron wheel set with carved stone tiles, rendered in Blender (Cycles) as
transparent WebP layers. The items *are* the tiles: one slab per slot, cut to the slot's wedge.

    blender -b -P art/forge/build.py -- [--samples 256] [--only plate,medallion,tiles] [--preview]

Writes themes/forge/plate.webp (the wheel), medallion.webp (the center) and tile-<n>.webp for a
ring of n = 3..16 items (the slab for one slot, pointing up; the theme turns it into place).
Everything is built here from primitives, so the theme stays CC0. 1 Blender unit = 100 CSS px.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "themes" / "forge"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(f"--{name}") + 1] if f"--{name}" in argv else default


SAMPLES = int(opt("samples", "256"))
ONLY = set((opt("only") or "plate,medallion,tiles").split(","))
PREVIEW = "--preview" in argv
TILE_COUNTS = [int(x) for x in (opt("counts") or ",".join(map(str, range(3, 17)))).split(",")]

# Geometry, in Blender units (×100 = CSS px). The theme CSS uses the same numbers.
PLATE_R = 1.90          # the wheel
TILE_IN, TILE_OUT = 0.64, 1.28   # the stone tiles' ring (items sit at r = 0.96)
CHANNEL_IN, CHANNEL_OUT = 0.60, 1.32
SOCKET_R, SOCKET_COUNT = 1.60, 16
MEDALLION_R = 0.56
GAP = 0.045             # the joint between two tiles, constant along the ring

# ── scene ───────────────────────────────────────────────────────────────────────

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = True
scene.cycles.device = "GPU"
scene.cycles.samples = 48 if PREVIEW else SAMPLES
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.35
scene.render.image_settings.file_format = "WEBP"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.quality = 90


def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def mesh_obj(name, bm, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def apply_mods(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def boolean(obj, cutter, op="DIFFERENCE"):
    m = obj.modifiers.new("bool", "BOOLEAN")
    m.operation = op
    m.solver = "EXACT"
    m.object = cutter
    apply_mods(obj)
    bpy.data.objects.remove(cutter)


def smooth(obj, bevel=0.01, segments=3, angle=35):
    m = obj.modifiers.new("bevel", "BEVEL")
    m.width = bevel
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.harden_normals = True
    obj.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def cylinder(coll, r, depth, z, verts=192):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=(0, 0, z))
    return link(bpy.context.active_object, coll)


def box(coll, size, loc, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot_z))
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return link(o, coll)


def annulus(coll, r_in, r_out, z0, z1, verts=192):
    outer = cylinder(coll, r_out, z1 - z0, (z0 + z1) / 2, verts)
    boolean(outer, cylinder(coll, r_in, (z1 - z0) + 0.4, (z0 + z1) / 2, verts))
    return outer


def sector(coll, r_in, r_out, half_angle_in, half_angle_out, z0, z1, steps=64):
    """An annular slab around +Y: its sides keep a constant joint, so the half-angle differs
    at the inner and outer radius."""
    bm = bmesh.new()
    pts = []
    for k in range(steps + 1):
        t = -half_angle_out + 2 * half_angle_out * k / steps
        pts.append((r_out * math.sin(t), r_out * math.cos(t)))
    for k in range(steps, -1, -1):
        t = -half_angle_in + 2 * half_angle_in * k / steps
        pts.append((r_in * math.sin(t), r_in * math.cos(t)))
    face = bm.faces.new([bm.verts.new((x, y, z0)) for x, y in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj("sector", bm, coll)


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.material_index = 0


# ── materials ──────────────────────────────────────────────────────────────────

class Nodes:
    """A small helper for building node trees in code."""

    def __init__(self, mat, seed):
        mat.use_nodes = True
        self.t = mat.node_tree
        self.n, self.l = self.t.nodes, self.t.links
        self.n.clear()
        self.seed = seed
        self.coord = self.n.new("ShaderNodeTexCoord")
        self.geo = self.n.new("ShaderNodeNewGeometry")
        self.out = self.n.new("ShaderNodeOutputMaterial")

    def node(self, kind, **inputs):
        x = self.n.new(kind)
        for k, v in inputs.items():
            x.inputs[k].default_value = v
        return x

    def link(self, a, b):
        self.l.new(a, b)

    def noise(self, scale, detail=8.0, rough=0.55, dist=0.0, kind="ShaderNodeTexNoise"):
        x = self.n.new(kind)
        x.noise_dimensions = "4D"
        for k, v in (("Scale", scale), ("Detail", detail), ("Roughness", rough), ("Distortion", dist), ("W", self.seed)):
            x.inputs[k].default_value = v
        self.l.new(self.coord.outputs["Object"], x.inputs["Vector"])
        return x.outputs["Fac"]

    def voronoi(self, scale, feature="DISTANCE_TO_EDGE"):
        x = self.n.new("ShaderNodeTexVoronoi")
        x.voronoi_dimensions = "4D"
        x.feature = feature
        x.inputs["Scale"].default_value = scale
        x.inputs["W"].default_value = self.seed
        self.l.new(self.coord.outputs["Object"], x.inputs["Vector"])
        return x.outputs["Distance"]

    def ramp(self, src, stops):
        r = self.n.new("ShaderNodeValToRGB")
        els = r.color_ramp.elements
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = (*col, 1)
        self.l.new(src, r.inputs["Fac"])
        return r.outputs["Color"]

    def bw(self, color):
        x = self.n.new("ShaderNodeRGBToBW")
        self.l.new(color, x.inputs["Color"])
        return x.outputs["Val"]

    def math(self, op, a, b=None, clamp=False):
        x = self.n.new("ShaderNodeMath")
        x.operation = op
        x.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                self.l.new(v, x.inputs[i])
        return x.outputs["Value"]

    def mixc(self, fac, a, b):
        x = self.n.new("ShaderNodeMix")
        x.data_type = "RGBA"
        if isinstance(fac, (int, float)):
            x.inputs[0].default_value = fac
        else:
            self.l.new(fac, x.inputs[0])
        for i, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                x.inputs[i].default_value = (*v, 1)
            else:
                self.l.new(v, x.inputs[i])
        return x.outputs[2]

    def edges(self, radius=0.012, gain=24.0):
        """1 on rounded convex edges (bevel normal vs true normal)."""
        bev = self.node("ShaderNodeBevel", Radius=radius)
        bev.samples = 8
        dot = self.n.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        self.l.new(bev.outputs["Normal"], dot.inputs[0])
        self.l.new(self.geo.outputs["Normal"], dot.inputs[1])
        return self.math("MULTIPLY", self.math("SUBTRACT", 1.0, dot.outputs["Value"]), gain, clamp=True), bev.outputs["Normal"]

    def cavity(self, dist=0.06):
        ao = self.node("ShaderNodeAmbientOcclusion", Distance=dist)
        ao.samples = 16
        return self.math("SUBTRACT", 1.0, ao.outputs["AO"])

    def bump(self, height, strength, distance, normal=None):
        b = self.node("ShaderNodeBump", Strength=strength, Distance=distance)
        self.l.new(height, b.inputs["Height"])
        if normal is not None:
            self.l.new(normal, b.inputs["Normal"])
        return b.outputs["Normal"]

    def principled(self, color, rough, metallic=0.0, normal=None):
        p = self.node("ShaderNodeBsdfPrincipled", Metallic=metallic)
        for sock, v in (("Base Color", color), ("Roughness", rough)):
            if isinstance(v, (int, float)):
                p.inputs[sock].default_value = v
            elif isinstance(v, tuple):
                p.inputs[sock].default_value = (*v, 1)
            else:
                self.l.new(v, p.inputs[sock])
        if normal is not None:
            self.l.new(normal, p.inputs["Normal"])
        return p.outputs["BSDF"]

    def mixs(self, fac, a, b):
        m = self.n.new("ShaderNodeMixShader")
        self.l.new(fac, m.inputs["Fac"])
        self.l.new(a, m.inputs[1])
        self.l.new(b, m.inputs[2])
        return m.outputs["Shader"]

    def done(self, shader):
        self.l.new(shader, self.out.inputs["Surface"])


def rusted_iron(name, seed=1.0):
    """Wrought iron gone to rust: dark metal, orange-brown scale in patches and recesses, edges
    rubbed back to grey steel."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat, seed)
    edge, bev = N.edges(0.014, 20.0)
    cav = N.cavity(0.08)
    patch = N.bw(N.ramp(N.noise(2.6, 14, 0.65, 0.5), [(0.42, (0, 0, 0)), (0.6, (1, 1, 1))]))
    speck = N.bw(N.ramp(N.noise(40, 6, 0.7), [(0.35, (0.3, 0.3, 0.3)), (0.65, (1, 1, 1))]))
    rust = N.math("MULTIPLY", N.math("MAXIMUM", N.math("MULTIPLY", patch, speck), N.math("MULTIPLY", cav, 1.8)), 1.0, clamp=True)
    rust = N.math("SUBTRACT", rust, N.math("MULTIPLY", edge, 1.2), clamp=True)
    # Old rust is brown, not orange: dark umber scale with only a little ochre in the freshest spots.
    rust_col = N.ramp(N.noise(9, 10, 0.6), [(0.25, (0.045, 0.022, 0.012)), (0.5, (0.11, 0.050, 0.022)), (0.72, (0.20, 0.095, 0.038)), (0.88, (0.085, 0.040, 0.020))])
    iron_col = N.mixc(edge, N.ramp(N.noise(6, 8), [(0.3, (0.030, 0.029, 0.028)), (0.7, (0.075, 0.070, 0.065))]), (0.34, 0.32, 0.30))
    height = N.math("ADD", N.noise(4, 3, 0.5), N.math("MULTIPLY", N.noise(180, 2), 0.4))
    height = N.math("ADD", height, N.math("MULTIPLY", N.math("MULTIPLY", N.noise(55, 6, 0.7), rust), 1.5))
    normal = N.bump(height, 0.45, 0.005, bev)
    iron = N.principled(iron_col, N.math("ADD", 0.38, N.math("MULTIPLY", N.noise(25), 0.25)), 1.0, normal)
    scale = N.principled(rust_col, 0.92, 0.0, normal)
    N.done(N.mixs(rust, iron, scale))
    return mat


def granite(name, seed=2.0):
    """Carved grey stone: speckled granite, hairline cracks, dust in the recesses, chipped edges a
    shade lighter."""
    mat = bpy.data.materials.new(name)
    N = Nodes(mat, seed)
    edge, bev = N.edges(0.02, 14.0)
    cav = N.cavity(0.05)
    base = N.ramp(N.noise(5, 12, 0.6), [(0.3, (0.085, 0.085, 0.09)), (0.7, (0.22, 0.215, 0.22))])
    flecks = N.ramp(N.noise(120, 2, 0.5), [(0.62, (0, 0, 0)), (0.7, (1, 1, 1))])
    col = N.mixc(N.math("MULTIPLY", N.bw(flecks), 0.5), base, (0.62, 0.62, 0.64))
    dark = N.ramp(N.noise(220, 2, 0.5), [(0.66, (0, 0, 0)), (0.72, (1, 1, 1))])
    col = N.mixc(N.math("MULTIPLY", N.bw(dark), 0.6), col, (0.05, 0.05, 0.05))
    # Cracks: the edges of large Voronoi cells, kept only in places.
    crack_line = N.math("LESS_THAN", N.voronoi(3.2), 0.018)
    crack_mask = N.bw(N.ramp(N.noise(1.6, 4, 0.5), [(0.5, (0, 0, 0)), (0.58, (1, 1, 1))]))
    crack = N.math("MULTIPLY", crack_line, crack_mask)
    col = N.mixc(crack, col, (0.03, 0.03, 0.03))
    col = N.mixc(N.math("MULTIPLY", cav, 1.4, clamp=True), col, (0.08, 0.075, 0.07))
    col = N.mixc(N.math("MULTIPLY", edge, 0.55), col, (0.48, 0.48, 0.50))
    height = N.math("ADD", N.noise(8, 10, 0.6), N.math("MULTIPLY", N.noise(90, 3), 0.25))
    height = N.math("SUBTRACT", height, N.math("MULTIPLY", crack, 1.5))
    normal = N.bump(height, 0.55, 0.006, bev)
    rough = N.math("ADD", 0.6, N.math("MULTIPLY", N.noise(30), 0.3))
    N.done(N.principled(col, rough, 0.0, normal))
    return mat


def bronze(name, seed=3.0):
    mat = bpy.data.materials.new(name)
    N = Nodes(mat, seed)
    edge, bev = N.edges(0.01, 24.0)
    cav = N.cavity(0.04)
    patch = N.bw(N.ramp(N.noise(3, 12, 0.6, 0.3), [(0.52, (0, 0, 0)), (0.6, (1, 1, 1))]))
    crust = N.math("SUBTRACT", N.math("MAXIMUM", N.math("MULTIPLY", patch, 0.8), N.math("MULTIPLY", cav, 2.0)), edge, clamp=True)
    metal_col = N.mixc(edge, N.ramp(N.noise(7, 10), [(0.3, (0.14, 0.085, 0.035)), (0.7, (0.30, 0.19, 0.08))]), (0.70, 0.50, 0.24))
    green = N.ramp(N.noise(12, 10), [(0.3, (0.04, 0.13, 0.10)), (0.65, (0.18, 0.38, 0.30))])
    normal = N.bump(N.math("ADD", N.noise(6, 3), N.math("MULTIPLY", N.noise(200, 2), 0.35)), 0.3, 0.004, bev)
    N.done(N.mixs(crust, N.principled(metal_col, 0.35, 1.0, normal), N.principled(green, 0.85, 0.0, normal)))
    return mat


def ember(name, color=(1.0, 0.45, 0.12), strength=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(e.outputs[0], n["Material Output"].inputs["Surface"])
    return mat


# ── models ──────────────────────────────────────────────────────────────────────

def plate(coll):
    """The wheel: rusted iron, a notched rim, a ring of bronze coin sockets, a deep channel where
    the tiles sit and a recess for the medallion."""
    top = 0.16
    w = cylinder(coll, PLATE_R, top, top / 2, verts=256)
    for i in range(24):
        a = 2 * math.pi * (i + 0.5) / 24
        boolean(w, box(coll, (0.10, 0.18, 0.4), ((PLATE_R - 0.04) * math.sin(a), (PLATE_R - 0.04) * math.cos(a), top / 2), -a))
    boolean(w, annulus(coll, CHANNEL_IN, CHANNEL_OUT, top - 0.07, top + 0.1))
    boolean(w, cylinder(coll, MEDALLION_R + 0.03, 0.3, top + 0.1 - 0.04, verts=192))
    # A raised lip round the channel's outer edge, and a groove at the wheel's edge.
    boolean(w, annulus(coll, CHANNEL_OUT, CHANNEL_OUT + 0.05, top, top + 0.02), "UNION")
    bpy.ops.mesh.primitive_torus_add(major_radius=PLATE_R - 0.16, minor_radius=0.012, major_segments=256, minor_segments=12, location=(0, 0, top))
    boolean(w, link(bpy.context.active_object, coll))
    sockets = []
    for i in range(SOCKET_COUNT):
        a = 2 * math.pi * i / SOCKET_COUNT
        x, y = SOCKET_R * math.sin(a), SOCKET_R * math.cos(a)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.2, vertices=64, location=(x, y, top))
        boolean(w, link(bpy.context.active_object, coll))
        bpy.ops.mesh.primitive_cylinder_add(radius=0.135, depth=0.05, vertices=64, location=(x, y, top - 0.03))
        coin = link(bpy.context.active_object, coll)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.105, depth=0.05, vertices=64, location=(x, y, top))
        boolean(coin, link(bpy.context.active_object, coll))
        sockets.append(smooth(coin, 0.008))
    smooth(w, 0.012)
    return w, sockets


def medallion(coll):
    """The center: an iron boss whose eight star points sit round its rim, framing a plain recessed
    dish in the middle, where the dial shows the profile's icon (and the hovered item's name)."""
    m = cylinder(coll, MEDALLION_R, 0.12, 0.06, verts=192)
    # The dish: a shallow recess r < 0.36 with a rounded lip.
    boolean(m, cylinder(coll, 0.36, 0.2, 0.12 + 0.1 - 0.035, verts=192))
    bpy.ops.mesh.primitive_torus_add(major_radius=MEDALLION_R - 0.05, minor_radius=0.010, major_segments=192, minor_segments=12, location=(0, 0, 0.12))
    boolean(m, link(bpy.context.active_object, coll))
    # Eight star points on the rim, pointing out, between the dish and the edge.
    star = None
    for i in range(8):
        a = 2 * math.pi * i / 8
        bm = bmesh.new()
        tip, base, w = 0.53, 0.37, 0.055
        pts = [(tip * math.sin(a), tip * math.cos(a)),
               (base * math.sin(a) + w * math.cos(a), base * math.cos(a) - w * math.sin(a)),
               ((base - 0.02) * math.sin(a), (base - 0.02) * math.cos(a)),
               (base * math.sin(a) - w * math.cos(a), base * math.cos(a) + w * math.sin(a))]
        face = bm.faces.new([bm.verts.new((x, y, 0.11)) for x, y in pts])
        ext = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.translate(bm, vec=(0, 0, 0.04), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
        point = mesh_obj(f"point{i}", bm, coll)
        if star is None:
            star = point
        else:
            boolean(star, point, "UNION")
    smooth(star, 0.006, 2, 30)
    smooth(m, 0.012)
    return m, star


def tile(coll, n):
    """One slot's stone slab for a ring of n: an annular sector with a constant joint to its
    neighbours, a raised border and a sunken field for the rune, chipped a little. Built as a quad
    grid (so it shades and displaces cleanly), the field pushed down by extruding its faces."""
    thick, field_depth, border = 0.11, 0.028, 0.06
    radial, angular = 20, max(16, 96 // n * 2)
    bm = bmesh.new()
    grid = []
    for i in range(radial + 1):
        r = TILE_IN + (TILE_OUT - TILE_IN) * i / radial
        half = math.pi / n - GAP / 2 / r
        row = []
        for j in range(angular + 1):
            t = -half + 2 * half * j / angular
            row.append(bm.verts.new((r * math.sin(t), r * math.cos(t), thick)))
        grid.append(row)
    faces = []
    for i in range(radial):
        for j in range(angular):
            faces.append((i, j, bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))))
    # The field: faces at least `border` in from every edge of the slab.
    field = []
    for i, j, f in faces:
        c = f.calc_center_median()
        r = math.hypot(c.x, c.y)
        arc = abs(math.atan2(c.x, c.y)) * r
        edge_arc = (math.pi / n) * r - GAP / 2
        if TILE_IN + border < r < TILE_OUT - border and arc < edge_arc - border:
            field.append(f)
    ext = bmesh.ops.extrude_face_region(bm, geom=field)
    bmesh.ops.translate(bm, vec=(0, 0, -field_depth), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.delete(bm, geom=field, context="FACES")
    # Give the slab its body: extrude the whole top down to z = 0.
    top = list(bm.faces)
    ext = bmesh.ops.extrude_face_region(bm, geom=top)
    down = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    for v in down:
        v.co.z = 0.0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s = mesh_obj("tile", bm, coll)
    smooth(s, 0.016, 3, 40)
    tex = bpy.data.textures.new(f"chips{n}", "CLOUDS")
    tex.noise_scale = 0.06
    d = s.modifiers.new("chips", "DISPLACE")
    d.texture = tex
    d.strength = 0.007
    d.mid_level = 0.5
    s.modifiers.move(s.modifiers.find("chips"), 0)
    return s


# ── light ───────────────────────────────────────────────────────────────────────

def area(name, loc, size, energy, color):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def rigs():
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
    # Still parts (wheel, medallion): a warm key from the top left, a cool rim, a little fill.
    key = [area("key", (-3.6, 3.2, 3.0), 3.0, 620, (1.0, 0.86, 0.70)),
           area("rim", (3.4, -3.0, 1.6), 2.5, 190, (0.62, 0.76, 1.0)),
           area("fill", (2.8, 3.6, 3.4), 4.0, 90, (1.0, 0.92, 0.84)),
           area("top", (0.6, 0.8, 7.0), 1.5, 30, (1.0, 0.96, 0.9))]
    # Tiles, which the theme turns into place: the same light all round, so no slot is lit
    # differently from another.
    even = [area(f"ring{i}", (3.6 * math.cos(i * math.pi / 4), 3.6 * math.sin(i * math.pi / 4), 1.6), 2.2, 85, (1.0, 0.9, 0.78))
            for i in range(8)]
    even.append(area("etop", (0, 0, 7.0), 2.0, 30, (1.0, 0.96, 0.9)))
    return {"key": key, "even": even}


def camera(scale):
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = scale
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 10)
    scene.camera = cam
    return cam


def shadow_catcher(coll, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, z - 0.001))
    p = link(bpy.context.active_object, coll)
    p.is_shadow_catcher = True
    return p


# ── build and render ────────────────────────────────────────────────────────────

lights = rigs()
cam = camera(4.0)
OUT.mkdir(parents=True, exist_ok=True)
iron = rusted_iron("iron")
stone = granite("stone")
brass = bronze("bronze")
glow = ember("ember")
jobs = []  # (name, collection, ortho scale, resolution, rig)

if "plate" in ONLY:
    c = collection("plate")
    w, sockets = plate(c)
    assign(w, iron)
    for s in sockets:
        assign(s, brass)
    shadow_catcher(c)
    jobs.append(("plate", c, 2 * PLATE_R + 0.12, 1200, "key"))

if "medallion" in ONLY:
    c = collection("medallion")
    m, star = medallion(c)
    assign(m, rusted_iron("iron2", seed=4.0))
    assign(star, bronze("bronze2", seed=5.0))
    shadow_catcher(c)
    jobs.append(("medallion", c, 2 * MEDALLION_R + 0.08, 384, "key"))

if "tiles" in ONLY:
    for n in TILE_COUNTS:
        c = collection(f"tile{n}")
        t = tile(c, n)
        assign(t, granite(f"stone{n}", seed=10.0 + n))
        jobs.append((f"tile-{n}", c, 2 * TILE_OUT + 0.12, 840, "even"))

for name, coll, scale, res, rig in jobs:
    for _, oc, *_ in jobs:
        oc.hide_render = oc is not coll
    for rname, objs in lights.items():
        for o in objs:
            o.hide_render = rname != rig
    cam.data.ortho_scale = scale
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.filepath = str(OUT / f"{name}.webp")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {name}.webp")
