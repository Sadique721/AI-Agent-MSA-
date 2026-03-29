import cv2
import numpy as np
import os

class ObjectDetector:
    def __init__(self, config_path="yolov3.cfg", weights_path="yolov3.weights", classes_path="coco.names"):
        # Just stubs for now since YOLO requires physical files to be downloaded
        if os.path.exists(weights_path) and os.path.exists(config_path):
            self.net = cv2.dnn.readNet(weights_path, config_path)
            self.classes = open(classes_path).read().strip().split('\n')
            self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
            self.is_ready = True
        else:
            self.is_ready = False

    def detect(self, frame):
        if not self.is_ready:
            return frame, [], [], []
            
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255, (416,416), swapRB=True)
        self.net.setInput(blob)
        outputs = self.net.forward(self.net.getUnconnectedOutLayersNames())

        boxes = []
        confidences = []
        class_ids = []

        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w/2)
                    y = int(center_y - h/2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])
                color = self.colors[class_ids[i]]
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame, boxes, confidences, class_ids
