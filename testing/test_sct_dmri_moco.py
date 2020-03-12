#!/usr/bin/env python
#########################################################################################
#
# Test function for sct_dmri_moco
#
# ---------------------------------------------------------------------------------------
# Copyright (c) 2017 Polytechnique Montreal <www.neuro.polymtl.ca>
# Author: Julien Cohen-Adad
#
# About the license: see the file LICENSE.TXT
#########################################################################################

import sct_utils as sct


def init(param_test):
    """
    Initialize class: param_test
    """
    # Reorient image to sagittal for testing another orientation (and crop to save time)
    sct.run('sct_image -i dmri/dmri.nii.gz -setorient AIL -o dmri/dmri_AIL.nii', verbose=0)
    sct.run('sct_crop_image -i dmri_AIL.nii -zmin 19 -zmax 21 -o dmri_AIL_crop.nii', verbose=0)
    # initialization
    default_args = [
        '-i dmri/dmri.nii.gz -bvec dmri/bvecs.txt -g 3 -x nn -r 0',
        '-i dmri/dmri_AIL_crop.nii -bvec dmri/bvecs.txt -g 3 -x nn -r 0']

    # assign default params
    if not param_test.args:
        param_test.args = default_args
    return param_test


def test_integrity(param_test):
    """
    Test integrity of function
    """
    param_test.output += '\nNot implemented.'
    return param_test
