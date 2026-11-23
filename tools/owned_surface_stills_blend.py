"""Side-by-side stills of a surface texture pair against the borrowed pair it would replace (tools/make_owned_surfaces.py).

    blender --background --factory-startup --python-exit-code 1 --python tools/owned_surface_stills_blend.py -- \\
        --a <dir>/asphalt_cracked --b <dir>/asphalt_dense --tile 4 --roughness 0.85 --out <prefix>

--a / --b are path prefixes: <prefix>_diffuse.jpg and <prefix>_normal.jpg (OpenGL convention, like every normal map in
assets/textures). Each goes on the same 48 m x 48 m plane, UVs on the kn5 prep's planar grid (u = x / tile, v = y / tile,
the same 4 m grid the road and the concrete get in AC), under the same sun, from three cameras:

  seat   a driver's eye 1.1 m up, looking down the plane: how the surface reads from the car, 40 m ahead
  above  straight down on 24 m x 24 m (6 x 6 tiles): where a repeat shows, it shows here
  close  0.8 m up, looking at the ground 2 m ahead with the sun low: grain and relief

Writes <prefix>_<camera>.png: A on the left, B on the right, a 6 px white bar between. Cycles, Standard view transform
(the texture's own colours, no film look), sun 35 deg up [invented] for seat / above, 12 deg for close.
"""
import math
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]


def arg(name, default=None):
    return a[a.index(name) + 1] if name in a else default


A, B, OUT = arg("--a"), arg("--b"), arg("--out")
TILE = float(arg("--tile", "4"))
ROUGH = float(arg("--roughness", "0.85"))
W, H = int(arg("--w", "1280")), int(arg("--h", "720"))
SAMPLES = int(arg("--samples", "48"))

scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:  # CPU is fine, just slower
    print("[stills] GPU not used:", e)
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"

world = bpy.data.worlds.new("sky")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.55, 0.68, 0.85, 1.0)
bg.inputs[1].default_value = 0.6
scene.world = world

# the plane: 48 m, subdivided so the UVs are exact at every vertex
bpy.ops.mesh.primitive_grid_add(x_subdivisions=48, y_subdivisions=48, size=48.0)
plane = bpy.context.active_object
me = plane.data
while me.uv_layers:                       # the primitive's own 0..1 map would win as the active render UV
    me.uv_layers.remove(me.uv_layers[0])
uv = me.uv_layers.new(name="UVMap")
uv.active = uv.active_render = True
for loop in me.loops:
    co = me.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.x / TILE, co.y / TILE)

mat = bpy.data.materials.new("surface")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = ROUGH
tex_d = nt.nodes.new("ShaderNodeTexImage")
tex_n = nt.nodes.new("ShaderNodeTexImage")
nmap = nt.nodes.new("ShaderNodeNormalMap")
nmap.space = "TANGENT"
nmap.uv_map = "UVMap"
nt.links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.append(mat)

sun_ob = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun_ob.data.energy = 4.0
sun_ob.data.angle = math.radians(0.53)
scene.collection.objects.link(sun_ob)

cam_ob = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam_ob)
scene.camera = cam_ob


def set_sun(elev_deg, az_deg):
    # a sun light shines along its -Z; rotate so it comes from azimuth az (from +y, clockwise) at elev
    sun_ob.rotation_euler = (math.radians(90 - elev_deg), 0.0, math.radians(180 - az_deg))


def look(cam, eye, target, fov_deg=None, ortho=None):
    cam.location = eye
    d = (np.array(target, float) - np.array(eye, float))
    from mathutils import Vector
    cam.rotation_euler = Vector(d.tolist()).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.angle = math.radians(fov_deg)
    cam.data.clip_start, cam.data.clip_end = 0.02, 500.0


CAMS = {
    "seat":  dict(eye=(1.0, -22.0, 1.1), target=(1.0, 18.0, 0.0), fov=62, sun=(35, 210)),
    "above": dict(eye=(0.0, 0.0, 60.0), target=(0.0, 0.001, 0.0), ortho=24.0, sun=(35, 210)),
    "close": dict(eye=(0.3, -1.0, 0.8), target=(0.3, 1.2, 0.0), fov=50, sun=(12, 160)),
}


def render_one(prefix, cam):
    tex_d.image = bpy.data.images.load(prefix + "_diffuse.jpg", check_existing=True)
    tex_n.image = bpy.data.images.load(prefix + "_normal.jpg", check_existing=True)
    tex_n.image.colorspace_settings.name = "Non-Color"
    c = CAMS[cam]
    set_sun(*c["sun"])
    look(cam_ob, c["eye"], c["target"], c.get("fov"), c.get("ortho"))
    path = f"{OUT}_{cam}_{'a' if prefix == A else 'b'}.png"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def pixels(path):
    im = bpy.data.images.load(path)
    px = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(px)
    return px.reshape(im.size[1], im.size[0], 4)


for cam in CAMS:
    pa, pb = render_one(A, cam), render_one(B, cam)
    left, right = pixels(pa), pixels(pb)
    bar = np.ones((left.shape[0], 6, 4), np.float32)
    both = np.concatenate([left, bar, right], axis=1)
    out = bpy.data.images.new(f"{cam}_ab", both.shape[1], both.shape[0], alpha=True)
    out.pixels.foreach_set(both.ravel())
    out.filepath_raw = f"{OUT}_{cam}.png"
    out.file_format = "PNG"
    out.save()
    print(f"[stills] {OUT}_{cam}.png (left {A.split('/')[-1]}, right {B.split('/')[-1]})")
