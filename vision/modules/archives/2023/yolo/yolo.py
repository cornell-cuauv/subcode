#!/usr/bin/env python3
import shm

# Write yolo output to shm groups
def write_objs(objs):
    for idx in range(0, 10):
        if idx >= len(objs):
            getattr(shm, f"yolo{idx+1}").id.set(-1)
            getattr(shm, f"yolo{idx+1}").name.set("")
            getattr(shm, f"yolo{idx+1}").confidence.set(0.0)
        else:
            getattr(shm, f"yolo{idx+1}").xmin.set(objs[idx][0])
            getattr(shm, f"yolo{idx+1}").ymin.set(objs[idx][1])
            getattr(shm, f"yolo{idx+1}").xmax.set(objs[idx][2])
            getattr(shm, f"yolo{idx+1}").ymax.set(objs[idx][3])
            getattr(shm, f"yolo{idx+1}").confidence.set(objs[idx][4])
            getattr(shm, f"yolo{idx+1}").id.set(objs[idx][5])
            getattr(shm, f"yolo{idx+1}").name.set(objs[idx][6])
            idx += 1

# Read yolo outputs from shm
def read_objs(ids=None):
    objs = []
    for idx in range(0, 10):
        vals = getattr(shm, f"yolo{idx+1}").get()
        if vals.id == -1:
            break
        if ids == None or vals.id in ids:
            objs.append([vals.xmin, vals.ymin, vals.xmax, vals.ymax, vals.confidence, vals.id, vals.name])
    return objs
