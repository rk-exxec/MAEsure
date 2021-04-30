#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2021  Raphael Kriegl

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
from typing import Tuple
import cv2
import numpy as np
import skimage.measure

from droplet import Droplet

DBG_NONE = 0x0
DBG_SHOW_CONTOURS = 0x1
DBG_DRAW_ELLIPSE = 0x2
DBG_DRAW_TAN_ANGLE = 0x4
DBG_ALL = 0x7
DEBUG = DBG_NONE

USE_GPU = False

class ContourError(Exception):
    pass


def evaluate_droplet(img, y_base, mask: Tuple[int,int,int,int] = None) -> Droplet:
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
    
    # block detection of syringe
    if (not mask is None):
        x,y,w,h = mask
        bw_edges[:, x:x+w] = 0
        #img[:, x:x+w] = 0
        masked = True
    else:
        masked = False

    edge = find_contour(bw_edges, masked)

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
    r2 = calc_regr_score_r2((x0,y0,a,b,phi), edge)

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

    if intersection is None or not isinstance(intersection, list):
        raise ContourError('No valid intersections found')
    x_int_l = min(intersection)
    x_int_r = max(intersection)

    foc_len = sqrt(abs(a**2 - b**2))

    # calc slope and angle of tangent at intersections
    m_t_l = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_l, y_base)
    m_t_r = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_r, y_base)

    # calc angle from inclination of tangents
    angle_l = (pi - atan2(m_t_l,1)) % pi
    angle_r = (atan2(m_t_r,1) + pi) % pi

    # calc area of droplet
    area = calc_area_of_droplet((x_int_l, x_int_r), (x0,y0,a,b,phi), y_base)

    # calc height of droplet
    drplt_height = calc_height_of_droplet((x0,y0,a,b,phi), y_base)
    
    # write values to droplet object
    drplt.angle_l = degrees(angle_l)
    drplt.angle_r = degrees(angle_r)
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
    drplt.r2 = r2
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
        img = cv2.putText(img, 'GOF: ' + str(round(r2,3)), (10, 20), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))

    #return drplt#, img

def find_contour(img, is_masked):
    """searches for contours and returns the ones with largest bounding rect

    :param img: grayscale or bw image
    :param is_masked: if image was masked
    :type is_masked: bool
    :raises ContourError: if no contours are detected
    :return: if not is_masked: contour with largest bounding rect

            else: the two contours with largest bounding rect merged
    :rtype: [type]
    """
    # find all contours in image, https://docs.opencv.org/3.4/d3/dc0/group__imgproc__shape.html#ga17ed9f5d79ae97bd4c7cf18403e1689a
    # https://docs.opencv.org/3.4/d9/d8b/tutorial_py_contours_hierarchy.html 
    # https://docs.opencv.org/3.4/d3/dc0/group__imgproc__shape.html#ga4303f45752694956374734a03c54d5ff
    # contours, hierarchy = cv2.findContours(bw_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if len(contours) == 0:
        raise ContourError('No contours found!')
    # edge = max(contours, key=cv2.contourArea)

    cntr_area_list = []
    for cont in contours:
        x,y,w,h = cv2.boundingRect(cont)
        # store contour, area of bounding rect and bounding rect in array
        cntr_area_list.append([cont, w*h, x, y, x+w, y+h])
    # sort contours by bounding rect area
    cntr_area_list_sorted = sorted(cntr_area_list, key=lambda item: item[1])
    
    if is_masked:
        # select largest 2 non overlapping contours, assumes mask splits largest contour in the middle
        rects = [elem[2:] for elem in cntr_area_list_sorted[-2:]]
        largest_conts = [elem[0] for elem in cntr_area_list_sorted[-2:]]

        #check if second largest contour is not from inside the droplet by checking overlap of bounding rects
        BR = rects[-1] # biggest rect
        SR = rects[0] # slightly smaller rect
        # check if smaller rect overaps with larger rect
        if (BR[2] < SR[0] or BR[0] > SR[2] or BR[1] > SR[3] or BR[3] < SR[1]):
            # if not both rects are valid droplet contours, merge them
            contour = np.concatenate((largest_conts[0], largest_conts[1]))
        else:
            # else only biggest is valid droplet contour
            contour = cntr_area_list_sorted[-1][0]
    else:
        # contour with largest area
        contour = cntr_area_list_sorted[-1][0]
    return contour

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
            return [x1,x2]
        elif det == 0:
            x: float = (-b / (2*a)) + x0
            return [x]
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
    x_rot = (x - x0)*cos(phi) + (y - y0)*sin(phi)
    y_rot = (y - y0)*cos(phi) - (x - x0)*sin(phi)
    # general line equation for tangent Ax + By = C
    tan_a = x_rot/a**2
    tan_b = y_rot/b**2
    # tan_c = 1
    #rotate tangent line back to angle of the rotated ellipse
    tan_a_r = tan_a*cos(phi) - tan_b*sin(phi)
    tan_b_r = tan_b*cos(phi) + tan_a*sin(phi)
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

