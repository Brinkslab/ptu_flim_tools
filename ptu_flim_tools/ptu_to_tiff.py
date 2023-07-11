"""convert a ptu file to two tiff files
"""
import logging
import pathlib

import numpy as np
import tifffile

from .third_party.readPTU_FLIM.readPTU_FLIM import PTUreader


def ptu_to_tiff(ptu_path, output_dir=None):
    """convert a ptu file to two tiff files

    ptu_path: location of file to read
    output_dir: where to write the tiff files to, defaults to the same
        directory as ptu_file

    will write a tiff file named stack.tif, containing each frame and a tiff
    file named sum.tif, containing the total intensity value per pixel, to the
    output_dir
    """
    path = pathlib.Path(ptu_path)
    if output_dir is None:
        output_dir = path.parent
    else:
        output_dir = pathlib.Path(output_dir)

    ptu_file = PTUreader(str(path))
    stack, cumulative = ptu_file.get_flim_data_stack()

    logging.info("converting to 8bit")
    if np.max(stack) > 0xFF or np.max(cumulative) > 0xFF:
        raise RuntimeError("data can't be converted to 8 bit")

    stack = stack.astype(np.uint8)
    cumulative = cumulative.astype(np.uint8)

    view = stack[:, :, 0]
    data = np.moveaxis(view, 2, 0)
    size = round(data.size / 10**6, 2)
    logging.info(f"stack shape {data.shape}, {size} mb, {data.dtype}")

    logging.info("writing stack as compressed tiff")
    stack_path = output_dir / f"stack_{path.stem}.tif"
    tifffile.imwrite(
        stack_path,
        data,
        photometric="minisblack",
        compression="zlib",
        compressionargs={"level": 8},
        predictor=True,
    )
    size = round(stack_path.stat().st_size / 10**6, 2)
    logging.info(f"created {stack_path}, {size} mb")

    logging.info("writing sum as compressed tiff")
    sum_path = output_dir / f"sum_{path.stem}.tif"
    tifffile.imwrite(
        sum_path,
        cumulative,
        photometric="minisblack",
        compression="zlib",
        compressionargs={"level": 8},
        predictor=True,
    )
    size = round(sum_path.stat().st_size / 10**6, 2)
    logging.info(f"created {sum_path}, {size} mb")


def _main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("ptu_path")
    parser.add_argument("output_dir", nargs="?")
    args = parser.parse_args()

    ptu_to_tiff(args.ptu_path, args.output_dir)


if __name__ == "__main__":
    _main()
