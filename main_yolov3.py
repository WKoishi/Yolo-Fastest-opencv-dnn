import cv2 as cv
import numpy as np
from time import perf_counter

# Initialize the parameters
confThreshold = 0.25  # Confidence threshold
nmsThreshold = 0.4  # Non-maximum suppression threshold
inpWidth = 320  # Width of network's input image
inpHeight = 320  # Height of network's input image

# Give the configuration and weight files for the model and load the network using them.
modelConfiguration = "Yolo-Fastest-voc/yolo-fastest-xl.cfg"
modelWeights = "Yolo-Fastest-voc/yolo-fastest-xl.weights"
# Load names of classes
classesFile = "voc.names"
classes = None
with open(classesFile, 'rt') as f:
    classes = f.read().rstrip('\n').split('\n')
colors = [np.random.randint(0, 255, size=3).tolist() for _ in range(len(classes))]

# Get the names of the output layers
def getOutputsNames(net):
    # Get the names of all the layers in the network
    layersNames = net.getLayerNames()
    # print(dir(net))
    # Get the names of the output layers, i.e. the layers with unconnected outputs
    return [layersNames[i[0] - 1] for i in net.getUnconnectedOutLayers()]

# Draw the predicted bounding box
def drawPred(classId, conf, left, top, right, bottom):
    # Draw a bounding box.
    cv.rectangle(frame, (left, top), (right, bottom), (0,0,255), thickness=4)

    label = '%.2f' % conf

    # Get the label for the class name and its confidence
    if classes:
        assert (classId < len(classes))
        label = '%s:%s' % (classes[classId], label)

    # Display the label at the top of the bounding box
    labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    top = max(top, labelSize[1])
    # cv.rectangle(frame, (left, top - round(1.5 * labelSize[1])), (left + round(1.5 * labelSize[0]), top + baseLine), (255,255,255), cv.FILLED)
    cv.putText(frame, label, (left, top-10), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), thickness=2)

# Remove the bounding boxes with low confidence using non-maxima suppression
def postprocess(frame, outs):
    frameHeight = frame.shape[0]
    frameWidth = frame.shape[1]

    # Scan through all the bounding boxes output from the network and keep only the
    # ones with high confidence scores. Assign the box's class label as the class with the highest score.
    classIds = []
    confidences = []
    boxes = []
    for out in outs:
        max_scores_index = np.argmax(out[:,5:], axis=1)
        max_scores = out[:,5:][np.arange(out.shape[0]), max_scores_index]
        select_index = max_scores > confThreshold
        out = out[select_index,:]
        max_scores = max_scores[select_index]
        max_scores_index = max_scores_index[select_index]
        for i, detection in enumerate(out):
            center_x = int(detection[0] * frameWidth)
            center_y = int(detection[1] * frameHeight)
            width = int(detection[2] * frameWidth)
            height = int(detection[3] * frameHeight)
            left = int(center_x - width / 2)
            top = int(center_y - height / 2)
            classIds.append(max_scores_index[i])
            confidences.append(float(max_scores[i]))
            boxes.append([left, top, width, height])

    # Perform non maximum suppression to eliminate redundant overlapping boxes with
    # lower confidences.
    indices = cv.dnn.NMSBoxes(boxes, confidences, confThreshold, nmsThreshold)
    for i in indices:
        i = i[0]
        box = boxes[i]
        left = box[0]
        top = box[1]
        width = box[2]
        height = box[3]
        drawPred(classIds[i], confidences[i], left, top, left + width, top + height)

if __name__=='__main__':

    net = cv.dnn.readNetFromDarknet(modelConfiguration, modelWeights)
    net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)

    output_layers = getOutputsNames(net)
    
    cap = cv.VideoCapture(1)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    cap.set(cv.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 600)

    while 1:
        ret, frame = cap.read()
        if ret:
            # Create a 4D blob from a frame.
            blob = cv.dnn.blobFromImage(frame, 1/255.0, (inpWidth, inpHeight), [0, 0, 0], swapRB=False, crop=False)

            # Sets the input to the network
            net.setInput(blob)

            # Runs the forward pass to get output of the output layers
            outs = net.forward(output_layers)
        
            # Remove the bounding boxes with low confidence
            postprocess(frame, outs)

            # Put efficiency information. The function getPerfProfile returns the overall time for inference(t) and the timings for each of the layers(in layersTimes)
            t, _ = net.getPerfProfile()
            label = 'Inference time: %.2f ms' % (t * 1000.0 / cv.getTickFrequency())
            cv.putText(frame, label, (0, 15), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255))

            winName = 'Deep learning object detection in OpenCV'
            cv.imshow(winName, frame)

        # press Esc to exit
        if cv.waitKey(1)&0XFF == 27:
            break

    cap.release()
    cv.destroyAllWindows()
