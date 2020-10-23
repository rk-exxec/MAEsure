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

from math import asin, copysign, cos, sin, atan, pi, sqrt, tan, atan2, radians, degrees
import cv2
DEBUG = 2
USE_GPU = True
class Droplet():
    def __init__(self):
        self.is_valid = False
        self.angle_l = 0
        self.angle_r = 0
        self.center = (0,0)
        self.maj = 0
        self.min = 0
        self.phi = 0.0
        self.tilt_deg = 0
        self.foc_pt1 = (0,0)
        self.foc_pt2 = (0,0)
        self.tan_l_m = 0
        self.int_l = (0,0)
        self.line_l = (0,0,0,0)
        self.tan_r_m = 0
        self.int_r = (0,0)
        self.line_r = (0,0,0,0)
        self.base_diam = 0
        
# BUG tangent slope not correct when ellipse tall and few points to fit!!
def evaluate_droplet(img, y_base) -> Droplet:
    drplt = Droplet()
    crop_img = img[:y_base,:]
    shape = img.shape
    height = shape[0]
    width = shape[1]
    if USE_GPU:
        crop_img = cv2.UMat(crop_img)
    # calculate thrresholds
    #thresh_high, thresh_im = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #thresh_low = 0.5*thresh_high
    # values only for 8bit images!
    bw_edges = cv2.Canny(crop_img, 76, 179)

   # cv2.imshow('Canny',bw_edges)
    #input('')
    contours, hierarchy = cv2.findContours(bw_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    if len(contours) == 0:
        raise ValueError('No contours found!')

    edge = max(contours, key=cv2.contourArea)
    #edge = contours[0]
    (x0,y0), (maj_ax,min_ax), phi_deg = cv2.fitEllipse(edge)

    phi = radians(phi_deg) # to radians
    a = maj_ax/2
    b = min_ax/2

    intersection = calc_intersection_line_ellipse((x0,y0,a,b,phi),(0,y_base))
    if intersection is None:
        raise ValueError('No intersections found')

    x_int_l = min(intersection)
    x_int_r = max(intersection)

    foc_len = sqrt(abs(a**2 - b**2))

    # calc slope and angle of tangent
    m_t_l = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_l, y_base)
    angle_l = pi - atan2(m_t_l,1)
 
    m_t_r = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_r, y_base)
    angle_r = atan2(m_t_r,1) + pi

    drplt.angle_l = angle_l
    drplt.angle_r = angle_r
    drplt.maj = maj_ax
    drplt.min = min_ax
    drplt.center = (x0, y0)
    drplt.phi = phi
    drplt.tilt_deg = phi_deg
    drplt.tan_l_m = m_t_l
    drplt.tan_r_m = m_t_r
    drplt.line_l = (int(round(x_int_l - (int(round(y_base))/m_t_l))), 0, int(round(x_int_l + ((height - int(round(y_base)))/m_t_l))), int(round(height)))
    drplt.line_r = (int(round(x_int_r - (int(round(y_base))/m_t_r))), 0, int(round(x_int_r + ((height - int(round(y_base)))/m_t_r))), int(round(height)))
    drplt.int_l = (x_int_l, y_base)
    drplt.int_r = (x_int_r, y_base)
    drplt.foc_pt1 = (x0 + foc_len*cos(phi), y0 + foc_len*sin(phi))
    drplt.foc_pt2 = (x0 - foc_len*cos(phi), y0 - foc_len*sin(phi))
    drplt.base_diam = x_int_r - x_int_l
    drplt.is_valid = True

    if DEBUG > 0:
        if USE_GPU:
            contours = [cv2.UMat.get(c) for c in contours]
            edge = cv2.UMat.get(edge)
        img = cv2.drawContours(img,contours,-1,(100,100,255),2)
        img = cv2.drawContours(img,edge,-1,(255,0,0),2)
    if DEBUG > 1:
        img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), int(round(phi*180/pi)), 0, 360, (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), 0, 0, 360, (0,0,255), thickness=1, lineType=cv2.LINE_AA)
        y_int = int(round(y_base))
        img = cv2.line(img, (int(round(x_int_l - (y_int/m_t_l))), 0), (int(round(x_int_l + ((height - y_int)/m_t_l))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.line(img, (int(round(x_int_r - (y_int/m_t_r))), 0), (int(round(x_int_r + ((height - y_int)/m_t_r))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.ellipse(img, (int(round(x_int_l)),y_int), (20,20), 0, 0, -int(round(angle_l*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.ellipse(img, (int(round(x_int_r)),y_int), (20,20), 0, 180, 180 + int(round(angle_r*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
        img = cv2.line(img, (0,y_int), (width, y_int), (255,0,0), thickness=2, lineType=cv2.LINE_AA)
        img = cv2.putText(img, '<' + str(round(angle_l*180/pi,1)), (5,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
        img = cv2.putText(img, '<' + str(round(angle_r*180/pi,1)), (width - 80,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))

    return drplt#, img

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
            x: float = -b / (2*a)
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
    if b > a:
        a,b = b,a
    else:
        phi -= pi/4
    # transform to non-rotated ellipse
    x_rot = (x - x0)*cos(phi) + (y - y0)*sin(phi)
    y_rot = (x - x0)*sin(phi) + (y - y0)*cos(phi)
    m_rot = (b**2 * x_rot)/(a**2 * y_rot) # slope of tangent to unrotated ellipse
    #rotate tangent line back to angle of the rotated ellipse
    m_tan = tan(atan2(m_rot,1) + phi)

    return m_tan

if __name__ == "__main__":
    im = cv2.imread('untitled1.png')
    # any value below 250 is just the droplet without the substrate
#     This is the result when I choose the surface to be at y=62:  
# [![Completely wrong][2]][2]
    drp = evaluate_droplet(im, 250)
    cv2.imshow('Test',im)
    cv2.waitKey(0)