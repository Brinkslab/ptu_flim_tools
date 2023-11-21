Tools for reading, converting and analysing ptu flim data.

### direct installation with pip
`pip install git+https://github.com/Brinkslab/ptu_flim_tools`

### installation from repo
`pip install .`

### tools
`ptu_to_tiff [-h] [-l] [-p MEAN_LIFETIME_MIN_PHOTONS] [-b MEAN_LIFETIME_BINRANGE MEAN_LIFETIME_BINRANGE]
                      [-x MEAN_LIFETIME_XRANGE MEAN_LIFETIME_XRANGE] [-y MEAN_LIFETIME_YRANGE MEAN_LIFETIME_YRANGE]
                      ptu_path [output_dir]`
                      converts a ptu file to a set of tiff files.

`tiff_to_avi.py [-h] tiff_file` convert a stack generated by `ptu_to_tiff` to a video file for easy viewing.
