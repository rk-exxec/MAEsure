import cv2

from evaluate_droplet import evaluate_droplet


img = cv2.imread('untitled1.png')
roi = cv2.selectROI('ROI', img)
drplt = evaluate_droplet(img, 250)

print(drplt)