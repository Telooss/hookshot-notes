import time, sys
from mem import Game
g = Game()
C = {"gd": 0x100a4c0c7c, "ph1": 0x1043a6f1f4, "ph2": 0x1043a94d0c, "ph3": 0x1043a94e3c, "ph4": 0x1043a912d0}
out = open("samples2.csv", "w"); out.write("t," + ",".join(f"{k}x,{k}y,{k}z" for k in C) + "\n")
t0 = time.time()
while time.time() - t0 < float(sys.argv[1]):
    row = [f"{time.time()-t0:.2f}"]
    for a in C.values(): row += [f"{v:.3f}" for v in (g.vec3(a) or (0, 0, 0))]
    out.write(",".join(row) + "\n"); out.flush(); time.sleep(0.1)
