#!/usr/bin/env python
#########################################################################################
# Register a volume (e.g., EPI from fMRI or DTI scan) to an anatomical image.
#
# See Usage() below for more information.
#
#
# DEPENDENCIES
# ---------------------------------------------------------------------------------------
# EXTERNAL PYTHON PACKAGES
# none
#
# EXTERNAL SOFTWARE
# - itksnap/sct_c3d <http://www.itksnap.org/pmwiki/pmwiki.php?n=Main.HomePage>
# - ants <http://stnava.github.io/ANTs/>
#
#
# ---------------------------------------------------------------------------------------
# Copyright (c) 2013 Polytechnique Montreal <www.neuro.polymtl.ca>
# Author: Julien Cohen-Adad
# Modified: 2014-06-03
#
# About the license: see the file LICENSE.TXT
#########################################################################################

# TODO: output name file for warp using "src" and "dest" file name, i.e. warp_filesrc2filedest.nii.gz
# TODO: testing script for all cases

# Note for the developer: DO NOT use --collapse-output-transforms 1, otherwise inverse warping field is not output

# TODO: make three possibilities:
# - one-step registration, using only image registration (by sliceReg or antsRegistration)
# - two-step registration, using first segmentation-based registration (based on sliceReg or antsRegistration) and second the image registration (and allow the choice of algo, metric, etc.)
# - two-step registration, using only segmentation-based registration


# DEFAULT PARAMETERS
class Param:
    ## The constructor
    def __init__(self):
        self.debug = 0
        self.remove_temp_files = 1  # remove temporary files
        self.outSuffix  = "_reg"
        self.padding = 5  # add 'padding' slices at the top and bottom of the volumes if deformation at the edge is not good. Default=5. Put 0 for no padding.
        self.algo = "syn"  # algo for registration
        self.param_syn = ['10',  # number of iterations. For several stages, add x. E.g.: 50x10
                      '2',  # shrink factor. For several stages, add x.
                      '0',  # smoothing factor. For several stages, add x.
                      '0.5',  # gradientStep
                      'MI']  # metric: CC,MI,MeanSquares
        self.param_slicereg = ['10',  # number of iterations. For several stages, add x. E.g.: 50x10
                      '3',  # degree of polynomial.
                      'MeanSquares']  # metric: CC,MI,MeanSquares
        self.verbose = 1  # verbose
        self.interp = 'linear'  # nn, linear, spline

import sys
import getopt
import os
import commands
import time
import sct_utils as sct


