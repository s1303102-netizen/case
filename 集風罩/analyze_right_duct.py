"""Read-only geometry analysis and a 1-D loss/manifold sizing model.

This does not run CFD and does not infer a fan curve from catalog endpoints.
All fan-static-pressure cases are conditional operating-pressure scenarios.
"""
from pathlib import Path
from collections import Counter, defaultdict
import json
import math
import hashlib

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
DATA = json.loads((ROOT/'鼓風機/集風罩_現況幾何.json').read_text())
rho, mu = 1.2, 1.8185e-5
Cd = 0.94  # Assumed preliminary smooth slot discharge coefficient, not measured.
gap = 0.002
Ain = 0.082*0.088
Abend = 0.100*0.070
Acore = 0.050*0.070
Dhcore = 2*0.050*0.070/(0.050+0.070)
Kfeed = 0.90  # All inlet, riser, bend, distribution losses normalized to Ain.

verts, faces = DATA['shell']['verts'], DATA['shell']['faces']
counts = Counter(tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in faces for i in range(len(face)))
edge_ids = set(i for edge,n in counts.items() if n==1 for i in edge)
upper = sorted([p for i,p in enumerate(verts) if i in edge_ids
                and abs(p[2]-70.9866)<0.005 and -55.001<=p[0]<=0.001 and p[1]<10])
lower = [p for i,p in enumerate(verts) if i in edge_ids
         and abs(p[2]-68.9866)<0.005 and abs(p[0])<=55.001 and p[1]<10]
zmid_cm = (sum(p[2] for p in upper)/len(upper)+sum(p[2] for p in lower)/len(lower))/2
fit = [p for p in upper if abs(p[0])<54.99]
ys=[p[1] for p in fit]; ds=[p[0]**2+p[1]**2 for p in fit]
ym=sum(ys)/len(ys); dm=sum(ds)/len(ds)
cy=sum((y-ym)*(d-dm) for y,d in zip(ys,ds))/sum((y-ym)**2 for y in ys)/2
R=math.sqrt(dm-2*cy*ym+cy*cy)
poly=[p[:2] for p in upper if p[0]<-2.5]
a,b=upper[-2:];t=(-2.5-a[0])/(b[0]-a[0])
poly.append([-2.5,a[1]+t*(b[1]-a[1])])
length_cm=sum(math.dist(p,q) for p,q in zip(poly,poly[1:]))
L=length_cm/100
theta0=math.asin(2.5/R);theta1=math.asin(55/R);thetafeed=math.radians(30)
# Use the actual near-30-degree opening vertex for the feed station.
feed_vertex=min(upper,key=lambda p:abs(p[0]+R*math.sin(thetafeed)))
thetafeed=math.atan2(-feed_vertex[0],cy-feed_vertex[1])
feed_arc=[feed_vertex[0]*10,feed_vertex[1]*10,zmid_cm*10]
branch_lengths=[R*(thetafeed-theta0)/100,R*(theta1-thetafeed)/100]
branch_lengths=[x*L/sum(branch_lengths) for x in branch_lengths]

# Blower port coordinates from the original dimensioned geometry and latest matrix.
matrix=DATA['blower']['matrix']
def transform(p):
    return [sum(matrix[i][j]*p[j] for j in range(3))+matrix[i][3] for i in range(3)]
old_port=transform((113,-1.5,159))
new_port=[feed_arc[0]/10,-10,old_port[2]]
angle=-thetafeed
c,s=math.cos(angle),math.sin(angle)
def moved(p):
    x,y,z=[p[i]-old_port[i] for i in range(3)]
    return [new_port[0]+c*x-s*y,new_port[1]+s*x+c*y,new_port[2]+z]
new_vertices=[moved(p) for p in DATA['blower']['verts']]
new_low=[min(p[i] for p in new_vertices) for i in range(3)]
new_high=[max(p[i] for p in new_vertices) for i in range(3)]
new_origin=moved([matrix[i][3] for i in range(3)])


def friction(v,D):
    Re=rho*abs(v)*D/mu
    if Re<1e-8:return 0
    if Re<2300:return 64/Re
    # Haaland approximation, assumed smoothed/sealed 0.05-mm internal roughness.
    return (-1.8*math.log10((0.00005/D/3.7)**1.11+6.9/Re))**-2


