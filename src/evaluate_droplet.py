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

import time
from typing import List, Tuple

from math import acos, cos, sin, pi, sqrt, atan2, radians, degrees

import numba as nb
import numpy as np
from pyqtgraph.graphicsItems.LegendItem import LegendItem
import skimage.measure
import cv2


from droplet import Droplet

DBG_NONE = 0x0
DBG_SHOW_CONTOURS = 0x1
DBG_DRAW_ELLIPSE = 0x2
DBG_DRAW_TAN_ANGLE = 0x4
DBG_ALL = 0x7
DEBUG = DBG_NONE

USE_GPU = False # slower somehow

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
        # if USE_GPU:
        mask_mat = np.ones([y_base, width], dtype="uint8")
        mask_mat[:, x:x+w] = 0
        
        bw_edges = cv2.bitwise_and(bw_edges, bw_edges, mask=mask_mat)
        # else:
        #     bw_edges[:, x:x+w] = 0
        #img[:, x:x+w] = 0
        masked = True
    else:
        masked = False

    if USE_GPU:
        # fetch contours from gpu memory
        # cntrs = [cv2.UMat.get(c) for c in contours]
        bw_edges = cv2.UMat.get(bw_edges)

    edge = find_contour(bw_edges, masked)

    if DEBUG & DBG_SHOW_CONTOURS:
        # img = cv2.drawContours(img,cntrs,-1,(100,100,255),2)
        img = cv2.drawContours(img,edge,-1,(255,0,0),2)

    # apply ellipse fitting algorithm to droplet
    (x0,y0), (maj_ax,min_ax), phi_deg = cv2.fitEllipse(edge)
    phi = radians(phi_deg)
    a = maj_ax/2
    b = min_ax/2

    if a == 0 or b == 0:
        raise ValueError('Malformed ellipse fit! Axis = 0')

    r2 = calc_regr_score_r2_y_only(x0,y0,a,b,phi, edge)

    if DEBUG & DBG_DRAW_ELLIPSE:
        img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), int(round(phi*180/pi)), 0, 360, (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        #img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), 0, 0, 360, (0,0,255), thickness=1, lineType=cv2.LINE_AA)

    # calculate intersections of ellipse with baseline
    intersection = calc_intersection_line_ellipse(x0,y0,a,b,phi,0,y_base)

    if intersection == []:
        raise ContourError('No valid intersections found')

    x_int_l = np.min(intersection)
    x_int_r = np.max(intersection)

    foc_len = np.sqrt(np.abs(a**2 - b**2))

    # calc slope and angle of tangent at intersections
    m_t_l = calc_slope_of_ellipse(x0,y0,a,b,phi, x_int_l, y_base)
    m_t_r = calc_slope_of_ellipse(x0,y0,a,b,phi, x_int_r, y_base)

    # calc angle from inclination of tangents
    angle_l = (pi - atan2(m_t_l,1)) % pi
    angle_r = (atan2(m_t_r,1) + pi) % pi

    # calc area of droplet
    #area = calc_area_of_droplet((x_int_l, x_int_r), (x0,y0,a,b,phi), y_base)
    volume = calc_volume_of_droplet(x0,y0,a,b,phi, y_base)

    # calc height of droplet
    drplt_height = calc_height_of_droplet(x0,y0,a,b,phi, y_base)

    #region droplet value assignment
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
    drplt.foc_pt1 = (x0 + foc_len*np.cos(phi), y0 + foc_len*np.sin(phi))
    drplt.foc_pt2 = (x0 - foc_len*np.cos(phi), y0 - foc_len*np.sin(phi))
    drplt.base_diam = x_int_r - x_int_l
    drplt.volume = volume
    drplt.height = drplt_height
    drplt.r2 = r2
    drplt.is_valid = True
    #endregion

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
        img = cv2.putText(img, 'R2: ' + str(round(r2,3)), (10, 20), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))

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
    
    return get_largest_area_contours(contours, is_masked)
    