# MAIN
# ==========================================================================================
def main():

    # Initialization
    fname_src = ''
    fname_dest = ''
    fname_src_seg = ''
    fname_dest_seg = ''
    fname_output = ''
    fname_mask = ''
    padding = param.padding
    param_user = ''
    # algo_first = 'SliceReg'
    # numberIterations = param.numberIterations
    remove_temp_files = param.remove_temp_files
    verbose = param.verbose
    use_segmentation = 0  # use spinal cord segmentation to improve robustness
    use_init_transfo = ''
    # gradientStep = param.gradientStep
    algo = param.algo
    start_time = time.time()
    print ''

    # get path of the toolbox
    status, path_sct = commands.getstatusoutput('echo $SCT_DIR')

    # Parameters for debug mode
    if param.debug:
        print '\n*** WARNING: DEBUG MODE ON ***\n'
        status, path_sct_data = commands.getstatusoutput('echo $SCT_TESTING_DATA_DIR')
        fname_dest = path_sct_data+'/mt/mt1.nii.gz'
        fname_src = path_sct_data+'/t2/t2.nii.gz'
        param_user = '10,syn,0.5,MI'
        remove_temp_files = 0
        verbose = 1
    else:
        # Check input parameters
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'ha:d:i:m:o:p:r:v:x:z:')
        except getopt.GetoptError:
            usage()
        if not opts:
            usage()
        for opt, arg in opts:
            if opt == '-h':
                usage()
            elif opt in ('-a'):
                algo = arg
            elif opt in ("-d"):
                fname_dest = arg
            elif opt in ("-i"):
                fname_src = arg
            elif opt in ("-m"):
                fname_mask = arg
            elif opt in ("-o"):
                fname_output = arg
            elif opt in ('-p'):
                param_user = arg
            elif opt in ('-r'):
                remove_temp_files = int(arg)
            elif opt in ('-v'):
                verbose = int(arg)
            elif opt in ('-x'):
                param.interp = arg
            elif opt in ('-z'):
                padding = arg

    # display usage if a mandatory argument is not provided
    if fname_src == '' or fname_dest == '':
        sct.printv('ERROR in '+os.path.basename(__file__)+': All mandatory arguments are not provided. Type: '+os.path.basename(__file__)+' -h.\n', 1, 'error')

    # parse argument for param
    if algo == 'syn' or algo == 'bsplinesyn':
        if not param_user == '':
            param.param_syn = param_user.replace(' ', '').split(',')  # remove spaces and parse with comma
            del param_user
        numberIterations, shrinkFactor, smoothingSigma, gradientStep, metric = param.param_syn
    elif algo == 'slicereg':
        if not param_user == '':
            param.param_slicereg = param_user.replace(' ', '').split(',')  # remove spaces and parse with comma
            del param_user
        numberIterations, degPoly, metric = param.param_slicereg
    else:
        sct.printv('ERROR: algo '+algo+' does not exist. Exit program', 1, 'error')

    # if sliceReg is used, we can't pad in the image...
    if algo == 'slicereg':
        sct.printv('WARNING: if sliceReg is used, padding should not be used. Now setting padding=0', 1, 'warning')
        padding = 0

    # print arguments
    print '\nInput parameters:'
    print '  Source .............. '+fname_src
    print '  Destination ......... '+fname_dest
    print '  Mask ................ '+fname_mask
    print '  Output name ......... '+fname_output
    print '  Algorithm ........... '+algo
    print '  Number of iterations  '+str(numberIterations)
    print '  Metric .............. '+metric
    print '  Remove temp files ... '+str(remove_temp_files)
    print '  Verbose ............. '+str(verbose)

    # check existence of input files
    print '\nCheck if files exist...'
    sct.check_file_exist(fname_src)
    sct.check_file_exist(fname_dest)
    if not fname_mask == '':
        sct.check_file_exist(fname_mask)

    # Get if input is 3D
    sct.printv('\nCheck if input data are 3D...', param.verbose)
    sct.check_if_3d(fname_src)
    sct.check_if_3d(fname_dest)

    # check if destination data is RPI
    sct.printv('\nCheck if destination data is RPI...', param.verbose)
    sct.check_if_rpi(fname_dest)

    # set metricSize
    if metric == 'MI':
        metricSize = '32'  # corresponds to number of bins
    else:
        metricSize = '4'  # corresponds to radius

    # Extract path, file and extension
    path_src, file_src, ext_src = sct.extract_fname(fname_src)
    path_dest, file_dest, ext_dest = sct.extract_fname(fname_dest)

    # define output folder and file name
    if fname_output == '':
        path_out = ''  # output in user's current directory
        file_out = file_src+"_reg"
        ext_out = ext_src
    else:
        path_out, file_out, ext_out = sct.extract_fname(fname_output)

    # create temporary folder
    print('\nCreate temporary folder...')
    path_tmp = 'tmp.'+time.strftime("%y%m%d%H%M%S")
    status, output = sct.run('mkdir '+path_tmp)

    # copy files to temporary folder
    print('\nCopy files...')
    sct.run('sct_c3d '+fname_src+' -o '+path_tmp+'/src.nii')
    sct.run('sct_c3d '+fname_dest+' -o '+path_tmp+'/dest.nii')
    if not fname_mask == '':
        sct.run('sct_c3d '+fname_mask+' -o '+path_tmp+'/mask.nii.gz')
        masking = '-x mask.nii.gz'  # this variable will be used when calling ants
    else:
        masking = ''  # this variable will be used when calling ants

    # go to tmp folder
    os.chdir(path_tmp)

    # Pad the destination image (because ants doesn't deform the extremities)
    sct.printv('\nPad src and destination volumes (because ants doesn''t deform the extremities)...', verbose)
    pad_image('dest.nii', 'dest_pad.nii', padding)

    # Put source into destination space using header (no estimation -- purely based on header)
    sct.printv('\nPut source into destination space using header...', verbose)
    sct.run('sct_antsRegistration -d 3 -t Translation[0] -m MI[dest_pad.nii,src.nii,1,16] -c 0 -f 1 -s 0 -o [regAffine,src_regAffine.nii] -n BSpline[3]')

    # Estimate transformation
    sct.printv('\nEstimate transformation (can take a couple of minutes)...', verbose)

    if algo == 'slicereg':
        cmd = ('sct_antsSliceRegularizedRegistration '
               '-t Translation[0.5] '
               '-m '+metric+'[dest_pad.nii,src_regAffine.nii,1,'+metricSize+',Regular,0.2] '
               '-p '+degPoly+' '
               '-i '+numberIterations+' '
               '-f 1 '
               '-s 0 '
               '-o [stage10,src_regAffineWarp.nii] '  # here the warp name is stage10 because antsSliceReg add "Warp"
               +masking)
    else:
        cmd = ('sct_antsRegistration '
               '--dimensionality 3 '
               '--transform '+algo+'['+gradientStep+',3,0] '
               '--metric '+metric+'[dest_pad.nii,src_regAffine.nii,1,'+metricSize+'] '
               '--convergence '+numberIterations+' '
               '--shrink-factors '+shrinkFactor+' '
               '--smoothing-sigmas '+smoothingSigma+'mm '
               '--restrict-deformation 1x1x0 '
               '--output [stage1,src_regAffineWarp.nii] '
               '--interpolation BSpline[3] '
               +masking)

    # run registration
    status, output = sct.run(cmd)
    if status:
        sct.printv(output, 1, 'error')
        sct.printv('\nERROR: ANTs failed. Exit program.\n', 1, 'error')

    # Concatenate transformations
    sct.printv('\nConcatenate affine and local transformations...', verbose)
    sct.run('sct_concat_transfo -w regAffine0GenericAffine.mat,stage10Warp.nii.gz -d dest.nii -o warp_src2dest.nii.gz')
    sct.run('sct_concat_transfo -w stage10InverseWarp.nii.gz,-regAffine0GenericAffine.mat -d src.nii -o warp_dest2src.nii.gz')

    # Apply warping field to src data
    sct.printv('\nApply transfo source --> dest...', verbose)
    sct.run('sct_apply_transfo -i src.nii -o src_reg.nii -d dest.nii -w warp_src2dest.nii.gz -x '+param.interp)
    sct.printv('\nApply transfo dest --> source...', verbose)
    sct.run('sct_apply_transfo -i dest.nii -o dest_reg.nii -d src.nii -w warp_dest2src.nii.gz -x '+param.interp)

    # come back to parent folder
    os.chdir('..')

    # Generate output files
    sct.printv('\nGenerate output files...', verbose)
    fname_src2dest = sct.generate_output_file(path_tmp+'/src_reg.nii', path_out+file_out+ext_out)
    sct.generate_output_file(path_tmp+'/warp_src2dest.nii.gz', path_out+'warp_'+file_src+'2'+file_dest+'.nii.gz')
    fname_dest2src = sct.generate_output_file(path_tmp+'/dest_reg.nii', path_out+file_dest+'_reg'+ext_dest)
    sct.generate_output_file(path_tmp+'/warp_dest2src.nii.gz', path_out+'warp_'+file_dest+'2'+file_src+'.nii.gz')
    # sct.generate_output_file(path_tmp+'/warp_dest2src.nii.gz', path_out+'warp_dest2src.nii.gz')

    # Delete temporary files
    if remove_temp_files == 1:
        print '\nRemove temporary files...'
        sct.run('rm -rf '+path_tmp)

    # display elapsed time
    elapsed_time = time.time() - start_time
    print '\nFinished! Elapsed time: '+str(int(round(elapsed_time)))+'s'

    # to view results
    print '\nTo view results, type:'
    print 'fslview '+fname_dest+' '+fname_src2dest+' &'
    print 'fslview '+fname_src+' '+fname_dest2src+' &'
    print ''


