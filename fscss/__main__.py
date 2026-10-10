import argparse
import os
import sys
import time

from fscss.compiler import compile_fscss


def compile_file(source_path, output_path):
    with open(source_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    css = compile_fscss(source)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(css)
    return css


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fscss",
        description="Compile FSCSS (Figured Shorthand CSS) to plain CSS")
    parser.add_argument("input", help="input .fscss file")
    parser.add_argument("output", help="output .css file")
    parser.add_argument("--watch", action="store_true",
                        help="recompile whenever the input changes")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        sys.exit("input not found: " + args.input)

    mtime = None
    try:
        while True:
            current = os.path.getmtime(args.input)
            if current != mtime:
                mtime = current
                css = compile_file(args.input, args.output)
                print("compiled %s -> %s (%d bytes)" % (args.input, args.output, len(css)))
            if not args.watch:
                break
            time.sleep(0.6)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()