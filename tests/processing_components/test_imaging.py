""" Unit tests for pipelines expressed via dask.delayed


"""

import logging
import sys
import unittest

import numpy
from astropy import units as u
from astropy.coordinates import SkyCoord

from data_models.polarisation import PolarisationFrame
from processing_components.image.operations import export_image_to_fits, smooth_image
from processing_components.imaging.base import predict_skycomponent_visibility
from processing_components.imaging.imaging_functions import predict_function, invert_function
from processing_components.simulation.testing_support import create_named_configuration, ingest_unittest_visibility, \
    create_unittest_model, insert_unittest_errors, create_unittest_components
from processing_components.skycomponent.operations import find_skycomponents, find_nearest_skycomponent, \
    insert_skycomponent
from processing_components.visibility.operations import copy_visibility

log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stdout))
log.addHandler(logging.StreamHandler(sys.stderr))


class TestImaging(unittest.TestCase):
    def setUp(self):
        
        from data_models.parameters import arl_path
        self.dir = arl_path('test_results')
    
    def actualSetUp(self, add_errors=False, freqwin=1, block=False, dospectral=True, dopol=False, zerow=False):
        
        self.npixel = 256
        self.low = create_named_configuration('LOWBD2', rmax=750.0)
        self.freqwin = freqwin
        self.vis_list = list()
        self.ntimes = 5
        self.times = numpy.linspace(-3.0, +3.0, self.ntimes) * numpy.pi / 12.0
        
        if freqwin > 1:
            self.frequency = numpy.linspace(0.8e8, 1.2e8, self.freqwin)
            self.channelwidth = numpy.array(freqwin * [self.frequency[1] - self.frequency[0]])
        else:
            self.frequency = numpy.array([0.8e8])
            self.channelwidth = numpy.array([1e6])
        
        if dopol:
            self.vis_pol = PolarisationFrame('linear')
            self.image_pol = PolarisationFrame('stokesIQUV')
            f = numpy.array([100.0, 20.0, -10.0, 1.0])
        else:
            self.vis_pol = PolarisationFrame('stokesI')
            self.image_pol = PolarisationFrame('stokesI')
            f = numpy.array([100.0])
        
        if dospectral:
            flux = numpy.array([f * numpy.power(freq / 1e8, -0.7) for freq in self.frequency])
        else:
            flux = numpy.array([f])
        
        self.phasecentre = SkyCoord(ra=+180.0 * u.deg, dec=-60.0 * u.deg, frame='icrs', equinox='J2000')
        self.vis = ingest_unittest_visibility(self.low,
                                              self.frequency,
                                              self.channelwidth,
                                              self.times,
                                              self.vis_pol,
                                              self.phasecentre, block=block,
                                              zerow=zerow)
        
        self.model = create_unittest_model(self.vis,
                                           self.image_pol,
                                           npixel=self.npixel)
        self.components = create_unittest_components(self.model,
                                                     flux[0, :][numpy.newaxis, :])
        
        self.model = insert_skycomponent(self.model, self.components)
        
        self.vis = predict_skycomponent_visibility(self.vis, self.components)
        
        self.cmodel = smooth_image(self.model)
        export_image_to_fits(self.model, '%s/test_imaging_model.fits' % self.dir)
        export_image_to_fits(self.cmodel, '%s/test_imaging_cmodel.fits' % self.dir)
        
        if add_errors and block:
            self.vis = insert_unittest_errors(self.vis)
    
    def test_time_setup(self):
        self.actualSetUp()
    
    def _checkcomponents(self, dirty, fluxthreshold=0.6, positionthreshold=1.0):
        comps = find_skycomponents(dirty, fwhm=1.0, threshold=10 * fluxthreshold, npixels=5)
        assert len(comps) == len(self.components), "Different number of components found: original %d, recovered %d" % \
                                                   (len(self.components), len(comps))
        cellsize = abs(dirty.wcs.wcs.cdelt[0])
        
        for comp in comps:
            # Check for agreement in direction
            ocomp, separation = find_nearest_skycomponent(comp.direction, self.components)
            assert separation / cellsize < positionthreshold, "Component differs in position %.3f pixels" % \
                                                              separation / cellsize
    
    def _predict_base(self, context='2d', extra='', fluxthreshold=1.0, facets=1, vis_slices=1, **kwargs):
        
        vis = copy_visibility(self.vis)
        vis.data['vis'][...] = 0
        vis = predict_function(vis, self.model, context=context,
                               vis_slices=vis_slices, facets=facets, **kwargs)
        
        vis.data['vis'][...] -= self.vis.data['vis'][...]
        
        dirty = invert_function(vis, self.model, context='2d', dopsf=False,
                                normalize=True)
        
        assert numpy.max(numpy.abs(dirty[0].data)), "Residual image is empty"
        export_image_to_fits(dirty[0], '%s/test_imaging_predict_%s%s_dirty.fits' %
                             (self.dir, context, extra))
        
        maxabs = numpy.max(numpy.abs(dirty[0].data))
        assert maxabs < fluxthreshold, "Error %.3f greater than fluxthreshold %.3f " % (maxabs, fluxthreshold)
    
    def _invert_base(self, context, extra='', fluxthreshold=1.0, positionthreshold=1.0, check_components=True,
                     facets=1, vis_slices=1, **kwargs):
        
        dirty = invert_function(self.vis, self.model, context=context,
                                dopsf=False, normalize=True, facets=facets, vis_slices=vis_slices,
                                **kwargs)
        export_image_to_fits(dirty[0], '%s/test_imaging_invert_%s%s_dirty.fits' %
                             (self.dir, context, extra))
        
        assert numpy.max(numpy.abs(dirty[0].data)), "Image is empty"
        
        if check_components:
            self._checkcomponents(dirty[0], fluxthreshold, positionthreshold)
    
    def test_predict_2d(self):
        self.actualSetUp(zerow=True)
        self._predict_base(context='2d')
    
    @unittest.skip("Facets requires overlap")
    def test_predict_facets(self):
        self.actualSetUp()
        self._predict_base(context='facets', fluxthreshold=15.0, facets=4)
    
    @unittest.skip("Timeslice predict needs better interpolation")
    def test_predict_facets_timeslice(self):
        self.actualSetUp()
        self._predict_base(context='facets_timeslice', fluxthreshold=19.0, facets=8, vis_slices=self.ntimes)
    
    @unittest.skip("Facets requires overlap")
    def test_predict_facets_wprojection(self):
        self.actualSetUp()
        self._predict_base(context='facets', extra='_wprojection', facets=8, wstep=8.0, fluxthreshold=15.0,
                           oversampling=2)
    
    @unittest.skip("Correcting twice?")
    def test_predict_facets_wstack(self):
        self.actualSetUp()
        self._predict_base(context='facets_wstack', fluxthreshold=15.0, facets=8, vis_slices=41)
    
    @unittest.skip("Timeslice predict needs better interpolation")
    def test_predict_timeslice(self):
        self.actualSetUp()
        self._predict_base(context='timeslice', fluxthreshold=19.0, vis_slices=self.ntimes)
    
    @unittest.skip("Timeslice predict needs better interpolation")
    def test_predict_timeslice_wprojection(self):
        self.actualSetUp()
        self._predict_base(context='timeslice', extra='_wprojection', fluxthreshold=3.0, wstep=10.0,
                           vis_slices=self.ntimes, oversampling=2)
    
    def test_predict_wprojection(self):
        self.actualSetUp()
        self._predict_base(context='2d', extra='_wprojection', wstep=10.0, fluxthreshold=2.0, oversampling=2)
    
    def test_predict_wstack(self):
        self.actualSetUp()
        self._predict_base(context='wstack', fluxthreshold=2.0, vis_slices=41)
    
    def test_predict_wstack_wprojection(self):
        self.actualSetUp()
        self._predict_base(context='wstack', extra='_wprojection', fluxthreshold=3.0, wstep=2.5, vis_slices=11,
                           oversampling=2)
    
    def test_predict_wstack_spectral(self):
        self.actualSetUp(dospectral=True)
        self._predict_base(context='wstack', extra='_spectral', fluxthreshold=4.0, vis_slices=41)
    
    def test_predict_wstack_spectral_pol(self):
        self.actualSetUp(dospectral=True, dopol=True)
        self._predict_base(context='wstack', extra='_spectral', fluxthreshold=4.0, vis_slices=41)
    
    def test_invert_2d(self):
        self.actualSetUp(zerow=True)
        self._invert_base(context='2d', positionthreshold=2.0, check_components=False)
    
    def test_invert_facets(self):
        self.actualSetUp()
        self._invert_base(context='facets', positionthreshold=2.0, check_components=True, facets=8)
    
    @unittest.skip("Correcting twice?")
    def test_invert_facets_timeslice(self):
        self.actualSetUp()
        self._invert_base(context='facets_timeslice', check_components=True, vis_slices=self.ntimes,
                          positionthreshold=5.0, flux_threshold=1.0, facets=8)
    
    def test_invert_facets_wprojection(self):
        self.actualSetUp()
        self._invert_base(context='facets', extra='_wprojection', check_components=True,
                          positionthreshold=2.0, wstep=10.0, oversampling=2, facets=4)
    
    @unittest.skip("Correcting twice?")
    def test_invert_facets_wstack(self):
        self.actualSetUp()
        self._invert_base(context='facets_wstack', positionthreshold=1.0, check_components=False, facets=4,
                          vis_slices=11)
    
    def test_invert_timeslice(self):
        self.actualSetUp()
        self._invert_base(context='timeslice', positionthreshold=1.0, check_components=True,
                          vis_slices=self.ntimes)
    
    def test_invert_timeslice_wprojection(self):
        self.actualSetUp()
        self._invert_base(context='timeslice', extra='_wprojection', positionthreshold=1.0,
                          check_components=True, wstep=20.0, vis_slices=self.ntimes, oversampling=2)
    
    def test_invert_wprojection(self):
        self.actualSetUp()
        self._invert_base(context='2d', extra='_wprojection', positionthreshold=2.0, wstep=10.0, oversampling=2)
    
    def test_invert_wprojection_wstack(self):
        self.actualSetUp()
        self._invert_base(context='wstack', extra='_wprojection', positionthreshold=1.0, wstep=2.5, vis_slices=11,
                          oversampling=2)
    
    def test_invert_wstack(self):
        self.actualSetUp()
        self._invert_base(context='wstack', positionthreshold=1.0, vis_slices=41)
    
    def test_invert_wstack_spectral(self):
        self.actualSetUp(dospectral=True)
        self._invert_base(context='wstack', extra='_spectral', positionthreshold=2.0,
                          vis_slices=41)
    
    def test_invert_wstack_spectral_pol(self):
        self.actualSetUp(dospectral=True, dopol=True)
        self._invert_base(context='wstack', extra='_spectral_pol', positionthreshold=2.0,
                          vis_slices=41)


if __name__ == '__main__':
    unittest.main()
