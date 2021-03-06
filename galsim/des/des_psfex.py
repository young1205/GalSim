# Copyright 2012, 2013 The GalSim developers:
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
#
# GalSim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GalSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GalSim.  If not, see <http://www.gnu.org/licenses/>
#
"""@file des_psfex.py

Part of the DES module.  This file implements one way that DES measures the PSF.

The DES_PSFEx class handles interpolated PCA images, which are generally stored in 
*_psfcat.psf files.
"""

import galsim

class DES_PSFEx(object):
    """Class that handles DES files describing interpolated principal component images
    of the PSF.  These are usually stored as *_psfcat.psf files.

    Typical usage:
        
        des_psfex = galsim.des.DES_PSFEx(fitpsf_file_name)
        
        ...

        pos = galsim.PositionD(image_x, image_y)  # position in pixels on the image
                                                  # NOT in arcsec on the sky!
        psf = des_psfex.getPSF(pos, pixel_scale=0.27)


    @param file_name  The file name to be read in.
    @param dir        Optionally a directory name can be provided if the file_name does not 
                      already include it.
    """
    _req_params = { 'file_name' : str }
    _opt_params = { 'dir' : str }
    _single_params = []
    _takes_rng = False

    def __init__(self, file_name, dir=None):

        if dir:
            import os
            file_name = os.path.join(dir,file_name)
        self.file_name = file_name

        try:
            self.read()
        except Exception, e:
            raise IOError("Unable to read DES_PSFEx file %s.  Error = %s"%(self.file_name,str(e)))

    def read(self):
        import pyfits
        hdu = pyfits.open(self.file_name)[1]
        pol_naxis = hdu.header['POLNAXIS']
        if pol_naxis != 2:
            raise IOError("PSFEx: Expected POLNAXIS == 2, got %d"%polnaxis)
        pol_zero1 = hdu.header['POLZERO1']
        pol_zero2 = hdu.header['POLZERO2']
        pol_scal1 = hdu.header['POLSCAL1']
        pol_scal2 = hdu.header['POLSCAL2']
        pol_name1 = hdu.header['POLNAME1']
        pol_name2 = hdu.header['POLNAME2']
        psf_naxis = hdu.header['PSFNAXIS']
        if psf_naxis != 3:
            raise IOError("PSFEx: Expected PSFNAXIS == 3, got %d"%psfnaxis)
        psf_axis1 = hdu.header['PSFAXIS1']
        psf_axis2 = hdu.header['PSFAXIS2']
        psf_axis3 = hdu.header['PSFAXIS3']
        pol_deg = hdu.header['POLDEG1']
        if psf_axis3 != ((pol_deg+1)*(pol_deg+2))/2:
            raise IOError("PSFEx: POLDEG and PSFAXIS3 disagree")
        psf_samp = hdu.header['PSF_SAMP']
        pol_ngrp = hdu.header['POLNGRP']
        # I'm not sure what this POLNGRP is really about, but Peter's code (from which I
        # am adapting this) says that it only works when POLNGRP == 1.
        if pol_ngrp != 1:
            raise IOError("PSFEx: Current implementation requires POLNGRP == 1, got %d"%pol_ngrp)

        # Note: older pyfits versions don't get the shape right.
        # For newer pyfits versions the reshape command should be a no op.
        basis = hdu.data.field('PSF_MASK')[0].reshape(psf_axis3,psf_axis2,psf_axis1)
        if basis.shape[0] != psf_axis3:
            raise IOError("PSFEx: PSFAXIS3 disagrees with actual basis size")
        if basis.shape[1] != psf_axis2:
            raise IOError("PSFEx: PSFAXIS2 disagrees with actual basis size")
        if basis.shape[2] != psf_axis1:
            raise IOError("PSFEx: PSFAXIS1 disagrees with actual basis size")

        # Save some of these values for use in building the interpolated images
        self.basis = basis
        self.fit_order = pol_deg
        self.fit_size = psf_axis3
        self.x_zero = pol_zero1
        self.y_zero = pol_zero2
        self.x_scale = pol_scal1
        self.y_scale = pol_scal2
        self.sample_scale = psf_samp


    def getPSF(self, pos, pixel_scale):
        """Returns the PSF at position pos

        The PSFEx class does everything in pixel units, so it has no concept of the pixel_scale.
        For Galsim, we do everything in physical units (i.e. arcsec typically), so the returned 
        psf needs to account for the pixel_scale.

        @param pos          The position in pixel units for which to build the PSF.
        @param pixel_scale  The pixel scale in arcsec/pixel.

        @returns an InterpolatedImage instance.
        """
        import numpy
        xto = self._define_xto( (pos.x - self.x_zero) / self.x_scale )
        yto = self._define_xto( (pos.y - self.y_zero) / self.y_scale )
        order = self.fit_order
        P = numpy.array([ xto[nx] * yto[ny] for ny in range(order+1) for nx in range(order+1-ny) ])
        assert len(P) == self.fit_size

        # Note: This is equivalent to:
        #
        #     P = numpy.empty(self.fit_size)
        #     k = 1
        #     for ny in range(self.fit_order+1):
        #         for nx in range(self.fit_order+1-ny):
        #             assert k == nx+ny(self.fit_order+1)-(ny*ny-1))/2
        #             P[k] = xto[nx] * yto[ny]
        #             k == k+1
        #
        # which is pretty much Peter's version of this code.

        ar = numpy.tensordot(P,self.basis,(0,0)).astype(numpy.float32)
        im = galsim.ImageViewF(array=ar)
        im.scale = pixel_scale * self.sample_scale
        return galsim.InterpolatedImage(im, flux=1, x_interpolant=galsim.Lanczos(3))

    def _define_xto(self, x):
        import numpy
        xto = numpy.empty(self.fit_order+1)
        xto[0] = 1
        for i in range(1,self.fit_order+1):
            xto[i] = x*xto[i-1]
        return xto

