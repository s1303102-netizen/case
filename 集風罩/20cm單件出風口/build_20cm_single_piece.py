"""Smaller single-piece duct; retain the original inlet and local nozzle profile.

Reuse the verified single-piece workflow with explicit, checked dimensional
changes. No bypass, pickups, joining lugs, split parts or original file edits.
"""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
single_source=HERE.parent/'30cm單件出風口/build_single_piece.py'
program=single_source.read_text()
old="prefix=source.read_text().split('# Rearward bypass keeps')[0]"
replacement="""prefix=source.read_text().split('# Rearward bypass keeps')[0]
geometry_changes={
    'L=240.0;halfangle=L/(2*R)':'L=160.0;halfangle=L/(2*R)',
    'neckend=50.;loftend=185.;bendZ=240.':'neckend=20.;loftend=95.;bendZ=150.',
    "new('240mm弧長_原剖面測試罩')":"new('160mm弧長_原剖面出風口')",
}
for original,updated in geometry_changes.items():
    assert prefix.count(original)==1,original
    prefix=prefix.replace(original,updated)
"""
assert program.count(old)==1;program=program.replace(old,replacement)
changes={
    "body.name='單件出風口_240mm弧長_原接口'":"body.name='單件出風口_160mm弧長_原接口'",
    "body['出風弧長_mm']=240.":"body['出風弧長_mm']=160.",
    "(0,15,140)":"(0,10,90)",
    "view_distance=500":"view_distance=350",
    "'30cm單件出風口.blend'":"'20cm單件出風口.blend'",
    "Vector((0,0,38))":"Vector((0,0,10))",
    "Vector((0,0,215))":"Vector((0,0,125))",
    "'slot_span_mm':240":"'slot_span_mm':160",
    "preview([body],.001,(.52,.65,.42),(0,.015,.14),.39,":"preview([body],.001,(.38,.50,.30),(0,.010,.095),.27,",
}
for original,updated in changes.items():
    assert program.count(original)==1,original
    program=program.replace(original,updated)
marker="body.name='單件出風口_160mm弧長_原接口'"
program=program.replace(marker,"""# Preserve the previous compact deliverables as well as the original models.
for p in [HERE.parent/'30cm單件出風口/30cm單件出風口.blend',
          HERE.parent/'30cm單件出風口/單件出風口_直接列印_mm.stl']:
    protected.append(p);hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
"""+marker)
program=program.replace("bodybounds=bounds(body)","bodybounds=bounds(body)\nassert max(bodybounds['size'])<200,bodybounds")
exec(compile(program,str(single_source)+'_20cm_parameters','exec'),globals())
# Report the material change as geometric solid volume, not slicer consumption.
report_path=HERE/'單件出風口_尺寸檢查.json'
report=json.loads(report_path.read_text())
old_report=json.loads((HERE.parent/'30cm單件出風口/單件出風口_尺寸檢查.json').read_text())
oldvolume=old_report['mesh']['signed_material_volume_mm3']
newvolume=report['mesh']['signed_material_volume_mm3']
report['print_envelope_limit_mm']=[200,200,200]
report['inlet_straight_mm']=20
report['loft_height_mm']=75
report['bend_approach_straight_mm']=55
report['material_comparison']={'previous_solid_volume_mm3':oldvolume,
    'new_solid_volume_mm3':newvolume,'solid_volume_reduction_percent':100*(1-newvolume/oldvolume),
    'includes_print_supports_brim_or_infill_settings':False}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('20CM_MODEL_COMPLETE',json.dumps({'size_mm':report['assembled_size_mm'],
    'solid_volume_reduction_percent':report['material_comparison']['solid_volume_reduction_percent']}),flush=True)
