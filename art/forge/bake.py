"""Bake Forge's materials into texture maps the dial's slice renderer lights live: for each material
a colour map (`<name>-albedo.webp`), a tangent-space normal map (`<name>-normal.webp`) and a
roughness map (`<name>-rough.webp`), covering the whole ring (no tiling, so no seams).

    blender -b -P art/forge/bake.py -- [--size 1024] [--only stone]
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(f"--{name}") + 1] if f"--{name}" in argv else default


SIZE = int(opt("size", "1024"))
ONLY = set((opt("only") or "stone").split(","))
OUT = Path(__file__).resolve().parent.parent.parent / "themes" / "forge"

# Reuse the materials from build.py without running its scene.
src = (Path(__file__).resolve().parent / "build.py").read_text()
head = src[: src.index("# ── models")]
head = head.replace('ONLY = set((opt("only") or "plate,medallion,tiles").split(","))', "ONLY = set()")
exec(compile(head, "build.py", "exec"))
ONLY = set((opt("only") or "stone").split(","))  # build.py's head set its own

scene = bpy.context.scene
scene.cycles.samples = 64
scene.cycles.bake_type = "DIFFUSE"


def bake_material(mat, name, extent=2.7):
    """Bake `mat` on a flat plane `extent` units wide (the ring's footprint)."""
    bpy.ops.mesh.primitive_plane_add(size=extent, location=(0, 0, 0))
    plane = bpy.context.active_object
    # Enough geometry for the bevel/AO nodes to sample; the plane itself stays flat.
    sub = plane.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 4
    plane.data.materials.append(mat)
    nt = mat.node_tree
    results = {}
    for kind, bake_type, colorspace in (("albedo", "DIFFUSE", "sRGB"), ("normal", "NORMAL", "Non-Color"), ("rough", "ROUGHNESS", "Non-Color")):
        img = bpy.data.images.new(f"{name}-{kind}", SIZE, SIZE, alpha=False, float_buffer=kind == "normal")
        img.colorspace_settings.name = colorspace
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        plane.select_set(True)
        bpy.context.view_layer.objects.active = plane
        bake = scene.render.bake
        if bake_type == "DIFFUSE":
            bake.use_pass_direct = False
            bake.use_pass_indirect = False
            bake.use_pass_color = True
        bake.margin = 0
        bpy.ops.object.bake(type=bake_type, normal_space="TANGENT")
        img.filepath_raw = str(OUT / f"{name}-{kind}.webp")
        img.file_format = "WEBP"
        img.save()
        nt.nodes.remove(node)
        results[kind] = img
        print(f"baked {name}-{kind}.webp")
    bpy.data.objects.remove(plane)
    return results


OUT.mkdir(parents=True, exist_ok=True)
if "stone" in ONLY:
    bake_material(granite("stone-bake", seed=11.0), "stone")
if "iron" in ONLY:
    bake_material(rusted_iron("iron-bake", seed=7.0), "iron", extent=4.0)
