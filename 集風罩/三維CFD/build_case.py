"""Create a genuinely 3-D body-fitted hexahedral mesh of the second concept.

Coordinates in metres. inlet: specified volumetric flow, outlet: ambient static
pressure. No impeller model or guessed fan curve. Does not modify any .blend.
"""
from pathlib import Path
from array import array
import math
import json
import hashlib
import struct
import argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
SOURCE=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
GEOM=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--grid',choices=['coarse','medium'],default='coarse')
parser.add_argument('--flow',type=float,default=1.778353495686213,help='m3/min')
args=parser.parse_args()
case=HERE/args.grid
for folder in ['constant/polyMesh','system','0']:(case/folder).mkdir(parents=True,exist_ok=True)
cfg={'coarse':(64,16,[8,72,12,24,32,6]),'medium':(96,24,[12,112,18,36,48,8])}
Nu,Nd,segments=cfg[args.grid]
Q=args.flow/60
R=GEOM['measured']['fitted_arc_radius_mm'];CY=GEOM['measured']['fitted_arc_center_Y_mm']
t0,t1=[math.radians(t) for t in GEOM['measured']['arc_theta_degrees']]
tf=(t0+t1)/2
port=[x*10 for x in SOURCE['blower']['proposed_port_center_cm']]
h=SOURCE['pre_nozzle_height_mm'];rvertical=SOURCE['bend']['vertical_center_r_mm']
rbend=SOURCE['bend']['mean_radius_mm'];Z=GEOM['measured']['opening_center_Z_mm'];bendZ=Z-rbend
neckend=port[2]+50;upperstart=bendZ-55
Lc=SOURCE['nozzle']['converging_length_mm'];Lnoz=SOURCE['nozzle']['total_length_mm']
lip=SOURCE['nozzle']['straight_lip_mm'];blend=6.;tanangle=math.tan(math.radians(7))
def S(t):return 10*t**3-15*t**4+6*t**5
def integral(x):
    if x<=0:return 0
    if x>=Lc:return Lc-blend
    if x<blend:
        t=x/blend;return blend*(t**3-.5*t**4)
    if x<=Lc-blend:return x-blend/2
    t=(x-Lc+blend)/blend;return Lc-1.5*blend+blend*(t-t**3+.5*t**4)
def hh(r):return 1 if r<=lip else h/2-tanangle*integral(Lnoz-r)
def arc(u,r):
    th=t0+(t1-t0)*u
    return (-(R+r)*math.sin(th),CY-(R+r)*math.cos(th))
def loft_center(u,lam):
    p0=(port[0]-82*(u-.5)*math.cos(tf),port[1]+82*(u-.5)*math.sin(tf))
    top=arc(u,rvertical)
    return tuple((1-lam)*a+lam*b for a,b in zip(p0,top))
def span(lam):
    pts=[loft_center(i/400,lam) for i in range(401)]
    return sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
toparea=span(1)*h
stations=[('neck',0.0)]
for name,count in zip(['neck','loft','straight','bend','nozzle','lip'],segments):
    stations.extend((name,j/count) for j in range(1,count+1))
Nt=len(stations)-1
radial=[-.5*math.cos(math.pi*j/Nd) for j in range(Nd+1)]
span_params=[i/Nu for i in range(Nu+1)]
def xyz(i,j,k):
    u=span_params[i];v=radial[j];name,t=stations[k]
    if name=='neck':
        p=loft_center(u,0);d=88
        out=(-math.sin(tf),-math.cos(tf));z=port[2]+50*t
    elif name=='loft':
        lam=S(t);p=loft_center(u,lam);d=(7216+(toparea-7216)*lam)/span_cache[k]
        du=1e-5;a=loft_center(u-du,lam);b=loft_center(u+du,lam)
        tx,ty=b[0]-a[0],b[1]-a[1];mag=math.hypot(tx,ty)
        out=(-ty/mag,tx/mag);z=neckend+(upperstart-neckend)*t
    elif name=='straight':
        p=arc(u,rvertical);d=h;th=t0+(t1-t0)*u
        out=(-math.sin(th),-math.cos(th));z=upperstart+55*t
    elif name=='bend':
        a=math.pi/2*t;r=Lnoz+(rbend+v*h)*math.cos(a)
        z=bendZ+(rbend+v*h)*math.sin(a);p=arc(u,r)
        return (p[0]/1000,p[1]/1000,z/1000)
    else:
        r=Lnoz-Lc*t if name=='nozzle' else lip*(1-t)
        p=arc(u,r);z=Z+v*2*hh(r)
        return (p[0]/1000,p[1]/1000,z/1000)
    return ((p[0]+out[0]*v*d)/1000,(p[1]+out[1]*v*d)/1000,z/1000)
