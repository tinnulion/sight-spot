#!/usr/bin/env python

"""
This file contains implementation of few auxiliary algorithms for SightSpotDetector.
"""

__author__    = 'Igor Ryabtsov aka Tinnulion'
__copyright__ = "Copyright (c) 2014"
__license__   = "Apache 2.0"
__version__   = "1.0"

import math
import sys
import numpy
import numpy.linalg
import scipy.ndimage
from PIL import Image

def eval_orgb_image(rgb_image):
    """
    Converts specified PIL image to 3d NumPy array with oRGB components.

    Parameters
    ----------
    rgb_image : PIL.Image
        Should be 3 channel RGB image with 8bit per channels
    """
    assert(len(rgb_image.shape) == 3)
    assert(rgb_image.shape[-1] == 3)
    h, w = rgb_image.shape[0:2]
    orgb_array = numpy.reshape(numpy.array(rgb_image, dtype='float32') / 255.0, (h * w, 3))
    pre_transform = numpy.array([[0.2990, 0.5870, 0.1140], [0.8660, -0.8660, 0.0], [0.5000, 0.5000, -1.0000]])
    orgb_array = numpy.dot(pre_transform, orgb_array.transpose()).transpose()
    for idx in xrange(orgb_array.shape[0]):

        # TODO FUCK ITS COULD BE FAST!!! numpy.sin() numpy[idx]
        lu, rg, yb = orgb_array[idx]
        t = math.atan2(rg, yb)
        if t >= 0.0:
            if t <= math.pi / 3:
                rt = 1.5 * t
            else:
                rt = 0.25 * math.pi + 0.75 * t
        else:
            if t >= math.pi / 3:
                rt = 1.5 * t
            else:
                rt = -0.25 * math.pi + 0.75 * t
        cos_dt = math.cos(rt - t)
        sin_dt = math.sin(rt - t)
        r_yb = cos_dt * yb - sin_dt * rg
        r_rg = sin_dt * yb + cos_dt * rg
        orgb_array[idx] = numpy.array([lu, r_rg, r_yb])
    orgb_image = orgb_array.reshape(h, w, 3)
    return orgb_image

################################################################################

def eval_saliency_map(orgb_image, small_sigma, large_sigma, params=(0.0, 0.0, 0.0)):
    """
    Calculates raw saliency map from given oRGB image.

    Parameters
    ----------
    orgb_image : ndarray
        Should be 3 channel oRGB image with float32 channels
    small_sigma : float
        Controls blur - it`s best to set ~ 1% of input image dimension.
    large_sigma : float
        Controls blur - it`s best to set ~ 20% of input image dimension.
    params : 3-tuple of floats or 'auto'
        Nonlinear correction is applied to saliency map to make it perceive better.

    Returns
    -------
    out : ndarray
        Raw saliency map of input image.
    """
    assert(len(orgb_image.shape) == 3)
    assert(orgb_image.shape[-1] == 3)
    assert(large_sigma > small_sigma)
    assert((type(params) == tuple and len(params) == 3) or params == 'auto')
    small_sigma_1 = 1 * small_sigma
    small_sigma_2 = 2 * small_sigma
    small_sigma_3 = 3 * small_sigma
    small_blur_image_1 = scipy.ndimage.gaussian_filter(orgb_image, [small_sigma_1, small_sigma_1, 0], mode='constant')
    small_blur_image_2 = scipy.ndimage.gaussian_filter(orgb_image, [small_sigma_2, small_sigma_2, 0], mode='constant')
    small_blur_image_3 = scipy.ndimage.gaussian_filter(orgb_image, [small_sigma_3, small_sigma_3, 0], mode='constant')
    large_sigma_1 = 1 * large_sigma
    large_sigma_2 = 2 * large_sigma
    large_sigma_3 = 3 * large_sigma
    large_blur_image_1 = scipy.ndimage.gaussian_filter(orgb_image, [large_sigma_1, large_sigma_1, 0], mode='constant')
    large_blur_image_2 = scipy.ndimage.gaussian_filter(orgb_image, [large_sigma_2, large_sigma_2, 0], mode='constant')
    large_blur_image_3 = scipy.ndimage.gaussian_filter(orgb_image, [large_sigma_3, large_sigma_3, 0], mode='constant')
    difference_1 = small_blur_image_1 - large_blur_image_1
    difference_2 = small_blur_image_2 - large_blur_image_2
    difference_3 = small_blur_image_3 - large_blur_image_3
    saliency_map_1 = numpy.apply_along_axis(numpy.linalg.norm, 2, difference_1) / 3.0
    saliency_map_2 = numpy.apply_along_axis(numpy.linalg.norm, 2, difference_1) / 3.0
    saliency_map_3 = numpy.apply_along_axis(numpy.linalg.norm, 2, difference_1) / 3.0
    saliency_map = (saliency_map_1 + saliency_map_2 + saliency_map_3) / 3.0
    if params == 'auto':
        a = numpy.mean(saliency_map) / 2.0
        b = numpy.std(saliency_map)
        c = 1.0
    else:
        a = float(params[0])
        b = float(params[1])
        c = float(params[2])
    saliency_map_log = 1.0 / (1.0 + numpy.exp(-(saliency_map - b) / a))
    saliency_map_adj = (1.0 - c) * saliency_map + c * saliency_map_log
    return saliency_map_adj

################################################################################

