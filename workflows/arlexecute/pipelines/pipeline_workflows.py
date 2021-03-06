""" SDP pipelines as processing components.
"""

from data_models.parameters import get_parameter
from ..calibration.calibration_workflows import calibrate_workflow
from ..execution_support.arlexecute import arlexecute
from workflows.arlexecute.imaging.imaging_workflows import invert_workflow, residual_workflow, \
    predict_workflow, zero_vislist_workflow, subtract_vislist_workflow, restore_workflow, \
    deconvolve_workflow


def ical_workflow(vis_list, model_imagelist, context='2d', calibration_context='TG', do_selfcal=True, **kwargs):
    """Create graph for ICAL pipeline

    :param vis_list:
    :param model_imagelist:
    :param context: imaging context e.g. '2d'
    :param calibration_context: Sequence of calibration steps e.g. TGB
    :param do_selfcal: Do the selfcalibration?
    :param kwargs: Parameters for functions in components
    :return:
    """
    psf_imagelist = invert_workflow(vis_list, model_imagelist, dopsf=True, context=context, **kwargs)
    
    model_vislist = zero_vislist_workflow(vis_list)
    model_vislist = predict_workflow(model_vislist, model_imagelist, context=context, **kwargs)
    if do_selfcal:
        # Make the predicted visibilities, selfcalibrate against it correcting the gains, then
        # form the residual visibility, then make the residual image
        vis_list = calibrate_workflow(vis_list, model_vislist,
                                       calibration_context=calibration_context, **kwargs)
        residual_vislist = subtract_vislist_workflow(vis_list, model_vislist)
        residual_imagelist = invert_workflow(residual_vislist, model_imagelist, dopsf=True, context=context,
                                              iteration=0, **kwargs)
    else:
        # If we are not selfcalibrating it's much easier and we can avoid an unnecessary round of gather/scatter
        # for visibility partitioning such as timeslices and wstack.
        residual_imagelist = residual_workflow(vis_list, model_imagelist, context=context, **kwargs)
    
    deconvolve_model_imagelist, _ = deconvolve_workflow(residual_imagelist, psf_imagelist, model_imagelist,
                                                         prefix='cycle 0', **kwargs)
    
    nmajor = get_parameter(kwargs, "nmajor", 5)
    if nmajor > 1:
        for cycle in range(nmajor):
            if do_selfcal:
                model_vislist = zero_vislist_workflow(vis_list)
                model_vislist = predict_workflow(model_vislist, deconvolve_model_imagelist,
                                                  context=context, **kwargs)
                vis_list = calibrate_workflow(vis_list, model_vislist,
                                               calibration_context=calibration_context,
                                               iteration=cycle, **kwargs)
                residual_vislist = subtract_vislist_workflow(vis_list, model_vislist)
                residual_imagelist = invert_workflow(residual_vislist, model_imagelist, dopsf=False,
                                                      context=context, **kwargs)
            else:
                residual_imagelist = residual_workflow(vis_list, deconvolve_model_imagelist,
                                                        context=context, **kwargs)
            
            prefix = "cycle %d" % (cycle+1)
            deconvolve_model_imagelist, _ = deconvolve_workflow(residual_imagelist, psf_imagelist,
                                                                 deconvolve_model_imagelist,
                                                                 prefix=prefix,
                                                                 **kwargs)
    residual_imagelist = residual_workflow(vis_list, deconvolve_model_imagelist, context=context, **kwargs)
    restore_imagelist = restore_workflow(deconvolve_model_imagelist, psf_imagelist, residual_imagelist)
    
    return arlexecute.execute((deconvolve_model_imagelist, residual_imagelist, restore_imagelist))


def continuum_imaging_workflow(vis_list, model_imagelist, context='2d', **kwargs):
    """ Create graph for the continuum imaging pipeline.
    
    Same as ICAL but with no selfcal.
    
    :param vis_list:
    :param model_imagelist:
    :param context: Imaging context
    :param kwargs: Parameters for functions in components
    :return:
    """
    psf_imagelist = invert_workflow(vis_list, model_imagelist, dopsf=True, context=context, **kwargs)
    
    residual_imagelist = residual_workflow(vis_list, model_imagelist, context=context, **kwargs)
    deconvolve_model_imagelist, _ = deconvolve_workflow(residual_imagelist, psf_imagelist, model_imagelist,
                                                         prefix='cycle 0',
                                                         **kwargs)
    
    nmajor = get_parameter(kwargs, "nmajor", 5)
    if nmajor > 1:
        for cycle in range(nmajor):
            prefix = "cycle %d" % (cycle+1)
            residual_imagelist = residual_workflow(vis_list, deconvolve_model_imagelist, context=context, **kwargs)
            deconvolve_model_imagelist, _ = deconvolve_workflow(residual_imagelist, psf_imagelist,
                                                                 deconvolve_model_imagelist,
                                                                 prefix=prefix,
                                                                 **kwargs)
    
    residual_imagelist = residual_workflow(vis_list, deconvolve_model_imagelist, context=context, **kwargs)
    restore_imagelist = restore_workflow(deconvolve_model_imagelist, psf_imagelist, residual_imagelist)
    return arlexecute.execute((deconvolve_model_imagelist, residual_imagelist, restore_imagelist))


def spectral_line_imaging_workflow(vis_list, model_imagelist, continuum_model_imagelist=None, context='2d', **kwargs):
    """Create graph for spectral line imaging pipeline

    Uses the ical pipeline after subtraction of a continuum model
    
    :param vis_list: List of visibility components
    :param model_imagelist: Spectral line model graph
    :param continuum_model_imagelist: Continuum model list
    :param context: Imaging context
    :param kwargs: Parameters for functions in components
    :return: (deconvolved model, residual, restored)
    """
    if continuum_model_imagelist is not None:
        vis_list = predict_workflow(vis_list, continuum_model_imagelist, context=context, **kwargs)
    
    return continuum_imaging_workflow(vis_list, model_imagelist, context=context, **kwargs)
