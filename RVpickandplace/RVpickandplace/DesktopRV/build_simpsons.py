# Type help("robolink") or help("robodk") for more information
# Press F5 to run the script
# Documentation: https://robodk.com/doc/en/RoboDK-API.html
# Reference:     https://robodk.com/doc/en/PythonAPI/index.html
# Note: It is not required to keep a copy of this file, your python script is saved with the station
from robodk.robolink import Robolink, RUNMODE_SIMULATE, ITEM_TYPE_ROBOT, ITEM_TYPE_TOOL, ITEM_TYPE_FRAME, \
    ITEM_TYPE_OBJECT
from robolink import *    # RoboDK API
from robodk import *      # Robot toolbox
from random import randint
import random
import cv2
import imutils
from matplotlib import pyplot as plt
import argparse
from scipy.spatial import distance as dist
from collections import OrderedDict
import numpy as np

from robodk.robolink import *
import datetime
from tkinter import *
from tkinter import filedialog

RDK = Robolink()

SIZE_BOX_Z = 50

#Calc Homography matrix from previously extracted red locations
# to calculate the transformation matrix
input_pts = np.float32([[160,88],[840,91],[158,546],[838,550]])
output_pts = np.float32([[750,370],[750,-370],[250,370],[250,-370]])
# Compute the perspective transform M
H = np.float32(cv2.getPerspectiveTransform(input_pts,output_pts))
print('Homography Matrix: \n', H)


#Image Processing stuff
#
#
class ShapeDetector:
    def __init__(self):
        pass
    def detect(self, c):
        # initialize the shape name and approximate the contour
        shape = "unidentified"
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        delta_x = approx[0][0][0] - approx[1][0][0]
        delta_y = approx[0][0][1] - approx[1][0][1]
        theta_radians = math.atan2(delta_y, delta_x)
    
        # if the shape is a triangle, it will have 3 vertices
        if len(approx) == 3:
            shape = "triangle"
        # if the shape has 4 vertices, it is either a square or
        # a rectangle
        elif len(approx) == 4:
            # compute the bounding box of the contour and use the
            # bounding box to compute the aspect ratio
            (x, y, w, h) = cv2.boundingRect(approx)
            ar = w / float(h)
            # a square will have an aspect ratio that is approximately
            # equal to one, otherwise, the shape is a rectangle
            shape = "square" if ar >= 0.95 and ar <= 1.05 else "rectangle"
        # if the shape is a pentagon, it will have 5 vertices
        elif len(approx) == 5:
            shape = "pentagon"
        # otherwise, we assume the shape is a circle
        else:
            shape = "circle"
        # return the name of the shape
        return shape, math.degrees(pi-theta_radians) #convert to deg fopr visu

class ColorLabeler:
    def __init__(self):
        # initialize the colors dictionary, containing the color
        # name as the key and the RGB tuple as the value
        colors = OrderedDict({
            "orange": (255, 0.55*255, 0),
            "green": (0, 255, 0),
            "yellow": (255, 255, 0),
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "blue": (0, 0, 255)})
        # allocate memory for the L*a*b* image, then initialize
        # the color names list
        self.lab = np.zeros((len(colors), 1, 3), dtype="uint8")
        self.colorNames = []
        # loop over the colors dictionary
        for (i, (name, rgb)) in enumerate(colors.items()):
            # update the L*a*b* array and the color names list
            self.lab[i] = rgb
            self.colorNames.append(name)
        # convert the L*a*b* array from the RGB color space
        # to L*a*b*
        self.lab = cv2.cvtColor(self.lab, cv2.COLOR_RGB2LAB)
        
    def label(self, image, c):
        # construct a mask for the contour, then compute the
        # average L*a*b* value for the masked region
        mask = np.zeros(image.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [c], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)
        mean = cv2.mean(image, mask=mask)[:3]
        # initialize the minimum distance found thus far
        minDist = (np.inf, None)
        # loop over the known L*a*b* color values
        for (i, row) in enumerate(self.lab):
            # compute the distance between the current L*a*b*
            # color value and the mean of the image
            d = dist.euclidean(row[0], mean)
            # if the distance is smaller than the current distance,
            # then update the bookkeeping variable
            if d < minDist[0]:
                minDist = (d, i)
        # return the name of the color with the smallest distance
        return self.colorNames[minDist[1]]