span_cache={k:span(S(t)) for k,(name,t) in enumerate(stations) if name=='loft'}
def pid(i,j,k):return i+(Nu+1)*(j+(Nd+1)*k)
def cid(i,j,k):return i+Nu*(j+Nd*k)
points=[xyz(i,j,k) for k in range(Nt+1) for j in range(Nd+1) for i in range(Nu+1)]

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def quad_area(face):
    a,b,c,d=[points[x] for x in face]
    x=cross(sub(b,a),sub(c,a));y=cross(sub(c,a),sub(d,a))
    return tuple((p+q)/2 for p,q in zip(x,y))
def face_center(face):return tuple(sum(points[q][i] for q in face)/4 for i in range(3))
faces=[];owners=[];neighbours=[];patches={'inlet':[],'outlet':[],'walls':[]}
def face(verts,owner,neigh=None,patch=None):
    if patch:patches[patch].append((verts,owner))
    else:faces.append(verts);owners.append(owner);neighbours.append(neigh)
# Face orientation follows positive u, depth or flow coordinate.
for k in range(Nt):
    for j in range(Nd):
        for i in range(Nu+1):
            f=(pid(i,j,k),pid(i,j+1,k),pid(i,j+1,k+1),pid(i,j,k+1))
            if i==0:face(tuple(reversed(f)),cid(0,j,k),patch='walls')
            elif i==Nu:face(f,cid(Nu-1,j,k),patch='walls')
            else:face(f,cid(i-1,j,k),cid(i,j,k))
for k in range(Nt):
    for j in range(Nd+1):
        for i in range(Nu):
            f=(pid(i,j,k),pid(i,j,k+1),pid(i+1,j,k+1),pid(i+1,j,k))
            if j==0:face(tuple(reversed(f)),cid(i,0,k),patch='walls')
            elif j==Nd:face(f,cid(i,Nd-1,k),patch='walls')
            else:face(f,cid(i,j-1,k),cid(i,j,k))
for k in range(Nt+1):
    for j in range(Nd):
        for i in range(Nu):
            f=(pid(i,j,k),pid(i+1,j,k),pid(i+1,j+1,k),pid(i,j+1,k))
            if k==0:face(tuple(reversed(f)),cid(i,j,0),patch='inlet')
            elif k==Nt:face(f,cid(i,j,Nt-1),patch='outlet')
            else:face(f,cid(i,j,k-1),cid(i,j,k))
internal=len(faces)
# Standard upper-triangular face ordering for OpenFOAM's LDU addressing.
order=sorted(range(internal),key=lambda q:(owners[q],neighbours[q]))
faces=[faces[q] for q in order]
owners=[owners[q] for q in order]
neighbours=[neighbours[q] for q in order]
patchmeta={}
for name,items in patches.items():
    patchmeta[name]={'startFace':len(faces),'nFaces':len(items)}
    for f,o in items:faces.append(f);owners.append(o)

header=lambda cls,obj: f'FoamFile\n{{\n version 2.0;\n format ascii;\n class {cls};\n object {obj};\n}}\n'
def write_list(name,cls,values,formatter):
    path=case/'constant/polyMesh'/name
    with path.open('w') as out:
        out.write(header(cls,name)+str(len(values))+'\n(\n')
        for x in values:out.write(formatter(x)+'\n')
        out.write(')\n')
write_list('points','vectorField',points,lambda p:'('+ ' '.join(f'{x:.11g}' for x in p)+')')
write_list('faces','faceList',faces,lambda p:'4('+ ' '.join(map(str,p))+')')
write_list('owner','labelList',owners,str)
write_list('neighbour','labelList',neighbours,str)
b=header('polyBoundaryMesh','boundary')+'3\n(\n'
for name,meta in patchmeta.items():
    b+=f'{name}\n{{ type {"wall" if name=="walls" else "patch"}; nFaces {meta["nFaces"]}; startFace {meta["startFace"]}; }}\n'