#@nb.jit(cache=True)
def get_largest_area_contours(contours, is_masked):
    length = len(contours)
    area_list = np.zeros(length, dtype=float)
    rect_list = np.zeros([length,4], dtype=float)
    contours = np.array(contours, dtype=object)

    for idx, cont in np.ndenumerate(contours):
        x,y,w,h = cv2.boundingRect(cont)
        # store contour, area of bounding rect and bounding rect in array
        area_list[idx] = w*h
        rect_list[idx] = [x,y,w,h]

    # sort contours by bounding rect area
    #cntr_area_list_sorted = sorted(contour_area_list, key=lambda item: item[1])
    sorted_indizes = area_list.argsort()
    area_list = area_list[sorted_indizes]
    contours_sorted = contours[sorted_indizes]
    rect_list = rect_list[sorted_indizes]
    
    if is_masked and len(rect_list) > 1:
        # select largest 2 non overlapping contours, assumes mask splits largest contour in the middle
        # check if second largest contour is not from inside the droplet by checking overlap of bounding rects
        BR = rect_list[-1] # biggest rect
        SR = rect_list[-2] # slightly smaller rect
        # check if smaller rect overlaps with larger rect
        if (BR[2] < SR[0] or BR[0] > SR[2] or BR[1] > SR[3] or BR[3] < SR[1]):
            # if not, both rects are valid droplet contours, merge them
            contour = np.concatenate((contours_sorted[-2], contours_sorted[-1]))
        else:
            # else only biggest is valid droplet contour
            contour = contours_sorted[-1]
    else:
        # contour with largest area
        contour = contours_sorted[-1]
    return contour

#@nb.njit(cache=True)
def calc_intersection_line_ellipse(x0, y0, h, v, phi, m, t,) -> List[float]:
    """
    calculates intersection(s) of an ellipse with a horizontal line

    :param x0, y0, h, v, phi: x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param m, t: m is the slope and t is intercept of the intersecting line
    :returns: x-coordinate(s) of intesection as list or float or none if none found
    """
    ## -->> http://quickcalcbasic.com/ellipse%20line%20intersection.pdf
    y = t - y0
    a = v**2 * np.cos(phi)**2 + h**2 * np.sin(phi)**2
    b = 2*y*np.cos(phi)*np.sin(phi) * (v**2 - h**2)
    c = y**2 * (v**2 * np.sin(phi)**2 + h**2 * np.cos(phi)**2) - (h**2 * v**2)
    det = b**2 - 4*a*c
    retval:list[float] = []
    if det > 0:
        x1: float = (-b - np.sqrt(det))/(2*a) + x0
        x2: float = (-b + np.sqrt(det))/(2*a) + x0
        retval.append(x1)
        retval.append(x2)
    elif det == 0:
        x: float = (-b / (2*a)) + x0
        retval.append(x)

    return retval

#@nb.njit(cache=True)
def calc_slope_of_ellipse(x0, y0, a, b, phi, x, y) -> float:
    """
    calculates slope of tangent at point x,y, the point needs to be on the ellipse!

    :param x0,y0,a,b,phi: x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param x: x-coord where the slope will be calculated
    :returns: the slope of the tangent
    """
    # transform to non-rotated ellipse centered to origin
    x_rot = (x - x0)*np.cos(phi) + (y - y0)*np.sin(phi)
    y_rot = (y - y0)*np.cos(phi) - (x - x0)*np.sin(phi)
    # general line equation for tangent Ax + By = C
    tan_a = x_rot/a**2
    tan_b = y_rot/b**2
    # tan_c = 1
    #rotate tangent line back to angle of the rotated ellipse
    tan_a_r = tan_a*np.cos(phi) - tan_b*np.sin(phi)
    tan_b_r = tan_b*np.cos(phi) + tan_a*np.sin(phi)
    #calc slope of tangent m = -A/B
    m_tan = - (tan_a_r / tan_b_r)

    return m_tan

