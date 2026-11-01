"""Compare transition geometry only. No CFD or pressure-loss prediction."""
from pathlib import Path
import math,json,csv
HERE=Path(__file__).resolve().parent
SPEC=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
R=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']['fitted_arc_radius_mm']
h=SPEC['pre_nozzle_height_mm'];rv=SPEC['bend']['vertical_center_r_mm'];angle=160/(2*R)
def old_schedule(t):return 10*t**3-15*t**4+6*t**5
def new_schedule(t):
    b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def new_depth(lam):return 88-104*lam+(104-88+h)*lam**2
def center(u,lam):
    a=(2*u-1)*angle
    return ((1-lam)*82*(u-.5)+lam*(R+rv)*math.sin(a),lam*(R+rv)*(1-math.cos(a)))
def span(lam):
    points=[center(i/160,lam) for i in range(161)]
    return sum(math.dist(a,b) for a,b in zip(points,points[1:]))
toparea=span(1)*h
def evaluate(t,version):
    lam=(old_schedule if version=='before' else new_schedule)(t)
    w=span(lam)
    d=(7216+(toparea-7216)*lam)/w if version=='before' else new_depth(lam)
    paths=[]
    for u,v in [(1,-.5),(1,.5),(.5,-.5),(.5,.5)]:
        a=(2*u-1)*angle;cx,cy=center(u,lam)
        dx=(1-lam)*82+lam*(R+rv)*math.cos(a)*2*angle
        dy=lam*(R+rv)*math.sin(a)*2*angle
        magnitude=math.hypot(dx,dy)
        paths.append((cx+v*d*dy/magnitude,cy-v*d*dx/magnitude))
    return {'lam':lam,'width_mm':w,'depth_mm':d,'area_mm2':w*d,'paths':paths}
N=1200
metrics={};tables={}
for version,height,neck,straight in [('before',75,20,55),('after',118,12,20)]:
    points=[evaluate(i/N,version) for i in range(N+1)]
    lateral=[];frontback=[];corner=[]
    dz=height/N
    for a,b in zip(points,points[1:]):
        for j in [0,1]:
            dx=(b['paths'][j][0]-a['paths'][j][0])/dz
            dy=(b['paths'][j][1]-a['paths'][j][1])/dz
            lateral.append(math.degrees(math.atan(abs(dx))))
            corner.append(math.degrees(math.atan(math.hypot(dx,dy))))
        for j in [2,3]:
            dy=(b['paths'][j][1]-a['paths'][j][1])/dz
            frontback.append(math.degrees(math.atan(abs(dy))))
    changes=[b['area_mm2']-a['area_mm2'] for a,b in zip(points,points[1:])]
    assert max(changes)<1e-4,(version,max(changes))
    metrics[version]={'inlet_straight_mm':neck,'loft_height_mm':height,'pre_bend_straight_mm':straight,
                      'max_lateral_edge_projected_angle_deg':max(lateral),
                      'max_center_front_back_projected_angle_deg':max(frontback),
                      'max_edge_path_3D_angle_to_vertical_deg':max(corner),
                      'area_monotonically_nonincreasing':True,
                      'inlet_area_mm2':points[0]['area_mm2'],'final_area_mm2':points[-1]['area_mm2'],
                      'first_and_second_end_derivatives_zero':True}
    tables[version]=[{k:v for k,v in evaluate(i/20,version).items() if k!='paths'}|{'z_mm':neck+height*i/20} for i in range(21)]
assert metrics['after']['max_lateral_edge_projected_angle_deg']<metrics['before']['max_lateral_edge_projected_angle_deg']
assert metrics['after']['max_center_front_back_projected_angle_deg']<metrics['before']['max_center_front_back_projected_angle_deg']
report={'scope':'section geometry and wall-path slopes only; not flow simulation',
        'CFD_executed':False,'pressure_loss_or_velocity_validated':False,
        'width_schedule':'integrated smoothstep slope ramps over first/last 20%; constant slope in between',
        'depth_polynomial_mm':'88 - 104*lambda + (104-88+h)*lambda^2',
        'metrics':metrics,'section_samples':tables}
(HERE/'轉接段_前後幾何比較.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
with (HERE/'轉接段_前後截面.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['版本','高度_mm','展寬參數','弧向寬_mm','厚度_mm','截面積_mm2'])
    for version,rows in tables.items():
        for row in rows:w.writerow([version,row['z_mm'],row['lam'],row['width_mm'],row['depth_mm'],row['area_mm2']])
print(json.dumps(metrics,ensure_ascii=False,indent=2))
