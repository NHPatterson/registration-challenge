import SimpleITK as sitk
from pathlib import Path


def register_2D_images(source_image, source_image_res, target_image,
                       target_image_res, reg_models, reg_output_fp):
    """ Register 2D images with multiple models and return a list of elastix
        transformation maps.

    Parameters
    ----------
    source_image : str
        file path to the image that will be aligned
    source_image_res : float
        pixel resolution of the source image(e.g., 0.25 um /px)
    target_image : str
        file path to the image to which source_image will be aligned
    source_image_res : float
        pixel resolution of the target image(e.g., 0.25 um /px)
    reg_models : list
        python list of file paths to elastix paramter files
    reg_output_fp : type
        where to place elastix registration data: transforms and iteration info

    Returns
    -------
    list
        list of elastix transforms for aligning subsequent images

    """

    source = sitk.ReadImage(source_image)
    target = sitk.ReadImage(target_image)

    source.SetSpacing((source_image_res, source_image_res))
    target.SetSpacing((target_image_res, target_image_res))

    try:
        selx = sitk.SimpleElastix()
    except AttributeError:
        selx = sitk.ElastixImageFilter()

    selx.LogToConsoleOn()

    selx.SetOutputDirectory(reg_output_fp)

    # if source_image_type == target_image_type:
    #     matcher = sitk.HistogramMatchingImageFilter()
    #     matcher.SetNumberOfHistogramLevels(64)
    #     matcher.SetNumberOfMatchPoints(7)
    #     matcher.ThresholdAtMeanIntensityOn()
    #     source.image = matcher.Execute(source.image, target.image)

    selx.SetMovingImage(source)
    selx.SetFixedImage(target)

    for idx, model in enumerate(reg_models):
        if idx == 0:
            pmap = sitk.ReadParameterFile(model)
            pmap["WriteResultImage"] = ("false", )
            #            pmap['MaximumNumberOfIterations'] = ('10', )

            selx.SetParameterMap(pmap)
        else:
            pmap = sitk.ReadParameterFile(model)
            pmap["WriteResultImage"] = ("false", )
            #            pmap['MaximumNumberOfIterations'] = ('10', )

            selx.AddParameterMap(pmap)

    selx.LogToFileOn()

    # execute registration:
    selx.Execute()

    return list(selx.GetTransformParameterMap())


def transform_2D_image(source_image,
                       source_image_res,
                       transformation_maps,
                       im_output_fp,
                       write_image=False):
    """Transform 2D images with multiple models and return the transformed image
        or write the transformed image to disk as a .tif file.

    Parameters
    ----------
    source_image : str
        file path to the image that will be transformed
    source_image_res : float
        pixel resolution of the source image(e.g., 0.25 um /px)
    transformation_maps : list
        python list of file paths to elastix parameter files
    im_output_fp : str
        output file path
    write_image : bool
        whether to write image or return it as python object

    Returns
    -------
    type
        Description of returned object.

    """

    try:
        transformix = sitk.SimpleTransformix()
    except AttributeError:
        transformix = sitk.TransformixImageFilter()

    if isinstance(source_image, sitk.Image):
        image = source_image
    else:
        print("reading image from file")
        image = sitk.ReadImage(source_image)
        image.SetSpacing((source_image_res, source_image_res))

    for idx, tmap in enumerate(transformation_maps):

        if idx == 0:
            tmap = sitk.ReadParameterFile(tmap)
            tmap["InitialTransformParametersFileName"] = (
                "NoInitialTransform", )
            transformix.SetTransformParameterMap(tmap)
            tmap["ResampleInterpolator"] = (
                "FinalNearestNeighborInterpolator", )
        else:
            tmap = sitk.ReadParameterFile(tmap)
            tmap["InitialTransformParametersFileName"] = (
                "NoInitialTransform", )
            tmap["ResampleInterpolator"] = (
                "FinalNearestNeighborInterpolator", )

            transformix.AddTransformParameterMap(tmap)

    #take care for RGB images
    pixelID = image.GetPixelID()

    transformix.LogToConsoleOn()
    transformix.LogToFileOn()
    transformix.SetOutputDirectory(str(Path(im_output_fp).parent))

    if pixelID in list(range(1, 13)) and image.GetDepth() == 0:
        transformix.SetMovingImage(image)
        image = transformix.Execute()
        image = sitk.Cast(image, pixelID)

    elif pixelID in list(range(1, 13)) and image.GetDepth() > 0:
        images = []
        for chan in range(image.GetDepth()):
            transformix.SetMovingImage(image[:, :, chan])
            images.append(sitk.Cast(transformix.Execute(), pixelID))
        image = sitk.JoinSeries(images)
        image = sitk.Cast(image, pixelID)

    elif pixelID > 12:
        images = []
        for idx in range(image.GetNumberOfComponentsPerPixel()):
            im = sitk.VectorIndexSelectionCast(image, idx)
            pixelID_nonvec = im.GetPixelID()
            transformix.SetMovingImage(im)
            images.append(sitk.Cast(transformix.Execute(), pixelID_nonvec))
            del im

        image = sitk.Compose(images)
        image = sitk.Cast(image, pixelID)

    if write_image is True:
        sitk.WriteImage(image, im_output_fp + "_registered.tif", True)
        return
    else:
        return image


#preprocessed
datapath = Path('/home/nhp/Desktop/hackathon/tissue_masks')

#preprocessed
outpath = Path('/home/nhp/Desktop/hackathon/masked_reg')

# grab all channel 2 images
#raw
ims = sorted(datapath.glob("*_c2_*"))

#preprocessed
ims = sorted(datapath.glob("*"))

# select the first index image as the target
target = str(ims[0])

#reg models
reg_models = [
    'registration/elx_reg_params/rigid.txt', 'elx_reg_2D/elx_reg_params/nl.txt'
]

for idx, image in enumerate(ims):
    out_folder = outpath / image.stem
    if out_folder.is_dir() is False:
        out_folder.mkdir()
    if idx > 0:
        tforms.append(
            register_2D_images(
                str(image),
                1,
                str(target),
                1,
                reg_models,
                str(out_folder),
            ))

        rig_tform = sorted(Path(out_folder).glob('*.0.txt'))
        nl_tform = sorted(Path(out_folder).glob('*.1.txt'))
        tform_list = [str(rig_tform[0]), str(nl_tform[0])]
        im = transform_2D_image(
            str(image), 1, tform_list, im_output_fp='', write_image=False)
        out_im_path = image.stem + '_registered.tiff'
        str(out_folder / out_im_path)
        sitk.WriteImage(im, str(out_folder / out_im_path), True)