(case/'constant/polyMesh/boundary').write_text(b+')\n')
for name in ['cellZones','faceZones','pointZones']:(case/'constant/polyMesh'/name).write_text(header('regIOobject',name)+'0\n()\n')
array('d',[x for p in points for x in p]).tofile((case/'points.bin').open('wb'))
array('i',[x for f in faces for x in f]).tofile((case/'faces.bin').open('wb'))
array('i',owners).tofile((case/'owner.bin').open('wb'))
array('i',neighbours).tofile((case/'neighbour.bin').open('wb'))

# Piola-style flux-consistent initial direction, not an imposed result.
initial_U=[]
min_jac=1e9;max_speed=0;centers=[]
for k in range(Nt):
    for j in range(Nd):
        for i in range(Nu):
            low=(pid(i,j,k),pid(i+1,j,k),pid(i+1,j+1,k),pid(i,j+1,k))
            up=tuple(x+(Nu+1)*(Nd+1) for x in low)
            dt=sub(face_center(up),face_center(low));mag=math.sqrt(dot(dt,dt))
            direction=tuple(x/mag for x in dt)
            av=tuple((x+y)/2 for x,y in zip(quad_area(low),quad_area(up)))
            ap=dot(av,direction);min_jac=min(min_jac,ap*mag)
            assert ap>0, f'Folded mapping at cell {i,j,k}'
            flow=Q/Nu*(radial[j+1]-radial[j])
            U=tuple(flow/ap*x for x in direction);initial_U.append(U)
            max_speed=max(max_speed,flow/ap)
            centers.append(tuple((x+y)/2 for x,y in zip(face_center(up),face_center(low))))
array('d',[x for p in centers for x in p]).tofile((case/'centers.bin').open('wb'))
def field(name,cls,dimensions,internal,boundary):
    (case/'0'/name).write_text(header(cls,name)+f'dimensions {dimensions};\ninternalField {internal};\nboundaryField\n{{\n{boundary}\n}}\n')
uvalues='nonuniform List<vector>\n'+str(len(initial_U))+'\n(\n'+'\n'.join('('+ ' '.join(f'{x:.9g}' for x in u)+')' for u in initial_U)+'\n)'
field('U','volVectorField','[0 1 -1 0 0 0 0]',uvalues,
      f'inlet {{ type flowRateInletVelocity; volumetricFlowRate constant {Q:.12g}; value uniform (0 0 {Q/(7216e-6):.8g}); }}\n'
      'outlet { type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0); }\n'
      'walls { type fixedValue; value uniform (0 0 0); }')
field('p','volScalarField','[0 2 -2 0 0 0 0]','uniform 0',
      'inlet {type zeroGradient;}\noutlet {type fixedValue; value uniform 0;}\nwalls {type zeroGradient;}')
uin=Q/(7216e-6);kin=1.5*(.05*uin)**2;omega=math.sqrt(kin)/(.09**.25*.006)
field('k','volScalarField','[0 2 -2 0 0 0 0]',f'uniform {kin:.9g}',
      f'inlet {{type fixedValue; value uniform {kin:.9g};}}\noutlet {{type inletOutlet; inletValue uniform {kin:.9g}; value uniform {kin:.9g};}}\n'
      'walls {type kLowReWallFunction; value uniform 1e-10;}')
field('omega','volScalarField','[0 0 -1 0 0 0 0]',f'uniform {omega:.9g}',
      f'inlet {{type fixedValue; value uniform {omega:.9g};}}\noutlet {{type inletOutlet; inletValue uniform {omega:.9g}; value uniform {omega:.9g};}}\n'
      f'walls {{type omegaWallFunction; blending binomial; value uniform {omega:.9g};}}')
field('nut','volScalarField','[0 2 -1 0 0 0 0]','uniform 0',
      'inlet {type calculated; value uniform 0;}\noutlet {type calculated; value uniform 0;}\nwalls {type nutUSpaldingWallFunction; maxIter 100; tolerance 1e-5; value uniform 0;}')