# Print usage
# ==========================================================================================
def usage():
    print """
"""+os.path.basename(__file__)+"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Part of the Spinal Cord Toolbox <https://sourceforge.net/projects/spinalcordtoolbox>

DESCRIPTION
  This program co-registers two 3D volumes. The deformation is non-rigid and is constrained along Z
  direction (i.e., axial plane). Hence, this function assumes that orientation of the destination
  image is axial (RPI). If you need to register two volumes with large deformations and/or different
  contrasts, it is recommended to input spinal cord segmentations (binary mask) in order to achieve
  maximum robustness.
  The program outputs a warping field that can be used to register other images to the destination
  image. To apply the warping field to another image, use sct_apply_transfo

USAGE
  """+os.path.basename(__file__)+""" -i <source> -d <dest>

MANDATORY ARGUMENTS
  -i <source>      source image
  -d <dest>        destination image

OPTIONAL ARGUMENTS
  -m <mask>        mask used on destination image.
  -o <output>      name of output file. Default=source_reg
  -a {syn,bsplinesyn,slicereg}  algorithm for registration.
                     more info on slicereg: http://goo.gl/Sj3ZeU
  -p <param>       parameters for registration. Separate with ','. Depends on the algorithm:
                   if a = syn or bsplinesyn:
                     1) number of iterations. For multiple stages, separate with 'x'. Default="""+param_default.param_syn[0]+"""
                     2) shrink factor. Default="""+param_default.param_syn[1]+"""
                     3) smoothing factor in mm. Default="""+param_default.param_syn[2]+"""
                     4) gradient step. The larger the more deformation. Default="""+param_default.param_syn[3]+"""
                     5) metric: Default="""+param_default.param_syn[4]+"""
                          MI: fast, but requires a minimum of voxels (otherwise it crashes)
                          MeanSquares: fast, requires similar contrast between src and dest.
                          CC: slow, but sometimes produces best results.
                   if a = slicereg:
                     1) number of iterations (only one stage). Default="""+param_default.param_slicereg[0]+"""
                     2) degree of polynomial function. Default="""+param_default.param_slicereg[1]+"""
                     3) metric: {MI,MeanSquares,CC}. Default="""+param_default.param_slicereg[2]+"""
  -z <padding>     size of z-padding to enable deformation at edges. Default="""+str(param_default.padding)+"""
  -x {nn,linear,spline}  Final Interpolation. Default="""+str(param_default.interp)+"""
  -r {0,1}         remove temporary files. Default="""+str(param.remove_temp_files)+"""
  -v {0,1}         verbose. Default="""+str(param_default.verbose)+"""

