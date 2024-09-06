#!/usr/bin/env python3

import shm
from ultralytics import YOLO
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_rect, draw_text

import onnxruntime as rt

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
    """
    enable_mem_pattern: This option controls whether memory pattern optimization is enabled or not. When enabled, onnxruntime can analyze the memory usage pattern of a model and allocate memory more efficiently, which can reduce memory usage and improve performance. Setting this option to False disables memory pattern optimization.
    
    enable_cpu_mem_arena: This option controls whether CPU memory arena is enabled or not. Memory arena is a technique used by onnxruntime to manage memory more efficiently. When enabled, onnxruntime allocates memory in chunks and reuses them, which can improve performance. Setting this option to False disables CPU memory arena.
    
    graph_optimization_level: This option controls the level of optimization performed on the ONNX graph during inference. onnxruntime provides several levels of optimization, ranging from ORT_DISABLE_ALL (which disables all optimization) to ORT_ENABLE_EXTENDED (which enables all available optimization). In the code you provided, ORT_DISABLE_ALL is used, which disables all optimization.
    """

    opt_session = rt.SessionOptions()
    opt_session.enable_mem_pattern = False
    opt_session.enable_cpu_mem_arena = False
    opt_session.graph_optimization_level = rt.GraphOptimizationLevel.ORT_DISABLE_ALL

    model_path = 'vision/yolo/auv_models/buoys640px.onnx'
    EP_list = ['CPUExecutionProvider', 'CUDAExecutionProvider'] # Will try to use CPU, else CUDA

    ort_session = rt.InferenceSession(model_path, providers=EP_list)

    def process(self, img):
        model_inputs = self.ort_session.get_inputs()
        input_names = [model_inputs[i].name for i in range(len(model_inputs))]
        input_shape = model_inputs[0].shape

        # Infer with model
        ## Resize image
        # img = img.resize(input_shape)
        input_image = resized / 255.0
        input_image = input_image.transpose(2,0,1)
        input_tensor = input_image[np.newaxis, :, :, :].astype(np.float32)

        outputs = self.ort_session.run(output_names, {input_names[0]: input_tensor})[0]

        for result in results:
            result = result.cpu()
            boxes = result.boxes.xyxy.numpy()
            class_name = result.boxes.cls
            conf = result.boxes.conf
            
            # Write to shm and Visualize
            for idx in range(0, 10):
                if idx < len(boxes) and idx < len(class_name) and idx < len(conf) and idx < len(result.names):
                    draw_rect(img, (int(boxes[idx][0]), int(boxes[idx][1])), (int(boxes[idx][2]), int(boxes[idx][3])), thickness=5, color=colors[idx])

                    draw_text(img, mapping[result.names[idx]] + " " + str(int(conf[idx].item()*100)), (int(boxes[idx][0]), int(boxes[idx][1])), scale=0.75, color=colors[idx], thickness=2)

                    getattr(shm, f"yolo{idx+1}").xmin.set(boxes[idx][0])  # xmin
                    getattr(shm, f"yolo{idx+1}").ymin.set(boxes[idx][1])  # ymin
                    getattr(shm, f"yolo{idx+1}").xmax.set(boxes[idx][2])  # xmax
                    getattr(shm, f"yolo{idx+1}").ymax.set(boxes[idx][3])  # ymax
                    getattr(shm, f"yolo{idx+1}").confidence.set(conf[idx].item())
                    getattr(shm, f"yolo{idx+1}").id.set(int(class_name[idx].item()))
                    getattr(shm, f"yolo{idx+1}").name.set(result.names[idx])
                else:
                    getattr(shm, f"yolo{idx+1}").id.set(-1)
                    getattr(shm, f"yolo{idx+1}").name.set("")
                    getattr(shm, f"yolo{idx+1}").confidence.set(0.0)

        self.post("det", img)

if __name__ == '__main__':
    Glyph_Yolo("forward", module_options)()