path = r"C:\Users\Harish\Desktop\RVpickandplace\DesktopRV\Punta.png"
def detect_bricks(path):
    # load the image and resize it to a smaller factor so that
    # the shapes can be approximated better
    image = cv2.imread(path)

    resized = imutils.resize(image, width=480)
    ratio = image.shape[0] / float(resized.shape[0])
    # blur the resized image slightly, then convert it to both
    # grayscale and the L*a*b* color spaces
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
    thresh = cv2.threshold(gray, 230 ,240, 1)[1]
    # find contours in the thresholded image
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    # initialize the shape detector and color labeler
    sd = ShapeDetector()
    cl = ColorLabeler()
    # concatanate image Horizontally
    Hori1 = np.concatenate((resized, blurred), axis=1)
    Hori2 = np.concatenate((cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB), cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)), axis=1)
    # concatanate image Vertically
    Verti = np.concatenate((Hori1, Hori2), axis=0)    
    #cv2.imshow('Preprocessing', Verti)
    #cv2.waitKey(10)

    img = cv2.drawContours(thresh, cnts, -1, (0,255,0), 3)


    # loop over the contours
    lego_brick_list = []
    for c in cnts:
        # compute the center of the contour
        M = cv2.moments(c)
        if M["m00"] != 0:
            cX = int((M["m10"] / M["m00"]) * ratio)
            cY = int((M["m01"] / M["m00"]) * ratio)
            # detect the shape of the contour and label the color
            shape, rotation = sd.detect(c)
            color = cl.label(lab, c)
            # multiply the contour (x, y)-coordinates by the resize ratio,
            # then draw the contours and the name of the shape and labeled
            # color on the image
            c = c.astype("float")
            c *= ratio
            c = c.astype("int")

            #Transofrm pixel coordinates to world coordinates
            world_coords = np.squeeze(cv2.perspectiveTransform(np.float32([cX,cY]).reshape(-1,1,2).astype(np.float32), H), axis=1)[0]
            text = "{} {} {} {}deg".format(color, int(world_coords[0]), int(world_coords[1]), int(rotation))
            print(color, shape,cX,cY)
            print('table coodinates: ', world_coords[0], world_coords[1])

            #insert brick woth pose and color into list to be used later
            lego_brick_list.append([world_coords[0],world_coords[1],math.radians(rotation),color,rotation])

            cv2.drawContours(image, [c], -1, (0, 255, 0), 2)
            cv2.putText(image, text, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (120, 120, 120), 1)
        # show the output image
    Hori3 = np.concatenate((Verti, image), axis=1)
    #cv2.imshow("Detected Bricks", Hori3)
    #cv2.waitKey(10)
    cv2.imwrite('vision_visu.png', Hori3)
    return lego_brick_list
                            



#Simulation stuff
#
#

def parts_setup(positions):
    """Place a list of parts in a reference frame. The part/reference object must have been previously copied to the clipboard."""
    nparts = len(positions)
    for i in range(nparts-4): #-4 to not generate the calibration cube
        print((position_list[i][:]))
        newpart = RDK.AddFile(r'box.sld')
        newpart.Scale([SIZE_BOX_Z/100, SIZE_BOX_Z/100, SIZE_BOX_Z/100]) #scale with respect to the reference object (100mm cube)
        newpart.setName('lego_brick ' + str(i+1)) #set item name
        newpart.setPose(transl(positions[i][0],positions[i][1],25)* rotz(random.uniform(0, 1.57)))#set item position 
        newpart.setVisible(True, False) #make item visible but hide the reference frame
        if i < 1:
            newpart.setColor([0,0,0,1]) #1x black
            newpart.setName('lego_brick ' + str(i+1) + '_black') #set item name
        elif i < 2:
            newpart.setColor([0,1,0,1]) #1x green
            newpart.setName('lego_brick ' + str(i+1) + '_green') #set item name
        elif i < 4:
            newpart.setColor([1,0.55,0,1]) #2x orange
            newpart.setName('lego_brick ' + str(i+1) + '_orange') #set item name
        elif i < 10:
            newpart.setColor([1,1,0,1])#6x yellow
            newpart.setName('lego_brick ' + str(i+1) + '_yellow') #set item name
        elif i < 14:
            newpart.setColor([0,0,1,1]) #4x blue
            newpart.setName('lego_brick ' + str(i+1) + '_blue') #set item name
        else:
            newpart.setColor([1,0,0,1]) #4x red calibration
            newpart.setName('lego_brick ' + str(i+1) + '_red_calib') #set item name