def calc_goodness_of_fit(ellipse_pars, contour) -> float:
    """calculates the goodness of the ellipse fit to the contour
    https://answers.opencv.org/question/20521/how-do-i-get-the-goodness-of-fit-for-the-result-of-fitellipse/

       if point (x,y) is on ellipse with axes a,b the following equation is true:
           (x/a)^2 + (y/b)^2 = 1

        goodness of fit is calculated as sum( abs( (x/a)^2 + (y/b)^2 - 1 ) )  

    -----
    :param ellipse_pars: ellipse parameters x0,y0,a,b,phi
    :param contour: contour the ellipse was fitted to
    :return: goodness of fit, smaller is better
    """
    (x0, y0, a, b, phi) = ellipse_pars

    cosphi = cos(phi)
    sinphi = sin(phi)

    def calc(point):
        x,y = point[0]
        # transform to non-rotated ellipse centered to origin
        x_rot = (x - x0)*cosphi + (y - y0)*sinphi
        y_rot = (y - y0)*cosphi - (x - x0)*sinphi
        # calculate difference to point on ellipse and add to sum
        return abs((x_rot/a)**2 + (y_rot/b)**2 - 1)

    output = [calc(point) for point in contour]
    gof = np.mean(output)
    return gof

def calc_regr_score_r2(ellipse_pars, contour) -> float:
    """calculates the coefficient of determination R²
    https://en.wikipedia.org/wiki/Coefficient_of_determination

    -----
    :param ellipse_pars: ellipse parameters x0,y0,a,b,phi
    :param contour: contour the ellipse was fitted to
    :return: R²: 0 worst, 1 best, other: wrong fit model!
    """
    (x0, y0, a, b, phi) = ellipse_pars
    data = np.reshape(contour,[-1,2])
    ell = skimage.measure.EllipseModel()
    ell.params = ellipse_pars
    cosphi = cos(phi)
    sinphi = sin(phi)
    xm, ym = np.mean(data, axis=0)
    sq_sum_res = sum(ell.residuals(data))

    def calc_sq_sum(point):
        xi,yi = point
        return np.sqrt((xi - xm)**2 + (yi - ym)**2)

    #sq_sum_tot = sum(np.linalg.norm(data,axis=1))
    sq_sum_tot = sum([calc_sq_sum(point) for point in data])

    r2 = 1 - sq_sum_res/sq_sum_tot

    return r2


# for testing purposes:
if __name__ == "__main__":
    im = cv2.imread('untitled1.png', cv2.IMREAD_GRAYSCALE)
    im = np.reshape(im, im.shape + (1,) )
    (h,w,d) = np.shape(im)
    try:
        drp = evaluate_droplet(im, 250, (int(w/2-40), 0, 80, h))
    except Exception as ex:
        print(ex)
    cv2.imshow('Test',im)
    cv2.waitKey(0)