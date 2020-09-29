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

#from fit_ellipse import fit_ellipse
import math
import cv2

#from sympy import Ellipse, Line, geometry, Line2D

class Droplet():
    def __init__(self):
        self.angle_l = 0
        self.angle_r = 0
        self.center = (0,0)
        self.maj = 0
        self.min = 0
        self.phi = 0
        self.foc_pt1 = (0,0)
        self.foc_pt2 = (0,0)
        self.tan_l_m = 0
        self.int_l = (0,0)
        self.tan_r_m = 0
        self.int_r = (0,0)
        self.base_diam = 0

def evaluate_droplet(img, y_base) -> Droplet:
    drplt = Droplet()
    crop_img = img[:y_base,:]
    height, width, channels = img.shape
    img = cv2.UMat(img)
    crop_img = cv2.UMat(crop_img)
    # calculate thrresholds
    #thresh_high, thresh_im = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #thresh_low = 0.5*thresh_high
    # values only for 8bit images!
    bw_edges = cv2.Canny(crop_img, 76, 179)

   # cv2.imshow('Canny',bw_edges)
    #input('')
    contours, hierarchy = cv2.findContours(bw_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    edge = max(contours, key=cv2.contourArea)
    #edge = contours[0]
    (x0,y0),(MA,ma),phi = cv2.fitEllipse(edge)
    phi = phi * math.pi / 180 # to radians
    #(a,b,x0,y0,phi) = fit_ellipse(pxls_x,pxls_y)
    pa = MA/2
    pb = ma/2
    a = pa**2 * math.sin(phi)**2 + pb**2*math.cos(phi)**2
    b = 2*(pb**2 - pa**2)*math.sin(phi)*math.cos(phi)
    c = pa**2 * math.cos(phi)**2 + pb**2*math.sin(phi)**2
    d = -2*a*x0 - b*y0
    e = -b*x0 -2*c*y0
    f = a*x0**2 + b*x0*y0 + c*y0**2 - pa**2*pb**2

    y_int = float(y_base)
    if a != 0:
        tmp = b**2*y_int**2 + 2*b*d*y_int + d**2 - 4*a*c*y_int**2 - 4*a*e*y_int - 4*a*f
        if tmp >= 0:
            intersection = [-(d + b*y_int + math.sqrt(tmp))/(2*a), -(d + b*y_int - math.sqrt(tmp))/(2*a)]
        else:
            raise ValueError('No Intersection found!')
        
    else:
        raise ValueError('Intersection equation is not valid for given parameters!')
    
    x_int_l = min(intersection)
    x_int_r = max(intersection)

    foc_len = math.sqrt(abs((MA/2)**2 - (ma/2)**2))
    # find left focal point and get y coord
    drplt.foc_pt1 = (x0 + foc_len*math.cos(phi), y0 + foc_len*math.sin(phi))
    drplt.foc_pt2 = (x0 - foc_len*math.cos(phi), y0 - foc_len*math.sin(phi))
    if drplt.foc_pt1[0] < drplt.foc_pt2[0]:
        y_foc = drplt.foc_pt1[1]
    else:
        y_foc = drplt.foc_pt2[1]


    # precalculations for slope of the tangents
    m_pre_l = (x_int_l*b**2 + e*b - 2*c*d - 4*a*c*x_int_l)/math.sqrt(b**2*x_int_l**2 + 2*b*e*x_int_l + e**2 - 4*a*c*x_int_l**2 - 4*c*d*x_int_l - 4*c*f)
    m_pre_r = (x_int_r*b**2 + e*b - 2*c*d - 4*a*c*x_int_r)/math.sqrt(b**2*x_int_r**2 + 2*b*e*x_int_r + e**2 - 4*a*c*x_int_r**2 - 4*c*d*x_int_r - 4*c*f)

    if y_base > y_foc:
        m_pre_l = -m_pre_l
        m_pre_r = -m_pre_r
    # if ellipse axes were wrong everything is mirrored
    # if ax_swap:
    #     m_pre_l = -m_pre_l
    #     m_pre_r = -m_pre_r

    # calc slope and angle of tangent
    m_t_l = -(b - m_pre_l)/(2*c)
    angle_l = math.atan(1/m_t_l) + math.pi/2
 
    m_t_r = -(b - m_pre_r)/(2*c)
    angle_r = math.atan(-1/m_t_r) + math.pi/2

    # ell = Ellipse((x0,y0), hradius=MA/2, vradius=ma/2).rotate(phi)
    # lin = Line((0,y_base), slope=0)
    # intersections = geometry.intersection(ell,lin)
    # if len(intersections) == 0:
    #     raise ValueError('No intersections found')
    # int_l = ell.tangent_lines(intersections[0])
    # int_r = ell.tangent_lines(intersections[1])

    drplt.angle_l = angle_l
    drplt.angle_r = angle_r
    drplt.maj = MA
    drplt.min = ma
    drplt.center = (x0, y0)
    drplt.phi = phi
    drplt.tan_l_m = m_t_l
    drplt.tan_r_m = m_t_r
    drplt.int_l = (x_int_l, y_base)
    drplt.int_r = (x_int_r, y_base)
    
    drplt.base_diam = x_int_r - x_int_l

    # TODO
    # test cv2 ellipse plot, line plot etc
    img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(pa)),int(round(pb))), int(round(phi*180/math.pi)), 0, 360, (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    y_int = int(round(y_int))
    img = cv2.line(img, (int(round(x_int_l - (y_int/m_t_l))), 0), (int(round(x_int_l + ((height - y_int)/m_t_l))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    img = cv2.line(img, (int(round(x_int_r - (y_int/m_t_r))), 0), (int(round(x_int_r + ((height - y_int)/m_t_r))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    img = cv2.ellipse(img, (int(round(x_int_l)),y_int), (20,20), 0, 0, -int(round(angle_l*180/math.pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    img = cv2.ellipse(img, (int(round(x_int_r)),y_int), (20,20), 0, 180, 180 + int(round(angle_r*180/math.pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    img = cv2.line(img, (0,y_int), (width, y_int), (255,0,0), thickness=2, lineType=cv2.LINE_AA)
    img = cv2.putText(img, '<' + str(round(angle_l*180/math.pi,1)), (5,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
    img = cv2.putText(img, '<' + str(round(angle_r*180/math.pi,1)), (width - 80,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
    cv2.imshow('Heyho',img)
    cv2.waitKey(0)
    return drplt



    


