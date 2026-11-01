"""Reopen both files, compare original data, check dimensions, then install."""
from pathlib import Path
import bpy
import json
import math
import hashlib
import os
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '第一版.blend'
STAGED = HERE / '第一版_鼓風機待驗證.blend'
BACKUP = HERE / '第一版_新增鼓風機前備份.blend'
REPORT = HERE / '鼓風機_尺寸與原物件檢查.json'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attribute_values(attribute):
    values=[]
    for item in attribute.data:
        fields={}
        for field in ('value','vector','color','uv'):
            if hasattr(item,field):
                value=getattr(item,field)
                fields[field]=value if isinstance(value,(str,bool,int,float)) else list(value)
        values.append(fields)
    return {'type':attribute.data_type,'domain':attribute.domain,'values':values}


def snapshot(obj):
    result={'type':obj.type,'data':obj.data.name if obj.data else None,
            'matrix':[list(row) for row in obj.matrix_world],
            'location':list(obj.location),'rotation':list(obj.rotation_euler),
            'scale':list(obj.scale),'rotation_mode':obj.rotation_mode,
            'parent':obj.parent.name if obj.parent else None,
            'collections':sorted(c.name for c in obj.users_collection),
            'hide_render':obj.hide_render,'hide_viewport':obj.hide_viewport,
            'modifiers':[(m.name,m.type) for m in obj.modifiers],
            'custom_properties':{k:repr(obj[k]) for k in obj.keys()}}
    if obj.type=='MESH':
        result['mesh']={'vertices':[list(v.co) for v in obj.data.vertices],
                        'edges':[list(e.vertices) for e in obj.data.edges],
                        'faces':[list(p.vertices) for p in obj.data.polygons],
                        'smooth':[p.use_smooth for p in obj.data.polygons],
                        'material_index':[p.material_index for p in obj.data.polygons],
                        'materials':[m.name if m else None for m in obj.data.materials],
                        'attributes':{a.name:attribute_values(a) for a in obj.data.attributes
                                      if not a.name.startswith('.uv_select')},
                        'uv':{layer.name:[list(v.uv) for v in layer.data] for layer in obj.data.uv_layers}}
    elif obj.type=='CAMERA':
        result['camera']=[obj.data.type,obj.data.lens,obj.data.clip_start,obj.data.clip_end,
                          obj.data.sensor_width,obj.data.sensor_height,obj.data.shift_x,obj.data.shift_y]
    elif obj.type=='LIGHT':
        result['light']=[obj.data.type,obj.data.energy,list(obj.data.color),obj.data.shadow_soft_size]
    return result


def units(scene):
    return [scene.unit_settings.system,scene.unit_settings.scale_length,scene.unit_settings.length_unit]


def bounds_mm(obj,root,depsgraph):
    evaluated=obj.evaluated_get(depsgraph)
    transform=root.matrix_world.inverted()@evaluated.matrix_world
    # Curve bound_box is padded conservatively in Blender; measure evaluated
    # surface vertices instead, so wires do not add fictitious envelope length.
    data=evaluated.to_mesh()
    pts=[transform@v.co for v in data.vertices]
    evaluated.to_mesh_clear()
    low=[min(p[i] for p in pts) for i in range(3)]
    high=[max(p[i] for p in pts) for i in range(3)]
    return {'min':low,'max':high,'size':[high[i]-low[i] for i in range(3)]}


assert file_hash(SOURCE)==file_hash(BACKUP), 'Original file changed during modeling; refusing to overwrite.'
bpy.ops.wm.open_mainfile(filepath=str(BACKUP))
baseline={o.name:snapshot(o) for o in bpy.data.objects}
baseline_units=units(bpy.context.scene)
baseline_scene_names=sorted(s.name for s in bpy.data.scenes)
bpy.ops.wm.open_mainfile(filepath=str(STAGED))
for name,original in baseline.items():
    assert name in bpy.data.objects, 'Original object missing: '+name
    assert snapshot(bpy.data.objects[name])==original, 'Original object changed: '+name
assert units(bpy.context.scene)==baseline_units, 'Scene units changed.'
assert sorted(s.name for s in bpy.data.scenes)==baseline_scene_names, 'Temporary scene was saved accidentally.'
collection=bpy.data.collections['鼓風機_150FLJ330W']
root=bpy.data.objects['鼓風機_總成_公分場景比例']
assert all(o.parent==root for o in collection.objects if o!=root)
assert len(bpy.data.objects)==len(baseline)+len(collection.objects)
bpy.context.view_layer.update()
depsgraph=bpy.context.evaluated_depsgraph_get()
parts={o.name:bounds_mm(o,root,depsgraph) for o in collection.objects
       if o.type in {'MESH','CURVE','FONT'}}
low=[min(b['min'][i] for b in parts.values()) for i in range(3)]
high=[max(b['max'][i] for b in parts.values()) for i in range(3)]
actual=[high[i]-low[i] for i in range(3)]
expected=[206,242,220]
for value,target in zip(actual,expected):
    assert abs(value-target)<0.025, f'Envelope mismatch: {actual} expected {expected}'
assert abs(low[2])<0.025, 'Blower does not rest at Z=0.'
flange=parts['鼓風機_出風口_120x118法蘭']
assert abs(flange['size'][1]-120)<0.025 and abs(flange['size'][2]-118)<0.025
front=bpy.data.objects['鼓風機_蝸殼_進風側板']
intake=[v for v in front.data.vertices if abs(math.hypot(v.co.x,v.co.z-93)-60)<0.005]
assert len(intake)>=150, '120 mm intake circle missing.'
foot=parts['鼓風機_底座_80mm長安裝腳']
assert abs(foot['size'][1]-80)<0.025
original_right=max((bpy.data.objects['Cube'].matrix_world@Vector(c)).x
                   for c in bpy.data.objects['Cube'].bound_box)
gap=root.location.x+low[0]*root.scale.x-original_right
assert gap>0, 'New blower overlaps original model.'
report=json.loads(REPORT.read_text(encoding='utf-8'))
report['已驗證儲存後原物件']=True
report['儲存後完整比對']={'通過':True,'原物件':list(baseline),
                       '檢查項目':'物件變換、父子關係、集合、網格頂點/邊/面、UV、屬性、材質、相機、燈光、場景單位',
                       '主體網格頂點數':len(bpy.data.objects['Cube'].data.vertices),
                       '主體網格面數':len(bpy.data.objects['Cube'].data.polygons)}
report['鼓風機']['實際零件包絡_mm']={'min':low,'max':high,'size':actual}
report['鼓風機']['原物體右側間隙_cm']=gap
report['實測檢查']={'總包絡_mm':actual,'法蘭外框_mm':flange['size'][1:],
                  '進風孔直徑_mm':120,'進風孔圓弧頂點數':len(intake),
                  '底座軸向長_mm':foot['size'][1],'尺寸誤差允許_mm':0.025}
assert file_hash(SOURCE)==file_hash(BACKUP), 'Source file changed before installation.'
verified_hash=file_hash(STAGED)
os.replace(STAGED,SOURCE)
assert file_hash(SOURCE)==verified_hash
report['完成檔案']=str(SOURCE)
report['完成檔案_sha256']=verified_hash
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
old_stage=Path(str(STAGED)+'1')
if old_stage.exists():
    old_stage.unlink()
print('BLOWER_VERIFIED_AND_INSTALLED',json.dumps({'objects_preserved':list(baseline),
      'blower_objects':len(collection.objects),'envelope_mm':actual,'gap_cm':gap,
      'file':str(SOURCE)},ensure_ascii=False))
