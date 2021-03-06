
**June 15, 2018** [Tim], Some more moves and renaming:
* processing_components/component_support->libs/execution support
* processing_components/util->processing_components/simulation

generic functions moved to image_components and visibility_components

**June 15 2018** [Tim], the capabilities for reading measurement sets have been improved.
* Both BlockVisibility's and Visibility's can be created. The former is preferred.
* A channel range e.g. range(17,32) can be specified.
* See tests/processing_components/test_visibility_ms for various ways to use this capability.

**June 14, 2018 [Tim]**, BufferDataModel has been introduced as the root of e.g. BufferImage, BufferSkyModel. All of 
these, except for BufferImage use ad hoc HDF5 files. Image can use fits.

**June 12, 2018 [Tim]**, To fill out the architecture, there is now a ProcessingComponentInterface function for executing 
some components. Components have to be wrapped by hand, and the interface defined via a JSON file.

**May 25, 2018** [Piers], Kubernetes support added.

**April 30 2018** [Tim], the ARL has been updated to be consistent with the SDP Processing Architecture. This required 
very substantial changes throughout. The code is consistent internally but ARL code kept outside the code tree will 
need to be updated manually.

* The top level directory arl has been split into three: libs, processing_components, and workflows
    - libs contains functions that are not accessed directly by the Execution Framework
    - processing_components contains functions that may be accessed by the EF. 
    - workflows contains high level workflows using the processing_components. This eventually will migrate to the EF
     but some are kept here as scripts or notebooks.
* The tests and notebooks have been moved to be inside the appropriate directory.
* The data definitions formerly in arl/data have been moved to a top level directory data_models. 
* The top level Makefile has been updated
* The docs have been updated
* The use of the term 'graph' has been replaced in many places by 'list' to reflect the wrapping of dask in 
arlexecute.

![SDP Processing Architecture](./docs/SDP_processing_architecture.png)

**April 18, 2018** [Tim], Deconvolution can now be done using overlapped, tapered sub-images (aka facets).
Look for deconvolve_facets, deconvolve_overlap, and deconvolve_taper arguments.