def manifold_branch(Pt,length,cd,g):
    n=80;ds=length/n
    q=[cd*g*ds*math.sqrt(2*Pt/rho)]*n
    for _ in range(160):
        remaining=sum(q); loss=0;next_q=[];press=[]
        for flow in q:
            axial=(remaining-flow/2)/Acore
            dynamic=rho*axial*axial/2
            f=friction(axial,Dhcore)
            Ps=max(1e-8,Pt-loss-dynamic-f*(ds/2)/Dhcore*dynamic)
            next_q.append(cd*g*ds*math.sqrt(2*Ps/rho))
            press.append(Ps)
            loss+=f*ds/Dhcore*dynamic
            remaining-=flow
        error=max(abs(x-y) for x,y in zip(q,next_q))
        q=[0.6*x+0.4*y for x,y in zip(q,next_q)]
        if error<1e-12:break
    velocities=[flow/(g*ds) for flow in q]
    return {'Q':sum(q),'velocities':velocities,'pressure':press,'friction_loss':loss}


def operating_case(Ps_fan,cd=Cd,kfeed=Kfeed,g=gap):
    # AMCA fan total pressure = fan static + outlet velocity pressure.
    # Assume free ambient intake, with inlet installation losses included in Kfeed.
    Pt_manifold=Ps_fan
    for _ in range(80):
        branches=[manifold_branch(Pt_manifold,l,cd,g) for l in branch_lengths]
        Q=sum(b['Q'] for b in branches)
        qin=rho*(Q/Ain)**2/2
        target=max(1,Ps_fan+qin-kfeed*qin)
        if abs(target-Pt_manifold)<1e-7:break
        Pt_manifold=0.5*(Pt_manifold+target)
    velocities=[v for b in branches for v in b['velocities']]
    mean=Q/(L*g)
    return {'fan_static_Pa':Ps_fan,'flow_m3_s':Q,'flow_m3_min':Q*60,
            'flow_m3_h':Q*3600,'mean_velocity_m_s':mean,
            'min_velocity_m_s':min(velocities),'max_velocity_m_s':max(velocities),
            'velocity_spread_pct':100*(max(velocities)-min(velocities))/mean,
            'feed_velocity_m_s':Q/Ain,'feed_loss_Pa':kfeed*qin,
            'fan_total_Pa':Ps_fan+qin,'manifold_total_Pa':Pt_manifold,
            'branch_flows_m3_min':[b['Q']*60 for b in branches],
            'branch_friction_loss_Pa':[b['friction_loss'] for b in branches]}


def required_case(target_velocity,g=gap):
    lo,hi=1,3000
    for _ in range(35):
        p=(lo+hi)/2
        if operating_case(p,g=g)['mean_velocity_m_s']<target_velocity:lo=p
        else:hi=p
    return operating_case((lo+hi)/2,g=g)


cases=[operating_case(p) for p in [250,300,350,400,420,450,460]]
requirements=[required_case(v) for v in [15,20,25,30,40]]
gap_cases=[operating_case(460,g=g/1000) for g in [1,1.5,2,3,4]]
sensitivity=[operating_case(460,cd=cd,kfeed=k) for cd in [.88,.94,.96] for k in [.5,.9,1.8]]

# Conservative clearance of the entire feed bend and 2-mm wall in plan.
n=[math.sin(thetafeed),math.cos(thetafeed)]  # horizontal jet direction
tangent=[-math.cos(thetafeed),math.sin(thetafeed)]
def localpoint(r,u):
    return [feed_arc[i]-n[i]*r+tangent[i]*u for i in range(2)]
bend_corners=[localpoint(r,u) for r in [85,185] for u in [-52,52]]
bend_min=[min(p[i] for p in bend_corners) for i in range(2)]
plenum_back_min_y=min(cy*10-(R*10+87)*math.cos(theta0+i*(theta1-theta0)/200) for i in range(201))
assert new_low[0]>-70 and new_high[0]<70
assert new_low[1]>-25 and new_high[1]<25
assert bend_min[1]>-250 and plenum_back_min_y>-250
assert abs(zmid_cm-69.9866)<0.01
assert abs(length_cm-59.28)<0.02
assert 0.024 < cases[-1]['flow_m3_s'] <0.034

