import sys
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Fix GLSL 130/140 incompatibility on macOS OpenGL
if sys.platform == 'darwin':
	import ursina.shaders.unlit_shader as _us
	_v120 = '''#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ModelMatrix;
attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uvs;
attribute vec4 p3d_Color;
varying vec4 vertex_color;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uvs = p3d_MultiTexCoord0;
    vertex_color = p3d_Color;
}
'''
	_f120 = '''#version 120
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
varying vec2 uvs;
varying vec4 vertex_color;
varying vec3 vertex_world_position;

void main() {
    vec4 color = texture2D(p3d_Texture0, uvs) * p3d_ColorScale * vertex_color;
    gl_FragColor = color;
}
'''
	_mac_shader = Shader(name='unlit_shader', language=Shader.GLSL, vertex=_v120, fragment=_f120)
	_us.unlit_shader = _mac_shader
	Entity.default_shader = _mac_shader

app = Ursina()
grass_texture = load_texture('assets/grass_block.png')
stone_texture = load_texture('assets/stone_block.png')
brick_texture = load_texture('assets/brick_block.png')
dirt_texture  = load_texture('assets/dirt_block.png')
sky_texture   = load_texture('assets/skybox.png')
arm_texture   = load_texture('assets/arm_texture.png')
punch_sound   = Audio('assets/punch_sound',loop = False, autoplay = False)
block_pick = 1

window.title = 'MINECRAFT — C.C.I. SYSTEM'
window.borderless = False
window.size = (1280, 720)
window.center_on_screen()
window.fps_counter.enabled = False
window.exit_button.visible = False

def input(key):
	if key == 'escape':
		application.quit()

def update():
	global block_pick

	if held_keys['left mouse'] or held_keys['right mouse']:
		hand.active()
	else:
		hand.passive()

	if held_keys['1']: block_pick = 1
	if held_keys['2']: block_pick = 2
	if held_keys['3']: block_pick = 3
	if held_keys['4']: block_pick = 4

class Voxel(Button):
	def __init__(self, position = (0,0,0), texture = grass_texture):
		super().__init__(
			parent = scene,
			position = position,
			model = 'assets/block',
			origin_y = 0.5,
			texture = texture,
			color = color.hsv(0, 0, random.uniform(0.9, 1)),
			shader = Entity.default_shader,
			scale = 0.5)

	def input(self,key):
		if self.hovered:
			if key == 'left mouse down':
				punch_sound.play()
				if block_pick == 1: voxel = Voxel(position = self.position + mouse.normal, texture = grass_texture)
				if block_pick == 2: voxel = Voxel(position = self.position + mouse.normal, texture = stone_texture)
				if block_pick == 3: voxel = Voxel(position = self.position + mouse.normal, texture = brick_texture)
				if block_pick == 4: voxel = Voxel(position = self.position + mouse.normal, texture = dirt_texture)

			if key == 'right mouse down':
				punch_sound.play()
				destroy(self)

class Sky(Entity):
	def __init__(self):
		super().__init__(
			parent = scene,
			model = 'sphere',
			texture = sky_texture,
			scale = 150,
			double_sided = True)

class Hand(Entity):
	def __init__(self):
		super().__init__(
			parent = camera.ui,
			model = 'assets/arm',
			texture = arm_texture,
			scale = 0.2,
			rotation = Vec3(150,-10,0),
			position = Vec2(0.4,-0.6))

	def active(self):
		self.position = Vec2(0.3,-0.5)

	def passive(self):
		self.position = Vec2(0.4,-0.6)

for z in range(20):
	for x in range(20):
		voxel = Voxel(position = (x,0,z))

player = FirstPersonController()
sky = Sky()
hand = Hand()

app.run()