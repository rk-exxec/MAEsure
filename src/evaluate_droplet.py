#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2020  Raphael Kriegl

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Droplet eval function

# TODO add rolling average, with outlier ingoring and 1 sec worth of averaging
# ideally to the whole contour before fitting the ellipse

from math import acos, cos, sin, pi, sqrt, atan2, radians, degrees
import cv2
import numpy as np

from droplet import Droplet

DBG_NONE = 0x0
DBG_SHOW_CONTOURS = 0x1
DBG_DRAW_ELLIPSE = 0x2
DBG_DRAW_TAN_ANGLE = 0x4
DEBUG = DBG_NONE

USE_GPU = False

class ContourError(Exception):
    pass


def evaluate_droplet(img, y_base, mask=None) -> Droplet:
    """ 
    Analyze an image for a droplet and determine the contact angles

    :param img: the image to be evaluated as np.ndarray
    :param y_base: the y coordinate of the surface the droplet sits on
    :returns: a Droplet() object with all the informations
    """
    drplt = Droplet()
    # crop img from baseline down (contains no useful information)
    crop_img = img[:y_base,:]
    shape = img.shape
    height = shape[0]
    width = shape[1]
    if USE_GPU:
        crop_img = cv2.UMat(crop_img)
    # calculate thrresholds
    thresh_high, thresh_im = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_low = 0.5*thresh_high
    # thresh_high = 179
    # thresh_low = 76

    # values only for 8bit images!

    # apply canny filter to image
    # FIXME adjust canny params, detect too much edges
    bw_edges = cv2.Canny(crop_img, thresh_low, thresh_high)
    
    # FIXME block detection of syringe
    if (not mask is None):
        x,y,w,h = mask
        bw_edges[y:y+h, x:x+w] = 0

    #find all contours in image and select the "longest", https://docs.opencv.org/3.4/d3/dc0/group__imgproc__shape.html#ga17ed9f5d79ae97bd4c7cf18403e1689a
    # https://docs.opencv.org/3.4/d9/d8b/tutorial_py_contours_hierarchy.html 
    # https://docs.opencv.org/3.4/d3/dc0/group__imgproc__shape.html#ga4303f45752694956374734a03c54d5ff
    # contours, hierarchy = cv2.findContours(bw_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    contours, hierarchy = cv2.findContours(bw_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if len(contours) == 0:
        raise ContourError('No contours found!')
    edge = max(contours, key=cv2.contourArea)

    if USE_GPU:
        # fetch contours from gpu memory
        # cntrs = [cv2.UMat.get(c) for c in contours]
        edge = cv2.UMat.get(edge)
        if DEBUG & DBG_SHOW_CONTOURS:
            # img = cv2.drawContours(img,cntrs,-1,(100,100,255),2)
            img = cv2.drawContours(img,edge,-1,(255,0,0),2)

    # apply ellipse fitting algorithm to droplet
    (x0,y0), (maj_ax,min_ax), phi_deg = cv2.fitEllipse(edge)
    phi = radians(phi_deg)
    a = maj_ax/2
    b = min_ax/2

    # diesen fit vllt zum laufen bringen https://scikit-image.org/docs/0.15.x/api/skimage.measure.html
    #points = edge.reshape(-1,2)
    #points[:,[0,1]] = points[:,[1,0]]
    # ell = EllipseModel()
    # if not ell.estimate(points): raise RuntimeError('Couldn\'t fit ellipse')
    # x0, y0, a, b, phi = ell.params
    # maj_ax = 2*a
    # min_ax = 2*b
    # phi_deg = degrees(phi)

    if DEBUG & DBG_DRAW_ELLIPSE:
        img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), int(round(phi*180/pi)), 0, 360, (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        #img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), 0, 0, 360, (0,0,255), thickness=1, lineType=cv2.LINE_AA)

    # calculate intersections of ellipse with baseline
    intersection = calc_intersection_line_ellipse((x0,y0,a,b,phi),(0,y_base))
    if intersection is None:
        raise ContourError('No intersections found')
    x_int_l = min(intersection)
    x_int_r = max(intersection)

    foc_len = sqrt(abs(a**2 - b**2))

    # calc slope and angle of tangent at intersections
    m_t_l = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_l, y_base)
    m_t_r = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_r, y_base)

    # calc angle of inclination of tangents
    angle_l = (pi - atan2(m_t_l,1)) % pi
    angle_r = (atan2(m_t_r,1) + pi) % pi

    # calc area of droplet
    area = calc_area_of_droplet((x_int_l, x_int_r), (x0,y0,a,b,phi), y_base)

    # calc height of droplet
    drplt_height = calc_height_of_droplet((x0,y0,a,b,phi), y_base)
    
    # write values to droplet object
    drplt.angle_l = angle_l
    drplt.angle_r = angle_r
    drplt.maj = maj_ax
    drplt.min = min_ax
    drplt.center = (x0, y0)
    drplt.phi = phi
    drplt.tilt_deg = phi_deg
    drplt.tan_l_m = m_t_l
    drplt.tan_r_m = m_t_r
    drplt.line_l = (x_int_l - y_base/m_t_l, 0, x_int_l + (height - y_base)/m_t_l, height)
    drplt.line_r = (x_int_r - y_base/m_t_r, 0, x_int_r + (height - y_base)/m_t_r, height)
    drplt.int_l = (x_int_l, y_base)
    drplt.int_r = (x_int_r, y_base)
    drplt.foc_pt1 = (x0 + foc_len*cos(phi), y0 + foc_len*sin(phi))
    drplt.foc_pt2 = (x0 - foc_len*cos(phi), y0 - foc_len*sin(phi))
    drplt.base_diam = x_int_r - x_int_l
    drplt.area = area
    drplt.height = drplt_height
    drplt.is_valid = True

    if DEBUG & DBG_DRAW_TAN_ANGLE:
        # painting
        y_int = int(round(y_base))
        img = cv2.line(img, (int(round(x_int_l - (y_int/m_t_l))), 0), (int(round(x_int_l + ((height - y_int)/m_t_l))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.line(img, (int(round(x_int_r - (y_int/m_t_r))), 0), (int(round(x_int_r + ((height - y_int)/m_t_r))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.ellipse(img, (int(round(x_int_l)),y_int), (20,20), 0, 0, -int(round(angle_l*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.ellipse(img, (int(round(x_int_r)),y_int), (20,20), 0, 180, 180 + int(round(angle_r*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.line(img, (0,y_int), (width, y_int), (255,0,0), thickness=2, lineType=cv2.LINE_AA)
        img = cv2.putText(img, '<' + str(round(angle_l*180/pi,1)), (5,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
        img = cv2.putText(img, '<' + str(round(angle_r*180/pi,1)), (width - 80,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))

    #return drplt#, img

def calc_intersection_line_ellipse(ellipse_pars, line_pars):
    """
    calculates intersection(s) of an ellipse with a horizontal line

    :param ellipse_pars: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param line_pars: tuple of (m,t): m is the slope and t is intercept of the intersecting line
    :returns: x-coordinate(s) of intesection as list or float or none if none found
    """
    ## -->> http://quickcalcbasic.com/ellipse%20line%20intersection.pdf
    (x0, y0, h, v, phi) = ellipse_pars
    (m, t) = line_pars
    y = t - y0
    try:
        a = v**2 * cos(phi)**2 + h**2 * sin(phi)**2
        b = 2*y*cos(phi)*sin(phi) * (v**2 - h**2)
        c = y**2 * (v**2 * sin(phi)**2 + h**2 * cos(phi)**2) - (h**2 * v**2)
        det = b**2 - 4*a*c
        if det > 0:
            x1: float = (-b - sqrt(det))/(2*a) + x0
            x2: float = (-b + sqrt(det))/(2*a) + x0
            return x1,x2
        elif det == 0:
            x: float = (-b / (2*a)) + x0
            return x
        else:
            return None
    except Exception as ex:
        raise ex

def calc_slope_of_ellipse(ellipse_pars, x, y):
    """
    calculates slope of tangent at point x,y, the point needs to be on the ellipse!

    :param ellipse_params: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param x: x-coord where the slope will be calculated
    :returns: the slope of the tangent
    """
    (x0, y0, a, b, phi) = ellipse_pars
    # transform to non-rotated ellipse centered to origin
    x_rot = (x - x0)*cos(phi) - (y - y0)*sin(phi)
    y_rot = (x - x0)*sin(phi) + (y - y0)*cos(phi)
    # general line equation for tangent Ax + By = C
    tan_a = x_rot/a**2
    tan_b = y_rot/b**2
    # tan_c = 1
    #rotate tangent line back to angle of the rotated ellipse
    tan_a_r = tan_a*cos(phi) + tan_b*sin(phi)
    tan_b_r = tan_b*cos(phi) - tan_a*sin(phi)
    #calc slope of tangent m = -A/B
    m_tan = - (tan_a_r / tan_b_r)

    return m_tan

def calc_area_of_droplet(line_intersections, ellipse_pars, y_int) -> float:
    """
    calculate the are of the droplet by approximating the area of the ellipse cut off at the baseline

    :param ellipse_params: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param y_int: y coordinate of baseline
    :returns: area of droplet in px^2 
    """
    (x0, y0, a, b, phi) = ellipse_pars
    (x1,x2) = line_intersections
    # calculate the angles of the vectors from ellipse origin to the intersections
    dy = abs(y_int - y0)
    dx1 = abs(x1 - x0)
    ang_x1 = acos(dx1 / sqrt(dy**2 + dx1**2))
    dx2 = abs(x2 - x0) 
    ang_x2 = acos(dx2 / sqrt(dy**2 + dx2**2))
    if y_int > y0:
        ang_x1 += pi
        ang_x2 -= pi/2
    else:
        ang_x1 = pi - ang_x1
    # adjust for ellipse tilt
    ang_x1 -= phi
    ang_x2 -= phi

    # calculate the surface area of the segment between x1 and x2, https://rechneronline.de/pi/elliptical-sector.php
    dphi = ang_x1 - ang_x2
    sec_area = a*b/2 * (dphi - atan2( (b-a)*sin(2*ang_x1), (a+b+(b-a)*cos(2*ang_x1) ) + atan2( (b-a)*sin(2*ang_x2), (a+b+(b-a)*cos(2*ang_x2)) )))
    # add or remove triangle enclosed by x1, x2 and origin of ellipse to get area of ellipse above baseline
    if y_int > y0:
        area = sec_area + (dy*(dx1/2 + dx2/2))
    else:
        area = sec_area - (dy*(dx1/2 + dx2/2))

    return area

def calc_height_of_droplet(ellipse_pars, y_base) -> float:
    """
    calculate the height of the droplet by measuring distance between baseline and top of ellipse

    :param ellipse_params: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param y_base: y coordinate of baseline
    :returns: height of ellipse in px
    """
    (x0, y0, a, b, phi) = ellipse_pars
    # https://math.stackexchange.com/questions/91132/how-to-get-the-limits-of-rotated-ellipse
    # lowspot of ellipse ( topspot in image ), ell_origin - ell_height
    y_low = y0 - sqrt(a**2 * sin(phi)**2 + b**2 * cos(phi)**2)
    # actual height, baseline - lowspot
    droplt_height = y_base - y_low
    return droplt_height

# for testing purposes:
if __name__ == "__main__":
    im = cv2.imread('untitled1.png', cv2.IMREAD_GRAYSCALE)
    im = np.reshape(im, im.shape + (1,) )
    try:
        drp = evaluate_droplet(im, 250, (10,10,50,50))
    except Exception as ex:
        print(ex)
    cv2.imshow('Test',im)
    cv2.waitKey(0)