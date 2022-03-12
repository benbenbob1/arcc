# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 17:31:39 2022

@author: benbrown
"""

from facenet_pytorch import MTCNN
import torch
import cv2

def cvPtsFromBB(bb):
    '''
        Given a bounding box tuple like (x,y,width,height), this function 
        returns ((x1,y1), (x2,y2))
    '''
    x = int(bb[0])
    y = int(bb[1])
    w = int(bb[2])
    h = int(bb[3])
    return ((x, y), (w, h))

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

img = cv2.imread("C:\\Users\\benbrown\\Downloads\\the-brady-bunch-tv-show-on-abc-canceled-no-season-6-1.jpg")
detector = MTCNN(keep_all=True, device=torch.device(device))
boxes, confidence = detector.detect(img) #x,y,w,h
for idx, bb in enumerate(boxes):
    tl, br = cvPtsFromBB(bb)
    print("BB "+str(idx)+": "+str(confidence[idx]))
    cv2.rectangle(img, tl, br, (0,255,0), 1)
cv2.imshow('Test', img)
cv2.waitKey(0)