def cleanup(objects, startswith="lego_brick"):
    """Deletes all objects where the name starts with "startswith", from the provided list of objects."""    
    for item in objects:
        if item.Name().startswith(startswith):
            item.Delete()
            
def WaitPartCamera():
    """Simulate camera detection"""
    RDK = Robolink()

    if RDK.RunMode() == RUNMODE_SIMULATE:
        # Simulate the camera by waiting for an object to be detected
        #if True:
        lego_brick_list = []
        for part in check_objects:
            # calculate the position of the part with respect to the target
            part_pose = part[0].PoseAbs()
            tx,ty,tz,rx,ry,rz = pose_2_xyzrpw(part_pose)
            rz = rz * pi/180.0 # Convert degrees to radians
            #print('Part detected: TX=%.1f,TY=%.1f,TZ=%.1f' % (tx,ty,rz))
            #if(part.
            lego_brick_list.append([tx,ty,rz,part[1]])

        return lego_brick_list
   # else:

        #RDK = Robolink()

        date_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path_rdk = RDK.getParam('PATH_OPENSTATION')
        file_name = "ScreenShot_" + date_str + ".png"

        types = (("PNG files", "*.png"), ("All files", "*.*"))
        fname = filedialog.asksaveasfile(title="Select file to save", defaultextension=types, filetypes=types,
                                         initialdir=path_rdk, initialfile=file_name)
        if fname is None:
            quit()

        # file_path = fname.name
        file_path = r"C:\Users\Harish\PycharmProjects\pythonProject\MiniProject\RobotImages"

        print("Saving image to: " + file_path)

        cmd = "Snapshot"
        # cmd = "SnapshotWhite" # Snapshot with white background
        # cmd = "SnapshotWhiteNoTextNoFrames" # Snapshot with white background, no text or coordinate systems

        returned = RDK.Command(cmd, file_path)
        print(returned)
        RDK.ShowMessage("Snapshot saved: " + file_path, False)


        #Use real image processing and brick detection
        print("Saving camera snapshot to file:" + 'Image-Camera-Simulation.png')
        RDK.Cam2D_Snapshot('Image-Camera-Simulation.png')

        # Implement your image processing here:
        return detect_bricks('Image-Camera-Simulation.png')
    else:
        RDK.RunProgram('WaitPartCamera')
    return 0,0,0


#Robot stuff

def TCP_On(toolitem):
    """Attaches the closest object to the toolitem Htool pose,
    It will also output appropriate function calls on the generated robot program (call to TCP_On)"""
    toolitem.AttachClosest()
    #toolitem.RDK().RunMessage('Set air valve on')
    toolitem.RDK().RunProgram('TCP_On()');
        
def TCP_Off(toolitem, itemleave=0):
    """Detaches the closest object attached to the toolitem Htool pose,
    It will also output appropriate function calls on the generated robot program (call to TCP_Off)"""
    #toolitem.DetachClosest(itemleave)
    toolitem.DetachAll(itemleave)
    #toolitem.RDK().RunMessage('Set air valve off')
    toolitem.RDK().RunProgram('TCP_Off()');

def find_brick(brick_list, color):
    """ Find brick of desired color in list an remove element
    """
    for i in range(len(brick_list)):
        if(brick_list[i][3] == color):
            x=brick_list[i][0]
            y=brick_list[i][1]
            r=brick_list[i][2]
            #remove brick from list to not use it again
            brick_list.pop(i)
            return x,y,r
    print('Houston, we have a problem!')

