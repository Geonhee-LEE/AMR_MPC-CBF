from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver, AcadosSimSolver
from casadi import SX, vertcat, sin, cos, Function
import numpy as np
import scipy.linalg
from CarModel import *
from Path import Path
import time
import matplotlib.pyplot as plt
from new_utils import *

Tf = 1.5  # prediction horizon
N = int(Tf*50)  # number of discretization steps
T = 30.0  # maximum simulation time[s]
v1 = 2.5
v2 = 1.5
sref_N1 = Tf*v1  # reference for final reference progress
sref_N2 = Tf*v2  # reference for final reference progress

n_lap = 5

l1=10
l2 = 3
path1 = Path(l1, l2, 2)
path2 = Path(l2, l1, 2, traslx=(l1-l2)/2, trasly=-(l1-l2)/2)

fixed_obstacles1 = np.array([[6., 0.1, 0.],
                            [13., -0.1, 0.],
                            [20., 0.2, 0.],
                            [25., -0.1, 0.],
                            [30., -0.1, 0.],
                            [35., 0.1, 0.],
                            [41., -0.1, 0.]])
fixed_obstacles1 = None#np.array([[7., 0.4, 0.],[13., -0.5, 0.]])
fixed_obstacles2 = None#np.array([[15., 0.4, 0.],[27.5, -0.4, 0.]])
 
moving_obstacles1 = np.array([5., 0.3, 0., 0.5])
moving_obstacles2 = np.array([25., -0.3, 0.0, 0.5])

x01 = np.array([0., 0., 0.])
x02 = np.array([15., 0., 0.])
acados_solver1, car_model1 = create_problem(path1, 1, 0.5, fixed_obstacles1, path2, fixed_obstacles2, N, Tf, n_lap, x01, "1")
acados_solver2, car_model1 = create_problem(path2, 1, 0.5, fixed_obstacles2, path1, fixed_obstacles1, N, Tf, n_lap, x02, "2")

Nsim = int(T * N / Tf)
# initialize data structs
nx = 3
nu = 2
simX = np.ndarray((Nsim, nx*2))
simU = np.ndarray((Nsim, nu*2))
simX_horizon = np.ndarray((Nsim, N, nx*2))
simObs_position1 = np.ndarray((Nsim, 1, 4))
simObs_position2 = np.ndarray((Nsim, 1, 4))
s01 = x01[0]
s02 = x02[0]
tcomp_sum = 0
tcomp_max = 0