output={'source_file':str(ROOT/'第一版.blend'),
        'source_sha256':hashlib.sha256((ROOT/'第一版.blend').read_bytes()).hexdigest(),
        'units':'geometry mm; original Blender coordinates interpreted as cm',
        'measured':{'shell_envelope_mm':[1400,500,1250],'right_X_range_mm':[-550,-25],
                    'right_projected_width_mm':525,'center_excluded_width_mm':50,
                    'right_arc_length_mm':length_cm*10,'opening_height_mm':20,
                    'opening_center_Z_mm':zmid_cm*10,'fitted_arc_radius_mm':R*10,
                    'fitted_arc_center_Y_mm':cy*10,'actual_arc_polyline_cm':poly,
                    'arc_theta_degrees':[math.degrees(theta0),math.degrees(theta1)]},
        'fan_catalog_photo':{'power_W':330,'rpm':2800,'airflow_m3_min':11,'static_Pa':460,
                             'current_A':1.6,'capacitor_uF':[5,6],
                             'curve_available':False,'frequency_available':False,
                             'same_working_point_confirmed':False},
        'design':{'slot_gap_mm':2,'adjustment_range_mm':[1.5,3],
                  'slot_area_mm2':L*1000*2,'fan_port_mm':[82,88],
                  'fan_flange_mm':[118,120],'neck_height_mm':50,
                  'riser_transition_mm':[82,88,100,70],
                  'plenum_core_mm':[50,70],'contraction_depth_mm':35,
                  'contraction_includes_final_straight_lip_mm':4,
                  'plenum_total_depth_mm':85,'wall_mm':2,
                  'bend_center_radius_mm':65,'bend_inner_radius_mm':30,
                  'bend_outer_radius_mm':100,'vane_radius_mm':math.sqrt(30*100),
                  'vane_thickness_mm':1,'upper_straight_length_mm':130,
                  'plenum_feed_point_mm':feed_arc,
                  'feed_theta_degrees':math.degrees(thetafeed),
                  'branch_lengths_mm':[l*1000 for l in branch_lengths],
                  'jet_direction':'horizontal, normal to local arc, toward +Y and +X on this half'},
        'blower_position':{'old_port_center_cm':old_port,'proposed_port_center_cm':new_port,
                           'port_shift_cm':[new_port[i]-old_port[i] for i in range(3)],
                           'Z_rotation_about_port_degrees':-math.degrees(thetafeed),
                           'proposed_object_origin_cm':new_origin,
                           'proposed_rotation_degrees':[0,-90,-math.degrees(thetafeed)],
                           'proposed_bounds_cm':{'min':new_low,'max':new_high},
                           'floor_clearance_mm':new_low[2]*10,
                           'current_side_envelope_clearance_mm':(-69.57562255859375+70)*10},
        'clearance':{'plenum_back_wall_clearance_mm':250+plenum_back_min_y,
                     'bend_back_wall_clearance_mm':250+bend_min[1]},
        'model':{'kind':'1-D Darcy/manifold pressure and discharge network; not CFD',
                 'rho_kg_m3':rho,'mu_Pa_s':mu,'nozzle_Cd_assumed':Cd,
                 'Kfeed_assumed_normalized_to_fan_port':Kfeed,
                 'core_area_mm2':Acore*1e6,'core_Dh_mm':Dhcore*1000,
                 'roughness_mm':0.05,'fan_curve_assumed':False,
                 'limitations':['Kfeed and Cd are assumed, not validated for this CAD geometry.',
                                '1-D distribution excludes inlet jet and bend-induced secondary vortices.',
                                'Flow rate and static pressure at the real operating point remain unknown.',
                                'Slots are pressure-limited; reducing gap does not double air speed.',
                                'Dimensions are preliminary clear flow dimensions, not a fabrication drawing.']},
        'conditional_cases':cases,'required_cases':requirements,'gap_cases_at_460Pa':gap_cases,
        'sensitivity_at_460Pa':{'velocity_range_m_s':[min(c['mean_velocity_m_s'] for c in sensitivity),
                                                    max(c['mean_velocity_m_s'] for c in sensitivity)]}}
(OUT/'右半邊集風罩_計算.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'measured':output['measured'],'position':output['blower_position'],
                  'clearance':output['clearance'],'at460':cases[-1],
                  'target25':requirements[2],'sensitivity':output['sensitivity_at_460Pa']},ensure_ascii=False,indent=2))
