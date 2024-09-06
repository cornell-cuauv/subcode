#!/usr/bin/env python3

import shm
import numpy as np
from ultralytics import YOLO
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_rect, draw_text

# Write yolo output to shm groups
def write_objs(objs):
    for idx in range(0, 10):
        if idx >= len(objs):
            getattr(shm, f"yolo{idx+1}").id.set(-1)
            getattr(shm, f"yolo{idx+1}").name.set("")
            getattr(shm, f"yolo{idx+1}").confidence.set(0.0)
        else:
            getattr(shm, f"yolo{idx+1}").xmin.set(objs[idx].xyxy[0][0])
            getattr(shm, f"yolo{idx+1}").ymin.set(objs[idx].xyxy[0][1])
            getattr(shm, f"yolo{idx+1}").xmax.set(objs[idx].xyxy[0][2])
            getattr(shm, f"yolo{idx+1}").ymax.set(objs[idx].xyxy[0][3])
            getattr(shm, f"yolo{idx+1}").confidence.set(objs[idx].conf[0])
            getattr(shm, f"yolo{idx+1}").id.set(objs[idx].cls[0])
            # getattr(shm, f"yolo{idx+1}").name.set(objs[idx][6])
            idx += 1

module_options = []

colors = [(128,0,0), (0,0,128), (60,180,75), (0,0,0), (245,130,48), (145,30,180), (0,128,128), (70,240,240), (255, 255, 25), (170, 110, 40)]
# mapping = {
#     0: "faucet",
#     1: "claw",
#     2: "curve",
#     3: "shovel",
#     4: "wishbone",
#     5: "nozzle",
#     6: "dipper",
#     7: "lightning",
#     8: "slingshot",
#     9: "dragon",
#     10: "belt",
#     11: "triangle",
#     12: "buoy"
# }
mapping = {
    "G1": "faucet",
    "G2": "wishbone",
    "G3": "nozzle",
    "G4": "dipper",
    "G5": "lightning",
    "G6": "slingshot",
    "G7": "dragon",
    "G8": "belt",
    "G9": "triangle",
    "G10": "claw",
    "G11": "curve",
    "G12": "shovel",
    "buoy": "buoy"
}

class Glyph_Yolo(ModuleBase):
    model = YOLO('vision/yolo/auv_models/buoys640px.pt')

    def process(self, img):
        # Infer with model
        results = self.model(img) # stream=True to avoid copying img to gpu
        for result in results:
            result = result.cpu()
            boxes = result.boxes.xyxy.numpy()
            class_name = result.boxes.cls
            conf = result.boxes.conf

            for shm_names in mapping:
                getattr(shm, f"{mapping[shm_names]}_glyph").heuristic.set(0)
            
            # Write to shm and Visualize
            for idx in range(0, len(mapping)):
                if idx < len(boxes) and idx < len(class_name) and idx < len(conf) and idx < len(result.names):
                    draw_rect(img, (int(boxes[idx][0]), int(boxes[idx][1])), (int(boxes[idx][2]), int(boxes[idx][3])), thickness=5, color=colors[int(class_name[idx].item())])
                                        
                    draw_text(img, str(mapping[result.names[class_name[idx].item()]] + " " + str(int(conf[idx].item()*100))), (int(boxes[idx][0]), int(boxes[idx][1])), color=colors[int(class_name[idx].item())], scale=0.75, thickness=2)

                    # draw_text(img, mapping[result.names[class_name[idx].item()]] + " " + str(int(conf[idx].item()*100)), (int(boxes[idx][0]), int(boxes[class_name[idx]][1])), scale=0.75, color=colors[int(class_name[idx].item())], thickness=2)

                    getattr(shm, f"yolo{idx+1}").xmin.set(boxes[idx][0])  # xmin
                    getattr(shm, f"yolo{idx+1}").ymin.set(boxes[idx][1])  # ymin
                    getattr(shm, f"yolo{idx+1}").xmax.set(boxes[idx][2])  # xmax
                    getattr(shm, f"yolo{idx+1}").ymax.set(boxes[idx][3])  # ymax
                    getattr(shm, f"yolo{idx+1}").confidence.set(conf[idx].item())
                    getattr(shm, f"yolo{idx+1}").id.set(int(class_name[idx].item()))
                    getattr(shm, f"yolo{idx+1}").name.set(result.names[idx])

                    # getattr(shm, f"{mapping[result.names[class_name[idx].item()]]}_glyph").area.set(abs(boxes[idx][0]-boxes[idx][2])*abs(boxes[idx][1]-boxes[idx][3]))
                    # getattr(shm, f"{mapping[result.names[class_name[idx].item()]]}_glyph").center_x.set((boxes[idx][0]+boxes[idx][2])/2)
                    # getattr(shm, f"{mapping[result.names[class_name[idx].item()]]}_glyph").center_y.set((boxes[idx][1]+boxes[idx][3])/2)
                    # getattr(shm, f"{mapping[result.names[class_name[idx].item()]]}_glyph").heuristic.set(conf[idx].item())
                    # getattr(shm, f"{mapping[result.names[class_name[idx].item()]]}_glyph").visible.set(1)
                    

                    

        self.post("det", img)

if __name__ == '__main__':
    Glyph_Yolo("forward", module_options)()