(case/'constant/transportProperties').write_text(header('dictionary','transportProperties')+'transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] 1.5154166667e-5;\n')
(case/'constant/turbulenceProperties').write_text(header('dictionary','turbulenceProperties')+'simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n')
(case/'system/fvSchemes').write_text(header('dictionary','fvSchemes')+'''
ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
 default none;
 div(phi,U) bounded Gauss linearUpwind grad(U);
 div(phi,k) bounded Gauss upwind;
 div(phi,omega) bounded Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
''')
(case/'system/fvSolution').write_text(header('dictionary','fvSolution')+'''
solvers
{
 p { solver GAMG; tolerance 1e-8; relTol 0.05; smoother DICGaussSeidel; cacheAgglomeration true; nCellsInCoarsestLevel 30; agglomerator faceAreaPair; mergeLevels 1; }
 U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-7; relTol 0.05; }
 "(k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-7; relTol 0.05; }
}
SIMPLE
{
 nNonOrthogonalCorrectors 2;
 residualControl { p 1e-5; U 1e-5; "(k|omega)" 1e-5; }
}
relaxationFactors
{
 fields { p 0.3; }
 equations { U 0.5; k 0.5; omega 0.5; }
}
''')
control=header('dictionary','controlDict')+'''
application simpleFoam;
startFrom latestTime;
startTime 0;
stopAt endTime;
endTime 2000;
deltaT 1;
writeControl timeStep;
writeInterval 200;
purgeWrite 3;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable true;
functions
{
'''
for name,patch,op,fields in [('inletFlow','inlet','sum','phi'),('outletFlow','outlet','sum','phi'),
                             ('inletStaticPressure','inlet','areaAverage','p'),('outletStaticPressure','outlet','areaAverage','p')]:
    control+=f'{name}\n{{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); regionType patch; name {patch}; operation {op}; fields ({fields}); log false; writeControl timeStep; writeInterval 20;}}\n'
control+='yPlus {type yPlus;libs ("libfieldFunctionObjects.so");writeControl writeTime;log true;}\n}\n'
(case/'system/controlDict').write_text(control)
(case/'system/decomposeParDict').write_text(header('dictionary','decomposeParDict')+'numberOfSubdomains 4;\nmethod scotch;\n')

# Closed fluid-volume STL for review. It is not the manufactured solid hood.
tris=[]
for name,items in patches.items():
    for f,_ in items:
        tris.extend([(f[0],f[1],f[2]),(f[0],f[2],f[3])])
with (case/'fluid_volume_closed.stl').open('wb') as out:
    out.write(b'Airblade concept fluid volume, metres; CFD only'.ljust(80,b' '));out.write(struct.pack('<I',len(tris)))
    for tri in tris:
        a,b,c=[points[i] for i in tri];nv=cross(sub(b,a),sub(c,a));mag=math.sqrt(dot(nv,nv));nv=tuple(v/mag for v in nv)
        out.write(struct.pack('<12fH',*nv,*a,*b,*c,0))

inletA=sum(math.sqrt(dot(quad_area(f),quad_area(f))) for f,_ in patches['inlet'])
outletA=sum(math.sqrt(dot(quad_area(f),quad_area(f))) for f,_ in patches['outlet'])
meta={'grid':args.grid,'Nu':Nu,'Nd':Nd,'Nt':Nt,'nCells':Nu*Nd*Nt,'nPoints':len(points),'nFaces':len(faces),'nInternalFaces':internal,
      'patches':patchmeta,'stations':stations,'radial_parameters':radial,'segments':segments,'Q_m3_s':Q,
      'Q_m3_min':Q*60,'rho':1.2,'nu':1.5154166667e-5,'turbulence':'steady RANS kOmegaSST',
      'inlet_turbulence_intensity':.05,'inlet_length_scale_m':.006,'inlet_area_m2':inletA,'outlet_area_m2':outletA,
      'ideal_mean_normal_exit_m_s':Q/outletA,'initial_max_speed_m_s':max_speed,'min_initial_cell_jacobian':min_jac,
      'source_blend_sha256':SOURCE['source_blend_sha256'],'geometry_source':str(HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json'),
      'scope':'internal duct only; uniform fan-port inflow; no fan rotor, free-jet external domain, umbrella or droplets',
      'actual_geometry_area_stages':'Loft 7216→7976 mm², circular thin bend, final cosine-slope 7° nozzle and 4-mm lip.'}
(case/'mesh_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
(case/'case.foam').touch()
print(json.dumps({k:meta[k] for k in ['grid','nCells','nPoints','inlet_area_m2','outlet_area_m2','ideal_mean_normal_exit_m_s','min_initial_cell_jacobian']},indent=2))
