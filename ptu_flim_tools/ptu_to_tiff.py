"""convert a ptu file to tiff files
"""
import logging
import pathlib

import numpy as np
import tifffile
import tttrlib


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


def _read_ptu(path):
    tttr = tttrlib.TTTR(path)
    image = tttrlib.CLSMImage(tttr, fill=True, channels=(0,))

    logging.info("converting to 8bit")
    if image.intensity.max() > 0xFF:
        raise RuntimeError("data can't be converted to 8 bit")

    return image.intensity.astype(np.uint8)


def ptu_to_tiff(ptu_path, output_dir=None):
    """convert a ptu file to tiff files

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

    stack = _read_ptu(path)

    # sum of all frames collapsed into one
    cumulative = stack.sum(axis=0, dtype=np.uint8)

    size = round(stack.size / 10**6, 2)
    logging.info(f"stack shape {stack.shape}, {size} mb, {stack.dtype}")

    _write_tiff("stack", stack, output_dir, path.stem)
    _write_tiff("sum", cumulative, output_dir, path.stem)


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
