import torch
import numpy as np

# Model
model = torch.hub.load('ultralytics/yolov5', 'custom', '../yolo/auv_models/balls.pt')

def infer(img):
    # Infer with model
    results = model(img)
    # Get results as dataframe
    df = results.pandas().xyxy[0]
    # Process results
    data = []
    for index, row in df.iterrows():
        obj = []
        obj.append(row['xmin'])
        obj.append(row['ymin'])
        obj.append(row['xmax'])
        obj.append(row['ymax'])
        obj.append(row['confidence'])
        obj.append(row['class'])
        obj.append(row['name'])
        data.append(obj)
    return data
        