# simulate
for i in range(Nsim):
    # update reference
    sref1 = s01 + sref_N1
    sref2 = s02 + sref_N2
    sref_obs1 = moving_obstacles1[0] + Tf*moving_obstacles1[3]
    sref_obs2 = moving_obstacles2[0] + Tf*moving_obstacles2[3]
    for j in range(N):
        yref = np.array([s01 + (sref1 - s01) * j / N, 0, 0, 0, 0])
        acados_solver1.set(j, "yref", yref)
        yref = np.array([s02 + (sref2 - s02) * j / N, 0, 0, 0, 0])
        acados_solver2.set(j, "yref", yref)

        p = np.zeros(12)
        p[0:4] = np.copy(moving_obstacles1) 
        p[4:8] = np.copy(moving_obstacles2)
        p[8:11] = np.copy(x02)
        p[11] = v2
        p[0] += (sref_obs1 - moving_obstacles1[0]) * j / N
        p[4] += (sref_obs2 - moving_obstacles2[0]) * j / N
        p[8] += (sref2 - s02) * j / N
        
        P = np.zeros_like(p)
        P[0], P[1] = path1.get_cartesian_coords(p[0], p[1])
        P[2] = path1.get_theta_r(p[0])
        P[3] = p[3]
        P[4], P[5] = path2.get_cartesian_coords(p[4], p[5])
        P[6] = path2.get_theta_r(p[4])
        P[7] = p[7]
        P[8], P[9] = path2.get_cartesian_coords(p[8], p[9])
        P[10] = path2.get_theta_r(p[8])
        P[11] = p[11]
        acados_solver1.set(j, "p", P)

        p = np.zeros(12)
        p[0:4] = np.copy(moving_obstacles1) 
        p[4:8] = np.copy(moving_obstacles2)
        p[8:11] = np.copy(x01)
        p[11] = v1
        p[0] += (sref_obs1 - moving_obstacles1[0]) * j / N
        p[4] += (sref_obs2 - moving_obstacles2[0]) * j / N
        p[8] += (sref1 - s01) * j / N
        
        P = np.zeros_like(p)
        P[0], P[1] = path1.get_cartesian_coords(p[0], p[1])
        P[2] = path1.get_theta_r(p[0])
        P[3] = p[3]
        P[4], P[5] = path2.get_cartesian_coords(p[4], p[5])
        P[6] = path2.get_theta_r(p[4])
        P[7] = p[7]
        P[8], P[9] = path1.get_cartesian_coords(p[8], p[9])
        P[10] = path2.get_theta_r(p[8])
        P[11] = p[11]
        acados_solver2.set(j, "p", P)

    yref_N = np.array([sref1, 0, 0])
    acados_solver1.set(N, "yref", yref_N)
    yref_N = np.array([sref2, 0, 0])
    acados_solver2.set(N, "yref", yref_N)
    
    p = np.zeros(12)
    p[0:4] = np.copy(moving_obstacles1) 
    p[4:8] = np.copy(moving_obstacles2)
    p[8:11] = np.copy(x02)
    p[11] = v2
    p[0] = sref_obs1
    p[4] = sref_obs2
    p[8] = sref2

    P = np.zeros_like(p)
    P[0], P[1] = path1.get_cartesian_coords(p[0], p[1])
    P[2] = path1.get_theta_r(p[0])
    P[3] = p[3]
    P[4], P[5] = path2.get_cartesian_coords(p[4], p[5])
    P[6] = path2.get_theta_r(p[4])
    P[7] = p[7]
    P[8], P[9] = path2.get_cartesian_coords(p[8], p[9])
    P[10] = path2.get_theta_r(p[8])
    P[11] = p[11]

    acados_solver1.set(N, "p", P)

    
    p = np.zeros(12)
    p[0:4] = np.copy(moving_obstacles1) 
    p[4:8] = np.copy(moving_obstacles2)
    p[8:11] = np.copy(x01)
    p[11] = v1
    p[0] = sref_obs1
    p[4] = sref_obs2
    p[8] = sref1

    P = np.zeros_like(p)
    P[0], P[1] = path1.get_cartesian_coords(p[0], p[1])
    P[2] = path1.get_theta_r(p[0])
    P[3] = p[3]
    P[4], P[5] = path2.get_cartesian_coords(p[4], p[5])
    P[6] = path2.get_theta_r(p[4])
    P[7] = p[7]
    P[8], P[9] = path2.get_cartesian_coords(p[8], p[9])
    P[10] = path1.get_theta_r(p[8])
    P[11] = p[11]

    acados_solver1.set(N, "p", P)

    # solve ocp
    t = time.time()

    status = acados_solver1.solve()
    if status != 0:
        print("acados (problem 1) returned status {} in closed loop iteration {}.".format(status, i))
    status = acados_solver2.solve()
    if status != 0:
        print("acados (problem 2) returned status {} in closed loop iteration {}.".format(status, i))

    elapsed = time.time() - t

    # manage timings
    tcomp_sum += elapsed
    if elapsed > tcomp_max:
        tcomp_max = elapsed

    # get solution
    x01 = acados_solver1.get(0, "x")
    x02 = acados_solver2.get(0, "x")
    u01 = acados_solver1.get(0, "u")
    u02 = acados_solver2.get(0, "u")
    for j in range(nx):
        simX[i, j] = x01[j]
    for j in range(nx):
        simX[i, j+nx] = x02[j]
    for j in range(nu):
        simU[i, j] = u01[j]
    for j in range(nu):
        simU[i, j+nu] = u02[j]
    for j in range(N):
        simX_horizon[i, j, 0:3] = acados_solver1.get(j, 'x')
    for j in range(N):
        simX_horizon[i, j, 3:6] = acados_solver2.get(j, 'x')
    
    # update initial condition
    x01 = acados_solver1.get(1, "x")
    acados_solver1.set(0, "lbx", x01)
    acados_solver1.set(0, "ubx", x01)
    s01 = x01[0]

    x02 = acados_solver2.get(1, "x")
    acados_solver2.set(0, "lbx", x02)
    acados_solver2.set(0, "ubx", x02)
    s02 = x02[0]
    
    simObs_position1[i, 0, :] = np.copy(moving_obstacles1)
    simObs_position2[i, 0, :] = np.copy(moving_obstacles2)
    moving_obstacles1[0] += (sref_obs1 - moving_obstacles1[0])/ N
    moving_obstacles2[0] += (sref_obs2 - moving_obstacles2[0])/ N
    
t = np.linspace(0.0, Nsim * Tf / N, Nsim)

time_now = datetime.datetime.now()
folder = time_now.strftime("%Y_%m_%d_%H:%M:%S")
os.mkdir('results/' + folder)

plotRes(simX, simU, t)
plt.savefig('results/' + folder + "/plots.png")
#plt.show()

simX1 = simX[:, :3]
simX2 = simX[:, 3:]
simU1 = simU[:, :2]
simU2 = simU[:, 2:]
simX_horizon1 = simX_horizon[:, :, :3]
simX_horizon2 = simX_horizon[:, :, 3:]
# THIS IS A BIT SLOW
renderVideo(simX1, simU1, simX_horizon1, fixed_obstacles1, simObs_position1, path1,
          simX2, simX2, simX_horizon2, fixed_obstacles2, simObs_position2, path2,
          car_model1, t, folder)