"""Build the smoother 20 cm single-piece revision without modifying old files."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
single_source=HERE.parent/'30cm單件出風口/build_single_piece.py'
program=single_source.read_text()
old="prefix=source.read_text().split('# Rearward bypass keeps')[0]"
replacement="""prefix=source.read_text().split('# Rearward bypass keeps')[0]
new_schedule='''def S(t):
    b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def transition_depth(lam):return 88-104*lam+(104-88+h)*lam**2'''
geometry_changes={
    'L=240.0;halfangle=L/(2*R)':'L=160.0;halfangle=L/(2*R)',
    'neckend=50.;loftend=185.;bendZ=240.':'neckend=12.;loftend=130.;bendZ=150.',
    'def S(t):return 10*t**3-15*t**4+6*t**5':new_schedule,
    'lam=S(t);p=center(u,lam);d=(7216+(toparea-7216)*lam)/span_cache[k]':
        'lam=S(t);p=center(u,lam);d=transition_depth(lam)',
    'z=loftend+55*t':'z=loftend+(bendZ-loftend)*t',
    "('loft',54)":"('loft',80)",
    "new('240mm弧長_原剖面測試罩')":"new('160mm弧長_平順改善版')",
    "mesh('測試集風罩_240mm弧長_本體'":"mesh('平順改善版_160mm出風口'",
}
for original,updated in geometry_changes.items():
    assert prefix.count(original)==1,original
    prefix=prefix.replace(original,updated)
"""
assert program.count(old)==1;program=program.replace(old,replacement)
changes={
    "body.name='單件出風口_240mm弧長_原接口'":"body.name='單件出風口_平順改善版_160mm弧長'",
    "body['出風弧長_mm']=240.":"body['出風弧長_mm']=160.",
    "(0,15,140)":"(0,10,90)",
    "view_distance=500":"view_distance=350",
    "'30cm單件出風口.blend'":"'20cm單件出風口_平順改善版.blend'",
    "Vector((0,0,38))":"Vector((0,0,10))",
    "Vector((0,0,215))":"Vector((0,0,140))",
    "'slot_span_mm':240":"'slot_span_mm':160",
    "'單件出風口_直接列印_mm'":"'平順改善版_單件出風口_直接列印_mm'",
    "'單件出風口_尺寸檢查.json'":"'平順改善版_尺寸檢查.json'",
    "'單件出風口_預覽.png'":"'平順改善版_預覽.png'",
    "preview([body],.001,(.52,.65,.42),(0,.015,.14),.39,":
        "preview([body],.001,(.38,.50,.30),(0,.010,.095),.27,",
}
for original,updated in changes.items():
    assert program.count(original)==1,original
    program=program.replace(original,updated)
marker="body.name='單件出風口_平順改善版_160mm弧長'"
program=program.replace(marker,"""# Preserve both previous compact versions.
for subdir,filename in [('20cm單件出風口','20cm單件出風口.blend'),
                        ('30cm單件出風口','30cm單件出風口.blend')]:
    for name in [filename,'單件出風口_直接列印_mm.stl']:
        p=HERE.parent/subdir/name
        protected.append(p);hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
"""+marker+"\nbody.data.name='平順改善版_160mm_Mesh'")
program=program.replace("bodybounds=bounds(body)","bodybounds=bounds(body)\nassert max(bodybounds['size'])<200,bodybounds")
exec(compile(program,str(single_source)+'_improved_20cm_parameters','exec'),globals())
report_path=HERE/'平順改善版_尺寸檢查.json'
report=json.loads(report_path.read_text())
baseline=json.loads((HERE.parent/'20cm單件出風口/單件出風口_尺寸檢查.json').read_text())
metrics=json.loads((HERE/'轉接段_前後幾何比較.json').read_text())
assert max(report['assembled_size_mm'])<200
assert metrics['metrics']['after']['area_monotonically_nonincreasing']
report['print_envelope_limit_mm']=[200,200,200]
report['inlet_straight_mm']=12
report['loft_height_mm']=118
report['bend_approach_straight_mm']=20
report['comparison_with_previous_20cm']={
    'geometry':metrics['metrics'],
    'old_solid_volume_mm3':baseline['mesh']['signed_material_volume_mm3'],
    'new_solid_volume_mm3':report['mesh']['signed_material_volume_mm3'],
    'solid_volume_change_percent':100*(report['mesh']['signed_material_volume_mm3']/baseline['mesh']['signed_material_volume_mm3']-1),
    'material_figures_exclude_supports_and_slicer_settings':True,
}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('IMPROVED_SINGLE_COMPLETE',json.dumps({'size_mm':report['assembled_size_mm'],
    'volume_change_pct':report['comparison_with_previous_20cm']['solid_volume_change_percent']}),flush=True)
