#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2020  Raphael Kriegl

#     this program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     this program is distributed in the hope that it will be useful,
#     but WIthOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Droplet eval function

from math import cos, sin, atan, pi, sqrt, tan, atan2
import cv2

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

def evaluate_droplet(img, y_base) -> Droplet:
    drplt = Droplet()
    crop_img = img[:y_base,:]
    shape = img.shape
    height = shape[0]
    width = shape[1]
    #img = cv2.UMat(img)
    #crop_img = cv2.UMat(crop_img)
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
    (x0,y0),(MA,ma),phi = cv2.fitEllipse(edge)
    phi = phi * pi / 180 # to radians
    #(a,b,x0,y0,phi) = fit_ellipse(pxls_x,pxls_y)
    a = MA/2
    b = ma/2

    intersection = calc_intersection_line_ellipse((x0,y0,a,b,phi),(0,y_base))
    if intersection is None:
        raise ValueError('No intersections found')

    x_int_l = min(intersection)
    x_int_r = max(intersection)

    foc_len = sqrt(abs(a**2 - b**2))

    # calc slope and angle of tangent
    m_t_l = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_l, y_base)
    angle_l = atan2(1,m_t_l) + pi/2
 
    m_t_r = calc_slope_of_ellipse((x0,y0,a,b,phi), x_int_r, y_base)
    angle_r = atan2(-1,m_t_r) + pi/2

    drplt.angle_l = angle_l
    drplt.angle_r = angle_r
    drplt.maj = MA
    drplt.min = ma
    drplt.center = (x0, y0)
    drplt.phi = phi
    drplt.tilt_deg = phi * 180/pi
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

    # img = cv2.ellipse(img, (int(round(x0)),int(round(y0))), (int(round(a)),int(round(b))), int(round(phi*180/pi)), 0, 360, (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    # y_int = int(round(y_base))
    # img = cv2.line(img, (int(round(x_int_l - (y_int/m_t_l))), 0), (int(round(x_int_l + ((height - y_int)/m_t_l))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    # img = cv2.line(img, (int(round(x_int_r - (y_int/m_t_r))), 0), (int(round(x_int_r + ((height - y_int)/m_t_r))), int(round(height))), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    # img = cv2.ellipse(img, (int(round(x_int_l)),y_int), (20,20), 0, 0, -int(round(angle_l*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    # img = cv2.ellipse(img, (int(round(x_int_r)),y_int), (20,20), 0, 180, 180 + int(round(angle_r*180/pi)), (255,0,255), thickness=1, lineType=cv2.LINE_AA)
    # img = cv2.line(img, (0,y_int), (width, y_int), (255,0,0), thickness=2, lineType=cv2.LINE_AA)
    # img = cv2.putText(img, '<' + str(round(angle_l*180/pi,1)), (5,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
    # img = cv2.putText(img, '<' + str(round(angle_r*180/pi,1)), (width - 80,y_int-5), cv2.FONT_HERSHEY_COMPLEX, .5, (0,0,0))
    # try:
    #     img = cv2.UMat.get()
    # except Exception as ex:
    #     print(ex)
    #cv2.imshow('Test',img)
    #cv2.waitKey(0)
    return drplt#, img

def calc_general_ell_params(x0, y0, pa, pb, phi):
    """
    calculates general ellipse params from major, minor axis and rotation  
    :param x0: x-coord of ellise center  
    :param y0: y-coord of ellipse center  
    :param pa: semi-major axis (0.5 major axis)  
    :param pb: semi-minor axis (0.5 minor axis)  
    :param phi: tilt of major axis relative to x axis  
    :returns: coefficients a,b,c,d,e,f for the general ellipse equation ax^2 + bxy + cy^2 + dx + ey + f = 0
    """
    a = pa**2 * sin(phi)**2 + pb**2*cos(phi)**2
    b = 2*(pb**2 - pa**2)*sin(phi)*cos(phi)
    c = pa**2 * cos(phi)**2 + pb**2*sin(phi)**2
    d = -2*a*x0 - b*y0
    e = -b*x0 - 2*c*y0
    f = a*x0**2 + b*x0*y0 + c*y0**2 - pa**2*pb**2
    return a, b, c, d, e, f

def calc_intersection_line_ellipse(ellipse_pars, line_pars):
    """
    calculates intersection(s) of an ellipse with a line  
    :param ellipse_pars: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis  
    :param line_pars: tuple of (m,t): m is the slope and t is intercept of the intersecting line  
    :returns: x-coordinate(s) of intesection as list or float or none if none found
    """
    (x0, y0, a, b, phi) = ellipse_pars
    (m, t) = line_pars
    # solutions for problem e(x) == f(x), where e(x) is the canonical eqn for a general ellipse and f(x) is the eqn of the intersecting line
    # e(x,y) = ((((x-x0)*cos(phi) + (y-y0)*sin(phi))**2) / a**2) + ((((x-x0)*sin(phi) - (y-y0)*cos(phi))**2) / b**2) == 1
    # f(x) = 0*x + t
    num = 2*a*b*sqrt((b**2 - a**2)*cos(phi)**2 + a**2 - (t-y0)**2) \
        + (b**2 - a**2)*(2*x0*cos(phi)**2 + (y0 - t)*sin(2*phi))
    den = 2*(b**2*cos(phi)**2 + a**2*sin(phi)**2)
    try:
        intersection = [(2*a**2*x0 + num) / den, (2*a**2*x0 - num) / den]
    except ZeroDivisionError as zde:
        print('No intersections found')
        return None
    except Exception as ex:
        raise ex
    if intersection[0] == intersection[1]: 
        return intersection[0]
    else:
        return intersection

    # eqn if slope is not 0
    # num = 2*a*b*sqrt(m**2*(b**2 - x0**2) + (1-m**2)*(b**2 - a**2)*cos(phi)**2 + m*(2*x0*y0 + (b**2 - a**2)*sin(2*phi) - t*x0) + (t + y0)**2 + a**2)\
    #   + (b**2 - a**2) * (2*(1+m*(t-y0))*cos(phi)**2 + (y0-t+m*x0)*sin(2*phi))
    # den = 2*((b**2 - a**2)*((1- m**2)*cos(phi)**2 - m*sin(2*phi)) + a**2 + b**2*m**2)
    # (2*a**2*x0 + 2*b**2*m*(y0 - t) + num)/den
    # (2*a**2*x0 + 2*b**2*m*(y0 - t) - num)/den
 
def calc_slope_of_ellipse(ellipse_pars, x, y):
    """
    calculates slope of tangent at point x,y
    :param ellipse_params: tuple of (x0,y0,a,b,phi): x0,y0 center of ellipse; a,b sem-axis of ellipse; phi tilt rel to x axis  
    :param x: x-coord where the slope will be calculated  
    :returns: the slope of the tangent 
    """
    (x0, y0, a, b, phi) = ellipse_pars
    # transform to non-rotated ellipse
    x_rot = (x - x0)*cos(phi) + (y - y0)*sin(phi)
    y_rot = (x - x0)*sin(phi) + (y - y0)*cos(phi)
    m_rot = -(x_rot/y_rot) * ((b**2)/(a**2)) # slope of tangent to unrotated ellipse
    #rotate tangent line back to angle of the rotated ellipse
    m_tan = tan(atan2(-m_rot,1) + phi)

    return m_tan

if __name__ == "__main__":
    im = cv2.imread('untitled1.png')
    drp = evaluate_droplet(im, 250)