EXAMPLES
  Register mean DWI data to the T1 volume using SyN:
  """+os.path.basename(__file__)+""" -i dwi_mean.nii.gz -d t1.nii.gz -a syn -p 50x5,4x2,0x0,0.5,MI -x linear \n"""

    # exit program
    sys.exit(2)


# pad an image
# ==========================================================================================
def pad_image(fname_in, file_out, padding):
    sct.run('sct_c3d '+fname_in+' -pad 0x0x'+str(padding)+'vox 0x0x'+str(padding)+'vox 0 -o '+file_out, 1)
    return


# START PROGRAM
# ==========================================================================================
if __name__ == "__main__":
    # initialize parameters
    param = Param()
    param_default = Param()
    # call main function
    main()



    # Convert deformation field to 4D volume (readable by fslview)
    # DONE: clean code below-- right now it does not work
    #===========
    #if convertDeformation:
    #    print('\nConvert deformation field...')
    #    cmd = 'sct_c3d -mcs tmp.regWarp.nii -oo tmp.regWarp_x.nii tmp.regWarp_y.nii tmp.regWarp_z.nii'
    #    print(">> "+cmd)
    #    os.system(cmd)
    #    cmd = 'fslmerge -t '+path_out+'warp_comp.nii tmp.regWarp_x.nii tmp.regWarp_y.nii tmp.regWarp_z.nii'
    #    print(">> "+cmd)
    #    os.system(cmd)
    #===========