# Now add this class to the config framework.
import galsim.config

# First we need to add the class itself as a valid input_type.
galsim.config.process.valid_input_types['des_psfex'] = ('galsim.des.DES_PSFEx', [], False)

# Also make a builder to create the PSF object for a given position.
# The builders require 4 args.
# config is a dictionary that includes 'type' plus other items you might want to allow or require.
# key is the key name one level up in the config structure.  Probably 'psf' in this case.
# base is the top level config dictionary where some global variables are stored.
# ignore is a list of key words that might be in the config dictionary that you should ignore.
def BuildDES_PSFEx(config, key, base, ignore):
    """@brief Build a RealGalaxy type GSObject from user input.
    """
    opt = { 'flux' : float }
    kwargs, safe = galsim.config.GetAllParams(config, key, base, opt=opt, ignore=ignore)

    if 'des_psfex' not in base:
        raise ValueError("No DES_PSFEx instance available for building type = DES_PSFEx")
    des_psfex = base['des_psfex']

    if 'chip_pos' not in base:
        raise ValueError("DES_PSFEx requested, but no chip_pos defined in base.")
    chip_pos = base['chip_pos']

    if 'pixel_scale' not in base:
        raise ValueError("DES_PSFEx requested, but no pixel_scale defined in base.")
    pixel_scale = base['pixel_scale']

    psf = des_psfex.getPSF(chip_pos, pixel_scale)

    if 'flux' in kwargs:
        psf.setFlux(kwargs['flux'])

    # The second item here is "safe", a boolean that declares whether the returned value is 
    # safe to save and use again for later objects.  In this case, we wouldn't want to do 
    # that, since they will be at different positions, so the interpolated PSF will be different.
    return psf, False


# Register this builder with the config framework:
galsim.config.gsobject.valid_gsobject_types['DES_PSFEx'] = 'galsim.des.BuildDES_PSFEx'