#@nb.njit(cache=True)
def calc_area_of_droplet(line_intersections, x0, y0, a, b, phi, y_int) -> float:
    """
    calculate the are of the droplet by approximating the area of the ellipse cut off at the baseline

    :param x0,y0,a,b,phi: x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param y_int: y coordinate of baseline
    :returns: area of droplet in px^2 
    """
    (x1,x2) = line_intersections
    # calculate the angles of the vectors from ellipse origin to the intersections
    dy = abs(y_int - y0)
    dx1 = abs(x1 - x0)
    ang_x1 = np.arcnp.cos(dx1 / np.sqrt(dy**2 + dx1**2))
    dx2 = abs(x2 - x0) 
    ang_x2 = np.arcnp.cos(dx2 / np.sqrt(dy**2 + dx2**2))
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
    sec_area = a*b/2 * (dphi - np.atan2( (b-a)*np.sin(2*ang_x1), (a+b+(b-a)*np.cos(2*ang_x1) ) + np.atan2( (b-a)*np.sin(2*ang_x2), (a+b+(b-a)*np.cos(2*ang_x2)) )))
    # add or remove triangle enclosed by x1, x2 and origin of ellipse to get area of ellipse above baseline
    if y_int > y0:
        area = sec_area + (dy*(dx1/2 + dx2/2))
    else:
        area = sec_area - (dy*(dx1/2 + dx2/2))

    return area

#@nb.njit(cache=True)
def calc_height_of_droplet(x0, y0, a, b, phi, y_base) -> float:
    """
    calculate the height of the droplet by measuring distance between baseline and top of ellipse

    :param x0,y0,a,b,phi: x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis
    :param y_base: y coordinate of baseline
    :returns: height of ellipse in px
    """
    # https://math.stackexchange.com/questions/91132/how-to-get-the-limits-of-rotated-ellipse
    # lowspot of ellipse ( topspot in image ), ell_origin - ell_height
    y_low = y0 - np.sqrt(a**2 * np.sin(phi)**2 + b**2 * np.cos(phi)**2)
    # actual height, baseline - lowspot
    droplt_height = y_base - y_low
    return droplt_height

#@nb.njit(cache=True)
def calc_volume_of_droplet(x0, y0, a, b, phi, y_base) -> float:
    """calculate the volume of the droplet by approximation of the ellipse to an ellipsoid

    :param ellipse_pars: ellipse fitted to the droplet
    :param y_base: baseline height
    :return: volume of droplet in px3
    :rtype: float
    """
    # cutting plane params Ax + By + Cz = D
    # transformation in same coordinate system as non rotated ellipse at origin
    rot_mat = np.array([[np.cos(-phi), -np.sin(-phi), 0.0],
                        [np.sin(-phi), np.cos(-phi), 0.0],
                        [0.0, 0.0, 1.0]] )
    ell_origin = np.array([x0, y0, 0.0])
    plane_norm_vec = np.array([0.0, 1.0, 0.0])
    plane_norm_vec = rot_mat.dot(plane_norm_vec.T).T
    plane_supp_vec = np.array([x0,y_base,0]) - ell_origin
    plane_supp_vec = rot_mat.dot(plane_supp_vec.T).T
    pA,pB,pC = plane_norm_vec
    pD = plane_supp_vec.dot(plane_norm_vec)

    # ellipsoid params a,b,c: c=a
    c = a

    # calculating volume https://math.stackexchange.com/questions/1145267/volume-of-the-smaller-region-of-ellipsoid-cut-by-plane
    frac = (np.abs(pD) / np.sqrt((pA*a)**2 + (pB*b)**2 + (pC*c)**2))
    volume = (a*b*c * pi/ 3) * (frac**3 - 3*frac + 2)
    # subtract piece above plane to get piece below plane
    volume = 4*pi/3 * a*b*c - volume
    return volume

