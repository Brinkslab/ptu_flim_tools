"""convert a ptu file to tiff files
"""
import logging
import pathlib

import numpy as np
import tifffile
import tttrlib


DEFAULT_LOGLEVEL = logging.INFO


def _write_tiff(name, data, output_dir, stem, comment=None):
    logging.info(f"writing {name} as compressed tiff")
    tif_path = output_dir / f"{name}_{stem}.tif"
    tifffile.imwrite(
        tif_path,
        data,
        photometric="minisblack",
        compression="zlib",
        compressionargs={"level": 8},
        predictor=True,
        description=comment,
    )
    size = round(tif_path.stat().st_size / 10**6, 2)
    logging.info(f"created {tif_path}, {size} mb")


def _read_ptu_intensity(path):
    tttr = tttrlib.TTTR(path)
    image = tttrlib.CLSMImage(tttr, fill=True, channels=(0,))
    return image.intensity


def _read_ptu_mean_lifetime(
    path, min_photons=1, binrange=None, xrange=None, yrange=None
):
    logging.debug(
        f"calculating lifetime min_photons={min_photons}, "
        f"binrange={binrange}, xrange={xrange}, yrange={yrange}"
    )
    if min_photons is None:
        min_photons = 1

    tttr = tttrlib.TTTR(path)
    image = tttrlib.CLSMImage(tttr)
    if xrange and yrange:
        image.crop(0, len(image), *xrange, *yrange)

    if binrange:
        bin_min, bin_max = binrange
        if bin_max == -1:
            bin_max = tttr.header.number_of_micro_time_channels

        image.fill(tttr, (0,), False, [[bin_min, bin_max]])
    else:
        image.fill(tttr, (0,), False)
        bin_min, bin_max = None, None

    stack = image.get_mean_lifetime(tttr, min_photons)[bin_min:bin_max]
    image.stack_frames()
    cumulative = image.get_mean_lifetime(tttr, min_photons)[bin_min:bin_max]
    return stack, cumulative


def ptu_to_tiff(ptu_path, output_dir=None):
    """convert a ptu file to tiff files of the intensity

    ptu_path: location of file to read
    output_dir: where to write the tiff files to, defaults to the same
        directory as ptu_file

    will write a tiff file named stack.tif, containing each frame and a tiff
    file named sum.tif, containing the total intensity value per pixel to
    the output_dir
    """
    path = pathlib.Path(ptu_path)
    if output_dir is None:
        output_dir = path.parent
    else:
        output_dir = pathlib.Path(output_dir)

    stack = _read_ptu_intensity(path)

    # sum of all frames collapsed into one
    cumulative = stack.sum(axis=0, dtype=np.uint8)

    size = round(stack.nbytes / 10**6, 2)
    logging.debug(f"stack shape {stack.shape}, {size} mb, {stack.dtype}")

    _write_tiff("stack", stack, output_dir, path.stem)
    _write_tiff("sum", cumulative, output_dir, path.stem)


def ptu_to_tiff_lifetime(
    ptu_path,
    min_photons=None,
    binrange=None,
    xrange=None,
    yrange=None,
    output_dir=None,
):
    """convert a ptu file to tiff files of the mean lifetime

    ptu_path: location of file to read
    output_dir: where to write the tiff files to, defaults to the same
        directory as ptu_file

    will write a tiff file named lifetime.tif, containing each frame and a tiff
    file named avglifetime.tif, containing the mean lifetime of all frames to
    the output_dir
    """
    path = pathlib.Path(ptu_path)
    if output_dir is None:
        output_dir = path.parent
    else:
        output_dir = pathlib.Path(output_dir)

    stack, cumulative = _read_ptu_mean_lifetime(
        path, min_photons, binrange, xrange, yrange
    )

    size = round(stack.nbytes / 10**6, 2)
    logging.debug(f"stack shape {stack.shape}, {size} mb, {stack.dtype}")

    _write_tiff("lifetime", stack, output_dir, path.stem)
    _write_tiff("avglifetime", cumulative, output_dir, path.stem)


def _main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("ptu_path", help="path of the ptu file to parse")
    parser.add_argument(
        "output_dir",
        nargs="?",
        help="output folder to place the created files, "
        "defaults to the location of the input file",
    )
    parser.add_argument(
        "-l",
        "--mean-lifetime",
        action="store_true",
        help="compute mean lifetime instead of intensity",
    )
    parser.add_argument(
        "-p",
        "--mean-lifetime-min-photons",
        type=int,
        help="minimum amount of photons required to include this pixel in the "
        "mean lifetime image",
    )
    parser.add_argument(
        "-b",
        "--mean-lifetime-binrange",
        nargs=2,
        type=int,
        help="a range to clip the values used for the mean lifetime image",
    )
    parser.add_argument(
        "-x",
        "--mean-lifetime-xrange",
        nargs=2,
        type=int,
        help="the x range of an roi for the mean lifetime image",
    )
    parser.add_argument(
        "-y",
        "--mean-lifetime-yrange",
        nargs=2,
        type=int,
        help="the y range of an roi for the mean lifetime image",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="print more output"
    )
    parser.add_argument(
        "-s", "--silent", action="count", default=0, help="print less output"
    )
    args = parser.parse_args()

    loglevel = max(0, DEFAULT_LOGLEVEL + 10 * (args.silent - args.verbose))
    logging.basicConfig(
        level=loglevel,
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    )

    if args.mean_lifetime:
        ptu_to_tiff_lifetime(
            args.ptu_path,
            min_photons=args.mean_lifetime_min_photons,
            binrange=args.mean_lifetime_binrange,
            xrange=args.mean_lifetime_xrange,
            yrange=args.mean_lifetime_yrange,
            output_dir=args.output_dir,
        )
    else:
        ptu_to_tiff(args.ptu_path, args.output_dir)


if __name__ == "__main__":
    _main()