def _get_lowest_grad_pos(orgb_image, x, y):
    nx, ny = int(x + 0.5), int(y + 0.5)
    low_x, high_x = nx - 2, nx+ 3
    assert (low_x >= 0)
    assert (high_x < orgb_image.shape[1])
    low_y, high_y = ny - 2, ny + 3
    assert (low_y >= 0)
    assert (high_y < orgb_image.shape[0])
    neighbor = orgb_image[low_y:high_y, low_x:high_x]
    opt_x, opt_y = nx, ny
    min_grad = sys.float_info.max
    for dy in xrange(1, 4):
        for dx in xrange(1, 4):
            diff_x = numpy.mean(neighbor[dy-1:dy+2, dx-1] - neighbor[dy-1:dy+2, dx+1], axis=0)
            diff_y = numpy.mean(neighbor[dy-1, dx-1:dx+2] - neighbor[dy+1, dx-1:dx+2], axis=0)
            grad = numpy.linalg.norm(diff_x, 2) + numpy.linalg.norm(diff_y, 2)
            if grad < min_grad:
                opt_x, opt_y = nx + dx - 2, ny + dy - 2
                min_grad = grad
    return opt_x, opt_y

def _init_clusters_centers(orgb_image, cell_size):
    width = orgb_image.shape[1]
    height = orgb_image.shape[0]
    cell_number_x = int(float(width) / cell_size - 0.5)
    cell_number_y = int(float(height) / cell_size - 0.5)
    pad_x = 0.5 * (width - cell_number_x * cell_size)
    pad_y = 0.5 * (height - cell_number_y * cell_size)
    assert(pad_x >= 2.0)
    assert(pad_y >= 2.0)
    cluster_centers = []
    for ny in xrange(cell_number_y):
        y = ny * cell_size + pad_y
        for nx in xrange(cell_number_x):
            x = nx * cell_size + pad_x
            lx, ly = _get_lowest_grad_pos(orgb_image, x, y)
            cluster_centers.append((lx, ly, orgb_image[y, x]))
    return cluster_centers

def _do_slic_iteration(orgb_image, cell_size, labels, distances, cluster_centers, alpha):
    width = orgb_image.shape[1]
    height = orgb_image.shape[0]
    labels = -1 * numpy.ones(orgb_image.shape[:2])
    distances = sys.float_info.max * numpy.ones(orgb_image.shape[:2])

    for i in xrange(cluster_centers):
        center_x, center_y = cluster_centers[i][0], cluster_centers[i][1]
        low_x, high_x = int(center_x - cell_size), int(center_x - cell_size + 1)
        low_y, high_y = int(center_y - cell_size), int(center_y - cell_size + 1)
        low_x = max(0, low_x)
        high_x = min(width, high_x)
        low_y = max(0, low_y)
        high_y = min(height, high_y)
        window = orgb_image[low_y:high_y, low_x:high_x]

        color_diff = window - cluster_centers[i][2]
        color_dist = numpy.sqrt(numpy.sum(numpy.square(color_diff), axis=2)) / 3.0
        mesh_x = numpy.square(numpy.arange(low_x, high_x) - center_x)
        mesh_y = numpy.square(numpy.arange(low_y, high_y) - center_y)
        mesh_xx, mesh_yy = numpy.meshgrid(mesh_x, mesh_y)
        coordinate_dist = numpy.sqrt(mesh_xx + mesh_yy)
        total_dist = color_dist + alpha * coordinate_dist

        window_distances = distances[low_y:high_y, low_x:high_x]
        threshold_idx = total_dist < window_distances
        window_distances[threshold_idx] = total_dist[total_dist]
        labels[low_y:high_y, low_x:high_x] = i
        distances[low_y:high_y, low_x:high_x] = window_distances

    for i in xrange(cluster_centers):
        current_cluster_idx = (labels == i)
        current_cluster = orgb_image[current_cluster_idx]

        distnp = indnp[idx]
        self.centers[k][0:3] = np.sum(colornp, axis=0)
        sumy, sumx = np.sum(distnp, axis=0)
        self.centers[k][3:] = sumx, sumy
        self.centers[k] /= np.sum(idx)

def _restore_connectivity():
    pass

def eval_slic_map(orgb_image, cell_size, alpha, iteration_number):
    """

    """
    assert(cell_size >= 4)
    labels = -1 * numpy.ones(orgb_image.shape[:2])
    distances = sys.float_info.max * numpy.ones(orgb_image.shape[:2])
    cluster_centers = _init_clusters_centers(orgb_image, cell_size)
    for k in xrange(iteration_number):
        _do_slic_iteration(orgb_image, cell_size, labels, distances, cluster_centers, alpha)
    _restore_connectivity()
    return labels

################################################################################

def _get_heatmap_palette():
    palette = []
    s = 1.0
    v = 255.0
    for idx in xrange(256):
        h = 240.0 * (1.0 - idx / 255.0)
        hi = math.floor(h / 60.0) % 6
        f =  (h / 60.0) - math.floor(h / 60.0)
        p = v * (1.0 - s)
        q = v * (1.0 - (f * s))
        t = v * (1.0 - ((1.0 - f) * s))
        aux_dict = {
            0: (v, t, p),
            1: (q, v, p),
            2: (p, v, t),
            3: (p, q, v),
            4: (t, p, v),
            5: (v, p, q)}
        r, g, b = aux_dict[hi]
        r = int(r + 0.5)
        g = int(g + 0.5)
        b = int(b + 0.5)
        palette.append((r, g, b))
    return palette

def eval_heatmap(saliency_map):
    """
    Calculates heatmap map from given saliency map.

    Parameters
    ----------
    saliency_map : ndarray
        Should be 2D-array with [0, 1] items.

    Returns
    -------
    out : PIL.Image
        Heatmap image.
    """
    assert(len(saliency_map.shape) == 2)
    palette = numpy.array(_get_heatmap_palette(), dtype='uint8')
    indices = numpy.array(255.0 * saliency_map + 0.5, dtype='uint8')
    heatmap = palette[indices]
    return Image.fromarray(heatmap)

################################################################################

#def eval

#def get_