#@nb.jit(cache=True)
def calc_goodness_of_fit(x0, y0, a, b, phi, contour) -> float:
    """calculates the goodness of the ellipse fit to the contour
    https://answers.opencv.org/question/20521/how-do-i-get-the-goodness-of-fit-for-the-result-of-fitellipse/

       if point (x,y) is on ellipse with axes a,b the following equation is true:
           (x/a)^2 + (y/b)^2 = 1

        goodness of fit is calculated as mean( abs( (x/a)^2 + (y/b)^2 - 1 ) )  

    -----
    :param ellipse_pars: ellipse parameters x0,y0,a,b,phi
    :param contour: contour the ellipse was fitted to
    :return: goodness of fit, smaller is better
    """

    cosphi = np.cos(phi)
    sinphi = np.sin(phi)

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

def calc_regr_score_r2(x0, y0, a, b, phi, contour) -> float:
    """calculates the coefficient of determination R²
    https://en.wikipedia.org/wiki/Coefficient_of_determination

    -----
    :param x0, y0, a, b, phi: ellipse parameters x0,y0,a,b,phi
    :param contour: contour the ellipse was fitted to
    :return: R²: 0 worst, 1 best, other: wrong fit model!
    """
    data = contour.reshape(-1,2)
    ell = skimage.measure.EllipseModel()
    ell.params = (x0, y0, a, b, phi)

    xm, ym = np.mean(data, axis=0)

    def calc_sq_sum(point):
        xi,yi = point
        return np.sqrt((xi - xm)**2 + (yi - ym)**2)

    #sq_sum_tot = sum(np.linalg.norm(data,axis=1))
    time_start = time.time()
    sq_sum_res = np.sum(ell.residuals(data))
    print(time.time() - time_start)
    sq_sum_tot = np.sum([calc_sq_sum(point) for point in data])
    print(time.time() - time_start)

    r2 = 1 - sq_sum_res/sq_sum_tot

    return r2

def calc_regr_score_r2_y_only(x0, y0, a, b, phi, contour) -> float:
    """
    calculates the coefficient of determination R² only from the y delta!
    https://en.wikipedia.org/wiki/Coefficient_of_determination


    -----
    :param x0, y0, a, b, phi: ellipse parameters x0,y0,a,b,phi
    :param contour: contour the ellipse was fitted to
    :return: R²: 0 worst, 1 best, other: wrong fit model!
    """
    data = contour.reshape(-1,2)
    y_data = data[:,1]

    rot_mat = np.array( [
                        [np.cos(phi)    ,   np.sin(phi)], 
                        [-np.sin(phi)   ,   np.cos(phi)] 
                        ])
    data_trans = data - np.array([x0, y0])
    data_trans = rot_mat.dot(data_trans.T).T
    sq_sum_res = calc_ss_res(data_trans, a, b).sum()

    ym = np.mean(y_data)
    sq_sum_tot = np.sum((y_data - ym)**2)

    r2 = 1 - sq_sum_res/sq_sum_tot

    return r2

# decorator makes function accept numpy array and applies calculation to every element, returns numpy array of results
@nb.guvectorize(['void(double[:], float32, float32, double[:])'], "(n),(),()->()", target='parallel')
def calc_ss_res(point, a, b, out):
    """calculate square of difference from points to points of ellipse

    :param point: point to check
    :type point: np.ndarray
    :param a,b: ellipse half-axes
    :return: (y_point - ell(x_point)) ^2
    """
    xi,yi = point
    xe = xi if np.abs(xi) < a else a * np.sign(xi) # prevent from checking points outside of ellipse
    ye = (np.sqrt(1 - (xe/a)**2) * b) * np.sign(yi)
    out[0] = (ye - yi)**2


# for testing purposes:
if __name__ == "__main__":
    im = cv2.imread('untitled1.png', cv2.IMREAD_GRAYSCALE)
    im = np.reshape(im, im.shape + (1,) )
    (h,w,d) = np.shape(im)
    dt = time.time()
    # try:
    drp = evaluate_droplet(im, 250, (int(w/2-40), 0, 80, h))
    print(time.time() - dt)
    # except Exception as ex:
    #     print(ex)
    cv2.imshow('Test',im)
    cv2.waitKey(0)