"""Project exact model dimensions into the existing top-view camera; no render."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

OUT=Path(__file__).resolve().parent
ROOT=Path('/Users/alissachang/Desktop/大專/夾傘機構/雙組前後9mm留殼模擬_20261030')
report=json.loads((ROOT/'前後9mm外殼_模擬檢查.json').read_text())
scene=bpy.context.scene
scene.render.resolution_x=scene.render.resolution_y=1450
scene.render.resolution_percentage=100
data=bpy.data.cameras.new('Existing top view projection')
data.type='ORTHO'
data.ortho_scale=.19
data.clip_start=.001
data.clip_end=100
camera=bpy.data.objects.new('Existing top view projection',data)
scene.collection.objects.link(camera)
camera.location=(.005,.22,1.20)
camera.rotation_euler=(Vector((0,.20,.66))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
bpy.context.view_layer.update()

rear=Vector(report['verified_mechanism_centers_preview_metres']['後組']['驅動輪_基本圓柱'])
front=Vector(report['verified_mechanism_centers_preview_metres']['前組']['驅動輪_基本圓柱'])
outer_rear=report['measured_groove_cm']['y_min']/100
outer_front=report['measured_groove_cm']['y_max']/100
inner_rear=outer_rear+.009
inner_front=outer_front-.009
z=rear.z

def point(x,y,height=z):
    q=world_to_camera_view(scene,camera,Vector((x,y,height)))
    return [q.x*1450,(1-q.y)*1450]

chains={
    'center':{'a':point(0,rear.y),'b':point(0,front.y),
              'da':point(-.072,rear.y),'db':point(-.072,front.y),'mm':60},
    'net_gap':{'a':point(.028,rear.y+.009),'b':point(.028,front.y-.009),
               'da':point(.064,rear.y+.009),'db':point(.064,front.y-.009),'mm':42},
    'rear_thickness':{'a':point(.028,rear.y-.009),'b':point(.028,rear.y+.009),
               'da':point(.064,rear.y-.009),'db':point(.064,rear.y+.009),'mm':18},
    'front_thickness':{'a':point(.028,front.y-.009),'b':point(.028,front.y+.009),
               'da':point(.064,front.y-.009),'db':point(.064,front.y+.009),'mm':18},
    'rear_clearance':{'a':point(-.026,inner_rear),'b':point(-.026,rear.y-.009),
               'da':point(-.052,inner_rear),'db':point(-.052,rear.y-.009),'mm':(rear.y-.009-inner_rear)*1000},
    'front_clearance':{'a':point(-.026,front.y+.009),'b':point(-.026,inner_front),
               'da':point(-.052,front.y+.009),'db':point(-.052,inner_front),'mm':(inner_front-front.y-.009)*1000},
    'left_clearance':{'a':point(-.045,rear.y),'b':point(-.038,rear.y),
               'da':point(-.045,rear.y),'db':point(-.038,rear.y),'mm':7},
    'right_clearance':{'a':point(.038,front.y),'b':point(.045,front.y),
               'da':point(.038,front.y),'db':point(.045,front.y),'mm':7},
    'rear_skin':{'a':point(.020,outer_rear,.70),'b':point(.020,inner_rear,.70),
               'da':point(.043,outer_rear,.70),'db':point(.043,inner_rear,.70),'mm':9},
    'front_skin':{'a':point(.020,inner_front,.70),'b':point(.020,outer_front,.70),
               'da':point(.043,inner_front,.70),'db':point(.043,outer_front,.70),'mm':9},
}
result={'source_image':str(ROOT/'03_前後留9mm外殼_俯視厚度.png'),
        'source_report':str(ROOT/'前後9mm外殼_模擬檢查.json'),
        'image_size':[1450,1450],'dimension_projection':chains,
        'values_mm':{'center_distance':60,'wheel_face_gap':42,'wheel_thickness_each':18,
            'front_rear_wheel_face_clearance_each':2,'left_right_radial_clearance_each':7,
            'front_rear_skin_thickness_each':9,'bottom_clearance_not_visible_in_top_view':6,
            'hub_to_end_wall_clearance_each':.4,'shaft_end_clearance_each':.2,
            'internal_axial_length':82,'internal_width':90,'wheel_diameter':76}}
assert abs(chains['rear_clearance']['mm']-2)<.001
assert abs(chains['front_clearance']['mm']-2)<.001
(OUT/'投影與尺寸資料.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