def build_figure(figure_frame, colors):
    poseref = figure_frame.Pose()
    for i in range(len(colors)):
        #robot.MoveJ(dont_hit_bricks)
        x,y,r = find_brick(lego_brick_list,colors[i])
        robot.MoveJ(Pose(x,y,SIZE_BOX_Z*4,180,0,0))
        robot.MoveJ(Pose(x,y,SIZE_BOX_Z,180,0,0))
        TCP_On(tool)
        robot.MoveJ(Pose(x,y,SIZE_BOX_Z*4,180,0,0))
        #robot.MoveJ(dont_hit_bricks)
        ang = r #rotate tool axis to correct rotation of brick
        posei = poseref*rotz(ang)*transl(0,0,-SIZE_BOX_Z*4) #calc new pose of brick for figure
        robot.MoveJ(posei)
        posei = poseref*rotz(ang)*transl(0,0,-SIZE_BOX_Z*i) #calc new pose of brick for figure
        robot.MoveJ(posei)
        TCP_Off(tool)

    
   

# gather robot, tool and reference frames from the station
robot               = RDK.Item('UR5', ITEM_TYPE_ROBOT)
tool                = RDK.Item('Gripper', ITEM_TYPE_TOOL)
table               = RDK.Item('World', ITEM_TYPE_FRAME)

robot.setPoseTool(tool)

#remove all old lego bricks
cleanup(RDK.ItemList())

#create list with semi-random non-overlapping bricks
position_list = []
position_list.append([randint(350,450),randint(-450,-400)])
position_list.append([randint(350,450),randint(-350,-300)])
position_list.append([randint(350,450),randint(-250,-200)])
position_list.append([randint(350,450),randint(-150,-100)])
position_list.append([randint(350,450),randint(-50,0)])
position_list.append([randint(350,450),randint(50,100)])
position_list.append([randint(350,450),randint(150,200)])
position_list.append([randint(350,450),randint(250,300)])
position_list.append([randint(550,650),randint(-450,-400)])
position_list.append([randint(550,650),randint(-350,-300)])
position_list.append([randint(550,650),randint(-150,-100)])
position_list.append([randint(550,650),randint(50,100)])
position_list.append([randint(550,650),randint(200,250)])
position_list.append([randint(550,650),randint(400,450)])

#calibration cubes
position_list.append([250,-370])
position_list.append([250,370])
position_list.append([750,-370])
position_list.append([750,370])


#setup brick with list
parts_setup(position_list)


# Get all object names to
all_objects = RDK.ItemList(ITEM_TYPE_OBJECT, True)
print(all_objects[0])
# Get object items in a list (faster) and filter by keyword
check_objects = []
for i in range(len(all_objects)):
    if all_objects[i].count('black') > 0:
        check_objects.append([RDK.Item(all_objects[i]), 'black'])
    if all_objects[i].count('green') > 0:
        check_objects.append([RDK.Item(all_objects[i]), 'green'])
    if all_objects[i].count('blue') > 0:
        check_objects.append([RDK.Item(all_objects[i]), 'blue'])
    if all_objects[i].count('yellow') > 0:
        check_objects.append([RDK.Item(all_objects[i]), 'yellow'])
    if all_objects[i].count('orange') > 0:
        check_objects.append([RDK.Item(all_objects[i]), 'orange'])
        
lego_brick_list = WaitPartCamera()
print(lego_brick_list)

# get the home target frames:
home = RDK.Item('Home')
homer = RDK.Item('Homer')
march = RDK.Item('March')
lisa = RDK.Item('Lisa')
bart = RDK.Item('Bart')
maggie = RDK.Item('Maggie')


#Move Robot Home and get Image from table
robot.MoveJ(home)

homer_colors = ['blue',  'black', 'yellow']
march_colors = ['green', 'yellow', 'blue']
lisa_colors = ['yellow',  'orange', 'yellow']
bart_colors = ['blue',  'orange', 'yellow']
maggie_colors = ['blue', 'yellow']

#Build Homer
build_figure(homer, homer_colors)
build_figure(march, march_colors)
build_figure(lisa, lisa_colors)
build_figure(bart, bart_colors)
build_figure(maggie, maggie_colors)

#Move Home after finish
robot.MoveJ(home)


